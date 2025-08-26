"use client"

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { 
  TrendingUp, TrendingDown, Activity, DollarSign, BarChart3, 
  Settings, AlertCircle, CheckCircle, XCircle, Clock, 
  RefreshCw, Zap, Shield, Target, TrendingDown as Loss
} from "lucide-react"
import { 
  useAccount, usePositions, useOrders, useSignals, 
  usePerformanceMetrics, useRiskMetrics, useWebSocket,
  useSubmitOrder, useClosePosition, useCancelOrder
} from '@/hooks/useAlpaca'
import { PositionsTable } from '@/components/trading/PositionsTable'
import { OrdersTable } from '@/components/trading/OrdersTable'
import { SignalsPanel } from '@/components/trading/SignalsPanel'
import { TradingChart } from '@/components/trading/TradingChart'
import { OrderForm } from '@/components/trading/OrderForm'
import { RiskPanel } from '@/components/trading/RiskPanel'
import { PerformanceChart } from '@/components/analytics/PerformanceChart'
import { CryptoDayTradingPanel } from '@/components/trading/CryptoDayTradingPanel'
import { CryptoActiveSidebar } from '@/components/trading/CryptoActiveSidebar'
import { formatCurrency, formatPercent } from '@/lib/utils'
import { toast } from 'sonner'

