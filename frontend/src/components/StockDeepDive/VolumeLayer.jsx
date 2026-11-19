import { useEffect } from 'react';
import PropTypes from 'prop-types';
import useChartSeries from '../../hooks/useChartSeries';
import { formatVolumeData } from '../../utils/charts/formatters';

export const VOLUME_SCALE_ID = 'volume';

/**
 * VolumeLayer - adds volume histogram bars on a separate price scale
 * occupying the bottom of the chart. Must be rendered inside ChartContainer.
 */
function VolumeLayer({ ohlcvData }) {
  const { addSeries, applyPriceScaleOptions, removeSeries } = useChartSeries();

  useEffect(() => {
    if (!ohlcvData?.length) return undefined;

    const result = addSeries(
      'histogram',
      { priceFormat: { type: 'volume' }, priceScaleId: VOLUME_SCALE_ID },
      formatVolumeData(ohlcvData)
    );
    if (!result) return undefined;

    applyPriceScaleOptions(VOLUME_SCALE_ID, { scaleMargins: { top: 0.78, bottom: 0 } });

    return () => removeSeries(result.seriesId);
  }, [addSeries, applyPriceScaleOptions, removeSeries, ohlcvData]);

  return null;
}

VolumeLayer.propTypes = {
  ohlcvData: PropTypes.array.isRequired,
};

export default VolumeLayer;
