const { test, expect } = require('@playwright/test');

test.describe('TradingView Charts Integration', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the trading page where TradingView charts are implemented
    await page.goto('http://localhost:9100/trading');
  });

  test('trading page loads with TradingView charts container', async ({ page }) => {
    // Wait for the page to load
    await expect(page.locator('h1')).toContainText('Trading Execution');
    
    // Check that chart container exists
    await expect(page.locator('#chart')).toBeVisible();
    
    // Check that TradingView script is loaded
    const scripts = await page.locator('script[src*="lightweight-charts"]').count();
    expect(scripts).toBeGreaterThan(0);
  });

  test('chart data loads and displays candlestick chart', async ({ page }) => {
    // Wait for chart container to be visible
    await expect(page.locator('#chart')).toBeVisible();
    
    // Wait for chart to initialize (check for canvas element)
    await page.waitForSelector('canvas', { timeout: 10000 });
    
    // Verify canvas elements are present (TradingView creates canvas elements)
    const canvasElements = await page.locator('canvas').count();
    expect(canvasElements).toBeGreaterThan(0);
    
    // Check that chart has some content (not just empty)
    const chartContainer = page.locator('#chart');
    const chartBounds = await chartContainer.boundingBox();
    expect(chartBounds.width).toBeGreaterThan(100);
    expect(chartBounds.height).toBeGreaterThan(100);
  });

  test('timeframe selector works and updates chart', async ({ page }) => {
    // Wait for chart to load initially
    await page.waitForSelector('canvas', { timeout: 10000 });
    
    // Check that 5m timeframe is active initially
    await expect(page.locator('.timeframe-btn.active')).toContainText('5m');
    
    // Click on 1h timeframe - use force click for mobile compatibility
    await page.locator('[data-timeframe="1Hour"]').click({ force: true });
    
    // Verify 1h becomes active
    await expect(page.locator('.timeframe-btn.active')).toContainText('1h');
    
    // Wait a moment for chart to update
    await page.waitForTimeout(1000);
    
    // Verify chart still has canvas elements after timeframe change
    const canvasElements = await page.locator('canvas').count();
    expect(canvasElements).toBeGreaterThan(0);
  });

  test('symbol input changes chart data', async ({ page }) => {
    // Wait for initial chart load
    await page.waitForSelector('canvas', { timeout: 10000 });
    
    // Verify initial symbol is AAPL
    const symbolInput = page.locator('#symbol');
    await expect(symbolInput).toHaveValue('AAPL');
    
    // Change symbol to MSFT
    await symbolInput.fill('MSFT');
    await symbolInput.press('Enter');
    
    // Wait for chart to update
    await page.waitForTimeout(2000);
    
    // Verify chart still renders after symbol change
    const canvasElements = await page.locator('canvas').count();
    expect(canvasElements).toBeGreaterThan(0);
  });

  test('indicators toggles work properly', async ({ page }) => {
    // Wait for chart to load
    await page.waitForSelector('canvas', { timeout: 10000 });
    
    // Wait for indicators panel to be visible
    await expect(page.locator('.indicators-panel')).toBeVisible();
    
    // Check that EMA toggle exists and is checked by default
    const emaToggle = page.locator('#ema-toggle');
    await expect(emaToggle).toBeChecked();
    
    // Click the toggle label to toggle EMA off - use force click for mobile compatibility
    const emaToggleLabel = page.locator('label.toggle-switch').filter({ has: emaToggle });
    await emaToggleLabel.click({ force: true });
    
    // Verify EMA is now unchecked
    await expect(emaToggle).not.toBeChecked();
    
    // Toggle volume indicator
    const volumeToggle = page.locator('#volume-toggle');
    await expect(volumeToggle).toBeChecked();
    
    const volumeToggleLabel = page.locator('label.toggle-switch').filter({ has: volumeToggle });
    await volumeToggleLabel.click({ force: true });
    
    // Verify volume is now unchecked
    await expect(volumeToggle).not.toBeChecked();
    
    // Wait for changes to apply
    await page.waitForTimeout(1000);
    
    // Verify chart still renders after indicator changes
    const canvasElements = await page.locator('canvas').count();
    expect(canvasElements).toBeGreaterThan(0);
  });

  test('trading signals load and display', async ({ page }) => {
    // Wait for signals to load - just check that element exists and has content
    await page.waitForFunction(() => {
      const signalElement = document.getElementById('signal-type');
      const valueElement = document.getElementById('signal-value');
      return signalElement && signalElement.textContent.length > 0 && 
             valueElement && valueElement.textContent.length > 0;
    }, { timeout: 10000 });
    
    // Check signal display - NEUTRAL is a valid signal state
    const signalType = page.locator('#signal-type');
    const signalText = await signalType.textContent();
    expect(['BUY', 'SELL', 'NEUTRAL']).toContain(signalText);
    
    // Check signal strength
    const signalValue = page.locator('#signal-value');
    const strengthText = await signalValue.textContent();
    expect(strengthText).toMatch(/^\d+%$/);
  });

  test('order form functionality works', async ({ page }) => {
    // Wait for page to load
    await page.waitForSelector('#symbol');
    
    // Fill order form
    await page.fill('#symbol', 'AAPL');
    await page.fill('#quantity', '10');
    
    // Switch to limit order
    await page.click('[data-type="limit"]');
    await expect(page.locator('.order-type-tab.active')).toContainText('Limit');
    
    // Verify limit price field becomes visible
    await expect(page.locator('#limit-price-group')).toBeVisible();
    
    // Fill limit price
    await page.fill('#limit-price', '150.00');
    
    // Select time in force
    await page.selectOption('#time-in-force', 'gtc');
    
    // Note: We don't actually submit the order in tests to avoid real trades
    // Just verify the form fields are working
    await expect(page.locator('#symbol')).toHaveValue('AAPL');
    await expect(page.locator('#quantity')).toHaveValue('10');
    await expect(page.locator('#limit-price')).toHaveValue('150.00');
  });

  test('order book displays properly', async ({ page }) => {
    // Wait for order book to load
    await page.waitForFunction(() => {
      const orderBook = document.getElementById('order-book-body');
      return orderBook && orderBook.textContent.length > 0;
    }, { timeout: 10000 });
    
    // Check order book table exists
    await expect(page.locator('.order-book table')).toBeVisible();
    
    // Check headers
    await expect(page.locator('.order-book th')).toHaveCount(4);
    
    // Should show either orders or "No active orders" message
    const orderBookBody = page.locator('#order-book-body');
    const bodyText = await orderBookBody.textContent();
    expect(bodyText.length).toBeGreaterThan(0);
  });

  test('chart responds to window resize', async ({ page }) => {
    // Wait for chart to load
    await page.waitForSelector('canvas', { timeout: 10000 });
    
    // Get initial chart size
    const initialBounds = await page.locator('#chart').boundingBox();
    
    // Resize window
    await page.setViewportSize({ width: 1400, height: 900 });
    
    // Wait for resize to take effect
    await page.waitForTimeout(1000);
    
    // Check that chart container size changed
    const newBounds = await page.locator('#chart').boundingBox();
    expect(newBounds.width).not.toBe(initialBounds.width);
    
    // Verify chart still renders after resize
    const canvasElements = await page.locator('canvas').count();
    expect(canvasElements).toBeGreaterThan(0);
  });

  test('chart updates with auto-refresh', async ({ page }) => {
    // Wait for initial chart load
    await page.waitForSelector('canvas', { timeout: 10000 });
    
    // Get initial chart content (we can't easily compare chart data, but we can verify it's still working)
    const initialCanvasCount = await page.locator('canvas').count();
    
    // Wait for auto-refresh interval (10 seconds as per the code)
    await page.waitForTimeout(11000);
    
    // Verify chart is still functional after refresh
    const updatedCanvasCount = await page.locator('canvas').count();
    expect(updatedCanvasCount).toBe(initialCanvasCount);
    
    // Verify chart container is still the right size
    const chartBounds = await page.locator('#chart').boundingBox();
    expect(chartBounds.width).toBeGreaterThan(100);
    expect(chartBounds.height).toBeGreaterThan(100);
  });

  test('error handling when API endpoints fail', async ({ page }) => {
    // Intercept network requests and make chart API fail
    await page.route('**/api/chart/**', route => {
      route.fulfill({
        status: 500,
        body: JSON.stringify({ error: 'Internal server error' })
      });
    });
    
    // Wait for chart container to be visible
    await expect(page.locator('#chart')).toBeVisible();
    
    // Wait for error condition to be handled
    await page.waitForTimeout(3000);
    
    // Chart should still be present even if data fails to load
    await expect(page.locator('#chart')).toBeVisible();
    
    // Check console for error messages (chart should handle API failures gracefully)
    const logs = [];
    page.on('console', msg => logs.push(msg.text()));
    
    // Trigger a chart reload - use force click for mobile compatibility
    await page.locator('[data-timeframe="1Hour"]').click({ force: true });
    await page.waitForTimeout(2000);
    
    // Should have logged the error
    const errorLogs = logs.filter(log => log.includes('Failed to load chart data'));
    expect(errorLogs.length).toBeGreaterThan(0);
  });
});