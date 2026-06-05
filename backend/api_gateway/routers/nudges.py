from fastapi import APIRouter

from backend.services.user_service.nudge_engine import NudgeEngine

router = APIRouter()
engine = NudgeEngine()
_DISMISSAL_LOG: list[dict[str, str]] = []


@router.get("/history")
async def get_nudge_history(user_id: str = "demo") -> list[dict]:
    return await engine.analyze_user_activity(
        user_id,
        [
            {"side": "BUY"},
            {"side": "BUY"},
            {"side": "BUY"},
        ],
    )


@router.post("/dismiss/{event_type}")
async def dismiss_nudge(event_type: str, user_id: str = "demo") -> dict[str, str]:
    record = {"status": "dismissed", "event_type": event_type, "user_id": user_id}
    _DISMISSAL_LOG.append(record)
    return {**record, "logged": "true"}


@router.get("/dismissals")
async def get_dismissal_log(user_id: str = "demo") -> list[dict[str, str]]:
    return [record for record in _DISMISSAL_LOG if record["user_id"] == user_id]
