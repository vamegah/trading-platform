# Implementation Plan: AI Trading Platform Frontend Chart Enrichment

## Overview

This plan adds financial charts to six existing dashboard components using `@tradingview/lightweight-charts`, plus custom SVG bar charts. The language is JavaScript (React 19, Vite 7), matching the existing frontend and `design.md`. No backend changes are needed; data comes from `frontend/src/services/api.js`.

Current repo state (read before starting):
- The library is installed (`frontend/package.json` aliases `@tradingview/lightweight-charts` to `lightweight-charts@^5.2.0`). A previous implementation lives under `frontend/src/components/Charts/` (`ChartContainer.jsx`, `AgentScoreChart.jsx`, `ChartErrorBoundary.jsx`), `frontend/src/hooks/useChartSeries.js`, `frontend/src/utils/charts/theme.js`, and `*Enhanced.jsx` variants of each target component.
- `design.md` specifies different paths (`ChartContainer/index.js`, `AgentScoreChart/index.js`, `ChartErrorBoundary/index.js`, `styles/chart-theme.js`, `StressTest/StressBarChart.js`, `DiscoveryScanner/ConfidenceBar.js`). The tasks below create or migrate code to the design paths and wire each target component's `index.js` to them. Reuse logic from the existing files where it fits, and update or remove the old files once nothing imports them.
- Note that lightweight-charts v5 replaced `addCandlestickSeries()` and similar methods with `addSeries(CandlestickSeries, opts)` and moved markers to `createSeriesMarkers`. Use the API that matches the installed version.

Delivery workflow (Requirement 11, design.md "Delivery Workflow"): every implementation unit of work is delivered on its own new branch cut from an up-to-date `main`. A unit of work is one task, or the group of tasks in one dependency-graph wave that the executor chooses to deliver together. For each unit:
- Fetch, update local `main` to match `origin/main`, and create the branch (`<type>/<task-ids>-<desc>`).
- Push the branch and open one PR to `main`.
- All GitHub Actions PR workflows must pass. Failures are fixed with new commits on the branch, with no force push, no `--no-verify`, and no disabled hooks or relaxed required checks. After 3 consecutive failures of the same check, stop, leave the PR open, and report the check name and failure output.
- Merge conflicts are resolved on the branch, keeping every change already on `main` from other contributors.
- Merge to `main` only when every check is green and there are no conflicts, then update local `main`.
- Monitor every workflow triggered on `main` until it finishes. A failing main workflow is fixed through a new unit of work.
- Each group's delivery task (2.7, 4.8, 5.3) starts only after the previous group's delivery has merged, so later groups branch from the updated `main`.

## Tasks

- [x] 1. Charting library installation
  - [x] 1.1 Declare `@tradingview/lightweight-charts` in `frontend/package.json`
    - Already present as an npm alias to `lightweight-charts@^5.2.0`. Confirm no other charting library (Chart.js, Recharts, D3) is a dependency.
    - _Requirements: 1.1, 1.2, 1.3_

