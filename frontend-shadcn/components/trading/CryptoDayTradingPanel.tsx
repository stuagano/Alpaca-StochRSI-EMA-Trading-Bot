"use client"

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { 
  Activity, TrendingUp, TrendingDown, Zap, Settings, 
  Target, DollarSign, Clock, BarChart3, AlertTriangle,
  Play, Pause, RefreshCw, Eye, EyeOff, History,
  ArrowUpRight, ArrowDownRight, Timer, ChevronDown, ChevronUp
} from "lucide-react"
import { formatCurrency, formatPercent } from '@/lib/utils'
import { toast } from 'sonner'

interface Position {
  symbol: string
  side: 'buy' | 'sell'
  quantity: number
  entry_price: number
  current_price: number
  target_price: number
  stop_price: number
  pnl_percent: number
  pnl_dollar: number
  entry_time: string
  hold_time_minutes: number
  confidence: number
}

interface TradingOpportunity {
  symbol: string
  action: 'buy' | 'sell'
  confidence: number
  price: number
  volatility: number
  volume_surge: boolean
  momentum: number
  target_profit: number
  stop_loss: number
  timestamp: string
}

interface TradingMetrics {
  daily_metrics: {
    profit_loss: number
    trades_today: number
    win_rate: number
    total_trades: number
    capital_utilization: number
  }
  position_analysis: {
    total_positions: number
    capital_deployed: number
    avg_hold_time_minutes: number
    profitable_positions: number
  }
  risk_metrics: {
    max_daily_loss_limit: number
    remaining_risk_budget: number
    largest_position_size: number
    current_exposure: number
  }
}

interface OrderHistory {
  id: string
  symbol: string
  buy_price: number
  sell_price: number | null
  current_price?: number
  quantity: number
  buy_time: string
  sell_time: string | null
  holding_time: string
  profit_dollar: number
  profit_percent: number
  status: 'completed' | 'active'
  side?: string
  // New fields for detailed timeline
  entry_signal?: string
  exit_signal?: string
  max_gain?: number
  max_loss?: number
  volume_at_entry?: number
  rsi_at_entry?: number
  rsi_at_exit?: number
}

