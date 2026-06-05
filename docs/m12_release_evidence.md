# Milestone 12 Release Evidence

Date: 2026-06-04

Scope: Milestone 12 Professional Trading Workstation Expansion is implemented in paper/sandbox mode. Live trading remains gated by Milestone 10 evidence, broker certifications, data-provider certifications, legal/compliance approval, suitability controls, disclosure controls, kill switches, and the go-live process.

## Implemented Surfaces

- Basket Trading and Rebalance Workbench for target weights, drift, child-order preview, account allocation, tax/margin/exposure impact, and controlled sandbox staging.
- Pre-Trade Control Tower for suitability, buying power, margin, concentration, stale signal, liquidity, borrow availability, PDT/day-trading treatment, kill switches, market-access controls, duplicate-order checks, and explainable fail-closed blocks.
- Tax and Lot Decision Center with lots, holding periods, cost basis, wash-sale risk, after-tax estimate, disposal-method comparison, and best-lot-to-sell rationale.
- Short Selling and Borrow Desk with short eligibility, locate status, hard-to-borrow flags, borrow fee, recall risk, short-sale restrictions, dividend liability, squeeze risk, and locate workflow.
- Portfolio Construction Lab, Market Microstructure Console, Institutional Trade Staging, Data Quality and Source Confidence Dashboard, Strategy Research Workbench, User Risk Constitution, Communications and Disclosure Archive, and Mobile Emergency Controls.

## Validation

| Check | Result |
| --- | --- |
| `python -m compileall backend migrations\versions\0003_professional_workstation.py` | Passed |
| `DATABASE_URL=sqlite:///C:/trading-platform/m12-alembic-temp.db alembic upgrade head` | Passed |
| `DATABASE_URL=sqlite:///C:/trading-platform/m12-alembic-temp.db alembic downgrade 0002_trader_operating_system` | Passed |
| `pytest -q backend\tests\integration\test_m12_professional_workstation.py` | Passed: 5 tests |
| `npm.cmd --prefix frontend run build` | Passed |
| `GET http://127.0.0.1:8000/workstation/overview` | 200 |
| `POST http://127.0.0.1:8000/workstation/pre-trade/check` | 200 |
| `GET http://127.0.0.1:8000/workstation/emergency` | 200 |

## Live Trading Boundary

M12 workflows intentionally run in sandbox mode. Basket, staged, short-sale, strategy, and emergency actions must pass explicit confirmation plus suitability, disclosure, stale-signal, liquidity, margin, concentration, borrow, market-access, audit, and kill-switch controls before any live-capital release can be considered. Production live trading remains disabled until M10 evidence is accepted.
