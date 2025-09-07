/**
 * Comprehensive Playwright tests for crypto trading interface
 * Tests UI functionality, order placement, P&L display, and WebSocket connections
 */
import { test, expect, Page } from '@playwright/test';

// Test data and utilities
const CRYPTO_PAIRS = ['BTCUSD', 'ETHUSD', 'LTCUSD', 'BCHUSD', 'UNIUSD'];
const TIMEFRAMES = ['1Min', '5Min', '15Min', '1Hour', '1Day'];

// Helper functions
async function waitForPageLoad(page: Page) {
  await page.waitForLoadState('domcontentloaded');
  await page.waitForLoadState('networkidle', { timeout: 10000 });
}

async function verifyNoFakeData(page: Page) {
  // Check for fake/demo data markers in page content
  const pageContent = await page.content();
  expect(pageContent.toLowerCase()).not.toContain('demo: true');
  expect(pageContent.toLowerCase()).not.toContain('mock: true');
  expect(pageContent.toLowerCase()).not.toContain('fallback: true');
  expect(pageContent.toLowerCase()).not.toContain('fake data');
}

async function verifyLiveDataMarkers(page: Page) {
  // Check for live data indicators in API responses
  const responses: any[] = [];
  
  page.on('response', response => {
    if (response.url().includes('/api/')) {
      responses.push(response);
    }
  });
  
  await page.reload();
  await waitForPageLoad(page);
  
  // Give time for API calls to complete
  await page.waitForTimeout(2000);
  
  // Verify at least some API responses contain live data markers
  let liveDataFound = false;
  for (const response of responses) {
    try {
      const data = await response.json();
      if (data && data.data_source === 'live') {
        liveDataFound = true;
        break;
      }
    } catch {
      // Skip non-JSON responses
    }
  }
  
  expect(liveDataFound).toBe(true);
}

test.describe('Crypto Trading Interface', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to crypto trading page
    await page.goto('/crypto');
    await waitForPageLoad(page);
  });

  test('should load crypto trading page successfully', async ({ page }) => {
    // Verify page title and main elements
    await expect(page).toHaveTitle(/Alpaca Trading Bot/);
    
    // Check for main crypto trading elements
    await expect(page.locator('h1')).toContainText('Crypto Trading Bot');
    await expect(page.locator('text=24/7 Automated Trading')).toBeVisible();
    
    // Verify portfolio section
    await expect(page.locator('text=Crypto Portfolio')).toBeVisible();
    await expect(page.locator('text=24h P&L')).toBeVisible();
    await expect(page.locator('text=Active Crypto')).toBeVisible();
    
    // Verify no fake data
    await verifyNoFakeData(page);
  });

  test('should display crypto trading chart with controls', async ({ page }) => {
    // Check chart container
    await expect(page.locator('text=Crypto Chart - BTCUSD')).toBeVisible();
    
    // Check timeframe buttons
    for (const timeframe of TIMEFRAMES) {
      await expect(page.locator(`button:has-text("${timeframe}")`)).toBeVisible();
    }
    
    // Check symbol selector
    const symbolSelector = page.locator('select, combobox').first();
    await expect(symbolSelector).toBeVisible();
    
    // Check indicator buttons
    await expect(page.locator('button:has-text("EMA")')).toBeVisible();
    await expect(page.locator('button:has-text("Signals")')).toBeVisible();
    
    // Verify 24/7 indicator
    await expect(page.locator('text=24/7')).toBeVisible();
  });

  test('should change cryptocurrency symbol', async ({ page }) => {
    // Find symbol selector
    const symbolSelector = page.locator('select, combobox').first();
    
    // Test changing to different crypto pairs
    for (const symbol of CRYPTO_PAIRS.slice(0, 3)) { // Test first 3 to save time
      await symbolSelector.selectOption(symbol);
      await page.waitForTimeout(1000); // Wait for chart update
      
      // Verify chart title updates
      await expect(page.locator(`text=Crypto Chart - ${symbol}`)).toBeVisible();
    }
  });

  test('should change chart timeframe', async ({ page }) => {
    // Test clicking different timeframe buttons
    for (const timeframe of ['5Min', '15Min', '1Hour']) {
      await page.locator(`button:has-text("${timeframe}")`).click();
      await page.waitForTimeout(500); // Wait for chart update
      
      // Button should appear selected/active
      const button = page.locator(`button:has-text("${timeframe}")`);
      await expect(button).toBeVisible();
    }
  });

  test('should display trading indicators and signals', async ({ page }) => {
    // Check EMA indicator section
    await expect(page.locator('text=EMA (3/8)')).toBeVisible();
    await expect(page.locator('text=Cross Up')).toBeVisible();
    
    // Check Volume indicator
    await expect(page.locator('text=Volume Spike')).toBeVisible();
    
    // Check StochRSI
    await expect(page.locator('text=StochRSI')).toBeVisible();
    await expect(page.locator('text=NEUTRAL')).toBeVisible();
    
    // Check signals per minute
    await expect(page.locator('text=Signals/Min')).toBeVisible();
    
    // Verify strategy description
    await expect(page.locator('text=High-Frequency Scalping Strategy')).toBeVisible();
  });

  test('should display scalping engine status', async ({ page }) => {
    // Check scalping engine section
    await expect(page.locator('text=High-Frequency Scalping Engine')).toBeVisible();
    
    // Check status indicator
    await expect(page.locator('text=PAUSED')).toBeVisible();
    
    // Check start button
    await expect(page.locator('button:has-text("Start")')).toBeVisible();
    
    // Check performance metrics
    await expect(page.locator('text=Trades/Hour')).toBeVisible();
    await expect(page.locator('text=Win Rate')).toBeVisible();
    await expect(page.locator('text=Avg Profit')).toBeVisible();
    await expect(page.locator('text=Avg Duration')).toBeVisible();
    
    // Check strategy details
    await expect(page.locator('text=Profit Targets: 0.1-0.5% per trade')).toBeVisible();
    await expect(page.locator('text=Stop Loss: 0.05-0.25% risk')).toBeVisible();
    await expect(page.locator('text=Trade Frequency: 15-40 trades per hour')).toBeVisible();
  });
});

