#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const evidenceDir = path.join(root, 'release-evidence');
const reportPath = path.join(evidenceDir, 'accessibility-report.json');
const minContrastRatio = 3;

function read(relativePath) {
  return fs.readFileSync(path.join(root, relativePath), 'utf8');
}

function ensureEvidenceDir() {
  fs.mkdirSync(evidenceDir, { recursive: true });
}

function luminance(hex) {
  const values = hex
    .replace('#', '')
    .match(/.{2}/g)
    .map((channel) => {
      const value = parseInt(channel, 16) / 255;
      return value <= 0.03928 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
    });

  return 0.2126 * values[0] + 0.7152 * values[1] + 0.0722 * values[2];
}

function contrastRatio(colorA, colorB) {
  const [light, dark] = [luminance(colorA), luminance(colorB)].sort((left, right) => right - left);
  return (light + 0.05) / (dark + 0.05);
}

const checks = [];

function check(name, passed, details = {}) {
  checks.push({
    name,
    passed: Boolean(passed),
    ...details,
  });
}

const theme = read('src/utils/charts/theme.js');
const css = read('src/index.css');
const palette = {
  up: '#10b981',
  down: '#ef4444',
  warning: '#f59e0b',
  neutral: '#9ca3af',
  text: '#f3f4f6',
  textSecondary: '#d1d5db',
};

for (const [name, color] of Object.entries(palette)) {
  const ratio = contrastRatio('#0d0d0d', color);
  check(`contrast:${name}`, ratio >= minContrastRatio && theme.includes(color), {
    color,
    ratio: Number(ratio.toFixed(2)),
    required: minContrastRatio,
  });
}

const surfaces = [
  {
    name: 'StockDeepDive',
    file: 'src/components/StockDeepDive/StockDeepDiveChart.jsx',
    fallback: /Price data unavailable|ChartDataTable/,
    errorBoundary: true,
  },
  {
    name: 'ExplainabilityPanel',
    file: 'src/components/ExplainabilityPanel/ExplainabilityPanelEnhanced.jsx',
    fallback: /Distribution data unavailable|Agent scores unavailable|ChartDataTable/,
    errorBoundary: true,
  },
  {
    name: 'BacktestViewer',
    file: 'src/components/BacktestViewer/BacktestViewerEnhanced.jsx',
    fallback: /Equity curve data unavailable|ChartDataTable/,
    errorBoundary: true,
  },
  {
    name: 'PortfolioHealth',
    file: 'src/components/PortfolioHealth/PortfolioHealthEnhanced.jsx',
    fallback: /Risk data unavailable|ChartDataTable/,
    errorBoundary: true,
  },
  {
    name: 'StressTest',
    file: 'src/components/StressTest/StressTestEnhanced.jsx',
    fallback: /Stress test data unavailable|ChartDataTable/,
    errorBoundary: true,
  },
  {
    name: 'DiscoveryScanner',
    file: 'src/components/DiscoveryScanner/DiscoveryScannerEnhanced.jsx',
    fallback: /Run a scan to rank the universe\./,
    errorBoundary: false,
  },
];

for (const surface of surfaces) {
  const content = read(surface.file);
  check(`${surface.name}:aria-label`, /aria-label/.test(content), { file: surface.file });
  check(`${surface.name}:role-img`, /role="img"/.test(content), { file: surface.file });
  check(`${surface.name}:text-fallback`, surface.fallback.test(content), { file: surface.file });
  if (surface.errorBoundary) {
    check(`${surface.name}:error-boundary`, /ChartErrorBoundary/.test(content), { file: surface.file });
  }
}

const chartDataTable = read('src/components/Charts/ChartDataTable.jsx');
const errorBoundary = read('src/components/Charts/ChartErrorBoundary.jsx');
const monitoring = read('src/utils/charts/monitoring.js');

check('screen-reader-data-table', /className="sr-only"/.test(chartDataTable) && /\.sr-only/.test(css));
check('error-boundary-alert', /role="alert"/.test(errorBoundary));
check('error-boundary-monitoring', /recordChartError/.test(errorBoundary) && /chart-render-errors/.test(monitoring));
check('feedback-capture', /chart-feedback/.test(monitoring) && /recordChartFeedback/.test(monitoring));

ensureEvidenceDir();

const failed = checks.filter((item) => !item.passed);
const report = {
  name: 'chart-accessibility',
  generatedAt: new Date().toISOString(),
  status: failed.length ? 'failed' : 'passed',
  checks,
};

fs.writeFileSync(reportPath, `${JSON.stringify(report, null, 2)}\n`);

if (failed.length) {
  console.error(`Accessibility validation failed: ${failed.map((item) => item.name).join(', ')}`);
  process.exit(1);
}

console.log(`Accessibility validation passed (${checks.length} checks).`);
