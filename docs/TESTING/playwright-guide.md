# Playwright Testing Guide for Alpaca Trading Bot

## Overview

This guide covers the Playwright testing setup for the Alpaca Trading Bot dashboard and frontend components.

## Installation

```bash
# Install Playwright and dependencies
npm install --save-dev @playwright/test playwright

# Install browsers
npx playwright install
```

## Project Structure

```
tests/
├── e2e/
│   ├── dashboard/      # Dashboard component tests
│   ├── portfolio/      # Portfolio management tests
│   ├── trading/        # Trading interface tests
│   ├── api/           # API endpoint tests
│   ├── fixtures/      # Test fixtures and mocks
│   └── utils/         # Helper functions
├── screenshots/       # Test screenshots
└── reports/          # Test reports
```

## Running Tests

### All Tests
```bash
npm test
```

### Specific Test Suites
```bash
npm run test:dashboard   # Dashboard tests only
npm run test:portfolio   # Portfolio tests only
npm run test:trading     # Trading tests only
npm run test:api        # API tests only
```

### Browser-Specific Tests
```bash
npm run test:chrome     # Chrome only
npm run test:firefox    # Firefox only
npm run test:safari     # Safari/WebKit only
npm run test:mobile     # Mobile browsers
```

### Debug Mode
```bash
npm run test:debug      # Run with Playwright Inspector
npm run test:headed     # Run with browser window visible
npm run test:ui         # Run with Playwright UI mode
```

### Generate Tests
```bash
npm run test:codegen    # Open Playwright code generator
```

## Test Configuration

The main configuration is in `playwright.config.ts`:

- **Base URL**: `http://localhost:5000` (configurable via `BASE_URL` env var)
- **Browsers**: Chrome, Firefox, Safari, Mobile Chrome, Mobile Safari
- **Parallel Execution**: Enabled
- **Retries**: 2 on CI, 0 locally
- **Screenshots**: On failure
- **Videos**: On failure
- **Traces**: On first retry

## Writing Tests

### Basic Test Structure

```typescript
import { test, expect } from '@playwright/test';

test.describe('Feature Name', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });
  
  test('should do something', async ({ page }) => {
    await page.click('[data-testid="button"]');
    await expect(page.locator('.result')).toBeVisible();
  });
});
```

### Using Fixtures

```typescript
import { test, expect } from '../fixtures/auth.fixture';

test('authenticated test', async ({ authenticatedPage, mockAPI }) => {
  // Test with authentication and mocked API
});
```

### Helper Functions

```typescript
import { DashboardHelpers } from '../utils/helpers';

test('dashboard test', async ({ page }) => {
  const helpers = new DashboardHelpers(page);
  await helpers.waitForDashboardLoad();
  await helpers.clickTab('positions');
});
```

## Test Data & Mocking

### Mock API Responses
The `MockAlpacaAPI` class in fixtures provides pre-configured API mocks:
- Account data
- Positions
- Orders
- Market data
- Trading signals

### Mock WebSocket
Use `mockWebSocket()` helper to simulate real-time updates:
```typescript
await mockWebSocket(page);
```

### Generate Test Data
```typescript
import { generateMockPositions, generateMockOrders } from '../utils/helpers';

const positions = generateMockPositions(10);
const orders = generateMockOrders(5);
```

## Best Practices

### 1. Use Data Attributes
Always use `data-testid` attributes for reliable element selection:
```html
<button data-testid="submit-order">Submit</button>
```

### 2. Wait for Elements
Use proper waiting strategies:
```typescript
await page.waitForSelector('.element');
await page.waitForLoadState('networkidle');
await expect(locator).toBeVisible();
```

### 3. Test Isolation
Each test should be independent:
- Use `beforeEach` for setup
- Clean up after tests
- Don't rely on test order

### 4. Meaningful Assertions
```typescript
// Good
expect(balance).toBeGreaterThan(0);
expect(orderStatus).toBe('filled');

// Bad
expect(result).toBeTruthy();
```

### 5. Handle Async Operations
```typescript
// Wait for API calls
await page.waitForResponse('**/api/positions');

// Wait for WebSocket messages
await page.waitForEvent('websocket');
```

## CI/CD Integration

Tests run automatically on:
- Push to main/develop branches
- Pull requests
- Manual workflow dispatch

GitHub Actions workflow:
- Tests on multiple OS (Ubuntu, Windows, macOS)
- Tests on all browsers
- Uploads reports as artifacts
- Runs in parallel for speed

## Debugging Failed Tests

### 1. View Test Report
```bash
npm run test:report
```

### 2. Debug Specific Test
```bash
npx playwright test path/to/test.spec.ts --debug
```

### 3. View Screenshots/Videos
Check `test-results/` folder for:
- Screenshots on failure
- Videos of failed tests
- Trace files

### 4. Use Playwright Inspector
```bash
npm run test:debug
```

## Performance Testing

### Response Time Checks
```typescript
const start = Date.now();
await page.goto('/');
const loadTime = Date.now() - start;
expect(loadTime).toBeLessThan(3000);
```

### Concurrent Request Testing
```typescript
const responses = await Promise.all([
  request.get('/api/account'),
  request.get('/api/positions'),
  request.get('/api/orders')
]);
```

## Accessibility Testing

```typescript
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('should be accessible', async ({ page }) => {
  await page.goto('/');
  const accessibilityScanResults = await new AxeBuilder({ page }).analyze();
  expect(accessibilityScanResults.violations).toEqual([]);
});
```

## Mobile Testing

### Viewport Testing
```typescript
test('mobile responsive', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 667 });
  // Test mobile layout
});
```

### Device Emulation
```typescript
import { devices } from '@playwright/test';

test.use({ ...devices['iPhone 12'] });
```

## Common Issues & Solutions

### Issue: Tests timeout
**Solution**: Increase timeout in config or specific test
```typescript
test.setTimeout(60000); // 60 seconds
```

### Issue: Element not found
**Solution**: Add proper wait or check selector
```typescript
await page.waitForSelector('.element', { timeout: 10000 });
```

### Issue: Flaky tests
**Solution**: Add retries and proper waits
```typescript
await page.waitForLoadState('networkidle');
await expect(element).toBeVisible({ timeout: 5000 });
```

### Issue: WebSocket connection fails
**Solution**: Use mock WebSocket for tests
```typescript
await mockWebSocket(page);
```

## Extending Tests

### Add New Test Suite
1. Create new folder in `tests/e2e/`
2. Create `*.spec.ts` files
3. Add npm script in `package.json`
4. Update CI workflow if needed

### Add Custom Fixtures
```typescript
export const test = base.extend({
  customFixture: async ({}, use) => {
    // Setup
    await use(customValue);
    // Teardown
  }
});
```

### Add Helper Functions
Add to `tests/e2e/utils/helpers.ts`:
```typescript
export class NewHelper {
  constructor(private page: Page) {}
  
  async customAction() {
    // Implementation
  }
}
```

## Resources

- [Playwright Documentation](https://playwright.dev)
- [Best Practices](https://playwright.dev/docs/best-practices)
- [API Reference](https://playwright.dev/docs/api/class-playwright)
- [Debugging Guide](https://playwright.dev/docs/debug)