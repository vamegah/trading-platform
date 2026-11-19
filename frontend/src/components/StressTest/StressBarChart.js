import PropTypes from 'prop-types';
import { CHART_THEME } from '../../styles/chart-theme';

const WIDTH = 680;
const GROUP_HEIGHT = 58;
const PAD = { top: 16, right: 130, bottom: 12, left: 70 };
const BAR_H = 16;

function stressedColor(position) {
  const pnl = Number(position.pnl ?? position.pnl_percent ?? 0);
  return pnl < 0 ? CHART_THEME.red : CHART_THEME.green;
}

/** Grouped SVG bars per position: current_value (neutral) vs stressed_value (red/green). */
export default function StressBarChart({ positions, ariaLabel }) {
  const height = PAD.top + positions.length * GROUP_HEIGHT + PAD.bottom;
  const chartWidth = WIDTH - PAD.left - PAD.right;
  const maxValue = Math.max(
    1,
    ...positions.flatMap((p) => [Number(p.current_value) || 0, Number(p.stressed_value) || 0])
  );
  const barWidth = (value) => Math.max(0, Math.min(1, (Number(value) || 0) / maxValue)) * chartWidth;

  return (
    <svg
      role="img"
      aria-label={ariaLabel || `Current versus stressed value for ${positions.length} positions`}
      viewBox={`0 0 ${WIDTH} ${height}`}
      width="100%"
    >
      <title>Stress test: current vs stressed value</title>
      {positions.map((p, i) => {
        const y = PAD.top + i * GROUP_HEIGHT;
        const pct = Number(p.pnl_percent) || 0;
        return (
          <g key={p.symbol}>
            <text
              x={PAD.left - 8}
              y={y + BAR_H + 4}
              textAnchor="end"
              fill={CHART_THEME.text}
              fontSize="12"
            >
              {p.symbol}
            </text>
            <rect
              data-bar="current"
              x={PAD.left}
              y={y}
              width={barWidth(p.current_value)}
              height={BAR_H}
              rx="3"
              fill={CHART_THEME.neutral}
            />
            <rect
              data-bar="stressed"
              x={PAD.left}
              y={y + BAR_H + 6}
              width={barWidth(p.stressed_value)}
              height={BAR_H}
              rx="3"
              fill={stressedColor(p)}
            />
            <text
              data-label="pnl-percent"
              x={PAD.left + barWidth(p.stressed_value) + 6}
              y={y + BAR_H + 6 + BAR_H - 4}
              fill={CHART_THEME.text}
              fontSize="11"
            >
              {`${pct.toFixed(1)}%`}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

StressBarChart.propTypes = {
  positions: PropTypes.arrayOf(
    PropTypes.shape({
      symbol: PropTypes.string.isRequired,
      current_value: PropTypes.number,
      stressed_value: PropTypes.number,
      pnl: PropTypes.number,
      pnl_percent: PropTypes.number,
    })
  ).isRequired,
  ariaLabel: PropTypes.string,
};
