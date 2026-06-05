from fastapi import APIRouter, HTTPException

from backend.services.marketplace.models import AgentReview

router = APIRouter()

_REVIEWS: list[AgentReview] = []


@router.post("")
async def create_review(review: AgentReview) -> AgentReview:
    if not 1 <= review.rating <= 5:
        raise HTTPException(status_code=400, detail="rating must be between 1 and 5")
    _REVIEWS.append(review)
    return review


@router.get("/{agent_id}")
async def agent_reviews(agent_id: str) -> list[AgentReview]:
    return [review for review in _REVIEWS if review.agent_id == agent_id]