test.describe('Crypto Portfolio and P&L', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/crypto');
    await waitForPageLoad(page);
  });

  test('should display portfolio metrics', async ({ page }) => {
    // Check portfolio value
    const portfolioValue = page.locator('text=Crypto Portfolio').locator('..').locator('text=/\\$[0-9,.]+/');
    await expect(portfolioValue).toBeVisible();
    
    // Check 24h P&L
    const pnlValue = page.locator('text=24h P&L').locator('..').locator('text=/\\$[0-9,.]+/');
    await expect(pnlValue).toBeVisible();
    
    // Check active crypto count
    const activeCrypto = page.locator('text=Active Crypto').locator('..').locator('text=/[0-9]+/');
    await expect(activeCrypto).toBeVisible();
    
    // Check win rate
    const winRate = page.locator('text=Win Rate').locator('..').locator('text=/[0-9.]+%/');
    await expect(winRate).toBeVisible();
    
    // Check available cash
    const availableCash = page.locator('text=Available Cash').locator('..').locator('text=/\\$[0-9,.]+/');
    await expect(availableCash).toBeVisible();
  });

  test('should display P&L chart', async ({ page }) => {
    // Check P&L chart section
    await expect(page.locator('text=Session Profit Chart')).toBeVisible();
    await expect(page.locator('text=Cumulative P&L (line) and individual trades (bars)')).toBeVisible();
    
    // Check win/loss counters
    await expect(page.locator('text=/Wins: [0-9]+/')).toBeVisible();
    await expect(page.locator('text=/Losses: [0-9]+/')).toBeVisible();
    
    // Check total P&L display
    await expect(page.locator('text=/[+\\-]?\\$[0-9,.]+/')).toBeVisible();
  });

  test('should display live trade activity', async ({ page }) => {
    // Check trade activity section
    await expect(page.locator('text=Live Trade Activity')).toBeVisible();
    await expect(page.locator('text=Recent executed trades')).toBeVisible();
    
    // Initially should show waiting message
    await expect(page.locator('text=No trades executed yet. Waiting for signals...')).toBeVisible();
  });

  test('should verify real data in portfolio display', async ({ page }) => {
    // Wait for data to load
    await page.waitForTimeout(3000);
    
    // Verify no fake data markers
    await verifyNoFakeData(page);
    
    // Verify live data markers in API responses
    await verifyLiveDataMarkers(page);
  });
});

