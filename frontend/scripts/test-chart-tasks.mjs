import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const read = (relativePath) => readFileSync(join(root, relativePath), 'utf8');
const json = (relativePath) => JSON.parse(read(relativePath));

function assertContains(file, pattern, message) {
  assert.match(read(file), pattern, `${message} (${file})`);
}

function assertNotContains(file, pattern, message) {
  assert.doesNotMatch(read(file), pattern, `${message} (${file})`);
}

function contrastRatio(hexA, hexB) {
  const rgb = (hex) =>
    hex
      .replace('#', '')
      .match(/.{2}/g)
      .map((value) => parseInt(value, 16) / 255)
      .map((value) => (value <= 0.03928 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4));
  const luminance = ([red, green, blue]) => 0.2126 * red + 0.7152 * green + 0.0722 * blue;
  const [light, dark] = [luminance(rgb(hexA)), luminance(rgb(hexB))].sort((a, b) => b - a);
  return (light + 0.05) / (dark + 0.05);
}

const packageJson = json('package.json');
assert.equal(
  packageJson.dependencies['@tradingview/lightweight-charts'],
  'npm:lightweight-charts@^5.2.0',
  'TradingView Lightweight Charts alias must be declared'
);
assert.equal(packageJson.scripts.test, 'cd .. && node frontend/scripts/test-chart-tasks.mjs', 'npm run test must be available');
assert.equal(
  packageJson.scripts['test:validate'],
  'cd .. && node frontend/scripts/generate-chart-release-evidence.mjs',
  'npm run test:validate must generate release evidence'
);
assert.equal(
  packageJson.scripts['smoke:release'],
  'cd .. && node frontend/scripts/smoke-chart-release.mjs',
  'npm run smoke:release must be available'
);

for (const forbidden of ['chart.js', 'recharts', 'd3']) {
  assert.ok(!packageJson.dependencies[forbidden], `${forbidden} must not be introduced`);
}

assertContains('vite.config.js', /"@tradingview\/lightweight-charts": "lightweight-charts"/, 'Vite must resolve the chart alias');
assertContains('src/components/Charts/ChartContainer.jsx', /createChart/, 'ChartContainer must create charts');
assertContains('src/components/Charts/ChartContainer.jsx', /chartRef\.current\.remove\(\)/, 'ChartContainer must clean up charts');
assertContains('src/components/Charts/ChartContainer.jsx', /setTimeout\(\(\) => \{[\s\S]*\}, 100\)/, 'ChartContainer must debounce resize at 100 ms');
assertContains('src/components/Charts/ChartContainer.jsx', /recordChartPerformance/, 'ChartContainer must record render timing');
assertContains('src/components/Charts/ChartErrorBoundary.jsx', /recordChartError/, 'Chart errors must be monitored');
assertContains('src/utils/charts/monitoring.js', /chart-render-errors/, 'Chart error storage key must exist');
assertContains('src/utils/charts/monitoring.js', /chart-performance-samples/, 'Chart performance storage key must exist');
assertContains('src/utils/charts/monitoring.js', /chart-feedback/, 'Chart feedback storage key must exist');
assertContains('src/App.js', /ChartFeedbackPanel/, 'Chart feedback panel must be mounted');
assertContains('src/hooks/useChartSeries.js', /chart\.addSeries/, 'useChartSeries must use the v5 addSeries API');
assertContains('src/hooks/useChartSeries.js', /CandlestickSeries/, 'useChartSeries must support candlesticks');
assertContains('src/hooks/useChartSeries.js', /HistogramSeries/, 'useChartSeries must support histograms');
assertContains('src/hooks/useChartSeries.js', /AreaSeries/, 'useChartSeries must support area charts');
assertContains('src/hooks/useChartSeries.js', /LineSeries/, 'useChartSeries must support line charts');
assertContains('src/hooks/useChartSeries.js', /createSeriesMarkers/, 'useChartSeries must support trade markers');

const chartTaskFiles = [
  'src/components/Charts/ChartContainer.jsx',
  'src/components/Charts/AgentScoreChart.jsx',
  'src/components/Charts/ChartErrorBoundary.jsx',
  'src/components/StockDeepDive/StockDeepDiveChart.jsx',
  'src/components/ExplainabilityPanel/ExplainabilityPanelEnhanced.jsx',
  'src/components/BacktestViewer/BacktestViewerEnhanced.jsx',
  'src/components/PortfolioHealth/PortfolioHealthEnhanced.jsx',
  'src/components/StressTest/StressTestEnhanced.jsx',
  'src/components/DiscoveryScanner/DiscoveryScannerEnhanced.jsx',
];

