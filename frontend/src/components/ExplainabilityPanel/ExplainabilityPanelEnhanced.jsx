import { useEffect, useMemo } from 'react';
import PropTypes from 'prop-types';
import AgentScoreChart from '../Charts/AgentScoreChart';
import ChartContainer from '../Charts/ChartContainer';
import ChartDataTable from '../Charts/ChartDataTable';
import ChartErrorBoundary from '../Charts/ChartErrorBoundary';
import useChartSeries from '../../hooks/useChartSeries';
import { formatAgentScores, probabilityScenarios } from '../../utils/charts/formatters';

function percent(value = 0) {
  return `${Math.round(value * 100)}%`;
}

function evidenceLabel(item) {
  if (typeof item === 'string') return item;
  const source = item.source || 'source';
  const type = item.type || 'evidence';
  return `${type.replaceAll('_', ' ')} - ${source}`;
}

function nestedSignalValue(signal, key) {
  return signal?.[key] || signal?.recommendation?.[key] || {};
}

function ProbabilityDistributionChart({ distribution }) {
  const { addSeries, fitContent, removeSeries } = useChartSeries();
  const scenarios = useMemo(() => probabilityScenarios(distribution), [distribution]);

  useEffect(() => {
    const data = scenarios.map((scenario, index) => ({
      time: index,
      value: Math.round(scenario.value * 100),
      color: scenario.color,
    }));
    const result = addSeries(
      'histogram',
      {
        color: '#9ca3af',
        priceFormat: {
          type: 'custom',
          formatter: (value) => `${Math.round(value)}%`,
        },
      },
      data
    );

    fitContent();

    return () => {
      if (result?.seriesId) removeSeries(result.seriesId);
    };
  }, [addSeries, fitContent, removeSeries, scenarios]);

  return null;
}

function ProbabilityRows({ probabilities = {}, tailRisk = {}, distribution = {} }) {
  const scenarios = probabilityScenarios(probabilities);

  return (
    <div className="chart-legend chart-legend--probability">
      {scenarios.map((scenario) => (
        <div className="chart-legend__item" key={scenario.key}>
          <span>{scenario.label}</span>
          <strong>{percent(scenario.value)}</strong>
        </div>
      ))}
      <div className="chart-legend__item">
        <span>Expected 20d return</span>
        <strong>{percent(distribution.expected_return_20d || 0)}</strong>
      </div>
      <div className="chart-legend__item">
        <span>CVaR 20d</span>
        <strong>{percent(tailRisk.cvar_20d || 0)}</strong>
      </div>
    </div>
  );
}

