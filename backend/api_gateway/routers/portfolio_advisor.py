from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.api_gateway.dependencies import get_current_active_user
from backend.services.portfolio_advisor_service.advisor import build_source_snapshot
from backend.services.portfolio_advisor_service.schemas import PortfolioAdvisorRequest
from backend.shared.audit import database_audit_store
from backend.shared.config import settings
from backend.shared.database import get_db
from backend.shared.event_bus import event_bus
from backend.shared.events import EVENT_TYPES, TOPICS
from backend.shared.models import Portfolio, PortfolioAdvisorJobModel, PrivacyRecordModel, User
from backend.shared.security import hash_lookup

router = APIRouter()


class PortfolioAdvisorConsentRequest(BaseModel):
    allow_bedrock_processing: bool


def _advisor_consent_record(db: Session, user: User) -> PrivacyRecordModel | None:
    return (
        db.query(PrivacyRecordModel)
        .filter(PrivacyRecordModel.user_id == str(user.id))
        .first()
    )


@router.get("/consent")
def get_portfolio_advisor_consent(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, object]:
    record = _advisor_consent_record(db, current_user)
    consent = bool(record and (record.consent or {}).get("portfolio_advisor_llm"))
    if record and record.deletion_requested_at:
        consent = False
    return {
        "allow_bedrock_processing": consent,
        "provider_enabled": settings.portfolio_advisor_llm_enabled,
        "research_enabled": settings.portfolio_advisor_research_enabled,
        "researcher_configured": bool(settings.researcher_agent_url),
        "model_id": settings.portfolio_advisor_bedrock_model_id if settings.portfolio_advisor_llm_enabled else None,
        "disclosure": "When enabled, portfolio symbols are searched using the configured web/news sources and a minimized analysis snapshot plus cited research is sent to Amazon Bedrock for narrative generation. User identity, email, portfolio ID, and retirement assumptions are excluded. AWS account, region, web-source, and provider processing terms apply.",
    }


@router.put("/consent")
def set_portfolio_advisor_consent(
    request: PortfolioAdvisorConsentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, object]:
    record = _advisor_consent_record(db, current_user)
    if request.allow_bedrock_processing and record and record.deletion_requested_at:
        raise HTTPException(status_code=409, detail="Consent cannot be enabled while a deletion request is pending")
    if not record:
        record = PrivacyRecordModel(
            user_id=str(current_user.id),
            email_hash=hash_lookup(current_user.email),
            consent={},
        )
        db.add(record)
    consent = dict(record.consent or {})
    consent["portfolio_advisor_llm"] = request.allow_bedrock_processing
    record.consent = consent
    db.commit()
    database_audit_store.append(
        "portfolio_advisor.llm_consent_updated",
        {"enabled": request.allow_bedrock_processing},
        current_user.id,
    )
    return get_portfolio_advisor_consent(db, current_user)


@router.get("/portfolios")
def list_advisor_portfolios(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, object]:
    portfolios = (
        db.query(Portfolio)
        .filter(Portfolio.user_id == current_user.id)
        .order_by(Portfolio.created_at.desc(), Portfolio.id.desc())
        .all()
    )
    return {
        "portfolios": [
            {"id": portfolio.id, "name": portfolio.name, "risk_profile": portfolio.risk_profile}
            for portfolio in portfolios
        ]
    }


@router.post("/jobs", status_code=202)
def request_portfolio_analysis(
    request: PortfolioAdvisorRequest,
    idempotency_header: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, object]:
    idempotency_key = idempotency_header or request.idempotency_key
    request_payload = {
        "retirement": request.retirement.model_dump(mode="json") if request.retirement else None,
        "max_market_data_age_days": request.max_market_data_age_days,
    }
    if request.use_llm:
        if not settings.portfolio_advisor_llm_enabled:
            raise HTTPException(status_code=503, detail="LLM report generation is not enabled")
        consent_record = _advisor_consent_record(db, current_user)
        if not consent_record or not (consent_record.consent or {}).get("portfolio_advisor_llm"):
            raise HTTPException(status_code=403, detail="Explicit portfolio-analysis AI consent is required")
        if consent_record.deletion_requested_at:
            raise HTTPException(status_code=409, detail="LLM processing is blocked while deletion is pending")
    request_payload["use_llm"] = request.use_llm
    if idempotency_key:
        existing = (
            db.query(PortfolioAdvisorJobModel)
            .filter(
                PortfolioAdvisorJobModel.user_id == current_user.id,
                PortfolioAdvisorJobModel.idempotency_key == idempotency_key,
            )
            .first()
        )
        if existing:
            if existing.portfolio_id != request.portfolio_id or existing.request_payload != request_payload:
                raise HTTPException(status_code=409, detail="Idempotency key was used for a different request")
            return {"job_id": existing.job_id, "status": existing.status, "idempotent": True}

    portfolio = (
        db.query(Portfolio)
        .filter(Portfolio.id == request.portfolio_id, Portfolio.user_id == current_user.id)
        .first()
    )
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    try:
        source_snapshot = build_source_snapshot(
            db,
            portfolio_id=portfolio.id,
            max_market_data_age_days=request.max_market_data_age_days,
        )
        job_id = str(uuid4())
        audit_event = database_audit_store.append(
            "portfolio_advisor.requested",
            {
                "job_id": job_id,
                "portfolio_id": portfolio.id,
                "source_snapshot_id": source_snapshot["snapshot_id"],
            },
            current_user.id,
        )
        job = PortfolioAdvisorJobModel(
            job_id=job_id,
            user_id=current_user.id,
            portfolio_id=portfolio.id,
            idempotency_key=idempotency_key,
            status="pending",
            request_payload=request_payload,
            source_snapshot=source_snapshot,
            audit_id=audit_event.event_id,
        )
        db.add(job)
        db.commit()
    except IntegrityError:
        db.rollback()
        if idempotency_key:
            existing = (
                db.query(PortfolioAdvisorJobModel)
                .filter(
                    PortfolioAdvisorJobModel.user_id == current_user.id,
                    PortfolioAdvisorJobModel.idempotency_key == idempotency_key,
                )
                .first()
            )
            if existing:
                if existing.portfolio_id != request.portfolio_id or existing.request_payload != request_payload:
                    raise HTTPException(status_code=409, detail="Idempotency key was used for a different request")
                return {"job_id": existing.job_id, "status": existing.status, "idempotent": True}
        raise HTTPException(status_code=409, detail="Analysis request conflicts with an existing job")
    except Exception:
        db.rollback()
        raise

    try:
        event_bus.publish(
            TOPICS.portfolio_advisor_commands,
            EVENT_TYPES.portfolio_advisor_requested,
            {"job_id": job_id},
            source="api_gateway",
            correlation_id=job_id,
        )
    except Exception:
        pass
    return {"job_id": job_id, "status": "pending", "idempotent": False}


@router.get("/jobs/{job_id}")
def get_portfolio_analysis(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, object]:
    job = (
        db.query(PortfolioAdvisorJobModel)
        .filter(
            PortfolioAdvisorJobModel.job_id == job_id,
            PortfolioAdvisorJobModel.user_id == current_user.id,
        )
        .first()
    )
    if not job:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return {
        "job_id": job.job_id,
        "status": job.status,
        "portfolio_id": job.portfolio_id,
        "result": job.result_payload,
        "error": job.error_message,
        "audit_id": job.audit_id,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
    }