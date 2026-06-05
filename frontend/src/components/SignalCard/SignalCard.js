// frontend/src/components/SignalCard.js
import React from 'react';

const SignalCard = ({ signal }) => {
  if (!signal) return <p>Loading...</p>;
  const color = signal.signal === 'BUY' ? 'green' : (signal.signal === 'SELL' ? 'red' : 'gray');
  return (
    <div className="p-4 border rounded shadow">
      <h2 className="text-xl font-semibold">{signal.symbol} Signal</h2>
      <p className={`text-2xl font-bold text-${color}-600`}>{signal.signal}</p>
      <p>Confidence: {signal.confidence}%</p>
      <p>Stop Loss: ${signal.stop_loss}</p>
      <p>Take Profit: ${signal.take_profit}</p>
      <p>Expected Return: {signal.probability_distribution?.expected_return_pct}%</p>
    </div>
  );
};