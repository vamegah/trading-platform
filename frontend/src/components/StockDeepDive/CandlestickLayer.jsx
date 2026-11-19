import { useEffect } from 'react';
import PropTypes from 'prop-types';
import useChartSeries from '../../hooks/useChartSeries';
import { formatCandleData } from '../../utils/charts/formatters';
import { colors, seriesColors } from '../../utils/charts/theme';

const present = (value) => value !== undefined && value !== null && value !== '' && Number.isFinite(Number(value));

/**
 * CandlestickLayer - adds the candlestick series plus entry-zone, stop-loss
 * and take-profit price lines. Must be rendered inside ChartContainer.
 */
function CandlestickLayer({ ohlcvData, signal }) {
  const { addSeries, createPriceLine, fitContent, removeSeries } = useChartSeries();
  const entryLow = signal?.entry_zone?.low;
  const entryHigh = signal?.entry_zone?.high;
  const stopLoss = signal?.stop_loss;
  const takeProfit = signal?.take_profit;

  useEffect(() => {
    if (!ohlcvData?.length) return undefined;

    const result = addSeries('candlestick', seriesColors.candlestick, formatCandleData(ohlcvData));
    if (!result) return undefined;
    const { seriesId } = result;

    const line = (price, color, lineStyle, title) =>
      createPriceLine(seriesId, {
        price: Number(price),
        color,
        lineWidth: 2,
        lineStyle,
        axisLabelVisible: true,
        title,
      });

    if (present(entryLow)) line(entryLow, colors.warning, 2, 'Entry Low');
    if (present(entryHigh)) line(entryHigh, colors.warning, 2, 'Entry High');
    if (present(stopLoss)) line(stopLoss, colors.down, 0, 'Stop Loss');
    if (present(takeProfit)) line(takeProfit, colors.up, 0, 'Take Profit');

    fitContent();

    return () => removeSeries(seriesId);
  }, [addSeries, createPriceLine, fitContent, removeSeries, ohlcvData, entryLow, entryHigh, stopLoss, takeProfit]);

  return null;
}

CandlestickLayer.propTypes = {
  ohlcvData: PropTypes.array.isRequired,
  signal: PropTypes.object,
};

export default CandlestickLayer;
