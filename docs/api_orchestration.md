# API Orchestration Layer

The platform now routes external API access through a shared orchestration layer instead of letting domain services scatter provider calls.

## Runtime Surfaces

- Gateway routes:
  - `GET /orchestrator/quote/{symbol}`
  - `GET /orchestrator/news/{symbol}`
  - `GET /orchestrator/status`
- Dedicated service:
  - `backend.services.api_orchestrator.main:app`
  - Docker Compose port `8010`
  - Kubernetes manifest `infrastructure/k8s/api-orchestrator-deployment.yaml`

## Configuration

Provider order, timeouts, TTLs, and rate limits live in:

- `config/external_apis.yaml`
- `config/rate_limits.yaml`

Credentials are still read from environment variables and should be injected through Vault-backed Kubernetes Secrets in production.

## Controls

- `backend/shared/external_api/circuit_breaker.py` opens a per-provider circuit after repeated failures.
- `backend/shared/external_api/cost_governor.py` enforces token-bucket style rate budgets.
- `backend/shared/external_api/cache.py` provides Redis-backed stale-while-revalidate caching.
- `backend/shared/external_api/router.py` wraps calls with timeout, rate checks, circuit breaker protection, and audit logging.
- `backend/data_pipeline/ingestion/orchestrator.py` handles data-specific failover and normalization.

## Current Provider Coverage

The quote orchestration chain supports Polygon, Financial Modeling Prep, Twelve Data, and Alpha Vantage. News orchestration supports Finnhub and NewsCatcher through the existing normalized event adapters. Additional provider categories should be added by extending `config/external_apis.yaml` and registering a provider adapter behind the same router.
