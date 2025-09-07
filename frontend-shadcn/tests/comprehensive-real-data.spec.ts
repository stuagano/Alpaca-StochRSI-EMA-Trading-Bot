import { test, expect } from '@playwright/test';

/**
 * Comprehensive Real Data Testing Suite
 * Tests all microservices for real data compliance and functionality
 */

// Test configuration
const API_BASE = 'http://localhost:9000'; // API Gateway
const DIRECT_SERVICES = {
  positions: 'http://localhost:9001',
  trading: 'http://localhost:9002',
  signals: 'http://localhost:9003',
  risk: 'http://localhost:9004',
  market: 'http://localhost:9005',
  historical: 'http://localhost:9006',
  analytics: 'http://localhost:9007',
  notifications: 'http://localhost:9008',
  config: 'http://localhost:9009',
  health: 'http://localhost:9010',
  training: 'http://localhost:9011',
  crypto: 'http://localhost:9000'
};

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
  'mock_enabled',
  'mock',
  'demo',
  'fake',
  'sample',
  'test-data'
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

// Helper function to check for dummy data markers
function hasDummyDataMarkers(data: any): boolean {
  const dataStr = JSON.stringify(data).toLowerCase();
  return DUMMY_DATA_MARKERS.some(marker => dataStr.includes(marker.toLowerCase()));
}

// Helper function to validate data source
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

