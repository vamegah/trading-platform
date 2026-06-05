from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from sqlalchemy.orm import Session

from backend.shared.config import settings
from backend.shared.database import SessionLocal
from backend.shared.models import SecretRecord
from backend.shared.security import decrypt_data, encrypt_data, hash_lookup


@dataclass(frozen=True)
class SecretVersion:
    name: str
    version: int
    ciphertext: str
    created_at: str
    key_id: str | None = None
    rotated_from_version: int | None = None
    active: bool = True


class SecretStore:
    def __init__(self, session_factory: Callable[[], Session] | None = None) -> None:
        self._versions: dict[str, list[SecretVersion]] = {}
        self._access_log: dict[str, list[str]] = {}
        self._session_factory = session_factory

    @classmethod
    def database_backed(cls) -> "SecretStore":
        return cls(SessionLocal)

    def put(self, name: str, plaintext: str) -> dict[str, object]:
        self._validate_secret_input(name, plaintext)
        if self._session_factory:
            return self._put_persisted(name, plaintext)
        normalized = hash_lookup(name)
        versions = self._versions.setdefault(normalized, [])
        previous_active = next((version for version in reversed(versions) if version.active), None)
        for version in versions:
            object.__setattr__(version, "active", False)
        secret = SecretVersion(
            name=normalized,
            version=len(versions) + 1,
            ciphertext=encrypt_data(plaintext),
            created_at=datetime.now(timezone.utc).isoformat(),
            key_id=settings.broker_encryption_key_id or settings.kms_key_id,
            rotated_from_version=previous_active.version if previous_active else None,
            active=True,
        )
        versions.append(secret)
        return self.describe(name)

    def get(self, name: str) -> str | None:
        self._validate_secret_name(name)
        if self._session_factory:
            return self._get_persisted(name)
        normalized = hash_lookup(name)
        versions = self._versions.get(normalized, [])
        for version in reversed(versions):
            if version.active:
                self._record_access(normalized)
                return decrypt_data(version.ciphertext)
        return None

    def rotate(self, name: str, plaintext: str) -> dict[str, object]:
        return self.put(name, plaintext)

    def describe(self, name: str) -> dict[str, object]:
        self._validate_secret_name(name)
        if self._session_factory:
            return self._describe_persisted(name)
        normalized = hash_lookup(name)
        versions = self._versions.get(normalized, [])
        active = next((version for version in reversed(versions) if version.active), None)
        return {
            "name_hash": normalized,
            "active_version": active.version if active else None,
            "versions": len(versions),
            "encrypted": bool(active),
            "key_id": active.key_id if active else None,
            "created_at": active.created_at if active else None,
            "last_rotated_at": active.created_at if active and active.version > 1 else None,
            "last_accessed_at": self._access_log.get(normalized, [None])[-1],
            "version_history": [
                {
                    "version": version.version,
                    "active": version.active,
                    "created_at": version.created_at,
                    "rotated_from_version": version.rotated_from_version,
                }
                for version in versions
            ],
            "plaintext_exposed": False,
        }

    def _validate_secret_input(self, name: str, plaintext: str) -> None:
        self._validate_secret_name(name)
        if not plaintext or len(plaintext.strip()) < 4:
            raise ValueError("secret value must be at least 4 characters")

    def _validate_secret_name(self, name: str) -> None:
        if not name or not name.strip():
            raise ValueError("secret name is required")

    def _record_access(self, normalized: str) -> None:
        self._access_log.setdefault(normalized, []).append(datetime.now(timezone.utc).isoformat())

    def _put_persisted(self, name: str, plaintext: str) -> dict[str, object]:
        normalized = hash_lookup(name)
        db = self._session_factory()
        try:
            active_versions = (
                db.query(SecretRecord)
                .filter(SecretRecord.name_hash == normalized, SecretRecord.active.is_(True))
                .all()
            )
            for version in active_versions:
                version.active = False
            latest = (
                db.query(SecretRecord)
                .filter(SecretRecord.name_hash == normalized)
                .order_by(SecretRecord.version.desc())
                .first()
            )
            next_version = (latest.version if latest else 0) + 1
            db.add(
                SecretRecord(
                    name_hash=normalized,
                    version=next_version,
                    ciphertext=encrypt_data(plaintext),
                    key_id=settings.broker_encryption_key_id or settings.kms_key_id,
                    active=True,
                    secret_metadata={
                        "managed_by": "trading-platform",
                        "rotated_from_version": latest.version if latest else None,
                        "rotation_reason": "initial_create" if next_version == 1 else "manual_rotation",
                    },
                )
            )
            db.commit()
            return self._describe_with_session(db, normalized)
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def _get_persisted(self, name: str) -> str | None:
        normalized = hash_lookup(name)
        db = self._session_factory()
        try:
            active = (
                db.query(SecretRecord)
                .filter(SecretRecord.name_hash == normalized, SecretRecord.active.is_(True))
                .order_by(SecretRecord.version.desc())
                .first()
            )
            self._record_access(normalized)
            return decrypt_data(active.ciphertext) if active else None
        finally:
            db.close()

    def _describe_persisted(self, name: str) -> dict[str, object]:
        normalized = hash_lookup(name)
        db = self._session_factory()
        try:
            return self._describe_with_session(db, normalized)
        finally:
            db.close()

    def _describe_with_session(self, db: Session, normalized: str) -> dict[str, object]:
        versions = (
            db.query(SecretRecord)
            .filter(SecretRecord.name_hash == normalized)
            .order_by(SecretRecord.version.asc())
            .all()
        )
        active = next((version for version in reversed(versions) if version.active), None)
        return {
            "name_hash": normalized,
            "active_version": active.version if active else None,
            "versions": len(versions),
            "encrypted": bool(active),
            "key_id": active.key_id if active else None,
            "created_at": active.created_at.isoformat() if active and active.created_at else None,
            "last_rotated_at": active.created_at.isoformat() if active and active.version > 1 and active.created_at else None,
            "last_accessed_at": self._access_log.get(normalized, [None])[-1],
            "version_history": [
                {
                    "version": version.version,
                    "active": version.active,
                    "created_at": version.created_at.isoformat() if version.created_at else None,
                    "rotated_from_version": (version.secret_metadata or {}).get("rotated_from_version"),
                }
                for version in versions
            ],
            "plaintext_exposed": False,
        }


secret_store = SecretStore.database_backed() if settings.is_production else SecretStore()
