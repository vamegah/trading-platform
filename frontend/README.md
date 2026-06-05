# Trading Platform Frontend

React 19 + Vite dashboard for the AI trading platform.

## Chart Enrichment

The chart layer uses TradingView Lightweight Charts through the `@tradingview/lightweight-charts` npm alias. Vite resolves the alias to the official `lightweight-charts` package.

Implemented chart surfaces:

- Stock deep dive candlestick and volume chart with entry, stop-loss, and take-profit price lines.
- Explainability probability histogram and seven-agent contribution score chart.
- Backtest equity curve with BUY/SELL markers.
- Portfolio risk metric bars with kill-switch breach state.
- Stress-test grouped position comparison chart populated from `/stress-test/scenarios`.
- Discovery scanner confidence bars and BUY/SELL/HOLD directional indicators.

## Commands

```powershell
npm --prefix frontend run build
npm --prefix frontend run test
npm --prefix frontend run test:validate
```

`npm --prefix frontend run test` runs the local chart-task verifier in `scripts/test-chart-tasks.mjs`.

`npm --prefix frontend run test:validate` runs the full chart release gate:

- chart task verifier
- production build
- accessibility validation
- performance and bundle budget validation
- data-shape validation
- visual layout validation
- release smoke validation

The gate writes JSON reports to `release-evidence/` and is also wired into CI and the deploy workflow.

## Runtime Monitoring

Chart rendering errors, chart render timings, and chart feedback are stored in browser `localStorage` and sent to `/chart-monitoring` with `navigator.sendBeacon` when available. The same records can be read with `getChartMonitoringSnapshot()` from `src/utils/charts/monitoring.js`.
