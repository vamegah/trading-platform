import { useEffect, useMemo, useState } from 'react';
import ChartContainer from '../Charts/ChartContainer';
import ChartDataTable from '../Charts/ChartDataTable';
import ChartErrorBoundary from '../Charts/ChartErrorBoundary';
import useChartSeries from '../../hooks/useChartSeries';
import { executePaperSignal, getTradeJournal, monitorModel, runWalkForwardBacktest, validateChampionChallenger } from '../../services/api';
import { formatAreaData, formatCurrency } from '../../utils/charts/formatters';
import { colors } from '../../utils/charts/theme';
import PropTypes from 'prop-types';

function equityCurveFromBacktest(backtest) {
  return backtest?.equity_curve || backtest?.full_walkforward_backtest?.equity_curve || [];
}

function tradesFromBacktest(backtest) {
  return backtest?.trades || backtest?.full_walkforward_backtest?.trades || [];
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

function EquityCurveChart({ equityCurve, trades = [], startDate }) {
  const { addSeries, fitContent, removeSeries, setSeriesMarkers } = useChartSeries();

  useEffect(() => {
    if (!equityCurve || equityCurve.length < 2) return undefined;

    const formattedData = formatAreaData(equityCurve);
    const finalEquity = equityCurve[equityCurve.length - 1];
    const profitable = finalEquity > 100000;
    const result = addSeries(
      'area',
      {
        topColor: profitable ? `${colors.up}55` : `${colors.down}55`,
        bottomColor: '#00000000',
        lineColor: profitable ? colors.up : colors.down,
        lineWidth: 2,
        priceFormat: {
          type: 'custom',
          formatter: (value) => formatCurrency(value),
        },
      },
      formattedData
    );

    if (result?.seriesId) {
      const markers = trades.map((trade, index) => {
        const side = String(trade.side || trade.action || '').toUpperCase();
        const isBuy = side === 'BUY';
        return {
          time: tradeTimeIndex(trade, index, startDate, equityCurve.length),
          position: isBuy ? 'belowBar' : 'aboveBar',
          color: isBuy ? colors.up : colors.down,
          shape: isBuy ? 'arrowUp' : 'arrowDown',
          text: side || 'TRADE',
        };
      });
      setSeriesMarkers(result.seriesId, markers);
    }

    fitContent();

    return () => {
      if (result?.seriesId) removeSeries(result.seriesId);
    };
  }, [addSeries, equityCurve, fitContent, removeSeries, setSeriesMarkers, startDate, trades]);

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

  const equityCurve = equityCurveFromBacktest(backtest);
  const trades = tradesFromBacktest(backtest);
  const hasEquityCurveData = equityCurve.length >= 2;
  const finalEquity = hasEquityCurveData ? equityCurve[equityCurve.length - 1] : 0;
  const areaColor = finalEquity > 100000 ? colors.up : colors.down;
  const equityRows = useMemo(
    () =>
      equityCurve.map((value, index) => ({
        id: index,
        period: index,
        equity: formatCurrency(value),
      })),
    [equityCurve]
  );

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
          <ChartErrorBoundary componentName="BacktestEquityCurve" fallbackHeight={250}>
            <div className="chart-frame chart-frame--equity">
              <ChartContainer
                aria-label={`Area chart showing equity curve over ${equityCurve.length} periods. Starting equity: $100,000. Final equity: ${formatCurrency(finalEquity)}.`}
                data-area-color={areaColor}
                height={250}
                monitoringName="BacktestEquityCurve"
                options={{
                  rightPriceScale: { visible: true },
                }}
                role="img"
                width={800}
              >
                <EquityCurveChart equityCurve={equityCurve} startDate={backtest?.start_date} trades={trades} />
              </ChartContainer>
            </div>
            <div className="chart-reference">
              <span>Start: $100,000</span>
              <span>End: {formatCurrency(finalEquity)}</span>
              <span>Markers: BUY below curve, SELL above curve</span>
            </div>
            <ChartDataTable
              caption="Walk-forward equity curve values"
              columns={[
                { key: 'period', label: 'Period' },
                { key: 'equity', label: 'Equity' },
              ]}
              rows={equityRows}
            />
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
