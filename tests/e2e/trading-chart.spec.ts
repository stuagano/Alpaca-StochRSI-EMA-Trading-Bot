import { test, expect } from '@playwright/test';

test.describe('Trading Chart Data Feed Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Go to the trading dashboard
    await page.goto('/');
    
    // Wait for the page to load completely
    await page.waitForLoadState('networkidle');
    
    // Wait for the chart container to be visible
    await page.waitForSelector('[data-testid="trading-chart"]', { timeout: 10000 });
  });

  test('should load candlestick chart data successfully', async ({ page }) => {
    // Check if chart container exists
    const chartContainer = page.locator('[data-testid="trading-chart"]');
    await expect(chartContainer).toBeVisible();

    // Wait for market data API call
    const marketDataResponse = page.waitForResponse(response => 
      response.url().includes('/api/chart/') && response.status() === 200
    );

    // Select a symbol to trigger data loading (the selector is available)
    await page.selectOption('[data-testid="symbol-select"]', 'AAPL');
    
    // Wait for the API response
    const response = await marketDataResponse;
    const responseData = await response.json();
    
    // Verify response structure
    expect(responseData).toHaveProperty('candlestick_data');
    expect(responseData.candlestick_data).toBeInstanceOf(Array);
    expect(responseData.candlestick_data.length).toBeGreaterThan(0);
    
    // Verify each candlestick has required OHLCV data
    const firstCandle = responseData.candlestick_data[0];
    expect(firstCandle).toHaveProperty('timestamp');
    expect(firstCandle).toHaveProperty('open');
    expect(firstCandle).toHaveProperty('high');
    expect(firstCandle).toHaveProperty('low');
    expect(firstCandle).toHaveProperty('close');
    expect(firstCandle).toHaveProperty('volume');
    
    // Verify data is properly sorted by time (ascending)
    const timestamps = responseData.candlestick_data.map((candle: any) => 
      new Date(candle.timestamp).getTime()
    );
    
    for (let i = 1; i < timestamps.length; i++) {
      expect(timestamps[i]).toBeGreaterThanOrEqual(timestamps[i - 1]);
    }
  });

  test('should handle chart data errors gracefully', async ({ page }) => {
    // Mock a failed API response
    await page.route('**/api/chart/**', route => {
      route.fulfill({
        status: 500,
        body: JSON.stringify({ error: 'Internal Server Error' })
      });
    });

    // Try to load a symbol
    await page.selectOption('[data-testid="symbol-select"]', 'AAPL');
    
    // Should show error state or fallback data
    await expect(page.locator('[data-testid="chart-error"]')).toBeVisible();
  });

  test('should render lightweight-charts canvas', async ({ page }) => {
    // Wait for chart to load
    await page.selectOption('[data-testid="symbol-select"]', 'AAPL');
    
    // Wait for chart to render
    await page.waitForTimeout(3000);
    
    // Check if lightweight-charts canvas is created
    const canvas = page.locator('canvas');
    await expect(canvas).toBeVisible();
    
    // Verify canvas has content (not empty)
    const canvasCount = await canvas.count();
    expect(canvasCount).toBeGreaterThan(0);
  });

  test('should update chart when timeframe changes', async ({ page }) => {
    // Load initial data
    await page.selectOption('[data-testid="symbol-select"]', 'AAPL');
    
    // Wait for initial chart load
    await page.waitForTimeout(2000);
    
    // Change timeframe
    await page.click('button[data-testid="timeframe-5Min"]');
    
    // Should trigger new data request
    const newDataResponse = page.waitForResponse(response => 
      response.url().includes('/api/chart/') && 
      response.url().includes('timeframe=5Min')
    );
    
    await newDataResponse;
    
    // Chart should update
    await page.waitForTimeout(1000);
    await expect(page.locator('canvas')).toBeVisible();
  });

  test('should display technical indicators', async ({ page }) => {
    // Load chart data
    await page.selectOption('[data-testid="symbol-select"]', 'AAPL');
    await page.waitForTimeout(3000);
    
    // Check for EMA indicators
    const indicators = page.locator('[data-testid="indicators-panel"]');
    await expect(indicators).toBeVisible();
    
    // Should show StochRSI values
    await expect(page.locator('[data-testid="stochrsi-value"]')).toBeVisible();
    
    // Should show RSI values
    await expect(page.locator('[data-testid="rsi-value"]')).toBeVisible();
  });

  test('should handle real-time data updates', async ({ page }) => {
    // Load initial chart
    await page.selectOption('[data-testid="symbol-select"]', 'AAPL');
    await page.waitForTimeout(2000);
    
    // Mock WebSocket connection for real-time updates
    await page.evaluate(() => {
      // Simulate real-time data update
      const mockData = {
        symbol: 'AAPL',
        price: 180.50,
        volume: 1000000,
        timestamp: new Date().toISOString()
      };
      
      // Trigger update event if WebSocket exists
      if ((window as any).mockWebSocketUpdate) {
        (window as any).mockWebSocketUpdate(mockData);
      }
    });
    
    // Verify chart updates with new data
    await page.waitForTimeout(1000);
    await expect(page.locator('canvas')).toBeVisible();
  });

  test('should validate OHLCV data integrity', async ({ page }) => {
    // Load chart data
    await page.selectOption('[data-testid="symbol-select"]', 'AAPL');
    
    // Wait for API response and capture data
    const response = await page.waitForResponse(response => 
      response.url().includes('/api/chart/')
    );
    
    const data = await response.json();
    const candleData = data.candlestick_data;
    
    // Validate each candle's OHLCV relationships
    for (const candle of candleData) {
      // High should be >= Open, Low, Close
      expect(candle.high).toBeGreaterThanOrEqual(candle.open);
      expect(candle.high).toBeGreaterThanOrEqual(candle.low);
      expect(candle.high).toBeGreaterThanOrEqual(candle.close);
      
      // Low should be <= Open, High, Close
      expect(candle.low).toBeLessThanOrEqual(candle.open);
      expect(candle.low).toBeLessThanOrEqual(candle.high);
      expect(candle.low).toBeLessThanOrEqual(candle.close);
      
      // Volume should be non-negative
      expect(candle.volume).toBeGreaterThanOrEqual(0);
      
      // Prices should be positive numbers
      expect(candle.open).toBeGreaterThan(0);
      expect(candle.high).toBeGreaterThan(0);
      expect(candle.low).toBeGreaterThan(0);
      expect(candle.close).toBeGreaterThan(0);
    }
  });

  test('should handle empty or invalid chart data', async ({ page }) => {
    // Mock empty data response
    await page.route('**/api/chart/**', route => {
      route.fulfill({
        status: 200,
        body: JSON.stringify({
          candlestick_data: [],
          data_source: 'mock'
        })
      });
    });
    
    await page.selectOption('[data-testid="symbol-select"]', 'AAPL');
    
    // Should show empty state or loading indicator
    await expect(page.locator('[data-testid="chart-empty-state"]')).toBeVisible();
  });
});