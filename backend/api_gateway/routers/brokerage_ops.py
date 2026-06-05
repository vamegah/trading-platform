from fastapi import APIRouter

from backend.services.brokerage_ops_service import (
    account_document,
    account_documents_center,
    admin_console,
    brokerage_ops_overview,
    cash_settlement_center,
    chart_trading_workspace,
    check_market_data_entitlement,
    corporate_actions_center,
    create_admin_override,
    create_cash_transfer,
    create_conditional_order,
    create_recurring_plan,
    create_support_case,
    entitlements_dashboard,
    evaluate_surveillance,
    generate_portfolio_review_pack,
    mobile_companion,
    mobile_emergency_pause,
    preview_chart_order,
    record_corporate_action_election,
    recurring_investments,
    simulate_conditional_order,
    support_center,
    surveillance_dashboard,
)

router = APIRouter()


@router.get("/overview")
async def overview() -> dict[str, object]:
    return brokerage_ops_overview()


@router.get("/cash-settlement")
async def cash_settlement() -> dict[str, object]:
    return cash_settlement_center()


@router.post("/cash-settlement/transfers")
async def cash_transfer(payload: dict) -> dict[str, object]:
    return create_cash_transfer(payload)


@router.get("/chart-trading/{symbol}")
async def chart_trading(symbol: str) -> dict[str, object]:
    return chart_trading_workspace(symbol)


@router.post("/chart-trading/order-preview")
async def chart_order_preview(payload: dict) -> dict[str, object]:
    return preview_chart_order(payload)


@router.get("/corporate-actions")
async def corporate_actions() -> dict[str, object]:
    return corporate_actions_center()


@router.post("/corporate-actions/{action_id}/election")
async def corporate_action_election(action_id: str, payload: dict) -> dict[str, object]:
    return record_corporate_action_election(action_id, payload)


@router.get("/account-documents")
async def account_documents() -> dict[str, object]:
    return account_documents_center()


@router.get("/account-documents/{document_id}")
async def account_document_preview(document_id: str) -> dict[str, object]:
    return account_document(document_id)


@router.get("/admin")
async def admin() -> dict[str, object]:
    return admin_console()


@router.post("/admin/overrides")
async def admin_override(payload: dict) -> dict[str, object]:
    return create_admin_override(payload)


@router.get("/surveillance")
async def surveillance() -> dict[str, object]:
    return surveillance_dashboard()


@router.post("/surveillance/evaluate")
async def surveillance_evaluate(payload: dict) -> dict[str, object]:
    return evaluate_surveillance(payload)


@router.get("/entitlements")
async def entitlements() -> dict[str, object]:
    return entitlements_dashboard()


@router.post("/entitlements/check")
async def entitlement_check(payload: dict) -> dict[str, object]:
    return check_market_data_entitlement(payload)


@router.get("/recurring-investments")
async def recurring() -> dict[str, object]:
    return recurring_investments()


@router.post("/recurring-investments")
async def recurring_plan(payload: dict) -> dict[str, object]:
    return create_recurring_plan(payload)


@router.post("/conditional-orders/simulate")
async def conditional_order_simulation(payload: dict) -> dict[str, object]:
    return simulate_conditional_order(payload)


@router.post("/conditional-orders")
async def conditional_order(payload: dict) -> dict[str, object]:
    return create_conditional_order(payload)


@router.post("/reports/portfolio-review")
async def portfolio_review(payload: dict | None = None) -> dict[str, object]:
    return generate_portfolio_review_pack(payload or {})


@router.get("/mobile")
async def mobile() -> dict[str, object]:
    return mobile_companion()


@router.post("/mobile/emergency-pause")
async def emergency_pause(payload: dict | None = None) -> dict[str, object]:
    return mobile_emergency_pause(payload)


@router.get("/support")
async def support() -> dict[str, object]:
    return support_center()


@router.post("/support/cases")
async def support_case(payload: dict) -> dict[str, object]:
    return create_support_case(payload)
