import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from sqlalchemy.orm import Session

from backend.shared.database import SessionLocal
from backend.shared.models import AuditLog
from backend.shared.security import sanitize_for_log


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def compute_audit_hash(
    previous_hash: str,
    action: str,
    details: dict[str, Any],
    user_id: int | str | None = None,
    timestamp: str | None = None,
) -> str:
    material = {
        "previous_hash": previous_hash,
        "action": action,
        "details": details,
        "user_id": user_id,
        "timestamp": timestamp,
    }
    return hashlib.sha256(canonical_json(material).encode()).hexdigest()


@dataclass(frozen=True)
class AuditEvent:
    action: str
    details: dict[str, Any]
    previous_hash: str
    current_hash: str
    timestamp: str
    user_id: int | str | None = None

    @property
    def event_id(self) -> str:
        return self.current_hash[:16]


class AuditChain:
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    def append(self, action: str, details: dict[str, Any], user_id: int | str | None = None) -> AuditEvent:
        previous_hash = self.events[-1].current_hash if self.events else "0" * 64
        timestamp = datetime.now(timezone.utc).isoformat()
        sanitized_details = sanitize_for_log(details)
        current_hash = compute_audit_hash(previous_hash, action, sanitized_details, user_id, timestamp)
        event = AuditEvent(action, sanitized_details, previous_hash, current_hash, timestamp, user_id)
        self.events.append(event)
        return event

    def verify(self, events: list[AuditEvent] | None = None) -> dict[str, object]:
        chain = events or self.events
        previous = "0" * 64
        for index, event in enumerate(chain):
            expected = compute_audit_hash(previous, event.action, event.details, event.user_id, event.timestamp)
            if event.previous_hash != previous or event.current_hash != expected:
                return {"valid": False, "broken_at": index, "expected_hash": expected}
            previous = event.current_hash
        return {"valid": True, "events": len(chain), "head": previous, "head_event_id": previous[:16]}


class DatabaseAuditStore:
    def __init__(self, session_factory: Callable[[], Session] | None = None) -> None:
        self._session_factory = session_factory or SessionLocal

    def append(self, action: str, details: dict[str, Any], user_id: int | str | None = None) -> AuditEvent:
        db = self._session_factory()
        try:
            last_log = db.query(AuditLog).order_by(AuditLog.id.desc()).first()
            previous_hash = last_log.current_hash if last_log else "0" * 64
            timestamp = datetime.now(timezone.utc)
            timestamp_text = timestamp.isoformat()
            sanitized_details = sanitize_for_log(details)
            current_hash = compute_audit_hash(previous_hash, action, sanitized_details, user_id, timestamp_text)
            row = AuditLog(
                user_id=int(user_id) if str(user_id).isdigit() else None,
                action=action,
                details=sanitized_details,
                timestamp=timestamp.replace(tzinfo=None),
                previous_hash=previous_hash,
                current_hash=current_hash,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return AuditEvent(
                action=row.action,
                details=row.details or {},
                previous_hash=row.previous_hash,
                current_hash=row.current_hash,
                timestamp=timestamp_text,
                user_id=row.user_id,
            )
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def verify(self) -> dict[str, object]:
        db = self._session_factory()
        try:
            rows = db.query(AuditLog).order_by(AuditLog.id.asc()).all()
            previous = "0" * 64
            for index, row in enumerate(rows):
                timestamp = (
                    row.timestamp.replace(tzinfo=timezone.utc).isoformat()
                    if row.timestamp
                    else ""
                )
                expected = compute_audit_hash(previous, row.action, row.details or {}, row.user_id, timestamp)
                if row.previous_hash != previous or row.current_hash != expected:
                    return {"valid": False, "broken_at": index, "expected_hash": expected}
                previous = row.current_hash
            return {"valid": True, "events": len(rows), "head": previous, "head_event_id": previous[:16]}
        finally:
            db.close()


audit_chain = AuditChain()
database_audit_store = DatabaseAuditStore()
