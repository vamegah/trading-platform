/**
 * Unit tests for the shared chart components.
 * Run with: npx vitest run (from frontend/)
 */
import React from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, render, screen } from '@testing-library/react';

const chartMock = vi.hoisted(() => ({
  chart: { applyOptions: vi.fn(), remove: vi.fn() },
  createChart: vi.fn(),
}));

vi.mock('@tradingview/lightweight-charts', () => ({
  createChart: chartMock.createChart,
}));

import ChartContainer from '../../components/ChartContainer';
import AgentScoreChart, {
  scoreColor,
  BUY_THRESHOLD,
  SELL_THRESHOLD,
} from '../../components/AgentScoreChart';
import ChartErrorBoundary from '../../components/ChartErrorBoundary';
import { CHART_THEME } from '../../styles/chart-theme';

afterEach(cleanup);

describe('ChartContainer', () => {
  let observers;

  beforeEach(() => {
    vi.useFakeTimers();
    observers = [];
    chartMock.chart.applyOptions.mockClear();
    chartMock.chart.remove.mockClear();
    chartMock.createChart.mockReset();
    chartMock.createChart.mockReturnValue(chartMock.chart);
    globalThis.ResizeObserver = class {
      constructor(cb) {
        this.cb = cb;
        this.observe = vi.fn();
        this.disconnect = vi.fn();
        observers.push(this);
      }
    };
  });

  afterEach(() => {
    vi.useRealTimers();
    delete globalThis.ResizeObserver;
  });

  it('calls createChart on mount and chart.remove on unmount', () => {
    const { unmount } = render(<ChartContainer ariaLabel="test chart" />);
    expect(chartMock.createChart).toHaveBeenCalledTimes(1);
    expect(chartMock.chart.remove).not.toHaveBeenCalled();

    unmount();
    expect(chartMock.chart.remove).toHaveBeenCalledTimes(1);
    expect(observers[0].disconnect).toHaveBeenCalled();
  });

  it('renders an accessible img container', () => {
    render(<ChartContainer ariaLabel="price chart" />);
    expect(screen.getByRole('img', { name: 'price chart' })).toBeTruthy();
  });

  it('applies new width/height via applyOptions on resize', () => {
    const { container } = render(<ChartContainer />);
    const el = container.firstChild;
    Object.defineProperty(el, 'clientWidth', { value: 640, configurable: true });
    Object.defineProperty(el, 'clientHeight', { value: 300, configurable: true });
    chartMock.chart.applyOptions.mockClear();

    act(() => {
      observers[0].cb([]);
      vi.advanceTimersByTime(100);
    });

    expect(chartMock.chart.applyOptions).toHaveBeenCalledWith(
      expect.objectContaining({ width: 640, height: 260 })
    );
  });
});

describe('scoreColor', () => {
  it('exports the documented thresholds', () => {
    expect(SELL_THRESHOLD).toBe(0.38);
    expect(BUY_THRESHOLD).toBe(0.68);
  });

  it('returns red at or below 0.38', () => {
    expect(scoreColor(0.38)).toBe(CHART_THEME.red);
    expect(scoreColor(0.1)).toBe(CHART_THEME.red);
  });

  it('returns green at or above 0.68', () => {
    expect(scoreColor(0.68)).toBe(CHART_THEME.green);
    expect(scoreColor(0.95)).toBe(CHART_THEME.green);
  });

  it('returns neutral strictly between the thresholds', () => {
    expect(scoreColor(0.39)).toBe(CHART_THEME.neutral);
    expect(scoreColor(0.5)).toBe(CHART_THEME.neutral);
    expect(scoreColor(0.67)).toBe(CHART_THEME.neutral);
  });
});

describe('AgentScoreChart', () => {
  // Track width in viewBox units: 600 - 130 (label) - 52 (value) - 12 (pad).
  const TRACK_W = 406;

  it('sizes each fill proportionally to value / maxValue', () => {
    const bars = [
      { label: 'a', value: 0.5, color: '#111111' },
      { label: 'b', value: 25, maxValue: 100, color: '#222222' },
      { label: 'c', value: 2, maxValue: 1, color: '#333333' },
      { label: 'd', value: 0, color: '#444444' },
    ];
    render(<AgentScoreChart bars={bars} ariaLabel="scores" />);
    const widths = screen
      .getAllByTestId('agent-score-fill')
      .map((r) => Number(r.getAttribute('width')));

    expect(widths[0]).toBeCloseTo(0.5 * TRACK_W);
    expect(widths[1]).toBeCloseTo(0.25 * TRACK_W);
    expect(widths[2]).toBeCloseTo(TRACK_W); // capped at 100%
    expect(widths[3]).toBe(0);
  });

  it('renders percentage text, bar colors, and an accessible title', () => {
    render(
      <AgentScoreChart
        bars={[{ label: 'x', value: 0.75, color: CHART_THEME.green }]}
        ariaLabel="agent scores"
      />
    );
    expect(screen.getByRole('img', { name: 'agent scores' })).toBeTruthy();
    expect(screen.getByText('75%')).toBeTruthy();
    expect(screen.getByTestId('agent-score-fill').getAttribute('fill')).toBe(CHART_THEME.green);
  });

  it('shows labels with underscores replaced by spaces', () => {
    // Consumers pass labels through the same replacement used in ExplainabilityPanel.
    const bars = ['news_sentiment', 'alt_data'].map((key) => ({
      label: key.replace(/_/g, ' '),
      value: 0.5,
    }));
    render(<AgentScoreChart bars={bars} />);
    expect(screen.getByText('news sentiment')).toBeTruthy();
    expect(screen.getByText('alt data')).toBeTruthy();
    expect(screen.queryByText(/_/)).toBeNull();
  });

  it('renders no rows for an empty bars array', () => {
    render(<AgentScoreChart bars={[]} />);
    expect(screen.queryAllByTestId('agent-score-row')).toHaveLength(0);
  });
});

describe('ChartErrorBoundary', () => {
  const Boom = () => {
    throw new Error('render failed');
  };

  beforeEach(() => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders default fallback text when a child throws', () => {
    render(
      <ChartErrorBoundary>
        <Boom />
      </ChartErrorBoundary>
    );
    const alert = screen.getByRole('alert');
    expect(alert.textContent).toBe('Chart unavailable');
    expect(alert.className).toBe('chart-error');
  });

  it('renders a custom fallback when provided', () => {
    render(
      <ChartErrorBoundary fallback="Price data unavailable">
        <Boom />
      </ChartErrorBoundary>
    );
    expect(screen.getByRole('alert').textContent).toBe('Price data unavailable');
  });

  it('renders children when nothing throws', () => {
    render(
      <ChartErrorBoundary>
        <span>ok</span>
      </ChartErrorBoundary>
    );
    expect(screen.getByText('ok')).toBeTruthy();
    expect(screen.queryByRole('alert')).toBeNull();
  });
});
