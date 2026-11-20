#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const zlib = require('zlib');
const { resizeDebounceMs, disposesChartOnUnmount } = require('./chart-gate-helpers.cjs');

const root = path.resolve(__dirname, '..');
const evidenceDir = path.join(root, 'release-evidence');
const reportPath = path.join(evidenceDir, 'performance-report.json');
const distAssetsDir = path.join(root, 'dist', 'assets');

function read(relativePath) {
  return relativePath.split('|').map((part) => fs.readFileSync(path.join(root, part), 'utf8')).join('\n');
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

const chartContainer = read('src/components/ChartContainer/index.js');
const resizeDebounce = resizeDebounceMs(chartContainer);
check('chart-container-cleanup', disposesChartOnUnmount(chartContainer));
check('chart-container-debounced-resize', resizeDebounce > 0 && resizeDebounce <= 100, {
  actualMs: resizeDebounce,
  budgetMs: 100,
});
check('chart-render-performance-monitoring', /recordChartPerformance/.test(chartContainer));

const chartTaskFiles = [
  'src/components/ChartContainer/index.js',
  'src/components/AgentScoreChart/index.js',
  'src/components/ChartErrorBoundary/index.js',
  'src/components/StockDeepDive/StockDeepDiveChart.jsx',
  'src/components/ExplainabilityPanel/index.js',
  'src/components/BacktestViewer/index.js',
  'src/components/PortfolioHealth/index.js',
  'src/components/StressTest/index.js|src/components/StressTest/StressBarChart.js|src/components/StressTest/ScenarioSelector.js',
  'src/components/DiscoveryScanner/index.js',
];

for (const file of chartTaskFiles) {
  const content = read(file);
  check(`${file}:no-inline-style-objects`, !/style=\{\{/.test(content));
}

check('backtest-no-random-fallback', !/Math\.random|Array\.from\(\{ length: 60/.test(read('src/components/BacktestViewer/index.js')));
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
