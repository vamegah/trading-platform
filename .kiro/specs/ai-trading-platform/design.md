# Design Document: AI Trading Platform — Frontend Chart Enrichment

## Overview

This design enriches the existing React 19 + Vite 7 frontend with interactive financial charts using `@tradingview/lightweight-charts` (v4+). Six target components — StockDeepDive, ExplainabilityPanel, BacktestViewer, PortfolioHealth, StressTest, and DiscoveryScanner — are augmented with purpose-built chart visualizations. All data flows through the existing `frontend/src/services/api.js` service layer; no backend changes are required.

The central architectural decision is a shared `ChartContainer` component that owns the Lightweight Charts lifecycle, paired with a `useChartSeries` hook that gives child components a safe, ref-based interface to add and update series data. A custom `AgentScoreChart` SVG component handles the bar-chart use cases that do not require a full Lightweight Charts instance (agent scores, portfolio risk metrics).

---

## Architecture

### Component Hierarchy

```
App
├── StockDeepDive
│   ├── ChartContainer          ← candlestick + volume
│   └── (existing text rows)
├── ExplainabilityPanel
│   ├── ChartContainer          ← probability distribution histogram
│   ├── AgentScoreChart         ← seven-agent bar chart (SVG)
│   └── (existing driver rows)
├── BacktestViewer
│   ├── ChartContainer          ← equity curve area series
│   └── (existing metric rows)
├── PortfolioHealth
│   ├── AgentScoreChart         ← risk metrics horizontal bars (SVG)
│   └── (existing text rows)
├── StressTest
│   ├── ScenarioSelector        ← dropdown populated from /stress-test/scenarios
│   ├── StressBarChart          ← grouped SVG bars (current vs stressed)
│   └── (existing summary rows)
└── DiscoveryScanner
    └── (table rows with inline ConfidenceBar + SignalIndicator)
```

### New Files to Create

```
frontend/src/components/ChartContainer/
  index.js          ← ChartContainer component + useChartSeries hook
  ChartContainer.css

frontend/src/components/AgentScoreChart/
  index.js          ← reusable SVG horizontal bar chart
  AgentScoreChart.css

frontend/src/components/StressTest/
  StressBarChart.js ← grouped SVG bar chart for stress scenarios
  ScenarioSelector.js

frontend/src/components/DiscoveryScanner/
  ConfidenceBar.js  ← inline progress-bar cell
  SignalIndicator.js ← directional indicator cell

frontend/src/components/ChartErrorBoundary/
  index.js          ← React error boundary wrapping all chart areas

frontend/src/styles/chart-theme.js ← shared dark-mode theme constants
```

---

## Dependency Installation

Add to `frontend/package.json` under `"dependencies"`:

```json
"@tradingview/lightweight-charts": "^4.2.0"
```

No other charting libraries are introduced. The existing plain-CSS approach is preserved; chart theming is applied via `createChart()` options rather than CSS overrides.

---

## Shared Theme Constants

`frontend/src/styles/chart-theme.js` exports a single object consumed by every `createChart()` call and by the SVG components:

```js
// frontend/src/styles/chart-theme.js
export const CHART_THEME = {
  background: '#0d0d0d',
  text:       '#e2e8f0',
  grid:       '#1e293b',
  border:     '#334155',
  // semantic colors — all meet ≥ 3:1 contrast on #0d0d0d
  green:  '#22c55e',   // contrast ~5.2:1
  red:    '#ef4444',   // contrast ~4.1:1
  amber:  '#f59e0b',   // contrast ~4.8:1
  grey:   '#94a3b8',   // contrast ~4.6:1
  orange: '#f97316',   // contrast ~4.5:1
  neutral:'#60a5fa',   // contrast ~4.9:1
};

export const CHART_OPTIONS = {
  layout: {
    background: { color: CHART_THEME.background },
    textColor:  CHART_THEME.text,
  },
  grid: {
    vertLines:  { color: CHART_THEME.grid },
    horzLines:  { color: CHART_THEME.grid },
  },
  timeScale: { borderColor: CHART_THEME.border },
};
```

