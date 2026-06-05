from backend.services.personalization.models import UserPersonaProfile


def build_persona(user_id: str) -> dict[str, object]:
    profile = UserPersonaProfile(
        user_id=user_id,
        persona="disciplined_researcher",
        nudge_sensitivity=0.45,
        preferred_detail_level="high",
    )
    return profile.__dict__

