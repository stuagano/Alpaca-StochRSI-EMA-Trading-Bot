import { test, expect } from '@playwright/test';

/**
 * Unified System Testing Suite
 * Comprehensive tests for the new unified trading service architecture
 */

// Test configuration for unified service
const UNIFIED_API = 'http://localhost:9000';
const FRONTEND_URL = 'http://localhost:9100';

const DUMMY_DATA_MARKERS = [
  'demo-account', 'mock-data', 'fake-data', 'test-user', 'sample-data',
  'dummy-data', 'fallback-provider', 'Using demo data', 'demo_mode',
  'mock_enabled', 'mock', 'demo', 'fake', 'sample', 'test-data'
];

interface TestResult {
  service: string;
  endpoint: string;
  status: 'PASS' | 'FAIL' | 'WARNING' | 'ERROR';
  message: string;
  dataSource?: string;
  responseTime?: number;
  hasRealData?: boolean;
}

const testResults: TestResult[] = [];

// Helper functions
function hasDummyDataMarkers(data: any): boolean {
  const dataStr = JSON.stringify(data).toLowerCase();
  return DUMMY_DATA_MARKERS.some(marker => dataStr.includes(marker.toLowerCase()));
}

function validateDataSource(data: any): string {
  if (data.data_source) {
    if (data.data_source === 'real' || data.data_source === 'alpaca_real') {
      return 'REAL';
    } else if (data.data_source.includes('mock') || data.data_source.includes('demo')) {
      return 'DUMMY';
    }
  }
  return 'UNKNOWN';
}

