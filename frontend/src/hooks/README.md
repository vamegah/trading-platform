# React Hooks

## `useChartSeries`

`useChartSeries` is the only hook chart children need for Lightweight Charts series lifecycle work. It reads the chart from `ChartContext`, supports v5 series definitions, and falls back to legacy v4 methods for tests or older chart mocks.

```jsx
function EquitySeries({ data }) {
  const { addSeries, removeSeries, fitContent } = useChartSeries();

  useEffect(() => {
    const result = addSeries('area', { lineWidth: 2 }, data);
    fitContent();
    return () => result?.seriesId && removeSeries(result.seriesId);
  }, [addSeries, data, fitContent, removeSeries]);

  return null;
}
```

Supported series types are `candlestick`, `histogram`, `area`, and `line`. The hook also exposes helpers for price lines, price-scale options, and trade markers.
