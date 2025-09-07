"use client"

import { useState, useEffect, useCallback } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { 
  Zap, TrendingUp, TrendingDown, Activity, DollarSign, BarChart3, 
  Settings, AlertCircle, CheckCircle, XCircle, Clock, 
  RefreshCw, Target, Shield, ArrowLeft, Play, Pause, Volume2,
  Bitcoin, Flame, Timer, Eye
} from "lucide-react"
import { 
  useAccount, usePositions, useOrders, useSignals, 
  usePerformanceMetrics, useWebSocket,
  useSubmitOrder, useClosePosition, useCancelOrder
} from '@/hooks/useAlpaca'
import { TradingProvider } from '@/contexts/TradingContext'
import { formatCurrency, formatPercent } from '@/lib/utils'
import { toast } from 'sonner'
import Link from 'next/link'
import { ScalpingOrderPanel } from '@/components/trading/ScalpingOrderPanel'
import { ScalpingPositionTracker } from '@/components/trading/ScalpingPositionTracker'
import { ScalpingChart } from '@/components/trading/ScalpingChart'
import { ScalpingMetrics } from '@/components/trading/ScalpingMetrics'
import { QuickActionPanel } from '@/components/trading/QuickActionPanel'
import { VolumeAlertsPanel } from '@/components/trading/VolumeAlertsPanel'

