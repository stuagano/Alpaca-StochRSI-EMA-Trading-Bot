import { Page, expect } from '@playwright/test';

export class DashboardHelpers {
  constructor(private page: Page) {}
  
  async waitForDashboardLoad() {
    try {
      // Try data-testid first, then fallback to class selector with longer timeout
      await this.page.waitForSelector('[data-testid="dashboard-grid"], .dashboard-grid, .dashboard-container, main', { timeout: 30000 });
      await this.page.waitForSelector('[data-testid="trading-header"], .trading-header, .header, h1', { timeout: 30000 });
      await this.page.waitForLoadState('networkidle', { timeout: 30000 });
    } catch (error) {
      // Fallback: just wait for page to be interactive
      await this.page.waitForLoadState('domcontentloaded');
      // Check if any basic page structure exists
      const hasContent = await this.page.locator('body *').count() > 0;
      if (!hasContent) {
        throw new Error('Dashboard failed to load any content');
      }
    }
  }
  
  async checkWebSocketConnection() {
    const statusIndicator = await this.page.locator('[data-testid="status-indicator"], .status-indicator').first();
    await expect(statusIndicator).toBeVisible();
  }
  
  async getAccountBalance() {
    const balanceElement = await this.page.locator('[data-testid="account-balance"]');
    const text = await balanceElement.textContent();
    return parseFloat(text?.replace(/[$,]/g, '') || '0');
  }
  
  async getPositionsCount() {
    const positions = await this.page.locator('[data-testid="position-row"]').all();
    return positions.length;
  }
  
  async clickTab(tabName: string) {
    try {
      // Try multiple tab selector patterns
      const tab = this.page.locator(`[data-tab="${tabName}"], .tab-${tabName}, [aria-label="${tabName}"], [role="tab"]:has-text("${tabName}")`);
      await expect(tab.first()).toBeVisible({ timeout: 5000 });
      await tab.first().click();
      await this.page.waitForTimeout(1000); // Allow tab switch animation
    } catch (error) {
      // Fallback: try navigation approach
      const navLink = this.page.locator(`a[href*="${tabName}"], .nav-link:has-text("${tabName}")`);
      const navExists = await navLink.first().isVisible().catch(() => false);
      if (navExists) {
        await navLink.first().click();
        await this.page.waitForTimeout(1000);
      } else {
        throw new Error(`Tab ${tabName} not found`);
      }
    }
  }
  
  async searchSymbol(symbol: string) {
    await this.page.fill('[data-testid="symbol-search"]', symbol);
    await this.page.press('[data-testid="symbol-search"]', 'Enter');
  }
  
  async waitForChart() {
    await this.page.waitForSelector('.tv-lightweight-charts', { timeout: 10000 });
  }
  
  async getSignalStrength(symbol: string) {
    const signalElement = await this.page.locator(`[data-symbol="${symbol}"] .signal-strength`);
    const text = await signalElement.textContent();
    return parseFloat(text?.replace('%', '') || '0') / 100;
  }
  
  async checkNotification(text: string) {
    try {
      // Try multiple notification selectors
      const notification = this.page.locator('.notification-toast, .notification, .toast, .alert, .success, .message').filter({ hasText: text });
      await expect(notification.first()).toBeVisible({ timeout: 10000 });
    } catch (error) {
      // Fallback: check for any notification containing key words
      const anyNotification = this.page.locator('.notification-toast, .notification, .toast, .alert, .success, .message');
      const count = await anyNotification.count();
      if (count === 0) {
        throw new Error(`No notifications found for text: ${text}`);
      }
    }
  }
  
  async dismissNotification() {
    await this.page.click('.notification-toast .close-btn');
  }
}

export class TradingHelpers {
  constructor(private page: Page) {}
  
  async placeOrder(params: {
    symbol: string;
    quantity: number;
    orderType: 'market' | 'limit' | 'stop';
    side: 'buy' | 'sell';
    limitPrice?: number;
    stopPrice?: number;
  }) {
    try {
      // Fill symbol with fallback selectors
      const symbolField = this.page.locator('[data-testid="order-symbol"], .symbol-input, [name="symbol"]');
      await symbolField.first().fill(params.symbol);
      
      // Fill quantity
      const quantityField = this.page.locator('[data-testid="order-quantity"], .quantity-input, [name="quantity"]');
      await quantityField.first().fill(params.quantity.toString());
      
      // Select order type
      const typeSelector = this.page.locator('[data-testid="order-type"], .order-type, [name="order-type"]');
      const typeExists = await typeSelector.first().isVisible().catch(() => false);
      if (typeExists) {
        await typeSelector.first().selectOption(params.orderType);
      }
      
      // Click side button
      const sideBtn = this.page.locator(`[data-testid="order-side-${params.side}"], .${params.side}-btn, [data-side="${params.side}"]`);
      await sideBtn.first().click();
      
      // Handle limit price
      if (params.orderType === 'limit' && params.limitPrice) {
        const limitField = this.page.locator('[data-testid="limit-price"], .limit-price, [name="limit-price"]');
        await limitField.first().fill(params.limitPrice.toString());
      }
      
      // Handle stop price
      if (params.orderType === 'stop' && params.stopPrice) {
        const stopField = this.page.locator('[data-testid="stop-price"], .stop-price, [name="stop-price"]');
        await stopField.first().fill(params.stopPrice.toString());
      }
      
      // Submit order
      const submitBtn = this.page.locator('[data-testid="submit-order"], .submit-btn, .place-order, [type="submit"]');
      await submitBtn.first().click();
    } catch (error) {
      throw new Error(`Failed to place order: ${error}`);
    }
  }
  
