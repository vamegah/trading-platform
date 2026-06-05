from fastapi import APIRouter

router = APIRouter()


@router.get("/signals/{symbol}")
async def partner_signal(symbol: str) -> dict[str, str | float]:
    return {
        "symbol": symbol.upper(),
        "rating": "watch",
        "confidence": 0.63,
        "distribution": "probabilistic output pending full partner integration",
    }


@router.get("/health")
async def partner_health() -> dict[str, str]:
    return {"status": "healthy", "surface": "partner_api"}

