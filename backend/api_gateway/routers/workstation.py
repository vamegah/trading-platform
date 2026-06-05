from fastapi import APIRouter

from backend.services.workstation_service import (
    approve_staged_order,
    basket_workbench,
    borrow_desk,
    cancel_all_orders,
    data_quality_dashboard,
    deploy_strategy,
    disclosure_archive,
    emergency_stage_decision,
    emergency_status,
    execution_and_quality_evidence,
    market_microstructure,
    pause_trading,
    portfolio_construction,
    pre_trade_control,
    preview_basket,
    release_staged_order,
    request_locate,
    risk_constitution,
    stage_order,
    strategy_research,
    submit_basket,
    tax_lot_decision,
    trade_staging,
    update_risk_constitution,
    evaluate_risk_constitution,
    workstation_overview,
)

router = APIRouter()


@router.get("/overview")
async def overview() -> dict[str, object]:
    return workstation_overview()


@router.get("/basket")
async def basket() -> dict[str, object]:
    return basket_workbench()


@router.post("/basket/preview")
async def basket_preview(payload: dict) -> dict[str, object]:
    return preview_basket(payload)


@router.post("/basket/submit")
async def basket_submit(payload: dict) -> dict[str, object]:
    return submit_basket(payload)


@router.post("/pre-trade/check")
async def pre_trade(payload: dict) -> dict[str, object]:
    return pre_trade_control(payload)


@router.get("/tax-lots/{symbol}")
async def tax_lots(symbol: str) -> dict[str, object]:
    return tax_lot_decision(symbol)


@router.post("/tax-lots/{symbol}/decision")
async def tax_lot_decision_for_order(symbol: str, payload: dict) -> dict[str, object]:
    return tax_lot_decision(symbol, payload)


@router.get("/borrow/{symbol}")
async def borrow(symbol: str) -> dict[str, object]:
    return borrow_desk(symbol)


@router.post("/borrow/locate")
async def locate(payload: dict) -> dict[str, object]:
    return request_locate(payload)


@router.post("/portfolio-lab/construct")
async def construct_portfolio(payload: dict) -> dict[str, object]:
    return portfolio_construction(payload)


@router.get("/microstructure/{symbol}")
async def microstructure(symbol: str, quantity: float | None = None) -> dict[str, object]:
    return market_microstructure(symbol, {"quantity": quantity} if quantity else None)


@router.get("/staging")
async def staging() -> dict[str, object]:
    return trade_staging()


@router.post("/staging/orders")
async def create_stage(payload: dict) -> dict[str, object]:
    return stage_order(payload)


@router.post("/staging/{stage_id}/approve")
async def approve_stage(stage_id: str, payload: dict | None = None) -> dict[str, object]:
    return approve_staged_order(stage_id, payload)


@router.post("/staging/{stage_id}/release")
async def release_stage(stage_id: str, payload: dict | None = None) -> dict[str, object]:
    return release_staged_order(stage_id, payload)


@router.get("/data-quality")
async def data_quality() -> dict[str, object]:
    return data_quality_dashboard()


@router.post("/strategy/research")
async def research_strategy(payload: dict) -> dict[str, object]:
    return strategy_research(payload)


@router.post("/strategy/deploy")
async def deploy(payload: dict) -> dict[str, object]:
    return deploy_strategy(payload)


@router.get("/risk-constitution")
async def get_risk_constitution() -> dict[str, object]:
    return risk_constitution()


@router.post("/risk-constitution")
async def save_risk_constitution_rule(payload: dict) -> dict[str, object]:
    return update_risk_constitution(payload)


@router.post("/risk-constitution/evaluate")
async def evaluate_risk_rule(payload: dict) -> dict[str, object]:
    return evaluate_risk_constitution(payload)


@router.get("/disclosure-archive")
async def archive(query: str | None = None) -> dict[str, object]:
    return disclosure_archive(query)


@router.get("/emergency")
async def emergency() -> dict[str, object]:
    return emergency_status()


@router.post("/emergency/pause")
async def pause(payload: dict | None = None) -> dict[str, object]:
    return pause_trading(payload)


@router.post("/emergency/cancel-all")
async def cancel_all(payload: dict | None = None) -> dict[str, object]:
    return cancel_all_orders(payload)


@router.post("/emergency/staged/{stage_id}/decision")
async def staged_decision(stage_id: str, payload: dict) -> dict[str, object]:
    return emergency_stage_decision(stage_id, payload)


@router.get("/execution-evidence")
async def execution_evidence() -> dict[str, object]:
    return execution_and_quality_evidence()
