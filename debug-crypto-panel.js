const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();

  // Listen for console logs and errors
  page.on('console', msg => {
    if (msg.type() === 'error') {
      console.log('❌ Console Error:', msg.text());
    } else if (msg.type() === 'warning') {
      console.log('⚠️ Console Warning:', msg.text());
    }
  });

  page.on('pageerror', error => {
    console.log('❌ Page Error:', error.message);
  });

  console.log('Navigating to dashboard...');
  await page.goto('http://localhost:9100', { waitUntil: 'networkidle' });
  await page.waitForTimeout(3000);

  console.log('Clicking crypto tab...');
  await page.click('[data-testid="crypto-tab"]');
  await page.waitForTimeout(3000);

  // Check if crypto trading panel loaded
  const cryptoPanel = page.locator('[data-testid="crypto-247-indicator"]');
  const panelVisible = await cryptoPanel.isVisible();
  console.log('Crypto 24/7 indicator visible:', panelVisible);

  // Check for crypto symbol selector
  const symbolSelector = page.locator('[data-testid="crypto-symbol-select"]');
  const selectorVisible = await symbolSelector.isVisible();
  console.log('Crypto symbol selector visible:', selectorVisible);

  // Check for crypto assets
  const assetSelector = page.locator('[data-testid="crypto-asset-selector"]');
  const assetsVisible = await assetSelector.isVisible();
  console.log('Crypto asset selector visible:', assetsVisible);

  // Take screenshot
  await page.screenshot({ path: 'crypto-debug.png', fullPage: true });
  console.log('Screenshot taken: crypto-debug.png');

  await browser.close();
})();