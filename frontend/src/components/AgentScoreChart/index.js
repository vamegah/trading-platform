import React from 'react';
import { CHART_THEME } from '../../styles/chart-theme';
import './AgentScoreChart.css';

export const BUY_THRESHOLD = 0.68;
export const SELL_THRESHOLD = 0.38;

/** Green at >= 0.68, red at <= 0.38, neutral otherwise. */
export function scoreColor(score) {
  if (score >= BUY_THRESHOLD) return CHART_THEME.green;
  if (score <= SELL_THRESHOLD) return CHART_THEME.red;
  return CHART_THEME.neutral;
}

// Fixed viewBox units: the SVG scales to any container width.
const VIEW_W = 600;
const ROW_H = 32;
const GAP = 8;
const LABEL_W = 130;
const VALUE_W = 52;
const PAD = 12;
const TRACK_W = VIEW_W - LABEL_W - VALUE_W - PAD;

function fillRatio(value, maxValue) {
  const max = Number(maxValue) > 0 ? Number(maxValue) : 1;
  const ratio = Number(value) / max;
  if (!Number.isFinite(ratio) || ratio < 0) return 0;
  return Math.min(ratio, 1);
}

export default function AgentScoreChart({ bars = [], ariaLabel = 'Bar chart' }) {
  const svgH = bars.length * (ROW_H + GAP) - (bars.length ? GAP : 0) + PAD * 2;

  return (
    <svg
      role="img"
      aria-label={ariaLabel}
      className="agent-score-chart"
      viewBox={`0 0 ${VIEW_W} ${svgH}`}
      preserveAspectRatio="xMinYMin meet"
    >
      <title>{ariaLabel}</title>
      {bars.map(({ label, value, maxValue = 1, color }, i) => {
        const y = PAD + i * (ROW_H + GAP);
        const ratio = fillRatio(value, maxValue);
        const textY = y + ROW_H / 2;
        return (
          <g key={`${label}-${i}`} data-testid="agent-score-row">
            <text
              className="agent-score-chart__label"
              x={0}
              y={textY}
              dominantBaseline="middle"
            >
              {label}
            </text>
            <rect
              className="agent-score-chart__track"
              x={LABEL_W}
              y={y}
              width={TRACK_W}
              height={ROW_H}
              rx={4}
            />
            <rect
              className="agent-score-chart__fill"
              data-testid="agent-score-fill"
              x={LABEL_W}
              y={y}
              width={ratio * TRACK_W}
              height={ROW_H}
              rx={4}
              fill={color || CHART_THEME.neutral}
            />
            <text
              className="agent-score-chart__value"
              x={LABEL_W + TRACK_W + 8}
              y={textY}
              dominantBaseline="middle"
            >
              {Math.round(ratio * 100)}%
            </text>
          </g>
        );
      })}
    </svg>
  );
}
