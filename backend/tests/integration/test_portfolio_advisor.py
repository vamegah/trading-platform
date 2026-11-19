import asyncio
from datetime import date

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.api_gateway.dependencies import get_db
from backend.api_gateway.main import app
from backend.services.portfolio_advisor_service.advisor import analyze_portfolio_snapshot, run_retirement_projection
from backend.services.portfolio_advisor_service import llm_report
from backend.services.portfolio_advisor_service import research as research_service
from backend.services.portfolio_advisor_service import worker as advisor_worker
from backend.services.portfolio_advisor_service.research import ingest_research_brief
from backend.services.portfolio_advisor_service.schemas import RetirementAssumptions
from backend.shared.audit import database_audit_store
from backend.shared.database import Base
from backend.shared.config import settings
from backend.shared.models import (
    AuditLog,
    MarketData,
    Portfolio,
    PortfolioAdvisorJobModel,
    Position,
    PrivacyRecordModel,
    ResearchSnapshotModel,
    User,
)
from backend.shared.security import create_access_token


def _assumptions() -> RetirementAssumptions:
    return RetirementAssumptions(
        years_until_retirement=10,
        annual_contribution=12000,
        target_annual_income=50000,
        years_in_retirement=25,
        allocation={"equity": 0.7, "fixed_income": 0.3},
        simulations=250,
        seed=42,
    )


def test_retirement_simulation_is_reproducible_and_assumptions_are_returned() -> None:
    first = run_retirement_projection(250000, _assumptions())
    second = run_retirement_projection(250000, _assumptions())

    assert first == second
    assert 0 <= first["success_rate"] <= 1
    assert "not modeled" in first["methodology"]["correlations"]
    assert first["assumptions"]["seed"] == 42


def test_snapshot_analysis_surfaces_stale_prices_without_using_them() -> None:
    snapshot = {
        "portfolio_id": 7,
        "snapshot_id": "snapshot-1",
        "data_snapshot_row_id": 1,
        "content_hash": "hash-1",
        "captured_at": "2026-10-01T00:00:00+00:00",
        "max_market_data_age_days": 5,
        "positions": [
            {
                "symbol": "AAPL",
                "quantity": 10,
                "price": 200,
                "price_as_of": "2026-09-20",
                "price_age_days": 11,
                "price_source": "fixture",
                "price_fresh": False,
                "market_value": None,
                "factor_exposures": {},
            }
        ],
    }

    result = analyze_portfolio_snapshot(snapshot, _assumptions())

    assert result["portfolio"]["known_market_value"] == 0
    assert result["report"]["status"] == "partial"
    assert result["report"]["data_warnings"][0]["reason"] == "stale_or_invalid_price"
    assert result["retirement"]["status"] == "not_calculated"
    assert "execution" not in result
    assert "recommendation" not in result


def test_retirement_assumptions_reject_invalid_allocation() -> None:
    with pytest.raises(ValueError):
        RetirementAssumptions(
            years_until_retirement=10,
            annual_contribution=1000,
            target_annual_income=30000,
            allocation={"equity": 0.7, "fixed_income": 0.2},
        )


def test_bedrock_report_uses_supported_agent_runner_without_exporting_identity(monkeypatch) -> None:
    captured = {}

    class FakeAgent:
        def __init__(self, **kwargs):
            captured["agent"] = kwargs

    class FakeRunner:
        @staticmethod
        async def run(agent, **kwargs):
            captured["input"] = kwargs["input"]
            captured["run_config"] = kwargs["run_config"]
            return type("Result", (), {"final_output": "## Summary\nDiversified exposure."})()

    monkeypatch.setattr(llm_report, "Agent", FakeAgent)
    monkeypatch.setattr(llm_report, "Runner", FakeRunner)
    monkeypatch.setattr(llm_report, "LitellmModel", lambda **kwargs: kwargs)

    result = {
        "portfolio": {"known_market_value": 1200, "position_count": 1},
        "report": {"observations": ["One holding"], "data_warnings": []},
        "charts": {
            "top_holdings": [{"symbol": "AAPL", "price_as_of": "2026-10-01", "price_source": "fixture"}],
            "factor_exposures": [],
        },
        "user_id": 999,
        "email": "private@example.com",
        "retirement": {"target_annual_income": 999999},
    }
    narrative = llm_report.generate_llm_report(result, "us.amazon.nova-pro-v1:0", "us-east-1")

    assert narrative.startswith("## Summary")
    assert captured["agent"]["model"] == {"model": "bedrock/converse/us.amazon.nova-pro-v1:0"}
    assert "AAPL" in captured["input"]
    assert "portfolio_id" not in captured["input"]
    assert "private@example.com" not in captured["input"]
    assert "999999" not in captured["input"]
    assert captured["run_config"].tracing_disabled is True


