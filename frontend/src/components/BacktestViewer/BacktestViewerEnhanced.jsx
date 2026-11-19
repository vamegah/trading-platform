import { useEffect, useMemo, useState } from 'react';
import { AreaSeries, LineStyle, createSeriesMarkers } from '@tradingview/lightweight-charts';
import ChartContainer, { useChartSeries } from '../ChartContainer';
import ChartErrorBoundary from '../ChartErrorBoundary';
import { executePaperSignal, getTradeJournal, monitorModel, runWalkForwardBacktest, validateChampionChallenger } from '../../services/api';
import { CHART_THEME } from '../../styles/chart-theme';
import PropTypes from 'prop-types';

function equityCurveFromBacktest(backtest) {
  const curve = backtest?.full_walkforward_backtest?.equity_curve ?? backtest?.equity_curve;
  return Array.isArray(curve) ? curve.filter((v) => Number.isFinite(v)) : [];
}

function tradesFromBacktest(backtest) {
  const trades = backtest?.full_walkforward_backtest?.trades ?? backtest?.trades;
  return Array.isArray(trades) ? trades : [];
}

function tradeTimeIndex(trade, index, startDate, equityCurveLength) {
  if (Number.isFinite(trade.index)) return Math.max(0, Math.min(equityCurveLength - 1, Number(trade.index)));
  if (Number.isFinite(trade.time_index)) return Math.max(0, Math.min(equityCurveLength - 1, Number(trade.time_index)));
  if (trade.date && startDate) {
    const start = new Date(startDate);
    const date = new Date(trade.date);
    const dayOffset = Math.round((date.getTime() - start.getTime()) / 86_400_000);
    if (Number.isFinite(dayOffset)) return Math.max(0, Math.min(equityCurveLength - 1, dayOffset));
  }
  if (!equityCurveLength) return 0;
  return Math.min(equityCurveLength - 1, Math.round((index / Math.max(1, index + 1)) * (equityCurveLength - 1)));
}

const START_EQUITY = 100000;

const usd = (value) =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(value);

function EquityCurveChart({ equityCurve, trades = [], startDate }) {
  const chartRef = useChartSeries();

  useEffect(() => {
    const chart = chartRef?.current;
    if (!chart || !equityCurve || equityCurve.length < 2) return undefined;

    const finalEquity = equityCurve[equityCurve.length - 1];
    const lineColor = finalEquity > START_EQUITY ? CHART_THEME.green : CHART_THEME.red;
    const series = chart.addSeries(AreaSeries, {
      lineColor,
      topColor: `${lineColor}66`,
      bottomColor: `${lineColor}05`,
      lineWidth: 2,
      priceLineVisible: false,
      priceFormat: { type: 'custom', formatter: usd, minMove: 1 },
    });
    // Time index (1-based) is used as the time coordinate.
    series.setData(equityCurve.map((value, i) => ({ time: i + 1, value })));
    series.createPriceLine({
      price: START_EQUITY,
      color: CHART_THEME.grey,
      lineStyle: LineStyle.Dashed,
      lineWidth: 1,
      axisLabelVisible: true,
      title: 'Start',
    });
    series.createPriceLine({
      price: finalEquity,
      color: lineColor,
      lineStyle: LineStyle.Dashed,
      lineWidth: 1,
      axisLabelVisible: true,
      title: 'Final',
    });

    const markers = trades
      .map((trade, index) => {
        const side = String(trade.side || trade.action || '').toUpperCase();
        const isBuy = side === 'BUY';
        return {
          time: tradeTimeIndex(trade, index, startDate, equityCurve.length) + 1,
          position: isBuy ? 'belowBar' : 'aboveBar',
          color: isBuy ? CHART_THEME.green : CHART_THEME.red,
          shape: isBuy ? 'arrowUp' : 'arrowDown',
          text: side || 'TRADE',
        };
      })
      .sort((a, b) => a.time - b.time);
    const markerApi = createSeriesMarkers(series, markers);
    chart.timeScale().fitContent();

    return () => {
      try {
        markerApi.detach();
        chart.removeSeries(series);
      } catch {
        // chart already disposed
      }
    };
  }, [chartRef, equityCurve, startDate, trades]);

  return null;
}

