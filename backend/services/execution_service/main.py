from fastapi import FastAPI

from backend.services.execution_service.order_router import AlmgrenChrissImpactModel, route_order
from backend.shared.models import OrderRequest
from backend.shared.observability import RequestContextMiddleware, add_observability_routes

app = FastAPI(title="Execution Service", version="0.1.0")
app.add_middleware(RequestContextMiddleware)
add_observability_routes(app, "execution_service", {"brokers": "configured"})


@app.get("/health")
async def health() -> dict[str, str]:
    return {"service": "execution_service", "status": "healthy"}


@app.post("/orders")
async def orders(order: OrderRequest) -> dict[str, str | float]:
    return route_order(order)


@app.post("/impact")
async def impact(order: OrderRequest, current_price: float = 100.0) -> dict[str, float]:
    return AlmgrenChrissImpactModel().estimate(
        symbol=order.symbol,
        order_size=order.quantity,
        side=order.side,
        current_price=current_price,
    ).__dict__
