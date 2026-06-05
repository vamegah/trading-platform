#!/usr/bin/env node

import { existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const repoRoot = join(root, '..');
const evidenceDir = join(root, 'release-evidence');
const reportPath = join(evidenceDir, 'smoke-report.json');

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

const packageJson = JSON.parse(read('package.json'));
check(
  'chart-package-alias',
  packageJson.dependencies?.['@tradingview/lightweight-charts'] === 'npm:lightweight-charts@^5.2.0'
);
check('chart-package-installed', existsSync(join(root, 'node_modules', '@tradingview', 'lightweight-charts')));
check('vite-alias-configured', /"@tradingview\/lightweight-charts": "lightweight-charts"/.test(read('vite.config.js')));

const distDir = join(root, 'dist');
const assetDir = join(distDir, 'assets');
check('dist-index-exists', existsSync(join(distDir, 'index.html')));
check('dist-assets-exist', existsSync(assetDir) && readdirSync(assetDir).some((file) => file.endsWith('.js')));

const monitoring = read('src/utils/charts/monitoring.js');
const app = read('src/App.js');
check('chart-error-monitoring-enabled', /chart-render-errors/.test(monitoring) && /recordChartError/.test(read('src/components/Charts/ChartErrorBoundary.jsx')));
check('chart-performance-monitoring-enabled', /recordChartPerformance/.test(read('src/components/Charts/ChartContainer.jsx')));
check('chart-feedback-mounted', /ChartFeedbackPanel/.test(app) && /chart-feedback/.test(monitoring));
check('monitoring-send-beacon-fallback', /sendBeacon/.test(monitoring) && /localStorage/.test(monitoring));

for (const reportName of ['accessibility-report.json', 'performance-report.json', 'data-report.json', 'visual-report.json']) {
  check(`evidence:${reportName}`, existsSync(join(evidenceDir, reportName)));
}

const ci = readFileSync(join(repoRoot, '.github', 'workflows', 'ci.yml'), 'utf8');
const deploy = readFileSync(join(repoRoot, '.github', 'workflows', 'deploy.yml'), 'utf8');
check('ci-runs-frontend-release-gate', /npm --prefix frontend run test:validate/.test(ci));
check('deploy-runs-frontend-release-gate', /npm --prefix frontend run test:validate/.test(deploy));
check('deploy-uploads-chart-evidence', /frontend\/release-evidence\/\*\.json/.test(deploy));

const failed = checks.filter((item) => !item.passed);
const report = {
  name: 'chart-release-smoke',
  generatedAt: new Date().toISOString(),
  status: failed.length ? 'failed' : 'passed',
  checks,
};

writeFileSync(reportPath, `${JSON.stringify(report, null, 2)}\n`);

if (failed.length) {
  console.error(`Release smoke validation failed: ${failed.map((item) => item.name).join(', ')}`);
  process.exit(1);
}

console.log(`Release smoke validation passed (${checks.length} checks).`);
