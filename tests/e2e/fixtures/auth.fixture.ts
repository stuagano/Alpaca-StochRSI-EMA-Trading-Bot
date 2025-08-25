import { test as base, expect } from '@playwright/test';

class MockAlpacaAPI {
  constructor(private page: any) {}
  
  async setup() {
    // Intercept API calls
    await this.page.route('**/api/account', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          balance: 100000,
          buying_power: 50000,
          cash: 50000,
          pattern_day_trader: false,
          account_number: 'TEST123456',
          status: 'ACTIVE'
        })
      });
    });
    
    await this.page.route('**/api/positions', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          positions: [
            {
              symbol: 'AAPL',
              qty: 100,
              avg_entry_price: 150.00,
              current_price: 155.00,
              market_value: 15500,
              unrealized_pl: 500,
              unrealized_plpc: 3.33,
              side: 'long'
            },
            {
              symbol: 'GOOGL',
              qty: 50,
              avg_entry_price: 2800.00,
              current_price: 2850.00,
              market_value: 142500,
              unrealized_pl: 2500,
              unrealized_plpc: 1.79,
              side: 'long'
            }
          ]
        })
      });
    });
    
    await this.page.route('**/api/signals/latest', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          signals: {
            'AAPL': { signal: 'BUY', strength: 0.85, timestamp: new Date().toISOString() },
            'GOOGL': { signal: 'HOLD', strength: 0.60, timestamp: new Date().toISOString() },
            'MSFT': { signal: 'SELL', strength: 0.30, timestamp: new Date().toISOString() }
          }
        })
      });
    });
  }
  
  async cleanup() {
    // Cleanup if needed
  }
}

type AuthFixtures = {
  authenticatedPage: any;
  mockAPI: MockAlpacaAPI;
};

export const test = base.extend<AuthFixtures>({
  authenticatedPage: async ({ page }, use) => {
    // Mock authentication if needed
    await page.addInitScript(() => {
      window.localStorage.setItem('auth_token', 'test-token');
      window.localStorage.setItem('api_connected', 'true');
    });
    
    await use(page);
  },
  
  mockAPI: async ({ page }, use) => {
    const mockAPI = new MockAlpacaAPI(page);
    await mockAPI.setup();
    await use(mockAPI);
    await mockAPI.cleanup();
  },
});

export { expect };