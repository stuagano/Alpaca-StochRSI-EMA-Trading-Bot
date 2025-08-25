const { chromium } = require('playwright');

(async () => {
  console.log('Starting simple test...');
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  
  try {
    console.log('Navigating to http://localhost:8765...');
    await page.goto('http://localhost:8765', { timeout: 5000 });
    
    console.log('Page loaded successfully!');
    const title = await page.title();
    console.log('Page title:', title);
    
    // Check for dashboard grid
    const dashboardGrid = await page.$('.dashboard-grid');
    if (dashboardGrid) {
      console.log('✓ Dashboard grid found');
    } else {
      console.log('✗ Dashboard grid NOT found');
    }
    
    // Check for trading header
    const tradingHeader = await page.$('.trading-header');
    if (tradingHeader) {
      console.log('✓ Trading header found');
    } else {
      console.log('✗ Trading header NOT found');
    }
    
    // Test API endpoint
    console.log('\nTesting API endpoint...');
    const response = await page.request.get('http://localhost:8765/api/account');
    console.log('API Response status:', response.status());
    if (response.ok()) {
      const data = await response.json();
      console.log('API Response:', JSON.stringify(data, null, 2));
    } else {
      console.log('API Error:', response.statusText());
    }
    
  } catch (error) {
    console.error('Test failed:', error.message);
  } finally {
    await browser.close();
    console.log('\nTest complete!');
  }
})();