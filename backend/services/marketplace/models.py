from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class MarketplaceAgent:
    id: str
    name: str
    publisher_id: str
    asset_types: list[str]
    description: str
    version: str = "0.1.0"
    status: str = "pending_review"
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AgentSubscription:
    user_id: str
    agent_id: str
    tier: str = "free"
    active: bool = True


@dataclass
class AgentReview:
    user_id: str
    agent_id: str
    rating: int
    comment: str = ""

