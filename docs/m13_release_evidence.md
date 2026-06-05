# Milestone 13 Release Evidence

Milestone 13 adds sandbox-first brokerage operations and client experience workflows behind fail-closed gates.

Implemented evidence:

- Brokerage operations schema models and migration `0004_brokerage_operations`.
- `/brokerage-ops` API surface for overview, cash settlement, chart trading, corporate actions, account documents, admin review, surveillance, entitlements, recurring investment, conditional orders, portfolio reports, mobile controls, and support cases.
- Named service owner modules for cash settlement, corporate actions, account documents, admin review, surveillance, entitlements, investment plans, conditional orders, reporting, and support.
- Frontend `Operations` workspace with clickable workflow actions for each M13 capability.
- Integration tests in `backend/tests/integration/test_m13_brokerage_operations.py`.

Live gates:

- Live cash movement remains blocked without M10 live-trading evidence and approved bank integration evidence.
- Chart order release requires explicit confirmation and pre-trade approval.
- Market data access fails closed when entitlements are missing.
- Conditional orders are simulated before being armed.
- Admin overrides require confirmation, reason, and audit linkage.
- Mobile emergency actions record audit IDs and push-ready status.

Primary verification command:

```bash
pytest backend/tests/integration/test_m13_brokerage_operations.py
```
