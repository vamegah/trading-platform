from dataclasses import dataclass


@dataclass(frozen=True)
class Topics:
    signal_commands: str = "commands.signal"
    signal_events: str = "events.signal"
    external_api_commands: str = "commands.external_api"
    external_api_events: str = "events.external_api"
    execution_commands: str = "commands.execution"
    execution_events: str = "events.execution"
    portfolio_commands: str = "commands.portfolio"
    portfolio_events: str = "events.portfolio"
    backtest_commands: str = "commands.backtest"
    backtest_events: str = "events.backtest"
    marketplace_commands: str = "commands.marketplace"
    marketplace_events: str = "events.marketplace"
    personalization_commands: str = "commands.personalization"
    personalization_events: str = "events.personalization"
    audit_events: str = "events.audit"


@dataclass(frozen=True)
class EventTypes:
    signal_evaluate_requested: str = "signal.evaluate.requested"
    signal_generated: str = "signal.generated"
    signal_failed: str = "signal.failed"
    quote_requested: str = "external_api.quote.requested"
    quote_received: str = "external_api.quote.received"
    news_requested: str = "external_api.news.requested"
    news_received: str = "external_api.news.received"
    order_route_requested: str = "order.route.requested"
    order_routed: str = "order.routed"
    order_rejected: str = "order.rejected"
    portfolio_risk_requested: str = "portfolio.risk.requested"
    portfolio_risk_evaluated: str = "portfolio.risk.evaluated"
    backtest_walk_forward_requested: str = "backtest.walk_forward.requested"
    backtest_completed: str = "backtest.completed"
    marketplace_agent_publish_requested: str = "marketplace.agent.publish.requested"
    marketplace_agent_published: str = "marketplace.agent.published"
    marketplace_subscription_requested: str = "marketplace.subscription.requested"
    marketplace_subscription_created: str = "marketplace.subscription.created"
    personalization_event_track_requested: str = "personalization.event.track.requested"
    personalization_event_tracked: str = "personalization.event.tracked"
    personalization_persona_requested: str = "personalization.persona.requested"
    personalization_persona_built: str = "personalization.persona.built"
    command_failed: str = "command.failed"


TOPICS = Topics()
EVENT_TYPES = EventTypes()

CORE_EVENT_TOPOLOGY = {
    "api_gateway": {
        "publishes": (
            TOPICS.signal_commands,
            TOPICS.external_api_commands,
            TOPICS.execution_commands,
            TOPICS.portfolio_commands,
            TOPICS.backtest_commands,
            TOPICS.marketplace_commands,
            TOPICS.personalization_commands,
        ),
        "subscribes": (),
    },
    "external_api_orchestrator": {
        "publishes": (TOPICS.external_api_events,),
        "subscribes": (TOPICS.external_api_commands,),
    },
    "signal_orchestrator": {
        "publishes": (TOPICS.signal_events,),
        "subscribes": (TOPICS.signal_commands,),
    },
    "execution_service": {
        "publishes": (TOPICS.execution_events,),
        "subscribes": (TOPICS.execution_commands,),
    },
    "portfolio_service": {
        "publishes": (TOPICS.portfolio_events,),
        "subscribes": (TOPICS.portfolio_commands,),
    },
    "backtest_engine": {
        "publishes": (TOPICS.backtest_events,),
        "subscribes": (TOPICS.backtest_commands,),
    },
    "marketplace_service": {
        "publishes": (TOPICS.marketplace_events,),
        "subscribes": (TOPICS.marketplace_commands,),
    },
    "personalization_engine": {
        "publishes": (TOPICS.personalization_events,),
        "subscribes": (TOPICS.personalization_commands,),
    },
}
