# Disaster Recovery Runbook

## Objectives

- Recovery point objective: 15 minutes.
- Recovery time objective: 60 minutes.
- Market-hours uptime target: 99.9%.

## Failover Steps

1. Freeze automated trading and cancel pending automated orders.
2. Promote the secondary database replica in the DR region.
3. Restore data lake metadata from the latest hourly backup.
4. Rehydrate Redis cache from durable event streams where available.
5. Route API gateway traffic to the secondary region.
6. Run smoke tests for auth, signal generation, execution precheck, and paper trading.
7. Resume research and paper trading first; require manual approval before live trading resumes.

## Restore Test

Restore tests must verify:

- Database schema and core tables.
- Data snapshot metadata.
- Model registry metadata.
- Audit chain continuity.
- Redis/event-bus replay behavior.
- Secret-store version restoration and KMS/Vault access.
- Cache rehydration from durable event streams.
- Gateway smoke tests in the secondary region.

The scaffold exposes `/reliability/dr` with the current DR assumptions and restore-test status.

## Evidence Requirements

Each drill must record a `drill_id`, restore evidence ID, RTO/RPO measurements, validated assets, and the operator or automation run that executed each step. Live trading remains disabled after failover until data reconciliation, risk approval, and compliance approval are complete.
