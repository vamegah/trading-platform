/**
 * Integration tests for the six chart-bearing dashboard components.
 * The charting library and the API service layer are mocked; components, shared
 * chart wrappers, and SVG charts are real.
 * Run with: npx vitest run (from frontend/)
 *
 * Covers Requirements 3.6, 3.7, 4.5, 5.5, 6.6, 7.3, 7.6, 8.3, 8.6, 9.2, 9.5.
 */
import React from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';

const lw = vi.hoisted(() => {
  const state = { series: [] };
  const makeChart = () => ({
    applyOptions: vi.fn(),
    remove: vi.fn(),
    removeSeries: vi.fn(),
    priceScale: vi.fn(() => ({ applyOptions: vi.fn() })),
    timeScale: vi.fn(() => ({ fitContent: vi.fn() })),
    addSeries: vi.fn((definition, options) => {
      const s = { definition, options, setData: vi.fn(), createPriceLine: vi.fn() };
      state.series.push(s);
      return s;
    }),
  });
  return { state, createChart: vi.fn(() => makeChart()), createSeriesMarkers: vi.fn(() => ({ detach: vi.fn() })) };
});

vi.mock('@tradingview/lightweight-charts', () => ({
  createChart: lw.createChart,
  createSeriesMarkers: lw.createSeriesMarkers,
  CandlestickSeries: 'CandlestickSeries',
  HistogramSeries: 'HistogramSeries',
  AreaSeries: 'AreaSeries',
  LineSeries: 'LineSeries',
  LineStyle: { Solid: 0, Dotted: 1, Dashed: 2 },
}));

const api = vi.hoisted(() => ({
  runWalkForwardBacktest: vi.fn(),
  validateChampionChallenger: vi.fn(),
  monitorModel: vi.fn(),
  getTradeJournal: vi.fn(),
  executePaperSignal: vi.fn(),
  evaluatePortfolioRisk: vi.fn(),
  calculatePositionSize: vi.fn(),
  optimizePortfolioTrade: vi.fn(),
  getStressTestScenarios: vi.fn(),
  runStressTest: vi.fn(),
  runDiscoveryScanner: vi.fn(),
}));

vi.mock('../../services/api', () => api);

import StockDeepDive from '../../components/StockDeepDive';
import ExplainabilityPanel from '../../components/ExplainabilityPanel';
import BacktestViewer from '../../components/BacktestViewer';
import PortfolioHealth from '../../components/PortfolioHealth';
import StressTest from '../../components/StressTest';
import DiscoveryScanner from '../../components/DiscoveryScanner';
import { CHART_THEME } from '../../styles/chart-theme';
import { generateSampleOHLCV } from '../../utils/charts/formatters';

const never = () => new Promise(() => {});

beforeEach(() => {
  lw.state.series = [];
  lw.createChart.mockClear();
  lw.createSeriesMarkers.mockClear();
  Object.values(api).forEach((fn) => fn.mockReset());
  api.validateChampionChallenger.mockResolvedValue({});
  api.monitorModel.mockResolvedValue({});
  api.getTradeJournal.mockResolvedValue({ entries: [] });
  api.calculatePositionSize.mockResolvedValue({ quantity: 10 });
  api.optimizePortfolioTrade.mockResolvedValue({ trade_allowed: true });
});
afterEach(cleanup);

describe('StockDeepDive integration', () => {
  const signal = { symbol: 'MSFT', signal: 'buy', entry_zone: { low: 148, high: 152 }, stop_loss: 145, take_profit: 160 };

  it('shows the placeholder while loading, without creating a chart', () => {
    const { container } = render(<StockDeepDive signal={signal} priceData={generateSampleOHLCV(60, 150)} />);
    expect(container.querySelector('.chart-placeholder')).toBeTruthy();
    expect(lw.createChart).not.toHaveBeenCalled();
  });

  it('renders candlestick and volume series with price lines once ready', async () => {
    render(<StockDeepDive signal={signal} priceData={generateSampleOHLCV(60, 150)} />);
    await waitFor(() => expect(lw.state.series.length).toBe(2));
    expect(lw.state.series.map((s) => s.definition)).toEqual(['CandlestickSeries', 'HistogramSeries']);
    expect(lw.state.series[0].createPriceLine).toHaveBeenCalledTimes(4);
  });

  it('shows "Price data unavailable" for empty data', async () => {
    render(<StockDeepDive signal={signal} priceData={[]} />);
    expect(await screen.findByText('Price data unavailable')).toBeTruthy();
    expect(lw.createChart).not.toHaveBeenCalled();
  });
});