function ExplainabilityPanel({ signal }) {
  const explainability = signal?.explainability || signal?.recommendation?.explainability || {};
  const drivers = explainability.top_drivers || [];
  const risks = explainability.plain_language_risks || [];
  const evidence = signal?.agent_outputs?.fundamentals?.evidence || [];
  const componentScores = nestedSignalValue(signal, 'component_scores');
  const probabilityDist = nestedSignalValue(signal, 'probability_distribution');
  const attributions = explainability.feature_attributions || {};
  const tailRisk = signal?.tail_risk_summary || signal?.recommendation?.tail_risk_summary || {};
  const returnDistribution = signal?.return_distribution || signal?.recommendation?.return_distribution || {};
  const agentData = formatAgentScores(componentScores);
  const hasComponentScores = Boolean(componentScores && Object.keys(componentScores).length);
  const hasProbabilityDistribution = Boolean(probabilityDist && Object.keys(probabilityDist).length);
  const isLoading = !signal;
  const probabilityRows = probabilityScenarios(probabilityDist).map((scenario) => ({
    id: scenario.key,
    scenario: scenario.label,
    probability: percent(scenario.value),
  }));

  return (
    <article className="panel">
      <header>
        <div>
          <span>Explainability</span>
          <strong>{explainability.method || 'Signal drivers'}</strong>
        </div>
        <span className="badge review">review</span>
      </header>

      <section className="chart-block" aria-label="Agent score chart section">
        <h4 className="chart-title">Agent Scores</h4>
        {hasComponentScores ? (
          <ChartErrorBoundary componentName="ExplainabilityAgentScores" fallbackHeight={250}>
            <AgentScoreChart
              aria-label={`Agent contribution scores: ${agentData
                .map((item) => `${item.label} ${Math.round(item.value)}%`)
                .join(', ')}`}
              data={agentData}
              height={330}
              maxValue={100}
              thresholdBuy={0.68}
              thresholdSell={0.38}
              title="Agent contribution score chart"
              width={620}
            />
            <ChartDataTable
              caption="Agent contribution scores"
              columns={[
                { key: 'agent', label: 'Agent' },
                { key: 'score', label: 'Score' },
              ]}
              rows={agentData.map((item) => ({
                id: item.label,
                agent: item.label,
                score: `${Math.round(item.value)}%`,
              }))}
            />
          </ChartErrorBoundary>
        ) : (
          <div className="chart-empty chart-frame--compact">Agent scores unavailable</div>
        )}
      </section>

      <section className="chart-block" aria-label="Probability distribution chart section">
        <h4 className="chart-title">Probability Distribution</h4>
        {isLoading ? (
          <div className="chart-placeholder chart-frame--compact">Loading distribution...</div>
        ) : hasProbabilityDistribution ? (
          <ChartErrorBoundary componentName="ExplainabilityProbabilityDistribution" fallbackHeight={220}>
            <div className="chart-frame chart-frame--compact">
              <ChartContainer
                aria-label={`Histogram chart showing probabilities for ${probabilityRows
                  .map((row) => `${row.scenario} ${row.probability}`)
                  .join(', ')}`}
                height={220}
                monitoringName="ExplainabilityProbabilityHistogram"
                role="img"
                width={620}
              >
                <ProbabilityDistributionChart distribution={probabilityDist} />
              </ChartContainer>
            </div>
            <ProbabilityRows
              distribution={returnDistribution}
              probabilities={probabilityDist}
              tailRisk={tailRisk}
            />
            <ChartDataTable
              caption="Probability distribution scenario values"
              columns={[
                { key: 'scenario', label: 'Scenario' },
                { key: 'probability', label: 'Probability' },
              ]}
              rows={probabilityRows}
            />
          </ChartErrorBoundary>
        ) : (
          <div className="chart-empty chart-frame--compact">Distribution data unavailable</div>
        )}
      </section>

      <div className="chart-text-group">
        <h4 className="chart-title">Signal Drivers</h4>
        {(drivers.length ? drivers : [{ factor: 'waiting_for_signal', contribution: 0 }]).map((driver) => (
          <div className="row" key={driver.factor}>
            <span>{driver.factor.replaceAll('_', ' ')}</span>
            <strong>{percent(Math.abs(driver.contribution ?? driver.score ?? 0))}</strong>
          </div>
        ))}
      </div>

      <div className="chart-text-group">
        <h4 className="chart-title">Feature Contributions</h4>
        {Object.entries(attributions).map(([name, value]) => (
          <div className="row" key={name}>
            <span>{name.replaceAll('_', ' ')}</span>
            <strong>{percent(value)}</strong>
          </div>
        ))}
        {!Object.keys(attributions).length && <p>Feature attributions will appear after analysis.</p>}
      </div>

      <div className="risk-list">
        <span>Key risks</span>
        {(risks.length ? risks : ['Risk language will appear after analysis.']).map((risk) => (
          <p key={risk}>{risk}</p>
        ))}
      </div>

      <div className="risk-list">
        <span>Source evidence</span>
        {(evidence.length ? evidence : ['Agent evidence pending.']).slice(0, 3).map((item) => (
          <p key={typeof item === 'string' ? item : `${item.type}-${item.snapshot_id}`}>
            {typeof item === 'object' && item.url ? (
              <a href={item.url} rel="noreferrer" target="_blank">
                {evidenceLabel(item)}
              </a>
            ) : (
              evidenceLabel(item)
            )}
          </p>
        ))}
      </div>
    </article>
  );
}

ExplainabilityPanel.propTypes = {
  signal: PropTypes.object,
};

ProbabilityDistributionChart.propTypes = {
  distribution: PropTypes.object.isRequired,
};

ProbabilityRows.propTypes = {
  probabilities: PropTypes.object,
  tailRisk: PropTypes.object,
  distribution: PropTypes.object,
};

export default ExplainabilityPanel;
