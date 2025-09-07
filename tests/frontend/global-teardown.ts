/**
 * Global teardown for Playwright tests
 * Cleanup after all tests complete
 */

async function globalTeardown() {
  console.log('🧹 Starting global teardown for trading bot tests...');
  
  // Cleanup test artifacts
  console.log('📁 Cleaning up test artifacts...');
  
  // Could add any necessary cleanup here
  // For now, just log completion
  
  console.log('✅ Global teardown completed');
}

export default globalTeardown;