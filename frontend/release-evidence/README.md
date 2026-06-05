# Chart Release Evidence

`npm run test:validate` writes release gate output here:

- `accessibility-report.json`
- `performance-report.json`
- `data-report.json`
- `visual-report.json`
- `smoke-report.json`
- `chart-release-evidence.json`

The JSON files are generated artifacts. CI and deploy workflows upload them for review.
