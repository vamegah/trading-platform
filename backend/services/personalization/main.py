from fastapi import FastAPI

from backend.services.personalization.event_tracker import track_event
from backend.services.personalization.persona_engine import build_persona
from backend.services.personalization.routers import preferences
from backend.shared.observability import instrument_app

app = FastAPI(title="Personalization Service", version="0.1.0")
instrument_app(app, "personalization", {"database": "configured", "redis": "optional"})
app.include_router(preferences.router, prefix="/preferences", tags=["preferences"])


@app.get("/health")
async def health() -> dict[str, str]:
    return {"service": "personalization", "status": "healthy"}


@app.post("/events")
async def events(event: dict) -> dict[str, object]:
    return track_event(event)


@app.get("/persona/{user_id}")
async def persona(user_id: str) -> dict[str, object]:
    return build_persona(user_id)
