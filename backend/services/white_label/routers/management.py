from fastapi import APIRouter

from backend.services.white_label.models import Partner

router = APIRouter()
_PARTNERS: dict[str, Partner] = {}


@router.post("/partners")
async def onboard_partner(partner: Partner) -> Partner:
    _PARTNERS[partner.id] = partner
    return partner


@router.get("/partners")
async def list_partners() -> list[Partner]:
    return list(_PARTNERS.values())