for (const file of chartTaskFiles) {
  assertNotContains(file, /style=\{\{/, 'Chart task files should use CSS classes instead of inline style objects');
}

assertContains('src/components/StockDeepDive/StockDeepDiveChart.jsx', /generateSampleOHLCV\(60/, 'StockDeepDive must render at least 60 OHLCV candles');
assertContains('src/components/StockDeepDive/StockDeepDiveChart.jsx', /Price data unavailable/, 'StockDeepDive must expose empty-data fallback');
assertContains('src/components/StockDeepDive/StockDeepDiveChart.jsx', /Entry Low/, 'StockDeepDive must create entry low line');
assertContains('src/components/StockDeepDive/StockDeepDiveChart.jsx', /Entry High/, 'StockDeepDive must create entry high line');
assertContains('src/components/StockDeepDive/StockDeepDiveChart.jsx', /Stop Loss/, 'StockDeepDive must create stop-loss line');
assertContains('src/components/StockDeepDive/StockDeepDiveChart.jsx', /Take Profit/, 'StockDeepDive must create take-profit line');

assertContains('src/components/ExplainabilityPanel/ExplainabilityPanelEnhanced.jsx', /ProbabilityDistributionChart/, 'Explainability must include probability chart');
assertContains('src/components/ExplainabilityPanel/ExplainabilityPanelEnhanced.jsx', /Distribution data unavailable/, 'Explainability must expose distribution fallback');
assertContains('src/components/ExplainabilityPanel/ExplainabilityPanelEnhanced.jsx', /Agent scores unavailable/, 'Explainability must expose agent score fallback');

assertContains('src/components/BacktestViewer/BacktestViewerEnhanced.jsx', /setSeriesMarkers/, 'BacktestViewer must set trade markers');
assertContains('src/components/BacktestViewer/BacktestViewerEnhanced.jsx', /arrowUp/, 'BacktestViewer must render BUY markers');
assertContains('src/components/BacktestViewer/BacktestViewerEnhanced.jsx', /arrowDown/, 'BacktestViewer must render SELL markers');
assertContains('src/components/BacktestViewer/BacktestViewerEnhanced.jsx', /Equity curve data unavailable/, 'BacktestViewer must expose missing equity fallback');
assertNotContains('src/components/BacktestViewer/BacktestViewerEnhanced.jsx', /Math\.random|Array\.from\(\{ length: 60/, 'BacktestViewer must not hide missing equity with random fallback data');

assertContains('src/components/PortfolioHealth/PortfolioHealthEnhanced.jsx', /Risk data unavailable/, 'PortfolioHealth must expose risk fallback');
assertContains('src/components/PortfolioHealth/PortfolioHealthEnhanced.jsx', /Risk breach - position trading disabled/, 'PortfolioHealth must expose kill-switch breach label');

assertContains('src/services/api.js', /getStressTestScenarios/, 'API service must expose stress-test scenarios');
assertContains('src/components/StressTest/StressTestEnhanced.jsx', /getStressTestScenarios/, 'StressTest must load scenarios from API');
assertContains('src/components/StressTest/StressTestEnhanced.jsx', /Stress test data unavailable/, 'StressTest must expose empty-data fallback');
assertNotContains('src/components/StressTest/StressTestEnhanced.jsx', /mockScenarios|In production, this would call/, 'StressTest must not use hardcoded scenario data');

assertContains('src/components/DiscoveryScanner/DiscoveryScannerEnhanced.jsx', /▲/, 'DiscoveryScanner must render BUY directional indicator');
assertContains('src/components/DiscoveryScanner/DiscoveryScannerEnhanced.jsx', /▼/, 'DiscoveryScanner must render SELL directional indicator');
assertContains('src/components/DiscoveryScanner/DiscoveryScannerEnhanced.jsx', /—/, 'DiscoveryScanner must render HOLD directional indicator');
assertContains('src/components/DiscoveryScanner/DiscoveryScannerEnhanced.jsx', /data-confidence-bar/, 'DiscoveryScanner must render confidence bars');
assertContains('src/components/DiscoveryScanner/DiscoveryScannerEnhanced.jsx', /Run a scan to rank the universe\./, 'DiscoveryScanner must preserve empty placeholder');

assertContains('src/index.css', /\.chart-frame/, 'Chart sizing must be class-based');
assertContains('src/index.css', /\.sr-only/, 'Hidden chart data tables must be available');
assertContains('src/components/Charts/ChartDataTable.jsx', /className="sr-only"/, 'ChartDataTable must render hidden data tables');

const theme = read('src/utils/charts/theme.js');
for (const color of ['#10b981', '#ef4444', '#f59e0b', '#9ca3af', '#f3f4f6']) {
  assert.ok(contrastRatio('#0d0d0d', color) >= 3, `${color} must meet 3:1 contrast against chart background`);
  assert.ok(theme.includes(color), `${color} must be documented in theme.js`);
}

console.log('Chart task verification passed.');
