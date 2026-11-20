import React, { createContext, useContext, useEffect, useRef, useState } from 'react';
import PropTypes from 'prop-types';
import { createChart } from '@tradingview/lightweight-charts';
import { CHART_OPTIONS } from '../../styles/chart-theme';
import { recordChartPerformance } from '../../utils/charts/monitoring';
import './ChartContainer.css';

const RESIZE_DEBOUNCE_MS = 50;

/** Context value is the chart ref ({ current: IChartApi | null }). */
export const ChartContext = createContext(null);

function isPlainObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function mergeOptions(base, overrides) {
  const merged = { ...base };
  Object.entries(overrides || {}).forEach(([key, value]) => {
    merged[key] =
      isPlainObject(value) && isPlainObject(merged[key]) ? mergeOptions(merged[key], value) : value;
  });
  return merged;
}

/** Returns the chart ref provided by the nearest ChartContainer. */
export function useChartSeries() {
  return useContext(ChartContext);
}

function ChartContainer({ height = 260, width, options, ariaLabel, children }) {
  const containerRef = useRef(null);
  const chartRef = useRef(null);
  const optionsRef = useRef(options);
  const sizeRef = useRef({ width, height });
  const [ready, setReady] = useState(false);

  optionsRef.current = options;
  sizeRef.current = { width, height };

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return undefined;

    const measure = () => ({
      width: sizeRef.current.width || el.clientWidth || 0,
      height: sizeRef.current.height || el.clientHeight || 0,
    });

    const startedAt = typeof performance !== 'undefined' ? performance.now() : Date.now();
    const chart = createChart(el, { ...mergeOptions(CHART_OPTIONS, optionsRef.current), ...measure() });
    chartRef.current = chart;
    recordChartPerformance({
      component: 'ChartContainer',
      durationMs: (typeof performance !== 'undefined' ? performance.now() : Date.now()) - startedAt,
      metadata: { phase: 'mount' },
    });
    setReady(true);

    let observer = null;
    let timer = null;
    if (typeof ResizeObserver !== 'undefined') {
      observer = new ResizeObserver(() => {
        clearTimeout(timer);
        timer = setTimeout(() => {
          if (chartRef.current) chartRef.current.applyOptions(measure());
        }, RESIZE_DEBOUNCE_MS);
      });
      observer.observe(el.parentElement || el);
    }

    return () => {
      clearTimeout(timer);
      if (observer) observer.disconnect();
      chart.remove();
      chartRef.current = null;
      setReady(false);
    };
  }, []);

  useEffect(() => {
    if (!chartRef.current) return;
    chartRef.current.applyOptions({
      ...mergeOptions(CHART_OPTIONS, options),
      ...(width ? { width } : {}),
      height,
    });
  }, [options, width, height]);

  const style = { '--chart-height': `${height}px` };
  if (width) style['--chart-width'] = `${width}px`;

  return (
    <ChartContext.Provider value={chartRef}>
      <div
        ref={containerRef}
        role="img"
        aria-label={ariaLabel}
        className={`chart-container${width ? ' chart-container--fixed-width' : ''}`}
        style={style}
      >
        {ready ? children : null}
      </div>
    </ChartContext.Provider>
  );
}

ChartContainer.propTypes = {
  height: PropTypes.number,
  width: PropTypes.number,
  options: PropTypes.object,
  ariaLabel: PropTypes.string,
  children: PropTypes.node,
};

export default ChartContainer;
