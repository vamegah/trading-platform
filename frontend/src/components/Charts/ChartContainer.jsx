import React, { useRef, useEffect, createContext, useState } from 'react';
import { createChart } from '@tradingview/lightweight-charts';
import PropTypes from 'prop-types';
import { darkThemeOptions } from '../../utils/charts/theme';
import { recordChartError, recordChartPerformance } from '../../utils/charts/monitoring';

export const ChartContext = createContext(null);

function mergeOptions(base, overrides) {
  const merged = { ...base };
  Object.entries(overrides || {}).forEach(([key, value]) => {
    if (
      value &&
      typeof value === 'object' &&
      !Array.isArray(value) &&
      merged[key] &&
      typeof merged[key] === 'object' &&
      !Array.isArray(merged[key])
    ) {
      merged[key] = mergeOptions(merged[key], value);
      return;
    }
    merged[key] = value;
  });
  return merged;
}

/**
 * ChartContainer - Reusable wrapper for Lightweight Charts instances
 * 
 * Handles lifecycle management, resizing, and cleanup to prevent memory leaks.
 * Provides chart instance to child components via ChartContext.
 */
const ChartContainer = React.forwardRef(({
  width = 800,
  height = 400,
  options = {},
  children,
  className = 'chart-canvas',
  ariaLabel,
  monitoringName = 'ChartContainer',
  role = 'img',
  ...props
}, ref) => {
  const containerRef = useRef(null);
  const chartRef = useRef(null);
  const [chartInstance, setChartInstance] = useState(null);
  const resizeTimeoutRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current) return;

    try {
      const startedAt = typeof performance !== 'undefined' ? performance.now() : Date.now();
      const chart = createChart(containerRef.current, {
        ...mergeOptions(darkThemeOptions, options),
        width: containerRef.current.clientWidth || width,
        height: containerRef.current.clientHeight || height,
      });

      chartRef.current = chart;
      setChartInstance(chart);
      recordChartPerformance({
        component: monitoringName,
        durationMs: (typeof performance !== 'undefined' ? performance.now() : Date.now()) - startedAt,
        metadata: {
          height,
          width,
        },
      });

      const handleResize = () => {
        if (resizeTimeoutRef.current) {
          clearTimeout(resizeTimeoutRef.current);
        }

        resizeTimeoutRef.current = setTimeout(() => {
          if (containerRef.current && chartRef.current) {
            chartRef.current.applyOptions({
              width: containerRef.current.clientWidth || width,
              height: containerRef.current.clientHeight || height,
            });
          }
        }, 100);
      };

      window.addEventListener('resize', handleResize);
      handleResize();

      return () => {
        window.removeEventListener('resize', handleResize);
        if (resizeTimeoutRef.current) {
          clearTimeout(resizeTimeoutRef.current);
        }
        if (chartRef.current) {
          chartRef.current.remove();
          chartRef.current = null;
          setChartInstance(null);
        }
      };
    } catch (error) {
      recordChartError({
        component: monitoringName,
        message: error?.message,
        stack: error?.stack,
      });
      console.error('Error creating chart:', error);
    }
    return undefined;
  }, []);

  useEffect(() => {
    if (!chartRef.current) return;
    chartRef.current.applyOptions({
      ...mergeOptions(darkThemeOptions, options),
      width: containerRef.current?.clientWidth || width,
      height: containerRef.current?.clientHeight || height,
    });
  }, [height, options, width]);

  useEffect(() => {
    if (ref) {
      if (typeof ref === 'function') {
        ref(chartRef.current);
      } else {
        ref.current = chartRef.current;
      }
    }
  }, [ref]);

  return (
    <ChartContext.Provider value={chartInstance}>
      <div
        ref={containerRef}
        aria-label={ariaLabel || props['aria-label']}
        className={className}
        role={role}
        {...props}
      >
        {chartInstance && children}
      </div>
    </ChartContext.Provider>
  );
});

ChartContainer.displayName = 'ChartContainer';

ChartContainer.propTypes = {
  width: PropTypes.number,
  height: PropTypes.number,
  options: PropTypes.object,
  children: PropTypes.node,
  className: PropTypes.string,
  ariaLabel: PropTypes.string,
  monitoringName: PropTypes.string,
  role: PropTypes.string,
};

export default ChartContainer;
