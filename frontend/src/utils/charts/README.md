# Chart Utilities

Utility helpers for the dashboard chart layer.

- `theme.js`: shared dark theme, WCAG contrast references, and chart color constants.
- `formatters.js`: transforms OHLCV, volume, area, probability, and score data into chart-ready shapes.
- `THEME_REFERENCE.md` and `theme.md`: palette and accessibility notes.

Example:

```javascript
import { formatCandleData, probabilityScenarios } from '../../utils/charts/formatters';
import { colors, darkThemeOptions } from '../../utils/charts/theme';
```

The sample OHLCV generator is deterministic so chart tests can verify data without unstable random output.
