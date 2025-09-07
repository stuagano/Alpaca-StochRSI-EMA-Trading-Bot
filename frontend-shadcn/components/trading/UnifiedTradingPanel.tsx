"use client"

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { formatCurrency, formatPercent } from '@/lib/utils'
import { 
  Activity, TrendingUp, TrendingDown, Clock, Target, 
  RefreshCw, Play, Pause, Eye, EyeOff, Settings,
  BarChart3, History, Zap, Bitcoin, DollarSign
} from 'lucide-react'
import { toast } from 'sonner'
import { usePositions, useOrders, useSignals, useWebSocket } from '@/hooks/useAlpaca'
import { MarketMode } from '@/lib/api/client'

// Import existing components
import { PositionsTable } from './PositionsTable'
import { OrdersTable } from './OrdersTable'
import { SignalsPanel } from './SignalsPanel'
import { OrderForm } from './OrderForm'
import { PerformanceChart } from '../analytics/PerformanceChart'

interface UnifiedTradingPanelProps {
  marketType: MarketMode
  selectedSymbol: string
  onSymbolChange: (symbol: string) => void
  onSubmitOrder?: (order: any) => void
  onClosePosition?: (symbol: string) => void
  onCancelOrder?: (orderId: string) => void
  buyingPower?: number
  isAutoTrading?: boolean
}

// Safe wrapper for PositionsTable to handle optional callbacks
function SafePositionsTable({ 
  positions, 
  onClose, 
  onSelect, 
  realtimeData 
}: {
  positions: any[]
  onClose?: (symbol: string) => void
  onSelect?: (symbol: string) => void
  realtimeData: Record<string, any>
}) {
  const safeOnClose = onClose || (() => {})
  const safeOnSelect = onSelect || (() => {})
  
  return (
    <PositionsTable
      positions={positions}
      onClose={safeOnClose}
      onSelect={safeOnSelect}
      realtimeData={realtimeData}
    />
  )
}

// Safe wrapper for OrdersTable to handle optional callbacks
function SafeOrdersTable({ 
  orders, 
  onCancel 
}: {
  orders: any[]
  onCancel?: (orderId: string) => void
}) {
  const safeOnCancel = onCancel || (() => {})
  
  return (
    <OrdersTable
      orders={orders}
      onCancel={safeOnCancel}
    />
  )
}

interface TradingMetrics {
  daily_profit: number
  active_positions: number
  daily_trades: number
  win_rate: number
  total_trades: number
  winning_trades: number
  losing_trades: number
  portfolio_value: number
  available_cash: number
}