- [x] 2. Shared chart foundation
  - [x] 2.1 Create `frontend/src/styles/chart-theme.js`
    - Export `CHART_THEME` (background `#0d0d0d`, text, grid, border, green, red, amber, grey, orange, neutral) and `CHART_OPTIONS` (layout, grid, timeScale) as in design.md.
    - Each semantic color must have at least 3:1 contrast against `#0d0d0d`.
    - Make `frontend/src/utils/charts/theme.js` re-export from this file, or update its importers, so colors are defined once.
    - _Requirements: 10.1, 10.2_

  - [x] 2.2 Create `frontend/src/components/ChartContainer/index.js` and `ChartContainer.css`
    - Default export `ChartContainer({ height = 260, width, options, ariaLabel, children })`. Call `createChart()` on mount with `CHART_OPTIONS` merged with `options`, and store the instance in a ref.
    - Call `chart.remove()` and disconnect the `ResizeObserver` on unmount.
    - On parent resize, call `chart.applyOptions({ width, height })` within 100 ms.
    - Render a `<div role="img" aria-label>` and provide the chart ref through context. Prefer a CSS class over inline height styles.
    - Export the `useChartSeries()` hook, which returns the chart ref, from the same file. Keep `frontend/src/hooks/useChartSeries.js` as a re-export or remove it and update importers.
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 10.1, 10.3_

  - [x] 2.3 Create `frontend/src/components/ChartErrorBoundary/index.js`
    - Class component with `getDerivedStateFromError`, a `componentDidCatch` that logs the error, and a `fallback` prop. Render `<p className="chart-error" role="alert">` with the fallback text, defaulting to "Chart unavailable".
    - _Requirements: 10.4, 10.3_

  - [x] 2.4 Create `frontend/src/components/AgentScoreChart/index.js` and `AgentScoreChart.css`
    - Pure SVG horizontal bar chart. Props: `bars` (`{ label, value, maxValue, color }[]`) and `ariaLabel`. Render `<svg role="img">` with a `<title>`, a label per row, and the percentage text. Bar length is `value / maxValue`, capped at 1.
    - Compute the fill width in a way that works at any container width (for example a `viewBox` with fixed units). Do not rely on the percentage-width approximation in the design sketch.
    - Export a small helper `scoreColor(score)` that returns green at 0.68 or above, red at 0.38 or below, and neutral otherwise.
    - _Requirements: 5.2, 5.3, 5.4, 7.1, 10.3_

  - [x] 2.5 Add chart placeholder and error styles to `frontend/src/index.css`
    - Add `.chart-placeholder` (shimmer gradient, `@keyframes shimmer`), `.chart-empty`, and `.chart-error`. Do not change `.analysis-grid` or `.panel` rules.
    - _Requirements: 10.5, 3.6, 4.4, 6.5, 7.5, 8.5_

  - [x] 2.6 Write unit tests for the shared components
    - `ChartContainer`: calls `createChart` on mount and `remove` on unmount (mock the library), and applies resize.
    - `AgentScoreChart`: bar proportions, label text with underscores replaced, and `scoreColor` thresholds at 0.38 and 0.68.
    - `ChartErrorBoundary`: renders fallback text when a child throws.
    - Put them in `frontend/src/__tests__/unit/`, extending or replacing `ChartComponents.test.js`.
    - _Requirements: 2.2, 2.3, 5.4, 10.4_

  - [x] 2.7 Deliver via branch, PR, and passing workflows
    - Start: `git fetch origin`, `git checkout main`, `git pull --ff-only origin main`, then `git checkout -b feat/t2-shared-chart-foundation`. Commit the work from 2.1-2.5, plus 2.6 if it was done.
    - Push with `git push -u origin <branch>`. If the push fails, leave local commits unchanged, report the reason, and do not open a PR.
    - Open the PR with `gh pr create --base main --head <branch>`, then run `gh pr checks <pr> --watch`.
    - On a failed check, inspect it with `gh run view <run-id> --log-failed`, fix with a new commit, and push without force. After 3 consecutive failures of the same check, stop, leave the PR open, and report.
    - On merge conflicts, `git fetch origin` and merge `origin/main` into the branch, keeping others' changes, then push and wait for checks.
    - When all checks pass and there are no conflicts, run `gh pr merge <pr> --squash`. Then `git checkout main`, `git fetch origin`, `git merge --ff-only origin/main`.
    - Run `gh run list --branch main --limit 5` and `gh run watch <run-id>` for each main workflow until it finishes. If one fails, deliver a fix as a new unit of work.
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7, 11.8, 11.9, 11.10, 11.11, 11.12, 11.13, 11.14_