def test_researcher_brief_ingests_cited_items_into_platform_snapshots(monkeypatch) -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = session_factory()
    requests = []

    class FakeResponse:
        def raise_for_status(self):
            return None

        @staticmethod
        def json():
            return {
                "run_id": "research-run-1",
                "parse_ok": True,
                "brief": {
                    "generated_at_utc": "2026-10-01T12:00:00Z",
                    "window": "7d",
                    "universe": ["AAPL"],
                    "items": [{
                        "headline": "AAPL filed quarterly results",
                        "tickers": ["AAPL"],
                        "summary": "Revenue and margin results were published.",
                        "sources": [{
                            "name": "SEC filing",
                            "url": "https://www.sec.gov/example",
                            "published_at": "2026-10-01T10:00:00Z",
                            "tier": 1,
                        }],
                    }],
                },
            }

    class FakeClient:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, path, json):
            requests.append((path, json))
            return FakeResponse()

    monkeypatch.setattr(research_service.httpx, "AsyncClient", FakeClient)
    result = asyncio.run(ingest_research_brief(
        db,
        job_id="job-research-1",
        result={"charts": {"top_holdings": [{"symbol": "AAPL", "value": 1000}]}},
        base_url="http://researcher-agent:8000",
        api_key="test-service-key",
    ))

    snapshot = db.query(ResearchSnapshotModel).one()
    assert requests[0][0] == "/research"
    assert requests[0][1]["ingest"] is False
    assert requests[0][1]["tickers"] == ["AAPL"]
    assert result["status"] == "ingested"
    assert snapshot.symbol == "AAPL"
    assert snapshot.source_refs[0]["url"] == "https://www.sec.gov/example"
    assert snapshot.audit_id == "advisor-research:job-research-1"
    db.close()
    engine.dispose()


def test_worker_runs_research_and_specialists_when_consent_is_active(monkeypatch) -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    monkeypatch.setattr(advisor_worker, "SessionLocal", session_factory)
    monkeypatch.setattr(database_audit_store, "_session_factory", session_factory)
    monkeypatch.setattr(settings, "portfolio_advisor_llm_enabled", True)
    monkeypatch.setattr(settings, "portfolio_advisor_research_enabled", True)
    monkeypatch.setattr(settings, "researcher_agent_url", "http://researcher-agent:8000")
    monkeypatch.setattr(settings, "researcher_api_key", "test-service-key")
    researcher_calls = []
    tagger_calls = []

    async def fake_research(_db, **kwargs):
        researcher_calls.append(kwargs)
        return {
            "status": "ingested",
            "snapshots": [{"symbol": "AAPL", "source_refs": [{"url": "https://example.test/aapl"}]}],
        }

    monkeypatch.setattr(
        advisor_worker,
        "ingest_research_brief",
        fake_research,
    )
    monkeypatch.setattr(
        advisor_worker,
        "classify_missing_instruments_sync",
        lambda instruments, **_kwargs: tagger_calls.extend(instruments) or [{
            "symbol": "AAPL",
            "allocation_asset_class": {"equity": 100},
            "allocation_regions": {"north_america": 100},
            "allocation_sectors": {"technology": 100},
        }],
    )
    monkeypatch.setattr(
        advisor_worker,
        "generate_llm_narratives",
        lambda *_args: {
            "portfolio_report": "Portfolio narrative with cited research.",
            "retirement_narrative": "The supplied scenario has substantial uncertainty.",
        },
    )
    db = session_factory()
    user = User(email="agent-user@example.com", email_hash="agent-user-hash", hashed_password="unused")
    db.add(user)
    db.flush()
    db.add(PrivacyRecordModel(
        user_id=str(user.id),
        email_hash="agent-user-hash",
        consent={"portfolio_advisor_llm": True},
    ))
    job = PortfolioAdvisorJobModel(
        job_id="job-agent-chain",
        user_id=user.id,
        portfolio_id=1,
        status="pending",
        request_payload={
            "use_llm": True,
            "max_market_data_age_days": 5,
            "retirement": _assumptions().model_dump(mode="json"),
        },
        source_snapshot={
            "portfolio_id": 1,
            "snapshot_id": "snapshot-agent-chain",
            "data_snapshot_row_id": 1,
            "content_hash": "snapshot-hash",
            "captured_at": "2026-10-01T00:00:00+00:00",
            "max_market_data_age_days": 5,
            "positions": [{
                "symbol": "AAPL",
                "quantity": 10,
                "price": 100,
                "price_as_of": "2026-10-01",
                "price_source": "fixture",
                "instrument_name": "Apple Inc.",
                "instrument_type": "equity",
                "instrument_metadata": {},
                "price_age_days": 0,
                "price_fresh": True,
                "market_value": 1000,
                "factor_exposures": {"quality": 0.4},
            }],
        },
        audit_id="audit-request",
    )
    db.add(job)
    db.commit()
    db.close()

    processed = advisor_worker.process_job("job-agent-chain")
    db = session_factory()
    completed = db.query(PortfolioAdvisorJobModel).filter_by(job_id="job-agent-chain").one()
    assert processed is True, completed.error_message
    assert len(researcher_calls) == 1
    assert researcher_calls[0]["job_id"] == "job-agent-chain"
    assert tagger_calls == [{"symbol": "AAPL", "name": "Apple Inc.", "instrument_type": "equity"}]
    assert completed.result_payload["research"]["status"] == "ingested"
    assert completed.result_payload["instrument_tagging"]["classified_symbols"] == ["AAPL"]
    assert completed.result_payload["charts"]["allocation"]["asset_class"][0]["category"] == "equity"
    assert completed.result_payload["multi_agent"]["instrument_tagger"] == "complete"
    assert completed.result_payload["llm_report"]["content"].startswith("Portfolio narrative")
    assert completed.result_payload["llm_retirement"]["content"].startswith("The supplied scenario")
    assert completed.result_payload["multi_agent"]["researcher"] == "ingested"
    assert completed.result_payload["multi_agent"]["retirement_specialist"] == "complete"
    db.close()
    engine.dispose()


