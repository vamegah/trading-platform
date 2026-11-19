from . import (
    brokers,
    dr_drill,
    infrastructure,
    legal,
    load_soak,
    models,
    paper_trading,
    persistent_controls,
    providers,
    security,
)

__all__ = [
    "provider_certification",
    "broker_certification",
    "model_validation",
    "persistent_controls_restore",
    "cloud_infrastructure_plan",
    "load_soak_test",
    "security_assessment",
    "dr_outage_drill",
    "legal_compliance_review",
    "paper_trading_validation",
]

# Map manifest category names to modules
provider_certification = providers
broker_certification = brokers
model_validation = models
persistent_controls_restore = persistent_controls
cloud_infrastructure_plan = infrastructure
load_soak_test = load_soak
security_assessment = security
dr_outage_drill = dr_drill
legal_compliance_review = legal
paper_trading_validation = paper_trading