- [x] 3. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 4. Component integrations
  - [ ] 4.1 StockDeepDive candlestick and volume chart
    - In `frontend/src/components/StockDeepDive/`, add `CandlestickLayer` and `VolumeLayer` (using `useChartSeries`) and render them inside `ChartContainer` wrapped in `ChartErrorBoundary`, wired through `index.js`.
    - Show at least 60 OHLCV candles. Put volume bars on a separate price scale below. Source OHLCV from the existing path in `StockDeepDiveChart.jsx` or `api.js`.
    - Add price lines for `entry_zone.low` and `entry_zone.high`, `stop_loss` (red), and `take_profit` (green) when present.
    - Show `chart-placeholder` while `status === "loading"` and do not create a chart with empty data. Show "Price data unavailable" when the OHLCV array is empty.
    - Keep the existing text rows (Fundamentals %, Technical setup %, Sentiment %, Macro context, Entry zone, Rationale).
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8_

  - [ ] 4.2 ExplainabilityPanel probability distribution chart
    - In `frontend/src/components/ExplainabilityPanel/`, render the four `probability_distribution` values as a `HistogramSeries` inside `ChartContainer`, with per-bar colors green (`up_5pct_20d`), red (`down_3pct_20d`), grey (`flat_20d`), orange (`tail_loss_8pct_20d`).
    - Add an HTML legend listing each scenario name and its percentage.
    - Show a placeholder while loading, and "Distribution data unavailable" when the object is absent. Keep driver rows, key risks, and source evidence.
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

  - [ ] 4.3 ExplainabilityPanel agent score chart
    - In the same panel (after 4.2, which edits the same files), render `AgentScoreChart` for `component_scores` with all seven agents: `fundamentals`, `technical`, `news_sentiment`, `macro`, `alt_data`, `debate`, `tax`.
    - Replace underscores in labels with spaces. Color bars with `scoreColor`. Show "Agent scores unavailable" when `component_scores` is absent.
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [ ] 4.4 BacktestViewer equity curve chart
    - In `frontend/src/components/BacktestViewer/`, render an `AreaSeries` from `full_walkforward_backtest.equity_curve` (at least two values). Use a green fill when the final value is above $100,000 and red otherwise.
    - Format the Y-axis in USD and show the start ($100,000) and final values as price lines or ticks.
    - Add markers from `trades`: up arrow for BUY, down arrow for SELL, positioned by time index.
    - Show a placeholder while loading, and "Equity curve data unavailable" when the curve is absent or shorter than two values. Keep all metric rows, the journal entries, and the "Paper execute" button.
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7_

  - [ ] 4.5 PortfolioHealth risk metrics bars
    - In `frontend/src/components/PortfolioHealth/`, render `AgentScoreChart` bars for VaR, CVaR, gross exposure, and net exposure from `metrics`. Normalize VaR and CVaR against total portfolio equity and exposures against 1.0.
    - When `risk.kill_switch_required` is true, color all bars red and show a "Risk breach" header badge. Otherwise color each bar on a green-to-amber scale by proximity to its threshold.
    - Show a placeholder while loading and "Risk data unavailable" when the response is missing. Keep the existing text rows.
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7_

  - [ ] 4.6 StressTest scenario selector and comparison chart
    - Create `frontend/src/components/StressTest/ScenarioSelector.js`, a dropdown populated from the `/stress-test/scenarios` endpoint, disabled while loading. Calling `runStressTest()` on change must update the chart (at least three scenarios supported).
    - Create `frontend/src/components/StressTest/StressBarChart.js`, grouped SVG bars per position: `current_value` in neutral, and `stressed_value` in red for negative `pnl` or green for positive. Label each group with `symbol` and put `pnl_percent` on the stressed bar.
    - Wire both into `StressTest/index.js` inside `ChartErrorBoundary`. Show a loading indicator on the chart area, and "Stress test data unavailable" when `positions` is empty. Keep the scenario name, total P/L, and portfolio impact rows.
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7_

  - [ ] 4.7 DiscoveryScanner confidence bars and signal indicators
    - Create `frontend/src/components/DiscoveryScanner/ConfidenceBar.js`: an inline bar proportional to `confidence` (0 to 100%), green at 0.68 or above, amber from 0.55 up to 0.68, red below 0.55.
    - Create `frontend/src/components/DiscoveryScanner/SignalIndicator.js`: ▲ green for BUY, ▼ red for SELL, — grey for HOLD.
    - Use both in the result rows in `DiscoveryScanner/index.js`. Keep all columns and filters, and render the "Run a scan to rank the universe." row with no chart elements when there are no results.
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

  - [ ] 4.8 Deliver via branch, PR, and passing workflows
    - Start only after 2.7 has merged. Run `git fetch origin`, `git checkout main`, `git pull --ff-only origin main`, then `git checkout -b feat/t4-component-chart-integrations` (or one branch per wave or component group if delivering in smaller units, such as `feat/t4-1-stock-deep-dive-chart`). Commit the work from 4.1-4.7.
    - Push with `git push -u origin <branch>`, open the PR with `gh pr create --base main --head <branch>`, and run `gh pr checks <pr> --watch`.
    - Fix failing checks with new commits and no force push or bypass. Stop and report after 3 consecutive failures of the same check.
    - Resolve any conflicts by merging `origin/main` into the branch, keeping others' changes.
    - Merge with `gh pr merge <pr> --squash` only when all checks pass. Then update local `main` with `git checkout main`, `git fetch origin`, `git merge --ff-only origin/main`.
    - Watch main workflows with `gh run list --branch main --limit 5` and `gh run watch <run-id>`. Fix failures through a new unit of work.
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7, 11.8, 11.9, 11.10, 11.11, 11.12, 11.13, 11.14_

