from fastapi import APIRouter

router = APIRouter()


@router.get("/{partner_id}/invoice-preview")
async def invoice_preview(partner_id: str) -> dict[str, str | float]:
    return {"partner_id": partner_id, "currency": "USD", "estimated_total": 0.0}

