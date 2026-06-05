#!/usr/bin/env node

import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const evidenceDir = join(root, 'release-evidence');
const reportPath = join(evidenceDir, 'visual-report.json');

const read = (relativePath) => readFileSync(join(root, relativePath), 'utf8');
const checks = [];

function check(name, passed, details = {}) {
  checks.push({
    name,
    passed: Boolean(passed),
    ...details,
  });
}

mkdirSync(evidenceDir, { recursive: true });

const css = read('src/index.css');
check('chart-dark-background', /\.chart-frame[\s\S]*background: #0d0d0d/.test(css));
check('chart-frame-price-size', /\.chart-frame--price/.test(css));
check('chart-frame-equity-size', /\.chart-frame--equity/.test(css));
check('chart-frame-risk-size', /\.chart-frame--risk/.test(css));
check('responsive-analysis-grid', /@media \(max-width: 920px\)[\s\S]*\.analysis-grid[\s\S]*grid-template-columns: 1fr/.test(css));
check('responsive-feedback-grid', /@media \(max-width: 920px\)[\s\S]*\.feedback-grid[\s\S]*grid-template-columns: 1fr/.test(css));
check('svg-label-classes', /\.chart-svg-label/.test(css) && /\.chart-svg-value/.test(css));

const chartFiles = [
  'src/components/Charts/AgentScoreChart.jsx',
  'src/components/StockDeepDive/StockDeepDiveChart.jsx',
  'src/components/ExplainabilityPanel/ExplainabilityPanelEnhanced.jsx',
  'src/components/BacktestViewer/BacktestViewerEnhanced.jsx',
  'src/components/PortfolioHealth/PortfolioHealthEnhanced.jsx',
  'src/components/StressTest/StressTestEnhanced.jsx',
  'src/components/DiscoveryScanner/DiscoveryScannerEnhanced.jsx',
];

for (const file of chartFiles) {
  check(`${file}:no-inline-style-objects`, !/style=\{\{/.test(read(file)), { file });
}

check('agent-score-svg-responsive', /width="100%"/.test(read('src/components/Charts/AgentScoreChart.jsx')));
check('stress-svg-responsive', /width="100%"/.test(read('src/components/StressTest/StressTestEnhanced.jsx')));
check('scanner-confidence-svg-responsive', /viewBox="0 0 100 8"/.test(read('src/components/DiscoveryScanner/DiscoveryScannerEnhanced.jsx')));
check('stock-deep-dive-text-rows-preserved', /<div className="row">/.test(read('src/components/StockDeepDive/StockDeepDiveChart.jsx')));
check('backtest-paper-execute-preserved', /Paper execute/.test(read('src/components/BacktestViewer/BacktestViewerEnhanced.jsx')));

const failed = checks.filter((item) => !item.passed);
const report = {
  name: 'chart-visual',
  generatedAt: new Date().toISOString(),
  status: failed.length ? 'failed' : 'passed',
  checks,
};

writeFileSync(reportPath, `${JSON.stringify(report, null, 2)}\n`);

if (failed.length) {
  console.error(`Visual validation failed: ${failed.map((item) => item.name).join(', ')}`);
  process.exit(1);
}

console.log(`Visual validation passed (${checks.length} checks).`);
