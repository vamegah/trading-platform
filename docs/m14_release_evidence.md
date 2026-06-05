# Milestone 14 Release Evidence

Milestone 14 adds a sandbox-first one-stop trading platform layer across market data, research, broker connectivity, account transfers, account-type controls, analytics, alerting, automation, strategy discovery, document AI, coaching, collaboration, fee/yield transparency, trust controls, and notifications.

Implemented evidence:

- One-stop platform schema models and migration `0005_one_stop_platform`.
- `/one-stop` API surface for terminal data, research, broker connectivity, ACATS transfers, account-type rule evaluation, portfolio analytics, alert builder, automation simulation, backtest marketplace, document AI, coaching, collaboration, fee/yield, trust, and notifications.
- Named service owner modules for each M14 workstream.
- Frontend `One Stop` workspace with clickable sandbox workflows.
- Integration tests in `backend/tests/integration/test_m14_one_stop_platform.py`.

Fail-closed controls:

- Level II market data is blocked without the required entitlement.
- Live broker refresh is blocked without M10 broker evidence.
- IRA/custodial account actions block prohibited margin, short, or options activity.
- Automation remains simulation or approval-required until pre-trade and human approval gates pass.
- Public collaboration spaces are blocked in sandbox.
- Account locks require explicit confirmation.
- Unconfigured notification providers are blocked with explainable status.

Primary verification command:

```bash
pytest backend/tests/integration/test_m14_one_stop_platform.py
```
