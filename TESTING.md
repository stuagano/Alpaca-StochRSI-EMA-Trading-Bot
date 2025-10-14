# Testing Guide - Trading Bot Dashboard

This guide explains how to test the Trading Bot Dashboard interface using Playwright.

## Quick Start

### 1. Install Dependencies
```bash
npm install
npx playwright install chromium
```

### 2. Run Tests

**Option A: Static Tests (No Backend Required)**
```bash
npx playwright test static-dashboard.spec.js
```

**Option B: Full Integration Tests (Backend Required)**

First, start the Flask backend:
```bash
python backend/api/run.py --port 5001
```

Then in another terminal:
```bash
npm test
```

**Option C: Use the Test Script**
```bash
./test-dashboard.sh
```

## Test Suites

### 📄 static-dashboard.spec.js
- **Purpose**: Tests the dashboard HTML file directly without backend
- **No server required**
- **Fast execution**
- **Tests**:
  - HTML structure and elements
  - CSS styling and layout
  - JavaScript initialization
  - External dependency loading (Chart.js, Socket.IO)
  - Button presence and functionality
  - Loading states

**Run with:**
```bash
npx playwright test static-dashboard.spec.js --headed
```

### 🌐 dashboard.spec.js
- **Purpose**: Full end-to-end tests with backend integration
- **Requires Flask server running on port 5001**
- **Tests**:
  - Page loading and navigation
  - WebSocket connectivity
  - API data fetching
  - Real-time updates
  - User interactions
  - Error handling
  - Visual regression

**Run with:**
```bash
# Start server first
python backend/api/run.py --port 5001

# In another terminal
npx playwright test dashboard.spec.js --headed
```

### 🔌 api.spec.js
- **Purpose**: Tests Flask API endpoints directly
- **Requires Flask server running**
- **Tests**:
  - Endpoint availability
  - Response formats
  - Status codes
  - Data structure validation
  - Trading operations

**Run with:**
```bash
npx playwright test api.spec.js
```

## Available NPM Scripts

```bash
# Run all tests (headless)
npm test

# Run tests with visible browser
npm run test:headed

# Run tests in UI mode (interactive)
npm run test:ui

# Run tests in debug mode (step through)
npm run test:debug

# Show test report
npm run test:report
```

## Test Modes

### Headless Mode (Default)
Tests run without visible browser window. Faster and suitable for CI/CD.
```bash
npm test
```

### Headed Mode
See the browser while tests run. Good for debugging.
```bash
npm run test:headed
```

### UI Mode
Interactive mode with test explorer, timeline, and debugging tools.
```bash
npm run test:ui
```

### Debug Mode
Step through tests line by line with browser DevTools.
```bash
npm run test:debug
```

## Troubleshooting

### Tests Failing with "Connection Refused"

**Problem**: Flask server not running

**Solution**:
```bash
# Terminal 1: Start Flask server
python backend/api/run.py --port 5001

# Terminal 2: Run tests
npm test
```

### Tests Timeout

**Problem**: Backend services not initialized

**Solution**: Run only static tests first to verify HTML:
```bash
npx playwright test static-dashboard.spec.js
```

### WebSocket Connection Errors

**Problem**: Socket.IO not connecting

**Solution**: Check these:
1. Flask server is running
2. SocketIO is installed: `pip install flask-socketio`
3. Check backend logs for errors
4. Verify port 5001 is not blocked

### "Browser not installed" Error

**Solution**: Install Playwright browsers
```bash
npx playwright install chromium
# Or install all browsers
npx playwright install
```

## Configuration

Edit `playwright.config.js` to customize:

- **Base URL**: Default is `http://localhost:5001`
- **Timeout**: Default is 30 seconds per test
- **Browsers**: chromium, firefox, webkit
- **Screenshots**: Taken on failure
- **Video**: Recorded on failure
- **Trace**: Captured on first retry

## Test Reports

After running tests, view the HTML report:
```bash
npm run test:report
```

This opens an interactive report showing:
- Test results (pass/fail)
- Screenshots of failures
- Videos of test runs
- Execution timeline
- Network activity
- Console logs

## Writing New Tests

Create a new test file in `tests/e2e/`:

```javascript
// @ts-check
const { test, expect } = require('@playwright/test');

test.describe('My Test Suite', () => {

  test('should do something', async ({ page }) => {
    await page.goto('/dashboard.html');
    // Your test code here
    await expect(page.locator('h1')).toBeVisible();
  });

});
```

## CI/CD Integration

For GitHub Actions or other CI systems:

```yaml
- name: Install dependencies
  run: npm ci

- name: Install Playwright browsers
  run: npx playwright install --with-deps chromium

- name: Start Flask server
  run: python backend/api/run.py --port 5001 &

- name: Run tests
  run: npm test

- name: Upload test report
  if: always()
  uses: actions/upload-artifact@v3
  with:
    name: playwright-report
    path: playwright-report/
```

## Best Practices

1. **Run static tests first** - They're faster and don't need backend
2. **Use headed mode for debugging** - See what's happening
3. **Check test reports** - Contains screenshots and videos of failures
4. **One test, one assertion** - Makes failures easier to diagnose
5. **Use data-testid attributes** - More stable than CSS selectors

## Common Issues & Solutions

### Issue: "Chromium not found"
```bash
npx playwright install chromium
```

### Issue: "Port 5001 already in use"
```bash
# Find and kill the process
lsof -ti:5001 | xargs kill -9

# Or use a different port
python backend/api/run.py --port 5002
# Update playwright.config.js baseURL to match
```

### Issue: Tests pass locally but fail in CI
- Ensure browser dependencies are installed: `npx playwright install --with-deps`
- Increase timeouts in CI environment
- Use `process.env.CI` checks in playwright.config.js

### Issue: Flaky tests (sometimes pass, sometimes fail)
- Add explicit waits: `await page.waitForSelector('.element')`
- Use `waitForLoadState('networkidle')` before assertions
- Avoid hard-coded `setTimeout`, use Playwright's built-in waiting

## Getting Help

- **Playwright Docs**: https://playwright.dev
- **Test Trace Viewer**: `npx playwright show-trace trace.zip`
- **Inspector**: `npx playwright test --debug`
- **VSCode Extension**: Install "Playwright Test for VSCode"

## Next Steps

1. Start with static tests to verify HTML structure
2. Run API tests to verify backend endpoints
3. Run full dashboard tests to verify integration
4. Add more test coverage as needed
5. Integrate into CI/CD pipeline
