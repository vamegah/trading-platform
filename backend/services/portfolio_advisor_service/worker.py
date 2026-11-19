import argparse
import asyncio
from datetime import UTC, datetime, timedelta

from backend.services.portfolio_advisor_service.advisor import (
    analyze_portfolio_snapshot,
    attach_instrument_classifications,
)
from backend.services.portfolio_advisor_service.llm_report import generate_llm_narratives
from backend.services.portfolio_advisor_service.research import ingest_research_brief
from backend.services.portfolio_advisor_service.schemas import RetirementAssumptions
from backend.services.portfolio_advisor_service.tagging import classify_missing_instruments_sync
from backend.shared.audit import database_audit_store
from backend.shared.config import settings
from backend.shared.database import SessionLocal
from backend.shared.event_bus import event_bus
from backend.shared.events import EVENT_TYPES, TOPICS
from backend.shared.models import PortfolioAdvisorJobModel, PrivacyRecordModel


MAX_ATTEMPTS = 3
STALE_JOB_MINUTES = 20


def _has_research_consent(user_id: int) -> bool:
    consent_db = SessionLocal()
    try:
        consent = (
            consent_db.query(PrivacyRecordModel)
            .filter(PrivacyRecordModel.user_id == str(user_id))
            .first()
        )
        return bool(
            consent
            and not consent.deletion_requested_at
            and (consent.consent or {}).get("portfolio_advisor_llm")
        )
    finally:
        consent_db.close()


