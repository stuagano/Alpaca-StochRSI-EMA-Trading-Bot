import { test, expect } from '@playwright/test';

/**
 * Service Dependency Testing Suite
 * Tests how services behave when their dependencies fail
 */

const SERVICES = {
  positions: 'http://localhost:9001',
  trading: 'http://localhost:9002',
  analytics: 'http://localhost:9007'
};

test.describe('Service Dependency Testing', () => {
  
  test('Analytics Service Dependency Chain', async ({ request }) => {
    console.log('\n🔗 Testing Analytics Service Dependencies...');
    
    // Test analytics when all dependencies are available
    const analyticsResponse = await request.get(`${SERVICES.analytics}/analytics/summary`);
    expect(analyticsResponse.ok()).toBe(true);
    
    const analyticsData = await analyticsResponse.json();
    console.log(`📊 Analytics Data Source: ${analyticsData.data_source || 'undefined'}`);
    
    // Verify analytics is getting real data
    if (analyticsData.data_source) {
      expect(['real', 'alpaca_real'].includes(analyticsData.data_source)).toBe(true);
    }
    
    // Check that analytics has meaningful data
    expect(analyticsData).toHaveProperty('total_pnl');
    expect(analyticsData).toHaveProperty('portfolio_value');
    expect(analyticsData).toHaveProperty('positions_count');
    
    console.log(`✅ Analytics: ${analyticsData.positions_count} positions, $${analyticsData.portfolio_value} portfolio value`);
  });

  test('Cross-Service Data Consistency', async ({ request }) => {
    console.log('\n🔄 Testing Cross-Service Data Consistency...');
    
    // Get positions from position service
    const positionsResponse = await request.get(`${SERVICES.positions}/positions`);
    const positionsData = await positionsResponse.json();
    const positionsCount = positionsData.positions?.length || 0;
    
    // Get analytics summary
    const analyticsResponse = await request.get(`${SERVICES.analytics}/analytics/summary`);
    const analyticsData = await analyticsResponse.json();
    const analyticsPositionsCount = analyticsData.positions_count || 0;
    
    // Get account data
    const accountResponse = await request.get(`${SERVICES.trading}/account`);
    const accountData = await accountResponse.json();
    const accountPortfolioValue = accountData.portfolio_value || 0;
    const analyticsPortfolioValue = analyticsData.portfolio_value || 0;
    
    console.log(`🏦 Positions Service: ${positionsCount} positions`);
    console.log(`📊 Analytics Service: ${analyticsPositionsCount} positions`);
    console.log(`💰 Account Value: $${accountPortfolioValue}`);
    console.log(`📈 Analytics Value: $${analyticsPortfolioValue}`);
    
    // These should match since analytics pulls from the same sources
    expect(positionsCount).toBe(analyticsPositionsCount);
    expect(Math.abs(accountPortfolioValue - analyticsPortfolioValue)).toBeLessThan(1.0); // Allow small floating point differences
  });

  test('Service Failure Scenarios', async ({ request }) => {
    console.log('\n💥 Testing Service Failure Scenarios...');
    
    // Test accessing a known bad endpoint
    const badResponse = await request.get(`${SERVICES.positions}/nonexistent-endpoint`);
    expect(badResponse.status()).toBe(404);
    
    // Test analytics with potential service failures
    const analyticsHealthResponse = await request.get(`${SERVICES.analytics}/health`);
    const healthData = await analyticsHealthResponse.json();
    
    console.log(`🔍 Analytics Health Check:`);
    console.log(`  - Positions Service Connected: ${healthData.positions_service_connected}`);
    console.log(`  - Trading Service Connected: ${healthData.trading_service_connected}`);
    console.log(`  - Data Source: ${healthData.data_source}`);
    
    // Analytics should report real data source only when all dependencies are healthy
    if (healthData.positions_service_connected && healthData.trading_service_connected) {
      expect(healthData.data_source).toBe('real');
    } else {
      expect(healthData.data_source).toBe('error');
    }
  });

  test('Data Flow Integrity', async ({ request }) => {
    console.log('\n🌊 Testing Data Flow Integrity...');
    
    // Test that all services have consistent timestamp formats
    const endpoints = [
      `${SERVICES.positions}/positions`,
      `${SERVICES.trading}/orders`, 
      `${SERVICES.analytics}/analytics/summary`
    ];
    
    for (const endpoint of endpoints) {
      const response = await request.get(endpoint);
      if (response.ok()) {
        const data = await response.json();
        
        // Check for timestamp field
        const hasTimestamp = data.timestamp || data.last_updated;
        expect(hasTimestamp).toBeTruthy();
        
        // Check for data source field
        expect(data.data_source).toBeDefined();
        expect(['real', 'alpaca_real', 'error'].includes(data.data_source)).toBe(true);
        
        console.log(`✅ ${endpoint.split('/').pop()}: ${data.data_source} data with timestamp`);
      }
    }
  });

  test('Real Data Validation', async ({ request }) => {
    console.log('\n✨ Validating Real Data Characteristics...');
    
    // Get positions and validate they look like real data
    const positionsResponse = await request.get(`${SERVICES.positions}/positions`);
    if (positionsResponse.ok()) {
      const positionsData = await positionsResponse.json();
      
      if (positionsData.positions && positionsData.positions.length > 0) {
        const firstPosition = positionsData.positions[0];
        
        // Real positions should have these characteristics:
        expect(firstPosition.symbol).toMatch(/^[A-Z]{1,5}(USD)?$/); // Valid ticker
        expect(typeof firstPosition.qty).toBe('number');
        expect(typeof firstPosition.market_value).toBe('number');
        expect(firstPosition.market_value).toBeGreaterThan(0);
        expect(['long', 'short'].includes(firstPosition.side)).toBe(true);
        
        console.log(`📈 Real Position: ${firstPosition.symbol} - ${firstPosition.qty} shares - $${firstPosition.market_value}`);
      } else {
        console.log('📭 No positions found (valid for new account)');
      }
    }
    
    // Get orders and validate structure
    const ordersResponse = await request.get(`${SERVICES.trading}/orders`);
    if (ordersResponse.ok()) {
      const ordersData = await ordersResponse.json();
      expect(Array.isArray(ordersData.orders)).toBe(true);
      expect(typeof ordersData.count).toBe('number');
      expect(ordersData.data_source).toBe('alpaca_real');
      
      console.log(`📋 Orders: ${ordersData.count} orders from ${ordersData.data_source}`);
    }
    
    // Get account and validate it's real
    const accountResponse = await request.get(`${SERVICES.trading}/account`);
    if (accountResponse.ok()) {
      const accountData = await accountResponse.json();
      
      // Real account should have these fields
      expect(accountData.id).toBeDefined();
      expect(typeof accountData.portfolio_value).toBe('number');
      expect(typeof accountData.buying_power).toBe('number');
      expect(accountData.currency).toBe('USD');
      expect(accountData.data_source).toBe('alpaca_real');
      
      console.log(`💼 Real Account: ID ${accountData.id} - $${accountData.portfolio_value} portfolio`);
    }
  });
});