from fastapi import APIRouter

from backend.services.one_stop_platform_service import (
    account_transfer_center,
    account_type_rules,
    alert_builder,
    automation_studio,
    backtest_marketplace,
    broker_connectivity_hub,
    coaching_center,
    collaboration_layer,
    compare_marketplace_strategies,
    create_acats_transfer,
    create_alert_rule,
    create_collaboration_space,
    document_ai_reader,
    evaluate_account_rule,
    fee_yield_center,
    lock_account,
    market_data_terminal,
    notification_system,
    one_stop_overview,
    portfolio_analytics_pro,
    refresh_broker_connection,
    research_lab,
    simulate_automation,
    test_alert_delivery,
    test_notification,
    trust_center,
)

router = APIRouter()


@router.get("/overview")
async def overview() -> dict[str, object]:
    return one_stop_overview()


@router.get("/terminal/{symbol}")
async def terminal(symbol: str) -> dict[str, object]:
    return market_data_terminal(symbol)


@router.get("/research/{symbol}")
async def research(symbol: str) -> dict[str, object]:
    return research_lab(symbol)


@router.post("/research/brief")
async def research_brief(payload: dict) -> dict[str, object]:
    return research_lab(payload.get("symbol", "MSFT"), payload)


@router.get("/brokers")
async def brokers() -> dict[str, object]:
    return broker_connectivity_hub()


@router.post("/brokers/refresh")
async def broker_refresh(payload: dict) -> dict[str, object]:
    return refresh_broker_connection(payload)


@router.get("/transfers")
async def transfers() -> dict[str, object]:
    return account_transfer_center()


@router.post("/transfers/acats")
async def acats_transfer(payload: dict) -> dict[str, object]:
    return create_acats_transfer(payload)


@router.get("/account-rules")
async def rules() -> dict[str, object]:
    return account_type_rules()


@router.post("/account-rules/evaluate")
async def rule_eval(payload: dict) -> dict[str, object]:
    return evaluate_account_rule(payload)


@router.get("/analytics/portfolio")
async def analytics() -> dict[str, object]:
    return portfolio_analytics_pro()


@router.get("/alerts")
async def alerts() -> dict[str, object]:
    return alert_builder()


@router.post("/alerts")
async def create_alert(payload: dict) -> dict[str, object]:
    return create_alert_rule(payload)


@router.post("/alerts/test")
async def test_alert(payload: dict) -> dict[str, object]:
    return test_alert_delivery(payload)


@router.get("/automation")
async def automation() -> dict[str, object]:
    return automation_studio()


@router.post("/automation/simulate")
async def automation_simulation(payload: dict) -> dict[str, object]:
    return simulate_automation(payload)


@router.get("/backtest-marketplace")
async def marketplace() -> dict[str, object]:
    return backtest_marketplace()


@router.post("/backtest-marketplace/compare")
async def compare_strategies(payload: dict) -> dict[str, object]:
    return compare_marketplace_strategies(payload)


@router.post("/document-ai/read")
async def document_ai(payload: dict | None = None) -> dict[str, object]:
    return document_ai_reader(payload or {})


@router.get("/coaching")
async def coaching() -> dict[str, object]:
    return coaching_center()


@router.get("/collaboration")
async def collaboration() -> dict[str, object]:
    return collaboration_layer()


@router.post("/collaboration/spaces")
async def collaboration_space(payload: dict) -> dict[str, object]:
    return create_collaboration_space(payload)


@router.get("/fees-yield")
async def fees_yield() -> dict[str, object]:
    return fee_yield_center()


@router.get("/trust")
async def trust() -> dict[str, object]:
    return trust_center()


@router.post("/trust/lock")
async def trust_lock(payload: dict) -> dict[str, object]:
    return lock_account(payload)


@router.get("/notifications")
async def notifications() -> dict[str, object]:
    return notification_system()


@router.post("/notifications/test")
async def notification_test(payload: dict) -> dict[str, object]:
    return test_notification(payload)
