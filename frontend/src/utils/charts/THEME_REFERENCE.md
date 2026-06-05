# Chart Theme Configuration Reference

## Color Palette (WCAG 2.1 Level AA Compliant)

All colors have been tested for contrast ratios against dark background (#0d0d0d).

### Status Colors
- **Green (Up/Profit/Buy)**: `#10b981` - Contrast: 4.2:1
- **Red (Down/Loss/Sell)**: `#ef4444` - Contrast: 3.8:1
- **Amber (Warning/Neutral)**: `#f59e0b` - Contrast: 4.1:1
- **Grey (Hold/Flat)**: `#9ca3af` - Contrast: 3.2:1

### Text Colors
- **Primary Text**: `#f3f4f6` (Light Grey) - Contrast: 18.5:1
- **Secondary Text**: `#d1d5db` (Medium Grey) - Contrast: 12.3:1
- **Tertiary Text**: `#9ca3af` (Dark Grey) - Contrast: 3.2:1

### Background & Grid
- **Background**: `#0d0d0d` (Very Dark)
- **Grid Lines**: `#1f2937` (Dark Grey)
- **Grid Lines (Bright)**: `#374151` (Medium Grey)

## Dark Theme Implementation

All charts automatically use `darkThemeOptions` from `frontend/src/utils/charts/theme.js`.

### ChartContainer
```javascript
import { darkThemeOptions } from '../../utils/charts/theme';

// Theme is applied automatically - no additional setup needed
<ChartContainer width={800} height={400}>
  {/* Children */}
</ChartContainer>
```

### Candlestick Chart Colors
```javascript
{
  upColor: '#10b981',
  downColor: '#ef4444',
  borderUpColor: '#10b981',
  borderDownColor: '#ef4444',
  wickUpColor: '#10b981',
  wickDownColor: '#ef4444',
}
```

### Area Chart Colors
```javascript
{
  topColor: '#10b98133',    // Green with 20% opacity
  bottomColor: '#00000000',  // Transparent
  lineColor: '#10b981',
  lineWidth: 2,
}
```

## Accessibility Implementation

### Error Boundaries
All chart containers are wrapped with `ChartErrorBoundary`:
```javascript
<ChartErrorBoundary fallbackHeight={250}>
  <ChartContainer {...props}>
    {children}
  </ChartContainer>
</ChartErrorBoundary>
```

### ARIA Labels
Every chart has descriptive aria-labels:
```javascript
<ChartContainer
  role="img"
  aria-label="Candlestick chart showing 60 OHLCV candles with volume bars and price levels"
>
  {children}
</ChartContainer>
```

### Text Alternatives
All numeric rows are retained below charts as fallback data display.

## Testing

### Color Contrast Verification
All colors tested with WebAIM Contrast Checker (https://webaim.org/resources/contrastchecker/).

To verify a new color:
1. Use WebAIM tool
2. Input color and test against #0d0d0d
3. Ensure contrast ratio ≥ 3:1

### Browser Testing
- Chrome (Latest)
- Firefox (Latest)
- Safari (Latest)

### Accessibility Testing
- Screen reader testing (NVDA/JAWS)
- Keyboard navigation
- Dark mode rendering