describe('ExplainabilityPanel integration', () => {
  const recommendation = {
    component_scores: {
      fundamentals: 0.75, technical: 0.65, news_sentiment: 0.55, macro: 0.7, alt_data: 0.3, debate: 0.68, tax: 0.5,
    },
    probability_distribution: { up_5pct_20d: 0.35, down_3pct_20d: 0.25, flat_20d: 0.3, tail_loss_8pct_20d: 0.1 },
  };

  it('shows the distribution placeholder while the signal is loading', () => {
    const { container } = render(<ExplainabilityPanel signal={null} />);
    expect(container.querySelector('.chart-placeholder')).toBeTruthy();
    expect(lw.createChart).not.toHaveBeenCalled();
  });

  it('renders a four-bar colored histogram and seven agent bars', async () => {
    render(<ExplainabilityPanel signal={{ recommendation }} />);
    await waitFor(() => expect(lw.state.series.length).toBe(1));
    const [hist] = lw.state.series;
    expect(hist.definition).toBe('HistogramSeries');
    const data = hist.setData.mock.calls[0][0];
    expect(data.map((d) => d.color)).toEqual([CHART_THEME.green, CHART_THEME.red, CHART_THEME.grey, CHART_THEME.orange]);
    expect(data.map((d) => d.value)).toEqual([35, 25, 30, 10]);
    expect(screen.getAllByTestId('agent-score-row')).toHaveLength(7);
    expect(screen.getByText('news sentiment')).toBeTruthy();
  });

  it('shows both unavailable messages when data is absent', () => {
    render(<ExplainabilityPanel signal={{ explainability: {} }} />);
    expect(screen.getByText('Distribution data unavailable')).toBeTruthy();
    expect(screen.getByText('Agent scores unavailable')).toBeTruthy();
    expect(lw.createChart).not.toHaveBeenCalled();
  });
});

describe('BacktestViewer integration', () => {
  const curve = (end) => Array.from({ length: 60 }, (_, i) => 100000 + ((end - 100000) * i) / 59);

  it('shows the placeholder while the backtest is loading', () => {
    api.runWalkForwardBacktest.mockReturnValue(never());
    const { container } = render(<BacktestViewer />);
    expect(container.querySelector('.chart-placeholder')).toBeTruthy();
    expect(lw.createChart).not.toHaveBeenCalled();
  });

  it('renders a green area with trade markers when final equity exceeds $100,000', async () => {
    api.runWalkForwardBacktest.mockResolvedValue({
      full_walkforward_backtest: {
        equity_curve: curve(110000),
        trades: [{ side: 'BUY', index: 5 }, { side: 'SELL', index: 40 }],
      },
      metrics: { sharpe: 1.5 },
    });
    render(<BacktestViewer />);
    await waitFor(() => expect(lw.state.series.length).toBe(1));
    const [area] = lw.state.series;
    expect(area.definition).toBe('AreaSeries');
    expect(area.options.lineColor).toBe(CHART_THEME.green);
    expect(area.setData.mock.calls[0][0]).toHaveLength(60);
    expect(area.createPriceLine).toHaveBeenCalledTimes(2);
    const markers = lw.createSeriesMarkers.mock.calls[0][1];
    expect(markers.map((m) => m.shape)).toEqual(['arrowUp', 'arrowDown']);
    expect(screen.getByText('Sharpe ratio')).toBeTruthy();
    expect(screen.getByText('Paper execute')).toBeTruthy();
  });

  it('renders a red area when final equity is below $100,000', async () => {
    api.runWalkForwardBacktest.mockResolvedValue({ full_walkforward_backtest: { equity_curve: curve(90000) } });
    render(<BacktestViewer />);
    await waitFor(() => expect(lw.state.series.length).toBe(1));
    expect(lw.state.series[0].options.lineColor).toBe(CHART_THEME.red);
  });

  it('shows "Equity curve data unavailable" for a curve shorter than two values', async () => {
    api.runWalkForwardBacktest.mockResolvedValue({ full_walkforward_backtest: { equity_curve: [100000] } });
    render(<BacktestViewer />);
    expect(await screen.findByText('Equity curve data unavailable')).toBeTruthy();
    expect(lw.createChart).not.toHaveBeenCalled();
  });
});