- [ ] 5. Theming, accessibility, and cleanup
  - [ ] 5.1 Audit theming, accessibility, and layout across all chart areas
    - Confirm every chart area is wrapped in `ChartErrorBoundary` and has an `ariaLabel` plus a text alternative (the existing numeric rows or a visually hidden table).
    - Confirm all charts take colors from `styles/chart-theme.js`, use no new inline styles that override `.analysis-grid` or `.panel`, and stay inside those classes.
    - Remove or redirect superseded files (`components/Charts/*`, `*Enhanced.jsx`, `utils/charts/theme.js`) only when no import remains, and make sure `npm run build` passes.
    - _Requirements: 1.2, 10.1, 10.2, 10.3, 10.4, 10.5_

  - [ ] 5.2 Write integration tests for chart-bearing components
    - Extend `frontend/src/__tests__/integration/ChartIntegration.test.js` with mocked API data covering, for each of the six components, the loading placeholder, the populated chart, and the specified unavailable message.
    - Cover the kill-switch color change in PortfolioHealth, the scenario switch in StressTest, and the confidence color thresholds in DiscoveryScanner.
    - _Requirements: 3.6, 3.7, 4.5, 5.5, 6.6, 7.3, 7.6, 8.3, 8.6, 9.2, 9.5_

  - [ ] 5.3 Deliver via branch, PR, and passing workflows
    - Start only after 4.8 has merged. Run `git fetch origin`, `git checkout main`, `git pull --ff-only origin main`, then `git checkout -b chore/t5-chart-theming-a11y-cleanup`. Commit the work from 5.1, plus 5.2 if it was done.
    - Push with `git push -u origin <branch>`, open the PR with `gh pr create --base main --head <branch>`, and run `gh pr checks <pr> --watch`.
    - Fix failing checks with new commits and no force push or bypass. Stop and report after 3 consecutive failures of the same check.
    - Resolve any conflicts on the branch by merging `origin/main`, keeping others' changes.
    - Merge with `gh pr merge <pr> --squash` only when all checks pass. Update local `main` with `git checkout main`, `git fetch origin`, `git merge --ff-only origin/main`.
    - Watch main workflows with `gh run watch <run-id>` until each finishes. Fix failures through a new unit of work.
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7, 11.8, 11.9, 11.10, 11.11, 11.12, 11.13, 11.14_

- [ ] 6. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 7. Final delivery verification
  - [ ] 7.1 Confirm repository state after all deliveries
    - Run `git fetch origin` and confirm `git rev-parse main` equals `git rev-parse origin/main`.
    - Run `gh run list --branch main --limit 10` and confirm the latest main workflows passed. Run `gh pr list --state open` and confirm every PR from this plan checks out as green or is merged.
    - Run `git branch -r --no-merged origin/main` and `git branch --no-merged main` and confirm no feature branch holds unmerged work. Report any that do.
    - _Requirements: 11.12, 11.13, 11.14, 11.2_

