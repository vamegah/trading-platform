import pytest
from fastapi import HTTPException

from backend.shared.audit import AuditChain
from backend.shared.security import (
    Permission,
    create_access_token,
    create_refresh_token,
    create_service_token,
    decode_token,
    has_permission,
    require_permission_from_claims,
    sanitize_for_log,
)
from backend.shared.secret_store import SecretStore


def test_invalid_token_decodes_to_empty_claims_and_fails_permission_check() -> None:
    assert decode_token("not-a-token") == {}
    assert has_permission(["admin"], "invalid:permission") is False
    with pytest.raises(HTTPException):
        require_permission_from_claims({}, Permission.MANAGE_USERS)


def test_admin_token_allows_audit_permission_but_user_token_does_not() -> None:
    admin = decode_token(create_access_token({"sub": "1", "roles": ["admin"]}))
    user = decode_token(create_access_token({"sub": "2", "roles": ["user"]}))

    require_permission_from_claims(admin, Permission.VIEW_AUDIT)
    with pytest.raises(HTTPException):
        require_permission_from_claims(user, Permission.VIEW_AUDIT)


def test_token_types_fail_closed_for_action_and_service_authorization() -> None:
    refresh = decode_token(create_refresh_token({"sub": "1", "roles": ["admin"]}))
    forged_service_role = decode_token(create_access_token({"sub": "2", "roles": ["service"]}))
    service = decode_token(create_service_token("signal_orchestrator"))

    with pytest.raises(HTTPException):
        require_permission_from_claims(refresh, Permission.VIEW_AUDIT)
    with pytest.raises(HTTPException):
        require_permission_from_claims(forged_service_role, Permission.SERVICE_INTERNAL)
    require_permission_from_claims(service, Permission.SERVICE_INTERNAL)


def test_secret_store_does_not_expose_plaintext_in_metadata() -> None:
    store = SecretStore()
    metadata = store.put("broker_secret", "plain-secret")

    assert "plain-secret" not in str(metadata)
    assert store.get("broker_secret") == "plain-secret"
    assert store.describe("broker_secret")["plaintext_exposed"] is False
    with pytest.raises(ValueError):
        store.put("", "plain-secret")


def test_recursive_log_redaction_removes_nested_credentials() -> None:
    payload = sanitize_for_log(
        {
            "symbol": "MSFT",
            "nested": {"api_key": "secret", "items": [{"refresh_token": "secret"}]},
        }
    )

    assert payload["symbol"] == "MSFT"
    assert payload["nested"]["api_key"] == "[REDACTED]"
    assert payload["nested"]["items"][0]["refresh_token"] == "[REDACTED]"


def test_audit_immutability_fails_closed_on_tampering() -> None:
    chain = AuditChain()
    event = chain.append("ORDER", {"symbol": "MSFT", "api_key": "secret"}, user_id=1)
    assert chain.verify()["valid"] is True
    assert event.details["api_key"] == "[REDACTED]"
    event.details["symbol"] = "AAPL"
    assert chain.verify()["valid"] is False
