from fastapi import APIRouter
from pydantic import BaseModel

from backend.services.notification_service.push import send_notification

router = APIRouter()


class AlertPreferences(BaseModel):
    user_id: str = "demo"
    push_enabled: bool = True
    email_enabled: bool = False
    high_conviction_threshold: float = 0.7
    stop_loss_alerts: bool = True
    thesis_change_alerts: bool = True


_PREFERENCES: dict[str, AlertPreferences] = {}


@router.get("")
async def list_alerts(user_id: str = "demo") -> list[dict[str, str | float]]:
    return [
        {"type": "high_conviction_signal", "symbol": "MSFT", "confidence": 0.72, "status": "queued"},
        {"type": "thesis_change", "symbol": "NVDA", "confidence": 0.64, "status": "watching"},
    ]


@router.get("/preferences/{user_id}")
async def get_preferences(user_id: str) -> AlertPreferences:
    return _PREFERENCES.get(user_id, AlertPreferences(user_id=user_id))


@router.post("/preferences")
async def save_preferences(preferences: AlertPreferences) -> AlertPreferences:
    _PREFERENCES[preferences.user_id] = preferences
    return preferences


@router.post("/test")
async def test_alert(message: str = "Alert preferences saved") -> dict[str, str]:
    return send_notification(message, priority="normal")