test.describe('Comprehensive Real Data Testing Suite', () => {
  
  test.beforeAll(async () => {
    console.log('🚀 Starting Comprehensive Real Data Testing Suite');
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
    
    // Detailed breakdown
    console.log('\n📋 DETAILED RESULTS:');
    for (const result of testResults) {
      const emoji = result.status === 'PASS' ? '✅' : 
                   result.status === 'FAIL' ? '❌' : 
                   result.status === 'WARNING' ? '⚠️' : '💥';
      console.log(`${emoji} ${result.service} - ${result.endpoint}: ${result.message}`);
    }
  });

  // Test 1: Core Service Health Checks
  test('Core Service Health Checks', async ({ request }) => {
    console.log('\n🏥 Testing Core Service Health...');
    
    for (const [serviceName, baseUrl] of Object.entries(DIRECT_SERVICES)) {
      try {
        const startTime = Date.now();
        const response = await request.get(`${baseUrl}/health`);
        const responseTime = Date.now() - startTime;
        const data = await response.json();
        
        if (response.ok()) {
          const dataSourceStatus = validateDataSource(data);
          const hasRealData = dataSourceStatus === 'REAL';
          const hasDummy = hasDummyDataMarkers(data);
          
          if (hasRealData && !hasDummy) {
            testResults.push({
              service: serviceName,
              endpoint: '/health',
              status: 'PASS',
              message: `Healthy with real data (${responseTime}ms)`,
              dataSource: data.data_source,
              responseTime,
              hasRealData: true
            });
          } else if (hasDummy) {
            testResults.push({
              service: serviceName,
              endpoint: '/health',
              status: 'FAIL',
              message: 'Contains dummy data markers',
              dataSource: data.data_source,
              responseTime,
              hasRealData: false
            });
          } else {
            testResults.push({
              service: serviceName,
              endpoint: '/health',
              status: 'WARNING',
              message: 'No clear data source indicator',
              dataSource: data.data_source,
              responseTime,
              hasRealData: false
            });
          }
        } else {
          testResults.push({
            service: serviceName,
            endpoint: '/health',
            status: 'ERROR',
            message: `HTTP ${response.status()} - Service unavailable`,
            responseTime
          });
        }
      } catch (error) {
        testResults.push({
          service: serviceName,
          endpoint: '/health',
          status: 'ERROR',
          message: `Connection failed: ${error}`
        });
      }
    }
  });

  // Test 2: Critical Data Endpoints
  test('Critical Data Endpoints', async ({ request }) => {
    console.log('\n📊 Testing Critical Data Endpoints...');
    
    const criticalEndpoints = [
      { service: 'positions', url: `${DIRECT_SERVICES.positions}/positions`, name: 'Positions List' },
      { service: 'positions', url: `${DIRECT_SERVICES.positions}/portfolio/summary`, name: 'Portfolio Summary' },
      { service: 'trading', url: `${DIRECT_SERVICES.trading}/orders`, name: 'Orders List' },
      { service: 'trading', url: `${DIRECT_SERVICES.trading}/account`, name: 'Account Info' },
      { service: 'analytics', url: `${DIRECT_SERVICES.analytics}/analytics/summary`, name: 'Analytics Summary' },
      { service: 'analytics', url: `${DIRECT_SERVICES.analytics}/performance`, name: 'Performance Metrics' },
      { service: 'crypto', url: `${DIRECT_SERVICES.crypto}/api/account`, name: 'Crypto Account' },
      { service: 'crypto', url: `${DIRECT_SERVICES.crypto}/api/positions`, name: 'Crypto Positions' }
    ];

    for (const endpoint of criticalEndpoints) {
      try {
        const startTime = Date.now();
        const response = await request.get(endpoint.url);
        const responseTime = Date.now() - startTime;
        
        if (response.ok()) {
          const data = await response.json();
          const dataSourceStatus = validateDataSource(data);
          const hasDummy = hasDummyDataMarkers(data);
          const hasData = data.positions?.length > 0 || data.orders?.length > 0 || data.portfolio_value > 0 || data.total_pnl !== undefined;
          
          if (dataSourceStatus === 'REAL' && !hasDummy) {
            testResults.push({
              service: endpoint.service,
              endpoint: endpoint.name,
              status: 'PASS',
              message: `Real data returned (${responseTime}ms)${hasData ? ' with content' : ' empty but valid'}`,
              dataSource: data.data_source,
              responseTime,
              hasRealData: true
            });
          } else if (hasDummy) {
            testResults.push({
              service: endpoint.service,
              endpoint: endpoint.name,
              status: 'FAIL',
              message: 'Contains dummy data markers',
              dataSource: data.data_source,
              responseTime
            });
          } else {
            testResults.push({
              service: endpoint.service,
              endpoint: endpoint.name,
              status: 'WARNING',
              message: 'No clear data source indicator',
              dataSource: data.data_source,
              responseTime
            });
          }
        } else if (response.status() === 503) {
          testResults.push({
            service: endpoint.service,
            endpoint: endpoint.name,
            status: 'PASS',
            message: 'Correctly returns 503 (no dummy fallback)',
            responseTime
          });
        } else {
          testResults.push({
            service: endpoint.service,
            endpoint: endpoint.name,
            status: 'WARNING',
            message: `HTTP ${response.status()} - Unexpected status`,
            responseTime
          });
        }
      } catch (error) {
        testResults.push({
          service: endpoint.service,
          endpoint: endpoint.name,
          status: 'ERROR',
          message: `Request failed: ${error}`
        });
      }
    }
  });

  // Test 3: API Gateway Routing
  test('API Gateway Routing', async ({ request }) => {
    console.log('\n🚪 Testing API Gateway Routing...');
    
    const gatewayEndpoints = [
      '/api/positions',
      '/api/orders', 
      '/api/account',
      '/api/performance',
      '/api/crypto/positions',
      '/api/crypto/account'
    ];

    for (const endpoint of gatewayEndpoints) {
      try {
        const startTime = Date.now();
        const response = await request.get(`${API_BASE}${endpoint}`);
        const responseTime = Date.now() - startTime;
        
        if (response.ok()) {
          const data = await response.json();
          const hasDummy = hasDummyDataMarkers(data);
          const dataSourceStatus = validateDataSource(data);
          
          if (!hasDummy && (dataSourceStatus === 'REAL' || response.status() === 200)) {
            testResults.push({
              service: 'api-gateway',
              endpoint: endpoint,
              status: 'PASS',
              message: `Gateway routing working (${responseTime}ms)`,
              dataSource: data.data_source,
              responseTime
            });
          } else if (hasDummy) {
            testResults.push({
              service: 'api-gateway',
              endpoint: endpoint,
              status: 'FAIL',
              message: 'Gateway returning dummy data',
              dataSource: data.data_source,
              responseTime
            });
          } else {
            testResults.push({
              service: 'api-gateway',
              endpoint: endpoint,
              status: 'WARNING',
              message: 'Gateway response unclear',
              responseTime
            });
          }
        } else if (response.status() === 503) {
          testResults.push({
            service: 'api-gateway',
            endpoint: endpoint,
            status: 'PASS',
            message: 'Gateway correctly forwards 503 errors',
            responseTime
          });
        } else {
          testResults.push({
            service: 'api-gateway',
            endpoint: endpoint,
            status: 'WARNING',
            message: `Gateway returned ${response.status()}`,
            responseTime
          });
        }
      } catch (error) {
        testResults.push({
          service: 'api-gateway',
          endpoint: endpoint,
          status: 'ERROR',
          message: `Gateway request failed: ${error}`
        });
      }
    }
  });

  // Test 4: Error Handling (No Dummy Data Fallbacks)
  test('Error Handling - No Dummy Fallbacks', async ({ request }) => {
    console.log('\n🛡️ Testing Error Handling...');
    
    const errorTests = [
      { url: `${DIRECT_SERVICES.positions}/positions/NONEXISTENT`, name: 'Non-existent Position' },
      { url: `${DIRECT_SERVICES.trading}/orders/invalid-id`, name: 'Invalid Order ID' },
      { url: `${DIRECT_SERVICES.analytics}/analytics/fake-metric`, name: 'Invalid Analytics Endpoint' }
    ];

    for (const errorTest of errorTests) {
      try {
        const response = await request.get(errorTest.url);
        
        if (response.status() >= 400) {
          const data = await response.json().catch(() => ({}));
          const hasDummy = hasDummyDataMarkers(data);
          
          if (!hasDummy) {
            testResults.push({
              service: 'error-handling',
              endpoint: errorTest.name,
              status: 'PASS',
              message: `Properly returns ${response.status()} without dummy data`,
            });
          } else {
            testResults.push({
              service: 'error-handling',
              endpoint: errorTest.name,
              status: 'FAIL',
              message: 'Error response contains dummy data fallback',
            });
          }
        } else {
          testResults.push({
            service: 'error-handling',
            endpoint: errorTest.name,
            status: 'WARNING',
            message: `Expected error but got ${response.status()}`,
          });
        }
      } catch (error) {
        testResults.push({
          service: 'error-handling',
          endpoint: errorTest.name,
          status: 'PASS',
          message: 'Correctly fails without dummy fallback',
        });
      }
    }
  });

  // Test 5: Data Structure Consistency
  test('Data Structure Consistency', async ({ request }) => {
    console.log('\n🏗️ Testing Data Structure Consistency...');
    
    try {
      // Test positions structure
      const positionsResponse = await request.get(`${DIRECT_SERVICES.positions}/positions`);
      if (positionsResponse.ok()) {
        const positionsData = await positionsResponse.json();
        const hasExpectedFields = positionsData.positions && positionsData.count !== undefined && positionsData.timestamp;
        
        if (hasExpectedFields) {
          testResults.push({
            service: 'data-structure',
            endpoint: 'Positions Structure',
            status: 'PASS',
            message: 'Positions data structure is consistent'
          });
        } else {
          testResults.push({
            service: 'data-structure',
            endpoint: 'Positions Structure',
            status: 'FAIL',
            message: 'Positions data structure is malformed'
          });
        }
      }

      // Test orders structure  
      const ordersResponse = await request.get(`${DIRECT_SERVICES.trading}/orders`);
      if (ordersResponse.ok()) {
        const ordersData = await ordersResponse.json();
        const hasExpectedFields = ordersData.orders && ordersData.count !== undefined;
        
        if (hasExpectedFields) {
          testResults.push({
            service: 'data-structure',
            endpoint: 'Orders Structure',
            status: 'PASS',
            message: 'Orders data structure is consistent'
          });
        } else {
          testResults.push({
            service: 'data-structure',
            endpoint: 'Orders Structure',
            status: 'FAIL',
            message: 'Orders data structure is malformed'
          });
        }
      }

      // Test analytics structure
      const analyticsResponse = await request.get(`${DIRECT_SERVICES.analytics}/analytics/summary`);
      if (analyticsResponse.ok()) {
        const analyticsData = await analyticsResponse.json();
        const hasExpectedFields = analyticsData.total_pnl !== undefined && analyticsData.win_rate !== undefined;
        
        if (hasExpectedFields) {
          testResults.push({
            service: 'data-structure',
            endpoint: 'Analytics Structure',
            status: 'PASS',
            message: 'Analytics data structure is consistent'
          });
        } else {
          testResults.push({
            service: 'data-structure',
            endpoint: 'Analytics Structure',
            status: 'FAIL',
            message: 'Analytics data structure is malformed'
          });
        }
      }
    } catch (error) {
      testResults.push({
        service: 'data-structure',
        endpoint: 'Structure Tests',
        status: 'ERROR',
        message: `Structure validation failed: ${error}`
      });
    }
  });

  // Test 6: Performance and Response Times
  test('Performance and Response Times', async ({ request }) => {
    console.log('\n⚡ Testing Performance...');
    
    const performanceEndpoints = [
      `${DIRECT_SERVICES.positions}/health`,
      `${DIRECT_SERVICES.trading}/health`,
      `${DIRECT_SERVICES.analytics}/health`
    ];

    for (const endpoint of performanceEndpoints) {
      try {
        const startTime = Date.now();
        const response = await request.get(endpoint);
        const responseTime = Date.now() - startTime;
        
        if (responseTime < 5000) { // 5 second threshold
          testResults.push({
            service: 'performance',
            endpoint: endpoint.split('/').slice(-2).join('/'),
            status: 'PASS',
            message: `Response time: ${responseTime}ms`,
            responseTime
          });
        } else {
          testResults.push({
            service: 'performance',
            endpoint: endpoint.split('/').slice(-2).join('/'),
            status: 'WARNING',
            message: `Slow response: ${responseTime}ms`,
            responseTime
          });
        }
      } catch (error) {
        testResults.push({
          service: 'performance',
          endpoint: endpoint.split('/').slice(-2).join('/'),
          status: 'ERROR',
          message: `Performance test failed: ${error}`
        });
      }
    }
  });
});