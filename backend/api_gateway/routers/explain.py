from fastapi import APIRouter

from backend.services.explainability import generate_explanation

router = APIRouter()


@router.get("/{symbol}")
async def explain_signal(symbol: str) -> dict[str, object]:
    return await generate_explanation(symbol.upper())
