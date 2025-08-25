import { test, expect } from '../fixtures/auth.fixture';
import { DashboardHelpers, mockWebSocket } from '../utils/helpers';

test.describe('Dashboard Main View', () => {
  let dashboardHelpers: DashboardHelpers;
  
  test.beforeEach(async ({ authenticatedPage, mockAPI }) => {
    dashboardHelpers = new DashboardHelpers(authenticatedPage);
    await mockWebSocket(authenticatedPage);
    await authenticatedPage.goto('/');
    await dashboardHelpers.waitForDashboardLoad();
  });
  
  test('should load dashboard with all main components', async ({ authenticatedPage }) => {
    // Check header
    await expect(authenticatedPage.locator('.trading-header')).toBeVisible();
    await expect(authenticatedPage.locator('h1')).toContainText('Epic 1 Trading Dashboard');
    
    // Check main grid layout
    await expect(authenticatedPage.locator('.dashboard-grid')).toBeVisible();
    
    // Check for chart container
    await expect(authenticatedPage.locator('.chart-container')).toBeVisible();
    
    // Check for positions panel
    await expect(authenticatedPage.locator('.positions-panel')).toBeVisible();
    
    // Check for signals panel
    await expect(authenticatedPage.locator('.signals-panel')).toBeVisible();
  });
  
  test('should display WebSocket connection status', async ({ authenticatedPage }) => {
    await dashboardHelpers.checkWebSocketConnection();
    
    const statusText = await authenticatedPage.locator('.connection-status').textContent();
    expect(statusText).toMatch(/Connected|Connecting/);
  });
  
  test('should show account information', async ({ authenticatedPage }) => {
    const balance = await dashboardHelpers.getAccountBalance();
    expect(balance).toBeGreaterThan(0);
    
    // Check buying power display
    const buyingPower = await authenticatedPage.locator('[data-testid="buying-power"]').textContent();
    expect(buyingPower).toBeTruthy();
  });
  
  test('should switch between tabs', async ({ authenticatedPage }) => {
    // Click on Positions tab
    await dashboardHelpers.clickTab('positions');
    await expect(authenticatedPage.locator('.positions-content')).toBeVisible();
    
    // Click on Signals tab
    await dashboardHelpers.clickTab('signals');
    await expect(authenticatedPage.locator('.signals-content')).toBeVisible();
    
    // Click on Orders tab
    await dashboardHelpers.clickTab('orders');
    await expect(authenticatedPage.locator('.orders-content')).toBeVisible();
  });
  
  test('should handle dark/light theme toggle', async ({ authenticatedPage }) => {
    const themeToggle = authenticatedPage.locator('[data-testid="theme-toggle"]');
    
    // Check initial theme
    const body = authenticatedPage.locator('body');
    await expect(body).toHaveClass(/dark-theme/);
    
    // Toggle to light theme
    await themeToggle.click();
    await expect(body).toHaveClass(/light-theme/);
    
    // Toggle back to dark theme
    await themeToggle.click();
    await expect(body).toHaveClass(/dark-theme/);
  });
  
  test('should display real-time price updates', async ({ authenticatedPage }) => {
    // Wait for initial price
    const priceElement = authenticatedPage.locator('[data-testid="aapl-price"]');
    const initialPrice = await priceElement.textContent();
    
    // Wait for WebSocket update (mocked to send updates every 2 seconds)
    await authenticatedPage.waitForTimeout(3000);
    
    const updatedPrice = await priceElement.textContent();
    expect(updatedPrice).not.toEqual(initialPrice);
  });
  
  test('should search for symbols', async ({ authenticatedPage }) => {
    await dashboardHelpers.searchSymbol('AAPL');
    
    // Check that chart updates
    await expect(authenticatedPage.locator('.chart-title')).toContainText('AAPL');
    
    // Check that relevant data loads
    await expect(authenticatedPage.locator('[data-symbol="AAPL"]')).toBeVisible();
  });
  
  test('should handle errors gracefully', async ({ authenticatedPage }) => {
    // Simulate API error
    await authenticatedPage.route('**/api/positions', route => {
      route.fulfill({ status: 500, body: 'Internal Server Error' });
    });
    
    await authenticatedPage.reload();
    
    // Should show error notification
    await dashboardHelpers.checkNotification('Failed to load positions');
    
    // Dashboard should still be functional
    await expect(authenticatedPage.locator('.dashboard-grid')).toBeVisible();
  });
  
  test('should be responsive on mobile', async ({ authenticatedPage }) => {
    // Set mobile viewport
    await authenticatedPage.setViewportSize({ width: 375, height: 667 });
    
    // Check that mobile menu appears
    await expect(authenticatedPage.locator('.mobile-menu-toggle')).toBeVisible();
    
    // Check that layout adjusts
    const dashboardGrid = authenticatedPage.locator('.dashboard-grid');
    const gridStyle = await dashboardGrid.evaluate(el => 
      window.getComputedStyle(el).gridTemplateColumns
    );
    expect(gridStyle).toContain('1fr'); // Single column on mobile
  });
  
  test('should export data', async ({ authenticatedPage }) => {
    // Setup download promise before clicking
    const downloadPromise = authenticatedPage.waitForEvent('download');
    
    // Click export button
    await authenticatedPage.click('[data-testid="export-data"]');
    
    // Wait for download
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toContain('trading-data');
    expect(download.suggestedFilename()).toMatch(/\.(csv|json)$/);
  });
});

test.describe('Dashboard Performance', () => {
  test('should load within acceptable time', async ({ authenticatedPage, mockAPI }) => {
    const startTime = Date.now();
    
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');
    
    const loadTime = Date.now() - startTime;
    expect(loadTime).toBeLessThan(3000); // Should load within 3 seconds
  });
  
  test('should handle large datasets efficiently', async ({ authenticatedPage, mockAPI }) => {
    // Mock large dataset
    const largePositions = Array(100).fill(null).map((_, i) => ({
      symbol: `STOCK${i}`,
      qty: 100,
      avg_entry_price: 100,
      current_price: 105,
      market_value: 10500,
      unrealized_pl: 500,
      unrealized_plpc: 5,
      side: 'long'
    }));
    
    await authenticatedPage.route('**/api/positions', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, positions: largePositions })
      });
    });
    
    await authenticatedPage.goto('/');
    
    // Check that virtualization is working (not all items rendered)
    const visiblePositions = await authenticatedPage.locator('[data-testid="position-row"]').count();
    expect(visiblePositions).toBeLessThan(100); // Should use virtualization
  });
});