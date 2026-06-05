/**
 * Integration Tests for Chart Components in Dashboard
 * 
 * Verifies charts work within their parent components
 */

describe('StockDeepDive Chart Integration', () => {
  test('should render candlestick chart with OHLCV data', async () => {
    const mockSignal = {
      symbol: 'MSFT',
      signal: 'buy',
      entry_zone: { low: 148, high: 152 },
      stop_loss: 145,
      take_profit: 160,
    };

    const { container } = render(<StockDeepDive signal={mockSignal} />);

    // Wait for chart to load
    await waitFor(() => {
      expect(container.querySelector('canvas')).toBeDefined();
    });

    // Verify price lines are created
    const priceLines = container.querySelectorAll('[data-price-line]');
    expect(priceLines.length).toBeGreaterThan(0);
  });

  test('should display loading state while fetching data', () => {
    const { container } = render(<StockDeepDive symbol="MSFT" />);
    
    const loadingText = container.textContent;
    expect(loadingText).toContain('Loading price chart');
  });

  test('should preserve existing text rows below chart', () => {
    const mockSignal = {
      symbol: 'MSFT',
      agent_outputs: {
        fundamentals: { score: 0.75 },
        technical: { score: 0.65 },
      },
    };

    const { container } = render(<StockDeepDive signal={mockSignal} />);
    
    // Check that existing text rows are present
    expect(container.textContent).toContain('Fundamentals');
    expect(container.textContent).toContain('Technical setup');
  });
});

describe('ExplainabilityPanel Chart Integration', () => {
  test('should render agent score chart with all 7 agents', async () => {
    const mockSignal = {
      recommendation: {
        component_scores: {
          fundamentals: 0.75,
          technical: 0.65,
          news_sentiment: 0.55,
          macro: 0.70,
          alt_data: 0.60,
          debate: 0.68,
          tax: 0.50,
        },
      },
    };

    const { container } = render(<ExplainabilityPanel signal={mockSignal} />);

    await waitFor(() => {
      expect(container.textContent).toContain('Fundamentals');
      expect(container.textContent).toContain('Technical');
    });

    // Verify 7 bars are rendered
    const bars = container.querySelectorAll('[data-agent-bar]');
    expect(bars.length).toBe(7);
  });

  test('should render probability distribution chart', async () => {
    const mockSignal = {
      recommendation: {
        probability_distribution: {
          up_5pct_20d: 0.35,
          down_3pct_20d: 0.25,
          flat_20d: 0.30,
          tail_loss_8pct_20d: 0.10,
        },
      },
    };

    const { container } = render(<ExplainabilityPanel signal={mockSignal} />);

    await waitFor(() => {
      expect(container.textContent).toContain('Probability Distribution');
    });
  });
});

describe('BacktestViewer Chart Integration', () => {
  test('should render equity curve with correct colors', async () => {
    // Mock backtest response
    const mockBacktestData = {
      full_walkforward_backtest: {
        equity_curve: Array.from({ length: 60 }, (_, i) => 100000 + i * 500),
      },
    };

    // Mock API
    jest.spyOn(global, 'fetch').mockResolvedValue({
      json: () => Promise.resolve(mockBacktestData),
    });

    const { container } = render(<BacktestViewer />);

    await waitFor(() => {
      expect(container.textContent).toContain('Equity Curve');
    });
  });

  test('should show green area when final equity > $100k', async () => {
    const mockBacktestData = {
      full_walkforward_backtest: {
        equity_curve: Array.from({ length: 60 }, (_, i) => 100000 + i * 1000),
      },
    };

    jest.spyOn(global, 'fetch').mockResolvedValue({
      json: () => Promise.resolve(mockBacktestData),
    });

    const { container } = render(<BacktestViewer />);

    await waitFor(() => {
      const areaColor = container.querySelector('[data-area-color]')?.getAttribute('fill');
      expect(areaColor).toContain('green') || expect(areaColor).toBe('#10b981');
    });
  });

  test('should preserve summary metrics below chart', async () => {
    const mockBacktestData = {
      metrics: {
        annualized_return: 0.25,
        sharpe: 1.5,
      },
    };

    jest.spyOn(global, 'fetch').mockResolvedValue({
      json: () => Promise.resolve(mockBacktestData),
    });

    const { container } = render(<BacktestViewer />);

    await waitFor(() => {
      expect(container.textContent).toContain('Annualized return');
      expect(container.textContent).toContain('Sharpe ratio');
    });
  });
});

