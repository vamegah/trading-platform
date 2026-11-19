import React, { useEffect, useState } from 'react';
import { getPortfolioSummary } from '../services/api';

const FALLBACK = [
  { label: 'Portfolio equity', value: '—' },
  { label: 'Net exposure', value: '—' },
  { label: 'Signal confidence', value: '—' },
  { label: 'Drawdown guard', value: '—' },
];

function toMetrics(summary) {
  if (!summary) return FALLBACK;
  return [
    { label: 'Portfolio equity', value: summary.equity != null ? `$${Number(summary.equity).toLocaleString()}` : '—' },
    { label: 'Net exposure', value: summary.net_exposure != null ? `${summary.net_exposure}%` : '—' },
    { label: 'Signal confidence', value: summary.signal_confidence != null ? `${summary.signal_confidence}%` : '—' },
    { label: 'Drawdown guard', value: summary.drawdown_guard != null ? `${summary.drawdown_guard}%` : '—' },
  ];
}

function Dashboard() {
  const [metrics, setMetrics] = useState(FALLBACK);

  useEffect(() => {
    getPortfolioSummary()
      .then(data => setMetrics(toMetrics(data)))
      .catch(() => {});
  }, []);

  return (
    <section id="dashboard" className="metrics" aria-label="Portfolio metrics">
      {metrics.map((metric) => (
        <article className="metric" key={metric.label}>
          <span>{metric.label}</span>
          <strong>{metric.value}</strong>
        </article>
      ))}
    </section>
  );
}

export default Dashboard;
