from dataclasses import dataclass


@dataclass(frozen=True)
class ServiceRoute:
    name: str
    prefix: str
    tags: tuple[str, ...]


GATEWAY_ROUTES: tuple[ServiceRoute, ...] = (
    ServiceRoute("auth", "/api/auth", ("auth",)),
    ServiceRoute("profile", "/api/profile", ("profile",)),
    ServiceRoute("health", "/api", ("health",)),
    ServiceRoute("integrations", "/integrations", ("external-integrations",)),
    ServiceRoute("orchestrator", "/orchestrator", ("api-orchestrator",)),
    ServiceRoute("marketplace", "/marketplace", ("marketplace",)),
    ServiceRoute("nudges", "/nudges", ("nudges",)),
    ServiceRoute("personalization", "/personalization", ("personalization",)),
    ServiceRoute("portfolio", "/portfolio", ("portfolio-risk",)),
    ServiceRoute("execution", "/execution", ("execution",)),
    ServiceRoute("backtest", "/backtest", ("backtest",)),
    ServiceRoute("signals", "/signals", ("signals",)),
    ServiceRoute("partner_api", "/api/partner", ("partner-api",)),
    ServiceRoute("stress_test", "/stress-test", ("stress-test",)),
    ServiceRoute("safety", "/safety", ("safety",)),
    ServiceRoute("tax", "/portfolio/tax", ("tax",)),
    ServiceRoute("trader_os", "/trader-os", ("trader-operating-system",)),
    ServiceRoute("workstation", "/workstation", ("professional-trading-workstation",)),
    ServiceRoute("brokerage_ops", "/brokerage-ops", ("brokerage-operations", "client-experience")),
    ServiceRoute("one_stop", "/one-stop", ("one-stop-trading-platform",)),
    ServiceRoute("freshness", "/signals/freshness", ("signal-freshness",)),
    ServiceRoute("explain", "/explain", ("explainability",)),
    ServiceRoute("paper", "/paper", ("paper-trading",)),
    ServiceRoute("trading", "/trading", ("trading",)),
    ServiceRoute("alerts", "/alerts", ("alerts",)),
    ServiceRoute("validation", "/validation", ("model-validation",)),
    ServiceRoute("compliance", "/compliance", ("compliance-security-audit",)),
    ServiceRoute("reliability", "/reliability", ("scalability-reliability",)),
)


SERVICE_GRAPH: dict[str, tuple[str, ...]] = {
    "api_gateway": (
        "auth",
        "portfolio",
        "execution",
        "signal_orchestrator",
        "api_orchestrator",
        "backtest",
        "marketplace",
        "personalization",
        "brokerage_ops",
        "one_stop",
        "redis_streams_event_bus",
        "safety",
    ),
    "signal_orchestrator": (
        "fundamentals_agent",
        "technical_agent",
        "news_sentiment_agent",
        "macro_agent",
        "bull_bear_debate_agent",
        "trader_risk_agent",
        "redis_cache",
        "data_lake_postgresql",
    ),
    "execution": ("external_broker_apis",),
    "backtest": ("data_lake_postgresql",),
    "marketplace": ("data_lake_postgresql", "redis_streams_event_bus"),
    "personalization": ("data_lake_postgresql", "redis_streams_event_bus"),
    "brokerage_ops": ("portfolio", "execution", "external_broker_apis", "data_lake_postgresql"),
    "one_stop": ("brokerage_ops", "marketplace", "notification_service", "external_market_data_apis", "data_lake_postgresql"),
    "api_orchestrator": ("external_market_data_apis", "redis_streams_event_bus"),
    "ml_pipeline": ("data_lake_postgresql",),
    "monitoring_logging": ("data_lake_postgresql",),
}


EVENT_DRIVEN_SERVICE_GRAPH: dict[str, tuple[str, ...]] = {
    "api_gateway": (
        "commands.signal",
        "commands.external_api",
        "commands.execution",
        "commands.portfolio",
        "commands.backtest",
        "commands.marketplace",
        "commands.personalization",
    ),
    "redis_streams_event_bus": (
        "signal_worker",
        "external_api_worker",
        "execution_worker",
        "portfolio_worker",
        "backtest_worker",
        "marketplace_worker",
        "personalization_worker",
    ),
    "event_workers": (
        "events.signal",
        "events.external_api",
        "events.execution",
        "events.portfolio",
        "events.backtest",
        "events.marketplace",
        "events.personalization",
    ),
}
