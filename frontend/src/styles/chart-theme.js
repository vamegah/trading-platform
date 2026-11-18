/**
 * Single source of truth for chart colors and base options.
 * Every semantic color has >= 3:1 contrast against the #0d0d0d background.
 */
export const CHART_THEME = {
  background: '#0d0d0d',
  text: '#e2e8f0',
  grid: '#1e293b',
  border: '#334155',
  // semantic colors
  green: '#22c55e',
  red: '#ef4444',
  amber: '#f59e0b',
  grey: '#94a3b8',
  orange: '#f97316',
  neutral: '#60a5fa',
};

export const CHART_OPTIONS = {
  layout: {
    background: { color: CHART_THEME.background },
    textColor: CHART_THEME.text,
  },
  grid: {
    vertLines: { color: CHART_THEME.grid },
    horzLines: { color: CHART_THEME.grid },
  },
  timeScale: { borderColor: CHART_THEME.border },
};
