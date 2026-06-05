import { useEffect, useMemo, useState } from 'react';
import ChartContainer from '../Charts/ChartContainer';
import ChartDataTable from '../Charts/ChartDataTable';
import ChartErrorBoundary from '../Charts/ChartErrorBoundary';
import useChartSeries from '../../hooks/useChartSeries';
import {
  formatCandleData,
  formatVolumeData,
  generateSampleOHLCV,
  formatCurrency,
} from '../../utils/charts/formatters';
import { colors, seriesColors } from '../../utils/charts/theme';
import PropTypes from 'prop-types';

function CandleStickChartComponent({ signal, ohlcvData }) {
  const {
    addSeries,
    applyPriceScaleOptions,
    createPriceLine,
    fitContent,
    removeSeries,
  } = useChartSeries();

  useEffect(() => {
    if (!ohlcvData.length) return undefined;

    const candles = formatCandleData(ohlcvData);
    const volume = formatVolumeData(ohlcvData);
    const candleResult = addSeries('candlestick', seriesColors.candlestick, candles);
    const volumeResult = addSeries(
      'histogram',
      {
        priceFormat: { type: 'volume' },
        priceScaleId: 'volume',
      },
      volume
    );

    if (!candleResult) return undefined;

    applyPriceScaleOptions('volume', {
      scaleMargins: {
        top: 0.78,
        bottom: 0,
      },
    });

    if (signal?.entry_zone) {
      createPriceLine(candleResult.seriesId, {
        price: signal.entry_zone.low,
        color: colors.warning,
        lineWidth: 2,
        lineStyle: 2,
        axisLabelVisible: true,
        title: 'Entry Low',
      });
      createPriceLine(candleResult.seriesId, {
        price: signal.entry_zone.high,
        color: colors.warning,
        lineWidth: 2,
        lineStyle: 2,
        axisLabelVisible: true,
        title: 'Entry High',
      });
    }

    if (signal?.stop_loss) {
      createPriceLine(candleResult.seriesId, {
        price: signal.stop_loss,
        color: colors.down,
        lineWidth: 2,
        lineStyle: 0,
        axisLabelVisible: true,
        title: 'Stop Loss',
      });
    }

    if (signal?.take_profit) {
      createPriceLine(candleResult.seriesId, {
        price: signal.take_profit,
        color: colors.up,
        lineWidth: 2,
        lineStyle: 0,
        axisLabelVisible: true,
        title: 'Take Profit',
      });
    }

    fitContent();

    return () => {
      if (volumeResult?.seriesId) removeSeries(volumeResult.seriesId);
      if (candleResult?.seriesId) removeSeries(candleResult.seriesId);
    };
  }, [
    addSeries,
    applyPriceScaleOptions,
    createPriceLine,
    fitContent,
    ohlcvData,
    removeSeries,
    signal?.entry_zone,
    signal?.stop_loss,
    signal?.take_profit,
  ]);

  return null;
}

const percent = (value = 0) => `${Math.round(value * 100)}%`;

function score(agent, fallback = 0) {
  if (!agent) return fallback;
  if (typeof agent.score === 'number') return agent.score > 1 ? agent.score / 100 : agent.score;
  if (typeof agent.confidence === 'number') return agent.confidence > 1 ? agent.confidence / 100 : agent.confidence;
  if (typeof agent.liquidity_score === 'number') {
    return agent.liquidity_score > 1 ? agent.liquidity_score / 100 : agent.liquidity_score;
  }
  return fallback;
}

function startingPrice(signal) {
  if (signal?.entry_zone?.low && signal?.entry_zone?.high) {
    return (Number(signal.entry_zone.low) + Number(signal.entry_zone.high)) / 2;
  }
  if (signal?.stop_loss && signal?.take_profit) {
    return (Number(signal.stop_loss) + Number(signal.take_profit)) / 2;
  }
  return 150;
}