---

## ChartContainer Component

`ChartContainer` is the sole owner of a Lightweight Charts instance. It mounts the chart, handles resize via `ResizeObserver`, and exposes a stable `chartRef` through context so child hooks can add series.

### Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `height` | `number` | `260` | Fixed pixel height of the chart area |
| `options` | `object` | `{}` | Merged into `CHART_OPTIONS` via `createChart()` |
| `ariaLabel` | `string` | required | Accessible label for the chart wrapper `<div>` |
| `children` | `node` | — | Series components rendered inside the context |

### Implementation Sketch

```js
// frontend/src/components/ChartContainer/index.js
import { createContext, useContext, useEffect, useRef } from 'react';
import { createChart } from '@tradingview/lightweight-charts';
import { CHART_OPTIONS } from '../../styles/chart-theme';
import './ChartContainer.css';

const ChartContext = createContext(null);

export function useChartSeries() {
  return useContext(ChartContext);
}

export default function ChartContainer({ height = 260, options = {}, ariaLabel, children }) {
  const containerRef = useRef(null);
  const chartRef     = useRef(null);

  useEffect(() => {
    const el = containerRef.current;
    chartRef.current = createChart(el, {
      ...CHART_OPTIONS,
      ...options,
      width:  el.clientWidth,
      height,
    });

    const observer = new ResizeObserver(([entry]) => {
      chartRef.current?.applyOptions({ width: entry.contentRect.width });
    });
    observer.observe(el);

    return () => {
      observer.disconnect();
      chartRef.current?.remove();
      chartRef.current = null;
    };
  }, []); // mount/unmount only

  // Sync height changes without remounting
  useEffect(() => {
    chartRef.current?.applyOptions({ height });
  }, [height]);

  return (
    <ChartContext.Provider value={chartRef}>
      <div
        ref={containerRef}
        className="chart-container"
        role="img"
        aria-label={ariaLabel}
        style={{ height }}
      />
      {children}
    </ChartContext.Provider>
  );
}
```

### useChartSeries Hook Pattern

Child components call `useChartSeries()` to get the `chartRef`, then add their series inside a `useEffect`:

```js
function CandlestickLayer({ data }) {
  const chartRef = useChartSeries();
  useEffect(() => {
    if (!chartRef.current || !data?.length) return;
    const series = chartRef.current.addCandlestickSeries({ ... });
    series.setData(data);
    return () => chartRef.current?.removeSeries(series);
  }, [data, chartRef]);
  return null;
}
```

This pattern keeps series logic co-located with the component that owns the data, while the chart instance lifecycle stays in `ChartContainer`.

---

## AgentScoreChart Component

`AgentScoreChart` is a pure SVG component used wherever a horizontal bar chart is needed without a full Lightweight Charts instance (agent scores, portfolio risk metrics). It has no external dependencies beyond React.

### Props

| Prop | Type | Description |
|------|------|-------------|
| `bars` | `Array<{ label, value, maxValue, color }>` | Bar data. `value` and `maxValue` define the fill ratio. |
| `height` | `number` | Total SVG height (auto-calculated from bar count if omitted) |
| `ariaLabel` | `string` | Accessible label for the `<svg>` element |

### Layout

Each bar row is 32 px tall with 8 px gap. Label text is left-aligned at 120 px; the bar track occupies the remaining width. A filled `<rect>` is drawn proportional to `value / maxValue`.

