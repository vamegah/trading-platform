import { useEffect, useMemo, useState } from 'react';
import AgentScoreChart from '../Charts/AgentScoreChart';
import ChartDataTable from '../Charts/ChartDataTable';
import ChartErrorBoundary from '../Charts/ChartErrorBoundary';
import { calculatePositionSize, evaluatePortfolioRisk, optimizePortfolioTrade } from '../../services/api';
import { formatCurrency } from '../../utils/charts/formatters';
import { colors } from '../../utils/charts/theme';

const RISK_PORTFOLIO = [
  { symbol: 'MSFT', market_value: 55000, beta: 1.1, volatility: 0.018, correlation: 0.72, stop_loss_pct: 0.07 },
  { symbol: 'SPY', market_value: 45000, beta: 1.0, volatility: 0.014, correlation: 0.72, stop_loss_pct: 0.06 },
];

function normalizeMetric(value, threshold) {
  if (!threshold) return 0;
  return Math.max(0, Math.min(100, (Math.abs(Number(value || 0)) / threshold) * 100));
}

function hexToRgb(hex) {
  const n = parseInt(hex.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

// Continuous green (0% of threshold) to amber (100% of threshold) scale.
function greenToAmber(percentUsed) {
  const t = Math.max(0, Math.min(1, percentUsed / 100));
  const from = hexToRgb(colors.up);
  const to = hexToRgb(colors.warning);
  const [r, g, b] = from.map((c, i) => Math.round(c + (to[i] - c) * t));
  return `rgb(${r}, ${g}, ${b})`;
}

function PortfolioHealth() {
  const [risk, setRisk] = useState(null);
  const [sizing, setSizing] = useState(null);
  const [tradeImpact, setTradeImpact] = useState(null);
  const [riskStatus, setRiskStatus] = useState('loading');

  useEffect(() => {
    setRiskStatus('loading');
    evaluatePortfolioRisk({ portfolio: RISK_PORTFOLIO })
      .then((data) => {
        setRisk(data);
        setRiskStatus('ready');
      })
      .catch(() => {
        setRisk(null);
        setRiskStatus('error');
      });

    calculatePositionSize({
      equity: 125000,
      entry_price: 100,
      stop_loss: 94,
      win_probability: 0.58,
      average_win_pct: 0.08,
      average_loss_pct: -0.04,
      volatility: 0.02,
      portfolio_volatility: 0.015,
      max_drawdown_tolerance: 0.2,
      current_portfolio_risk: 0.06,
      risk_profile: 'balanced',
    })
      .then(setSizing)
      .catch(() => undefined);

    optimizePortfolioTrade({
      holdings: { MSFT: 55000, SPY: 45000 },
      proposed_trade: { symbol: 'NVDA', side: 'BUY', notional: 10000 },
      constraints: { max_sector_weight: 0.65, max_factor_exposure: 0.5 },
    })
      .then(setTradeImpact)
      .catch(() => undefined);
  }, []);

  const riskMetricsData = useMemo(() => {
    if (!risk?.metrics) return [];

    const m = risk.metrics;
    const portfolioEquity = Number(m.portfolio_equity || risk.portfolio_value || 100000);
    // Exposures are ratios of equity; derive them from the submitted portfolio if the API omits them.
    const longValue = RISK_PORTFOLIO.reduce((s, p) => s + Math.max(p.market_value, 0), 0);
    const shortValue = RISK_PORTFOLIO.reduce((s, p) => s + Math.min(p.market_value, 0), 0);
    const values = {
      var: m.var,
      cvar: m.cvar,
      gross_exposure: m.gross_exposure ?? (longValue - shortValue) / portfolioEquity,
      net_exposure: m.net_exposure ?? (longValue + shortValue) / portfolioEquity,
    };
    // VaR/CVaR limits are fractions of equity; exposures are compared against 1.0.
    const thresholds = {
      var: portfolioEquity * 0.05,
      cvar: portfolioEquity * 0.075,
      gross_exposure: 1,
      net_exposure: 1,
    };
    const isMoney = { var: true, cvar: true, gross_exposure: false, net_exposure: false };

    return [
      ['VaR', 'var'],
      ['CVaR', 'cvar'],
      ['Gross exposure', 'gross_exposure'],
      ['Net exposure', 'net_exposure'],
    ].map(([label, key]) => {
      const percentUsed = normalizeMetric(values[key], thresholds[key]);
      return {
        label,
        value: percentUsed,
        rawValue: values[key],
        threshold: thresholds[key],
        isMoney: isMoney[key],
        color: risk.kill_switch_required ? colors.down : greenToAmber(percentUsed),
        displayValue: `${Math.round(percentUsed)}%`,
      };
    });
  }, [risk]);

  const hasRiskData = Boolean(risk?.metrics && riskMetricsData.length);

  return (
    <article id="portfolio" className="panel">
      <header>
        <div>
          <span>Portfolio health</span>
          <strong>{risk?.kill_switch_required ? 'Risk breach' : 'Balanced'}</strong>
        </div>
        <span className={risk?.kill_switch_required ? 'badge review' : 'badge healthy'}>
          {risk?.kill_switch_required ? 'Risk breach' : 'healthy'}
        </span>
      </header>

      <section className="chart-block" aria-label="Portfolio risk metric chart section">
        <h4 className="chart-title">Risk Metrics</h4>
        {riskStatus === 'loading' ? (
          <div className="chart-placeholder chart-frame--risk">Loading risk metrics...</div>
        ) : hasRiskData ? (
          <ChartErrorBoundary componentName="PortfolioRiskMetrics" fallbackHeight={220}>
            {risk.kill_switch_required && (
              <div className="risk-breach-label">Risk breach - position trading disabled</div>
            )}
            <AgentScoreChart
              aria-label={`Horizontal bar chart showing risk metrics: ${riskMetricsData
                .map((metric) => `${metric.label} ${Math.round(metric.value)}%`)
                .join(', ')}. ${risk.kill_switch_required ? 'Risk breach active.' : 'Within limits.'}`}
              data={riskMetricsData}
              height={230}
              maxValue={100}
              role="img"
              thresholdBuy={100}
              thresholdSell={0}
              title="Portfolio risk metrics chart"
              width={620}
            />
            <ChartDataTable
              caption="Portfolio risk metrics normalized to thresholds"
              columns={[
                { key: 'metric', label: 'Metric' },
                { key: 'value', label: 'Value' },
                { key: 'threshold', label: 'Threshold' },
                { key: 'used', label: 'Threshold used' },
              ]}
              rows={riskMetricsData.map((metric) => ({
                id: metric.label,
                metric: metric.label,
                value: metric.isMoney ? formatCurrency(metric.rawValue) : Number(metric.rawValue).toFixed(2),
                threshold: metric.isMoney ? formatCurrency(metric.threshold) : metric.threshold.toFixed(2),
                used: metric.displayValue,
              }))}
            />
          </ChartErrorBoundary>
        ) : (
          <div className="chart-empty chart-frame--risk">Risk data unavailable</div>
        )}
      </section>

      <div className="row">
        <span>VaR / CVaR</span>
        <strong>
          {risk?.metrics ? `${formatCurrency(risk.metrics.var)} / ${formatCurrency(risk.metrics.cvar)}` : 'pending'}
        </strong>
      </div>
      <div className="row">
        <span>Next position</span>
        <strong>{sizing ? `${sizing.quantity} sh` : 'pending'}</strong>
      </div>
      <div className="row">
        <span>Trade impact</span>
        <strong>{tradeImpact?.trade_allowed ? 'Allowed' : 'Review'}</strong>
      </div>
    </article>
  );
}

export default PortfolioHealth;