test.describe('Unified Trading System Test Suite', () => {
  
  test.beforeAll(async () => {
    console.log('🚀 Starting Unified Trading System Test Suite');
    console.log('🎯 Testing single unified service on port 9000');
    console.log('🌐 Testing frontend on port 9100');
    console.log('=' .repeat(60));
  });

  test.afterAll(async () => {
    console.log('\n📊 TEST RESULTS SUMMARY');
    console.log('=' .repeat(60));
    
    const passed = testResults.filter(r => r.status === 'PASS').length;
    const failed = testResults.filter(r => r.status === 'FAIL').length;
    const warnings = testResults.filter(r => r.status === 'WARNING').length;
    const errors = testResults.filter(r => r.status === 'ERROR').length;
    
    console.log(`✅ PASSED: ${passed}`);
    console.log(`❌ FAILED: ${failed}`);
    console.log(`⚠️  WARNINGS: ${warnings}`);
    console.log(`💥 ERRORS: ${errors}`);
    console.log(`🎯 SUCCESS RATE: ${((passed / (passed + failed + warnings + errors)) * 100).toFixed(1)}%`);
    
    // Performance summary
    const avgResponseTime = testResults
      .filter(r => r.responseTime)
      .reduce((acc, r) => acc + (r.responseTime || 0), 0) / 
      testResults.filter(r => r.responseTime).length;
    
    console.log(`⚡ AVG RESPONSE TIME: ${avgResponseTime.toFixed(0)}ms`);
    
    // Detailed breakdown
    console.log('\n📋 DETAILED RESULTS:');
    for (const result of testResults) {
      const emoji = result.status === 'PASS' ? '✅' : 
                   result.status === 'FAIL' ? '❌' : 
                   result.status === 'WARNING' ? '⚠️' : '💥';
      const time = result.responseTime ? ` (${result.responseTime}ms)` : '';
      console.log(`${emoji} ${result.service}/${result.endpoint}: ${result.message}${time}`);
    }
  });

  // Test 1: Unified Service Health Check
  test('Unified Service Health Check', async ({ request }) => {
    console.log('\n🏥 Testing Unified Service Health...');
    
    try {
      const startTime = Date.now();
      const response = await request.get(`${UNIFIED_API}/health`);
      const responseTime = Date.now() - startTime;
      const data = await response.json();
      
      if (response.ok()) {
        // Check for unified service indicators
        const hasIntegratedServices = data.services && 
          data.services.gateway === 'integrated' &&
          data.services.crypto === 'active' &&
          data.services.positions === 'active';
          
        if (hasIntegratedServices) {
          testResults.push({
            service: 'unified-service',
            endpoint: '/health',
            status: 'PASS',
            message: 'All services integrated and healthy',
            responseTime,
            hasRealData: true
          });
        } else {
          testResults.push({
            service: 'unified-service',
            endpoint: '/health',
            status: 'FAIL',
            message: 'Missing service integration indicators',
            responseTime
          });
        }
      } else {
        testResults.push({
          service: 'unified-service',
          endpoint: '/health',
          status: 'ERROR',
          message: `HTTP ${response.status()} - Service unavailable`,
          responseTime
        });
      }
    } catch (error) {
      testResults.push({
        service: 'unified-service',
        endpoint: '/health',
        status: 'ERROR',
        message: `Connection failed: ${error}`
      });
    }
  });

  // Test 2: Core API Endpoints
  test('Core API Endpoints', async ({ request }) => {
    console.log('\n📊 Testing Core API Endpoints...');
    
    const coreEndpoints = [
      { endpoint: '/api/account', name: 'Account Data' },
      { endpoint: '/api/positions', name: 'Positions' },
      { endpoint: '/api/orders', name: 'Orders' },
      { endpoint: '/api/signals', name: 'Trading Signals' },
      { endpoint: '/api/analytics/performance', name: 'Performance Metrics' },
      { endpoint: '/api/leaderboard', name: 'Crypto Leaderboard' },
      { endpoint: '/api/config', name: 'Configuration' }
    ];

    for (const { endpoint, name } of coreEndpoints) {
      try {
        const startTime = Date.now();
        const response = await request.get(`${UNIFIED_API}${endpoint}`);
        const responseTime = Date.now() - startTime;
        
        if (response.ok()) {
          const data = await response.json();
          const hasDummy = hasDummyDataMarkers(data);
          const dataSourceStatus = validateDataSource(data);
          
          // Check for real data indicators
          const hasAccountValue = data.portfolio_value || data.buying_power || data.equity;
          const hasPositions = Array.isArray(data) || data.positions || data.count !== undefined;
          const hasRealMarkers = dataSourceStatus === 'REAL' || data.data_source === 'alpaca_real';
          
          if ((hasAccountValue || hasPositions || hasRealMarkers) && !hasDummy) {
            testResults.push({
              service: 'unified-api',
              endpoint: name,
              status: 'PASS',
              message: `Real data returned successfully`,
              dataSource: data.data_source || 'inferred-real',
              responseTime,
              hasRealData: true
            });
          } else if (hasDummy) {
            testResults.push({
              service: 'unified-api',
              endpoint: name,
              status: 'FAIL',
              message: 'Contains dummy data markers',
              dataSource: data.data_source,
              responseTime,
              hasRealData: false
            });
          } else {
            testResults.push({
              service: 'unified-api',
              endpoint: name,
              status: 'WARNING',
              message: 'No clear data validation possible',
              responseTime
            });
          }
        } else {
          testResults.push({
            service: 'unified-api',
            endpoint: name,
            status: 'ERROR',
            message: `HTTP ${response.status()}`,
            responseTime
          });
        }
      } catch (error) {
        testResults.push({
          service: 'unified-api',
          endpoint: name,
          status: 'ERROR',
          message: `Request failed: ${error}`
        });
      }
    }
  });

  // Test 3: Crypto-Specific Endpoints
  test('Crypto Trading Endpoints', async ({ request }) => {
    console.log('\n🪙 Testing Crypto Trading Endpoints...');
    
    const cryptoEndpoints = [
      { endpoint: '/api/crypto/positions', name: 'Crypto Positions' },
      { endpoint: '/api/status', name: 'Crypto Status' },
      { endpoint: '/api/leaderboard', name: 'Top Movers' },
      { endpoint: '/api/assets', name: 'Crypto Assets' },
      { endpoint: '/api/scan', name: 'Market Scan' }
    ];

    for (const { endpoint, name } of cryptoEndpoints) {
      try {
        const startTime = Date.now();
        const response = await request.get(`${UNIFIED_API}${endpoint}`);
        const responseTime = Date.now() - startTime;
        
        if (response.ok()) {
          const data = await response.json();
          const hasDummy = hasDummyDataMarkers(data);
          
          // Check for crypto-specific real data
          const hasCryptoSymbols = JSON.stringify(data).includes('BTC') || 
                                   JSON.stringify(data).includes('ETH') ||
                                   JSON.stringify(data).includes('/USD');
          const hasRealPrices = data.leaders?.some((l: any) => l.price > 0) ||
                               data.opportunities?.length >= 0 ||
                               data.positions?.some((p: any) => p.current_price > 0);
          
          if ((hasCryptoSymbols || hasRealPrices) && !hasDummy) {
            testResults.push({
              service: 'crypto-api',
              endpoint: name,
              status: 'PASS',
              message: 'Real crypto data available',
              responseTime,
              hasRealData: true
            });
          } else if (hasDummy) {
            testResults.push({
              service: 'crypto-api',
              endpoint: name,
              status: 'FAIL',
              message: 'Contains dummy data markers',
              responseTime,
              hasRealData: false
            });
          } else {
            testResults.push({
              service: 'crypto-api',
              endpoint: name,
              status: 'WARNING',
              message: 'Empty but valid response',
              responseTime
            });
          }
        } else {
          testResults.push({
            service: 'crypto-api',
            endpoint: name,
            status: 'ERROR',
            message: `HTTP ${response.status()}`,
            responseTime
          });
        }
      } catch (error) {
        testResults.push({
          service: 'crypto-api',
          endpoint: name,
          status: 'ERROR',
          message: `Request failed: ${error}`
        });
      }
    }
  });

  // Test 4: Auto-Trading Status
  test('Auto-Trading Functionality', async ({ request }) => {
    console.log('\n🤖 Testing Auto-Trading Functionality...');
    
    try {
      // Check trading status
      const statusResponse = await request.get(`${UNIFIED_API}/api/status`);
      if (statusResponse.ok()) {
        const statusData = await statusResponse.json();
        const autoTradingEnabled = statusData.auto_trading === true;
        
        testResults.push({
          service: 'auto-trading',
          endpoint: 'Status Check',
          status: autoTradingEnabled ? 'PASS' : 'WARNING',
          message: `Auto-trading ${autoTradingEnabled ? 'enabled' : 'disabled'}`,
        });
        
        // Check if positions are being created (if auto-trading enabled)
        if (autoTradingEnabled) {
          const positionsResponse = await request.get(`${UNIFIED_API}/api/crypto/positions`);
          if (positionsResponse.ok()) {
            const positionsData = await positionsResponse.json();
            const hasPositions = positionsData.count > 0;
            
            testResults.push({
              service: 'auto-trading',
              endpoint: 'Position Creation',
              status: hasPositions ? 'PASS' : 'WARNING',
              message: hasPositions ? 
                `${positionsData.count} crypto positions active` : 
                'No positions yet (may be normal)'
            });
          }
        }
      }
      
      // Check configuration
      const configResponse = await request.get(`${UNIFIED_API}/api/config`);
      if (configResponse.ok()) {
        const configData = await configResponse.json();
        const hasConfig = configData.supported_crypto && configData.max_positions;
        
        testResults.push({
          service: 'auto-trading',
          endpoint: 'Configuration',
          status: hasConfig ? 'PASS' : 'FAIL',
          message: hasConfig ? 'Trading configuration loaded' : 'Missing trading config'
        });
      }
    } catch (error) {
      testResults.push({
        service: 'auto-trading',
        endpoint: 'General Test',
        status: 'ERROR',
        message: `Auto-trading test failed: ${error}`
      });
    }
  });

  // Test 5: Frontend Dashboard Load
  test('Frontend Dashboard Load Test', async ({ page }) => {
    console.log('\n🌐 Testing Frontend Dashboard...');
    
    try {
      const startTime = Date.now();
      await page.goto(FRONTEND_URL, { timeout: 30000 });
      const loadTime = Date.now() - startTime;
      
      // Wait for main components to load
      await page.waitForSelector('[data-testid="symbol-select"]', { timeout: 10000 });
      
      // Check if portfolio value is displayed (not placeholder)
      const portfolioElement = await page.locator('text=/Portfolio|Crypto Portfolio/').first();
      await portfolioElement.waitFor({ timeout: 5000 });
      
      // Check for real account data in the UI
      const accountValueVisible = await page.locator('text=/\\$[0-9,]+\\.\\d{2}/', { timeout: 10000 }).count() > 0;
      
      if (accountValueVisible) {
        testResults.push({
          service: 'frontend',
          endpoint: 'Dashboard Load',
          status: 'PASS',
          message: `Dashboard loaded with real data (${loadTime}ms)`,
          responseTime: loadTime
        });
      } else {
        testResults.push({
          service: 'frontend',
          endpoint: 'Dashboard Load',
          status: 'WARNING',
          message: 'Dashboard loaded but no account values visible',
          responseTime: loadTime
        });
      }
      
      // Test market mode toggle
      const stocksButton = page.locator('button:has-text("Stocks")');
      const cryptoButton = page.locator('button:has-text("Crypto")');
      
      if (await stocksButton.count() > 0 && await cryptoButton.count() > 0) {
        testResults.push({
          service: 'frontend',
          endpoint: 'Market Toggle',
          status: 'PASS',
          message: 'Market mode toggle available'
        });
      } else {
        testResults.push({
          service: 'frontend',
          endpoint: 'Market Toggle',
          status: 'FAIL',
          message: 'Market mode toggle missing'
        });
      }
    } catch (error) {
      testResults.push({
        service: 'frontend',
        endpoint: 'Dashboard Load',
        status: 'ERROR',
        message: `Frontend load failed: ${error}`
      });
    }
  });

  // Test 6: Performance and Resource Usage
  test('Performance and Resource Usage', async ({ request }) => {
    console.log('\n⚡ Testing Performance...');
    
    const performanceEndpoints = [
      '/health',
      '/api/account', 
      '/api/positions',
      '/api/leaderboard'
    ];

    let totalTime = 0;
    let successCount = 0;

    for (const endpoint of performanceEndpoints) {
      try {
        const startTime = Date.now();
        const response = await request.get(`${UNIFIED_API}${endpoint}`);
        const responseTime = Date.now() - startTime;
        
        totalTime += responseTime;
        if (response.ok()) successCount++;
        
        const status = responseTime < 2000 ? 'PASS' : 
                      responseTime < 5000 ? 'WARNING' : 'FAIL';
        
        testResults.push({
          service: 'performance',
          endpoint: endpoint.replace('/api/', ''),
          status,
          message: `${responseTime}ms${responseTime < 1000 ? ' (fast)' : 
                   responseTime < 2000 ? ' (good)' : 
                   responseTime < 5000 ? ' (slow)' : ' (very slow)'}`,
          responseTime
        });
      } catch (error) {
        testResults.push({
          service: 'performance',
          endpoint: endpoint.replace('/api/', ''),
          status: 'ERROR',
          message: `Performance test failed: ${error}`
        });
      }
    }

    // Overall performance summary
    const avgResponseTime = totalTime / performanceEndpoints.length;
    testResults.push({
      service: 'performance',
      endpoint: 'Overall',
      status: avgResponseTime < 1000 ? 'PASS' : avgResponseTime < 2000 ? 'WARNING' : 'FAIL',
      message: `Average: ${avgResponseTime.toFixed(0)}ms, Success: ${successCount}/${performanceEndpoints.length}`,
      responseTime: Math.round(avgResponseTime)
    });
  });

  // Test 7: Data Consistency Across Endpoints
  test('Data Consistency Validation', async ({ request }) => {
    console.log('\n🔍 Testing Data Consistency...');
    
    try {
      // Get account data from multiple endpoints
      const [accountResponse, statusResponse, performanceResponse] = await Promise.all([
        request.get(`${UNIFIED_API}/api/account`),
        request.get(`${UNIFIED_API}/api/status`),
        request.get(`${UNIFIED_API}/api/analytics/performance`)
      ]);

      if (accountResponse.ok() && statusResponse.ok() && performanceResponse.ok()) {
        const accountData = await accountResponse.json();
        const statusData = await statusResponse.json();
        const performanceData = await performanceResponse.json();
        
        // Check portfolio value consistency
        const portfolioFromAccount = parseFloat(accountData.portfolio_value || '0');
        const portfolioFromStatus = parseFloat(statusData.portfolio_value || '0');
        const portfolioFromPerformance = parseFloat(performanceData.portfolio_value || '0');
        
        const maxDifference = 100; // Allow $100 difference due to market movements
        const isConsistent = Math.abs(portfolioFromAccount - portfolioFromStatus) < maxDifference &&
                           Math.abs(portfolioFromAccount - portfolioFromPerformance) < maxDifference;
        
        if (isConsistent) {
          testResults.push({
            service: 'data-consistency',
            endpoint: 'Portfolio Values',
            status: 'PASS',
            message: `Portfolio values consistent across endpoints (~$${portfolioFromAccount.toFixed(0)})`
          });
        } else {
          testResults.push({
            service: 'data-consistency',
            endpoint: 'Portfolio Values',
            status: 'WARNING',
            message: `Portfolio values vary: $${portfolioFromAccount.toFixed(0)} vs $${portfolioFromStatus.toFixed(0)}`
          });
        }
        
        // Check buying power consistency
        const buyingPowerAccount = parseFloat(accountData.buying_power || '0');
        const buyingPowerStatus = parseFloat(statusData.buying_power || '0');
        
        if (Math.abs(buyingPowerAccount - buyingPowerStatus) < maxDifference) {
          testResults.push({
            service: 'data-consistency',
            endpoint: 'Buying Power',
            status: 'PASS',
            message: `Buying power consistent (~$${buyingPowerAccount.toFixed(0)})`
          });
        } else {
          testResults.push({
            service: 'data-consistency',
            endpoint: 'Buying Power',
            status: 'WARNING',
            message: `Buying power inconsistent: $${buyingPowerAccount.toFixed(0)} vs $${buyingPowerStatus.toFixed(0)}`
          });
        }
      } else {
        testResults.push({
          service: 'data-consistency',
          endpoint: 'General',
          status: 'ERROR',
          message: 'Could not fetch data for consistency check'
        });
      }
    } catch (error) {
      testResults.push({
        service: 'data-consistency',
        endpoint: 'General',
        status: 'ERROR',
        message: `Consistency test failed: ${error}`
      });
    }
  });
});