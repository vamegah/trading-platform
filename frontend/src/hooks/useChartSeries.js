import { useContext, useCallback, useRef, useEffect } from 'react';
import { ChartContext } from '../components/Charts/ChartContainer';
import {
  AreaSeries,
  CandlestickSeries,
  HistogramSeries,
  LineSeries,
  createSeriesMarkers,
} from '@tradingview/lightweight-charts';

/**
 * useChartSeries - Hook to add and manage series data within a chart
 * 
 * Provides methods to add series and update data without direct chart access.
 * Automatically handles series cleanup on unmount.
 * 
 * @param {string} seriesType - Type of series: 'candlestick', 'histogram', 'area', 'line'
 * @param {Array} initialData - Initial data for the series
 * @returns {Object} - { addSeries, updateSeriesData, series }
 */
const useChartSeries = (seriesType, initialData = []) => {
  const chart = useContext(ChartContext);
  const seriesRef = useRef(null);
  const seriesMapRef = useRef(new Map());
  const markerMapRef = useRef(new Map());
  const nextSeriesIdRef = useRef(0);

  const SERIES_METHODS = {
    candlestick: { definition: CandlestickSeries, legacyMethod: 'addCandlestickSeries' },
    histogram: { definition: HistogramSeries, legacyMethod: 'addHistogramSeries' },
    area: { definition: AreaSeries, legacyMethod: 'addAreaSeries' },
    line: { definition: LineSeries, legacyMethod: 'addLineSeries' },
  };

  const validateSeriesType = useCallback((type) => {
    if (!SERIES_METHODS[type]) {
      throw new Error(
        `Invalid series type: ${type}. Supported types: ${Object.keys(SERIES_METHODS).join(', ')}`
      );
    }
  }, []);

  const addSeries = useCallback((type, options = {}, data = []) => {
    if (!chart) {
      console.warn('Chart instance not available. useChartSeries must be used within ChartContainer.');
      return null;
    }

    try {
      validateSeriesType(type);
      const config = SERIES_METHODS[type];
      const series =
        typeof chart.addSeries === 'function'
          ? chart.addSeries(config.definition, options)
          : chart[config.legacyMethod](options);

      if (data.length > 0) {
        series.setData(data);
      }

      // Store series reference
      nextSeriesIdRef.current += 1;
      const seriesId = `${type}-${nextSeriesIdRef.current}`;
      seriesMapRef.current.set(seriesId, series);

      return { series, seriesId };
    } catch (error) {
      console.error(`Error adding ${type} series:`, error);
      return null;
    }
  }, [chart, validateSeriesType]);

  const getSeries = useCallback((seriesOrId) => {
    if (!seriesOrId) return null;
    if (typeof seriesOrId === 'string') return seriesMapRef.current.get(seriesOrId) || null;
    return seriesOrId;
  }, []);

  const updateSeriesData = useCallback((seriesId, data) => {
    const series = getSeries(seriesId);
    if (!series) {
      console.warn(`Series with ID ${seriesId} not found.`);
      return;
    }

    try {
      series.setData(data);
    } catch (error) {
      console.error('Error updating series data:', error);
    }
  }, [getSeries]);

  const createPriceLine = useCallback((seriesId, options = {}) => {
    const series = getSeries(seriesId);
    if (!series || typeof series.createPriceLine !== 'function') return null;
    try {
      return series.createPriceLine(options);
    } catch (error) {
      console.error('Error creating price line:', error);
      return null;
    }
  }, [getSeries]);

  const setSeriesMarkers = useCallback((seriesId, markers = []) => {
    const series = getSeries(seriesId);
    if (!series) return null;

    try {
      if (typeof series.setMarkers === 'function') {
        series.setMarkers(markers);
        return series;
      }

      const markerKey = typeof seriesId === 'string' ? seriesId : `series-${markers.length}`;
      const existing = markerMapRef.current.get(markerKey);
      if (existing && typeof existing.setMarkers === 'function') {
        existing.setMarkers(markers);
        return existing;
      }

      const markerApi = createSeriesMarkers(series, markers);
      markerMapRef.current.set(markerKey, markerApi);
      return markerApi;
    } catch (error) {
      console.error('Error setting series markers:', error);
      return null;
    }
  }, [getSeries]);

  const applyPriceScaleOptions = useCallback((priceScaleId, options = {}) => {
    if (!chart || typeof chart.priceScale !== 'function') return;
    try {
      chart.priceScale(priceScaleId).applyOptions(options);
    } catch (error) {
      console.error('Error applying price scale options:', error);
    }
  }, [chart]);

  const fitContent = useCallback(() => {
    if (!chart || typeof chart.timeScale !== 'function') return;
    try {
      chart.timeScale().fitContent();
    } catch (error) {
      console.error('Error fitting chart content:', error);
    }
  }, [chart]);

  const removeSeries = useCallback((seriesId) => {
    const series = getSeries(seriesId);
    if (!series || !chart) return;

    try {
      chart.removeSeries(series);
      if (typeof seriesId === 'string') {
        seriesMapRef.current.delete(seriesId);
        markerMapRef.current.delete(seriesId);
      }
    } catch (error) {
      console.error('Error removing series:', error);
    }
  }, [chart, getSeries]);

  const removeAllSeries = useCallback(() => {
    seriesMapRef.current.forEach((series) => {
      if (chart) {
        try {
          chart.removeSeries(series);
        } catch (error) {
          console.error('Error removing series:', error);
        }
      }
    });
    seriesMapRef.current.clear();
  }, [chart]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      removeAllSeries();
    };
  }, [removeAllSeries]);

  // Initialize with data if provided
  useEffect(() => {
    if (seriesType && initialData.length > 0 && !seriesRef.current) {
      const result = addSeries(seriesType, {}, initialData);
      if (result) {
        seriesRef.current = result.seriesId;
      }
    }
  }, [seriesType, initialData, addSeries]);

  return {
    addSeries,
    updateSeriesData,
    removeSeries,
    removeAllSeries,
    createPriceLine,
    setSeriesMarkers,
    applyPriceScaleOptions,
    fitContent,
    series: seriesRef.current,
  };
};

export default useChartSeries;