function StockDeepDive({ signal, symbol = 'MSFT', priceData }) {
  const [chartStatus, setChartStatus] = useState('loading');
  const agents = signal?.agent_outputs || {};
  const recommendation = (signal?.signal || 'loading').toLowerCase();
  const fundamentals = score(agents.fundamentals);
  const technical = score(agents.technical);
  const sentiment = score(agents.news_sentiment);
  const macro = score(agents.macro);
  const tailRisk =
    typeof signal?.tail_risk_summary === 'object'
      ? signal.tail_risk_summary.tail_loss_probability
      : signal?.probability_distribution?.tail_loss_8pct_20d;
  const expectedReturn = signal?.return_distribution?.expected_return_20d;
  const topFactor = Object.entries(signal?.factor_exposures || {}).sort((left, right) => right[1] - left[1])[0];

  const ohlcvData = useMemo(() => {
    if (Array.isArray(priceData)) return priceData;
    return generateSampleOHLCV(60, startingPrice(signal));
  }, [priceData, signal]);

  useEffect(() => {
    setChartStatus('loading');
    const timer = window.setTimeout(() => setChartStatus('ready'), 150);
    return () => window.clearTimeout(timer);
  }, [symbol, signal]);

  const hasPriceData = ohlcvData.length >= 60;
  const latestCandle = ohlcvData[ohlcvData.length - 1];

  return (
    <article className="panel">
      <header>
        <div>
          <span>Stock deep dive</span>
          <strong>{signal?.symbol || symbol}</strong>
        </div>
        <span
          className={`badge ${
            recommendation === 'buy' ? 'buy' : recommendation === 'sell' ? 'review' : 'hold'
          }`}
        >
          {recommendation}
        </span>
      </header>

      <section className="chart-block" aria-label="Price chart section">
        {chartStatus === 'loading' ? (
          <div className="chart-placeholder chart-frame--price">Loading price chart...</div>
        ) : hasPriceData ? (
          <ChartErrorBoundary componentName="StockDeepDiveChart" fallbackHeight={300}>
            <div className="chart-frame chart-frame--price">
              <ChartContainer
                aria-label={`Candlestick chart showing ${ohlcvData.length} OHLCV data points for ${symbol} with volume bars, entry zone, stop-loss, and take-profit levels when available`}
                height={300}
                monitoringName="StockDeepDiveCandlestick"
                options={{ timeScale: { timeVisible: true } }}
                role="img"
                width={800}
              >
                <CandleStickChartComponent ohlcvData={ohlcvData} signal={signal} />
              </ChartContainer>
            </div>
            <ChartDataTable
              caption={`${symbol} OHLCV data used by the candlestick chart`}
              columns={[
                { key: 'time', label: 'Time' },
                { key: 'open', label: 'Open' },
                { key: 'high', label: 'High' },
                { key: 'low', label: 'Low' },
                { key: 'close', label: 'Close' },
                { key: 'volume', label: 'Volume' },
              ]}
              rows={ohlcvData.map((row) => ({
                id: row.time,
                time: row.time,
                open: row.open,
                high: row.high,
                low: row.low,
                close: row.close,
                volume: row.volume,
              }))}
            />
          </ChartErrorBoundary>
        ) : (
          <div className="chart-empty chart-frame--price">Price data unavailable</div>
        )}
      </section>

      <div className="row">
        <span>Fundamentals</span>
        <strong>{percent(fundamentals)}</strong>
      </div>
      <div className="row">
        <span>Technical setup</span>
        <strong>{percent(technical)}</strong>
      </div>
      <div className="row">
        <span>Sentiment</span>
        <strong>{percent(sentiment)}</strong>
      </div>
      <div className="row">
        <span>Macro context</span>
        <strong>{agents.macro?.regime || percent(macro)}</strong>
      </div>
      <div className="row">
        <span>Entry zone</span>
        <strong>{signal?.entry_zone ? `${formatCurrency(signal.entry_zone.low)} - ${formatCurrency(signal.entry_zone.high)}` : 'pending'}</strong>
      </div>
      <div className="row">
        <span>Expected return</span>
        <strong>{typeof expectedReturn === 'number' ? percent(expectedReturn) : 'pending'}</strong>
      </div>
      <div className="row">
        <span>Tail risk</span>
        <strong>{typeof tailRisk === 'number' ? percent(tailRisk) : 'pending'}</strong>
      </div>
      <div className="row">
        <span>Latest close</span>
        <strong>{latestCandle ? formatCurrency(latestCandle.close) : 'pending'}</strong>
      </div>
      <div className="row">
        <span>Position size</span>
        <strong>{signal?.position_size ? formatCurrency(signal.position_size) : 'pending'}</strong>
      </div>
      <div className="row">
        <span>Top factor</span>
        <strong>{topFactor ? `${topFactor[0].replaceAll('_', ' ')} ${percent(topFactor[1])}` : 'pending'}</strong>
      </div>
      <div className="rationale-list">
        {(signal?.rationale || ['Signal rationale will appear after analysis.']).map((item) => (
          <p key={item}>{item}</p>
        ))}
      </div>
    </article>
  );
}

StockDeepDive.propTypes = {
  signal: PropTypes.object,
  symbol: PropTypes.string,
  priceData: PropTypes.array,
};

CandleStickChartComponent.propTypes = {
  signal: PropTypes.object,
  ohlcvData: PropTypes.array.isRequired,
};

export default StockDeepDive;