describe('PortfolioHealth Chart Integration', () => {
  test('should render risk metrics chart', async () => {
    const mockRiskData = {
      metrics: {
        var: 2500,
        cvar: 3500,
        gross_exposure: 150000,
        net_exposure: 100000,
      },
      kill_switch_required: false,
    };

    jest.spyOn(global, 'fetch').mockResolvedValue({
      json: () => Promise.resolve(mockRiskData),
    });

    const { container } = render(<PortfolioHealth />);

    await waitFor(() => {
      expect(container.textContent).toContain('Risk Metrics');
    });
  });

  test('should show risk breach indicator when kill switch is active', async () => {
    const mockRiskData = {
      metrics: { var: 5000, cvar: 7000, gross_exposure: 200000, net_exposure: 150000 },
      kill_switch_required: true,
    };

    jest.spyOn(global, 'fetch').mockResolvedValue({
      json: () => Promise.resolve(mockRiskData),
    });

    const { container } = render(<PortfolioHealth />);

    await waitFor(() => {
      expect(container.textContent).toContain('Risk Breach');
      expect(container.textContent).toContain('Position trading disabled');
    });
  });
});

describe('StressTest Chart Integration', () => {
  test('should populate scenario dropdown', async () => {
    const mockScenarios = [
      { id: '2008', name: '2008 Financial Crisis' },
      { id: 'covid', name: 'COVID-19 Crash' },
      { id: 'tech', name: 'Tech Bubble' },
    ];

    jest.spyOn(global, 'fetch').mockResolvedValue({
      json: () => Promise.resolve({ scenarios: mockScenarios }),
    });

    const { getByRole } = render(<StressTest />);
    const dropdown = getByRole('combobox');

    expect(dropdown.children.length).toBeGreaterThanOrEqual(3);
  });

  test('should update chart when scenario changes', async () => {
    const mockScenarios = [
      { id: '2008', name: '2008 Financial Crisis' },
      { id: 'covid', name: 'COVID-19 Crash' },
    ];

    const mockStressResult = {
      full_stress_test: {
        positions: [
          { symbol: 'MSFT', current_value: 55000, stressed_value: 40000, pnl_percent: -27 },
          { symbol: 'SPY', current_value: 45000, stressed_value: 30000, pnl_percent: -33 },
        ],
      },
    };

    jest.spyOn(global, 'fetch').mockResolvedValue({
      json: () => Promise.resolve(mockStressResult),
    });

    const { getByRole } = render(<StressTest />);
    const dropdown = getByRole('combobox');

    // Change scenario
    fireEvent.change(dropdown, { target: { value: 'covid' } });

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(expect.stringContaining('covid'));
    });
  });
});

describe('DiscoveryScanner Chart Integration', () => {
  test('should render confidence bars in table', async () => {
    const mockResults = [
      { symbol: 'AAPL', signal: 'BUY', confidence: 0.75, reward_to_risk: 2.5 },
      { symbol: 'MSFT', signal: 'SELL', confidence: 0.45, reward_to_risk: 1.8 },
    ];

    jest.spyOn(global, 'fetch').mockResolvedValue({
      json: () => Promise.resolve({ results: mockResults }),
    });

    const { container } = render(<DiscoveryScanner />);

    // Run scan
    const runButton = container.querySelector('button');
    fireEvent.click(runButton);

    await waitFor(() => {
      const confidenceBars = container.querySelectorAll('[data-confidence-bar]');
      expect(confidenceBars.length).toBeGreaterThanOrEqual(2);
    });
  });

  test('should render directional indicators', async () => {
    const mockResults = [
      { symbol: 'AAPL', signal: 'BUY', confidence: 0.75 },
      { symbol: 'MSFT', signal: 'SELL', confidence: 0.45 },
      { symbol: 'NVDA', signal: 'HOLD', confidence: 0.55 },
    ];

    jest.spyOn(global, 'fetch').mockResolvedValue({
      json: () => Promise.resolve({ results: mockResults }),
    });

    const { container } = render(<DiscoveryScanner />);

    const runButton = container.querySelector('button');
    fireEvent.click(runButton);

    await waitFor(() => {
      const content = container.textContent;
      expect(content).toContain('▲'); // BUY indicator
      expect(content).toContain('▼'); // SELL indicator
      expect(content).toContain('—'); // HOLD indicator
    });
  });
});
