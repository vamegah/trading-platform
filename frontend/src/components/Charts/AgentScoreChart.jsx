import React, { useMemo } from 'react';
import PropTypes from 'prop-types';
import { colors } from '../../utils/charts/theme';

const clamp = (value, min = 0, max = 100) => Math.max(min, Math.min(max, value));
const thresholdRatio = (value) => (value > 1 ? value / 100 : value);

/**
 * AgentScoreChart - SVG horizontal bar chart for agent scores and risk metrics.
 *
 * Values can be provided as 0-1 ratios or 0-100 percentages. The chart keeps
 * all labels as SVG text so the visual has an accessible text equivalent.
 */
function AgentScoreChart({
  data = [],
  width = 620,
  height,
  maxValue = 100,
  thresholdBuy = 0.68,
  thresholdSell = 0.38,
  showValues = true,
  title = 'Horizontal score chart',
  ...props
}) {
  const viewHeight = height || Math.max(150, data.length * 44 + 42);
  const padding = { top: 18, right: 72, bottom: 26, left: 150 };
  const chartWidth = Math.max(1, width - padding.left - padding.right);
  const barHeight = 20;
  const barGap = 22;
  const buyThreshold = thresholdRatio(thresholdBuy);
  const sellThreshold = thresholdRatio(thresholdSell);

  const getColor = (value, explicitColor) => {
    if (explicitColor) return explicitColor;
    const ratio = thresholdRatio(maxValue === 1 ? value : value / maxValue);
    if (ratio >= buyThreshold) return colors.up;
    if (ratio <= sellThreshold) return colors.down;
    return colors.warning;
  };

  const rows = useMemo(
    () =>
      data.map((item, index) => {
        const rawValue = Number(item.value || 0);
        const ratio = thresholdRatio(maxValue === 1 ? rawValue : rawValue / maxValue);
        const percent = clamp(ratio * 100);
        const y = padding.top + index * (barHeight + barGap);

        return {
          ...item,
          color: getColor(rawValue, item.color),
          displayValue: item.displayValue || `${Math.round(percent)}%`,
          percent,
          width: (percent / 100) * chartWidth,
          y,
        };
      }),
    [chartWidth, data, maxValue]
  );

  if (!data.length) {
    return (
      <svg
        aria-label="No chart data available"
        className="agent-score-chart"
        height="120"
        role="img"
        viewBox="0 0 620 120"
        width="100%"
        {...props}
      >
        <title>No data available</title>
        <rect className="chart-svg-bg" height="120" width="620" x="0" y="0" />
        <text className="chart-svg-muted" dominantBaseline="middle" textAnchor="middle" x="310" y="60">
          No data available
        </text>
      </svg>
    );
  }

  return (
    <svg
      aria-label={props['aria-label'] || title}
      className="agent-score-chart"
      height={viewHeight}
      role="img"
      viewBox={`0 0 ${width} ${viewHeight}`}
      width="100%"
      {...props}
    >
      <title>{title}</title>
      <rect className="chart-svg-bg" height={viewHeight} width={width} x="0" y="0" />
      {[25, 50, 75, 100].map((pct) => {
        const x = padding.left + (pct / 100) * chartWidth;
        return (
          <g key={`grid-${pct}`}>
            <line className="chart-svg-grid" x1={x} x2={x} y1={padding.top - 6} y2={viewHeight - padding.bottom} />
            <text className="chart-svg-axis" textAnchor="middle" x={x} y={viewHeight - 8}>
              {pct}%
            </text>
          </g>
        );
      })}

      {rows.map((bar) => (
        <g key={bar.label}>
          <text
            className="chart-svg-label"
            dominantBaseline="middle"
            textAnchor="end"
            x={padding.left - 12}
            y={bar.y + barHeight / 2}
          >
            {bar.label}
          </text>
          <rect
            className="agent-score-chart__track"
            height={barHeight}
            rx="4"
            width={chartWidth}
            x={padding.left}
            y={bar.y}
          />
          <rect
            data-agent-bar="true"
            fill={bar.color}
            height={barHeight}
            rx="4"
            width={bar.width}
            x={padding.left}
            y={bar.y}
          />
          {showValues && (
            <text
              className="chart-svg-value"
              dominantBaseline="middle"
              x={padding.left + Math.min(chartWidth + 8, bar.width + 8)}
              y={bar.y + barHeight / 2}
            >
              {bar.displayValue}
            </text>
          )}
        </g>
      ))}
    </svg>
  );
}

AgentScoreChart.propTypes = {
  data: PropTypes.arrayOf(
    PropTypes.shape({
      label: PropTypes.string.isRequired,
      value: PropTypes.number.isRequired,
      threshold: PropTypes.number,
      color: PropTypes.string,
      displayValue: PropTypes.string,
    })
  ),
  width: PropTypes.number,
  height: PropTypes.number,
  maxValue: PropTypes.number,
  thresholdBuy: PropTypes.number,
  thresholdSell: PropTypes.number,
  showValues: PropTypes.bool,
  title: PropTypes.string,
};

export default AgentScoreChart;