- [ ] 8. Infrastructure follow-up: Lambda artifact paths
  - [ ] 8.1 Align Lambda zip locations between the CI build and the Terraform stacks
    - Outside the chart scope of this plan. Found while fixing CI on PR #29: `terraform validate` passes only because of `fileexists(...) ? ... : null` guards, and `terraform apply` would not find the zips.
    - Pick one artifact location and file name per Lambda, then use it in `.github/scripts/ci/build_one_lambda.sh`, `.github/workflows/build-lambdas.yml`, `scripts/deploy.py`, and every stack. Paths resolve from each stack folder (`infrastructure/terraform/<stack>`), so `${path.module}/../..` is `infrastructure/` and the repo root is `${path.module}/../../..`.
    - Fix the build script inputs, which point at folders that do not exist: `SERVICE_DIR` is `backend/services/<arg>`, but the API is in `backend/api_gateway`, the planner is in `backend/services/agents/portfolio_planner`, and ingestion is in `backend/services/knowledge_base/ingestion` (the workflow passes `api_gateway`, `portfolio_planner`, and `knowledge_base/ingest`).
    - Fix the Terraform references:
      - `3_ingestion/main.tf`: `../../backend/services/knowledge_base/ingestion/lambda_function.zip` (the build copies it to `knowledge_base.zip`).
      - `4_researcher/main.tf`: `../../backend/scheduler/lambda_function.zip`; the scheduler is in `backend/services/scheduler` and the build expects `scheduler.zip`.
      - `6_agents/main.tf`: `../../backend/${each.key}/${each.key}_lambda.zip` for `planner`, `tagger`, `reporter`, `charter`, `retirement`; the build renames these to `<name>.zip` inside each agent folder.
      - `7_frontend/main.tf`: `../../backend/api/api_lambda.zip`; the build renames it to `api.zip`, and `scripts/deploy.py` expects `api_lambda.zip`.
    - Keep the `fileexists` guards so `terraform validate` still passes on a checkout without built zips.
    - Verify: build at least one Lambda through `build_one_lambda.sh`, confirm the zip lands at the path its stack references, and run `terraform validate` for stacks 2-8 plus `terraform fmt -check -recursive`.
    - _Requirements: none in requirements.md (infrastructure fix outside the chart scope)_

  - [ ] 8.2 Deliver via branch, PR, and passing workflows
    - Start only after 7.1. Run `git fetch origin`, `git checkout main`, `git pull --ff-only origin main`, then `git checkout -b fix/t8-lambda-artifact-paths`. Commit the work from 8.1.
    - Push with `git push -u origin <branch>`, open the PR with `gh pr create --base main --head <branch>`, and run `gh pr checks <pr> --watch`.
    - Fix failing checks with new commits and no force push or bypass. Stop and report after 3 consecutive failures of the same check.
    - Resolve any conflicts on the branch by merging `origin/main`, keeping others' changes.
    - Merge with `gh pr merge <pr> --squash` only when all checks pass. Update local `main` with `git checkout main`, `git fetch origin`, `git merge --ff-only origin/main`.
    - Watch main workflows with `gh run watch <run-id>` until each finishes. Fix failures through a new unit of work.
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7, 11.8, 11.9, 11.10, 11.11, 11.12, 11.13, 11.14_