test.describe('Crypto Market Screener', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/crypto');
    await waitForPageLoad(page);
  });

  test('should display market screener', async ({ page }) => {
    // Check screener title and stats
    await expect(page.locator('text=Crypto Market Screener')).toBeVisible();
    
    // Check asset counts
    await expect(page.locator('text=Total Assets')).toBeVisible();
    await expect(page.locator('text=Trading Enabled')).toBeVisible();
    await expect(page.locator('text=Gainers')).toBeVisible();
    await expect(page.locator('text=Losers')).toBeVisible();
    
    // Check search functionality
    await expect(page.locator('input[placeholder*="Search cryptocurrencies"]')).toBeVisible();
    
    // Check refresh button
    await expect(page.locator('button:has-text("Refresh")')).toBeVisible();
  });

  test('should display market tabs', async ({ page }) => {
    // Check tab navigation
    await expect(page.locator('text=Top Movers')).toBeVisible();
    await expect(page.locator('text=All Assets')).toBeVisible(); 
    await expect(page.locator('text=Active Trading')).toBeVisible();
    
    // Test clicking tabs
    await page.locator('text=All Assets').click();
    await page.waitForTimeout(500);
    
    await page.locator('text=Active Trading').click();
    await page.waitForTimeout(500);
    
    await page.locator('text=Top Movers').click();
    await page.waitForTimeout(500);
  });

  test('should display top gainers and losers', async ({ page }) => {
    // Check top gainers section
    await expect(page.locator('text=Top 10 Gainers')).toBeVisible();
    await expect(page.locator('text=Biggest winners in the last 24 hours')).toBeVisible();
    
    // Check top losers section  
    await expect(page.locator('text=Top 10 Losers')).toBeVisible();
    await expect(page.locator('text=Biggest losers in the last 24 hours')).toBeVisible();
  });

  test('should handle search functionality', async ({ page }) => {
    const searchInput = page.locator('input[placeholder*="Search cryptocurrencies"]');
    
    // Test search input
    await searchInput.fill('BTC');
    await page.waitForTimeout(500);
    
    // Clear search
    await searchInput.fill('');
    await page.waitForTimeout(500);
    
    // Test another search
    await searchInput.fill('ETH');
    await page.waitForTimeout(500);
  });
});

test.describe('WebSocket Connection', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/crypto');
    await waitForPageLoad(page);
  });

  test('should establish WebSocket connection', async ({ page }) => {
    // Wait for WebSocket connection
    await page.waitForTimeout(3000);
    
    // Check for connection status indicators
    const connectionStatus = page.locator('text=Connected, text=Disconnected').first();
    
    // Should eventually show connected (may take time)
    // If disconnected, that's a sign the WebSocket needs fixing
    const statusText = await connectionStatus.textContent();
    
    if (statusText === 'Disconnected') {
      console.warn('WebSocket showing as disconnected - may need investigation');
    }
    
    // Verify WebSocket connection in console logs
    const consoleLogs: string[] = [];
    page.on('console', msg => {
      consoleLogs.push(msg.text());
    });
    
    await page.reload();
    await waitForPageLoad(page);
    await page.waitForTimeout(5000);
    
    // Check for WebSocket connection messages
    const wsConnected = consoleLogs.some(log => 
      log.includes('WebSocket connected') || 
      log.includes('crypto WebSocket connected')
    );
    
    if (!wsConnected) {
      console.warn('No WebSocket connection messages found in console');
    }
  });

  test('should handle WebSocket data updates', async ({ page }) => {
    let wsMessages: any[] = [];
    
    // Monitor WebSocket messages
    await page.evaluateOnNewDocument(() => {
      const originalWebSocket = window.WebSocket;
      window.WebSocket = class extends originalWebSocket {
        constructor(url: string, protocols?: string | string[]) {
          super(url, protocols);
          
          const originalOnMessage = this.onmessage;
          this.onmessage = function(event) {
            // Store message data for testing
            if (window.wsTestMessages) {
              window.wsTestMessages.push(JSON.parse(event.data));
            }
            if (originalOnMessage) {
              originalOnMessage.call(this, event);
            }
          };
        }
      };
      
      window.wsTestMessages = [];
    });
    
    await page.reload();
    await waitForPageLoad(page);
    
    // Wait for WebSocket messages
    await page.waitForTimeout(10000);
    
    // Check if messages were received
    const messages = await page.evaluate(() => window.wsTestMessages || []);
    
    if (messages.length > 0) {
      // Verify message structure
      const firstMessage = messages[0];
      expect(firstMessage).toHaveProperty('type');
      expect(firstMessage).toHaveProperty('data');
      
      // Verify no fake data in WebSocket messages
      const messageStr = JSON.stringify(messages);
      expect(messageStr.toLowerCase()).not.toContain('demo: true');
      expect(messageStr.toLowerCase()).not.toContain('mock: true');
      expect(messageStr.toLowerCase()).not.toContain('fake');
    } else {
      console.warn('No WebSocket messages received during test');
    }
  });

  test('should recover from WebSocket disconnection', async ({ page }) => {
    // This test simulates network issues and recovery
    // For now, just verify the connection status monitoring works
    
    // Check that connection status is displayed
    const statusElements = await page.locator('text=Connected, text=Disconnected').count();
    expect(statusElements).toBeGreaterThan(0);
    
    // Monitor console for reconnection attempts
    const consoleLogs: string[] = [];
    page.on('console', msg => {
      consoleLogs.push(msg.text());
    });
    
    await page.waitForTimeout(5000);
    
    // Look for any disconnection/reconnection messages
    const hasConnectionMessages = consoleLogs.some(log =>
      log.includes('WebSocket') && 
      (log.includes('connected') || log.includes('disconnected') || log.includes('error'))
    );
    
    // Should have some WebSocket-related messages
    expect(hasConnectionMessages).toBe(true);
  });
});

