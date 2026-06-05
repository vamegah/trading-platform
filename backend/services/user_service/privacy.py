from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

from sqlalchemy.orm import Session

from backend.shared.config import settings
from backend.shared.database import SessionLocal
from backend.shared.models import PrivacyRecordModel
from backend.shared.security import hash_lookup


@dataclass
class PrivacyRecord:
    user_id: str
    email_hash: str
    consent: dict[str, bool] = field(default_factory=dict)
    deletion_requested_at: str | None = None
    consent_updated_at: str | None = None


class PrivacyManager:
    def __init__(self, session_factory: Callable[[], Session] | None = None) -> None:
        self.records: dict[str, PrivacyRecord] = {}
        self._session_factory = session_factory

    @classmethod
    def database_backed(cls) -> "PrivacyManager":
        return cls(SessionLocal)

    def upsert_consent(self, user_id: str, email: str, consent: dict[str, bool]) -> dict[str, object]:
        if self._session_factory:
            return self._upsert_consent_persisted(user_id, email, consent)
        self._validate_user_id(user_id)
        record = self.records.get(user_id) or PrivacyRecord(user_id=user_id, email_hash=hash_lookup(email))
        record.consent.update(consent)
        record.consent_updated_at = datetime.now(timezone.utc).isoformat()
        self.records[user_id] = record
        return self.export(user_id)

    def export(self, user_id: str) -> dict[str, object]:
        if self._session_factory:
            return self._export_persisted(user_id)
        record = self.records.get(user_id)
        if not record:
            return {"user_id": user_id, "exists": False, "data": {}}
        return {
            "user_id": user_id,
            "exists": True,
            "data": {
                "email_hash": record.email_hash,
                "consent": record.consent,
                "deletion_requested_at": record.deletion_requested_at,
                "consent_updated_at": record.consent_updated_at,
                "privacy_controls": {
                    "export_available": True,
                    "deletion_request_available": True,
                    "retention_policy": "legal_and_regulatory_records_may_be_retained",
                },
            },
        }

    def request_deletion(self, user_id: str) -> dict[str, object]:
        if self._session_factory:
            return self._request_deletion_persisted(user_id)
        self._validate_user_id(user_id)
        record = self.records.get(user_id) or PrivacyRecord(user_id=user_id, email_hash="")
        record.deletion_requested_at = datetime.now(timezone.utc).isoformat()
        self.records[user_id] = record
        return self._deletion_response(user_id, record.deletion_requested_at)

    def consent_status(self, user_id: str) -> dict[str, object]:
        exported = self.export(user_id)
        if not exported["exists"]:
            return {"user_id": user_id, "exists": False, "consent_complete": False, "missing_purposes": []}
        consent = dict(exported["data"].get("consent", {}))
        required = {"analytics", "terms", "research"}
        missing = sorted(required - set(consent))
        return {
            "user_id": user_id,
            "exists": True,
            "consent_complete": not missing,
            "missing_purposes": missing,
            "consent": consent,
        }

    def _validate_user_id(self, user_id: str) -> None:
        if not user_id or not user_id.strip():
            raise ValueError("user_id is required")

    def _deletion_response(self, user_id: str, requested_at: str) -> dict[str, object]:
        return {
            "user_id": user_id,
            "deletion_requested": True,
            "requested_at": requested_at,
            "request_id": f"privacy-delete-{hash_lookup(user_id)[:12]}",
            "status": "pending_legal_retention_review",
            "regulatory_retention_applies": True,
            "retention_policy": {
                "audit_records": "retained_for_regulatory_and_security_obligations",
                "personal_profile": "queued_for_deletion_after_identity_and_retention_review",
            },
        }

    def _upsert_consent_persisted(self, user_id: str, email: str, consent: dict[str, bool]) -> dict[str, object]:
        db = self._session_factory()
        try:
            record = db.query(PrivacyRecordModel).filter(PrivacyRecordModel.user_id == user_id).first()
            if not record:
                record = PrivacyRecordModel(user_id=user_id, email_hash=hash_lookup(email), consent={})
                db.add(record)
            current = dict(record.consent or {})
            current.update(consent)
            record.consent = current
            record.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
            db.commit()
            return self._export_from_record(record)
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def _export_persisted(self, user_id: str) -> dict[str, object]:
        db = self._session_factory()
        try:
            record = db.query(PrivacyRecordModel).filter(PrivacyRecordModel.user_id == user_id).first()
            if not record:
                return {"user_id": user_id, "exists": False, "data": {}}
            return self._export_from_record(record)
        finally:
            db.close()

    def _request_deletion_persisted(self, user_id: str) -> dict[str, object]:
        db = self._session_factory()
        try:
            record = db.query(PrivacyRecordModel).filter(PrivacyRecordModel.user_id == user_id).first()
            if not record:
                record = PrivacyRecordModel(user_id=user_id, email_hash="", consent={})
                db.add(record)
            requested_at = datetime.now(timezone.utc).replace(tzinfo=None)
            record.deletion_requested_at = requested_at
            db.commit()
            return self._deletion_response(user_id, requested_at.replace(tzinfo=timezone.utc).isoformat())
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def _export_from_record(self, record: PrivacyRecordModel) -> dict[str, object]:
        deletion_requested_at = (
            record.deletion_requested_at.replace(tzinfo=timezone.utc).isoformat()
            if record.deletion_requested_at
            else None
        )
        return {
            "user_id": record.user_id,
            "exists": True,
            "data": {
                "email_hash": record.email_hash,
                "consent": record.consent or {},
                "deletion_requested_at": deletion_requested_at,
                "consent_updated_at": (
                    record.updated_at.replace(tzinfo=timezone.utc).isoformat()
                    if record.updated_at
                    else None
                ),
                "privacy_controls": {
                    "export_available": True,
                    "deletion_request_available": True,
                    "retention_policy": "legal_and_regulatory_records_may_be_retained",
                },
            },
        }


privacy_manager = PrivacyManager.database_backed() if settings.is_production else PrivacyManager()
