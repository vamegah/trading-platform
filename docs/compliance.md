# Compliance, Security, and Trading Controls

This platform is a research and execution workflow scaffold. It is not a registered investment adviser, broker-dealer, or legal compliance system.

## Operating Modes

- Research mode: users can inspect signals, explanations, risks, backtests, and paper-trading results.
- Paper trading mode: simulated orders use the production order router and safety checks, but no real capital is deployed.
- One-click live mode: a user must complete suitability checks and explicitly approve each order.
- Automated live mode: requires suitability completion, automation consent, stale-signal checks, risk limits, kill-switch checks, and broker capability validation.

## Required Controls Before Live Trading

- Legal review of recommendations, disclosures, and jurisdiction-specific requirements.
- Broker API credential review and rotation policy.
- Validation of suitability questionnaire scoring and restricted strategies.
- Audit trail retention policy and incident response plan.
- Paper trading validation using production-equivalent routing.
- Signed one-click, automated, and live-trading acknowledgements before any order can reach a live broker.
- Human review of automated-trading enablement, model promotion, and high-severity risk-control changes.

## Auditability

Every recommendation must carry:

- Input data snapshot identifiers.
- Model version identifiers.
- Signal confidence, probability distribution, factor exposure, tail risk, and freshness.
- Tamper-evident audit event linkage for regulated actions.

## Privacy

User privacy controls support consent capture, export, and deletion request workflows. Production deployments must connect these workflows to persistent storage and legal retention rules for GDPR/CCPA handling.

Deletion requests are tracked and queued for identity and retention review. Audit records, legal evidence, and security logs may be retained where regulatory obligations require it; export payloads expose hashed identifiers rather than plaintext personal data.

## Regulatory Limitations

The platform must not be marketed as personalized legal, tax, investment-advisory, broker-dealer, or fiduciary service without separate counsel approval and the required registrations. Live launch remains blocked until provider certification, broker certification, model validation, security assessment, privacy review, and legal/compliance approval evidence are accepted.
