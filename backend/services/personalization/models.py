from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class UserPersonaProfile:
    user_id: str
    persona: str
    nudge_sensitivity: float
    preferred_detail_level: str
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class UserPreferenceOverride:
    user_id: str
    key: str
    value: str

