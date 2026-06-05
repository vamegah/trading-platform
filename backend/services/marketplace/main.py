from fastapi import FastAPI

from backend.services.marketplace.routers import agents, reviews, subscriptions
from backend.shared.observability import instrument_app

app = FastAPI(title="Agent Marketplace", version="0.1.0")
instrument_app(app, "marketplace", {"database": "configured", "redis": "optional"})
app.include_router(agents.router, prefix="/agents", tags=["marketplace-agents"])
app.include_router(subscriptions.router, prefix="/subscriptions", tags=["subscriptions"])
app.include_router(reviews.router, prefix="/reviews", tags=["reviews"])


@app.get("/health")
async def health() -> dict[str, str]:
    return {"service": "marketplace", "status": "healthy"}
