"use client"

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { 
  TrendingUp, TrendingDown, Activity, DollarSign, BarChart3, 
  Settings, AlertCircle, CheckCircle, XCircle, Clock, 
  RefreshCw, Zap, Shield, Target, TrendingDown as Loss,
  Bitcoin, ArrowLeft
} from "lucide-react"
import { 
  useAccount, usePositions, useOrders, useSignals, 
  usePerformanceMetrics, useRiskMetrics, useWebSocket,
  useSubmitOrder, useClosePosition, useCancelOrder,
  useTradingHistory, usePnlChart, useTradingMetrics, useTradingStrategies
} from '@/hooks/useAlpaca'
import { TradingChart } from '@/components/trading/TradingChart'
import { ScalpingEngine } from '@/components/trading/ScalpingEngine'
import { CryptoMarketScreener } from '@/components/trading/CryptoMarketScreener'
import { LiveTradeFeed } from '@/components/trading/LiveTradeFeed'
import { TradingProvider } from '@/contexts/TradingContext'
import { formatCurrency, formatPercent } from '@/lib/utils'
import { toast } from 'sonner'
import Link from 'next/link'

export default function CryptoTradingPage() {
  const [selectedSymbol, setSelectedSymbol] = useState('BTCUSD')
  const [isCryptoBotActive, setIsCryptoBotActive] = useState(false)
  const [realtimeData, setRealtimeData] = useState<any>({})

  // Crypto-specific data hooks - always use 'crypto' mode
  const { data: account, isLoading: accountLoading } = useAccount('crypto')
  const { data: positions = [], isLoading: positionsLoading } = usePositions('crypto')
  const { data: orders = [], isLoading: ordersLoading } = useOrders('open', 'crypto')
  const { data: signals = [], isLoading: signalsLoading } = useSignals(undefined, 'crypto')
  const { data: performance } = usePerformanceMetrics('crypto')
  const { data: riskMetrics } = useRiskMetrics('crypto')
  
  // New data hooks for additional metrics
  const { data: tradingHistory } = useTradingHistory('crypto')
  const { data: pnlChart } = usePnlChart('crypto')
  const { data: tradingMetrics } = useTradingMetrics('crypto')
  const { data: strategies } = useTradingStrategies('crypto')
  
  // Mutations for crypto
  const submitOrder = useSubmitOrder('crypto')
  const closePosition = useClosePosition('crypto')
  const cancelOrder = useCancelOrder('crypto')

  // WebSocket for real-time crypto data
  const { isConnected } = useWebSocket(
    positions.map((p: any) => p.symbol),
    (data: any) => {
      setRealtimeData((prev: any) => ({
        ...prev,
        [data.symbol]: data
      }))
    },
    'crypto'
  )

  // Crypto Bot Logic - 24/7 Trading
  useEffect(() => {
    if (!isCryptoBotActive || !signals.length) return

    const interval = setInterval(() => {
      const cryptoSignals = signals.filter((s: any) => 
        s.symbol.includes('USD') || s.symbol.includes('USDT') || s.symbol.includes('USDC')
      )

      cryptoSignals.forEach((signal: any) => {
        if (signal.strength > 0.70) {
          const hasPosition = positions.some((p: any) => p.symbol === signal.symbol)
          
          if (signal.signal_type === 'buy' && !hasPosition) {
            submitOrder.mutate({
              symbol: signal.symbol,
              qty: 0.01, // Fractional quantities for crypto
              side: 'buy',
              type: 'market',
              time_in_force: 'gtc'
            })
            toast.success(`🪙 Crypto Bot: BUY ${signal.symbol}`)
          } else if (signal.signal_type === 'sell' && hasPosition) {
            closePosition.mutate(signal.symbol)
            toast.success(`🪙 Crypto Bot: SELL ${signal.symbol}`)
          }
        }
      })
    }, 5000) // Check every 5 seconds for crypto

    return () => clearInterval(interval)
  }, [isCryptoBotActive, signals, positions])

  // Calculate crypto-specific stats
  const totalValue = performance?.portfolio_value || performance?.total_equity || account?.portfolio_value || 0
  const buyingPower = performance?.buying_power || account?.buying_power || 0
  
  // Convert daily_return percentage to dollar amount
  const dailyReturnPct = performance?.daily_return || 0
  const dayChange = totalValue > 0 ? (totalValue * dailyReturnPct / 100) : 0
  const totalPL = dayChange  // For crypto, daily P&L is the same as total P&L for the day
  
  const winRate = (performance?.win_rate || 0) / 100  // Convert from percentage to decimal

  return (
    <TradingProvider>
      <div className="min-h-screen bg-background">
      {/* Crypto Header */}
      <header className="border-b bg-gradient-to-r from-orange-500/10 to-yellow-500/10 backdrop-blur">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <Link href="/">
                <Button variant="ghost" size="sm">
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  Back to Stocks
                </Button>
              </Link>
              <Bitcoin className="h-8 w-8 text-yellow-500" />
              <div>
                <h1 className="text-2xl font-bold">Crypto Trading Bot</h1>
                <p className="text-sm text-muted-foreground">24/7 Automated Trading • 15-40 trades/hour</p>
              </div>
              <Badge variant={isConnected ? "default" : "destructive"}>
                {isConnected ? "Live" : "Disconnected"}
              </Badge>
              <Badge variant="default" className="bg-yellow-500">
                24/7 Trading
              </Badge>
            </div>
            <div className="flex items-center space-x-4">
              <Badge 
                variant={isCryptoBotActive ? "default" : "outline"}
                className={isCryptoBotActive ? "bg-orange-500" : ""}
              >
                <Bitcoin className="mr-1 h-3 w-3" />
                Crypto Bot: {isCryptoBotActive ? "ON" : "OFF"}
              </Badge>
              <Button
                variant={isCryptoBotActive ? "destructive" : "default"}
                onClick={async () => {
                  const newState = !isCryptoBotActive
                  setIsCryptoBotActive(newState)
                  // Log to backend
                  try {
                    await fetch(`/api/bot/${newState ? 'activate' : 'deactivate'}`, {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({ market: 'crypto' })
                    })
                  } catch (e) {
                    console.error('Failed to update bot status:', e)
                  }
                }}
                className={isCryptoBotActive ? "animate-pulse" : ""}
              >
                <Zap className="mr-2 h-4 w-4" />
                {isCryptoBotActive ? "⚡ CRYPTO BOT ACTIVE" : "Start Crypto Bot"}
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
        {/* Crypto Stats Cards */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5 mb-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Crypto Portfolio</CardTitle>
              <DollarSign className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {formatCurrency(totalValue)}
              </div>
              <p className="text-xs text-muted-foreground">
                <span className={dayChange >= 0 ? "text-green-500" : "text-red-500"}>
                  {formatPercent(totalValue > 0 ? dayChange / totalValue : 0)}
                </span> today (24h)
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">24h P&L</CardTitle>
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
                {performance?.winning_positions || 0} wins / {performance?.losing_positions || 0} losses
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Active Crypto</CardTitle>
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
              <p className="text-xs text-muted-foreground">24h trading</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Available Cash</CardTitle>
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

        {/* New Metrics Row - Display new API data */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mb-6">
          {/* Trading Metrics Card */}
          {tradingMetrics && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Trading Metrics</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-1">
                  <div className="flex justify-between text-sm">
                    <span>Daily Return:</span>
                    <span className={tradingMetrics.daily_return >= 0 ? "text-green-500" : "text-red-500"}>
                      {formatPercent(tradingMetrics.daily_return / 100)}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span>Win Rate:</span>
                    <span>{formatPercent(tradingMetrics.win_rate / 100)}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span>Positions:</span>
                    <span>{tradingMetrics.total_positions}</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* P&L Chart Summary */}
          {pnlChart && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">P&L Summary</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-1">
                  <div className="flex justify-between text-sm">
                    <span>Total P&L:</span>
                    <span className={pnlChart.total_pnl >= 0 ? "text-green-500" : "text-red-500"}>
                      {formatCurrency(pnlChart.total_pnl)}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span>P&L %:</span>
                    <span className={pnlChart.total_pnl_pct >= 0 ? "text-green-500" : "text-red-500"}>
                      {formatPercent(pnlChart.total_pnl_pct / 100)}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span>Equity:</span>
                    <span>{formatCurrency(pnlChart.current_equity)}</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Active Strategies */}
          {strategies && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Active Strategies</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-1">
                  {strategies.strategies?.slice(0, 3).map((strategy: any) => (
                    <div key={strategy.id} className="flex justify-between text-sm">
                      <span className="truncate">{strategy.name}:</span>
                      <Badge variant={strategy.enabled ? "default" : "secondary"} className="text-xs">
                        {strategy.enabled ? "Active" : "Inactive"}
                      </Badge>
                    </div>
                  ))}
                  <div className="text-xs text-muted-foreground mt-1">
                    {strategies.active_count} of {strategies.strategies?.length} active
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Trading History Summary */}
          {tradingHistory && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Recent History</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-1">
                  <div className="flex justify-between text-sm">
                    <span>Total Trades:</span>
                    <span>{tradingHistory.count || 0}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span>Data Source:</span>
                    <Badge variant="outline" className="text-xs">
                      {tradingHistory.data_source}
                    </Badge>
                  </div>
                  {tradingHistory.history && tradingHistory.history[0] && (
                    <div className="text-xs text-muted-foreground mt-1">
                      Last: {tradingHistory.history[0].symbol} ({tradingHistory.history[0].side})
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Trading Interface */}
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Left Panel - Chart */}
          <div className="lg:col-span-2 space-y-6">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle>Crypto Chart - {selectedSymbol}</CardTitle>
                  <CardDescription>24/7 Cryptocurrency Trading</CardDescription>
                </div>
              </CardHeader>
              <CardContent>
                <TradingChart 
                  symbol={selectedSymbol} 
                  realtimeData={realtimeData[selectedSymbol]}
                  marketType="crypto"
                  onSymbolChange={setSelectedSymbol}
                  height={400}
                />
              </CardContent>
            </Card>

            {/* Scalping Engine */}
            <ScalpingEngine
              marketType="crypto"
              selectedSymbol={selectedSymbol}
              isActive={isCryptoBotActive}
              onToggleActive={() => setIsCryptoBotActive(!isCryptoBotActive)}
              onExecuteSignal={(signal) => {
                const order = {
                  symbol: signal.symbol,
                  qty: 0.01,
                  side: signal.direction.toLowerCase() as 'buy' | 'sell',
                  type: 'market' as const,
                  time_in_force: 'gtc' as const
                }
                submitOrder.mutate(order)
                toast.success(`🪙 Crypto: ${signal.direction} ${signal.symbol}`)
              }}
            />

            {/* Live Trade Feed with Profit Chart */}
            <LiveTradeFeed marketType="crypto" />
          </div>

          {/* Right Panel - Market Screener & Positions */}
          <div className="space-y-6">
            {/* Crypto Market Screener */}
            <CryptoMarketScreener
              onSymbolSelect={setSelectedSymbol}
              onTradingToggle={(symbol, enabled) => {
                toast.info(`${symbol} trading ${enabled ? 'enabled' : 'disabled'}`)
              }}
            />

            {/* Positions */}
            <Card>
              <CardHeader>
                <CardTitle>Crypto Positions</CardTitle>
                <CardDescription>Current holdings</CardDescription>
              </CardHeader>
              <CardContent>
                {positionsLoading ? (
                  <div className="text-center py-4">Loading positions...</div>
                ) : positions.length === 0 ? (
                  <div className="text-center py-4 text-muted-foreground">No crypto positions</div>
                ) : (
                  <div className="space-y-2">
                    {positions.map((position: any) => (
                      <div key={position.symbol} className="flex items-center justify-between p-2 border rounded">
                        <div>
                          <div className="font-medium">{position.symbol}</div>
                          <div className="text-sm text-muted-foreground">
                            {position.qty} @ {formatCurrency(parseFloat(position.avg_entry_price))}
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
                            Close
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
    </TradingProvider>
  )
}