# Chart Enrichment Verification Report

Date: June 3, 2026

Status: implemented with executable release gates.

## Local Gates

Run from the repository root:

```powershell
npm --prefix frontend run test
npm --prefix frontend run test:validate
npm --prefix frontend run build
```

`npm --prefix frontend run test:validate` produces JSON release evidence in `frontend/release-evidence/`:

- `accessibility-report.json`
- `performance-report.json`
- `data-report.json`
- `visual-report.json`
- `smoke-report.json`
- `chart-release-evidence.json`

## Coverage

- V1 unit/source verification: `scripts/test-chart-tasks.mjs`
- V2 integration/source verification: chart parent components and API wiring checks
- V3 visual baseline: responsive CSS and chart layout checks
- V4 accessibility: contrast, ARIA, hidden data tables, error fallback checks
- V5 performance: production bundle budgets, cleanup, debounced resize, no random fallback checks
- V6 data validation: formatter execution and API-shape checks

## Release Automation

CI runs `npm run test:validate` in the frontend job and uploads `frontend/release-evidence/*.json`.

The deploy workflow runs the same frontend release gate before Terraform planning and uploads the chart evidence with the release candidate artifacts.

Runtime monitoring is implemented in `src/utils/charts/monitoring.js`:

- chart render errors are recorded under `chart-render-errors`
- chart render timings are recorded under `chart-performance-samples`
- chart feedback is recorded under `chart-feedback`
- records are stored locally and sent with `navigator.sendBeacon('/chart-monitoring', ...)` when available

## Notes

The repository now implements the checklist as code and workflow gates. External staging or production execution still depends on running the configured GitHub Actions workflow against the target environment.
