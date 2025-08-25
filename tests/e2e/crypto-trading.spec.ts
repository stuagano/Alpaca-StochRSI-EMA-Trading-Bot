import { test, expect } from '@playwright/test';

test.describe('Crypto Trading Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Navigate to crypto tab
    await page.click('[data-testid="crypto-tab"]');
    await page.waitForTimeout(2000);
  });

  test('should load crypto assets successfully', async ({ page }) => {
    // Wait for crypto assets API call
    const assetsResponse = page.waitForResponse(response => 
      response.url().includes('/api/crypto/assets') && response.status() === 200
    );
    
    const response = await assetsResponse;
    const data = await response.json();
    
    // Verify crypto assets structure
    expect(data).toHaveProperty('assets');
    expect(data).toHaveProperty('trading_hours', '24/7');
    expect(data.assets).toBeInstanceOf(Array);
    expect(data.assets.length).toBeGreaterThan(0);
    
    // Verify each asset has required properties
    const firstAsset = data.assets[0];
    expect(firstAsset).toHaveProperty('symbol');
    expect(firstAsset).toHaveProperty('name');
    expect(firstAsset).toHaveProperty('tradable', true);
    expect(firstAsset).toHaveProperty('fractionable', true);
    
    // Should display crypto assets in UI
    await expect(page.locator('[data-testid="crypto-asset-selector"]')).toBeVisible();
  });

  test('should display 24/7 trading indicator', async ({ page }) => {
    // Check for 24/7 badge
    await expect(page.locator('[data-testid="crypto-247-indicator"]')).toBeVisible();
    await expect(page.locator('[data-testid="crypto-247-indicator"]')).toContainText('24/7');
  });

  test('should handle crypto quote requests', async ({ page }) => {
    // Select BTC/USD
    await page.selectOption('[data-testid="crypto-symbol-select"]', 'BTC/USD');
    
    // Wait for quote API call
    const quoteResponse = page.waitForResponse(response => 
      response.url().includes('/api/crypto/quotes/BTC/USD')
    );
    
    const response = await quoteResponse;
    
    if (response.status() === 200) {
      const quoteData = await response.json();
      
      // Verify quote structure
      expect(quoteData).toHaveProperty('symbol', 'BTC/USD');
      expect(quoteData).toHaveProperty('bid');
      expect(quoteData).toHaveProperty('ask');
      expect(quoteData).toHaveProperty('last');
      expect(quoteData).toHaveProperty('timestamp');
      
      // Verify bid <= ask relationship
      expect(quoteData.bid).toBeLessThanOrEqual(quoteData.ask);
      
      // Should display quote in UI
      await expect(page.locator('[data-testid="crypto-current-price"]')).toBeVisible();
    }
  });

  test('should support fractional crypto orders', async ({ page }) => {
    // Select crypto asset
    await page.selectOption('[data-testid="crypto-symbol-select"]', 'BTC/USD');
    
    // Switch to quantity mode
    await page.click('[data-testid="quantity-mode-button"]');
    
    // Enter fractional quantity
    await page.fill('[data-testid="crypto-quantity-input"]', '0.0001');
    
    // Verify minimum order validation
    const quantityInput = page.locator('[data-testid="crypto-quantity-input"]');
    await expect(quantityInput).toHaveValue('0.0001');
    
    // Should not show validation error for minimum amount
    await expect(page.locator('[data-testid="quantity-error"]')).not.toBeVisible();
  });

  test('should support dollar amount orders', async ({ page }) => {
    // Select crypto asset
    await page.selectOption('[data-testid="crypto-symbol-select"]', 'ETH/USD');
    
    // Switch to dollar amount mode
    await page.click('[data-testid="dollar-mode-button"]');
    
    // Enter dollar amount
    await page.fill('[data-testid="crypto-notional-input"]', '1000.00');
    
    // Should accept dollar amounts up to max
    const notionalInput = page.locator('[data-testid="crypto-notional-input"]');
    await expect(notionalInput).toHaveValue('1000.00');
    
    // Test maximum validation (should reject over $200k)
    await page.fill('[data-testid="crypto-notional-input"]', '250000.00');
    await page.blur('[data-testid="crypto-notional-input"]');
    
    // Should show validation error
    await expect(page.locator('[data-testid="notional-error"]')).toBeVisible();
  });

  test('should display crypto positions', async ({ page }) => {
    // Wait for positions API call
    const positionsResponse = page.waitForResponse(response => 
      response.url().includes('/api/crypto/positions')
    );
    
    await positionsResponse;
    
    // Navigate to positions tab within crypto section
    await page.click('[data-testid="crypto-positions-tab"]');
    
    // Should show positions or empty state
    const positionsContainer = page.locator('[data-testid="crypto-positions-container"]');
    await expect(positionsContainer).toBeVisible();
  });

  test('should handle crypto order submission', async ({ page }) => {
    // Select crypto asset
    await page.selectOption('[data-testid="crypto-symbol-select"]', 'BTC/USD');
    
    // Enter order details
    await page.click('[data-testid="crypto-buy-button"]');
    await page.click('[data-testid="dollar-mode-button"]');
    await page.fill('[data-testid="crypto-notional-input"]', '100.00');
    
    // Mock successful order response
    await page.route('**/api/crypto/orders', route => {
      route.fulfill({
        status: 200,
        body: JSON.stringify({
          id: 'test-order-123',
          symbol: 'BTC/USD',
          side: 'buy',
          status: 'accepted',
          notional: 100.00
        })
      });
    });
    
    // Submit order
    await page.click('[data-testid="crypto-submit-order-button"]');
    
    // Should show success toast
    await expect(page.locator('[data-testid="success-toast"]')).toBeVisible();
  });

  test('should validate crypto trading hours are always open', async ({ page }) => {
    // Check trading hours endpoint
    const hoursResponse = page.waitForResponse(response => 
      response.url().includes('/api/crypto/trading-hours')
    );
    
    // This might be called automatically or we can trigger it
    await page.reload();
    
    // Try to catch the response or make direct API call
    await page.evaluate(async () => {
      const response = await fetch('/api/crypto/trading-hours');
      const data = await response.json();
      
      // Store result for test verification
      (window as any).cryptoTradingHours = data;
    });
    
    // Verify trading hours data
    const tradingHours = await page.evaluate(() => (window as any).cryptoTradingHours);
    
    if (tradingHours) {
      expect(tradingHours.trading_hours).toBe('24/7');
      expect(tradingHours.is_open).toBe(true);
      expect(tradingHours.next_close).toBe(null);
    }
  });

  test('should display crypto market data correctly', async ({ page }) => {
    // Navigate to crypto market tab
    await page.click('[data-testid="crypto-market-tab"]');
    
    // Should show available crypto pairs
    await expect(page.locator('[data-testid="crypto-market-grid"]')).toBeVisible();
    
    // Should show major crypto pairs
    await expect(page.locator('[data-testid="crypto-pair-BTC/USD"]')).toBeVisible();
    await expect(page.locator('[data-testid="crypto-pair-ETH/USD"]')).toBeVisible();
    
    // Each pair should show trading status
    const btcPair = page.locator('[data-testid="crypto-pair-BTC/USD"]');
    await expect(btcPair.locator('[data-testid="tradable-badge"]')).toBeVisible();
    await expect(btcPair.locator('[data-testid="fractional-badge"]')).toBeVisible();
  });

  test('should handle crypto WebSocket connections', async ({ page }) => {
    // Wait for WebSocket connection indicator
    await page.waitForTimeout(3000);
    
    // Should show connection status
    const connectionStatus = page.locator('[data-testid="crypto-connection-status"]');
    await expect(connectionStatus).toBeVisible();
    
    // Status should be either "Live" or "Disconnected"
    const statusText = await connectionStatus.textContent();
    expect(['Live', 'Disconnected']).toContain(statusText);
  });

  test('should show crypto-specific trading rules', async ({ page }) => {
    // Check that crypto-specific rules are displayed
    await expect(page.locator('[data-testid="crypto-rules"]')).toBeVisible();
    
    // Should mention no margin/shorting
    await expect(page.locator('[data-testid="no-margin-notice"]')).toBeVisible();
    await expect(page.locator('[data-testid="no-shorting-notice"]')).toBeVisible();
    
    // Should show T+0 settlement
    await expect(page.locator('[data-testid="instant-settlement"]')).toBeVisible();
  });
});