describe('PortfolioHealth integration', () => {
  const metrics = { var: 2000, cvar: 3000, gross_exposure: 0.8, net_exposure: 0.6, portfolio_equity: 100000 };
  const fills = () => screen.getAllByTestId('agent-score-fill').map((el) => el.getAttribute('fill'));

  it('shows the placeholder while risk data is loading', () => {
    api.evaluatePortfolioRisk.mockReturnValue(never());
    const { container } = render(<PortfolioHealth />);
    expect(container.querySelector('.chart-placeholder')).toBeTruthy();
  });

  it('renders four non-red bars and no breach label within limits', async () => {
    api.evaluatePortfolioRisk.mockResolvedValue({ metrics, kill_switch_required: false });
    render(<PortfolioHealth />);
    await waitFor(() => expect(screen.getAllByTestId('agent-score-row')).toHaveLength(4));
    expect(fills()).not.toContain(CHART_THEME.red);
    expect(screen.queryByText(/position trading disabled/)).toBeNull();
  });

  it('turns every bar red and shows the breach label when the kill switch is required', async () => {
    api.evaluatePortfolioRisk.mockResolvedValue({ metrics, kill_switch_required: true });
    render(<PortfolioHealth />);
    await waitFor(() => expect(screen.getAllByTestId('agent-score-row')).toHaveLength(4));
    expect(fills()).toEqual(Array(4).fill(CHART_THEME.red));
    expect(screen.getByText(/Risk breach - position trading disabled/)).toBeTruthy();
    expect(screen.getAllByText('Risk breach').length).toBeGreaterThan(0);
  });

  it('shows "Risk data unavailable" when the request fails', async () => {
    api.evaluatePortfolioRisk.mockRejectedValue(new Error('down'));
    render(<PortfolioHealth />);
    expect(await screen.findByText('Risk data unavailable')).toBeTruthy();
    expect(screen.getByText('VaR / CVaR')).toBeTruthy();
  });
});

describe('StressTest integration', () => {
  const scenarios = { scenarios: [{ name: '2008', label: '2008 Crisis' }, { name: 'covid', label: 'COVID Crash' }, { name: 'tech', label: 'Tech Bubble' }] };
  const result = (symbol, pnl) => ({
    total_pnl: pnl,
    total_pnl_percent: -20,
    positions: [{ symbol, current_value: 50000, stressed_value: 50000 + pnl, pnl, pnl_percent: (pnl / 50000) * 100 }],
  });

  it('shows the loading placeholder and a disabled selector while loading', () => {
    api.getStressTestScenarios.mockReturnValue(never());
    const { container } = render(<StressTest />);
    expect(container.querySelector('.chart-placeholder')).toBeTruthy();
    expect(screen.getByRole('combobox').disabled).toBe(true);
  });

  it('populates the selector and renders grouped bars with red stressed bars for losses', async () => {
    api.getStressTestScenarios.mockResolvedValue(scenarios);
    api.runStressTest.mockResolvedValue(result('SPY', -10000));
    const { container } = render(<StressTest />);
    await waitFor(() => expect(container.querySelector('[data-bar="stressed"]')).toBeTruthy());
    expect(screen.getByRole('combobox').children.length).toBe(3);
    expect(container.querySelector('[data-bar="current"]').getAttribute('fill')).toBe(CHART_THEME.neutral);
    expect(container.querySelector('[data-bar="stressed"]').getAttribute('fill')).toBe(CHART_THEME.red);
    expect(container.querySelector('[data-label="pnl-percent"]').textContent).toBe('-20.0%');
  });

  it('re-runs the stress test and updates the chart when the scenario changes', async () => {
    api.getStressTestScenarios.mockResolvedValue(scenarios);
    api.runStressTest.mockImplementation((name) =>
      Promise.resolve(name === 'covid' ? result('QQQ', 5000) : result('SPY', -10000))
    );
    const { container } = render(<StressTest />);
    await waitFor(() => expect(container.querySelector('[data-bar="stressed"]')).toBeTruthy());
    expect(api.runStressTest).toHaveBeenLastCalledWith('2008');

    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'covid' } });

    await waitFor(() => expect(api.runStressTest).toHaveBeenLastCalledWith('covid'));
    await waitFor(() =>
      expect(container.querySelector('[data-bar="stressed"]').getAttribute('fill')).toBe(CHART_THEME.green)
    );
    expect(container.textContent).toContain('QQQ');
    expect(screen.getByText('Scenario', { selector: 'span' }).nextSibling.textContent).toBe('COVID Crash');
  });

  it('shows "Stress test data unavailable" when positions are empty', async () => {
    api.getStressTestScenarios.mockResolvedValue(scenarios);
    api.runStressTest.mockResolvedValue({ positions: [], total_pnl: 0, total_pnl_percent: 0 });
    render(<StressTest />);
    expect(await screen.findByText('Stress test data unavailable')).toBeTruthy();
    expect(screen.getByText('Total P/L')).toBeTruthy();
  });
});