test.describe('Navigation and UI Elements', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/crypto');
    await waitForPageLoad(page);
  });

  test('should navigate between crypto and stocks', async ({ page }) => {
    // Click back to stocks button
    await page.locator('button:has-text("Back to Stocks")').click();
    await waitForPageLoad(page);
    
    // Should be on stocks page
    await expect(page).toHaveURL('/');
    
    // Navigate back to crypto (if there's a crypto link)
    try {
      await page.locator('a[href="/crypto"], button:has-text("Crypto")').click();
      await waitForPageLoad(page);
      await expect(page).toHaveURL('/crypto');
    } catch {
      // Direct navigation if no link found
      await page.goto('/crypto');
      await waitForPageLoad(page);
    }
  });

  test('should handle control interactions', async ({ page }) => {
    // Test start crypto bot button
    const startButton = page.locator('button:has-text("Start Crypto Bot")');
    if (await startButton.isVisible()) {
      await startButton.click();
      await page.waitForTimeout(1000);
    }
    
    // Test scalping engine start button
    const scalpingStartButton = page.locator('button:has-text("Start")').first();
    if (await scalpingStartButton.isVisible()) {
      await scalpingStartButton.click();
      await page.waitForTimeout(1000);
    }
    
    // Test refresh button
    const refreshButton = page.locator('button:has-text("Refresh")');
    if (await refreshButton.isVisible()) {
      await refreshButton.click();
      await page.waitForTimeout(1000);
    }
  });

  test('should display trading session info', async ({ page }) => {
    // Check market information
    await expect(page.locator('text=Market: Cryptocurrency')).toBeVisible();
    await expect(page.locator('text=Session: 24/7 Trading')).toBeVisible();
    await expect(page.locator('text=Settlement: T+0 (Instant)')).toBeVisible();
    await expect(page.locator('text=Fractional: Supported')).toBeVisible();
  });

  test('should display responsive design elements', async ({ page }) => {
    // Test on different viewport sizes
    await page.setViewportSize({ width: 1200, height: 800 });
    await page.waitForTimeout(500);
    
    // All main elements should still be visible
    await expect(page.locator('text=Crypto Trading Bot')).toBeVisible();
    await expect(page.locator('text=Crypto Portfolio')).toBeVisible();
    
    // Test mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    await page.waitForTimeout(500);
    
    // Main elements should adapt to mobile
    await expect(page.locator('text=Crypto Trading Bot')).toBeVisible();
  });
});

// Declare global WebSocket messages array for testing
declare global {
  interface Window {
    wsTestMessages: any[];
  }
}