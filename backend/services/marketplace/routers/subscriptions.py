from fastapi import APIRouter

from backend.services.marketplace.models import AgentSubscription

router = APIRouter()

_SUBSCRIPTIONS: list[AgentSubscription] = []


@router.post("")
async def subscribe(subscription: AgentSubscription) -> AgentSubscription:
    _SUBSCRIPTIONS.append(subscription)
    return subscription


@router.get("/{user_id}")
async def user_subscriptions(user_id: str) -> list[AgentSubscription]:
    return [item for item in _SUBSCRIPTIONS if item.user_id == user_id and item.active]

