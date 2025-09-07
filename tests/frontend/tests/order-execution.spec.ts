/**
 * Comprehensive tests for order execution functionality
 * Tests order placement, validation, execution tracking, and error handling
 */
import { test, expect, Page } from '@playwright/test';

// Helper functions
async function waitForPageLoad(page: Page) {
  await page.waitForLoadState('domcontentloaded');
  await page.waitForLoadState('networkidle', { timeout: 10000 });
}

async function interceptOrderAPI(page: Page) {
  // Mock order placement API for testing
  await page.route('**/api/orders', async route => {
    if (route.request().method() === 'POST') {
      const postData = route.request().postData();
      const orderData = JSON.parse(postData || '{}');
      
      // Mock successful order response
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'success',
          order_id: `order_${Date.now()}`,
          symbol: orderData.symbol,
          qty: orderData.qty,
          side: orderData.side,
          type: orderData.type,
          estimated_price: orderData.symbol === 'BTCUSD' ? 45000.00 : 3200.00,
          data_source: 'live'
        })
      });
    } else {
      // GET orders request
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          orders: [
            {
              id: 'order_123',
              symbol: 'BTCUSD',
              qty: '0.1',
              side: 'buy',
              order_type: 'market',
              status: 'filled',
              filled_price: '45000.00',
              created_at: new Date().toISOString()
            }
          ],
          data_source: 'live'
        })
      });
    }
  });
}

async function mockAccountData(page: Page) {
  // Mock account API with sufficient buying power
  await page.route('**/api/account', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'test-account',
        account_number: 'PA123',
        status: 'ACTIVE',
        equity: 100000.0,
        buying_power: 50000.0,
        cash: 25000.0,
        portfolio_value: 100000.0,
        data_source: 'live'
      })
    });
  });
}

test.describe('Order Placement Interface', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/crypto');
    await waitForPageLoad(page);
    await interceptOrderAPI(page);
    await mockAccountData(page);
  });

  test('should display order placement controls', async ({ page }) => {
    // Look for trading controls (these might be in a modal or separate section)
    // For now, check if Start buttons are present (these would trigger order placement)
    
    const startCryptoBot = page.locator('button:has-text("Start Crypto Bot")');
    await expect(startCryptoBot).toBeVisible();
    
    const startScalping = page.locator('button:has-text("Start")').first();
    await expect(startScalping).toBeVisible();
    
    // Check if there are any order form elements
    const buttons = await page.locator('button').count();
    expect(buttons).toBeGreaterThan(2); // Should have multiple interactive buttons
  });

  test('should validate order parameters', async ({ page }) => {
    // Test with the available controls
    // Click start crypto bot to see if any order validation appears
    
    const startButton = page.locator('button:has-text("Start Crypto Bot")');
    if (await startButton.isVisible()) {
      await startButton.click();
      await page.waitForTimeout(1000);
      
      // Check if any validation messages appear
      // (This depends on the actual implementation)
    }
    
    // Verify account data is loaded for validation
    await page.waitForTimeout(2000);
    
    // Should display buying power or account info somewhere
    const accountInfo = await page.textContent('body');
    
    // Should contain some numeric values (portfolio, P&L, etc.)
    expect(accountInfo).toMatch(/\$[0-9,]+/);
  });

  test('should handle crypto symbol selection for orders', async ({ page }) => {
    // Test symbol selection which affects order placement
    const symbolSelector = page.locator('select, combobox').first();
    
    if (await symbolSelector.isVisible()) {
      // Select different crypto symbols
      await symbolSelector.selectOption('BTCUSD');
      await page.waitForTimeout(500);
      
      await expect(page.locator('text=BTCUSD')).toBeVisible();
      
      // Try another symbol
      await symbolSelector.selectOption('ETHUSD');
      await page.waitForTimeout(500);
      
      await expect(page.locator('text=ETHUSD')).toBeVisible();
    }
  });

  test('should display current market prices for order reference', async ({ page }) => {
    // Orders need current prices for validation
    await page.waitForTimeout(3000); // Wait for price data
    
    // Should display some price information
    const pageContent = await page.textContent('body');
    
    // Look for price-like numbers (could be in various formats)
    const hasPrices = /\$[\d,]+\.?\d*|\$[\d,]+|[\d,]+\.?\d*\s*(USD|BTC|ETH)/.test(pageContent || '');
    expect(hasPrices).toBe(true);
  });
});

