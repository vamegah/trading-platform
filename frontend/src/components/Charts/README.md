# Chart Components

Reusable chart components for the trading dashboard.

## Components

- `ChartContainer`: mounts a TradingView Lightweight Charts instance, applies the shared dark theme, debounces window resize at 100 ms, exposes the chart through `ChartContext`, and removes the instance on unmount.
- `ChartErrorBoundary`: catches chart rendering errors and shows fallback text without crashing the surrounding panel.
- `ChartDataTable`: renders hidden screen-reader tables with the underlying chart data.
- `AgentScoreChart`: responsive SVG horizontal bar chart used for agent contribution scores and portfolio risk metrics.

## Usage

```jsx
<ChartErrorBoundary fallbackHeight={300}>
  <div className="chart-frame chart-frame--price">
    <ChartContainer
      aria-label="Candlestick chart showing 60 OHLCV data points"
      height={300}
      width={800}
    >
      <PriceSeries data={ohlcvData} />
    </ChartContainer>
  </div>
</ChartErrorBoundary>
```

Chart sizing should come from CSS classes such as `chart-frame--price` rather than inline styles, so panels continue to respect the existing `.analysis-grid` and `.panel` layout.
