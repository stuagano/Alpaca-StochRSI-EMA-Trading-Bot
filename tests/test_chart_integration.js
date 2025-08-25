#!/usr/bin/env node

/**
 * Test script to verify TradingView chart integration
 */

const axios = require('axios');

const API_BASE_URL = 'http://localhost:9000';
const FRONTEND_URL = 'http://localhost:9100';

async function testChartAPI() {
    console.log('🧪 Testing TradingView Chart Integration\n');
    console.log('=' .repeat(50));
    
    // Test 1: Check if frontend is accessible
    console.log('\n1️⃣ Testing Frontend Service...');
    try {
        const response = await axios.get(`${FRONTEND_URL}/trading`);
        if (response.status === 200) {
            console.log('   ✅ Frontend service is running');
            
            // Check for chart library script tag
            if (response.data.includes('lightweight-charts@4.1.0')) {
                console.log('   ✅ Updated chart library CDN link found');
            } else {
                console.log('   ❌ Chart library CDN link not found or outdated');
            }
        }
    } catch (error) {
        console.log(`   ❌ Frontend service error: ${error.message}`);
    }
    
    // Test 2: Check API Gateway chart endpoint
    console.log('\n2️⃣ Testing API Gateway Chart Endpoint...');
    try {
        const response = await axios.get(`${API_BASE_URL}/api/chart/AAPL?timeframe=5Min&limit=10`);
        
        if (response.data && response.data.candlestick_data) {
            console.log(`   ✅ Chart API returned ${response.data.candlestick_data.length} data points`);
            
            // Validate data structure
            const firstCandle = response.data.candlestick_data[0];
            const requiredFields = ['timestamp', 'open', 'high', 'low', 'close', 'volume'];
            const hasAllFields = requiredFields.every(field => field in firstCandle);
            
            if (hasAllFields) {
                console.log('   ✅ OHLCV data structure is correct');
                console.log(`   📊 Sample data: O:${firstCandle.open} H:${firstCandle.high} L:${firstCandle.low} C:${firstCandle.close} V:${firstCandle.volume}`);
            } else {
                console.log('   ❌ OHLCV data structure is incomplete');
            }
        } else {
            console.log('   ❌ No candlestick data returned');
        }
    } catch (error) {
        console.log(`   ❌ API Gateway error: ${error.message}`);
    }
    
    // Test 3: Check signals endpoint
    console.log('\n3️⃣ Testing Signals Endpoint...');
    try {
        const response = await axios.get(`${API_BASE_URL}/api/signals?symbol=AAPL`);
        
        if (response.data) {
            console.log(`   ✅ Signal: ${response.data.signal}`);
            console.log(`   ✅ Strength: ${(response.data.strength * 100).toFixed(0)}%`);
        }
    } catch (error) {
        console.log(`   ❌ Signals endpoint error: ${error.message}`);
    }
    
    // Test 4: Test different timeframes
    console.log('\n4️⃣ Testing Multiple Timeframes...');
    const timeframes = ['1Min', '5Min', '15Min', '1Hour', '1Day'];
    
    for (const tf of timeframes) {
        try {
            const response = await axios.get(`${API_BASE_URL}/api/chart/AAPL?timeframe=${tf}&limit=5`);
            if (response.data && response.data.candlestick_data) {
                console.log(`   ✅ ${tf}: ${response.data.candlestick_data.length} candles`);
            }
        } catch (error) {
            console.log(`   ❌ ${tf}: Failed`);
        }
    }
    
    console.log('\n' + '='.repeat(50));
    console.log('\n📋 SUMMARY:');
    console.log('If all tests pass, the TradingView charts should work.');
    console.log('If charts still don\'t load, check:');
    console.log('  1. Browser console for JavaScript errors');
    console.log('  2. Network tab for failed resource loads');
    console.log('  3. CORS settings if accessing from different domain');
    console.log('\n🔗 Open http://localhost:9100/trading to test manually');
}

// Run tests
testChartAPI().catch(console.error);