#!/usr/bin/env node

import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const repoRoot = join(root, '..');
const evidenceDir = join(root, 'release-evidence');
const reportPath = join(evidenceDir, 'chart-release-evidence.json');

function runNpmScript(script) {
  if (process.platform === 'win32') {
    return spawnSync('cmd.exe', ['/d', '/s', '/c', `npm --prefix frontend run ${script}`], {
      cwd: repoRoot,
      stdio: 'inherit',
    });
  }

  return spawnSync('npm', ['--prefix', 'frontend', 'run', script], {
    cwd: repoRoot,
    stdio: 'inherit',
  });
}

mkdirSync(evidenceDir, { recursive: true });

const steps = [
  { name: 'chart task verifier', script: 'test' },
  { name: 'production build', script: 'build' },
  { name: 'accessibility validation', script: 'validate:accessibility' },
  { name: 'performance validation', script: 'validate:performance' },
  { name: 'data validation', script: 'validate:data' },
  { name: 'visual validation', script: 'validate:visual' },
  { name: 'release smoke validation', script: 'smoke:release' },
];

const results = [];

for (const step of steps) {
  const startedAt = new Date().toISOString();
  console.log(`\n[chart-release] ${step.name}`);
  const result = runNpmScript(step.script);

  results.push({
    name: step.name,
    command: `npm --prefix frontend run ${step.script}`,
    startedAt,
    finishedAt: new Date().toISOString(),
    status: result.status === 0 && !result.error ? 'passed' : 'failed',
    exitCode: result.status,
    error: result.error?.message,
  });
}

const reportNames = [
  'accessibility-report.json',
  'performance-report.json',
  'data-report.json',
  'visual-report.json',
  'smoke-report.json',
];

const reports = Object.fromEntries(
  reportNames.map((name) => {
    const file = join(evidenceDir, name);
    return [name, existsSync(file) ? JSON.parse(readFileSync(file, 'utf8')) : null];
  })
);

const failed = results.filter((result) => result.status !== 'passed');
const releaseEvidence = {
  name: 'chart-release-evidence',
  generatedAt: new Date().toISOString(),
  status: failed.length ? 'failed' : 'passed',
  checklist: {
    preDeployment: {
      acceptanceCriteria: 'covered by npm run test',
      verificationTests: 'covered by npm run test:validate',
      codeReview: 'CI uploads release evidence for reviewer signoff',
      consoleErrors: 'covered by build and smoke gates',
      performance: 'covered by performance-report.json',
      accessibility: 'covered by accessibility-report.json',
    },
    deployment: {
      frontendBuild: 'covered by production build step',
      stagingArtifacts: 'covered by deploy workflow artifact upload',
      stagingSmoke: 'covered by smoke-chart-release.mjs and deployed gateway smoke when configured',
      productionCharts: 'covered by deploy workflow release gate before production approval',
      monitoring: 'covered by chart monitoring storage and sendBeacon hooks',
    },
    postDeployment: {
      userFeedback: 'covered by ChartFeedbackPanel and chart-feedback storage',
      errorRates: 'covered by chart-render-errors storage and sendBeacon hooks',
      performanceMetrics: 'covered by chart-performance-samples storage and release evidence',
      accessibilityRerun: 'covered by npm run validate:accessibility',
    },
  },
  steps: results,
  reports,
};

writeFileSync(reportPath, `${JSON.stringify(releaseEvidence, null, 2)}\n`);

if (failed.length) {
  console.error(`Chart release evidence failed: ${failed.map((item) => item.name).join(', ')}`);
  process.exit(1);
}

console.log(`\nChart release evidence passed. Report: ${reportPath}`);