describe('DiscoveryScanner integration', () => {
  const row = (symbol, signal, confidence) => ({ symbol, signal, confidence, reward_to_risk: 2, tail_risk: 0.1, sector: 'technology' });
  const barFill = (symbol) =>
    screen.getByText(symbol).closest('tr').querySelector('[data-confidence-bar] rect:last-of-type').getAttribute('fill');

  it('renders the empty prompt with no chart elements before a scan', () => {
    const { container } = render(<DiscoveryScanner />);
    expect(screen.getByText('Run a scan to rank the universe.')).toBeTruthy();
    expect(container.querySelector('[data-confidence-bar]')).toBeNull();
    expect(container.querySelector('[data-signal-indicator]')).toBeNull();
  });

  it('shows a scanning state while the request is pending', () => {
    api.runDiscoveryScanner.mockReturnValue(never());
    render(<DiscoveryScanner />);
    fireEvent.click(screen.getByRole('button', { name: 'Run scan' }));
    expect(screen.getByText('Scanning...')).toBeTruthy();
  });

  it('colors confidence bars by threshold and shows direction indicators', async () => {
    api.runDiscoveryScanner.mockResolvedValue({
      results: [
        row('AAA', 'BUY', 0.68),
        row('BBB', 'SELL', 0.67),
        row('CCC', 'HOLD', 0.55),
        row('DDD', 'BUY', 0.54),
      ],
    });
    const { container } = render(<DiscoveryScanner />);
    fireEvent.click(screen.getByRole('button', { name: 'Run scan' }));
    await waitFor(() => expect(container.querySelectorAll('[data-confidence-bar]')).toHaveLength(4));

    expect(barFill('AAA')).toBe(CHART_THEME.green);
    expect(barFill('BBB')).toBe(CHART_THEME.amber);
    expect(barFill('CCC')).toBe(CHART_THEME.amber);
    expect(barFill('DDD')).toBe(CHART_THEME.red);
    expect(container.querySelector('[data-signal-indicator="BUY"]').textContent).toContain('▲');
    expect(container.querySelector('[data-signal-indicator="SELL"]').textContent).toContain('▼');
    expect(container.querySelector('[data-signal-indicator="HOLD"]').textContent).toContain('—');
  });

  it('shows the failure message and no chart elements when the scan fails', async () => {
    api.runDiscoveryScanner.mockRejectedValue(new Error('down'));
    const { container } = render(<DiscoveryScanner />);
    fireEvent.click(screen.getByRole('button', { name: 'Run scan' }));
    expect(await screen.findByText('Scan failed. Try again.')).toBeTruthy();
    expect(container.querySelector('[data-confidence-bar]')).toBeNull();
  });
});
