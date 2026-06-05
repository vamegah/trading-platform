/**
 * Unit Tests for Chart Components
 * 
 * Run with: npm test (requires Jest/Vitest setup)
 */

// Test: ChartContainer mounts and unmounts without memory leaks
describe('ChartContainer', () => {
  test('should mount without errors', () => {
    const { container } = render(
      <ChartContainer width={800} height={400}>
        <div>Test Content</div>
      </ChartContainer>
    );
    expect(container.firstChild).toBeInTheDocument();
  });

  test('should cleanup on unmount', () => {
    const { unmount } = render(
      <ChartContainer width={800} height={400}>
        <div>Test Content</div>
      </ChartContainer>
    );
    
    // Check that chart cleanup is called
    unmount();
    
    // Verify no lingering event listeners
    expect(window.removeEventListener).toHaveBeenCalled();
  });

  test('should handle resize events with debouncing', (done) => {
    jest.useFakeTimers();
    
    render(
      <ChartContainer width={800} height={400}>
        <div>Test Content</div>
      </ChartContainer>
    );
    
    // Trigger multiple resize events
    window.dispatchEvent(new Event('resize'));
    window.dispatchEvent(new Event('resize'));
    window.dispatchEvent(new Event('resize'));
    
    // Fast-forward time to trigger debounced handler
    jest.advanceTimersByTime(100);
    
    // Verify handler is called only once
    expect(applyOptions).toHaveBeenCalledTimes(1);
    
    jest.useRealTimers();
    done();
  });
});

// Test: useChartSeries hook
describe('useChartSeries', () => {
  test('should add series correctly', () => {
    const { result } = renderHook(() => useChartSeries('candlestick', []), {
      wrapper: ({ children }) => (
        <ChartContext.Provider value={mockChartInstance}>
          {children}
        </ChartContext.Provider>
      ),
    });

    const { addSeries } = result.current;
    const series = addSeries('candlestick', {}, testData);
    
    expect(series).toBeDefined();
    expect(mockChartInstance.addCandlestickSeries).toHaveBeenCalled();
  });

  test('should update series data', () => {
    const { result } = renderHook(() => useChartSeries('candlestick', testData), {
      wrapper: ({ children }) => (
        <ChartContext.Provider value={mockChartInstance}>
          {children}
        </ChartContext.Provider>
      ),
    });

    const { updateSeriesData } = result.current;
    const newData = [...testData, { time: 61, open: 100, high: 105, low: 99, close: 102 }];
    
    updateSeriesData('candlestick-123', newData);
    
    expect(mockSeriesInstance.setData).toHaveBeenCalledWith(newData);
  });

  test('should throw error for invalid series type', () => {
    const { result } = renderHook(() => useChartSeries('invalid', []), {
      wrapper: ({ children }) => (
        <ChartContext.Provider value={mockChartInstance}>
          {children}
        </ChartContext.Provider>
      ),
    });

    const { addSeries } = result.current;
    
    expect(() => {
      addSeries('invalid_type', {}, []);
    }).toThrow('Invalid series type');
  });
});

// Test: AgentScoreChart
describe('AgentScoreChart', () => {
  test('should render bars with correct colors', () => {
    const data = [
      { label: 'Fundamentals', value: 80 },
      { label: 'Technical', value: 40 },
      { label: 'Sentiment', value: 60 },
    ];

    const { container } = render(
      <AgentScoreChart data={data} width={500} height={300} maxValue={100} />
    );

    const rects = container.querySelectorAll('rect');
    
    // Check that bars are rendered
    expect(rects.length).toBeGreaterThan(0);
    
    // Verify green bar (80% > threshold 68%)
    expect(rects[0]).toHaveAttribute('fill', '#10b981');
    
    // Verify red bar (40% < threshold 38%)
    expect(rects[1]).toHaveAttribute('fill', '#ef4444');
    
    // Verify amber bar (60% is between thresholds)
    expect(rects[2]).toHaveAttribute('fill', '#f59e0b');
  });

  test('should display percentage labels', () => {
    const data = [{ label: 'Test', value: 75 }];
    
    const { container } = render(
      <AgentScoreChart data={data} width={500} height={300} showValues={true} />
    );

    const textElements = container.querySelectorAll('text');
    const labelExists = Array.from(textElements).some(el => el.textContent.includes('75%'));
    
    expect(labelExists).toBe(true);
  });

  test('should show "No data available" when data is empty', () => {
    const { container } = render(
      <AgentScoreChart data={[]} width={500} height={300} />
    );

    const text = container.querySelector('text');
    expect(text.textContent).toBe('No data available');
  });
});

// Test: ChartErrorBoundary
describe('ChartErrorBoundary', () => {
  test('should catch errors and display fallback UI', () => {
    const ThrowError = () => {
      throw new Error('Chart rendering failed');
    };

    const { container } = render(
      <ChartErrorBoundary>
        <ThrowError />
      </ChartErrorBoundary>
    );

    const fallback = container.querySelector('div');
    expect(fallback.textContent).toContain('Chart failed to load');
  });

  test('should log errors to console', () => {
    const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();
    
    const ThrowError = () => {
      throw new Error('Test error');
    };

    render(
      <ChartErrorBoundary>
        <ThrowError />
      </ChartErrorBoundary>
    );

    expect(consoleErrorSpy).toHaveBeenCalledWith('Chart Error:', expect.any(Error));
    consoleErrorSpy.mockRestore();
  });
});

// Test: Theme colors meet contrast requirements
describe('Theme Colors Contrast', () => {
  test('should have sufficient contrast ratios', () => {
    const background = '#0d0d0d';
    const colors = {
      green: '#10b981',
      red: '#ef4444',
      amber: '#f59e0b',
      grey: '#9ca3af',
      text: '#f3f4f6',
    };

    // Verify contrast ratios (simplified check)
    Object.entries(colors).forEach(([name, color]) => {
      const contrast = calculateContrastRatio(background, color);
      expect(contrast).toBeGreaterThanOrEqual(3.0);
    });
  });
});
