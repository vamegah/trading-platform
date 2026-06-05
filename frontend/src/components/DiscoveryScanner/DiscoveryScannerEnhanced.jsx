import { useState } from 'react';
import PropTypes from 'prop-types';
import { runDiscoveryScanner } from '../../services/api';

function ConfidenceBar({ confidence = 0 }) {
  let colorClass = 'confidence-bar--low';
  if (confidence >= 0.68) colorClass = 'confidence-bar--high';
  else if (confidence >= 0.55) colorClass = 'confidence-bar--medium';

  const percentage = Math.max(0, Math.min(100, Math.round(confidence * 100)));

  return (
    <div className="confidence-cell" aria-label={`Confidence ${percentage}%`}>
      <svg className="confidence-bar" data-confidence-bar="true" role="img" viewBox="0 0 100 8">
        <title>{`Confidence ${percentage}%`}</title>
        <rect className="confidence-bar__track" height="8" rx="4" width="100" x="0" y="0" />
        <rect className={colorClass} height="8" rx="4" width={percentage} x="0" y="0" />
      </svg>
      <span className="confidence-cell__value">{percentage}%</span>
    </div>
  );
}

function DirectionalIndicator({ signal }) {
  const normalized = String(signal || 'HOLD').toUpperCase();
  const config = {
    BUY: { symbol: '▲', label: 'BUY', className: 'directional-indicator--buy' },
    SELL: { symbol: '▼', label: 'SELL', className: 'directional-indicator--sell' },
    HOLD: { symbol: '—', label: 'HOLD', className: 'directional-indicator--hold' },
  }[normalized] || { symbol: '—', label: normalized, className: 'directional-indicator--hold' };

  return (
    <span
      aria-label={config.label}
      className={`directional-indicator ${config.className}`}
      data-signal-indicator={config.label}
    >
      {config.symbol}
    </span>
  );
}

function topFactor(exposures = {}) {
  const [factor] = Object.entries(exposures).sort((left, right) => right[1] - left[1])[0] || [];
  return factor ? factor.replaceAll('_', ' ') : 'n/a';
}

function DiscoveryScanner() {
  const [universe, setUniverse] = useState('AAPL,MSFT,NVDA,AMD,GOOGL');
  const [minConfidence, setMinConfidence] = useState(0.55);
  const [factor, setFactor] = useState('momentum');
  const [sector, setSector] = useState('technology');
  const [minRewardToRisk, setMinRewardToRisk] = useState(0);
  const [maxTailRisk, setMaxTailRisk] = useState(0.45);
  const [results, setResults] = useState([]);
  const [status, setStatus] = useState('idle');

  const runScan = async () => {
    setStatus('loading');
    const payload = {
      universe: universe
        .split(',')
        .map((item) => item.trim().toUpperCase())
        .filter(Boolean),
      min_confidence: Number(minConfidence),
      factor: factor || null,
      sector: sector || null,
      custom_criteria: {
        min_reward_to_risk: Number(minRewardToRisk),
        max_tail_risk: Number(maxTailRisk),
      },
    };
    try {
      const response = await runDiscoveryScanner(payload);
      setResults(response.results || []);
      setStatus('ready');
    } catch {
      setResults([]);
      setStatus('error');
    }
  };

  return (
    <section className="panel">
      <header>
        <div>
          <span>Discovery scanner</span>
          <strong>Ranked opportunities</strong>
        </div>
        <button type="button" disabled={status === 'loading'} onClick={runScan}>
          {status === 'loading' ? 'Scanning' : 'Run scan'}
        </button>
      </header>

      <div className="filter-grid">
        <label>
          Universe
          <input value={universe} onChange={(event) => setUniverse(event.target.value)} />
        </label>
        <label>
          Min confidence
          <input
            max="0.95"
            min="0"
            step="0.05"
            type="number"
            value={minConfidence}
            onChange={(event) => setMinConfidence(event.target.value)}
          />
        </label>
        <label>
          Factor
          <select value={factor} onChange={(event) => setFactor(event.target.value)}>
            <option value="">Any</option>
            <option value="momentum">Momentum</option>
            <option value="quality">Quality</option>
            <option value="growth">Growth</option>
            <option value="value">Value</option>
            <option value="low_volatility">Low volatility</option>
          </select>
        </label>
        <label>
          Sector
          <select value={sector} onChange={(event) => setSector(event.target.value)}>
            <option value="">Any</option>
            <option value="technology">Technology</option>
            <option value="communication_services">Communication services</option>
            <option value="financials">Financials</option>
            <option value="energy">Energy</option>
          </select>
        </label>
        <label>
          Min reward/risk
          <input
            min="0"
            step="0.25"
            type="number"
            value={minRewardToRisk}
            onChange={(event) => setMinRewardToRisk(event.target.value)}
          />
        </label>
        <label>
          Max tail risk
          <input
            max="1"
            min="0"
            step="0.05"
            type="number"
            value={maxTailRisk}
            onChange={(event) => setMaxTailRisk(event.target.value)}
          />
        </label>
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Symbol</th>
              <th className="table-col-signal">Signal</th>
              <th className="table-col-confidence">Confidence</th>
              <th>Expected return</th>
              <th>Reward/risk</th>
              <th>Tail risk</th>
              <th>Top factor</th>
              <th>Sector</th>
            </tr>
          </thead>
          <tbody>
            {results.map((row) => (
              <tr key={row.symbol}>
                <td className="table-cell-strong">{row.symbol}</td>
                <td className="table-cell-center">
                  <DirectionalIndicator signal={row.signal} />
                </td>
                <td>
                  <ConfidenceBar confidence={row.confidence} />
                </td>
                <td>{Math.round((row.expected_return_rank || 0) * 100)}%</td>
                <td>{row.reward_to_risk}</td>
                <td>{Math.round((row.tail_risk || 0) * 100)}%</td>
                <td>{topFactor(row.factor_exposures)}</td>
                <td>{row.sector}</td>
              </tr>
            ))}
            {!results.length && (
              <tr>
                <td className="table-empty" colSpan="8">
                  {status === 'loading'
                    ? 'Scanning...'
                    : status === 'error'
                      ? 'Scan failed. Try again.'
                      : 'Run a scan to rank the universe.'}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

DiscoveryScanner.propTypes = {};

ConfidenceBar.propTypes = {
  confidence: PropTypes.number,
};

DirectionalIndicator.propTypes = {
  signal: PropTypes.string,
};

export default DiscoveryScanner;
