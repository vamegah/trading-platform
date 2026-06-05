from fastapi import FastAPI

from backend.services.white_label.routers import billing, management, partner_api
from backend.shared.observability import instrument_app

app = FastAPI(title="White Label Service", version="0.1.0")
instrument_app(app, "white_label", {"database": "configured"})
app.include_router(partner_api.router, prefix="/partner-api", tags=["partner-api"])
app.include_router(management.router, prefix="/management", tags=["partner-management"])
app.include_router(billing.router, prefix="/billing", tags=["partner-billing"])


@app.get("/health")
async def health() -> dict[str, str]:
    return {"service": "white_label", "status": "healthy"}
