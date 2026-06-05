from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.services.user_service.privacy import PrivacyManager
from backend.shared.audit import DatabaseAuditStore
from backend.shared.database import Base
from backend.shared.models import AuditLog, PrivacyRecordModel, SecretRecord
from backend.shared.secret_store import SecretStore


def _session_factory():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine, tables=[AuditLog.__table__, SecretRecord.__table__, PrivacyRecordModel.__table__])
    return sessionmaker(bind=engine)


def test_database_secret_store_persists_rotates_and_redacts() -> None:
    sessions = _session_factory()
    first_store = SecretStore(sessions)

    first_metadata = first_store.put("alpaca_api_secret", "first-secret")
    second_metadata = first_store.rotate("alpaca_api_secret", "second-secret")

    reloaded_store = SecretStore(sessions)

    assert first_metadata["active_version"] == 1
    assert second_metadata["active_version"] == 2
    assert reloaded_store.get("alpaca_api_secret") == "second-secret"
    assert "second-secret" not in str(reloaded_store.describe("alpaca_api_secret"))


def test_database_audit_store_verifies_persisted_hash_chain_and_detects_tampering() -> None:
    sessions = _session_factory()
    audit_store = DatabaseAuditStore(sessions)

    audit_store.append("ORDER_CREATED", {"symbol": "MSFT"}, user_id=1)
    audit_store.append("ORDER_FILLED", {"symbol": "MSFT", "price": 101.0}, user_id=1)

    assert DatabaseAuditStore(sessions).verify()["valid"] is True

    db = sessions()
    try:
        row = db.query(AuditLog).order_by(AuditLog.id.desc()).first()
        row.details = {"symbol": "AAPL"}
        db.commit()
    finally:
        db.close()

    assert DatabaseAuditStore(sessions).verify()["valid"] is False


def test_database_privacy_manager_survives_restart_and_tracks_deletion_request() -> None:
    sessions = _session_factory()
    manager = PrivacyManager(sessions)

    manager.upsert_consent("user-1", "user@example.com", {"analytics": True})
    reloaded = PrivacyManager(sessions)
    export = reloaded.export("user-1")

    assert export["exists"] is True
    assert export["data"]["consent"] == {"analytics": True}

    deletion = reloaded.request_deletion("user-1")
    assert deletion["deletion_requested"] is True
    assert PrivacyManager(sessions).export("user-1")["data"]["deletion_requested_at"] is not None
