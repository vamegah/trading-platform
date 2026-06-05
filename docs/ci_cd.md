# CI/CD

The application uses GitHub Actions for pull request checks, release candidate validation, image publication, and gated deployment.

## Continuous Integration

`.github/workflows/ci.yml` runs on pull requests and pushes to `main`.

- Backend quality: install dependencies, Ruff, pytest, compile checks, migration model import.
- Frontend quality: `npm --prefix frontend run test:validate`, production build, chart release evidence upload.
- Security gates: `pip-audit`, `npm audit`, Bandit, and a scoped `detect-secrets` baseline scan.
- Infrastructure validation: Terraform format/init/validate plus Kubernetes manifest parsing.
- Containers: Build backend and frontend images and scan both with Trivy.
- Release readiness: Produce staging readiness and M9 implementation review artifacts.

## Continuous Deployment

`.github/workflows/deploy.yml` is manually dispatched for `staging` or `production`.

The deploy workflow:

- Re-runs backend, frontend, and release-candidate checks.
- Blocks production through `scripts/go_live_gate.py` when live-trading evidence is missing.
- Builds and pushes backend/frontend images to GHCR.
- Generates release evidence and changelog artifacts.
- Runs Terraform plan on every deployment.
- Applies Terraform only when `apply_infrastructure` is explicitly enabled.
- Applies Kubernetes manifests only when `deploy_kubernetes` is explicitly enabled.
- Runs `scripts/smoke_test.py` when `SMOKE_TEST_BASE_URL` is configured.
- Prints the rollback checklist automatically on failed production deploys.

## Required Repository Settings

Configure GitHub Environments named `staging` and `production`. Production should require reviewer approval.

Recommended variables:

- `SMOKE_TEST_BASE_URL`
- `VITE_API_BASE_URL`
- `AWS_ACCOUNT_ID`
- `RELEASE_EVIDENCE_MANIFEST`

Recommended secrets:

- `TF_DATABASE_PASSWORD`
- `KUBE_CONFIG_B64`

## External Evidence Boundary

M10 vendor, broker, legal, security-assessment, load/soak, and final go-live evidence is intentionally not fabricated in CI. Those artifacts are accepted through the evidence manifest and enforced by the deploy workflow before production live trading.
