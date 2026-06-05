from fastapi import APIRouter

from backend.services.personalization.models import UserPreferenceOverride

router = APIRouter()
_PREFERENCES: list[UserPreferenceOverride] = []


@router.post("")
async def set_preference(preference: UserPreferenceOverride) -> UserPreferenceOverride:
    _PREFERENCES.append(preference)
    return preference


@router.get("/{user_id}")
async def get_preferences(user_id: str) -> list[UserPreferenceOverride]:
    return [preference for preference in _PREFERENCES if preference.user_id == user_id]

