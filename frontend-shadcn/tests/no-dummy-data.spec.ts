import { test, expect } from '@playwright/test'

/**
 * Playwright tests to enforce the NO DUMMY DATA policy
 * These tests verify that all API endpoints return real data or proper errors
 * NO mock, fallback, or demo data should ever be returned
 */

const CRYPTO_API_BASE = 'http://localhost:9000'
const FRONTEND_BASE = 'http://localhost:9100'

// List of crypto API endpoints that must return real data only
const CRYPTO_ENDPOINTS = [
  '/api/positions',
  '/api/orders',
  '/api/signals',
  '/api/bars/BTCUSD?timeframe=5Min&limit=10',
  '/api/account',
  '/api/metrics',
  '/api/history',
  '/api/pnl-chart',
  '/api/strategies',
  '/api/assets'
]

// Forbidden dummy data indicators (specific to our app, not framework code)
const DUMMY_DATA_MARKERS = [
  'demo-account',
  'mock-data',
  'fake-data', 
  'test-user',
  'sample-data',
  'dummy-data',
  'fallback-provider',
  'Using demo data',
  'Service unavailable, using demo',
  'demo_mode',
  'mock_enabled'
]

test.describe('No Dummy Data Policy Enforcement', () => {
  
  test.beforeAll(async () => {
    console.log('🚨 Testing NO DUMMY DATA policy enforcement')
    console.log('All endpoints must return real data or throw proper errors')
  })

  test('Frontend should not contain any fallback data providers', async ({ page }) => {
    // Navigate to main page and check for our specific dummy data markers
    await page.goto(FRONTEND_BASE)
    
    // Wait for page to load
    await page.waitForTimeout(2000)
    
    // Get page content (visible text only, not compiled JS)
    const pageContent = await page.locator('body').textContent() || ''
    
    // Check for our specific dummy data markers in visible content
    for (const marker of DUMMY_DATA_MARKERS) {
      expect(pageContent).not.toContain(marker)
    }
    
    // Also check the page title and meta tags
    const title = await page.title()
    expect(title).not.toMatch(/demo|mock|test|sample/i)
  })

  test('Crypto service health check should not contain demo markers', async ({ request }) => {
    const response = await request.get(`${CRYPTO_API_BASE}/health`)
    
    if (response.ok()) {
      const data = await response.json()
      const responseText = JSON.stringify(data)
      
      for (const marker of DUMMY_DATA_MARKERS) {
        expect(responseText).not.toContain(marker)
      }
    }
  })

  CRYPTO_ENDPOINTS.forEach(endpoint => {
    test(`${endpoint} should return real data or proper error`, async ({ request }) => {
      const response = await request.get(`${CRYPTO_API_BASE}${endpoint}`)
      
      if (response.ok()) {
        const data = await response.json()
        const responseText = JSON.stringify(data)
        
        // Check for dummy data markers
        for (const marker of DUMMY_DATA_MARKERS) {
          expect(responseText).not.toContain(marker)
        }
        
        // Verify response structure indicates real data
        if (endpoint.includes('/positions')) {
          expect(data).toHaveProperty('positions')
          expect(data).toHaveProperty('count')
          expect(data).toHaveProperty('timestamp')
          
          // If positions exist, they should have real structure
          if (data.positions && data.positions.length > 0) {
            for (const position of data.positions) {
              expect(position).toHaveProperty('symbol')
              expect(position.symbol).not.toMatch(/^(demo|mock|test|fake)-/)
            }
          }
        }
        
        if (endpoint.includes('/orders')) {
          expect(data).toHaveProperty('orders')
          expect(data).toHaveProperty('count')
          
          // If orders exist, they should have real IDs
          if (data.orders && data.orders.length > 0) {
            for (const order of data.orders) {
              expect(order).toHaveProperty('id')
              expect(order.id).not.toMatch(/^(demo|mock|test|fake)-/)
            }
          }
        }
        
        if (endpoint.includes('/bars')) {
          expect(data).toHaveProperty('bars')
          expect(data).toHaveProperty('symbol')
          
          // If bars exist, they should have real timestamps
          if (data.bars && data.bars.length > 0) {
            for (const bar of data.bars) {
              expect(bar).toHaveProperty('time')
              expect(bar).toHaveProperty('open')
              expect(bar).toHaveProperty('close')
              // Real data should have proper timestamp format
              expect(bar.time).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/)
            }
          }
        }
        
      } else {
        // If service is unavailable, should return proper error, not fallback data
        expect(response.status()).toBeGreaterThanOrEqual(500)
        
        const errorText = await response.text()
        
        // Error messages should indicate real service unavailability
        expect(errorText).toMatch(/(unavailable|not available|service|error)/i)
        expect(errorText).not.toMatch(/(using demo|demo-account|mock-data)/i)
      }
    })
  })

  test('Frontend UI should handle service errors gracefully without dummy data', async ({ page }) => {
    // Navigate to the trading interface
    await page.goto(FRONTEND_BASE)
    
    // Check for any dummy data indicators in the UI
    const pageContent = await page.content()
    
    for (const marker of DUMMY_DATA_MARKERS) {
      expect(pageContent).not.toContain(marker)
    }
    
    // Check console for dummy data warnings
    const consoleLogs: string[] = []
    page.on('console', msg => consoleLogs.push(msg.text()))
    
    // Wait for any async data loading
    await page.waitForTimeout(3000)
    
    // Check console logs for dummy data usage
    const allLogs = consoleLogs.join(' ')
    for (const marker of DUMMY_DATA_MARKERS) {
      expect(allLogs).not.toContain(marker)
    }
  })

  test('WebSocket connections should not send dummy data', async ({ page }) => {
    const wsMessages: any[] = []
    
    // Capture WebSocket messages
    page.on('websocket', ws => {
      ws.on('framereceived', event => {
        try {
          const data = JSON.parse(event.payload.toString())
          wsMessages.push(data)
        } catch (e) {
          // Ignore non-JSON messages
        }
      })
    })
    
    // Navigate and wait for WebSocket connections
    await page.goto(FRONTEND_BASE)
    await page.waitForTimeout(5000)
    
    // Check all WebSocket messages for dummy data markers
    for (const message of wsMessages) {
      const messageText = JSON.stringify(message)
      for (const marker of DUMMY_DATA_MARKERS) {
        expect(messageText).not.toContain(marker)
      }
    }
  })

  test('API client should throw errors instead of using fallbacks', async ({ page }) => {
    // Navigate to frontend
    await page.goto(FRONTEND_BASE)
    
    // Check for any error handling that uses fallback data
    const errors: string[] = []
    page.on('pageerror', error => errors.push(error.message))
    
    // Wait for page to load and make API calls
    await page.waitForTimeout(5000)
    
    // Any errors should be about service unavailability, not dummy data usage
    for (const error of errors) {
      expect(error).not.toMatch(/(demo-account|mock-data|dummy-data)/i)
    }
  })

  test('Crypto service configuration should enforce real data only', async ({ request }) => {
    const response = await request.get(`${CRYPTO_API_BASE}/api/config`)
    
    if (response.ok()) {
      const config = await response.json()
      const configText = JSON.stringify(config)
      
      // Configuration should not contain demo flags
      for (const marker of DUMMY_DATA_MARKERS) {
        expect(configText).not.toContain(marker)
      }
      
      // Should not have demo mode enabled
      expect(config).not.toHaveProperty('demo_mode')
      expect(config).not.toHaveProperty('use_fake_data')
      expect(config).not.toHaveProperty('mock_data_enabled')
    }
  })
})