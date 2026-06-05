# Trading Platform

AI-assisted trading platform scaffold with a FastAPI gateway, agent-oriented Python services, data and ML pipelines, a React dashboard, and deployment placeholders.

## Layout

- `backend/api_gateway`: public FastAPI gateway for auth, signals, portfolio, and backtests.
- `backend/services`: domain microservices and independent AI agents.
- `backend/data_pipeline`: ingestion, quality, raw lake, and feature store modules.
- `backend/ml_training`: model stubs and champion/challenger selection.
- `frontend`: Vite React workspace dashboard.
- `infrastructure`: Docker, Kubernetes, and Terraform starter files.
- `config`: environment-specific configuration examples.

## Local Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd frontend
npm install
```

## Database Migrations

The project uses SQLAlchemy models with Alembic for schema migration.

```bash
alembic revision --autogenerate -m "describe change"
python scripts/migrate_db.py
```

For local scaffold-only runs, `CREATE_TABLES_ON_STARTUP=true` can create tables automatically. Production and staging should use migrations only.

## Service Probes

Core FastAPI services expose:

- `/health` for liveness
- `/ready` for dependency readiness
- `/metrics` for lightweight request counters and latency snapshots

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cd frontend
npm install
```

## Run Locally

```bash
uvicorn backend.api_gateway.main:app --reload --host 0.0.0.0 --port 8000
```

```bash
cd frontend
npm run dev
```

The API gateway listens on `http://localhost:8000` and the frontend uses `http://localhost:5173` by default.

## Docker

```bash
docker compose up --build
```

The Docker setup exposes the API gateway on `8000`, the frontend on `3000`, Redis on `6379`, and sample agent services on `8010` and `8011`.

## Next Steps

- Replace stub broker, market data, and ML implementations with real providers.
- Add database migrations and production-grade auth.
- Expand tests around orchestration, execution safety, and backtest assumptions.
- Wire `deploy.yml` to your chosen cloud target.

## Compliance Boundary

The platform separates research, paper trading, one-click execution, and automated live trading. Automated trading is gated by suitability, explicit consent, risk limits, stale-signal checks, kill-switch state, and broker capability validation. See [docs/compliance.md](docs/compliance.md) for regulatory limitations, privacy controls, auditability expectations, and live-trading readiness requirements.

Operational incident response, manual trading pause, provider outage, data corruption, model rollback, key rotation, disaster recovery, and customer communication procedures are defined in [docs/operations_runbook.md](docs/operations_runbook.md).

Authentication, token, RBAC, service-account, MFA, and production identity-provider requirements are defined in [docs/auth_hardening.md](docs/auth_hardening.md).

Release-candidate gates and required evidence are tracked in [docs/release_candidate.md](docs/release_candidate.md).

Provider credential, SLA, failover, and certification requirements are tracked in [docs/provider_integrations.md](docs/provider_integrations.md).

Broker paper/live certification requirements are tracked in [docs/broker_certification.md](docs/broker_certification.md).

Model validation, calibration, drift, explainability, and promotion requirements are tracked in [docs/model_validation.md](docs/model_validation.md).

Production signoff evidence is collected and validated through the manifest described in [docs/evidence_manifest.md](docs/evidence_manifest.md).
