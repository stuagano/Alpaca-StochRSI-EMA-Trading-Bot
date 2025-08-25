const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();

  console.log('Navigating to dashboard...');
  await page.goto('http://localhost:9100', { waitUntil: 'networkidle' });

  // Wait for page to load
  await page.waitForTimeout(3000);

  // Check if crypto tab exists
  const cryptoTab = await page.locator('[data-testid="crypto-tab"]');
  const isVisible = await cryptoTab.isVisible();
  
  console.log('Crypto tab visible:', isVisible);

  if (isVisible) {
    console.log('Crypto tab found! Clicking it...');
    await cryptoTab.click();
    await page.waitForTimeout(2000);
    
    // Take screenshot after clicking crypto tab
    await page.screenshot({ path: 'crypto-mode.png' });
    console.log('Screenshot taken: crypto-mode.png');
  } else {
    console.log('Crypto tab not found. Taking screenshot of current state...');
    await page.screenshot({ path: 'no-crypto-tab.png' });
    
    // List all tabs that are visible
    const allTabs = await page.locator('[role="tab"]').all();
    console.log('Available tabs:');
    for (const tab of allTabs) {
      const text = await tab.textContent();
      console.log('- ', text);
    }
  }

  await browser.close();
})();