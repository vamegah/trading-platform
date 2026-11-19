import React from 'react';

const COLOR = { BUY: '#16a34a', SELL: '#dc2626', default: '#6b7280' };

function SignalCard({ signal }) {
  if (!signal) return <p>Loading...</p>;
  const color = COLOR[signal.signal] ?? COLOR.default;
  return (
    <article className="signal-card">
      <h2>{signal.symbol} Signal</h2>
      <p style={{ color, fontWeight: 'bold', fontSize: '1.5rem' }}>{signal.signal}</p>
      <p>Confidence: {signal.confidence}%</p>
      <p>Stop Loss: ${signal.stop_loss}</p>
      <p>Take Profit: ${signal.take_profit}</p>
      <p>Expected Return: {signal.probability_distribution?.expected_return_pct}%</p>
    </article>
  );
}

export default SignalCard;