- [ ] 9. Restore automatic deploy triggers
  - [ ] 9.1 Switch the deploy workflows back from manual-only to their original triggers
    - Background: after PR #29 the deploy workflows failed on every push to `main`, so they were made manual-only (`workflow_dispatch`) on branch `fix/deploy-workflows-manual-dispatch`. Do this task only after tasks 1-8 are complete.
    - Prerequisites (check each before changing triggers):
      - Task 8 has merged, so the Lambda zips land where Terraform expects them.
      - `terraform-apply.yml` points at a Terraform folder that exists. It currently uses `infrastructure/terraform/envs/<environment>`, which is not in the repo; create those environment roots or point it at the numbered stacks.
      - The repository secrets used by the workflows are set: `AWS_DEPLOY_ROLE_ARN`, `TFVARS_STAGING`, `TFVARS_PROD`, `CLERK_PUBLISHABLE_KEY_STAGING`, `CLERK_PUBLISHABLE_KEY_PROD`.
      - The GitHub environments `staging` and `prod` exist, with required reviewers on `prod`.
      - `deploy-staging` and `deploy-production` have each completed one successful manual run from the Actions tab.
    - In `.github/workflows/deploy-staging.yml`, restore `push: branches: [main]` alongside `workflow_dispatch`.
    - In `.github/workflows/deploy-production.yml`, restore `push: tags: ["v*.*.*"]` alongside `workflow_dispatch`, keeping the `guard` confirmation and the `m10-gate` go-live gate before `build`.
    - Remove the "Manual only" comments from both files. Leave `deploy.yml` as `workflow_dispatch` only; it was manual before PR #29.
    - Verify: `actionlint` passes on all workflows; after merge, the push to `main` starts `deploy-staging` and it finishes green. Production runs only when a `v*.*.*` tag is pushed.
    - _Requirements: none in requirements.md (CI/CD follow-up outside the chart scope)_

  - [ ] 9.2 Deliver via branch, PR, and passing workflows
    - Start only after 9.1 prerequisites are met. Run `git fetch origin`, `git checkout main`, `git pull --ff-only origin main`, then `git checkout -b ci/t9-restore-deploy-triggers`. Commit the work from 9.1.
    - Push with `git push -u origin <branch>`, open the PR with `gh pr create --base main --head <branch>`, and run `gh pr checks <pr> --watch`.
    - Fix failing checks with new commits and no force push or bypass. Stop and report after 3 consecutive failures of the same check.
    - Resolve any conflicts on the branch by merging `origin/main`, keeping others' changes.
    - Merge with `gh pr merge <pr> --squash` only when all checks pass. Update local `main` with `git checkout main`, `git fetch origin`, `git merge --ff-only origin/main`.
    - This merge triggers `deploy-staging`. Watch it with `gh run watch <run-id>` until it finishes, and fix failures through a new unit of work.
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7, 11.8, 11.9, 11.10, 11.11, 11.12, 11.13, 11.14_

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP.
- `design.md` has no Correctness Properties section, so there are no property-based test tasks. Unit and integration tests are used instead.
- Task 1.1 is already complete. Other tasks are unchecked because the earlier implementation lives at non-design paths. Where the old code already satisfies a requirement, migrate it rather than rewrite it.
- Each task references requirement numbers from `requirements.md`.
- Delivery tasks (2.7, 4.8, 5.3) and final verification (7.1) are required, not optional. Optional test tasks (2.6, 5.2) are included in the delivery when they were done.
- Delivery follows Requirement 11. Never use force push, `--no-verify`, or bypass required checks.
- Task 8 is an infrastructure follow-up outside the chart scope. It touches CI scripts and Terraform only, and no frontend code.
- Task 9 restores the automatic deploy triggers that were switched to manual-only after PR #29. It runs last, after tasks 1-8.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["2.1"] },
    { "id": 1, "tasks": ["2.2", "2.3", "2.4", "2.5"] },
    { "id": 2, "tasks": ["2.6"] },
    { "id": 3, "tasks": ["2.7"] },
    { "id": 4, "tasks": ["4.1", "4.2", "4.4", "4.5", "4.6", "4.7"] },
    { "id": 5, "tasks": ["4.3"] },
    { "id": 6, "tasks": ["4.8"] },
    { "id": 7, "tasks": ["5.1"] },
    { "id": 8, "tasks": ["5.2"] },
    { "id": 9, "tasks": ["5.3"] },
    { "id": 10, "tasks": ["6"] },
    { "id": 11, "tasks": ["7.1"] },
    { "id": 12, "tasks": ["8.1"] },
    { "id": 13, "tasks": ["8.2"] },
    { "id": 14, "tasks": ["9.1"] },
    { "id": 15, "tasks": ["9.2"] }
  ]
}
```