def process_job(job_id: str) -> bool:
    db = SessionLocal()
    try:
        job = (
            db.query(PortfolioAdvisorJobModel)
            .filter(PortfolioAdvisorJobModel.job_id == job_id)
            .with_for_update(skip_locked=True)
            .first()
        )
        if not job or job.status in {"completed", "running"}:
            return bool(job and job.status in {"completed", "running"})
        if job.status not in {"pending", "retrying"} or job.attempt_count >= MAX_ATTEMPTS:
            return False

        job_id_value = job.job_id
        job_user_id = job.user_id
        job_request = dict(job.request_payload)
        source_snapshot = dict(job.source_snapshot)
        job_portfolio_id = job.portfolio_id
        job_snapshot_id = source_snapshot.get("snapshot_id")
        job.status = "running"
        job.attempt_count += 1
        job.error_message = None
        retirement_data = job_request.get("retirement")
        retirement = RetirementAssumptions.model_validate(retirement_data) if retirement_data else None
        db.commit()

        result = analyze_portfolio_snapshot(source_snapshot, retirement)
        result["research"] = {"status": "not_requested", "snapshots": []}
        result["llm_report"] = {"status": "not_requested", "content": None}
        result["llm_retirement"] = {"status": "not_requested", "content": None}
        result["multi_agent"] = {
            "planner": "completed",
            "instrument_tagger": "pending",
            "chart_maker": "completed",
            "report_writer": "not_requested",
            "retirement_specialist": "not_requested",
            "researcher": "not_requested",
        }
        if job_request.get("use_llm"):
            if not _has_research_consent(job_user_id):
                result["llm_report"] = {"status": "consent_revoked", "content": None}
                result["llm_retirement"] = {"status": "consent_revoked", "content": None}
                result["research"] = {"status": "consent_revoked", "snapshots": []}
                result["multi_agent"].update({
                    "instrument_tagger": "blocked",
                    "report_writer": "blocked",
                    "retirement_specialist": "blocked",
                    "researcher": "blocked",
                })
            elif not settings.portfolio_advisor_llm_enabled:
                result["llm_report"] = {"status": "provider_disabled", "content": None}
                result["llm_retirement"] = {"status": "provider_disabled", "content": None}
                result["multi_agent"].update({
                    "instrument_tagger": "disabled",
                    "report_writer": "disabled",
                    "retirement_specialist": "disabled",
                    "researcher": "disabled",
                })
            else:
                allocation_fields = (
                    "allocation_asset_class",
                    "allocation_regions",
                    "allocation_sectors",
                )
                candidates = []
                candidate_symbols = set()
                skipped_symbols = []
                for position in source_snapshot["positions"]:
                    metadata = position.get("instrument_metadata") or {}
                    if all(metadata.get(field) for field in allocation_fields):
                        continue
                    name = str(position.get("instrument_name") or "").strip()
                    if not name:
                        skipped_symbols.append(position["symbol"])
                        continue
                    symbol = position["symbol"].upper()
                    if symbol in candidate_symbols:
                        continue
                    candidate_symbols.add(symbol)
                    candidates.append({
                        "symbol": symbol,
                        "name": name,
                        "instrument_type": position.get("instrument_type") or position.get("asset_type") or "equity",
                    })
                candidates = candidates[:10]
                if candidates and _has_research_consent(job_user_id):
                    try:
                        classifications = classify_missing_instruments_sync(
                            candidates,
                            model_id=settings.portfolio_advisor_bedrock_model_id,
                            region=settings.portfolio_advisor_bedrock_region,
                        )
                        tagger_status = "complete" if len(classifications) == len(candidates) else "partial"
                    except Exception:
                        classifications = []
                        tagger_status = "unavailable"
                elif candidates:
                    classifications = []
                    tagger_status = "consent_revoked"
                else:
                    classifications = []
                    tagger_status = "not_required" if not skipped_symbols else "metadata_unavailable"
                attach_instrument_classifications(
                    result,
                    source_snapshot,
                    classifications,
                    status=tagger_status,
                    skipped_symbols=skipped_symbols,
                )
                result["multi_agent"]["instrument_tagger"] = tagger_status

                if settings.portfolio_advisor_research_enabled:
                    if _has_research_consent(job_user_id):
                        result["research"] = asyncio.run(ingest_research_brief(
                            db,
                            job_id=job_id_value,
                            result=result,
                            base_url=settings.researcher_agent_url,
                            api_key=settings.researcher_api_key or "",
                        ))
                        db.commit()
                    else:
                        result["research"] = {"status": "consent_revoked", "snapshots": []}
                    result["multi_agent"]["researcher"] = result["research"]["status"]
                else:
                    result["research"] = {"status": "disabled", "snapshots": []}
                    result["multi_agent"]["researcher"] = "disabled"

                if not _has_research_consent(job_user_id):
                    result["llm_report"] = {"status": "consent_revoked", "content": None}
                    result["llm_retirement"] = {"status": "consent_revoked", "content": None}
                    result["multi_agent"]["report_writer"] = "blocked"
                    result["multi_agent"]["retirement_specialist"] = "blocked"
                else:
                    try:
                        narratives = generate_llm_narratives(
                            result,
                            settings.portfolio_advisor_bedrock_model_id,
                            settings.portfolio_advisor_bedrock_region,
                        )
                        report = narratives["portfolio_report"]
                        result["llm_report"] = {
                            "status": "complete" if report else "unavailable",
                            "content": report,
                            "provider": "aws_bedrock" if report else None,
                            "model_id": settings.portfolio_advisor_bedrock_model_id if report else None,
                        }
                        retirement_text = narratives["retirement_narrative"]
                        result["llm_retirement"] = {
                            "status": "complete" if retirement_text else (
                                "not_calculated" if result["retirement"].get("status") != "calculated" else "unavailable"
                            ),
                            "content": retirement_text,
                            "provider": "aws_bedrock" if retirement_text else None,
                            "model_id": settings.portfolio_advisor_bedrock_model_id if retirement_text else None,
                        }
                        result["multi_agent"]["report_writer"] = result["llm_report"]["status"]
                        result["multi_agent"]["retirement_specialist"] = result["llm_retirement"]["status"]
                    except Exception:
                        result["llm_report"] = {"status": "unavailable", "content": None}
                        result["llm_retirement"] = {"status": "unavailable", "content": None}
                        result["multi_agent"]["report_writer"] = "unavailable"
                        result["multi_agent"]["retirement_specialist"] = "unavailable"
        audit = database_audit_store.append(
            "portfolio_advisor.completed",
            {
                "job_id": job_id_value,
                "portfolio_id": job_portfolio_id,
                "source_snapshot_id": job_snapshot_id,
                "result_status": result["report"]["status"],
            },
            job_user_id,
        )
        job.result_payload = result
        job.status = "completed"
        job.updated_at = datetime.now(UTC).replace(tzinfo=None)
        job.audit_id = audit.event_id
        db.commit()
        try:
            event_bus.publish(
                TOPICS.portfolio_advisor_events,
                EVENT_TYPES.portfolio_advisor_completed,
                {"job_id": job_id_value, "status": "completed"},
                source="portfolio_advisor_worker",
                correlation_id=job_id_value,
            )
        except Exception:
            pass
        return True
    except Exception as exc:
        db.rollback()
        job = (
            db.query(PortfolioAdvisorJobModel)
            .filter(PortfolioAdvisorJobModel.job_id == job_id)
            .first()
        )
        if job:
            job.status = "failed" if job.attempt_count >= MAX_ATTEMPTS else "retrying"
            job.error_message = str(exc)[:1000]
            job.updated_at = datetime.now(UTC).replace(tzinfo=None)
            db.commit()
        return False
    finally:
        db.close()


