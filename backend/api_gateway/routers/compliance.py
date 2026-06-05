from fastapi import APIRouter, Header, HTTPException

from backend.services.user_service.privacy import privacy_manager
from backend.shared.audit import audit_chain, database_audit_store
from backend.shared.config import settings
from backend.shared.secret_store import secret_store
from backend.shared.security import Permission, decode_token, require_permission_from_claims

router = APIRouter()


def _claims(authorization: str | None) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        return {}
    return decode_token(authorization.split(" ", 1)[1])


@router.post("/secrets")
async def put_secret(payload: dict, authorization: str | None = Header(default=None)) -> dict[str, object]:
    require_permission_from_claims(_claims(authorization), Permission.MANAGE_SECRETS)
    if not payload.get("name") or not payload.get("value"):
        raise HTTPException(status_code=422, detail="name and value are required")
    try:
        metadata = secret_store.put(str(payload["name"]), str(payload["value"]))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    audit_chain.append("SECRET_UPSERT", {"name_hash": metadata["name_hash"], "version": metadata["active_version"]})
    return metadata


@router.post("/secrets/{name}/rotate")
async def rotate_secret(name: str, payload: dict, authorization: str | None = Header(default=None)) -> dict[str, object]:
    require_permission_from_claims(_claims(authorization), Permission.MANAGE_SECRETS)
    if not payload.get("value"):
        raise HTTPException(status_code=422, detail="value is required")
    try:
        metadata = secret_store.rotate(name, str(payload["value"]))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    audit_chain.append("SECRET_ROTATE", {"name_hash": metadata["name_hash"], "version": metadata["active_version"]})
    return metadata


@router.get("/secrets/{name}")
async def describe_secret(name: str, authorization: str | None = Header(default=None)) -> dict[str, object]:
    require_permission_from_claims(_claims(authorization), Permission.MANAGE_SECRETS)
    try:
        return secret_store.describe(name)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/audit/events")
async def append_audit_event(payload: dict, authorization: str | None = Header(default=None)) -> dict[str, object]:
    require_permission_from_claims(_claims(authorization), Permission.VIEW_AUDIT)
    event = database_audit_store.append(
        payload.get("action", "manual_event"),
        payload.get("details", {}),
        payload.get("user_id"),
    ) if settings.is_production else audit_chain.append(
        payload.get("action", "manual_event"),
        payload.get("details", {}),
        payload.get("user_id"),
    )
    return event.__dict__


@router.get("/audit/verify")
async def verify_audit_chain(authorization: str | None = Header(default=None)) -> dict[str, object]:
    require_permission_from_claims(_claims(authorization), Permission.VIEW_AUDIT)
    return database_audit_store.verify() if settings.is_production else audit_chain.verify()


@router.post("/privacy/consent")
async def save_privacy_consent(payload: dict) -> dict[str, object]:
    try:
        result = privacy_manager.upsert_consent(
            user_id=str(payload.get("user_id", "demo")),
            email=str(payload.get("email", "demo@example.com")),
            consent={key: bool(value) for key, value in payload.get("consent", {}).items()},
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    audit_chain.append("PRIVACY_CONSENT_UPSERT", {"user_id": result["user_id"], "purposes": sorted(payload.get("consent", {}))})
    return result


@router.get("/privacy/export/{user_id}")
async def export_privacy_data(user_id: str) -> dict[str, object]:
    return privacy_manager.export(user_id)


@router.post("/privacy/delete/{user_id}")
async def request_privacy_deletion(user_id: str) -> dict[str, object]:
    result = privacy_manager.request_deletion(user_id)
    audit_chain.append("PRIVACY_DELETION_REQUEST", {"user_id": user_id, "request_id": result["request_id"]})
    return result


@router.get("/privacy/consent/{user_id}")
async def privacy_consent_status(user_id: str) -> dict[str, object]:
    return privacy_manager.consent_status(user_id)


@router.get("/disclosures")
async def regulatory_disclosures() -> dict[str, object]:
    return {
        "platform_status": "research_and_execution_workflow_scaffold",
        "not_registered_as": ["investment_adviser", "broker_dealer", "legal_compliance_system"],
        "live_trading_requires": [
            "legal_review",
            "broker_certification",
            "suitability_completion",
            "explicit_user_consent",
            "risk_limits_and_kill_switch",
            "tamper_evident_audit_retention",
        ],
        "operating_modes": {
            "research": "signals, explanations, backtests, and paper-trading analysis",
            "paper": "simulated orders using production-equivalent validation",
            "one_click_live": "each live order requires explicit approval",
            "automated_live": "requires signed automation acknowledgement and human-reviewed launch controls",
        },
    }