function BacktestViewer({ symbol = 'MSFT' }) {
  const [backtest, setBacktest] = useState(null);
  const [validation, setValidation] = useState(null);
  const [monitor, setMonitor] = useState(null);
  const [journal, setJournal] = useState([]);
  const [isBacktestLoading, setIsBacktestLoading] = useState(true);
  const [paperStatus, setPaperStatus] = useState('idle');

  useEffect(() => {
    setIsBacktestLoading(true);
    setBacktest(null);

    runWalkForwardBacktest({ symbol, days: 252 })
      .then((data) => {
        setBacktest(data);
      })
      .catch(() => {
        setBacktest(null);
      })
      .finally(() => {
        setIsBacktestLoading(false);
      });

    validateChampionChallenger({
      model_name: 'signal_orchestrator',
      champion_scores: [0.61, 0.62, 0.63],
      challenger_scores: [0.66, 0.67, 0.68],
    })
      .then(setValidation)
      .catch(() => undefined);

    monitorModel({
      reference: [0.5, 0.52, 0.51],
      latest: [0.62, 0.63, 0.64],
      actual: [1, 0, 1],
      predicted_probability: [0.7, 0.4, 0.68],
      signal_ages_minutes: [20, 80, 180],
    })
      .then(setMonitor)
      .catch(() => undefined);

    getTradeJournal()
      .then((data) => setJournal(data.entries || []))
      .catch(() => undefined);
  }, [symbol]);

  const runPaperTrade = async () => {
    setPaperStatus('executing');
    try {
      await executePaperSignal(symbol);
      const data = await getTradeJournal();
      setJournal(data.entries || []);
      setPaperStatus('executed');
    } catch {
      setPaperStatus('error');
    }
  };

  const equityCurve = useMemo(() => equityCurveFromBacktest(backtest), [backtest]);
  const trades = useMemo(() => tradesFromBacktest(backtest), [backtest]);
  const hasEquityCurveData = equityCurve.length >= 2;
  const finalEquity = hasEquityCurveData ? equityCurve[equityCurve.length - 1] : 0;

  return (
    <article id="backtest" className="panel">
      <header>
        <div>
          <span>Backtest viewer</span>
          <strong>Walk-forward v0</strong>
        </div>
        <span className={monitor?.alert ? 'badge review' : 'badge healthy'}>
          {monitor?.alert ? 'review' : 'pass'}
        </span>
      </header>

      <section className="chart-block" aria-label="Equity curve chart section">
        <h4 className="chart-title">Equity Curve</h4>
        {isBacktestLoading ? (
          <div className="chart-placeholder chart-frame--equity">Loading equity curve...</div>
        ) : hasEquityCurveData ? (
          <ChartErrorBoundary fallback="Equity curve chart unavailable">
            <ChartContainer
              height={250}
              ariaLabel={`Area chart showing equity curve over ${equityCurve.length} periods. Starting equity: $100,000. Final equity: ${usd(finalEquity)}.`}
              options={{
                rightPriceScale: { visible: true },
                timeScale: { tickMarkFormatter: (time) => String(time) },
                localization: { timeFormatter: (time) => `Period ${time}` },
              }}
            >
              <EquityCurveChart equityCurve={equityCurve} startDate={backtest?.start_date} trades={trades} />
            </ChartContainer>
            <div className="chart-reference">
              <span>Start: $100,000</span>
              <span>End: {usd(finalEquity)}</span>
              <span>Markers: BUY ▲ below curve, SELL ▼ above curve</span>
            </div>
          </ChartErrorBoundary>
        ) : (
          <div className="chart-empty chart-frame--equity">Equity curve data unavailable</div>
        )}
      </section>

      <div className="row">
        <span>Annualized return</span>
        <strong>{backtest ? `${Math.round((backtest.metrics?.annualized_return || 0) * 100)}%` : 'pending'}</strong>
      </div>
      <div className="row">
        <span>Sharpe ratio</span>
        <strong>{backtest?.metrics?.sharpe ?? 'pending'}</strong>
      </div>
      <div className="row">
        <span>Sortino / Calmar</span>
        <strong>{backtest ? `${backtest.metrics?.sortino ?? 'n/a'} / ${backtest.metrics?.calmar ?? 'n/a'}` : 'pending'}</strong>
      </div>
      <div className="row">
        <span>Benchmark excess</span>
        <strong>{backtest ? `${Math.round((backtest.benchmark?.excess_return || 0) * 100)}%` : 'pending'}</strong>
      </div>
      <div className="row">
        <span>Champion challenger</span>
        <strong>{validation?.model_promotion_pipeline?.gate || 'pending'}</strong>
      </div>
      <div className="row">
        <span>Journal entries</span>
        <strong>{journal.length}</strong>
      </div>
      <div className="row">
        <span>Paper action</span>
        <strong>{paperStatus}</strong>
      </div>
      <button
        type="button"
        className="ghost-button"
        disabled={paperStatus === 'executing'}
        onClick={runPaperTrade}
      >
        {paperStatus === 'executing' ? 'Executing' : 'Paper execute'}
      </button>
    </article>
  );
}

BacktestViewer.propTypes = {
  symbol: PropTypes.string,
};

EquityCurveChart.propTypes = {
  equityCurve: PropTypes.array.isRequired,
  trades: PropTypes.array,
  startDate: PropTypes.string,
};

export default BacktestViewer;
