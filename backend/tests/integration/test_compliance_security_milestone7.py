import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.api_gateway.main import app
from backend.services.signal_orchestrator.orchestrator import generate_signal
from backend.services.user_service.privacy import PrivacyManager
from backend.shared.audit import AuditChain, DatabaseAuditStore
from backend.shared.database import Base
from backend.shared.models import AuditLog
from backend.shared.secret_store import SecretStore
from backend.shared.security import (
    Permission,
    create_access_token,
    has_permission,
    permission_report,
    require_permission_from_claims,
    sanitize_for_log,
)


def test_rbac_permissions_cover_user_admin_and_service_roles() -> None:
    assert has_permission(["user"], Permission.READ_SIGNALS) is True
    assert has_permission(["user"], Permission.MANAGE_SECRETS) is False
    assert has_permission(["admin"], Permission.MANAGE_SECRETS) is True
    assert has_permission(["service"], Permission.SERVICE_INTERNAL) is True
    assert has_permission(["user"], "not:a:permission") is False
    assert "trade:one_click" in permission_report(["user"])["permissions"]

    with pytest.raises(HTTPException):
        require_permission_from_claims({"roles": ["user"]}, Permission.VIEW_AUDIT)


def test_secret_store_encrypts_rotates_and_redacts_sensitive_values() -> None:
    store = SecretStore()
    first = store.put("alpaca_api_key", "first-secret")
    second = store.rotate("alpaca_api_key", "second-secret")

    assert first["active_version"] == 1
    assert second["active_version"] == 2
    assert store.get("alpaca_api_key") == "second-secret"
    assert store.describe("alpaca_api_key")["last_accessed_at"] is not None
    assert store.describe("alpaca_api_key")["version_history"][1]["rotated_from_version"] == 1
    assert "second-secret" not in str(second)
    sanitized = sanitize_for_log({"api_key": "plain", "nested": {"refresh_token": "plain"}, "symbol": "MSFT"})
    assert sanitized["api_key"] == "[REDACTED]"
    assert sanitized["nested"]["refresh_token"] == "[REDACTED]"


def test_tamper_evident_audit_chain_detects_modified_events() -> None:
    chain = AuditChain()
    first = chain.append("SIGNAL_CREATE", {"symbol": "MSFT"}, user_id=1)
    chain.append("ORDER_PRECHECK", {"allowed": True}, user_id=1)

    assert chain.verify()["valid"] is True
    first.details["symbol"] = "AAPL"
    assert chain.verify()["valid"] is False


def test_database_audit_chain_hashes_persisted_timestamp_and_detects_timestamp_tampering() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine, tables=[AuditLog.__table__])
    sessions = sessionmaker(bind=engine)
    store = DatabaseAuditStore(sessions)

    store.append("ORDER_CREATE", {"symbol": "MSFT"}, user_id=1)
    assert store.verify()["valid"] is True

    db = sessions()
    try:
        row = db.query(AuditLog).first()
        row.timestamp = row.timestamp.replace(year=row.timestamp.year - 1)
        db.commit()
    finally:
        db.close()

    assert store.verify()["valid"] is False


def test_privacy_manager_exports_consent_and_records_deletion_request() -> None:
    manager = PrivacyManager()
    manager.upsert_consent("user-1", "person@example.com", {"marketing": False, "analytics": True})
    exported = manager.export("user-1")
    deleted = manager.request_deletion("user-1")

    assert exported["exists"] is True
    assert exported["data"]["email_hash"] != "person@example.com"
    assert exported["data"]["consent"]["analytics"] is True
    assert deleted["deletion_requested"] is True
    assert deleted["regulatory_retention_applies"] is True
    assert manager.consent_status("user-1")["missing_purposes"] == ["research", "terms"]


@pytest.mark.asyncio
async def test_signal_contains_reproducibility_metadata_for_regulatory_review() -> None:
    signal = await generate_signal("MSFT")

    assert signal["model_version_id"]
    assert signal["data_snapshot_id"]
    assert signal["audit_metadata"]["reproducible"] is True
    assert signal["audit_metadata"]["input_data_hash"]
    assert signal["audit_metadata"]["replay_instructions"]["symbol"] == "MSFT"
    assert "market_data" in signal["audit_metadata"]["input_data_snapshots"]
    assert "signal_orchestrator" in signal["audit_metadata"]["model_versions"]


@pytest.mark.asyncio
async def test_compliance_gateway_enforces_rbac_and_supports_privacy_workflows() -> None:
    admin_token = create_access_token({"sub": "1", "roles": ["admin"]})
    user_token = create_access_token({"sub": "2", "roles": ["user"]})
    headers = {"Authorization": f"Bearer {admin_token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        forbidden = await client.post(
            "/compliance/secrets",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"name": "polygon", "value": "secret-value"},
        )
        secret = await client.post(
            "/compliance/secrets",
            headers=headers,
            json={"name": "polygon", "value": "secret-value"},
        )
        rotated = await client.post(
            "/compliance/secrets/polygon/rotate",
            headers=headers,
            json={"value": "rotated-secret"},
        )
        audit = await client.post(
            "/compliance/audit/events",
            headers=headers,
            json={"action": "MODEL_PROMOTION", "details": {"model": "challenger"}},
        )
        verified = await client.get("/compliance/audit/verify", headers=headers)
        consent = await client.post(
            "/compliance/privacy/consent",
            json={"user_id": "demo", "email": "demo@example.com", "consent": {"analytics": True}},
        )
        export = await client.get("/compliance/privacy/export/demo")
        deletion = await client.post("/compliance/privacy/delete/demo")
        consent_status = await client.get("/compliance/privacy/consent/demo")
        disclosures = await client.get("/compliance/disclosures")
        anonymous_secret = await client.post(
            "/compliance/secrets",
            json={"name": "anonymous", "value": "secret-value"},
        )

    assert forbidden.status_code == 403
    assert anonymous_secret.status_code == 401
    assert secret.status_code == 200
    assert secret.json()["encrypted"] is True
    assert secret.json()["plaintext_exposed"] is False
    assert rotated.json()["active_version"] == 2
    assert audit.status_code == 200
    assert verified.json()["valid"] is True
    assert consent.json()["data"]["consent"]["analytics"] is True
    assert export.json()["exists"] is True
    assert deletion.json()["deletion_requested"] is True
    assert consent_status.json()["exists"] is True
    assert disclosures.json()["platform_status"] == "research_and_execution_workflow_scaffold"
