from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api_gateway.middleware.audit_log import AuditLogMiddleware
from backend.api_gateway.middleware.identity_propagation import IdentityPropagationMiddleware
from backend.api_gateway.middleware.rate_limit import RateLimitMiddleware
from backend.api_gateway.routers import (
    alerts,
    auth,
    backtest,
    brokerage_ops,
    compliance,
    execution,
    explain,
    freshness,
    health,
    integrations,
    marketplace,
    nudges,
    one_stop,
    orchestrator,
    paper,
    partner_api,
    personalization,
    portfolio,
    profile,
    reliability,
    safety,
    signals,
    stress_test,
    tax,
    trader_os,
    trading,
    validation,
    workstation,
)
from backend.shared.config import settings
from backend.shared.database import Base, engine
from backend.shared.logging_config import setup_logging
from backend.shared.observability import RequestContextMiddleware, add_observability_routes
from backend.shared.service_registry import GATEWAY_ROUTES

setup_logging()


@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    settings.validate_runtime()
    if settings.create_tables_on_startup:
        Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Trading Platform API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(IdentityPropagationMiddleware)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(AuditLogMiddleware)
add_observability_routes(app, "api_gateway", {"database": "configured", "redis": "optional"})

_ROUTER_MODULES = {
    "auth": auth,
    "profile": profile,
    "health": health,
    "integrations": integrations,
    "marketplace": marketplace,
    "nudges": nudges,
    "one_stop": one_stop,
    "orchestrator": orchestrator,
    "portfolio": portfolio,
    "personalization": personalization,
    "execution": execution,
    "backtest": backtest,
    "brokerage_ops": brokerage_ops,
    "signals": signals,
    "partner_api": partner_api,
    "stress_test": stress_test,
    "safety": safety,
    "tax": tax,
    "trader_os": trader_os,
    "workstation": workstation,
    "freshness": freshness,
    "explain": explain,
    "paper": paper,
    "trading": trading,
    "alerts": alerts,
    "validation": validation,
    "compliance": compliance,
    "reliability": reliability,
}

for route in GATEWAY_ROUTES:
    app.include_router(
        _ROUTER_MODULES[route.name].router,
        prefix=route.prefix,
        tags=list(route.tags),
    )


@app.get("/health")
async def root_health() -> dict[str, str]:
    return {"service": "api_gateway", "status": "healthy"}
