"use client"

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { 
  TrendingUp, TrendingDown, Activity, DollarSign, BarChart3, 
  Settings, AlertCircle, CheckCircle, XCircle, Clock, 
  RefreshCw, Zap, Shield, Target, TrendingDown as Loss,
  TrendingUp as Stock, ArrowRight
} from "lucide-react"
import { 
  useAccount, usePositions, useOrders, useSignals, 
  usePerformanceMetrics, useRiskMetrics, useWebSocket,
  useSubmitOrder, useClosePosition, useCancelOrder
} from '@/hooks/useAlpaca'
import { TradingChart } from '@/components/trading/TradingChart'
import { ScalpingEngine } from '@/components/trading/ScalpingEngine'
import { VolatilityTickerSelector } from '@/components/trading/VolatilityTickerSelector'
import { RiskPanel } from '@/components/trading/RiskPanel'
import { TradeActivityLog } from '@/components/trading/TradeActivityLog'
import { formatCurrency, formatPercent } from '@/lib/utils'
import { toast } from 'sonner'
import Link from 'next/link'

export default function StockTradingPage() {
  const [selectedSymbol, setSelectedSymbol] = useState('AAPL')
  const [isStockBotActive, setIsStockBotActive] = useState(false)
  const [realtimeData, setRealtimeData] = useState<any>({})

  // Stock-specific data hooks - always use 'stocks' mode
  const { data: account, isLoading: accountLoading } = useAccount('stocks')
  const { data: positions = [], isLoading: positionsLoading } = usePositions('stocks')
  const { data: orders = [], isLoading: ordersLoading } = useOrders('open', 'stocks')
  const { data: signals = [], isLoading: signalsLoading } = useSignals(undefined, 'stocks')
  const { data: performance } = usePerformanceMetrics('stocks')
  const { data: riskMetrics } = useRiskMetrics('stocks')
  
  // Mutations for stocks
  const submitOrder = useSubmitOrder('stocks')
  const closePosition = useClosePosition('stocks')
  const cancelOrder = useCancelOrder('stocks')

  // WebSocket for real-time stock data
  const { isConnected } = useWebSocket(
    positions.map((p: any) => p.symbol),
    (data: any) => {
      setRealtimeData((prev: any) => ({
        ...prev,
        [data.symbol]: data
      }))
    },
    'stocks'
  )

  // Stock Bot Logic - Market Hours Only
  useEffect(() => {
    if (!isStockBotActive || !signals.length) return

    const interval = setInterval(() => {
      // Check if market is open
      const now = new Date()
      const hour = now.getHours()
      const isMarketOpen = hour >= 9 && hour < 16
      
      if (!isMarketOpen) {
        console.log('Stock market closed - bot paused')
        return
      }

      const stockSignals = signals.filter((s: any) => 
        !s.symbol.includes('USD') && !s.symbol.includes('BTC') && !s.symbol.includes('ETH')
      )

      stockSignals.forEach((signal: any) => {
        if (signal.strength > 0.75) {
          const hasPosition = positions.some((p: any) => p.symbol === signal.symbol)
          
          if (signal.signal_type === 'buy' && !hasPosition) {
            submitOrder.mutate({
              symbol: signal.symbol,
              qty: 10, // Share quantities for stocks
              side: 'buy',
              type: 'market',
              time_in_force: 'day'
            })
            toast.success(`📈 Stock Bot: BUY ${signal.symbol}`)
          } else if (signal.signal_type === 'sell' && hasPosition) {
            closePosition.mutate(signal.symbol)
            toast.success(`📈 Stock Bot: SELL ${signal.symbol}`)
          }
        }
      })
    }, 10000) // Check every 10 seconds for stocks

    return () => clearInterval(interval)
  }, [isStockBotActive, signals, positions])

  // Calculate stock-specific stats
  const totalPL = positions.reduce((sum: number, pos: any) => sum + parseFloat(pos.unrealized_pl || '0'), 0)
  const totalValue = parseFloat(account?.portfolio_value || '0')
  const buyingPower = parseFloat(account?.buying_power || '0')
  const dayChange = positions.reduce((sum: number, pos: any) => sum + parseFloat(pos.unrealized_intraday_pl || '0'), 0)
  const winRate = performance?.win_rate || 0

  return (
    <div className="min-h-screen bg-background">
      {/* Stock Header */}
      <header className="border-b bg-card/50 backdrop-blur">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <BarChart3 className="h-8 w-8 text-primary" />
              <div>
                <h1 className="text-2xl font-bold">Stock Trading Bot</h1>
                <p className="text-sm text-muted-foreground">Market Hours Trading • 10-30 trades/hour</p>
              </div>
              <Badge variant={isConnected ? "default" : "destructive"}>
                {isConnected ? "Live" : "Disconnected"}
              </Badge>
              <Link href="/crypto">
                <Button variant="outline" size="sm">
                  Switch to Crypto
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
            </div>
            <div className="flex items-center space-x-4">
              <Badge 
                variant={isStockBotActive ? "default" : "outline"}
                className={isStockBotActive ? "bg-green-500" : ""}
              >
                <Stock className="mr-1 h-3 w-3" />
                Stock Bot: {isStockBotActive ? "ON" : "OFF"}
              </Badge>
              <Button
                variant={isStockBotActive ? "destructive" : "default"}
                onClick={() => setIsStockBotActive(!isStockBotActive)}
                className={isStockBotActive ? "animate-pulse" : ""}
              >
                <Zap className="mr-2 h-4 w-4" />
                {isStockBotActive ? "⚡ STOCK BOT ACTIVE" : "Start Stock Bot"}
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
        {/* Stock Stats Cards */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5 mb-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Portfolio Value</CardTitle>
              <DollarSign className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {formatCurrency(totalValue)}
              </div>
              <p className="text-xs text-muted-foreground">
                <span className={dayChange >= 0 ? "text-green-500" : "text-red-500"}>
                  {formatPercent(totalValue > 0 ? dayChange / totalValue : 0)}
                </span> today
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Today's P&L</CardTitle>
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
                {positions.filter((p: any) => parseFloat(p.unrealized_pl) > 0).length} winning / 
                {positions.filter((p: any) => parseFloat(p.unrealized_pl) < 0).length} losing
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Positions</CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{positions.length}</div>
              <p className="text-xs text-muted-foreground">
                {orders.length} pending orders
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Win Rate</CardTitle>
              <Target className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatPercent(winRate)}</div>
              <p className="text-xs text-muted-foreground">Last {performance?.total_trades || 0} trades</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Buying Power</CardTitle>
              <Shield className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatCurrency(buyingPower)}</div>
              <p className="text-xs text-muted-foreground">
                Risk score: {(riskMetrics as any)?.risk_score || 0}/10
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Trading Interface */}
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Left Panel - Chart */}
          <div className="lg:col-span-2 space-y-6">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle>Stock Chart - {selectedSymbol}</CardTitle>
                  <CardDescription>Real-time price with technical indicators</CardDescription>
                </div>
              </CardHeader>
              <CardContent>
                <TradingChart 
                  symbol={selectedSymbol} 
                  realtimeData={realtimeData[selectedSymbol]}
                  marketType="stocks"
                  onSymbolChange={setSelectedSymbol}
                  height={400}
                />
              </CardContent>
            </Card>

            {/* Scalping Engine */}
            <ScalpingEngine
              marketType="stocks"
              selectedSymbol={selectedSymbol}
              isActive={isStockBotActive}
              onToggleActive={() => setIsStockBotActive(!isStockBotActive)}
              onExecuteSignal={(signal) => {
                const order = {
                  symbol: signal.symbol,
                  qty: 10,
                  side: signal.direction.toLowerCase() as 'buy' | 'sell',
                  type: 'market' as const,
                  time_in_force: 'day' as const
                }
                submitOrder.mutate(order)
                toast.success(`📈 Stock: ${signal.direction} ${signal.symbol}`)
              }}
            />

            {/* Live Trade Activity Log */}
            <TradeActivityLog marketType="stocks" />
          </div>

          {/* Right Panel - Volatility Selector & Positions */}
          <div className="space-y-6">
            {/* Volatility Ticker Selector */}
            <VolatilityTickerSelector
              marketType="stocks"
              currentSymbol={selectedSymbol}
              onSymbolChange={setSelectedSymbol}
              onAutoSelectMostVolatile={setSelectedSymbol}
            />

            {/* Risk Management */}
            <RiskPanel 
              riskMetrics={riskMetrics}
              positions={positions}
            />

            {/* Positions */}
            <Card>
              <CardHeader>
                <CardTitle>Stock Positions</CardTitle>
                <CardDescription>Current holdings</CardDescription>
              </CardHeader>
              <CardContent>
                {positionsLoading ? (
                  <div className="text-center py-4">Loading positions...</div>
                ) : positions.length === 0 ? (
                  <div className="text-center py-4 text-muted-foreground">No stock positions</div>
                ) : (
                  <div className="space-y-2">
                    {positions.map((position: any) => (
                      <div key={position.symbol} className="flex items-center justify-between p-2 border rounded">
                        <div>
                          <div className="font-medium">{position.symbol}</div>
                          <div className="text-sm text-muted-foreground">
                            {position.qty} shares @ {formatCurrency(parseFloat(position.avg_entry_price))}
                          </div>
                        </div>
                        <div className="text-right">
                          <div className={parseFloat(position.unrealized_pl) >= 0 ? 'text-green-500' : 'text-red-500'}>
                            {formatCurrency(parseFloat(position.unrealized_pl))}
                          </div>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => closePosition.mutate(position.symbol)}
                          >
                            Sell
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </main>
    </div>
  )
}