/**
 * Chart utilities for data formatting and helpers
 */

/**
 * Format candlestick OHLCV data for Lightweight Charts
 * @param {Array} data - Raw OHLCV data points
 * @returns {Array} - Formatted for CandlestickSeries
 */
export const formatCandleData = (data = []) => {
  if (!Array.isArray(data)) return [];
  return data.map((point, index) => ({
    time: point.time ?? point.date ?? index,
    open: Number(point.open ?? point.o ?? 0),
    high: Number(point.high ?? point.h ?? 0),
    low: Number(point.low ?? point.l ?? 0),
    close: Number(point.close ?? point.c ?? 0),
  }));
};

/**
 * Format volume data for histogram
 * @param {Array} data - Raw volume data
 * @returns {Array} - Formatted for HistogramSeries
 */
export const formatVolumeData = (data = []) => {
  if (!Array.isArray(data)) return [];
  return data.map((point, index) => ({
    time: point.time ?? point.date ?? index,
    value: Number(point.volume ?? point.v ?? 0),
    color: Number(point.close ?? point.c ?? 0) >= Number(point.open ?? point.o ?? 0) ? '#10b981' : '#ef4444',
  }));
};

/**
 * Format area chart data
 * @param {Array} data - Raw data points
 * @returns {Array} - Formatted for AreaSeries
 */
export const formatAreaData = (data = []) => {
  if (!Array.isArray(data)) return [];
  return data.map((point, index) => ({
    time: typeof point === 'number' ? index : point.time ?? point.date ?? index,
    value: typeof point === 'number' ? point : Number(point.value ?? point.price ?? 0),
  }));
};

/**
 * Generate horizontal price lines
 * @param {number} price - Price level
 * @param {string} color - Line color
 * @param {string} label - Line label
 * @returns {Object} - Price line options
 */
export const createPriceLine = (price, color = '#999999', label = 'Price') => ({
  price,
  color,
  lineWidth: 2,
  lineStyle: 1, // Solid
  axisLabelVisible: true,
  title: label,
});

/**
 * Determine color based on value and thresholds
 * @param {number} value - Value to evaluate
 * @param {number} thresholdBuy - Buy threshold (default 0.68)
 * @param {number} thresholdSell - Sell threshold (default 0.38)
 * @returns {string} - Color hex code
 */
export const getColorForValue = (value, thresholdBuy = 0.68, thresholdSell = 0.38) => {
  if (value >= thresholdBuy) return '#10b981'; // Green
  if (value <= thresholdSell) return '#ef4444'; // Red
  return '#f59e0b'; // Amber
};

/**
 * Format agent scores for AgentScoreChart
 * @param {Object} scores - Component scores from recommendation
 * @returns {Array} - Formatted data for AgentScoreChart
 */
export const formatAgentScores = (scores = {}) => {
  const agents = [
    'fundamentals',
    'technical',
    'news_sentiment',
    'macro',
    'alt_data',
    'debate',
    'tax'
  ];

  return agents.map(agent => ({
    label: agent.replace(/_/g, ' '),
    value: normalizeValue(Number(scores[agent] || 0), 1),
  }));
};

/**
 * Generate deterministic sample OHLCV data for testing and demo states
 * @param {number} count - Number of candles
 * @param {number} startPrice - Starting price
 * @returns {Array} - Sample OHLCV data
 */
export const generateSampleOHLCV = (count = 60, startPrice = 100) => {
  const data = [];
  let price = startPrice;

  for (let i = 0; i < count; i++) {
    const wave = Math.sin(i / 4) * 1.8 + Math.cos(i / 7) * 0.9;
    const drift = 0.16 + ((i % 9) - 4) * 0.09;
    const change = wave * 0.22 + drift;
    const open = price;
    const close = price + change;
    const high = Math.max(open, close) + 0.85 + (i % 5) * 0.17;
    const low = Math.min(open, close) - 0.75 - (i % 4) * 0.14;
    const volume = 5_000_000 + (i % 12) * 420_000 + Math.round(Math.abs(wave) * 180_000);

    data.push({
      time: i,
      open: parseFloat(open.toFixed(2)),
      high: parseFloat(high.toFixed(2)),
      low: parseFloat(low.toFixed(2)),
      close: parseFloat(close.toFixed(2)),
      volume,
    });

    price = close;
  }

  return data;
};

/**
 * Normalize values to 0-100 scale
 * @param {number} value - Value to normalize
 * @param {number} max - Maximum value
 * @returns {number} - Normalized 0-100
 */
export const normalizeValue = (value, max = 100) => {
  return Math.max(0, Math.min(100, (value / max) * 100));
};

export const probabilityScenarios = (distribution = {}) => [
  {
    key: 'up_5pct_20d',
    label: 'Up 5%+',
    value: Number(distribution.up_5pct_20d || 0),
    color: '#10b981',
  },
  {
    key: 'down_3pct_20d',
    label: 'Down 3%+',
    value: Number(distribution.down_3pct_20d || 0),
    color: '#ef4444',
  },
  {
    key: 'flat_20d',
    label: 'Flat',
    value: Number(distribution.flat_20d || 0),
    color: '#9ca3af',
  },
  {
    key: 'tail_loss_8pct_20d',
    label: 'Tail loss 8%+',
    value: Number(distribution.tail_loss_8pct_20d || 0),
    color: '#f59e0b',
  },
];

export const formatPercent = (value = 0, digits = 0) => `${(Number(value || 0) * 100).toFixed(digits)}%`;

export const formatCurrency = (value = 0) =>
  `$${Math.round(Number(value || 0)).toLocaleString()}`;