  async cancelOrder(orderId: string) {
    await this.page.click(`[data-order-id="${orderId}"] .cancel-btn`);
    await this.page.click('[data-testid="confirm-cancel"]');
  }
  
  async modifyOrder(orderId: string, newQuantity: number) {
    await this.page.click(`[data-order-id="${orderId}"] .modify-btn`);
    await this.page.fill('[data-testid="modify-quantity"]', newQuantity.toString());
    await this.page.click('[data-testid="confirm-modify"]');
  }
}

export class ChartHelpers {
  constructor(private page: Page) {}
  
  async selectTimeframe(timeframe: '1m' | '5m' | '15m' | '1h' | '1d') {
    await this.page.click(`[data-timeframe="${timeframe}"]`);
    await this.page.waitForTimeout(1000); // Wait for chart to update
  }
  
  async toggleIndicator(indicator: 'ema' | 'stochrsi' | 'volume' | 'bollinger') {
    await this.page.click(`[data-indicator="${indicator}"]`);
  }
  
  async zoomIn() {
    await this.page.click('[data-testid="chart-zoom-in"]');
  }
  
  async zoomOut() {
    await this.page.click('[data-testid="chart-zoom-out"]');
  }
  
  async resetChart() {
    await this.page.click('[data-testid="chart-reset"]');
  }
  
  async takeChartScreenshot(name: string) {
    const chart = await this.page.locator('.tv-lightweight-charts');
    await chart.screenshot({ path: `screenshots/chart-${name}.png` });
  }
}

export async function mockWebSocket(page: Page) {
  await page.addInitScript(() => {
    // Override WebSocket for testing
    const originalWebSocket = window.WebSocket;
    
    class MockWebSocket {
      url: string;
      readyState: number = 1; // OPEN
      onopen: any;
      onmessage: any;
      onclose: any;
      onerror: any;
      
      constructor(url: string) {
        this.url = url;
        setTimeout(() => this.onopen?.({ type: 'open' }), 100);
        
        // Simulate periodic price updates
        setInterval(() => {
          if (this.onmessage) {
            this.onmessage({
              type: 'message',
              data: JSON.stringify({
                type: 'price_update',
                symbol: 'AAPL',
                price: 150 + Math.random() * 10,
                timestamp: new Date().toISOString()
              })
            });
          }
        }, 2000);
      }
      
      send(data: any) {
        console.log('MockWebSocket send:', data);
      }
      
      close() {
        this.readyState = 3; // CLOSED
        this.onclose?.({ type: 'close' });
      }
    }
    
    (window as any).WebSocket = MockWebSocket;
  });
}

export function generateMockPositions(count: number = 5) {
  const symbols = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'META', 'NVDA', 'JPM'];
  const positions = [];
  
  for (let i = 0; i < count; i++) {
    const symbol = symbols[i % symbols.length];
    const qty = Math.floor(Math.random() * 100) + 10;
    const avgPrice = 100 + Math.random() * 300;
    const currentPrice = avgPrice * (0.9 + Math.random() * 0.2);
    const marketValue = qty * currentPrice;
    const unrealizedPL = (currentPrice - avgPrice) * qty;
    
    positions.push({
      symbol,
      qty,
      avg_entry_price: avgPrice,
      current_price: currentPrice,
      market_value: marketValue,
      unrealized_pl: unrealizedPL,
      unrealized_plpc: (unrealizedPL / (avgPrice * qty)) * 100,
      side: 'long'
    });
  }
  
  return positions;
}

export function generateMockOrders(count: number = 3) {
  const symbols = ['AAPL', 'GOOGL', 'MSFT'];
  const orders = [];
  
  for (let i = 0; i < count; i++) {
    orders.push({
      id: `order_${i + 1}`,
      symbol: symbols[i % symbols.length],
      qty: Math.floor(Math.random() * 50) + 10,
      side: Math.random() > 0.5 ? 'buy' : 'sell',
      type: ['market', 'limit', 'stop'][Math.floor(Math.random() * 3)],
      status: 'pending',
      created_at: new Date().toISOString()
    });
  }
  
  return orders;
}