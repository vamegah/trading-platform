from fastapi import APIRouter

from backend.services.white_label.metering import record_usage

router = APIRouter()


@router.get("/signals/{symbol}")
async def partner_signal(symbol: str, partner_id: str = "demo") -> dict[str, object]:
    usage = record_usage(partner_id, f"/signals/{symbol}")
    return {"symbol": symbol.upper(), "rating": "watch", "confidence": 0.63, "usage": usage}