```js
// frontend/src/components/AgentScoreChart/index.js
export default function AgentScoreChart({ bars = [], ariaLabel }) {
  const ROW_H = 32, GAP = 8, LABEL_W = 130, PAD = 12;
  const svgH = bars.length * (ROW_H + GAP) + PAD * 2;

  return (
    <svg
      role="img"
      aria-label={ariaLabel}
      width="100%"
      height={svgH}
      className="agent-score-chart"
    >
      <title>{ariaLabel}</title>
      {bars.map(({ label, value, maxValue = 1, color }, i) => {
        const y = PAD + i * (ROW_H + GAP);
        const pct = Math.min(value / maxValue, 1);
        return (
          <g key={label}>
            <text x={0} y={y + ROW_H / 2 + 5} fill="#e2e8f0" fontSize={12}>{label}</text>
            <rect x={LABEL_W} y={y} width="100%" height={ROW_H} rx={4} fill="#1e293b" />
            {/* bar fill width is computed via a foreignObject or inline calc */}
            <rect
              x={LABEL_W} y={y}
              width={`${pct * (100 - (LABEL_W / 600) * 100)}%`}
              height={ROW_H} rx={4}
              fill={color}
            />
            <text x={LABEL_W + 8} y={y + ROW_H / 2 + 5} fill="#0d0d0d" fontSize={11} fontWeight="700">
              {Math.round(value * 100)}%
            </text>
          </g>
        );
      })}
    </svg>
  );
}
```

---

## ChartErrorBoundary Component

Every chart area is wrapped in a `ChartErrorBoundary`. On error it renders a plain text fallback, preventing a single chart failure from crashing the entire panel.

```js
// frontend/src/components/ChartErrorBoundary/index.js
import { Component } from 'react';

export default class ChartErrorBoundary extends Component {
  state = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return (
        <p className="chart-error" role="alert">
          {this.props.fallback ?? 'Chart unavailable'}
        </p>
      );
    }
    return this.props.children;
  }
}
```

Usage pattern in every chart-bearing component:

```jsx
<ChartErrorBoundary fallback="Price data unavailable">
  {status === 'loading' && <div className="chart-placeholder" aria-busy="true" />}
  {status === 'ready' && ohlcv.length > 0 && (
    <ChartContainer height={280} ariaLabel={`${symbol} price chart`}>
      <CandlestickLayer data={ohlcv} signal={signal} />
      <VolumeLayer data={ohlcv} />
    </ChartContainer>
  )}
  {status === 'ready' && ohlcv.length === 0 && (
    <p className="chart-empty">Price data unavailable</p>
  )}
</ChartErrorBoundary>
```

---

## Loading and Error State Patterns

All six components follow the same three-state pattern:

| State | Condition | Rendered output |
|-------|-----------|-----------------|
| `loading` | API call in-flight | `<div className="chart-placeholder" aria-busy="true" />` — a grey shimmer block matching chart height |
| `ready` + data present | API resolved, data non-empty | Full chart component |
| `ready` + data absent / `error` | API resolved with empty data, or API rejected | Inline `<p>` with the specified error string |

The `chart-placeholder` CSS class is added to `index.css`:

```css
.chart-placeholder {
  background: linear-gradient(90deg, #1e293b 25%, #253041 50%, #1e293b 75%);
  background-size: 200% 100%;
  animation: shimmer 1.4s infinite;
  border-radius: 8px;
  width: 100%;
}

@keyframes shimmer {
  0%   { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
```

---

## Delivery Workflow

This section addresses Requirement 11. Each Unit_of_Work (one task, or a logical group of related tasks from `tasks.md`) is delivered through its own Feature_Branch and Pull_Request. The GitHub CLI (`gh`) is used for all GitHub operations (PR creation, check monitoring, merge, workflow run inspection); plain `git` is used for local operations.

### Branch Naming Convention

Format: `<type>/<task-ids>-<short-kebab-description>`

| Part | Values |
|------|--------|
| `type` | `feat`, `fix`, `chore`, `docs`, `test` |
| `task-ids` | Task number(s) from `tasks.md`, e.g. `t3` or `t3-t4` |
| description | Short kebab-case summary |

Examples: `feat/t2-chart-container`, `feat/t5-agent-score-chart`, `fix/ci-chart-lint-errors`.

### Delivery Steps

