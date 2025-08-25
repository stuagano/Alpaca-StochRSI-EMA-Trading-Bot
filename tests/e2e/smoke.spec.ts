import { test, expect } from '@playwright/test';

test.describe('Smoke Tests', () => {
  test('should load dashboard', async ({ page }) => {
    await page.goto('http://localhost:8765');
    
    // Check title
    await expect(page).toHaveTitle(/Trading Dashboard/);
    
    // Check main elements exist
    await expect(page.locator('.dashboard-grid')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('.trading-header')).toBeVisible({ timeout: 5000 });
  });
  
  test('should fetch account data', async ({ request }) => {
    const response = await request.get('http://localhost:8765/api/account');
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data.success).toBe(true);
    expect(data.balance).toBeDefined();
  });
  
  test('should fetch positions', async ({ request }) => {
    const response = await request.get('http://localhost:8765/api/positions');
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data.success).toBe(true);
    expect(Array.isArray(data.positions)).toBe(true);
  });
  
  test('should have WebSocket connection indicator', async ({ page }) => {
    await page.goto('http://localhost:8765');
    
    // Wait for page to load
    await page.waitForLoadState('networkidle');
    
    // Check for connection status element
    const statusIndicator = page.locator('.status-indicator, .connection-status');
    await expect(statusIndicator.first()).toBeVisible({ timeout: 5000 });
  });
  
  test('should display chart container', async ({ page }) => {
    await page.goto('http://localhost:8765');
    
    // Check for chart container
    const chartContainer = page.locator('.chart-container, #main-chart, .tv-lightweight-charts');
    await expect(chartContainer.first()).toBeVisible({ timeout: 5000 });
  });
});