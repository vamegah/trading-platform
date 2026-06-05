from datetime import datetime

from fastapi import APIRouter

from backend.services.signal_orchestrator.orchestrator import attach_freshness

router = APIRouter()


@router.post("")
async def freshness(signal: dict) -> dict:
    now = signal.pop("now", None)
    return attach_freshness(
        signal,
        datetime.fromisoformat(now) if isinstance(now, str) else None,
    )