def test_analysis_routes_enforce_auth_ownership_idempotency_and_no_execution(monkeypatch) -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(settings, "portfolio_advisor_llm_enabled", True)
    monkeypatch.setattr(database_audit_store, "_session_factory", session_factory)
    published_topics = []
    monkeypatch.setattr(
        "backend.api_gateway.routers.portfolio_advisor.event_bus.publish",
        lambda topic, *_args, **_kwargs: published_topics.append(topic) or {"published": True},
    )
    monkeypatch.setattr("backend.services.portfolio_advisor_service.worker.SessionLocal", session_factory)

    db = session_factory()
    owner = User(email="owner@example.com", email_hash="owner-hash", hashed_password="not-used")
    other = User(email="other@example.com", email_hash="other-hash", hashed_password="not-used")
    db.add_all([owner, other])
    db.flush()
    portfolio = Portfolio(user_id=owner.id, name="Long term")
    other_portfolio = Portfolio(user_id=other.id, name="Other")
    db.add_all([portfolio, other_portfolio])
    db.flush()
    db.add(
        Position(
            portfolio_id=portfolio.id,
            symbol="AAPL",
            asset_type="equity",
            quantity=10,
            average_cost=90,
            market_value=1000,
            factor_exposures={"quality": 0.4},
        )
    )
    db.add(
        MarketData(
            symbol="AAPL",
            date=date.today(),
            open=100,
            high=101,
            low=99,
            close=100,
            volume=1000,
            source="fixture",
        )
    )
    db.commit()
    owner_id, portfolio_id, other_portfolio_id, other_user_id = (
        owner.id,
        portfolio.id,
        other_portfolio.id,
        other.id,
    )
    db.close()

    owner_token = create_access_token({"sub": str(owner_id), "roles": ["user"]})
    other_token = create_access_token({"sub": str(other_user_id), "roles": ["user"]})

    async def requests():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            unauthorized = await client.post(
                "/portfolio-advisor/jobs", json={"portfolio_id": portfolio_id}
            )
            forbidden_portfolio = await client.post(
                "/portfolio-advisor/jobs",
                headers={"Authorization": f"Bearer {owner_token}"},
                json={"portfolio_id": other_portfolio_id},
            )
            payload = {"portfolio_id": portfolio_id, "idempotency_key": "test-advisor-key-001"}
            first = await client.post(
                "/portfolio-advisor/jobs",
                headers={"Authorization": f"Bearer {owner_token}"},
                json=payload,
            )
            conflict = await client.post(
                "/portfolio-advisor/jobs",
                headers={"Authorization": f"Bearer {owner_token}"},
                json={**payload, "max_market_data_age_days": 4},
            )
            repeated = await client.post(
                "/portfolio-advisor/jobs",
                headers={"Authorization": f"Bearer {owner_token}"},
                json=payload,
            )
            hidden_job = await client.get(
                f"/portfolio-advisor/jobs/{first.json()['job_id']}",
                headers={"Authorization": f"Bearer {other_token}"},
            )
            return unauthorized, forbidden_portfolio, first, conflict, repeated, hidden_job

    unauthorized, forbidden_portfolio, first, conflict, repeated, hidden_job = asyncio.run(requests())
    assert unauthorized.status_code == 401
    assert forbidden_portfolio.status_code == 404
    assert first.status_code == 202
    assert conflict.status_code == 409
    assert repeated.status_code == 202
    assert repeated.json()["job_id"] == first.json()["job_id"]
    assert repeated.json()["idempotent"] is True
    assert hidden_job.status_code == 404
    assert published_topics == ["commands.portfolio_advisor"]

    from backend.services.portfolio_advisor_service import worker

    analyze = worker.analyze_portfolio_snapshot
    monkeypatch.setattr(
        worker,
        "analyze_portfolio_snapshot",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("transient analysis failure")),
    )
    assert worker.process_job(first.json()["job_id"]) is False
    db = session_factory()
    retried_job = db.query(PortfolioAdvisorJobModel).filter_by(job_id=first.json()["job_id"]).one()
    assert retried_job.status == "retrying"
    assert retried_job.attempt_count == 1
    db.close()

    monkeypatch.setattr(worker, "analyze_portfolio_snapshot", analyze)
    assert worker.process_job(first.json()["job_id"]) is True
    db = session_factory()
    job = db.query(PortfolioAdvisorJobModel).filter_by(job_id=first.json()["job_id"]).one()
    assert job.status == "completed"
    assert job.attempt_count == 2
    assert job.result_payload["portfolio"]["known_market_value"] == 1000
    assert job.result_payload["report"]["status"] == "complete"
    assert job.result_payload["source_snapshot"]["snapshot_id"] == job.source_snapshot["snapshot_id"]
    assert any(row.action == "portfolio_advisor.completed" for row in db.query(AuditLog).all())
    db.close()

    async def consent_requests():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            no_consent = await client.post(
                "/portfolio-advisor/jobs",
                headers={"Authorization": f"Bearer {owner_token}"},
                json={"portfolio_id": portfolio_id, "use_llm": True},
            )
            enabled = await client.put(
                "/portfolio-advisor/consent",
                headers={"Authorization": f"Bearer {owner_token}"},
                json={"allow_bedrock_processing": True},
            )
            consented = await client.post(
                "/portfolio-advisor/jobs",
                headers={"Authorization": f"Bearer {owner_token}"},
                json={"portfolio_id": portfolio_id, "use_llm": True},
            )
            revoked = await client.put(
                "/portfolio-advisor/consent",
                headers={"Authorization": f"Bearer {owner_token}"},
                json={"allow_bedrock_processing": False},
            )
            no_longer_consented = await client.post(
                "/portfolio-advisor/jobs",
                headers={"Authorization": f"Bearer {owner_token}"},
                json={"portfolio_id": portfolio_id, "use_llm": True},
            )
            return no_consent, enabled, consented, revoked, no_longer_consented

    no_consent, enabled, consented, revoked, no_longer_consented = asyncio.run(consent_requests())
    app.dependency_overrides.pop(get_db, None)
    assert no_consent.status_code == 403
    assert enabled.status_code == 200
    assert enabled.json()["allow_bedrock_processing"] is True
    assert consented.status_code == 202
    assert revoked.status_code == 200
    assert revoked.json()["allow_bedrock_processing"] is False
    assert no_longer_consented.status_code == 403
    consented_job_id = consented.json()["job_id"]
    from backend.services.portfolio_advisor_service import worker

    monkeypatch.setattr(
        worker,
        "generate_llm_narratives",
        lambda *_args, **_kwargs: pytest.fail("revoked consent must block provider inference"),
    )
    assert worker.process_job(consented_job_id) is True
    db = session_factory()
    consented_job = db.query(PortfolioAdvisorJobModel).filter_by(job_id=consented_job_id).one()
    assert consented_job.result_payload["llm_report"]["status"] == "consent_revoked"
    db.close()
    app.dependency_overrides.pop(get_db, None)
    engine.dispose()