import { useEffect, useMemo, useState } from 'react';
import PropTypes from 'prop-types';
import ChartDataTable from '../Charts/ChartDataTable';
import ChartErrorBoundary from '../Charts/ChartErrorBoundary';
import { getStressTestScenarios, runStressTest } from '../../services/api';
import { formatCurrency } from '../../utils/charts/formatters';
import { colors } from '../../utils/charts/theme';

function normalizeScenarios(payload) {
  const scenarios = Array.isArray(payload) ? payload : payload?.scenarios || [];
  return scenarios.map((scenario) => ({
    id: scenario.name || scenario.id,
    name: scenario.label || scenario.name || scenario.id,
    description: scenario.description,
  }));
}

function positionsFromResult(result) {
  return result?.positions || result?.full_stress_test?.positions || [];
}

function StressScenarioChart({ positions = [] }) {
  const width = 680;
  const height = Math.max(220, positions.length * 58 + 60);
  const padding = { top: 20, right: 112, bottom: 28, left: 90 };
  const chartWidth = width - padding.left - padding.right;
  const maxValue = Math.max(1, ...positions.flatMap((position) => [
    Number(position.current_value || 0),
    Number(position.stressed_value || 0),
  ]));

  return (
    <svg
      aria-label={`Grouped bar chart comparing current and stressed value for ${positions.length} positions`}
      className="stress-scenario-chart"
      height={height}
      role="img"
      viewBox={`0 0 ${width} ${height}`}
      width="100%"
    >
      <title>Stress test scenario comparison</title>
      <rect className="chart-svg-bg" height={height} width={width} x="0" y="0" />
      {positions.map((position, index) => {
        const y = padding.top + index * 58;
        const currentWidth = (Number(position.current_value || 0) / maxValue) * chartWidth;
        const stressedWidth = (Number(position.stressed_value || 0) / maxValue) * chartWidth;
        const stressedColor = Number(position.pnl_percent || 0) >= 0 ? colors.up : colors.down;

        return (
          <g key={position.symbol}>
            <text className="chart-svg-label" dominantBaseline="middle" textAnchor="end" x={padding.left - 12} y={y + 17}>
              {position.symbol}
            </text>
            <rect
              className="stress-scenario-chart__track"
              height="16"
              rx="4"
              width={chartWidth}
              x={padding.left}
              y={y}
            />
            <rect
              data-stress-current-bar="true"
              fill={colors.neutral}
              height="16"
              rx="4"
              width={currentWidth}
              x={padding.left}
              y={y}
            />
            <rect
              className="stress-scenario-chart__track"
              height="16"
              rx="4"
              width={chartWidth}
              x={padding.left}
              y={y + 24}
            />
            <rect
              data-stress-stressed-bar="true"
              fill={stressedColor}
              height="16"
              rx="4"
              width={stressedWidth}
              x={padding.left}
              y={y + 24}
            />
            <text className="chart-svg-value" dominantBaseline="middle" x={padding.left + chartWidth + 12} y={y + 8}>
              {formatCurrency(position.current_value)}
            </text>
            <text className="chart-svg-value" dominantBaseline="middle" x={padding.left + chartWidth + 12} y={y + 32}>
              {formatCurrency(position.stressed_value)} ({Number(position.pnl_percent || 0).toFixed(1)}%)
            </text>
          </g>
        );
      })}
      <text className="chart-svg-axis" textAnchor="middle" x={padding.left + chartWidth / 2} y={height - 8}>
        Current value vs stressed value
      </text>
    </svg>
  );
}

function StressTest() {
  const [scenarios, setScenarios] = useState([]);
  const [selectedScenario, setSelectedScenario] = useState('');
  const [result, setResult] = useState(null);
  const [isScenarioLoading, setIsScenarioLoading] = useState(true);
  const [isResultLoading, setIsResultLoading] = useState(false);

  useEffect(() => {
    setIsScenarioLoading(true);
    getStressTestScenarios()
      .then((payload) => {
        const normalized = normalizeScenarios(payload);
        setScenarios(normalized);
        setSelectedScenario((current) => current || normalized[0]?.id || '');
      })
      .catch(() => {
        setScenarios([]);
      })
      .finally(() => {
        setIsScenarioLoading(false);
      });
  }, []);

  useEffect(() => {
    if (!selectedScenario) return;
    setIsResultLoading(true);
    runStressTest(selectedScenario)
      .then(setResult)
      .catch(() => setResult(null))
      .finally(() => setIsResultLoading(false));
  }, [selectedScenario]);

  const positions = positionsFromResult(result);
  const hasPositions = positions.length > 0;
  const selectedScenarioName =
    scenarios.find((scenario) => scenario.id === selectedScenario)?.name || selectedScenario || 'Loading...';
  const tableRows = useMemo(
    () =>
      positions.map((position) => ({
        id: position.symbol,
        symbol: position.symbol,
        current: formatCurrency(position.current_value),
        stressed: formatCurrency(position.stressed_value),
        pnl: `${Number(position.pnl_percent || 0).toFixed(1)}%`,
      })),
    [positions]
  );

  const handleScenarioChange = (event) => {
    setSelectedScenario(event.target.value);
  };

  return (
    <section className="panel">
      <header>
        <div>
          <span>Stress test</span>
          <strong>Scenario Runner</strong>
        </div>
        <span className="badge review">phase 4</span>
      </header>

      <div className="scenario-control">
        <label htmlFor="stress-scenario">Scenario</label>
        <select
          disabled={isScenarioLoading || isResultLoading || !scenarios.length}
          id="stress-scenario"
          onChange={handleScenarioChange}
          value={selectedScenario}
        >
          {scenarios.map((scenario) => (
            <option key={scenario.id} value={scenario.id}>
              {scenario.name}
            </option>
          ))}
        </select>
        {(isScenarioLoading || isResultLoading) && <span className="chart-loading-note">Loading...</span>}
      </div>

      <section className="chart-block" aria-label="Stress test comparison chart section">
        <h4 className="chart-title">Position Comparison</h4>
        {isScenarioLoading || isResultLoading ? (
          <div className="chart-placeholder chart-frame--stress">Loading stress test data...</div>
        ) : hasPositions ? (
          <ChartErrorBoundary componentName="StressScenarioComparison" fallbackHeight={300}>
            <StressScenarioChart positions={positions} />
            <div className="chart-reference">
              <span>Neutral: current value</span>
              <span>Green/red: stressed value</span>
              <span>Labels show stressed P/L percent</span>
            </div>
            <ChartDataTable
              caption="Stress test position comparison"
              columns={[
                { key: 'symbol', label: 'Symbol' },
                { key: 'current', label: 'Current value' },
                { key: 'stressed', label: 'Stressed value' },
                { key: 'pnl', label: 'P/L percent' },
              ]}
              rows={tableRows}
            />
          </ChartErrorBoundary>
        ) : (
          <div className="chart-empty chart-frame--stress">Stress test data unavailable</div>
        )}
      </section>

      <div className="row">
        <span>Scenario</span>
        <strong>{selectedScenarioName}</strong>
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

StressScenarioChart.propTypes = {
  positions: PropTypes.array,
};

export default StressTest;
