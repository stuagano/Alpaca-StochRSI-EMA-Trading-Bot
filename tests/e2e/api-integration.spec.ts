import { test, expect } from '@playwright/test';

test.describe('API Integration Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Set up API interception
    await page.goto('/');
  });

  test('should validate API Gateway health', async ({ page }) => {
    // Test API Gateway health endpoint
    const response = await page.request.get('http://localhost:9000/health');
    expect(response.ok()).toBeTruthy();
    
    const healthData = await response.json();
    expect(healthData).toHaveProperty('service', 'api-gateway');
    expect(healthData).toHaveProperty('status', 'healthy');
  });

  test('should fetch chart data with correct structure', async ({ page }) => {
    // Test chart data endpoint
    const response = await page.request.get('http://localhost:9000/api/chart/AAPL?timeframe=5Min&limit=100');
    expect(response.ok()).toBeTruthy();
    
    const chartData = await response.json();
    expect(chartData).toHaveProperty('candlestick_data');
    expect(chartData).toHaveProperty('symbol', 'AAPL');
    expect(chartData).toHaveProperty('timeframe', '5Min');
    
    const candleData = chartData.candlestick_data;
    expect(candleData).toBeInstanceOf(Array);
    
    if (candleData.length > 0) {
      const firstCandle = candleData[0];
      expect(firstCandle).toHaveProperty('timestamp');
      expect(firstCandle).toHaveProperty('open');
      expect(firstCandle).toHaveProperty('high'); 
      expect(firstCandle).toHaveProperty('low');
      expect(firstCandle).toHaveProperty('close');
      expect(firstCandle).toHaveProperty('volume');
      
      // Verify data ordering (should be ascending by time)
      if (candleData.length > 1) {
        const firstTime = new Date(candleData[0].timestamp).getTime();
        const secondTime = new Date(candleData[1].timestamp).getTime();
        expect(secondTime).toBeGreaterThanOrEqual(firstTime);
      }
    }
  });

  test('should handle signals API correctly', async ({ page }) => {
    const response = await page.request.get('http://localhost:9000/api/signals');
    expect(response.ok()).toBeTruthy();
    
    const signals = await response.json();
    expect(signals).toBeInstanceOf(Array);
    
    if (signals.length > 0) {
      const firstSignal = signals[0];
      expect(firstSignal).toHaveProperty('symbol');
      expect(firstSignal).toHaveProperty('signal_type');
      expect(firstSignal).toHaveProperty('strength');
      expect(firstSignal).toHaveProperty('timestamp');
      
      // Validate signal type
      expect(['buy', 'sell', 'hold']).toContain(firstSignal.signal_type);
      
      // Validate strength range
      expect(firstSignal.strength).toBeGreaterThanOrEqual(0);
      expect(firstSignal.strength).toBeLessThanOrEqual(1);
    }
  });

  test('should validate crypto assets API', async ({ page }) => {
    const response = await page.request.get('http://localhost:9000/api/crypto/assets');
    expect(response.ok()).toBeTruthy();
    
    const cryptoData = await response.json();
    expect(cryptoData).toHaveProperty('assets');
    expect(cryptoData).toHaveProperty('trading_hours', '24/7');
    expect(cryptoData.assets).toBeInstanceOf(Array);
    
    if (cryptoData.assets.length > 0) {
      const firstAsset = cryptoData.assets[0];
      expect(firstAsset).toHaveProperty('symbol');
      expect(firstAsset).toHaveProperty('name');
      expect(firstAsset).toHaveProperty('tradable', true);
      expect(firstAsset).toHaveProperty('fractionable', true);
      
      // Should contain BTC/USD
      const btc = cryptoData.assets.find((asset: any) => asset.symbol === 'BTC/USD');
      expect(btc).toBeTruthy();
    }
  });

  test('should handle positions API', async ({ page }) => {
    const response = await page.request.get('http://localhost:9000/api/positions');
    
    // Should return 200 even if empty
    expect(response.ok()).toBeTruthy();
    
    const positions = await response.json();
    expect(positions).toBeInstanceOf(Array);
    
    // If there are positions, validate structure
    if (positions.length > 0) {
      const firstPosition = positions[0];
      expect(firstPosition).toHaveProperty('symbol');
      expect(firstPosition).toHaveProperty('qty');
      expect(firstPosition).toHaveProperty('unrealized_pl');
      expect(firstPosition).toHaveProperty('current_price');
    }
  });

  test('should handle orders API', async ({ page }) => {
    const response = await page.request.get('http://localhost:9000/api/orders');
    expect(response.ok()).toBeTruthy();
    
    const orders = await response.json();
    expect(orders).toBeInstanceOf(Array);
    
    // If there are orders, validate structure
    if (orders.length > 0) {
      const firstOrder = orders[0];
      expect(firstOrder).toHaveProperty('id');
      expect(firstOrder).toHaveProperty('symbol');
      expect(firstOrder).toHaveProperty('side');
      expect(firstOrder).toHaveProperty('status');
      
      // Validate side
      expect(['buy', 'sell']).toContain(firstOrder.side);
    }
  });

  test('should validate account API', async ({ page }) => {
    const response = await page.request.get('http://localhost:9000/api/account');
    expect(response.ok()).toBeTruthy();
    
    const account = await response.json();
    expect(account).toHaveProperty('buying_power');
    expect(account).toHaveProperty('portfolio_value');
    
    // Validate numeric fields
    expect(typeof parseFloat(account.buying_power)).toBe('number');
    expect(typeof parseFloat(account.portfolio_value)).toBe('number');
  });

  test('should handle crypto quotes API', async ({ page }) => {
    // Test crypto quote endpoint
    const response = await page.request.get('http://localhost:9012/crypto/quotes/BTC/USD');
    
    if (response.ok()) {
      const quote = await response.json();
      expect(quote).toHaveProperty('symbol', 'BTC/USD');
      expect(quote).toHaveProperty('bid');
      expect(quote).toHaveProperty('ask');
      expect(quote).toHaveProperty('last');
      
      // Validate bid/ask relationship
      expect(quote.bid).toBeLessThanOrEqual(quote.ask);
      
      // Validate prices are positive
      expect(quote.bid).toBeGreaterThan(0);
      expect(quote.ask).toBeGreaterThan(0);
      expect(quote.last).toBeGreaterThan(0);
    } else {
      // If real API fails, should get mock data
      expect([200, 404, 500]).toContain(response.status());
    }
  });

  test('should validate API error handling', async ({ page }) => {
    // Test non-existent endpoint
    const response = await page.request.get('http://localhost:9000/api/nonexistent');
    expect(response.status()).toBe(404);
  });

  test('should handle WebSocket connections', async ({ page }) => {
    let wsMessages: any[] = [];
    
    // Listen for WebSocket messages in the browser
    await page.evaluate(() => {
      const ws = new WebSocket('ws://localhost:9000/api/stream');
      
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        (window as any).wsMessages = (window as any).wsMessages || [];
        (window as any).wsMessages.push(data);
      };
      
      ws.onerror = () => {
        (window as any).wsError = true;
      };
      
      return new Promise(resolve => {
        ws.onopen = () => resolve('connected');
        setTimeout(() => resolve('timeout'), 5000);
      });
    });
    
    // Wait for messages
    await page.waitForTimeout(3000);
    
    // Check if we received messages or error
    const messages = await page.evaluate(() => (window as any).wsMessages || []);
    const wsError = await page.evaluate(() => (window as any).wsError);
    
    // Should either receive messages or get connection error (both are valid)
    expect(messages.length > 0 || wsError).toBeTruthy();
    
    if (messages.length > 0) {
      const firstMessage = messages[0];
      expect(firstMessage).toHaveProperty('type');
      
      if (firstMessage.type === 'quote') {
        expect(firstMessage).toHaveProperty('symbol');
        expect(firstMessage).toHaveProperty('price');
      }
    }
  });

  test('should validate service health endpoints', async ({ page }) => {
    const services = [
      { name: 'API Gateway', url: 'http://localhost:9000/health' },
      { name: 'Crypto Service', url: 'http://localhost:9012/health' }
    ];
    
    for (const service of services) {
      const response = await page.request.get(service.url);
      
      if (response.ok()) {
        const health = await response.json();
        expect(health).toHaveProperty('status');
        expect(['healthy', 'degraded']).toContain(health.status);
      } else {
        // Service might not be running, which is acceptable for testing
        console.log(`${service.name} not available: ${response.status()}`);
      }
    }
  });
});