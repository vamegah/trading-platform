import { useEffect, useState } from 'react';
import ChartErrorBoundary from '../ChartErrorBoundary';
import ScenarioSelector from './ScenarioSelector';
import StressBarChart from './StressBarChart';
import { getStressTestScenarios, runStressTest } from '../../services/api';

function normalizeScenarios(payload) {
  const list = Array.isArray(payload) ? payload : payload?.scenarios || [];
  return list
    .map((s) => (typeof s === 'string' ? { id: s, name: s } : { id: s.name || s.id, name: s.label || s.name || s.id }))
    .filter((s) => s.id);
}

function formatCurrency(value) {
  return Number(value || 0).toLocaleString('en-US', { style: 'currency', currency: 'USD' });
}

function StressTest() {
  const [scenarios, setScenarios] = useState([]);
  const [selected, setSelected] = useState('');
  const [result, setResult] = useState(null);
  const [scenariosLoading, setScenariosLoading] = useState(true);
  const [resultLoading, setResultLoading] = useState(false);

  useEffect(() => {
    let active = true;
    getStressTestScenarios()
      .then((payload) => {
        if (!active) return;
        const list = normalizeScenarios(payload);
        setScenarios(list);
        setSelected((cur) => cur || list[0]?.id || '');
      })
      .catch(() => active && setScenarios([]))
      .finally(() => active && setScenariosLoading(false));
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!selected) return undefined;
    let active = true;
    setResultLoading(true);
    runStressTest(selected)
      .then((data) => active && setResult(data))
      .catch(() => active && setResult(null))
      .finally(() => active && setResultLoading(false));
    return () => {
      active = false;
    };
  }, [selected]);

  const loading = scenariosLoading || resultLoading;
  const positions = result?.positions || result?.full_stress_test?.positions || [];
  const scenarioName = scenarios.find((s) => s.id === selected)?.name || selected || 'Loading...';

  return (
    <section className="panel">
      <header>
        <div>
          <span>Stress test</span>
          <strong>Scenario Runner</strong>
        </div>
        <span className="badge review">phase 4</span>
      </header>

      <ScenarioSelector scenarios={scenarios} value={selected} onChange={setSelected} loading={loading} />

      <ChartErrorBoundary>
        {loading ? (
          <div className="chart-placeholder" role="status" aria-busy="true">
            Loading stress test data...
          </div>
        ) : positions.length > 0 ? (
          <StressBarChart positions={positions} />
        ) : (
          <p className="chart-empty">Stress test data unavailable</p>
        )}
      </ChartErrorBoundary>

      <div className="row">
        <span>Scenario</span>
        <strong>{scenarioName}</strong>
      </div>
      <div className="row">
        <span>Total P/L</span>
        <strong>{result ? formatCurrency(result.total_pnl) : 'pending'}</strong>
      </div>
      <div className="row">
        <span>Portfolio impact</span>
        <strong>{result ? `${Number(result.total_pnl_percent || 0).toFixed(1)}%` : 'pending'}</strong>
      </div>
    </section>
  );
}

export default StressTest;
