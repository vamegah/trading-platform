from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Partner:
    id: str
    name: str
    status: str = "pending"
    theme_id: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class UsageRecord:
    partner_id: str
    endpoint: str
    units: int = 1

