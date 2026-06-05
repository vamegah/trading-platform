#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const root = path.resolve(__dirname, '..');
const evidenceDir = path.join(root, 'release-evidence');
const reportPath = path.join(evidenceDir, 'data-report.json');

function read(relativePath) {
  return fs.readFileSync(path.join(root, relativePath), 'utf8');
}

function loadFormatterExports() {
  const source = read('src/utils/charts/formatters.js')
    .replace(/export const /g, 'const ')
    .replace(/export default[\s\S]*$/m, '');
  const module = { exports: {} };
  const context = { console, module, exports: module.exports, Math, Number, parseFloat };

  vm.runInNewContext(
    `${source}
module.exports = {
  formatCandleData,
  formatVolumeData,
  formatAreaData,
  formatAgentScores,
  generateSampleOHLCV,
  normalizeValue,
  probabilityScenarios,
};`,
    context,
    { filename: 'formatters.js' }
  );

  return module.exports;
}

const checks = [];

function check(name, passed, details = {}) {
  checks.push({
    name,
    passed: Boolean(passed),
    ...details,
  });
}

fs.mkdirSync(evidenceDir, { recursive: true });

const formatters = loadFormatterExports();
const ohlcv = formatters.generateSampleOHLCV(60, 150);
const candles = formatters.formatCandleData(ohlcv);
const volume = formatters.formatVolumeData(ohlcv);

check('ohlcv-count', ohlcv.length >= 60, { count: ohlcv.length });
check(
  'ohlcv-shape',
  ohlcv.every(
    (candle) =>
      Number.isFinite(candle.open) &&
      Number.isFinite(candle.high) &&
      Number.isFinite(candle.low) &&
      Number.isFinite(candle.close) &&
      Number.isFinite(candle.volume)
  )
);
check(
  'ohlcv-price-bounds',
  ohlcv.every((candle) => candle.high >= candle.low && candle.high >= candle.open && candle.high >= candle.close)
);
check('formatted-candles-match-source-count', candles.length === ohlcv.length);
check('formatted-volume-match-source-count', volume.length === ohlcv.length);

const probabilities = {
  up_5pct_20d: 0.35,
  down_3pct_20d: 0.25,
  flat_20d: 0.3,
  tail_loss_8pct_20d: 0.1,
};
const probabilityRows = formatters.probabilityScenarios(probabilities);
const probabilityTotal = Object.values(probabilities).reduce((total, value) => total + value, 0);
check('probability-scenario-count', probabilityRows.length === 4, { count: probabilityRows.length });
check('probability-sum', Math.abs(probabilityTotal - 1) < 0.01, { total: probabilityTotal });
check('probability-values-in-range', probabilityRows.every((row) => row.value >= 0 && row.value <= 1));

const agentRows = formatters.formatAgentScores({
  fundamentals: 0.75,
  technical: 0.65,
  news_sentiment: 0.55,
  macro: 0.7,
  alt_data: 0.6,
  debate: 0.68,
  tax: 0.5,
});
check('agent-score-count', agentRows.length === 7, { count: agentRows.length });
check('agent-score-range', agentRows.every((row) => row.value >= 0 && row.value <= 100));

const areaRows = formatters.formatAreaData([100000, 101250, 99750]);
check('equity-curve-format', areaRows.length === 3 && areaRows.every((row) => row.value > 0));

check('stock-deep-dive-uses-sixty-candles', /generateSampleOHLCV\(60/.test(read('src/components/StockDeepDive/StockDeepDiveChart.jsx')));
check('explainability-uses-api-distribution', /probability_distribution/.test(read('src/components/ExplainabilityPanel/ExplainabilityPanelEnhanced.jsx')));
check('backtest-requires-real-equity-curve', /Equity curve data unavailable/.test(read('src/components/BacktestViewer/BacktestViewerEnhanced.jsx')));
check('portfolio-normalizes-risk-metrics', /normalizeMetric/.test(read('src/components/PortfolioHealth/PortfolioHealthEnhanced.jsx')));
check('stress-test-uses-scenarios-api', /getStressTestScenarios/.test(read('src/components/StressTest/StressTestEnhanced.jsx')));
check('scanner-clamps-confidence-values', /Math\.max\(0, Math\.min\(100/.test(read('src/components/DiscoveryScanner/DiscoveryScannerEnhanced.jsx')));

const failed = checks.filter((item) => !item.passed);
const report = {
  name: 'chart-data',
  generatedAt: new Date().toISOString(),
  status: failed.length ? 'failed' : 'passed',
  checks,
};

fs.writeFileSync(reportPath, `${JSON.stringify(report, null, 2)}\n`);

if (failed.length) {
  console.error(`Data validation failed: ${failed.map((item) => item.name).join(', ')}`);
  process.exit(1);
}

console.log(`Data validation passed (${checks.length} checks).`);
