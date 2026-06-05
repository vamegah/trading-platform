#!/usr/bin/env node

const { spawnSync } = require('child_process');
const path = require('path');

const root = path.resolve(__dirname, '..', '..');
const node = process.execPath;
const result = spawnSync(node, ['frontend/scripts/generate-chart-release-evidence.mjs'], {
  cwd: root,
  stdio: 'inherit',
});

process.exit(result.status || 1);