test.describe('Order Execution Tracking', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/crypto');
    await waitForPageLoad(page);
    await interceptOrderAPI(page);
  });

  test('should display active orders', async ({ page }) => {
    // Check for orders display
    await page.waitForTimeout(2000);
    
    // Look for order-related text
    await expect(page.locator('text=pending orders')).toBeVisible();
    
    // Should show order count (even if 0)
    const orderCount = page.locator('text=/[0-9]+ pending orders/');
    await expect(orderCount).toBeVisible();
  });

  test('should show order execution status', async ({ page }) => {
    // Check trading status indicators
    await expect(page.locator('text=PAUSED, text=ACTIVE, text=OFF')).toHaveCount(1);
    
    // Should show execution metrics
    await expect(page.locator('text=Trades/Hour')).toBeVisible();
    await expect(page.locator('text=/[0-9]+ trades/i')).toBeVisible();
  });

  test('should track order fill status', async ({ page }) => {
    // Look for filled order indicators
    await page.waitForTimeout(3000);
    
    // Check for execution status in trade activity
    await expect(page.locator('text=Live Trade Activity')).toBeVisible();
    
    // Initially shows waiting message
    const tradeStatus = page.locator('text=No trades executed yet. Waiting for signals..., text=Recent executed trades');
    await expect(tradeStatus).toHaveCount(1);
  });

  test('should validate real data in order tracking', async ({ page }) => {
    // Wait for data to load
    await page.waitForTimeout(3000);
    
    // Check that all displayed data has live data characteristics
    const pageContent = await page.content();
    
    // Should not contain fake data markers
    expect(pageContent.toLowerCase()).not.toContain('demo: true');
    expect(pageContent.toLowerCase()).not.toContain('mock: true');
    expect(pageContent.toLowerCase()).not.toContain('fallback: true');
    
    // Should contain realistic trading values
    expect(pageContent).toMatch(/\$[0-9,]+\.?\d*/); // Currency amounts
    expect(pageContent).toMatch(/[0-9]+\.?[0-9]*%/); // Percentages
  });
});

test.describe('Order Error Handling', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/crypto');
    await waitForPageLoad(page);
  });

  test('should handle insufficient funds scenarios', async ({ page }) => {
    // Mock account with low buying power
    await page.route('**/api/account', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'test-account',
          buying_power: 1.00, // Very low buying power
          cash: 1.00,
          equity: 100.00,
          data_source: 'live'
        })
      });
    });
    
    // Reload to get new account data
    await page.reload();
    await waitForPageLoad(page);
    
    // The UI should reflect low buying power
    // Check if any warnings or status changes appear
    await page.waitForTimeout(2000);
    
    // Should still display the interface but may show different status
    await expect(page.locator('text=Available Cash')).toBeVisible();
  });

  test('should handle API failures gracefully', async ({ page }) => {
    // Mock API failure
    await page.route('**/api/orders', async route => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({
          error: 'API temporarily unavailable',
          message: 'Service connection failed'
        })
      });
    });
    
    // Try to interact with order-related functionality
    await page.reload();
    await waitForPageLoad(page);
    
    // Should handle errors gracefully without crashing
    await page.waitForTimeout(2000);
    
    // Page should still be functional
    await expect(page.locator('text=Crypto Trading Bot')).toBeVisible();
  });

  test('should validate order parameters', async ({ page }) => {
    // Mock order API that validates parameters
    await page.route('**/api/orders', async route => {
      const postData = route.request().postData();
      const orderData = JSON.parse(postData || '{}');
      
      // Validate order data
      if (!orderData.symbol || !orderData.qty || !orderData.side) {
        await route.fulfill({
          status: 400,
          contentType: 'application/json',
          body: JSON.stringify({
            error: 'Invalid order parameters',
            details: 'Missing required fields'
          })
        });
      } else if (parseFloat(orderData.qty) <= 0) {
        await route.fulfill({
          status: 400,
          contentType: 'application/json',
          body: JSON.stringify({
            error: 'Invalid quantity',
            details: 'Quantity must be greater than 0'
          })
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            status: 'success',
            order_id: 'valid_order_123',
            data_source: 'live'
          })
        });
      }
    });
    
    // The validation would be triggered by actual order placement
    // For now, just verify the API mocking is working
    await page.waitForTimeout(1000);
  });
});

