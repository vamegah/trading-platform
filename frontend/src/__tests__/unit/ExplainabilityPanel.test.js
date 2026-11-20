import React from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

vi.mock('../../components/ChartContainer', async () => {
  const { createContext } = await import('react');
  return { default: () => null, ChartContext: createContext(null) };
});

import ExplainabilityPanel from '../../components/ExplainabilityPanel';
import { CHART_THEME } from '../../styles/chart-theme';

afterEach(cleanup);

const scores = {
  fundamentals: 0.7,
  technical: 0.68,
  news_sentiment: 0.5,
  macro: 0.38,
  alt_data: 0.2,
  debate: 0.45,
  tax: 0.9,
};

describe('ExplainabilityPanel agent scores', () => {
  it('renders seven bars with spaced labels, percentages and threshold colors', () => {
    render(<ExplainabilityPanel signal={{ recommendation: { component_scores: scores } }} />);
    const rows = screen.getAllByTestId('agent-score-row');
    expect(rows).toHaveLength(7);
    expect(screen.getByText('news sentiment')).toBeTruthy();
    expect(screen.getByText('alt data')).toBeTruthy();
    const fills = screen.getAllByTestId('agent-score-fill').map((el) => el.getAttribute('fill'));
    expect(fills).toEqual([
      CHART_THEME.green,
      CHART_THEME.green,
      CHART_THEME.neutral,
      CHART_THEME.red,
      CHART_THEME.red,
      CHART_THEME.neutral,
      CHART_THEME.green,
    ]);
    expect(screen.getByText('70%')).toBeTruthy();
  });

  it('shows "Agent scores unavailable" when component_scores is absent', () => {
    render(<ExplainabilityPanel signal={{ explainability: {} }} />);
    expect(screen.getByText('Agent scores unavailable')).toBeTruthy();
    expect(screen.queryAllByTestId('agent-score-row')).toHaveLength(0);
  });
});