export default function TradingDashboard() {
  const [marketMode, setMarketMode] = useState<'stocks' | 'crypto'>('stocks')
  const [selectedSymbol, setSelectedSymbol] = useState('AAPL')
  const [selectedCrypto, setSelectedCrypto] = useState('BTC/USD')
  const [isAutoTrading, setIsAutoTrading] = useState(false)
  const [realtimeData, setRealtimeData] = useState<any>({})
  const [cryptoMetrics, setCryptoMetrics] = useState<any>({})

  // Data Hooks - Stock Market Data
  const { data: account, isLoading: accountLoading } = useAccount()
  const { data: positions = [], isLoading: positionsLoading } = usePositions()
  const { data: orders = [], isLoading: ordersLoading } = useOrders('open')
  const { data: signals = [], isLoading: signalsLoading } = useSignals()
  const { data: performance, isLoading: perfLoading } = usePerformanceMetrics()
  const { data: riskMetrics, isLoading: riskLoading } = useRiskMetrics()
  
  // Crypto Data Fetching
  useEffect(() => {
    if (marketMode === 'crypto') {
      fetchCryptoMetrics()
      const interval = setInterval(fetchCryptoMetrics, 30000) // Update every 30 seconds
      return () => clearInterval(interval)
    }
  }, [marketMode])
  
  const fetchCryptoMetrics = async () => {
    try {
      const response = await fetch('http://localhost:9012/api/metrics')
      if (response.ok) {
        const data = await response.json()
        setCryptoMetrics(data)
      }
    } catch (error) {
      console.error('Failed to fetch crypto metrics:', error)
    }
  }

  // Mutations
  const submitOrder = useSubmitOrder()
  const closePosition = useClosePosition()
  const cancelOrder = useCancelOrder()

  // WebSocket for real-time data
  const { isConnected } = useWebSocket(
    positions.map(p => p.symbol),
    (data: any) => {
      setRealtimeData((prev: any) => ({
        ...prev,
        [data.symbol]: data
      }))
    }
  )

  // Auto-trading logic
  useEffect(() => {
    if (!isAutoTrading || !signals.length) return

    const interval = setInterval(() => {
      signals.forEach((signal: any) => {
        if (signal.strength > 0.75) {
          const hasPosition = positions.some(p => p.symbol === signal.symbol)
          
          if (signal.signal_type === 'buy' && !hasPosition) {
            submitOrder.mutate({
              symbol: signal.symbol,
              qty: 10, // Default quantity
              side: 'buy',
              type: 'market',
              time_in_force: 'day'
            })
            toast.success(`Auto-trade: BUY ${signal.symbol}`)
          } else if (signal.signal_type === 'sell' && hasPosition) {
            closePosition.mutate(signal.symbol)
            toast.success(`Auto-trade: SELL ${signal.symbol}`)
          }
        }
      })
    }, 10000) // Check every 10 seconds

    return () => clearInterval(interval)
  }, [isAutoTrading, signals, positions])

  // Calculate statistics based on market mode
  const totalPL = marketMode === 'crypto' 
    ? cryptoMetrics.daily_profit || 0
    : positions.reduce((sum, pos) => sum + parseFloat(pos.unrealized_pl || '0'), 0)
    
  const totalValue = marketMode === 'crypto'
    ? cryptoMetrics.portfolio_value || 0
    : parseFloat(account?.portfolio_value || '0')
    
  const buyingPower = marketMode === 'crypto'
    ? cryptoMetrics.available_cash || 0
    : parseFloat(account?.buying_power || '0')
    
  const dayChange = marketMode === 'crypto'
    ? cryptoMetrics.daily_profit || 0
    : positions.reduce((sum, pos) => sum + parseFloat(pos.unrealized_intraday_pl || '0'), 0)
    
  const activePositionsCount = marketMode === 'crypto'
    ? cryptoMetrics.active_positions || 0
    : positions.length
    
  const pendingOrdersCount = marketMode === 'crypto'
    ? cryptoMetrics.pending_orders || 0
    : orders.length
    
  const currentWinRate = marketMode === 'crypto'
    ? cryptoMetrics.win_rate || 0
    : performance?.win_rate || 0
    
  const totalTrades = marketMode === 'crypto'
    ? cryptoMetrics.total_trades || 0
    : performance?.total_trades || 0
    
  const riskScore = marketMode === 'crypto'
    ? cryptoMetrics.risk_score || 0
    : (riskMetrics as any)?.risk_score || 0

  // Market-specific data
  const currentSymbol = marketMode === 'crypto' ? selectedCrypto : selectedSymbol
  const symbolOptions = marketMode === 'crypto' 
    ? ['BTC/USD', 'ETH/USD', 'DOGE/USD', 'SOL/USD', 'ADA/USD', 'XRP/USD', 'DOT/USD', 'MATIC/USD']
    : ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'SPY', 'QQQ']
  
  const headerGradient = marketMode === 'crypto' 
    ? 'bg-gradient-to-r from-orange-500/10 to-yellow-500/10'
    : 'bg-card/50'
  
  const headerIcon = marketMode === 'crypto'
    ? <Zap className="h-8 w-8 text-yellow-500" />
    : <BarChart3 className="h-8 w-8 text-primary" />
    
  const headerTitle = marketMode === 'crypto'
    ? "Crypto Day Trading Bot"
    : "Alpaca Trading Bot"
    
  const headerSubtitle = marketMode === 'crypto'
    ? "High-Frequency Scalping Strategy"
    : "StochRSI + EMA Strategy"

  // Unified interface for both markets
  return (
    <div className="min-h-screen bg-background">
      {/* Universal Header with Market Toggle */}
      <header className={`border-b ${headerGradient} backdrop-blur`}>
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              {headerIcon}
              <div>
                <h1 className="text-2xl font-bold">{headerTitle}</h1>
                <p className="text-sm text-muted-foreground">{headerSubtitle}</p>
              </div>
              <Badge variant={isConnected ? "default" : "destructive"} className="ml-2">
                {isConnected ? "Live" : "Disconnected"}
              </Badge>
              {marketMode === 'crypto' && (
                <Badge variant="default" className="bg-yellow-500">
                  24/7 Trading
                </Badge>
              )}
            </div>
            <div className="flex items-center space-x-4">
              {/* Market Mode Toggle */}
              <div className="flex items-center bg-muted rounded-lg p-1">
                <Button
                  variant={marketMode === 'stocks' ? 'default' : 'ghost'}
                  size="sm"
                  onClick={() => setMarketMode('stocks')}
                  className="px-4"
                >
                  📈 Stocks
                </Button>
                <Button
                  variant={marketMode === 'crypto' ? 'default' : 'ghost'}
                  size="sm"
                  onClick={() => setMarketMode('crypto')}
                  className="px-4"
                >
                  🪙 Crypto
                </Button>
              </div>
              <Button
                variant={isAutoTrading ? "destructive" : "default"}
                onClick={() => setIsAutoTrading(!isAutoTrading)}
              >
                <Zap className="mr-2 h-4 w-4" />
                {marketMode === 'crypto' 
                  ? (isAutoTrading ? "Stop Scalping" : "Start Scalping")
                  : (isAutoTrading ? "Stop Auto-Trading" : "Start Auto-Trading")}
              </Button>
              <Button variant="outline" size="icon">
                <RefreshCw className="h-4 w-4" />
              </Button>
              <Button variant="outline" size="icon">
                <Settings className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-6">
        {/* Market-Specific Stats Cards */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5 mb-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                {marketMode === 'crypto' ? 'Crypto Portfolio' : 'Portfolio Value'}
              </CardTitle>
              <DollarSign className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {(marketMode === 'crypto' ? !cryptoMetrics.portfolio_value : accountLoading) ? "..." : formatCurrency(totalValue)}
              </div>
              <p className="text-xs text-muted-foreground">
                <span className={dayChange >= 0 ? "text-green-500" : "text-red-500"}>
                  {totalValue > 0 ? formatPercent(dayChange / totalValue) : '0%'}
                </span>
                {marketMode === 'crypto' ? ' today (24h)' : ' today'}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                {marketMode === 'crypto' ? 'Daily P&L (24h)' : "Today's P&L"}
              </CardTitle>
              {dayChange >= 0 ? 
                <TrendingUp className="h-4 w-4 text-green-500" /> :
                <Loss className="h-4 w-4 text-red-500" />
              }
            </CardHeader>
            <CardContent>
              <div className={`text-2xl font-bold ${dayChange >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                {formatCurrency(dayChange)}
              </div>
              <p className="text-xs text-muted-foreground">
                {marketMode === 'crypto' ? (
                  `${cryptoMetrics.winning_trades || 0} wins / ${cryptoMetrics.losing_trades || 0} losses`
                ) : (
                  `${positions.filter(p => parseFloat(p.unrealized_pl) > 0).length} winning / ${positions.filter(p => parseFloat(p.unrealized_pl) < 0).length} losing`
                )}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                {marketMode === 'crypto' ? 'Active Crypto' : 'Positions'}
              </CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{activePositionsCount}</div>
              <p className="text-xs text-muted-foreground">
                {pendingOrdersCount} pending orders
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Win Rate</CardTitle>
              <Target className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {(marketMode === 'crypto' ? !cryptoMetrics.win_rate : perfLoading) ? "..." : formatPercent(currentWinRate)}
              </div>
              <p className="text-xs text-muted-foreground">
                {marketMode === 'crypto' ? '24h trading' : `Last ${totalTrades} trades`}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                {marketMode === 'crypto' ? 'Available Cash' : 'Buying Power'}
              </CardTitle>
              <Shield className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {(marketMode === 'crypto' ? !cryptoMetrics.available_cash : accountLoading) ? "..." : formatCurrency(buyingPower)}
              </div>
              <p className="text-xs text-muted-foreground">
                Risk score: {riskScore}/10
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Main Trading Interface */}
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Left Panel - Chart and Trading */}
          <div className="lg:col-span-2 space-y-6">
            {/* Trading Chart */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle>Price Chart - {currentSymbol}</CardTitle>
                  <CardDescription>
                    {marketMode === 'crypto' ? '24/7 Crypto Trading' : 'Real-time price with technical indicators'}
                  </CardDescription>
                </div>
                <select 
                  data-testid="symbol-select"
                  value={currentSymbol}
                  onChange={(e) => {
                    if (marketMode === 'crypto') {
                      setSelectedCrypto(e.target.value)
                    } else {
                      setSelectedSymbol(e.target.value)
                    }
                  }}
                  className="px-3 py-1 border rounded-md bg-background"
                >
                  {symbolOptions.map(symbol => (
                    <option key={symbol} value={symbol}>{symbol}</option>
                  ))}
                </select>
              </CardHeader>
              <CardContent>
                <TradingChart 
                  symbol={currentSymbol} 
                  realtimeData={realtimeData[currentSymbol]}
                  marketType={marketMode}
                />
              </CardContent>
            </Card>

            {/* Trading Tabs */}
            <Tabs defaultValue="positions" className="space-y-4">
              <TabsList className="grid w-full grid-cols-4">
                <TabsTrigger value="positions" data-testid="positions-tab">
                  {marketMode === 'crypto' ? 'Crypto Positions' : 'Positions'}
                </TabsTrigger>
                <TabsTrigger value="orders" data-testid="orders-tab">Orders</TabsTrigger>
                <TabsTrigger value="signals" data-testid="signals-tab">
                  {marketMode === 'crypto' ? 'Opportunities' : 'Signals'}
                </TabsTrigger>
                <TabsTrigger value="analytics" data-testid="analytics-tab">Analytics</TabsTrigger>
              </TabsList>

              <TabsContent value="positions" className="space-y-4">
                {marketMode === 'crypto' ? (
                  // Show full crypto trading interface for crypto mode
                  <CryptoDayTradingPanel />
                ) : (
                  // Show stock positions for stock mode
                  <PositionsTable 
                    positions={positions}
                    onClose={(symbol) => closePosition.mutate(symbol)}
                    onSelect={setSelectedSymbol}
                    realtimeData={realtimeData}
                  />
                )}
              </TabsContent>

              <TabsContent value="orders" className="space-y-4">
                {marketMode === 'crypto' ? (
                  // Show crypto order history for crypto mode
                  <div className="space-y-4">
                    <Card>
                      <CardHeader>
                        <CardTitle>Crypto Order History</CardTitle>
                        <CardDescription>Recent crypto trades from Alpaca</CardDescription>
                      </CardHeader>
                      <CardContent>
                        <iframe 
                          src="http://localhost:9012/api/history" 
                          style={{ display: 'none' }}
                          onLoad={(e) => {
                            // We'll use the crypto history component instead
                          }}
                        />
                        <p className="text-muted-foreground">Switch to the History tab in crypto positions for detailed order timeline</p>
                      </CardContent>
                    </Card>
                  </div>
                ) : (
                  // Show stock orders for stock mode
                  <OrdersTable 
                    orders={orders}
                    onCancel={(orderId) => cancelOrder.mutate(orderId)}
                  />
                )}
              </TabsContent>

              <TabsContent value="signals" className="space-y-4">
                {marketMode === 'crypto' ? (
                  // Show crypto opportunities for crypto mode
                  <div className="space-y-4">
                    <Card>
                      <CardHeader>
                        <CardTitle>Crypto Trading Opportunities</CardTitle>
                        <CardDescription>High-volatility crypto signals detected</CardDescription>
                      </CardHeader>
                      <CardContent>
                        <div className="text-center py-8">
                          <Zap className="h-12 w-12 text-yellow-500 mx-auto mb-4" />
                          <p className="text-muted-foreground">Switch to the Opportunities tab in crypto positions for live trading signals</p>
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                ) : (
                  // Show stock signals for stock mode
                  <SignalsPanel 
                    signals={signals}
                    onExecute={(signal) => {
                      submitOrder.mutate({
                        symbol: signal.symbol,
                        qty: 10,
                        side: signal.signal_type === 'buy' ? 'buy' : 'sell',
                        type: 'market',
                        time_in_force: 'day'
                      })
                    }}
                  />
                )}
              </TabsContent>

              <TabsContent value="analytics" className="space-y-4">
                {marketMode === 'crypto' ? (
                  // Show crypto analytics for crypto mode
                  <div className="space-y-4">
                    <Card>
                      <CardHeader>
                        <CardTitle>Crypto Trading Analytics</CardTitle>
                        <CardDescription>Performance metrics and risk analysis</CardDescription>
                      </CardHeader>
                      <CardContent>
                        <div className="text-center py-8">
                          <BarChart3 className="h-12 w-12 text-primary mx-auto mb-4" />
                          <p className="text-muted-foreground">Switch to the Metrics tab in crypto positions for detailed performance analytics</p>
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                ) : (
                  // Show stock analytics for stock mode  
                  <PerformanceChart />
                )}
              </TabsContent>
            </Tabs>
          </div>

          {/* Right Panel - Order Entry and Risk */}
          <div className="space-y-6">
            {/* Order Form - Only for Stock Mode */}
            {marketMode === 'stocks' && (
              <Card>
                <CardHeader>
                  <CardTitle>Place Order</CardTitle>
                  <CardDescription>Quick order entry</CardDescription>
                </CardHeader>
                <CardContent>
                  <OrderForm 
                    defaultSymbol={selectedSymbol}
                    buyingPower={buyingPower}
                    onSubmit={(order) => submitOrder.mutate(order)}
                  />
                </CardContent>
              </Card>
            )}
            
            {/* Crypto Automation Status */}
            {marketMode === 'crypto' && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <Zap className="h-4 w-4 text-yellow-500" />
                    <span>Automated Trading</span>
                  </CardTitle>
                  <CardDescription>Fully automated crypto scalping bot</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between p-3 bg-green-500/10 rounded-lg">
                    <div className="flex items-center space-x-2">
                      <CheckCircle className="h-4 w-4 text-green-500" />
                      <span className="text-sm font-medium text-green-700">Bot Active</span>
                    </div>
                    <Badge variant="default" className="bg-green-500">
                      24/7 Trading
                    </Badge>
                  </div>
                  <div className="text-xs text-muted-foreground space-y-1">
                    <p>• High-frequency scalping strategy</p>
                    <p>• Automatic position management</p>
                    <p>• Risk controls active</p>
                    <p>• No manual intervention required</p>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Risk Management - Only for Stock Mode */}
            {marketMode === 'stocks' && (
              <RiskPanel 
                riskMetrics={riskMetrics}
                positions={positions}
              />
            )}

            {/* Active Signals Summary */}
            <CryptoActiveSidebar marketMode={marketMode} signals={signals} onExecute={submitOrder} />
          </div>
        </div>
      </main>
    </div>
  )
}