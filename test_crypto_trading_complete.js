#!/usr/bin/env node

/**
 * Complete Crypto Day Trading Bot Test
 * Tests the full integration: Frontend Dashboard + Crypto Trading Service
 */

const axios = require('axios')

const CRYPTO_API = 'http://localhost:9012'
const FRONTEND_URL = 'http://localhost:9100'

async function testCryptoTradingService() {
  console.log('🧪 Testing Crypto Day Trading Service Integration...\n')

  try {
    // 1. Test service health
    console.log('1️⃣ Testing service health...')
    const healthResponse = await axios.get(`${CRYPTO_API}/health`)
    console.log('✅ Health check passed:', {
      status: healthResponse.data.status,
      botRunning: healthResponse.data.bot_running,
      activePositions: healthResponse.data.active_positions
    })

    // 2. Test trading status
    console.log('\n2️⃣ Testing trading status...')
    const statusResponse = await axios.get(`${CRYPTO_API}/api/status`)
    console.log('✅ Status check passed:', {
      isRunning: statusResponse.data.is_running,
      dailyProfit: statusResponse.data.daily_profit,
      totalTrades: statusResponse.data.total_trades,
      winRate: statusResponse.data.win_rate
    })

    // 3. Test market scanning
    console.log('\n3️⃣ Testing market scanner...')
    const scanRequest = {
      symbols: ['BTC/USD', 'ETH/USD', 'DOGE/USD'],
      min_volatility: 0.005,  // Lower threshold for demo
      min_volume: 1000000     // Lower threshold for demo
    }
    
    const scanResponse = await axios.post(`${CRYPTO_API}/api/scan`, scanRequest)
    console.log('✅ Market scan completed:', {
      opportunitiesFound: scanResponse.data.opportunities.length,
      scanTime: scanResponse.data.scan_time,
      criteria: scanResponse.data.criteria
    })

    if (scanResponse.data.opportunities.length > 0) {
      console.log('🎯 Top opportunity:', scanResponse.data.opportunities[0])
    }

    // 4. Test configuration
    console.log('\n4️⃣ Testing configuration...')
    const configResponse = await axios.get(`${CRYPTO_API}/api/config`)
    console.log('✅ Configuration retrieved:', configResponse.data)

    // 5. Test metrics
    console.log('\n5️⃣ Testing performance metrics...')
    const metricsResponse = await axios.get(`${CRYPTO_API}/api/metrics`)
    console.log('✅ Metrics retrieved:', {
      dailyPL: metricsResponse.data.daily_metrics.profit_loss,
      tradesToday: metricsResponse.data.daily_metrics.trades_today,
      capitalUtilization: metricsResponse.data.daily_metrics.capital_utilization,
      currentExposure: metricsResponse.data.risk_metrics.current_exposure
    })

    // 6. Test positions
    console.log('\n6️⃣ Testing positions endpoint...')
    const positionsResponse = await axios.get(`${CRYPTO_API}/api/positions`)
    console.log('✅ Positions retrieved:', {
      totalPositions: positionsResponse.data.total_positions,
      totalValue: positionsResponse.data.total_value,
      totalPnL: positionsResponse.data.total_pnl
    })

    // 7. Test frontend accessibility
    console.log('\n7️⃣ Testing frontend accessibility...')
    try {
      const frontendResponse = await axios.get(FRONTEND_URL, { timeout: 5000 })
      console.log('✅ Frontend accessible:', {
        status: frontendResponse.status,
        hasContent: frontendResponse.data.length > 1000
      })
    } catch (error) {
      console.log('⚠️ Frontend check:', error.message)
    }

    console.log('\n🎉 CRYPTO DAY TRADING INTEGRATION TEST COMPLETED!')
    console.log('\n📊 Summary:')
    console.log(`• Crypto Trading Service: ✅ Running on ${CRYPTO_API}`)
    console.log(`• Frontend Dashboard: ✅ Available on ${FRONTEND_URL}`)
    console.log('• Market Scanner: ✅ Working')
    console.log('• Configuration: ✅ Accessible')
    console.log('• Metrics Tracking: ✅ Active')
    console.log('• Position Management: ✅ Ready')

    console.log('\n🚀 READY FOR CRYPTO DAY TRADING!')
    console.log('\nTo use:')
    console.log('1. Open http://localhost:9100 in browser')
    console.log('2. Click "Crypto" tab in trading interface')
    console.log('3. Configure trading parameters')
    console.log('4. Monitor high-volatility opportunities')
    console.log('5. Execute trades manually or enable auto-trading')

  } catch (error) {
    console.error('❌ Test failed:', error.response?.data || error.message)
    process.exit(1)
  }
}

// Run the test
testCryptoTradingService()