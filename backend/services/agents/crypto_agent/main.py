from fastapi import FastAPI

from backend.services.agents.crypto_agent.defi_metrics import get_defi_metrics
from backend.services.agents.crypto_agent.exchange_flow import analyze_exchange_flow
from backend.services.agents.crypto_agent.on_chain import analyze_on_chain
from backend.shared.observability import instrument_app

app = FastAPI(title="Crypto Agent", version="0.1.0")
instrument_app(app, "crypto_agent", {"on_chain_data": "configured"})


@app.get("/health")
async def health() -> dict[str, str]:
    return {"service": "crypto_agent", "status": "healthy"}


@app.get("/analyze/{asset}")
async def analyze(asset: str) -> dict[str, object]:
    return {
        "asset": asset.upper(),
        "asset_type": "crypto",
        "on_chain": analyze_on_chain(asset),
        "defi": get_defi_metrics(asset),
        "exchange_flow": analyze_exchange_flow(asset),
    }
