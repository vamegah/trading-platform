const STORAGE_KEYS = {
  errors: 'chart-render-errors',
  performance: 'chart-performance-samples',
  feedback: 'chart-feedback',
};

const MAX_RECORDS = 75;

function browserWindow() {
  return typeof window !== 'undefined' ? window : null;
}

function nowIso() {
  return new Date().toISOString();
}

function readRecords(key) {
  const currentWindow = browserWindow();
  if (!currentWindow?.localStorage) return [];

  try {
    const parsed = JSON.parse(currentWindow.localStorage.getItem(key) || '[]');
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeRecords(key, records) {
  const currentWindow = browserWindow();
  if (!currentWindow?.localStorage) return;

  currentWindow.localStorage.setItem(key, JSON.stringify(records.slice(-MAX_RECORDS)));
}

function publish(record) {
  const currentWindow = browserWindow();
  if (!currentWindow?.navigator?.sendBeacon) return;

  try {
    const body = new Blob([JSON.stringify(record)], { type: 'application/json' });
    currentWindow.navigator.sendBeacon('/chart-monitoring', body);
  } catch {
    // Local storage remains the source of truth when sendBeacon is unavailable.
  }
}

function appendRecord(key, record) {
  const enriched = {
    ...record,
    at: record.at || nowIso(),
    url: browserWindow()?.location?.href || '',
  };

  writeRecords(key, [...readRecords(key), enriched]);
  publish(enriched);
  return enriched;
}

export function recordChartError({ component = 'unknown', message = '', stack = '', errorInfo = '' } = {}) {
  return appendRecord(STORAGE_KEYS.errors, {
    type: 'chart_error',
    component,
    message: String(message || 'Chart rendering error'),
    stack: String(stack || ''),
    errorInfo: String(errorInfo || ''),
  });
}

export function recordChartPerformance({ component = 'unknown', durationMs = 0, metadata = {} } = {}) {
  return appendRecord(STORAGE_KEYS.performance, {
    type: 'chart_performance',
    component,
    durationMs: Number(durationMs || 0),
    metadata,
  });
}

export function recordChartFeedback({ rating = 0, comment = '', context = 'dashboard' } = {}) {
  return appendRecord(STORAGE_KEYS.feedback, {
    type: 'chart_feedback',
    context,
    rating: Number(rating || 0),
    comment: String(comment || '').slice(0, 1000),
  });
}

export function getChartMonitoringSnapshot() {
  return {
    errors: readRecords(STORAGE_KEYS.errors),
    performance: readRecords(STORAGE_KEYS.performance),
    feedback: readRecords(STORAGE_KEYS.feedback),
  };
}

export function clearChartMonitoring() {
  const currentWindow = browserWindow();
  if (!currentWindow?.localStorage) return;

  Object.values(STORAGE_KEYS).forEach((key) => currentWindow.localStorage.removeItem(key));
}

export { STORAGE_KEYS as chartMonitoringStorageKeys };