export function UnifiedTradingPanel({
  marketType,
  selectedSymbol,
  onSymbolChange,
  onSubmitOrder,
  onClosePosition,
  onCancelOrder,
  buyingPower = 0,
  isAutoTrading = false
}: UnifiedTradingPanelProps) {
  const [activeTab, setActiveTab] = useState('positions')
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [tradingMetrics, setTradingMetrics] = useState<TradingMetrics>({
    daily_profit: 0,
    active_positions: 0,
    daily_trades: 0,
    win_rate: 0,
    total_trades: 0,
    winning_trades: 0,
    losing_trades: 0,
    portfolio_value: 0,
    available_cash: 0
  })

  // Data hooks - market type aware
  const { data: positions = [], isLoading: positionsLoading } = usePositions(marketType)
  const { data: orders = [], isLoading: ordersLoading } = useOrders('open', marketType)
  const { data: signals = [], isLoading: signalsLoading } = useSignals(undefined, marketType)

  // WebSocket for real-time data
  const { isConnected } = useWebSocket(
    positions.map((p: any) => p.symbol),
    () => {},
    marketType
  )

  // Fetch crypto-specific metrics if in crypto mode
  useEffect(() => {
    if (marketType === 'crypto') {
      const fetchCryptoMetrics = async () => {
        try {
          const response = await fetch('http://localhost:9012/api/status')
          if (response.ok) {
            const data = await response.json()
            setTradingMetrics({
              daily_profit: data.daily_profit || 0,
              active_positions: data.active_positions || 0,
              daily_trades: data.daily_trades || 0,
              win_rate: data.win_rate || 0,
              total_trades: data.total_trades || 0,
              winning_trades: data.winning_trades || 0,
              losing_trades: data.losing_trades || 0,
              portfolio_value: data.portfolio_value || 0,
              available_cash: data.available_cash || 0
            })
          }
        } catch (error) {
          console.error('Failed to fetch crypto metrics:', error)
        }
      }

      fetchCryptoMetrics()
      const interval = setInterval(fetchCryptoMetrics, 3000)
      return () => clearInterval(interval)
    }
  }, [marketType])

  // Market-specific configuration
  const isCrypto = marketType === 'crypto'
  const headerIcon = isCrypto ? <Bitcoin className="h-5 w-5 text-orange-500" /> : <BarChart3 className="h-5 w-5 text-primary" />
  const headerTitle = isCrypto ? 'Cryptocurrency Trading' : 'Stock Trading'
  const headerBadges = isCrypto ? (
    <>
      <Badge variant="outline" className="flex items-center gap-1">
        <Clock className="h-3 w-3" />
        24/7
      </Badge>
      <Badge variant={isConnected ? "default" : "destructive"}>
        {isConnected ? "Live" : "Disconnected"}
      </Badge>
      {isAutoTrading && (
        <Badge variant="default" className="bg-green-500">
          <Zap className="h-3 w-3 mr-1" />
          Auto-Trading
        </Badge>
      )}
    </>
  ) : (
    <>
      <Badge variant={isConnected ? "default" : "destructive"}>
        {isConnected ? "Market Open" : "Market Closed"}
      </Badge>
      {isAutoTrading && (
        <Badge variant="default" className="bg-blue-500">
          Auto-Trading
        </Badge>
      )}
    </>
  )

  // Unified tab configuration
  const tabs = [
    { id: 'positions', label: 'Positions', icon: Activity },
    { id: 'orders', label: 'Orders', icon: Target },
    { id: 'signals', label: 'Signals', icon: TrendingUp },
    ...(isCrypto ? [{ id: 'history', label: 'History', icon: History }] : []),
    { id: 'analytics', label: 'Analytics', icon: BarChart3 }
  ]

  return (
    <Card className="w-full">
      <CardHeader className="flex flex-row items-center space-y-0 pb-2">
        <div className="flex items-center space-x-2">
          {headerIcon}
          <CardTitle>{headerTitle}</CardTitle>
        </div>
        <div className="ml-auto flex items-center gap-2">
          {headerBadges}
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowAdvanced(!showAdvanced)}
          >
            {showAdvanced ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </Button>
        </div>
      </CardHeader>

      <CardContent>
        {/* Market-specific quick stats */}
        {isCrypto && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4 p-4 bg-muted/50 rounded-lg">
            <div className="text-center">
              <div className="text-lg font-bold text-green-500">
                {formatCurrency(tradingMetrics.daily_profit)}
              </div>
              <div className="text-xs text-muted-foreground">Daily P&L</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-bold">
                {tradingMetrics.active_positions}
              </div>
              <div className="text-xs text-muted-foreground">Active Positions</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-bold">
                {tradingMetrics.daily_trades}
              </div>
              <div className="text-xs text-muted-foreground">Trades Today</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-bold">
                {formatPercent(tradingMetrics.win_rate)}
              </div>
              <div className="text-xs text-muted-foreground">Win Rate</div>
            </div>
          </div>
        )}

        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-4 lg:grid-cols-5">
            {tabs.map((tab) => (
              <TabsTrigger key={tab.id} value={tab.id} className="flex items-center gap-1">
                <tab.icon className="h-3 w-3" />
                <span className="hidden sm:inline">{tab.label}</span>
              </TabsTrigger>
            ))}
          </TabsList>

          <TabsContent value="positions" className="space-y-4">
            {isCrypto ? (
              /* Crypto Positions - Custom layout optimized for crypto */
              <div className="space-y-3">
                {positionsLoading ? (
                  <div className="text-center py-8">
                    <RefreshCw className="h-6 w-6 animate-spin mx-auto mb-2" />
                    <p className="text-sm text-muted-foreground">Loading positions...</p>
                  </div>
                ) : positions.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    No active crypto positions
                  </div>
                ) : (
                  positions.map((position: any, index: number) => {
                    const pl = parseFloat(position.unrealized_pl || '0')
                    const plPercent = parseFloat(position.unrealized_plpc || '0')
                    const isProfit = pl >= 0

                    return (
                      <Card key={index} className="p-4">
                        <div className="flex items-center justify-between">
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="font-semibold">{position.symbol}</span>
                              <Badge variant="outline">
                                <Clock className="h-3 w-3 mr-1" />
                                24/7
                              </Badge>
                              {position.side && (
                                <Badge variant={position.side === 'long' ? 'default' : 'destructive'}>
                                  {position.side.toUpperCase()}
                                </Badge>
                              )}
                            </div>
                            <div className="text-sm text-muted-foreground">
                              {parseFloat(position.qty || '0').toFixed(8)} @ {formatCurrency(parseFloat(position.avg_entry_price || '0'))}
                            </div>
                            {showAdvanced && position.entry_time && (
                              <div className="text-xs text-muted-foreground">
                                Entry: {new Date(position.entry_time).toLocaleString()}
                              </div>
                            )}
                          </div>
                          <div className="text-right">
                            <div className={`font-semibold ${isProfit ? 'text-green-500' : 'text-red-500'}`}>
                              <span className="flex items-center">
                                {isProfit ? <TrendingUp className="h-4 w-4 mr-1" /> : <TrendingDown className="h-4 w-4 mr-1" />}
                                {formatCurrency(pl)}
                              </span>
                            </div>
                            <div className="text-sm text-muted-foreground">
                              {formatPercent(plPercent)}
                            </div>
                            {onClosePosition && (
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => onClosePosition(position.symbol)}
                                className="mt-2"
                              >
                                Close
                              </Button>
                            )}
                          </div>
                        </div>
                      </Card>
                    )
                  })
                )}
              </div>
            ) : (
              /* Stock Positions - Use existing PositionsTable */
              <SafePositionsTable
                positions={positions}
                onClose={onClosePosition}
                onSelect={onSymbolChange}
                realtimeData={{}}
              />
            )}
          </TabsContent>

          <TabsContent value="orders" className="space-y-4">
            <SafeOrdersTable
              orders={orders}
              onCancel={onCancelOrder}
            />
          </TabsContent>

          <TabsContent value="signals" className="space-y-4">
            <SignalsPanel
              signals={signals}
              onExecute={(signal) => {
                if (onSubmitOrder) {
                  onSubmitOrder({
                    symbol: signal.symbol,
                    qty: isCrypto ? 0.1 : 10,
                    side: signal.signal_type === 'buy' ? 'buy' : 'sell',
                    type: 'market',
                    time_in_force: isCrypto ? 'gtc' : 'day'
                  })
                }
              }}
            />
          </TabsContent>

          {isCrypto && (
            <TabsContent value="history" className="space-y-4">
              <div className="text-center py-8 text-muted-foreground">
                <History className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>Crypto trading history will be displayed here</p>
                <p className="text-sm">Integration with crypto day trading panel history</p>
              </div>
            </TabsContent>
          )}

          <TabsContent value="analytics" className="space-y-4">
            <PerformanceChart />
          </TabsContent>
        </Tabs>

        {/* Market-specific order form */}
        {!isCrypto && onSubmitOrder && (
          <div className="mt-6 pt-6 border-t">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <DollarSign className="h-4 w-4" />
              Quick Order
            </h3>
            <OrderForm
              defaultSymbol={selectedSymbol}
              buyingPower={buyingPower}
              onSubmit={onSubmitOrder}
            />
          </div>
        )}

        {/* Crypto automated trading notice */}
        {isCrypto && (
          <div className="mt-6 pt-6 border-t">
            <Card className="p-3 bg-orange-500/10 border-orange-500/20">
              <div className="flex items-center space-x-2">
                <Bitcoin className="h-4 w-4 text-orange-500" />
                <span className="text-sm font-medium">Crypto Trading Rules</span>
              </div>
              <ul className="text-xs text-muted-foreground mt-2 space-y-1">
                <li>• Fully automated trading - no manual orders</li>
                <li>• 24/7 market availability</li>
                <li>• Fractional shares supported</li>
                <li>• T+0 settlement (instant)</li>
                <li>• No margin or short selling</li>
              </ul>
            </Card>
          </div>
        )}
      </CardContent>
    </Card>
  )
}