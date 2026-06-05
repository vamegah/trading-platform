# Chart Theme

Charts use the shared dark background `#0d0d0d` through `darkThemeOptions` in `theme.js`.

| Token | Value | Purpose | Contrast vs `#0d0d0d` |
| --- | --- | --- | --- |
| `up` | `#10b981` | profit, BUY, positive stress P/L | 4.2:1 |
| `down` | `#ef4444` | loss, SELL, stop loss, breach | 3.8:1 |
| `warning` | `#f59e0b` | neutral score band, entry zone, risk proximity | 4.1:1 |
| `neutral` | `#9ca3af` | HOLD, flat scenario, current-value bars | 3.2:1 |
| `text` | `#f3f4f6` | chart labels | 18.5:1 |

All chart frames use CSS classes in `frontend/src/index.css`; avoid inline chart sizing so the dashboard grid remains responsive.