async def run_once(consumer: str = "portfolio-advisor-worker") -> dict[str, int]:
    try:
        messages = event_bus.read_for_consumer(
            TOPICS.portfolio_advisor_commands,
            "portfolio-advisor-service",
            consumer,
            count=10,
            block_ms=100,
        )
    except Exception:
        messages = []
    handled_ids = set()
    acked: list[str] = []
    processed = 0
    for message in messages:
        envelope = message["envelope"]
        if envelope.get("event_type") != EVENT_TYPES.portfolio_advisor_requested:
            acked.append(str(message["stream_id"]))
            continue
        job_id = str((envelope.get("payload") or {}).get("job_id", ""))
        if job_id:
            handled_ids.add(job_id)
            if await asyncio.to_thread(process_job, job_id):
                processed += 1
                acked.append(str(message["stream_id"]))

    db = SessionLocal()
    try:
        stale_before = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=STALE_JOB_MINUTES)
        db.query(PortfolioAdvisorJobModel).filter(
            PortfolioAdvisorJobModel.status == "running",
            PortfolioAdvisorJobModel.updated_at < stale_before,
        ).update({PortfolioAdvisorJobModel.status: "retrying"}, synchronize_session=False)
        db.commit()
        pending_ids = [
            row.job_id
            for row in (
                db.query(PortfolioAdvisorJobModel)
                .filter(PortfolioAdvisorJobModel.status.in_(("pending", "retrying")))
                .order_by(PortfolioAdvisorJobModel.created_at)
                .limit(10)
                .all()
            )
        ]
    finally:
        db.close()

    for job_id in pending_ids:
        if job_id not in handled_ids and await asyncio.to_thread(process_job, job_id):
            processed += 1
    try:
        event_bus.ack(TOPICS.portfolio_advisor_commands, "portfolio-advisor-service", *acked)
    except Exception:
        pass
    return {"processed": processed, "pending_checked": len(pending_ids)}


async def run_forever(consumer: str = "portfolio-advisor-worker") -> None:
    while True:
        await run_once(consumer)
        await asyncio.sleep(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Consume portfolio advisor jobs.")
    parser.add_argument("--consumer", default="portfolio-advisor-worker")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    if args.once:
        print(asyncio.run(run_once(args.consumer)))
        return
    asyncio.run(run_forever(args.consumer))


if __name__ == "__main__":
    main()