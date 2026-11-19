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

## Portfolio Advisor Narrative

The Portfolio Advisor's calculated summaries work without an LLM. Optional written narratives use the OpenAI Agents SDK with its LiteLLM adapter to call Amazon Bedrock. The feature is disabled unless `PORTFOLIO_ADVISOR_LLM_ENABLED=true`; configure `PORTFOLIO_ADVISOR_BEDROCK_MODEL_ID` and `PORTFOLIO_ADVISOR_BEDROCK_REGION`, and grant the worker's AWS role permission to invoke the selected Bedrock model. LiteLLM uses the standard AWS credential chain and `AWS_REGION_NAME` for the configured region.

Users must separately enable “Allow this service to send the analysis snapshot to Amazon Bedrock” in Portfolio Advisor. The worker rechecks persisted `portfolio_advisor_llm` consent immediately before inference and blocks processing after revocation or a pending deletion request. The model receives aggregate statistics, top holdings, source dates/providers, factor exposures, and data warnings; it does not receive user identity, email, portfolio IDs, or retirement assumptions. Agents SDK tracing is disabled for this run because default tracing can export prompts and responses outside the configured Bedrock account. The report agent has no broker, execution, or order tools.

The Alex Researcher MCP service is opt-in locally: set `PORTFOLIO_ADVISOR_LLM_ENABLED=true`, `PORTFOLIO_ADVISOR_RESEARCH_ENABLED=true`, a private `RESEARCHER_API_KEY`, and a Bedrock-enabled AWS profile, then start Compose with `docker compose --profile research up --build`. The gateway worker calls `http://researcher-agent:8000` on the private Compose network. The researcher is called with `ingest=false`; its validated cited brief is written to the platform's `one_stop_research_snapshots` table. Do not expose the researcher container port publicly. Production deployments must provide a private service URL, secret-managed API key, Chromium/Playwright runtime, Bedrock model access, and reviewed network controls. The standalone Alex Terraform module's public unauthenticated Lambda Function URL is not used by this integration.
