/**
 * Unit tests for StockDeepDive candlestick + volume chart (Requirement 3).
 * Run with: npx vitest run (from frontend/)
 */
import React from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';

const lw = vi.hoisted(() => {
  const state = { chart: null, series: [] };
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
  return {
    state,
    createChart: vi.fn(() => {
      state.chart = makeChart();
      return state.chart;
    }),
  };
});

vi.mock('@tradingview/lightweight-charts', () => ({
  createChart: lw.createChart,
  CandlestickSeries: 'CandlestickSeries',
  HistogramSeries: 'HistogramSeries',
  AreaSeries: 'AreaSeries',
  LineSeries: 'LineSeries',
  createSeriesMarkers: vi.fn(),
}));

import StockDeepDive from '../../components/StockDeepDive';
import { generateSampleOHLCV } from '../../utils/charts/formatters';

const signal = {
  symbol: 'MSFT',
  signal: 'buy',
  entry_zone: { low: 148, high: 152 },
  stop_loss: 145,
  take_profit: 160,
};

beforeEach(() => {
  lw.state.series = [];
  lw.state.chart = null;
  lw.createChart.mockClear();
});
afterEach(cleanup);

describe('StockDeepDive chart', () => {
  it('shows a placeholder and creates no chart while loading', () => {
    const { container } = render(<StockDeepDive signal={signal} />);
    expect(container.querySelector('.chart-placeholder')).toBeTruthy();
    expect(lw.createChart).not.toHaveBeenCalled();
  });

  it('adds candlestick (60+ candles) and volume series on a separate scale with price lines', async () => {
    const data = generateSampleOHLCV(60, 150);
    render(<StockDeepDive signal={signal} priceData={data} />);
    await waitFor(() => expect(lw.state.series.length).toBe(2));

    const [candles, volume] = lw.state.series;
    expect(candles.definition).toBe('CandlestickSeries');
    expect(candles.setData.mock.calls[0][0].length).toBeGreaterThanOrEqual(60);
    expect(volume.definition).toBe('HistogramSeries');
    expect(volume.options.priceScaleId).toBe('volume');
    expect(volume.setData.mock.calls[0][0].length).toBe(candles.setData.mock.calls[0][0].length);

    const lines = candles.createPriceLine.mock.calls.map(([o]) => [o.price, o.title]);
    expect(lines).toEqual(
      expect.arrayContaining([
        [148, 'Entry Low'],
        [152, 'Entry High'],
        [145, 'Stop Loss'],
        [160, 'Take Profit'],
      ])
    );
    const colorOf = (title) => candles.createPriceLine.mock.calls.find(([o]) => o.title === title)[0].color;
    expect(colorOf('Stop Loss')).not.toBe(colorOf('Take Profit'));
  });

  it('omits price lines when signal levels are absent', async () => {
    render(<StockDeepDive signal={{ symbol: 'MSFT' }} priceData={generateSampleOHLCV(60, 150)} />);
    await waitFor(() => expect(lw.state.series.length).toBe(2));
    expect(lw.state.series[0].createPriceLine).not.toHaveBeenCalled();
  });

  it('shows "Price data unavailable" and creates no chart for empty data', async () => {
    render(<StockDeepDive signal={signal} priceData={[]} />);
    expect(await screen.findByText('Price data unavailable')).toBeTruthy();
    expect(lw.createChart).not.toHaveBeenCalled();
  });

  it('keeps the existing text rows', async () => {
    render(<StockDeepDive signal={signal} priceData={[]} />);
    for (const label of ['Fundamentals', 'Technical setup', 'Sentiment', 'Macro context', 'Entry zone']) {
      expect(screen.getByText(label)).toBeTruthy();
    }
  });
});
