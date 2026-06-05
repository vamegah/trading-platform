#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const zlib = require('zlib');

const root = path.resolve(__dirname, '..');
const evidenceDir = path.join(root, 'release-evidence');
const reportPath = path.join(evidenceDir, 'performance-report.json');
const distAssetsDir = path.join(root, 'dist', 'assets');

function read(relativePath) {
  return fs.readFileSync(path.join(root, relativePath), 'utf8');
}

function size(assetPath) {
  const buffer = fs.readFileSync(assetPath);
  return {
    rawBytes: buffer.length,
    gzipBytes: zlib.gzipSync(buffer).length,
  };
}

function kb(bytes) {
  return Number((bytes / 1024).toFixed(2));
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

if (!fs.existsSync(distAssetsDir)) {
  check('build-assets-exist', false, { path: path.relative(root, distAssetsDir) });
} else {
  check('build-assets-exist', true, { path: path.relative(root, distAssetsDir) });
  const assets = fs.readdirSync(distAssetsDir).map((file) => path.join(distAssetsDir, file));
  const jsAssets = assets.filter((asset) => asset.endsWith('.js'));
  const cssAssets = assets.filter((asset) => asset.endsWith('.css'));
  const jsTotals = jsAssets.map(size).reduce(
    (total, asset) => ({
      rawBytes: total.rawBytes + asset.rawBytes,
      gzipBytes: total.gzipBytes + asset.gzipBytes,
    }),
    { rawBytes: 0, gzipBytes: 0 }
  );
  const cssTotals = cssAssets.map(size).reduce(
    (total, asset) => ({
      rawBytes: total.rawBytes + asset.rawBytes,
      gzipBytes: total.gzipBytes + asset.gzipBytes,
    }),
    { rawBytes: 0, gzipBytes: 0 }
  );

  check('javascript-bundle-gzip-budget', jsTotals.gzipBytes <= 180 * 1024, {
    actualKb: kb(jsTotals.gzipBytes),
    budgetKb: 180,
  });
  check('javascript-bundle-raw-budget', jsTotals.rawBytes <= 700 * 1024, {
    actualKb: kb(jsTotals.rawBytes),
    budgetKb: 700,
  });
  check('css-bundle-gzip-budget', cssTotals.gzipBytes <= 30 * 1024, {
    actualKb: kb(cssTotals.gzipBytes),
    budgetKb: 30,
  });
}

const chartContainer = read('src/components/Charts/ChartContainer.jsx');
check('chart-container-cleanup', /chartRef\.current\.remove\(\)/.test(chartContainer));
check('chart-container-debounced-resize', /setTimeout\(\(\) => \{[\s\S]*\}, 100\)/.test(chartContainer));
check('chart-render-performance-monitoring', /recordChartPerformance/.test(chartContainer));

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
  const content = read(file);
  check(`${file}:no-inline-style-objects`, !/style=\{\{/.test(content));
}

check('backtest-no-random-fallback', !/Math\.random|Array\.from\(\{ length: 60/.test(read('src/components/BacktestViewer/BacktestViewerEnhanced.jsx')));
check('deterministic-sample-ohlcv', !/Math\.random/.test(read('src/utils/charts/formatters.js')));
check('runtime-sample-cap', /MAX_RECORDS = 75/.test(read('src/utils/charts/monitoring.js')));

const failed = checks.filter((item) => !item.passed);
const report = {
  name: 'chart-performance',
  generatedAt: new Date().toISOString(),
  status: failed.length ? 'failed' : 'passed',
  checks,
};

fs.writeFileSync(reportPath, `${JSON.stringify(report, null, 2)}\n`);

if (failed.length) {
  console.error(`Performance validation failed: ${failed.map((item) => item.name).join(', ')}`);
  process.exit(1);
}

console.log(`Performance validation passed (${checks.length} checks).`);
