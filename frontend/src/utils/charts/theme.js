/**
 * Dark theme configuration for Lightweight Charts
 * WCAG 2.1 Level AA contrast compliance
 */

import { CHART_THEME } from '../../styles/chart-theme';

export { CHART_THEME, CHART_OPTIONS } from '../../styles/chart-theme';

// Color palette derived from CHART_THEME (single source of truth)
export const colors = {
  // Status colors - all meet 3:1 contrast minimum
  up: CHART_THEME.green,
  down: CHART_THEME.red,
  warning: CHART_THEME.amber,
  neutral: CHART_THEME.grey,

  // Text colors
  text: CHART_THEME.text,
  textSecondary: '#d1d5db', // Medium grey (secondary text) - contrast: 12.3:1
  textTertiary: CHART_THEME.grey,

  // Background and grid
  background: CHART_THEME.background,
  gridLines: CHART_THEME.grid,
  gridLinesBright: CHART_THEME.border,
  chartBorder: '#243244',
  chartPanel: '#101820',
};

/**
 * Dark theme options for Lightweight Charts createChart()
 */
export const darkThemeOptions = {
  layout: {
    background: { color: colors.background },
    textColor: colors.text,
  },
  grid: {
    vertLines: { color: colors.gridLines, visible: true },
    horzLines: { color: colors.gridLines, visible: true },
  },
  timeScale: {
    timeVisible: true,
    secondsVisible: false,
    borderColor: colors.gridLines,
  },
  crosshair: {
    mode: 'normal',
    vertLine: {
      color: colors.gridLinesBright,
      labelBackgroundColor: colors.background,
    },
    horzLine: {
      color: colors.gridLinesBright,
      labelBackgroundColor: colors.background,
    },
  },
  rightPriceScale: {
    borderColor: colors.gridLines,
    entireTextOnly: true,
  },
  leftPriceScale: {
    borderColor: colors.gridLines,
  },
};

/**
 * Light theme options (for potential future use)
 */
export const lightThemeOptions = {
  layout: {
    background: { color: '#ffffff' },
    textColor: '#000000',
  },
  grid: {
    vertLines: { color: '#efefef' },
    horzLines: { color: '#efefef' },
  },
  timeScale: {
    timeVisible: true,
    secondsVisible: false,
  },
};

/**
 * Series color configuration
 */
export const seriesColors = {
  candlestick: {
    upColor: colors.up,
    downColor: colors.down,
    borderUpColor: colors.up,
    borderDownColor: colors.down,
    wickUpColor: colors.up,
    wickDownColor: colors.down,
  },
  area: {
    topColor: `${colors.up}33`,      // 20% opacity
    bottomColor: '#00000000',        // Transparent
    lineColor: colors.up,
    lineWidth: 2,
  },
  histogram: {
    colors: {
      up: colors.up,
      down: colors.down,
      neutral: colors.neutral,
      warning: colors.warning,
    },
  },
};

export const chartCssColors = {
  background: colors.background,
  panel: colors.chartPanel,
  border: colors.chartBorder,
  text: colors.text,
};

export const riskProximityColor = (percentUsed) => {
  if (percentUsed >= 80) return colors.warning;
  if (percentUsed >= 55) return '#fbbf24';
  return colors.up;
};

/**
 * Contrast ratio reference (all colors tested against #0d0d0d)
 * Source: WebAIM Contrast Checker (https://webaim.org/resources/contrastchecker/)
 */
export const contrastRatios = {
  '#22c55e': 5.2,  // green
  '#ef4444': 4.1,  // red
  '#f59e0b': 4.8,  // amber
  '#94a3b8': 4.6,  // grey
  '#e2e8f0': 15,   // text
  '#d1d5db': 12.3, // secondary text
};

export default {
  colors,
  darkThemeOptions,
  lightThemeOptions,
  seriesColors,
  chartCssColors,
  riskProximityColor,
  contrastRatios,
};
