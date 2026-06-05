from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4


@dataclass(frozen=True)
class AgentEnvelope:
    agent_id: str
    action: str
    payload: dict
    correlation_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)


def encode_message(envelope: AgentEnvelope) -> dict:
    return {
        "agent_id": envelope.agent_id,
        "action": envelope.action,
        "payload": envelope.payload,
        "correlation_id": envelope.correlation_id,
        "created_at": envelope.created_at.isoformat(),
    }