export default function ScalpingDashboard() {
  const [selectedSymbol, setSelectedSymbol] = useState('BTCUSD')
  const [isScalpingActive, setIsScalpingActive] = useState(false)
  const [quickPositionSize, setQuickPositionSize] = useState(0.005) // 0.5% of account
  const [realtimeData, setRealtimeData] = useState<any>({})
  const [hotkeysEnabled, setHotkeysEnabled] = useState(true)
  const [riskLimits, setRiskLimits] = useState({
    dailyLossLimit: 200,
    maxPositions: 3,
    maxPositionSize: 25
  })

  // Crypto-specific data hooks
  const { data: account, isLoading: accountLoading } = useAccount('crypto')
  const { data: positions = [], isLoading: positionsLoading } = usePositions('crypto')
  const { data: orders = [], isLoading: ordersLoading } = useOrders('open', 'crypto')
  const { data: signals = [], isLoading: signalsLoading } = useSignals(undefined, 'crypto')
  const { data: performance } = usePerformanceMetrics('crypto')
  
  // Mutations for crypto trading
  const submitOrder = useSubmitOrder('crypto')
  const closePosition = useClosePosition('crypto')
  const cancelOrder = useCancelOrder('crypto')

  // WebSocket for real-time crypto data
  const { isConnected } = useWebSocket(
    [selectedSymbol, ...positions.map((p: any) => p.symbol)],
    (data: any) => {
      setRealtimeData((prev: any) => ({
        ...prev,
        [data.symbol]: data
      }))
    },
    'crypto'
  )

  // Calculate scalping stats
  const totalValue = performance?.portfolio_value || account?.portfolio_value || 0
  const buyingPower = performance?.buying_power || account?.buying_power || 0
  const dailyReturnPct = performance?.daily_return || 0
  const dayChange = totalValue > 0 ? (totalValue * dailyReturnPct / 100) : 0
  
  // Quick buy/sell functions
  const quickBuy = useCallback(async () => {
    if (!isConnected || positions.length >= riskLimits.maxPositions) return
    
    const quantity = Math.min(
      riskLimits.maxPositionSize / (realtimeData[selectedSymbol]?.price || 45000),
      (totalValue * quickPositionSize) / (realtimeData[selectedSymbol]?.price || 45000)
    )
    
    try {
      await submitOrder.mutateAsync({
        symbol: selectedSymbol,
        qty: quantity,
        side: 'buy',
        type: 'market',
        time_in_force: 'gtc'
      })
      toast.success(`⚡ Quick BUY ${selectedSymbol}`)
    } catch (error) {
      toast.error('Quick buy failed')
    }
  }, [selectedSymbol, submitOrder, isConnected, positions.length, riskLimits, quickPositionSize, totalValue, realtimeData])

  const quickSell = useCallback(async () => {
    const position = positions.find((p: any) => p.symbol === selectedSymbol)
    if (!position) return
    
    try {
      await closePosition.mutateAsync(selectedSymbol)
      toast.success(`⚡ Quick SELL ${selectedSymbol}`)
    } catch (error) {
      toast.error('Quick sell failed')
    }
  }, [selectedSymbol, closePosition, positions])

  const closeAllPositions = useCallback(async () => {
    try {
      await Promise.all(positions.map((p: any) => closePosition.mutateAsync(p.symbol)))
      toast.success('🚫 All positions closed')
    } catch (error) {
      toast.error('Failed to close all positions')
    }
  }, [positions, closePosition])

  // Hotkey support
  useEffect(() => {
    if (!hotkeysEnabled) return

    const handleKeyPress = (event: KeyboardEvent) => {
      if (event.target instanceof HTMLInputElement) return // Don't trigger in inputs
      
      switch (event.code) {
        case 'Space':
          event.preventDefault()
          if (event.shiftKey) {
            quickSell()
          } else {
            quickBuy()
          }
          break
        case 'Escape':
          closeAllPositions()
          break
      }
    }

    window.addEventListener('keydown', handleKeyPress)
    return () => window.removeEventListener('keydown', handleKeyPress)
  }, [hotkeysEnabled, quickBuy, quickSell, closeAllPositions])

  return (
    <TradingProvider>
      <div className="min-h-screen bg-background">
        {/* Scalping Header */}
        <header className="border-b bg-gradient-to-r from-red-500/10 to-orange-500/10 backdrop-blur">
          <div className="container mx-auto px-4 py-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <Link href="/crypto">
                  <Button variant="ghost" size="sm">
                    <ArrowLeft className="mr-2 h-4 w-4" />
                    Back to Crypto
                  </Button>
                </Link>
                <Zap className="h-8 w-8 text-orange-500" />
                <div>
                  <h1 className="text-2xl font-bold">Crypto Scalping Dashboard</h1>
                  <p className="text-sm text-muted-foreground">Ultra High-Frequency Trading • 40-100 trades/hour</p>
                </div>
                <Badge variant={isConnected ? "default" : "destructive"}>
                  {isConnected ? "Live Feed" : "Disconnected"}
                </Badge>
                <Badge variant="destructive" className="animate-pulse">
                  <Flame className="mr-1 h-3 w-3" />
                  SCALPING MODE
                </Badge>
              </div>
              
              <div className="flex items-center space-x-3">
                <div className="text-xs text-muted-foreground">
                  {hotkeysEnabled && (
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="text-xs">SPACE = Buy</Badge>
                      <Badge variant="outline" className="text-xs">SHIFT+SPACE = Sell</Badge>
                      <Badge variant="outline" className="text-xs">ESC = Close All</Badge>
                    </div>
                  )}
                </div>
                
                <Button
                  variant={isScalpingActive ? "destructive" : "default"}
                  onClick={() => setIsScalpingActive(!isScalpingActive)}
                  className={isScalpingActive ? "animate-pulse" : ""}
                >
                  {isScalpingActive ? <Pause className="mr-2 h-4 w-4" /> : <Play className="mr-2 h-4 w-4" />}
                  {isScalpingActive ? "PAUSE SCALPING" : "START SCALPING"}
                </Button>
                
                <Button variant="outline" size="icon">
                  <Settings className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </div>
        </header>

        {/* Main Scalping Interface */}
        <main className="container mx-auto px-4 py-4">
          {/* Top Stats Row */}
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-6 mb-4">
            <Card>
              <CardContent className="pt-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs text-muted-foreground">Portfolio</p>
                    <p className="text-lg font-bold">{formatCurrency(totalValue)}</p>
                  </div>
                  <DollarSign className="h-4 w-4 text-muted-foreground" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs text-muted-foreground">Day P&L</p>
                    <p className={`text-lg font-bold ${dayChange >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                      {formatCurrency(dayChange)}
                    </p>
                  </div>
                  {dayChange >= 0 ? 
                    <TrendingUp className="h-4 w-4 text-green-500" /> :
                    <TrendingDown className="h-4 w-4 text-red-500" />
                  }
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs text-muted-foreground">Positions</p>
                    <p className="text-lg font-bold">{positions.length}/{riskLimits.maxPositions}</p>
                  </div>
                  <Activity className="h-4 w-4 text-muted-foreground" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs text-muted-foreground">Buying Power</p>
                    <p className="text-lg font-bold">{formatCurrency(buyingPower)}</p>
                  </div>
                  <Shield className="h-4 w-4 text-muted-foreground" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs text-muted-foreground">Orders</p>
                    <p className="text-lg font-bold">{orders.length}</p>
                  </div>
                  <Clock className="h-4 w-4 text-muted-foreground" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs text-muted-foreground">Risk Level</p>
                    <p className="text-lg font-bold text-orange-500">
                      {Math.round((Math.abs(dayChange) / riskLimits.dailyLossLimit) * 100)}%
                    </p>
                  </div>
                  <AlertCircle className="h-4 w-4 text-orange-500" />
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Main Trading Interface */}
          <div className="grid gap-4 lg:grid-cols-12">
            {/* Left Column - Quick Actions & Orders */}
            <div className="lg:col-span-3 space-y-4">
              <QuickActionPanel 
                selectedSymbol={selectedSymbol}
                onQuickBuy={quickBuy}
                onQuickSell={quickSell}
                onCloseAll={closeAllPositions}
                positionSize={quickPositionSize}
                onPositionSizeChange={setQuickPositionSize}
                hotkeysEnabled={hotkeysEnabled}
                onHotkeysToggle={setHotkeysEnabled}
              />
              
              <ScalpingOrderPanel 
                selectedSymbol={selectedSymbol}
                onSymbolChange={setSelectedSymbol}
                realtimePrice={realtimeData[selectedSymbol]?.price}
                maxPositionSize={riskLimits.maxPositionSize}
              />
            </div>

            {/* Center Column - Chart */}
            <div className="lg:col-span-6 space-y-4">
              <ScalpingChart 
                symbol={selectedSymbol}
                realtimeData={realtimeData[selectedSymbol]}
                height={400}
              />
              
              <ScalpingMetrics 
                isActive={isScalpingActive}
                selectedSymbol={selectedSymbol}
              />
            </div>

            {/* Right Column - Positions & Alerts */}
            <div className="lg:col-span-3 space-y-4">
              <ScalpingPositionTracker 
                positions={positions}
                realtimeData={realtimeData}
                onClosePosition={async (symbol) => {
                  try {
                    await closePosition.mutateAsync(symbol)
                    toast.success(`Closed ${symbol}`)
                  } catch (error) {
                    toast.error(`Failed to close ${symbol}`)
                  }
                }}
              />
              
              <VolumeAlertsPanel 
                selectedSymbol={selectedSymbol}
                signals={signals}
                onSymbolSelect={setSelectedSymbol}
              />
            </div>
          </div>
        </main>
      </div>
    </TradingProvider>
  )
}