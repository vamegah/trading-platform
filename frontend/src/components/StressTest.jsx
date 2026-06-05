// Simplified component
import React, { useState } from 'react';
import { runStressTest } from '../services/api';

const StressTest = () => {
  const [scenario, setScenario] = useState('2008_financial_crisis');
  const [result, setResult] = useState(null);

  const handleRun = async () => {
    const data = await runStressTest(scenario);
    setResult(data);
  };

  return (
    <div>
      <select value={scenario} onChange={e => setScenario(e.target.value)}>
        <option value="2008_financial_crisis">2008 Crisis</option>
        <option value="covid_crash_2020">COVID Crash</option>
        <option value="inflation_shock_2022">Inflation Shock</option>
      </select>
      <button onClick={handleRun}>Run Test</button>
      {result && (
        <div>
          <h3>Portfolio P&L: {result.total_pnl_percent.toFixed(2)}%</h3>
          <ul>
            {result.positions.map(p => (
              <li key={p.symbol}>{p.symbol}: {p.pnl_percent.toFixed(2)}%</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default StressTest;