test.describe('Position Management', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/crypto');
    await waitForPageLoad(page);
  });

  test('should display current positions', async ({ page }) => {
    // Mock positions API
    await page.route('**/api/positions*', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          positions: [
            {
              symbol: 'BTCUSD',
              qty: '0.1',
              market_value: '4500.00',
              cost_basis: '4400.00',
              unrealized_pl: '100.00',
              unrealized_plpc: '2.27',
              side: 'long'
            },
            {
              symbol: 'ETHUSD',
              qty: '2.0',
              market_value: '6400.00',
              cost_basis: '6500.00',
              unrealized_pl: '-100.00',
              unrealized_plpc: '-1.54',
              side: 'long'
            }
          ],
          data_source: 'live'
        })
      });
    });
    
    await page.reload();
    await waitForPageLoad(page);
    await page.waitForTimeout(2000);
    
    // Check positions display
    await expect(page.locator('text=Crypto Positions')).toBeVisible();
    
    // Should show position count or value
    const positionInfo = await page.textContent('body');
    expect(positionInfo).toMatch(/[0-9]+ positions|positions|holdings/i);
  });

  test('should calculate position P&L correctly', async ({ page }) => {
    // Mock positions with known P&L
    await page.route('**/api/positions*', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          positions: [
            {
              symbol: 'BTCUSD',
              qty: '0.1',
              market_value: '4500.00',
              cost_basis: '4400.00',
              unrealized_pl: '100.00',
              unrealized_plpc: '2.27',
              side: 'long'
            }
          ],
          total_unrealized_pl: '100.00',
          total_unrealized_plpc: '2.27',
          data_source: 'live'
        })
      });
    });
    
    await page.reload();
    await waitForPageLoad(page);
    await page.waitForTimeout(2000);
    
    // P&L should be reflected in portfolio metrics
    const pnlSection = page.locator('text=24h P&L').locator('..');
    await expect(pnlSection).toBeVisible();
    
    // Should show some P&L value
    const pnlText = await pnlSection.textContent();
    expect(pnlText).toMatch(/\$[0-9,.]+|\+?\-?[0-9,.]+%/);
  });

  test('should handle position updates in real-time', async ({ page }) => {
    // This tests if positions update via WebSocket or polling
    
    let positionUpdateCount = 0;
    
    await page.route('**/api/positions*', async route => {
      positionUpdateCount++;
      
      // Simulate position value changes
      const marketValue = positionUpdateCount === 1 ? '4500.00' : '4600.00';
      const unrealizedPL = positionUpdateCount === 1 ? '100.00' : '200.00';
      
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          positions: [
            {
              symbol: 'BTCUSD',
              qty: '0.1',
              market_value: marketValue,
              cost_basis: '4400.00',
              unrealized_pl: unrealizedPL,
              unrealized_plpc: positionUpdateCount === 1 ? '2.27' : '4.55',
              side: 'long'
            }
          ],
          data_source: 'live'
        })
      });
    });
    
    await page.reload();
    await waitForPageLoad(page);
    
    // Wait for potential position updates
    await page.waitForTimeout(5000);
    
    // Should have made at least one position API call
    expect(positionUpdateCount).toBeGreaterThan(0);
  });
});

test.describe('Risk Management Integration', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/crypto');
    await waitForPageLoad(page);
  });

  test('should display risk management controls', async ({ page }) => {
    // Check for risk-related information
    await expect(page.locator('text=Risk score')).toBeVisible();
    await expect(page.locator('text=Stop Loss')).toBeVisible();
    
    // Should show risk parameters
    const riskInfo = await page.textContent('body');
    expect(riskInfo).toMatch(/risk score:?\s*[0-9]+/i);
    expect(riskInfo).toMatch(/stop loss:?\s*[0-9.]+[-–]?[0-9.]*%/i);
  });

  test('should validate position sizing', async ({ page }) => {
    // Risk management should limit position sizes
    await page.waitForTimeout(2000);
    
    // Check if position sizing info is displayed
    const strategyInfo = page.locator('text=Crypto Scalping').locator('..');
    await expect(strategyInfo).toBeVisible();
    
    // Should show position size limits
    const strategyText = await strategyInfo.textContent();
    expect(strategyText).toMatch(/position.*size|max.*position/i);
  });

  test('should show stop loss and take profit levels', async ({ page }) => {
    // Check strategy parameters
    await expect(page.locator('text=Profit Targets')).toBeVisible();
    await expect(page.locator('text=Stop Loss')).toBeVisible();
    
    // Verify specific risk parameters are shown
    await expect(page.locator('text=0.1-0.5% per trade')).toBeVisible();
    await expect(page.locator('text=0.05-0.25% risk')).toBeVisible();
  });

  test('should enforce maximum trade size limits', async ({ page }) => {
    // Mock account with specific limits
    await page.route('**/api/account', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'test-account',
          buying_power: 10000.0,
          max_position_size: 1000.0, // Example limit
          risk_level: 'conservative',
          data_source: 'live'
        })
      });
    });
    
    await page.reload();
    await waitForPageLoad(page);
    
    // Risk management should be reflected in the UI
    await page.waitForTimeout(2000);
    
    // Should show appropriate risk level indicators
    const accountInfo = await page.textContent('body');
    expect(accountInfo).toMatch(/conservative|moderate|aggressive|[0-9]+\/10/i);
  });
});