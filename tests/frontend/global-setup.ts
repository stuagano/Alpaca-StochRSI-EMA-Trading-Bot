/**
 * Global setup for Playwright tests
 * Ensures trading service is running and accessible before tests begin
 */
import { chromium, FullConfig } from '@playwright/test';

async function globalSetup(config: FullConfig) {
  console.log('🚀 Starting global setup for trading bot tests...');
  
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    // Check if trading service is accessible
    console.log('⏳ Checking if trading service is accessible...');
    await page.goto('http://localhost:9100', { waitUntil: 'domcontentloaded', timeout: 30000 });
    
    // Verify basic page loads
    await page.waitForSelector('body', { timeout: 10000 });
    console.log('✅ Trading service is accessible');

    // Check API endpoints are responding
    const apiResponse = await page.request.get('http://localhost:9000/api/account');
    if (apiResponse.ok()) {
      console.log('✅ API endpoints are responding');
    } else {
      console.log('⚠️  API endpoints may not be fully ready, but proceeding with tests');
    }

    // Check WebSocket connectivity
    try {
      await page.evaluate(async () => {
        return new Promise((resolve, reject) => {
          const ws = new WebSocket('ws://localhost:9000/ws/trading');
          ws.onopen = () => {
            ws.close();
            resolve(true);
          };
          ws.onerror = () => reject(false);
          setTimeout(() => reject(false), 5000);
        });
      });
      console.log('✅ WebSocket connection is working');
    } catch {
      console.log('⚠️  WebSocket connection test failed, but proceeding with tests');
    }

    console.log('🎯 Global setup completed successfully');
    
  } catch (error) {
    console.error('❌ Global setup failed:', error);
    throw error;
  } finally {
    await context.close();
    await browser.close();
  }
}

export default globalSetup;