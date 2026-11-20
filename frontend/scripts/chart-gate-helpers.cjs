// Shared source-level helpers for the chart release gates.

/**
 * Returns the delay (ms) of the resize debounce `setTimeout(() => { ... }, delay)`
 * inside a ResizeObserver callback, resolving a named constant if one is used.
 * Returns NaN when no debounced ResizeObserver resize is found.
 */
function resizeDebounceMs(source) {
  const match = source.match(/new ResizeObserver\([\s\S]*?setTimeout\(\(\) => \{[\s\S]*?applyOptions[\s\S]*?\},\s*([A-Za-z_$][\w$]*|\d+)\s*\)/);
  if (!match) return Number.NaN;
  if (/^\d+$/.test(match[1])) return Number(match[1]);
  const constant = source.match(new RegExp(`const ${match[1]}\\s*=\\s*(\\d+)`));
  return constant ? Number(constant[1]) : Number.NaN;
}

/** True when the effect cleanup disposes the chart instance (chart.remove() or chartRef.current.remove()). */
function disposesChartOnUnmount(source) {
  return /return \(\) => \{[\s\S]*?\b(?:chart|chartRef\.current)\.remove\(\)/.test(source);
}

module.exports = { resizeDebounceMs, disposesChartOnUnmount };
