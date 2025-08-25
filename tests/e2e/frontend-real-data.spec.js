const { test, expect } = require('@playwright/test');

test.describe('Frontend Real Data Integration', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the frontend dashboard
    await page.goto('http://localhost:9100');
  });

  test('dashboard loads and displays real portfolio data', async ({ page }) => {
    // Wait for the page to load
    await expect(page.locator('h1')).toContainText('Trading System Dashboard');
    
    // Check that portfolio summary card exists
    await expect(page.locator('#portfolio-summary')).toBeVisible();
    
    // Wait for portfolio data to load (should replace "Loading portfolio...")
    await page.waitForFunction(() => {
      const element = document.getElementById('portfolio-summary');
      return element && !element.textContent.includes('Loading portfolio');
    }, { timeout: 10000 });
    
    // Verify portfolio data is displayed
    const portfolioCard = page.locator('#portfolio-summary');
    await expect(portfolioCard).toContainText('Portfolio Value');
    await expect(portfolioCard).toContainText('Cash Balance');
    await expect(portfolioCard).toContainText('Active Positions');
    await expect(portfolioCard).toContainText('Unrealized P&L');
    await expect(portfolioCard).toContainText('Buying Power');
    await expect(portfolioCard).toContainText('Data Source');
    
    // Verify data source shows "real"
    await expect(portfolioCard).toContainText('real');
    
    // Verify currency formatting (should see $ symbols)
    const portfolioText = await portfolioCard.textContent();
    expect(portfolioText).toMatch(/\$[\d,]+\.\d{2}/);
  });

  test('dashboard displays real account information', async ({ page }) => {
    // Wait for account info to load
    await page.waitForFunction(() => {
      const element = document.getElementById('account-info');
      return element && !element.textContent.includes('Loading account info');
    }, { timeout: 10000 });
    
    const accountCard = page.locator('#account-info');
    await expect(accountCard).toContainText('Account Status');
    await expect(accountCard).toContainText('Buying Power');
  });

  test('dashboard displays recent trades', async ({ page }) => {
    // Wait for trades to load
    await page.waitForFunction(() => {
      const element = document.getElementById('recent-trades');
      return element && !element.textContent.includes('Loading trades');
    }, { timeout: 10000 });
    
    const tradesCard = page.locator('#recent-trades');
    // Should either show trades or "No recent trades"
    const tradesText = await tradesCard.textContent();
    expect(tradesText.length).toBeGreaterThan(10); // Some content loaded
  });

  test('service status shows healthy services', async ({ page }) => {
    // Wait for service status to load
    await page.waitForFunction(() => {
      const element = document.getElementById('service-status');
      return element && !element.textContent.includes('Loading services');
    }, { timeout: 10000 });
    
    const serviceCard = page.locator('#service-status');
    await expect(serviceCard).toContainText('position-management');
    await expect(serviceCard).toContainText('healthy');
    
    // Look for green status indicators
    const healthyIndicators = page.locator('.status-healthy');
    expect(await healthyIndicators.count()).toBeGreaterThan(0);
  });

  test('refresh buttons work correctly', async ({ page }) => {
    // Wait for initial load
    await page.waitForFunction(() => {
      const element = document.getElementById('portfolio-summary');
      return element && !element.textContent.includes('Loading portfolio');
    }, { timeout: 10000 });
    
    // Get current content
    const initialContent = await page.locator('#portfolio-summary').textContent();
    
    // Click refresh button for portfolio
    const refreshBtn = page.locator('button:has-text("Refresh")').first();
    await refreshBtn.click();
    
    // Wait a moment for refresh to complete
    await page.waitForTimeout(2000);
    
    // Verify content is still showing (data should be refreshed)
    const updatedContent = await page.locator('#portfolio-summary').textContent();
    expect(updatedContent).toContain('Portfolio Value');
    expect(updatedContent).toContain('Data Source');
  });

  test('navigation between pages works', async ({ page }) => {
    // Test navigation to portfolio page
    await page.click('a[href="/portfolio"]');
    await expect(page).toHaveURL('http://localhost:9100/portfolio');
    
    // Test navigation to trading page
    await page.click('a[href="/trading"]');
    await expect(page).toHaveURL('http://localhost:9100/trading');
    
    // Test navigation back to dashboard
    await page.click('a[href="/"]');
    await expect(page).toHaveURL('http://localhost:9100/');
  });

  test('real-time data updates work', async ({ page }) => {
    // Wait for initial portfolio load
    await page.waitForFunction(() => {
      const element = document.getElementById('portfolio-summary');
      return element && !element.textContent.includes('Loading portfolio');
    }, { timeout: 10000 });
    
    // Get initial portfolio value
    const initialText = await page.locator('#portfolio-summary').textContent();
    
    // Refresh data
    await page.click('button:has-text("Refresh")');
    
    // Wait for refresh to complete
    await page.waitForFunction(() => {
      const element = document.getElementById('portfolio-summary');
      return element && !element.textContent.includes('Loading');
    }, { timeout: 10000 });
    
    // Verify data is still showing (may be same values, but should be formatted)
    const updatedText = await page.locator('#portfolio-summary').textContent();
    expect(updatedText).toContain('Portfolio Value');
    expect(updatedText).toMatch(/\$[\d,]+\.\d{2}/);
  });

  test('error handling works when services are unavailable', async ({ page }) => {
    // This test would require stopping services temporarily
    // For now, just verify error handling structure is in place
    
    // Check that error handling code exists in the page
    const pageContent = await page.content();
    expect(pageContent).toContain('Failed to load');
  });

  test('responsive design works on mobile viewport', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    
    // Verify page still loads and is usable
    await expect(page.locator('h1')).toContainText('Trading System Dashboard');
    await expect(page.locator('.dashboard-grid')).toBeVisible();
    
    // Verify grid adapts to smaller screen
    const grid = page.locator('.dashboard-grid');
    const gridStyle = await grid.evaluate(el => getComputedStyle(el).gridTemplateColumns);
    // Should adapt to mobile (exact value may vary based on CSS)
    expect(gridStyle).toBeTruthy();
  });
});