| Step | Action | Commands | Requirement |
|------|--------|----------|-------------|
| 1 | Update `main` and create the branch | `git fetch origin`, `git checkout main`, `git merge --ff-only origin/main`, `git checkout -b <branch>` | 11.1, 11.2 |
| 2 | Implement the Unit_of_Work with commits on the branch only | `git add <files>`, `git commit` | 11.2 |
| 3 | Push the branch | `git push -u origin <branch>` | 11.3 |
| 4 | Open one PR targeting `main` | `gh pr create --base main --head <branch>` | 11.2, 11.5 |
| 5 | Wait for every PR_Check to reach a final status | `gh pr checks <pr> --watch` | 11.6 |
| 6 | Merge only when every check passed and there are no conflicts | `gh pr merge <pr> --squash` (or the repository's configured merge method) | 11.6, 11.11 |
| 7 | Sync local `main` to remote `main` | `git checkout main`, `git fetch origin`, `git merge --ff-only origin/main` | 11.12 |
| 8 | Monitor Main_Workflows triggered by the merge | `gh run list --branch main --limit 5`, `gh run watch <run-id>` | 11.13 |

PR_Checks are the workflows in `.github/workflows` triggered by pull requests (for example `ci.yml` and `pr-validate.yml`) plus any required status checks on `main`. Main_Workflows are those triggered by a push to `main` (build and deploy workflows).

### Push Failure Handling (11.4)

If `git push` is rejected or fails, the Feature_Branch and its local commits are left unchanged. The failure reason is reported and no PR is opened until a push succeeds. The fix is applied with a normal fetch and merge or rebase, never a force push.

### PR Check Failure Handling (11.7, 11.8, 11.9)

```
attempts = 0; lastFailedCheck = null
loop:
  wait until all PR_Checks have a final status
  if all passed: break
  failed = name of the failing check
  attempts = (failed == lastFailedCheck) ? attempts + 1 : 1
  lastFailedCheck = failed
  if attempts >= 3:
    stop; leave PR open and unmerged;
    report check name and failure output (gh run view <run-id> --log-failed)
    exit
  inspect failure output, fix with a NEW commit on the Feature_Branch
  git push            # non-force
```

Rules:
- Fixes are always new commits pushed non-force. `--force`, `--force-with-lease`, `--no-verify`, disabling or editing git hooks, and skipping or relaxing required status checks are not used.
- The attempt counter tracks consecutive pushes where the same check fails. A different check failing, or a passing run, resets the counter.
- After the third consecutive failure of the same check, no further fix attempts are made. The PR stays open and unmerged, and the check name and failure output go to the project maintainer.

### Merge Conflict Resolution (11.10)

When the PR conflicts with `main`:
1. `git fetch origin`
2. Merge (`git merge origin/main`) or rebase `main` into the Feature_Branch. If a rebase would rewrite commits already pushed, use merge so the push stays non-force.
3. Resolve each conflict so that every change already on `main` from other contributors is kept alongside this branch's changes. A conflicting hunk is never resolved by discarding the `main` side wholesale.
4. Push non-force and wait for PR_Checks to re-run until all pass.

### Post-Merge Failure Handling (11.13, 11.14)

After the merge, every Main_Workflow triggered by the push to `main` is watched until it reports passed, failed, or cancelled. If one fails:
1. Identify the failing job and its output: `gh run view <run-id> --log-failed`.
2. Do not push directly to `main` and do not revert outside the process. Start a new Unit_of_Work (branch name such as `fix/main-<workflow>-<short-cause>`) that follows steps 1 to 8 above.

### Verification Approach

The Delivery Workflow is a process contract over git and GitHub, so it has no pure-function logic suited to property-based tests. It is enforced and verified through repository settings and observable state:
- Branch protection on `main` requires the PR_Checks and disallows force pushes and direct pushes.
- After each merge, `git rev-parse main` equals `git rev-parse origin/main`.
- `gh pr list --state open --head <branch>` shows exactly one PR per Feature_Branch.
- Main_Workflow run conclusions are checked with `gh run list --branch main`.