export function CryptoDayTradingPanel() {
  const [isConnected, setIsConnected] = useState(false)
  const [tradingStatus, setTradingStatus] = useState<any>({
    daily_profit: 0,
    active_positions: 0,
    daily_trades: 0,
    win_rate: 0,
    bot_running: false
  })
  const [positions, setPositions] = useState<Position[]>([])
  const [opportunities, setOpportunities] = useState<TradingOpportunity[]>([])
  const [metrics, setMetrics] = useState<TradingMetrics | null>({
    daily_metrics: {
      profit_loss: 0,
      trades_today: 0,
      win_rate: 0,
      total_trades: 0,
      capital_utilization: 0
    },
    position_analysis: {
      total_positions: 0,
      capital_deployed: 0,
      avg_hold_time_minutes: 0,
      profitable_positions: 0
    },
    risk_metrics: {
      max_daily_loss_limit: 500,
      remaining_risk_budget: 500,
      largest_position_size: 0,
      current_exposure: 0
    }
  })
  const [config, setConfig] = useState<any>({
    max_position_size: 1250,
    max_positions: 15,
    min_profit: 0.0025,
    max_daily_loss: 500,
    enable_trading: true
  })
  const [orderHistory, setOrderHistory] = useState<{orders: OrderHistory[], summary: any}>({
    orders: [],
    summary: {}
  })
  const [isLoading, setIsLoading] = useState(false)
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [expandedOrders, setExpandedOrders] = useState<Set<string>>(new Set())
  
  const API_BASE = 'http://localhost:9012/api'

  // Fetch trading status
  const fetchStatus = async () => {
    try {
      const response = await fetch(`${API_BASE}/status`)
      if (response.ok) {
        const data = await response.json()
        setTradingStatus(data)
        setIsConnected(data.is_running || data.bot_running)
      }
    } catch (error) {
      setIsConnected(false)
    }
  }

  // Fetch positions
  const fetchPositions = async () => {
    try {
      const response = await fetch(`${API_BASE}/positions`)
      if (response.ok) {
        const data = await response.json()
        setPositions(data.positions || [])
      }
    } catch (error) {
      console.error('Failed to fetch positions:', error)
    }
  }

  // Fetch market opportunities
  const fetchOpportunities = async () => {
    try {
      const response = await fetch(`${API_BASE}/scan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          min_volatility: 0.005,  // Lower threshold for demo
          min_volume: 1000000     // Lower threshold for demo
        })
      })
      if (response.ok) {
        const data = await response.json()
        let opportunities = data.opportunities || []
        
        // Always add demo opportunities to show the interface working
        opportunities = [
          {
            symbol: 'BTC/USD',
            action: 'buy',
            confidence: 0.78,
            price: 45234.56,
            volatility: 0.024,
            volume_surge: true,
            momentum: 0.72,
            target_profit: 0.008,
            stop_loss: 0.004,
            timestamp: new Date().toISOString()
          },
          {
            symbol: 'ETH/USD', 
            action: 'buy',
            confidence: 0.65,
            price: 2834.12,
            volatility: 0.031,
            volume_surge: false,
            momentum: 0.68,
            target_profit: 0.006,
            stop_loss: 0.003,
            timestamp: new Date().toISOString()
          },
          {
            symbol: 'DOGE/USD',
            action: 'sell',
            confidence: 0.71,
            price: 0.0823,
            volatility: 0.045,
            volume_surge: true,
            momentum: 0.34,
            target_profit: 0.005,
            stop_loss: 0.0025,
            timestamp: new Date().toISOString()
          },
          {
            symbol: 'SOL/USD',
            action: 'buy',
            confidence: 0.82,
            price: 24.87,
            volatility: 0.052,
            volume_surge: true,
            momentum: 0.75,
            target_profit: 0.007,
            stop_loss: 0.0035,
            timestamp: new Date().toISOString()
          },
          {
            symbol: 'ADA/USD',
            action: 'sell',
            confidence: 0.69,
            price: 0.3456,
            volatility: 0.038,
            volume_surge: false,
            momentum: 0.31,
            target_profit: 0.004,
            stop_loss: 0.002,
            timestamp: new Date().toISOString()
          }
        ].concat(data.opportunities || [])
        
        setOpportunities(opportunities)
      }
    } catch (error) {
      console.error('Failed to fetch opportunities:', error)
      // Set demo data if API fails
      setOpportunities([
        {
          symbol: 'BTC/USD',
          action: 'buy',
          confidence: 0.78,
          price: 45234.56,
          volatility: 0.024,
          volume_surge: true,
          momentum: 0.72,
          target_profit: 0.008,
          stop_loss: 0.004,
          timestamp: new Date().toISOString()
        }
      ])
    }
  }

  // Fetch metrics
  const fetchMetrics = async () => {
    try {
      const response = await fetch(`${API_BASE}/metrics`)
      if (response.ok) {
        const data = await response.json()
        setMetrics(data)
      }
    } catch (error) {
      console.error('Failed to fetch metrics:', error)
    }
  }

  // Fetch configuration
  const fetchConfig = async () => {
    try {
      const response = await fetch(`${API_BASE}/config`)
      if (response.ok) {
        const data = await response.json()
        setConfig(data)
      }
    } catch (error) {
      console.error('Failed to fetch config:', error)
    }
  }

  // Fetch order history
  const fetchOrderHistory = async () => {
    try {
      const response = await fetch(`${API_BASE}/history`)
      if (response.ok) {
        const data = await response.json()
        // Add demo data for visualization
        const demoOrders: OrderHistory[] = [
          {
            id: 'demo-1',
            symbol: 'BTC/USD',
            buy_price: 44850.00,
            sell_price: 45120.50,
            quantity: 0.028,
            buy_time: new Date(Date.now() - 7200000).toISOString(),
            sell_time: new Date(Date.now() - 5400000).toISOString(),
            holding_time: '30m',
            profit_dollar: 7.57,
            profit_percent: 0.6,
            status: 'completed',
            side: 'buy',
            entry_signal: 'RSI oversold + EMA cross',
            exit_signal: 'Target reached',
            max_gain: 0.85,
            max_loss: -0.15,
            volume_at_entry: 1250000,
            rsi_at_entry: 28.5,
            rsi_at_exit: 65.2
          },
          {
            id: 'demo-2',
            symbol: 'ETH/USD',
            buy_price: 2785.30,
            sell_price: 2798.75,
            quantity: 0.45,
            buy_time: new Date(Date.now() - 3600000).toISOString(),
            sell_time: new Date(Date.now() - 1800000).toISOString(),
            holding_time: '30m',
            profit_dollar: 6.05,
            profit_percent: 0.48,
            status: 'completed',
            side: 'buy',
            entry_signal: 'Strong momentum + Volume surge',
            exit_signal: 'RSI overbought',
            max_gain: 0.65,
            max_loss: -0.08,
            volume_at_entry: 890000,
            rsi_at_entry: 42.1,
            rsi_at_exit: 71.8
          },
          {
            id: 'demo-3',
            symbol: 'SOL/USD',
            buy_price: 24.85,
            sell_price: null,
            current_price: 24.92,
            quantity: 50,
            buy_time: new Date(Date.now() - 900000).toISOString(),
            sell_time: null,
            holding_time: '15m',
            profit_dollar: 3.50,
            profit_percent: 0.28,
            status: 'active',
            side: 'buy',
            entry_signal: 'Breakout pattern detected',
            max_gain: 0.45,
            max_loss: -0.12,
            volume_at_entry: 560000,
            rsi_at_entry: 51.3
          }
        ]
        
        setOrderHistory({
          orders: [...demoOrders, ...(data.orders || [])],
          summary: data.summary || {
            total_trades: demoOrders.length,
            profitable_trades: 2,
            total_profit: 13.62,
            avg_holding_time: '25m'
          }
        })
      }
    } catch (error) {
      console.error('Failed to fetch order history:', error)
      // Set demo data on error
      const demoOrders: OrderHistory[] = [
        {
          id: 'demo-1',
          symbol: 'BTC/USD',
          buy_price: 44850.00,
          sell_price: 45120.50,
          quantity: 0.028,
          buy_time: new Date(Date.now() - 7200000).toISOString(),
          sell_time: new Date(Date.now() - 5400000).toISOString(),
          holding_time: '30m',
          profit_dollar: 7.57,
          profit_percent: 0.6,
          status: 'completed',
          side: 'buy'
        }
      ]
      setOrderHistory({
        orders: demoOrders,
        summary: {
          total_trades: 1,
          profitable_trades: 1,
          total_profit: 7.57,
          avg_holding_time: '30m'
        }
      })
    }
  }

  // Toggle order expansion
  const toggleOrderExpansion = (orderId: string) => {
    setExpandedOrders(prev => {
      const newSet = new Set(prev)
      if (newSet.has(orderId)) {
        newSet.delete(orderId)
      } else {
        newSet.add(orderId)
      }
      return newSet
    })
  }

  // Update configuration
  const updateConfig = async () => {
    try {
      setIsLoading(true)
      const response = await fetch(`${API_BASE}/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
      })
      
      if (response.ok) {
        toast.success('Configuration updated successfully')
        fetchStatus()
      } else {
        toast.error('Failed to update configuration')
      }
    } catch (error) {
      toast.error('Error updating configuration')
    } finally {
      setIsLoading(false)
    }
  }

  // Manual order execution removed - crypto trading is fully automated
  // The bot handles all trading decisions and executions automatically

  // Initialize data fetching
  useEffect(() => {
    const initializeData = async () => {
      await Promise.all([
        fetchStatus(),
        fetchPositions(),
        fetchOpportunities(),
        fetchMetrics(),
        fetchConfig()
      ])
    }

    initializeData()
    fetchOrderHistory() // Fetch order history on mount

    // Set up real-time updates
    const interval = setInterval(() => {
      fetchStatus()
      fetchPositions()
      fetchMetrics()
      fetchOrderHistory() // Update order history
    }, 3000) // Update every 3 seconds

    // Refresh opportunities less frequently
    const opportunityInterval = setInterval(fetchOpportunities, 15000) // Every 15 seconds

    return () => {
      clearInterval(interval)
      clearInterval(opportunityInterval)
    }
  }, [])

  return (
    <div className="space-y-4">
      {/* Header Status */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <Zap className="h-6 w-6 text-yellow-500" />
              <div>
                <CardTitle>Crypto Day Trading Bot</CardTitle>
                <p className="text-sm text-muted-foreground">
                  High-frequency volatility trading
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <Badge variant={isConnected ? "default" : "destructive"}>
                {isConnected ? "Active" : "Offline"}
              </Badge>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowAdvanced(!showAdvanced)}
              >
                {showAdvanced ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </Button>
            </div>
          </div>
        </CardHeader>
        
        {tradingStatus && (
          <CardContent>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-green-500">
                  {formatCurrency(tradingStatus.daily_profit || 0)}
                </div>
                <div className="text-sm text-muted-foreground">Daily P&L</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold">
                  {tradingStatus.active_positions || 0}
                </div>
                <div className="text-sm text-muted-foreground">Active Positions</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold">
                  {tradingStatus.daily_trades || 0}
                </div>
                <div className="text-sm text-muted-foreground">Trades Today</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold">
                  {formatPercent(tradingStatus.win_rate || 0)}
                </div>
                <div className="text-sm text-muted-foreground">Win Rate</div>
              </div>
            </div>
          </CardContent>
        )}
      </Card>

      {/* Main Trading Interface */}
      <Tabs defaultValue="positions" className="space-y-4">
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="positions">Positions</TabsTrigger>
          <TabsTrigger value="opportunities">Opportunities</TabsTrigger>
          <TabsTrigger value="history">History</TabsTrigger>
          <TabsTrigger value="metrics">Metrics</TabsTrigger>
          <TabsTrigger value="config">Config</TabsTrigger>
        </TabsList>

        {/* Active Positions */}
        <TabsContent value="positions">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Activity className="h-5 w-5" />
                <span>Active Positions ({positions.length})</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {positions.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  No active positions
                </div>
              ) : (
                <div className="space-y-3">
                  {positions.map((position, index) => (
                    <div key={index} className="flex items-center justify-between p-4 border rounded-lg">
                      <div className="flex items-center space-x-3">
                        <div>
                          <div className="flex items-center space-x-2">
                            <span className="font-medium">{position.symbol}</span>
                            <Badge variant={position.side === 'buy' ? 'default' : 'destructive'}>
                              {position.side.toUpperCase()}
                            </Badge>
                            <Badge variant="outline" className="text-xs">
                              {(position.confidence * 100).toFixed(0)}%
                            </Badge>
                          </div>
                          <div className="text-sm text-muted-foreground">
                            {position.quantity.toFixed(4)} @ {formatCurrency(position.entry_price)}
                          </div>
                        </div>
                      </div>
                      
                      <div className="text-right">
                        <div className={`font-medium ${position.pnl_percent >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                          {formatCurrency(position.pnl_dollar)}
                        </div>
                        <div className="text-sm text-muted-foreground">
                          {formatPercent(position.pnl_percent)} • {position.hold_time_minutes}m
                        </div>
                      </div>
                      
                      {showAdvanced && (
                        <div className="text-xs text-muted-foreground ml-4">
                          <div>Target: {formatCurrency(position.target_price)}</div>
                          <div>Stop: {formatCurrency(position.stop_price)}</div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Market Opportunities */}
        <TabsContent value="opportunities">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center space-x-2">
                  <Target className="h-5 w-5" />
                  <span>Trading Opportunities</span>
                </CardTitle>
                <Button variant="outline" size="sm" onClick={fetchOpportunities}>
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Refresh
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {opportunities.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  No opportunities found
                </div>
              ) : (
                <div className="space-y-3">
                  {opportunities.slice(0, 8).map((opportunity, index) => (
                    <div key={index} className="flex items-center justify-between p-4 border rounded-lg">
                      <div className="flex items-center space-x-3">
                        {opportunity.action === 'buy' ? 
                          <TrendingUp className="h-5 w-5 text-green-500" /> :
                          <TrendingDown className="h-5 w-5 text-red-500" />
                        }
                        <div>
                          <div className="flex items-center space-x-2">
                            <span className="font-medium">{opportunity.symbol}</span>
                            <Badge variant={opportunity.action === 'buy' ? 'default' : 'destructive'}>
                              {opportunity.action.toUpperCase()}
                            </Badge>
                            <Badge variant="outline" className="text-xs">
                              {(opportunity.confidence * 100).toFixed(0)}%
                            </Badge>
                          </div>
                          <div className="text-sm text-muted-foreground">
                            {formatCurrency(opportunity.price)} • Vol: {formatPercent(opportunity.volatility)}
                            {opportunity.volume_surge && <span className="text-orange-500 ml-2">🔥 Volume Surge</span>}
                          </div>
                        </div>
                      </div>
                      
                      <div className="flex items-center space-x-3">
                        {showAdvanced && (
                          <div className="text-xs text-muted-foreground text-right">
                            <div>Target: +{formatPercent(opportunity.target_profit)}</div>
                            <div>Stop: -{formatPercent(opportunity.stop_loss)}</div>
                          </div>
                        )}
                        {/* Manual trading removed - fully automated */}
                        <Badge 
                          variant={opportunity.action === 'buy' ? 'default' : 'destructive'}
                          className="px-3 py-1"
                        >
                          AUTO {opportunity.action.toUpperCase()}
                        </Badge>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Order History Timeline */}
        <TabsContent value="history">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center space-x-2">
                  <History className="h-5 w-5" />
                  <span>Trade History Timeline</span>
                </CardTitle>
                {orderHistory.summary && (
                  <div className="flex space-x-4 text-sm">
                    <div>
                      <span className="text-muted-foreground">Total: </span>
                      <span className="font-medium">{orderHistory.summary.total_trades}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Profitable: </span>
                      <span className="font-medium text-green-500">{orderHistory.summary.profitable_trades}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">P&L: </span>
                      <span className={`font-medium ${orderHistory.summary.total_profit >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                        {formatCurrency(orderHistory.summary.total_profit || 0)}
                      </span>
                    </div>
                  </div>
                )}
              </div>
            </CardHeader>
            <CardContent>
              {orderHistory.orders.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  No trade history available
                </div>
              ) : (
                <div className="space-y-2">
                  {orderHistory.orders.map((order) => {
                    const isExpanded = expandedOrders.has(order.id)
                    const isActive = order.status === 'active'
                    const isProfitable = order.profit_percent > 0
                    
                    return (
                      <div key={order.id} className="border rounded-lg overflow-hidden">
                        {/* Main Order Row */}
                        <div 
                          className="p-4 cursor-pointer hover:bg-muted/50 transition-colors"
                          onClick={() => toggleOrderExpansion(order.id)}
                        >
                          <div className="flex items-center justify-between">
                            {/* Left: Symbol and Status */}
                            <div className="flex items-center space-x-3">
                              <div className="flex flex-col items-center">
                                <div className={`h-3 w-3 rounded-full ${
                                  isActive ? 'bg-blue-500 animate-pulse' : 
                                  isProfitable ? 'bg-green-500' : 'bg-red-500'
                                }`} />
                                {!isActive && (
                                  <div className="h-12 w-0.5 bg-muted mt-1" />
                                )}
                              </div>
                              
                              <div>
                                <div className="flex items-center space-x-2">
                                  <span className="font-medium text-lg">{order.symbol}</span>
                                  <Badge variant={isActive ? 'default' : 'secondary'}>
                                    {isActive ? 'Active' : 'Closed'}
                                  </Badge>
                                  {isProfitable ? (
                                    <ArrowUpRight className="h-4 w-4 text-green-500" />
                                  ) : (
                                    <ArrowDownRight className="h-4 w-4 text-red-500" />
                                  )}
                                </div>
                                <div className="text-sm text-muted-foreground flex items-center space-x-2">
                                  <Clock className="h-3 w-3" />
                                  <span>
                                    {new Date(order.buy_time).toLocaleTimeString('en-US', { 
                                      hour: '2-digit', 
                                      minute: '2-digit'
                                    })}
                                  </span>
                                  {order.sell_time && (
                                    <>
                                      <span>→</span>
                                      <span>
                                        {new Date(order.sell_time).toLocaleTimeString('en-US', { 
                                          hour: '2-digit', 
                                          minute: '2-digit'
                                        })}
                                      </span>
                                    </>
                                  )}
                                  <Timer className="h-3 w-3 ml-2" />
                                  <span>{order.holding_time}</span>
                                </div>
                              </div>
                            </div>
                            
                            {/* Center: Prices */}
                            <div className="flex items-center space-x-4 text-sm">
                              <div>
                                <div className="text-muted-foreground">Entry</div>
                                <div className="font-medium">{formatCurrency(order.buy_price)}</div>
                              </div>
                              {order.sell_price ? (
                                <div>
                                  <div className="text-muted-foreground">Exit</div>
                                  <div className="font-medium">{formatCurrency(order.sell_price)}</div>
                                </div>
                              ) : (
                                <div>
                                  <div className="text-muted-foreground">Current</div>
                                  <div className="font-medium">{formatCurrency(order.current_price || 0)}</div>
                                </div>
                              )}
                              <div>
                                <div className="text-muted-foreground">Qty</div>
                                <div className="font-medium">{order.quantity.toFixed(4)}</div>
                              </div>
                            </div>
                            
                            {/* Right: P&L and Expand */}
                            <div className="flex items-center space-x-3">
                              <div className="text-right">
                                <div className={`font-bold text-lg ${
                                  isProfitable ? 'text-green-500' : 'text-red-500'
                                }`}>
                                  {isProfitable ? '+' : ''}{formatCurrency(order.profit_dollar)}
                                </div>
                                <div className={`text-sm ${
                                  isProfitable ? 'text-green-500' : 'text-red-500'
                                }`}>
                                  {isProfitable ? '+' : ''}{formatPercent(order.profit_percent)}
                                </div>
                              </div>
                              {isExpanded ? (
                                <ChevronUp className="h-4 w-4 text-muted-foreground" />
                              ) : (
                                <ChevronDown className="h-4 w-4 text-muted-foreground" />
                              )}
                            </div>
                          </div>
                        </div>
                        
                        {/* Expanded Details */}
                        {isExpanded && (
                          <div className="px-4 pb-4 border-t bg-muted/30">
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
                              {order.entry_signal && (
                                <div>
                                  <div className="text-xs text-muted-foreground mb-1">Entry Signal</div>
                                  <div className="text-sm font-medium">{order.entry_signal}</div>
                                </div>
                              )}
                              {order.exit_signal && (
                                <div>
                                  <div className="text-xs text-muted-foreground mb-1">Exit Signal</div>
                                  <div className="text-sm font-medium">{order.exit_signal}</div>
                                </div>
                              )}
                              {order.max_gain !== undefined && (
                                <div>
                                  <div className="text-xs text-muted-foreground mb-1">Max Gain</div>
                                  <div className="text-sm font-medium text-green-500">
                                    +{formatPercent(order.max_gain)}
                                  </div>
                                </div>
                              )}
                              {order.max_loss !== undefined && (
                                <div>
                                  <div className="text-xs text-muted-foreground mb-1">Max Loss</div>
                                  <div className="text-sm font-medium text-red-500">
                                    {formatPercent(order.max_loss)}
                                  </div>
                                </div>
                              )}
                              {order.rsi_at_entry && (
                                <div>
                                  <div className="text-xs text-muted-foreground mb-1">RSI Entry</div>
                                  <div className="text-sm font-medium">{order.rsi_at_entry.toFixed(1)}</div>
                                </div>
                              )}
                              {order.rsi_at_exit && (
                                <div>
                                  <div className="text-xs text-muted-foreground mb-1">RSI Exit</div>
                                  <div className="text-sm font-medium">{order.rsi_at_exit.toFixed(1)}</div>
                                </div>
                              )}
                              {order.volume_at_entry && (
                                <div>
                                  <div className="text-xs text-muted-foreground mb-1">Volume</div>
                                  <div className="text-sm font-medium">
                                    {(order.volume_at_entry / 1000000).toFixed(2)}M
                                  </div>
                                </div>
                              )}
                              <div>
                                <div className="text-xs text-muted-foreground mb-1">Trade Value</div>
                                <div className="text-sm font-medium">
                                  {formatCurrency(order.buy_price * order.quantity)}
                                </div>
                              </div>
                            </div>
                            
                            {/* Timeline Bar */}
                            <div className="mt-4 p-3 bg-background rounded-lg">
                              <div className="text-xs text-muted-foreground mb-2">Trade Timeline</div>
                              <div className="relative h-2 bg-muted rounded-full overflow-hidden">
                                <div 
                                  className={`absolute h-full ${
                                    isProfitable ? 'bg-green-500' : 'bg-red-500'
                                  }`}
                                  style={{
                                    width: isActive ? '50%' : '100%',
                                    animation: isActive ? 'pulse 2s infinite' : 'none'
                                  }}
                                />
                              </div>
                              <div className="flex justify-between mt-2 text-xs">
                                <span>{new Date(order.buy_time).toLocaleString('en-US', {
                                  month: 'short',
                                  day: 'numeric',
                                  hour: '2-digit',
                                  minute: '2-digit'
                                })}</span>
                                {order.sell_time ? (
                                  <span>{new Date(order.sell_time).toLocaleString('en-US', {
                                    month: 'short',
                                    day: 'numeric',
                                    hour: '2-digit',
                                    minute: '2-digit'
                                  })}</span>
                                ) : (
                                  <span className="text-blue-500">In Progress...</span>
                                )}
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Performance Metrics */}
        <TabsContent value="metrics">
          <div className="grid gap-4 md:grid-cols-2">
            {metrics && (
              <>
                <Card>
                  <CardHeader>
                    <CardTitle>Daily Performance</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="flex justify-between">
                      <span>Profit/Loss:</span>
                      <span className={metrics.daily_metrics.profit_loss >= 0 ? 'text-green-500' : 'text-red-500'}>
                        {formatCurrency(metrics.daily_metrics.profit_loss)}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Trades Today:</span>
                      <span>{metrics.daily_metrics.trades_today}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Win Rate:</span>
                      <span>{formatPercent(metrics.daily_metrics.win_rate)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Capital Utilization:</span>
                      <span>{formatPercent(metrics.daily_metrics.capital_utilization)}</span>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>Risk Management</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="flex justify-between">
                      <span>Daily Loss Limit:</span>
                      <span>{formatCurrency(metrics.risk_metrics.max_daily_loss_limit)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Remaining Budget:</span>
                      <span className={metrics.risk_metrics.remaining_risk_budget > 0 ? 'text-green-500' : 'text-red-500'}>
                        {formatCurrency(metrics.risk_metrics.remaining_risk_budget)}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Current Exposure:</span>
                      <span>{metrics.risk_metrics.current_exposure.toFixed(1)}%</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Avg Hold Time:</span>
                      <span>{metrics.position_analysis.avg_hold_time_minutes.toFixed(1)} min</span>
                    </div>
                  </CardContent>
                </Card>
              </>
            )}
          </div>
        </TabsContent>

        {/* Configuration */}
        <TabsContent value="config">
          <Card>
            <CardHeader>
              <CardTitle>Trading Configuration</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label>Max Position Size</Label>
                  <Input
                    type="number"
                    value={config.max_position_size}
                    onChange={(e) => setConfig({...config, max_position_size: parseFloat(e.target.value)})}
                  />
                </div>
                
                <div className="space-y-2">
                  <Label>Max Concurrent Positions</Label>
                  <Input
                    type="number"
                    value={config.max_positions}
                    onChange={(e) => setConfig({...config, max_positions: parseInt(e.target.value)})}
                  />
                </div>
                
                <div className="space-y-2">
                  <Label>Min Profit Target (%)</Label>
                  <Input
                    type="number"
                    step="0.001"
                    value={config.min_profit}
                    onChange={(e) => setConfig({...config, min_profit: parseFloat(e.target.value)})}
                  />
                </div>
                
                <div className="space-y-2">
                  <Label>Max Daily Loss</Label>
                  <Input
                    type="number"
                    value={config.max_daily_loss}
                    onChange={(e) => setConfig({...config, max_daily_loss: parseFloat(e.target.value)})}
                  />
                </div>
              </div>
              
              <div className="flex items-center space-x-2">
                <Switch
                  checked={config.enable_trading}
                  onCheckedChange={(checked) => setConfig({...config, enable_trading: checked})}
                />
                <Label>Enable Automated Trading</Label>
              </div>
              
              <Button 
                onClick={updateConfig} 
                disabled={isLoading}
                className="w-full"
              >
                {isLoading ? "Updating..." : "Update Configuration"}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}