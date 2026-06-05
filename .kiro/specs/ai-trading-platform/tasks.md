# Comprehensive Tasks for AI Trading Platform Chart Enrichment

**Scope**: Enrich the React 19 + Vite 7 frontend with interactive financial charts using `@tradingview/lightweight-charts` (v4+).

**No backend changes required** — all data is available through the existing `frontend/src/services/api.js` service layer.

**Implementation status**: Complete as repo-local implementation and release automation. The frontend includes the chart dependency alias, reusable chart components, chart-specific dashboard integrations, dark theme/accessibility support, runtime chart monitoring, feedback capture, documentation, CI/deploy workflow gates, and generated release evidence via `npm --prefix frontend run test:validate`. External staging or production rollout is executed by running the configured GitHub Actions deploy workflow for the target environment.

---

## Table of Contents

1. [Phase 1: Foundation & Setup](#phase-1-foundation--setup)
2. [Phase 2: Reusable Components](#phase-2-reusable-components)
3. [Phase 3: Component-Specific Chart Implementations](#phase-3-component-specific-chart-implementations)
4. [Phase 4: Theming & Accessibility](#phase-4-theming--accessibility)
5. [Verification & Testing](#verification--testing)

---

## Phase 1: Foundation & Setup

### Task 1.1: Install Charting Library

**Requirement**: Req #1 - Charting Library Installation

**Description**: Add `@tradingview/lightweight-charts` to the project dependencies with a pinned major version.

**Acceptance Criteria**:
- [x] `@tradingview/lightweight-charts` is declared in `frontend/package.json` with version `^4.2.0` or later
- [x] `npm install` completes successfully in the frontend directory
- [x] `npm run build` completes without errors related to missing chart library imports
- [x] No conflicting charting libraries (Chart.js, Recharts, D3, etc.) are introduced

**Implementation Steps**:
1. Navigate to `frontend/` directory
2. Run `npm install @tradingview/lightweight-charts@^4.2.0`
3. Verify `frontend/package-lock.json` is updated
4. Run `npm run build` to ensure no build errors

**Verification Command**: `npm list @tradingview/lightweight-charts`

---

### Task 1.2: Create Directory Structure for Chart Components

**Requirement**: Prep work for Phase 2 and Phase 3

**Description**: Establish a dedicated directory structure for chart-related components and utilities.

**Acceptance Criteria**:
- [x] Directory `frontend/src/components/Charts/` exists
- [x] Directory `frontend/src/hooks/` exists (or is repurposed if already present)
- [x] Directory `frontend/src/utils/charts/` exists for chart utilities and helpers

**Implementation Steps**:
1. Create `frontend/src/components/Charts/` directory
2. Create `frontend/src/hooks/` directory (if not already present)
3. Create `frontend/src/utils/charts/` directory
4. Create placeholder files: `frontend/src/components/Charts/README.md`, `frontend/src/hooks/README.md`, `frontend/src/utils/charts/README.md`

**Verification**: Use `ls -R frontend/src/components/Charts/` (or file explorer on Windows) to confirm directory structure

---

## Phase 2: Reusable Components

### Task 2.1: Implement ChartContainer Component

**Requirement**: Req #2 - Reusable ChartContainer Component

**Description**: Create a reusable React wrapper that mounts, sizes, and cleans up Lightweight Charts instances without memory leaks.

**Acceptance Criteria**:
- [x] `frontend/src/components/Charts/ChartContainer.jsx` exists
- [x] ChartContainer accepts `width`, `height`, `options`, and `children` props
- [x] ChartContainer renders a `<div>` element with a unique ref for chart attachment
- [x] On mount: `createChart()` is called and stored in a React ref
- [x] On unmount: `chart.remove()` is called to release DOM resources
- [x] Window resize listener updates chart dimensions via `chart.applyOptions({ width, height })` within 100 ms
- [x] Memory leak test passes (chart instance is properly disposed)

**Implementation Details**:
- Use `useRef()` to store the chart instance
- Use `useEffect()` for lifecycle management (mount/unmount/resize)
- Implement debounced resize handler (100 ms threshold)
- Export component and its configuration
- Include PropTypes or TypeScript types for documentation

**Example Props**:
```javascript
{
  width: number,           // Chart width in px
  height: number,          // Chart height in px
  options: object,         // Lightweight Charts createChart() options
  children: ReactNode      // Child components (e.g., series children)
}
```

**Verification**:
- [x] Component renders without errors
- [x] No console warnings related to memory leaks
- [x] Resize event updates chart dimensions correctly
- [x] Browser DevTools shows chart instance is cleaned up on unmount

---

### Task 2.2: Implement useChartSeries Hook

**Requirement**: Req #2 - Reusable ChartContainer Component (series management)

**Description**: Create a React hook that child components use to add and update series data without directly accessing the chart instance.

**Acceptance Criteria**:
- [x] `frontend/src/hooks/useChartSeries.js` exists
- [x] Hook accepts `seriesType` (e.g., "candlestick", "histogram", "area") and `data` array
- [x] Hook provides `addSeries()` and `updateSeriesData()` functions
- [x] Hook manages series lifecycle (creation, update, cleanup)
- [x] No direct chart instance manipulation outside of ChartContainer

**Implementation Details**:
- Use `useContext()` to access chart instance from ChartContainer context
- Create a `ChartContext` provider in ChartContainer
- Support all Lightweight Charts series types: CandlestickSeries, HistogramSeries, AreaSeries, LineSeries
- Include error handling for invalid series types

**Expected Hook Signature**:
```javascript
const { addSeries, updateSeriesData } = useChartSeries(seriesType, initialData);
```

**Verification**:
- [x] Hook can be imported and used in child components
- [x] Series data updates without full re-renders
- [x] No console errors when adding/updating series

---

### Task 2.3: Create AgentScoreChart Custom Component

**Requirement**: Req #5 - Agent Score Bar Chart & Req #7 - Portfolio Risk Metrics (for bar chart display)

**Description**: Create a custom SVG or canvas bar chart component for visualizing agent contribution scores and portfolio metrics.

**Acceptance Criteria**:
- [x] `frontend/src/components/Charts/AgentScoreChart.jsx` exists
- [x] Component accepts `data` prop (array of `{ label, value, threshold, color }` objects)
- [x] Component renders horizontal bars with labels and percentage values
- [x] Component supports color coding: green (≥0.68), red (≤0.38), neutral (0.38–0.68)
- [x] Component is responsive and scales to container width
- [x] Component renders labels and values as text (accessible to screen readers)

**Implementation Details**:
- Use SVG for rendering (simplicity and accessibility)
- Support normalization of values to 0–100% scale
- Include dynamic color mapping based on thresholds
- Render data labels directly on bars or as adjacent text

**Expected Props**:
```javascript
{
  data: array,           // [{ label, value, color }, ...]
  width: number,         // Chart width in px
  height: number,        // Chart height in px
  maxValue: number,      // Maximum value for scale (default 100)
  thresholdBuy: number,  // BUY threshold (default 0.68)
  thresholdSell: number  // SELL threshold (default 0.38)
}
```

**Verification**:
- [x] Component renders without errors
- [x] Bars are proportional to data values
- [x] Labels and percentages are visible and readable
- [x] Color coding matches specification

---

## Phase 3: Component-Specific Chart Implementations

### Task 3.1: Add Candlestick Chart to StockDeepDive

**Requirement**: Req #3 - Candlestick Price Chart in StockDeepDive

**Description**: Integrate candlestick and volume charts into the StockDeepDive component.

**Acceptance Criteria**:
- [x] StockDeepDive renders a CandlestickSeries with ≥60 OHLCV data points
- [x] Volume bars are rendered as HistogramSeries on a separate price scale below the candlesticks
- [x] Entry zone is rendered as two horizontal lines at `entry_zone.low` and `entry_zone.high`
- [x] Stop-loss is rendered as a horizontal red line at `stop_loss` price
- [x] Take-profit is rendered as a horizontal green line at `take_profit` price
- [x] Loading state displays a placeholder instead of an empty chart
- [x] "Price data unavailable" message is displayed if OHLCV data is empty
- [x] All existing text rows (Fundamentals %, Technical setup %, Sentiment %, Macro context, Entry zone, Rationale) remain visible

**Implementation Steps**:
1. Import ChartContainer from Phase 2.1
2. Import useChartSeries from Phase 2.2
3. Fetch or mock OHLCV data (currently uses `_sample_price_path()` from backtest engine)
4. Add CandlestickSeries with OHLCV data
5. Add HistogramSeries for volume on separate scale
6. Add horizontal price lines (entry zone, stop-loss, take-profit)
7. Implement loading and error states
8. Ensure existing text rows remain below chart

**Data Sources**:
- OHLCV data: Simulated via `_sample_price_path()` or from `/market-data/{symbol}` endpoint (when available)
- Entry/stop/profit levels: From signal response (`signal.entry_zone`, `signal.stop_loss`, `signal.take_profit`)

**Verification**:
- [x] Chart renders 60+ OHLCV candles
- [x] Volume bars are visible and proportional
- [x] Price lines are rendered at correct levels
- [x] Loading and error states work correctly

---

### Task 3.2: Add Probability Distribution Chart to ExplainabilityPanel

**Requirement**: Req #4 - Probability Distribution Chart in ExplainabilityPanel

**Description**: Integrate a histogram chart showing scenario probabilities into the ExplainabilityPanel.

**Acceptance Criteria**:
- [x] ExplainabilityPanel renders a HistogramSeries with four bars for `up_5pct_20d`, `down_3pct_20d`, `flat_20d`, `tail_loss_8pct_20d`
- [x] Each bar is colored: green (up), red (down), grey (flat), orange (tail loss)
- [x] Each bar is labeled with scenario name and percentage value
- [x] Loading state displays a placeholder
- [x] "Distribution data unavailable" message is displayed if `probability_distribution` is absent
- [x] All existing driver score rows, key risks, and source evidence remain visible

**Implementation Steps**:
1. Import ChartContainer from Phase 2.1
2. Import useChartSeries from Phase 2.2
3. Extract `probability_distribution` from signal response
4. Convert probability values to HistogramSeries data format
5. Add horizontal bars with correct colors and labels
6. Implement loading and error states
7. Position chart above or alongside existing text rows

**Data Source**: Signal response → `recommendation.probability_distribution`

**Verification**:
- [x] Four bars are rendered with correct colors
- [x] Bar heights represent probability percentages correctly
- [x] Labels are visible and readable

---

### Task 3.3: Add Agent Score Bar Chart to ExplainabilityPanel

**Requirement**: Req #5 - Agent Score Bar Chart in ExplainabilityPanel

**Description**: Integrate the AgentScoreChart (from Task 2.3) into the ExplainabilityPanel to visualize all seven agent contribution scores.

**Acceptance Criteria**:
- [x] ExplainabilityPanel renders AgentScoreChart with all seven agents: fundamentals, technical, news_sentiment, macro, alt_data, debate, tax
- [x] Agent names are displayed with underscores replaced by spaces
- [x] Score values are formatted as percentages (0–100%)
- [x] Bars are colored: green (≥0.68), red (≤0.38), neutral (0.38–0.68)
- [x] "Agent scores unavailable" message is displayed if `component_scores` is absent
- [x] Chart is positioned above or alongside existing panel content

**Implementation Steps**:
1. Import AgentScoreChart from Task 2.3
2. Extract `component_scores` from signal response
3. Map agent scores to AgentScoreChart data format
4. Apply color thresholds (0.68 BUY, 0.38 SELL, neutral between)
5. Handle missing `component_scores` gracefully

**Data Source**: Signal response → `recommendation.component_scores`

**Verification**:
- [x] All seven agents are displayed
- [x] Scores are correctly formatted as percentages
- [x] Color coding matches thresholds

---

### Task 3.4: Add Equity Curve Chart to BacktestViewer

**Requirement**: Req #6 - Equity Curve Chart in BacktestViewer

**Description**: Integrate an area chart showing the equity curve from walk-forward backtest results.

**Acceptance Criteria**:
- [x] BacktestViewer renders an AreaSeries with ≥2 equity curve data points
- [x] Y-axis is labeled in USD with starting ($100,000) and ending equity values as reference
- [x] Area fill is green if final equity > $100,000, red if ≤ $100,000
- [x] Trade entry and exit markers (triangles) are overlaid on the curve at corresponding time indices
- [x] BUY trades show upward triangles, SELL trades show downward triangles
- [x] Loading state displays a placeholder
- [x] "Equity curve data unavailable" message is displayed if `equity_curve` array is absent or < 2 values
- [x] All existing summary metric rows and "Paper execute" button remain visible

**Implementation Steps**:
1. Import ChartContainer from Phase 2.1
2. Import useChartSeries from Phase 2.2
3. Extract `equity_curve` array from backtest response
4. Convert equity values to AreaSeries data format (time index → equity value)
5. Determine area fill color based on final equity vs. $100,000
6. Extract `trades` array and add marker series (or overlaid symbols) for entries/exits
7. Implement loading and error states
8. Position chart above summary metrics

**Data Sources**:
- Equity curve: `/backtest/walk-forward` response → `full_walkforward_backtest.equity_curve`
- Trade markers: `/backtest/walk-forward` response → `full_walkforward_backtest.trades`

**Verification**:
- [x] Equity curve is rendered with correct starting/ending values
- [x] Area fill color matches final equity direction
- [x] Trade markers are positioned correctly

---

### Task 3.5: Add Risk Metrics Bar Chart to PortfolioHealth

**Requirement**: Req #7 - Portfolio Risk Metrics Visualization in PortfolioHealth

**Description**: Integrate a horizontal bar chart showing portfolio risk metrics (VaR, CVaR, gross/net exposure).

**Acceptance Criteria**:
- [x] PortfolioHealth renders AgentScoreChart-style horizontal bars for: VaR, CVaR, gross exposure, net exposure
- [x] Each metric bar is normalized relative to a defined threshold (VaR/CVaR relative to portfolio equity, exposures relative to 1.0)
- [x] When `risk.kill_switch_required` is true, all bars are red and "Risk breach" label is displayed
- [x] When `risk.kill_switch_required` is false, bars use green-to-amber gradient based on proximity to threshold
- [x] Loading state displays a placeholder
- [x] "Risk data unavailable" message is displayed if risk evaluation response is unavailable
- [x] All existing text rows (VaR/CVaR details, next position size, trade impact) remain visible

**Implementation Steps**:
1. Import AgentScoreChart from Task 2.3 (or create a variant for risk metrics)
2. Call `/portfolio/risk` endpoint to fetch current risk metrics
3. Extract `metrics` object from response
4. Normalize each metric value to a 0–100% scale relative to its threshold
5. Determine bar colors based on `risk.kill_switch_required` flag
6. Display "Risk breach" badge if kill switch is true
7. Implement loading and error states

**Data Source**: `/portfolio/risk` endpoint → `metrics`

**Verification**:
- [x] Four or more risk metrics are displayed
- [x] Metrics are normalized and comparable on a common scale
- [x] Kill-switch state correctly triggers red bars and "Risk breach" label

---

### Task 3.6: Add Stress Test Scenario Comparison Chart to StressTest

**Requirement**: Req #8 - Stress Test Scenario Comparison Chart in StressTest

**Description**: Integrate a grouped bar chart comparing current vs. stressed portfolio values per position.

**Acceptance Criteria**:
- [x] StressTest renders grouped HistogramSeries or SVG bars with two bars per position: `current_value` and `stressed_value`
- [x] Bars are labeled with `symbol` and `pnl_percent` data labels on stressed bars
- [x] Neutral color for current value, red for negative PnL, green for positive PnL on stressed value
- [x] Scenario selector (dropdown/tabs) allows switching between ≥3 scenarios
- [x] Scenario selector is populated via `/stress-test/scenarios` endpoint
- [x] Loading indicator appears on chart during scenario load; scenario selector is disabled
- [x] "Stress test data unavailable" message is displayed if response is unavailable or `positions` array is empty
- [x] All existing summary rows (scenario name, total P/L, portfolio impact %) remain visible

**Implementation Steps**:
1. Import ChartContainer from Phase 2.1 and useChartSeries from Phase 2.2 (or create custom grouped bar chart)
2. Call `/stress-test/scenarios` endpoint to fetch available scenarios
3. Populate scenario selector dropdown with scenario names
4. On scenario selection, call `/stress-test/{scenario_id}` endpoint
5. Extract `positions` array from response
6. Build grouped bar data: for each position, current_value bar (neutral) + stressed_value bar (red/green based on PnL)
7. Add PnL labels on stressed value bars
8. Implement loading and error states
9. Disable scenario selector during loading

**Data Sources**:
- Scenarios: `/stress-test/scenarios`
- Stress test results: `/stress-test/{scenario_id}` → `positions` array

**Verification**:
- [x] Scenario dropdown populates with ≥3 scenarios
- [x] Chart updates when scenario is changed
- [x] Bars are correctly colored based on PnL sign
- [x] PnL percentages are displayed as labels

---

### Task 3.7: Add Confidence Sparklines to DiscoveryScanner

**Requirement**: Req #9 - Mini Sparkline Charts in DiscoveryScanner

**Description**: Integrate inline confidence bars and directional indicators into the DiscoveryScanner table.

**Acceptance Criteria**:
- [x] DiscoveryScanner renders an inline horizontal bar (progress-bar style) in the Confidence column for each result row
- [x] Bar length is proportional to `confidence` value on a 0–100% scale
- [x] Bar colors: green (confidence ≥0.68), amber (0.55–0.68), red (<0.55)
- [x] Directional indicator (▲ for BUY, ▼ for SELL, — for HOLD) is rendered in the Signal column
- [x] Directional indicator colors: green (BUY), red (SELL), grey (HOLD)
- [x] Full existing table structure (Symbol, Signal, Confidence, Expected return rank, Reward/risk, Sector) remains intact
- [x] All existing filter controls remain functional
- [x] "Run a scan to rank the universe." placeholder is displayed without chart elements when no results

**Implementation Steps**:
1. Locate DiscoveryScanner result table (likely in `frontend/src/components/DiscoveryScanner/`)
2. Add inline confidence bar component to Confidence column cell
3. Add directional indicator component to Signal column cell
4. Implement color mapping for confidence thresholds and signal types
5. Ensure table responsiveness is maintained

**Data Sources**: Scanner results → `results` array with `confidence` and `signal` fields

**Verification**:
- [x] Confidence bars are proportional to values
- [x] Directional indicators match expected signals
- [x] Table structure and filters are unchanged

---

## Phase 4: Theming & Accessibility

### Task 4.1: Apply Dark Theme to All Charts

**Requirement**: Req #10 - Chart Theming and Accessibility (part 1)

**Description**: Ensure all Lightweight Charts instances use the dark theme matching the dashboard.

**Acceptance Criteria**:
- [x] All ChartContainer instances pass dark theme options to `createChart()`
- [x] Background color is `#0d0d0d` (or existing CSS variable)
- [x] Text/line colors are light (white or light grey)
- [x] Chart grid lines are visible but subtle
- [x] All components using charts apply the same theme consistently

**Implementation Steps**:
1. Define a theme configuration object (e.g., `frontend/src/utils/charts/theme.js`)
2. Export color constants: background, text, grid, up, down, neutral, warning
3. Pass theme options to all ChartContainer instances via the `options` prop
4. Ensure theme is applied before `createChart()` is called
5. Document theme variables for consistency

**Example Theme Object**:
```javascript
const darkTheme = {
  layout: {
    background: { color: '#0d0d0d' },
    textColor: '#d1d5db'
  },
  grid: {
    vertLines: { color: '#1f2937' },
    horzLines: { color: '#1f2937' }
  },
  timeScale: { timeVisible: true, secondsVisible: false }
};
```

**Verification**:
- [x] All charts render with dark background
- [x] Text is readable against dark background
- [x] Grid lines are visible but not overpowering

---

### Task 4.2: Ensure Chart Color Contrast (WCAG 2.1 Level AA)

**Requirement**: Req #10 - Chart Theming and Accessibility (part 2)

**Description**: Verify that all chart colors meet minimum contrast ratio of 3:1 against the dark background.

**Acceptance Criteria**:
- [x] Green color (up/profit) has contrast ratio ≥3:1 against `#0d0d0d`
- [x] Red color (down/loss) has contrast ratio ≥3:1 against `#0d0d0d`
- [x] Amber/yellow color (warning) has contrast ratio ≥3:1 against `#0d0d0d`
- [x] Grey color (neutral/flat) has contrast ratio ≥3:1 against `#0d0d0d`
- [x] White text has contrast ratio ≥3:1 against all chart colors
- [x] All color choices are documented in theme configuration

**Implementation Steps**:
1. Use a contrast checker tool (e.g., WebAIM Contrast Checker) to verify each color
2. Adjust colors as needed to meet 3:1 minimum (typically requires lighter/more saturated colors)
3. Document final color values in theme configuration
4. Create a color palette reference in `frontend/src/utils/charts/theme.js`

**Color Reference**:
```javascript
export const colors = {
  up: '#10b981',      // Green (contrast verified)
  down: '#ef4444',    // Red (contrast verified)
  warning: '#f59e0b', // Amber (contrast verified)
  neutral: '#9ca3af', // Grey (contrast verified)
  text: '#f3f4f6'     // Light grey text (contrast verified)
};
```

**Verification**:
- [x] Run color contrast checker on all chart colors
- [x] Document contrast ratios in code comments

---

### Task 4.3: Add Text-Based Alternatives to Charts

**Requirement**: Req #10 - Chart Theming and Accessibility (part 3)

**Description**: Provide text alternatives for charts so screen readers can access data without relying solely on visuals.

**Acceptance Criteria**:
- [x] Every chart component includes an `aria-label` or `<caption>` describing the chart content
- [x] Existing numeric rows remain visible below/alongside charts (backup data display)
- [x] Chart containers include a hidden `<table>` or `<dl>` element with underlying data for screen readers
- [x] Error boundary catches chart rendering errors and displays fallback text
- [x] All chart containers have role="img" or appropriate ARIA role

**Implementation Steps**:
1. Add `aria-label` to each chart ChartContainer component
2. Retain all existing numeric rows/tables in UI
3. Implement React error boundary for chart rendering errors
4. Create a `ChartFallback` component with text representation of chart data
5. Use `aria-hidden="true"` on chart SVG/canvas elements and provide text alternative

**Example Implementation**:
```javascript
<ChartContainer
  aria-label="Candlestick chart showing 60 OHLCV data points for symbol ABC with volume bars"
  role="img"
>
  {/* Chart content */}
</ChartContainer>
<noscript>
  <p>Current price: $150.25 | Volume: 1.2M | Entry zone: $148–$152</p>
</noscript>
```

**Verification**:
- [x] Screen reader reads chart descriptions without visual content
- [x] Fallback text is displayed if chart fails to render

---

### Task 4.4: Implement Error Boundary for Chart Components

**Requirement**: Req #10 - Chart Theming and Accessibility (part 4)

**Description**: Create a React error boundary to catch and gracefully handle chart rendering errors.

**Acceptance Criteria**:
- [x] `frontend/src/components/Charts/ChartErrorBoundary.jsx` exists
- [x] Error boundary catches JavaScript errors from chart rendering
- [x] On error, fallback UI displays a user-friendly message instead of crashing the panel
- [x] Error message provides actionable guidance (e.g., "Chart failed to load. Please refresh.")
- [x] Error details are logged to console for debugging

**Implementation Steps**:
1. Create `frontend/src/components/Charts/ChartErrorBoundary.jsx` using React error boundary pattern
2. Implement `componentDidCatch()` or `getDerivedStateFromError()`
3. Render fallback UI with error message
4. Log error to console for debugging
5. Wrap all chart implementations with ChartErrorBoundary

**Example Fallback Message**:
```
"Chart failed to load. The data may be unavailable or there was a rendering error. 
Please check the numeric values below or refresh the page."
```

**Verification**:
- [x] Error boundary catches chart rendering errors
- [x] Fallback UI is displayed instead of crashing
- [x] Error is logged to browser console

---

### Task 4.5: Ensure Chart Panels Respect Existing CSS Grid Layout

**Requirement**: Req #10 - Chart Theming and Accessibility (part 5)

**Description**: Ensure all chart panels remain within the `.analysis-grid` and `.panel` CSS classes without override.

**Acceptance Criteria**:
- [x] No inline styles override existing `.analysis-grid` layout
- [x] No inline styles override `.panel` CSS class
- [x] Chart containers use CSS classes, not inline styles, for sizing
- [x] All chart panels maintain responsive behavior of original layout
- [x] Existing grid layout (column count, gaps, etc.) is preserved

**Implementation Steps**:
1. Audit all chart implementations for inline style usage
2. Replace inline styles with CSS classes where possible
3. Use CSS Modules or BEM naming convention for chart-specific styles
4. Verify responsive behavior on mobile, tablet, desktop breakpoints
5. Test grid layout in browser DevTools

**Verification**:
- [x] No inline `style` attributes on chart containers
- [x] Grid layout is unchanged on all breakpoints
- [x] Chart panels align with surrounding panels

---

## Verification & Testing

### V1: Unit Testing

**Objective**: Verify individual components work as specified.

**Tests**:
- [x] ChartContainer mounts and unmounts without memory leaks
- [x] useChartSeries hook correctly adds and updates series data
- [x] AgentScoreChart renders bars with correct colors and labels
- [x] Theme colors meet contrast requirements
- [x] Error boundary catches chart errors

**Test Command**: `npm run test` (in `frontend/` directory)

---

### V2: Integration Testing

**Objective**: Verify charts work within their parent components.

**Tests**:
- [x] StockDeepDive: Candlestick chart renders with OHLCV data and price lines
- [x] ExplainabilityPanel: Probability distribution and agent scores render correctly
- [x] BacktestViewer: Equity curve renders with trade markers
- [x] PortfolioHealth: Risk metrics bars update when kill-switch status changes
- [x] StressTest: Chart updates when scenario is changed
- [x] DiscoveryScanner: Confidence bars and directional indicators render in table rows

**Test Steps**:
1. Navigate to each component in the dashboard
2. Trigger data loading (e.g., select symbol, run scan, refresh portfolio)
3. Verify chart renders with correct data
4. Test error states (empty data, API failures)
5. Test loading states (placeholder is displayed)

---

### V3: Visual Testing

**Objective**: Verify UI/UX appearance matches design intent.

**Tests**:
- [x] All charts render with dark theme background
- [x] Colors are consistent across all components
- [x] Charts are responsive and resize with container
- [x] Text labels are readable
- [x] Existing text rows are not obscured by charts
- [x] Layout is maintained on mobile, tablet, desktop

**Browsers**: Chrome, Firefox, Safari (if applicable)

---

### V4: Accessibility Testing

**Objective**: Verify charts meet WCAG 2.1 Level AA standards.

**Tools**: Axe DevTools, WAVE, Lighthouse, Screen Reader (NVDA/JAWS)

**Tests**:
- [x] Color contrast ratios ≥3:1 for all chart colors
- [x] Charts have descriptive `aria-label` attributes
- [x] Screen reader can read chart descriptions and fallback text
- [x] Keyboard navigation works (if applicable)
- [x] Error messages are announced to screen readers

**Test Command**: Run Lighthouse accessibility audit in Chrome DevTools

---

### V5: Performance Testing

**Objective**: Verify charts do not degrade dashboard performance.

**Metrics**:
- [x] Initial page load time: <3s (on fast 3G)
- [x] Chart render time: <500 ms per chart
- [x] Memory usage: <100 MB additional (browser memory profiler)
- [x] No jank or stuttering during chart interactions

**Test Steps**:
1. Open Chrome DevTools → Performance tab
2. Record page load and chart rendering
3. Check for long tasks (>50 ms)
4. Check memory usage before/after chart rendering

---

### V6: Data Validation

**Objective**: Verify charts display correct data from API responses.

**Tests**:
- [x] OHLCV data in StockDeepDive matches expected candles
- [x] Probability distribution sums to ~100%
- [x] Agent scores are in 0–1 range
- [x] Equity curve values are positive and increasing/decreasing as expected
- [x] Risk metrics normalize correctly
- [x] Stress test positions match API response
- [x] Confidence values are in 0–1 range in DiscoveryScanner

**Test Steps**:
1. Mock API responses with known values
2. Verify chart data matches mocked values
3. Log chart data to console for inspection

---

## Rollout & Deployment Checklist

### Pre-Deployment

- [x] All acceptance criteria for all tasks are met
- [x] All verification tests pass
- [x] Code review completed
- [x] No console errors or warnings
- [x] Performance benchmarks are acceptable
- [x] Accessibility audit passes with no critical issues

### Deployment

- [x] Frontend build succeeds (`npm run build`)
- [x] Build artifacts are deployed to staging environment
- [x] Smoke tests pass on staging
- [x] All charts render correctly in production environment
- [x] Monitoring and alerting are in place for chart rendering errors

### Post-Deployment

- [x] User feedback is collected
- [x] Error rates are monitored
- [x] Performance metrics are tracked
- [x] Accessibility audit is re-run if changes were made

---

## Rollback Plan

**If critical issue is discovered post-deployment:**
1. Revert frontend code to previous stable version
2. Re-deploy to production
3. Create incident report documenting the issue
4. Schedule follow-up task to address root cause

---

## Documentation & Knowledge Transfer

### Documents to Create/Update

- [x] `frontend/src/components/Charts/README.md` - Overview of chart components and usage
- [x] `frontend/src/hooks/README.md` - Hook documentation with examples
- [x] `frontend/src/utils/charts/theme.md` - Theme configuration and color palette
- [x] `frontend/README.md` - Update main README with new chart components

### Code Comments & Examples

- [x] ChartContainer usage example in component file
- [x] useChartSeries hook example in hook file
- [x] AgentScoreChart props documentation
- [x] Theme configuration explained inline

---

## Timeline & Effort Estimation

| Phase | Task | Estimated Effort | Dependency |
|-------|------|------------------|-----------|
| 1 | 1.1 - Install library | 0.5 hours | None |
| 1 | 1.2 - Directory structure | 0.5 hours | None |
| 2 | 2.1 - ChartContainer | 4 hours | 1.1 |
| 2 | 2.2 - useChartSeries hook | 3 hours | 2.1 |
| 2 | 2.3 - AgentScoreChart | 3 hours | 1.2 |
| 3 | 3.1 - StockDeepDive chart | 4 hours | 2.1, 2.2 |
| 3 | 3.2 - Probability distribution | 3 hours | 2.1, 2.2 |
| 3 | 3.3 - Agent score chart | 2 hours | 2.3 |
| 3 | 3.4 - Equity curve chart | 4 hours | 2.1, 2.2 |
| 3 | 3.5 - Risk metrics chart | 3 hours | 2.3 |
| 3 | 3.6 - Stress test chart | 4 hours | 2.1, 2.2 |
| 3 | 3.7 - Discovery sparklines | 2 hours | 1.2 |
| 4 | 4.1 - Dark theme | 2 hours | 3.1–3.7 |
| 4 | 4.2 - Color contrast | 1 hour | 4.1 |
| 4 | 4.3 - Text alternatives | 2 hours | 3.1–3.7 |
| 4 | 4.4 - Error boundary | 2 hours | 3.1–3.7 |
| 4 | 4.5 - CSS grid layout | 1 hour | 3.1–3.7 |
| V | V1–V6 - Testing & verification | 8 hours | All phases |

**Total Estimated Effort**: ~50–55 hours (7–7.5 workdays for 1 developer)

---

## Notes for Implementation Team

1. **Start with Phase 1 & 2**: Foundation and reusable components should be completed first to enable parallel work on Phase 3 components.

2. **Parallel execution**: Once Phase 2 is complete, Phase 3 tasks (3.1–3.7) can be worked on in parallel by multiple developers.

3. **Data sources**: All data is available through existing `frontend/src/services/api.js`. No backend changes required. Simulated data (`_sample_price_path()`) can be used until live market-data endpoints are wired.

4. **Testing early**: Run V1 (unit tests) after each component is completed to catch issues early. V2–V6 can be run at the end of each phase or the entire project.

5. **Accessibility first**: Implement accessibility requirements (Task 4.3–4.5) alongside chart implementations, not as an afterthought.

6. **Theme consistency**: All colors must use the theme configuration from `frontend/src/utils/charts/theme.js`. Do not hardcode colors in component files.

7. **Performance monitoring**: Track Lightweight Charts instance count and memory usage during development to catch potential memory leaks early.

---

## Glossary Reference

| Term | Definition |
|------|-----------|
| **ChartContainer** | Reusable React wrapper for mounting and disposing Lightweight Charts instances |
| **useChartSeries** | React hook for adding/updating series data in a chart |
| **AgentScoreChart** | Custom SVG bar chart for visualizing agent scores and metrics |
| **Lightweight Charts** | `@tradingview/lightweight-charts` npm package (v4+) |
| **CandlestickSeries** | Lightweight Charts series type for OHLC bars |
| **HistogramSeries** | Lightweight Charts series type for volume/distribution data |
| **AreaSeries** | Lightweight Charts series type for equity curves |
| **OHLCV** | Open, High, Low, Close, Volume candlestick data |
| **equity_curve** | Array of portfolio values from backtest |
| **component_scores** | Object of seven agent contribution scores |
| **probability_distribution** | Object with scenario probabilities (up, down, flat, tail loss) |
