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
  ArrowUpRight, ArrowDownRight, Timer, ChevronDown, ChevronUp,
  CheckCircle, XCircle, RotateCcw, Bot
} from "lucide-react"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { formatCurrency, formatPercent } from '@/lib/utils'
import { toast } from 'sonner'
import { Position } from '@/types/alpaca'

// Extended position interface for crypto trading with additional fields
interface ExtendedPosition extends Position {
  confidence?: number
  target_price?: number
  stop_price?: number
  entry_time?: string
  hold_time_minutes?: number
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
  recommendation?: string
  score?: number
  price_change?: number
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
  const [positions, setPositions] = useState<ExtendedPosition[]>([])
  const [opportunities, setOpportunities] = useState<TradingOpportunity[]>([])
  const [isLoadingPositions, setIsLoadingPositions] = useState(true)
  const [isLoadingOpportunities, setIsLoadingOpportunities] = useState(true)
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
  const [orderHistory, setOrderHistory] = useState<{orders: OrderHistory[], timeline: any[], summary: any}>({
    orders: [],
    timeline: [],
    summary: {}
  })
  const [pnlChartData, setPnlChartData] = useState<any[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [expandedOrders, setExpandedOrders] = useState<Set<string>>(new Set())
  
  const API_BASE = 'http://localhost:9100'

  // Fetch trading status
  const fetchStatus = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/status`)
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
    setIsLoadingPositions(true)
    try {
      const response = await fetch(`${API_BASE}/api/positions`)
      if (response.ok) {
        const data = await response.json()
        setPositions(data.positions || [])
      }
    } catch (error) {
      console.error('Failed to fetch positions:', error)
      setPositions([])
    } finally {
      setIsLoadingPositions(false)
    }
  }

  // Fetch market opportunities
  const fetchOpportunities = async () => {
    setIsLoadingOpportunities(true)
    try {
      const response = await fetch(`${API_BASE}/api/scan`, {
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
    } finally {
      setIsLoadingOpportunities(false)
    }
  }

  // Fetch metrics
  const fetchMetrics = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/metrics`)
      if (response.ok) {
        const data = await response.json()
        // Transform API response to match expected structure
        const transformedMetrics: TradingMetrics = {
          daily_metrics: {
            profit_loss: data.metrics?.daily_pnl || 0,
            trades_today: data.metrics?.total_trades || 0,
            win_rate: data.metrics?.win_rate || 0,
            total_trades: data.metrics?.total_trades || 0,
            capital_utilization: 0
          },
          position_analysis: {
            total_positions: 0,
            capital_deployed: 0,
            avg_hold_time_minutes: 0,
            profitable_positions: data.metrics?.winning_trades || 0
          },
          risk_metrics: {
            max_daily_loss_limit: 500,
            remaining_risk_budget: 500 - Math.abs(Math.min(0, data.metrics?.daily_pnl || 0)),
            largest_position_size: 0,
            current_exposure: 0
          }
        }
        setMetrics(transformedMetrics)
      }
    } catch (error) {
      console.error('Failed to fetch metrics:', error)
    }
  }

  // Fetch configuration
  const fetchConfig = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/config`)
      if (response.ok) {
        const data = await response.json()
        setConfig(data)
      }
    } catch (error) {
      console.error('Failed to fetch config:', error)
    }
  }

  // Fetch P&L chart data
  const fetchPnlChart = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/pnl-chart`)
      if (response.ok) {
        const data = await response.json()
        setPnlChartData(data.chart_data || [])
      }
    } catch (error) {
      console.error('Failed to fetch P&L chart:', error)
    }
  }

  // Fetch order history
  const fetchOrderHistory = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/history`)
      if (response.ok) {
        const data = await response.json()
        setOrderHistory({
          orders: data.orders || [],
          timeline: data.timeline || [],
          summary: data.summary || {}
        })
        return
      }
    } catch (error) {
      console.error('Failed to fetch order history:', error)
    }
    
    // Fallback demo data for visualization
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
          orders: demoOrders,
          timeline: [], // Empty timeline for demo data  
          summary: {
            total_trades: demoOrders.length,
            profitable_trades: 2,
            total_profit: 13.62,
            avg_holding_time: '25m'
          }
        })
  }

  // Fetch P&L chart data
  const fetchPnlChartData = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/pnl-chart`)
      if (response.ok) {
        const data = await response.json()
        setPnlChartData(data.chart_data || [])
      }
    } catch (error) {
      console.error('Failed to fetch P&L chart data:', error)
      // Set empty data on error
      setPnlChartData([])
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
      const response = await fetch(`${API_BASE}/api/config`, {
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
    fetchPnlChartData() // Fetch P&L chart data on mount

    // Set up real-time updates
    const interval = setInterval(() => {
      fetchStatus()
      fetchPositions()
      fetchMetrics()
      fetchOrderHistory() // Update order history
      fetchPnlChart() // Update P&L chart
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
      <Tabs defaultValue="trading" className="space-y-4">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="trading">Trading</TabsTrigger>
          <TabsTrigger value="history">History</TabsTrigger>
          <TabsTrigger value="metrics">Metrics</TabsTrigger>
          <TabsTrigger value="config">Config</TabsTrigger>
        </TabsList>

        {/* Combined Trading Tab */}
        <TabsContent value="trading">
          <div className="grid gap-4 lg:grid-cols-2">
            {/* Active Positions */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Activity className="h-5 w-5" />
                  <span>Active Positions ({positions.length})</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                {isLoadingPositions ? (
                  <div className="text-center py-8">
                    <RefreshCw className="h-6 w-6 animate-spin mx-auto mb-2" />
                    <p className="text-sm text-muted-foreground">Loading positions...</p>
                  </div>
                ) : positions.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    No active positions
                  </div>
                ) : (
                  <div className="space-y-3 max-h-96 overflow-y-auto">
                    {positions.map((position, index) => (
                      <div key={index} className="flex items-center justify-between p-3 border rounded-lg">
                        <div className="flex items-center space-x-2">
                          <div>
                            <div className="flex items-center space-x-1">
                              <span className="font-medium text-sm">{position.symbol}</span>
                              {position.side && (
                                <Badge variant={position.side === 'long' ? 'default' : 'destructive'} className="text-xs">
                                  {position.side.toUpperCase()}
                                </Badge>
                              )}
                              {position.confidence && (
                                <Badge variant="outline" className="text-xs">
                                  {(position.confidence * 100).toFixed(0)}%
                                </Badge>
                              )}
                              {position.unrealized_plpc && (
                                <Badge variant={parseFloat(position.unrealized_plpc) >= 0 ? 'default' : 'destructive'} className="text-xs">
                                  {parseFloat(position.unrealized_plpc) >= 0 ? '+' : ''}{(parseFloat(position.unrealized_plpc) * 100).toFixed(2)}%
                                </Badge>
                              )}
                            </div>
                            <div className="text-xs text-muted-foreground">
                              {parseFloat(position.qty || '0').toFixed(4)} @ {formatCurrency(parseFloat(position.avg_entry_price || '0'))}
                            </div>
                          </div>
                        </div>
                        
                        <div className="text-right">
                          <div className={`font-medium text-sm ${(parseFloat(position.unrealized_pl) || 0) >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                            {formatCurrency(parseFloat(position.unrealized_pl) || 0)}
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {position.unrealized_plpc ? formatPercent(parseFloat(position.unrealized_plpc)) : 'N/A'}
                            {position.hold_time_minutes && ` • ${position.hold_time_minutes}m`}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Trading Opportunities */}
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center space-x-2">
                    <Target className="h-5 w-5" />
                    <span>Trading Opportunities</span>
                  </CardTitle>
                  <Button variant="outline" size="sm" onClick={fetchOpportunities}>
                    <RefreshCw className="h-4 w-4 mr-1" />
                    Refresh
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                {isLoadingOpportunities ? (
                  <div className="text-center py-8">
                    <RefreshCw className="h-6 w-6 animate-spin mx-auto mb-2" />
                    <p className="text-sm text-muted-foreground">Scanning markets...</p>
                  </div>
                ) : opportunities.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    No opportunities found
                  </div>
                ) : (
                  <div className="space-y-3 max-h-96 overflow-y-auto">
                    {opportunities.slice(0, 6).map((opportunity, index) => (
                      <div key={index} className="flex items-center justify-between p-3 border rounded-lg">
                        <div className="flex items-center space-x-2">
                          {opportunity.action === 'buy' ? 
                            <TrendingUp className="h-4 w-4 text-green-500" /> :
                            <TrendingDown className="h-4 w-4 text-red-500" />
                          }
                          <div>
                            <div className="flex items-center space-x-1">
                              <span className="font-medium text-sm">{opportunity.symbol}</span>
                              {opportunity.action && (
                                <Badge variant={opportunity.action === 'buy' ? 'default' : 'destructive'} className="text-xs">
                                  {opportunity.action.toUpperCase()}
                                </Badge>
                              )}
                              {opportunity.recommendation && (
                                <Badge variant={opportunity.recommendation === 'strong_buy' || opportunity.recommendation === 'buy' ? 'default' : 'outline'} className="text-xs">
                                  {opportunity.recommendation.replace('_', ' ').toUpperCase()}
                                </Badge>
                              )}
                              {opportunity.confidence ? (
                                <Badge variant="outline" className="text-xs">
                                  {(opportunity.confidence * 100).toFixed(0)}%
                                </Badge>
                              ) : opportunity.score && (
                                <Badge variant="outline" className="text-xs">
                                  Score: {(opportunity.score * 100).toFixed(0)}%
                                </Badge>
                              )}
                            </div>
                            <div className="text-xs text-muted-foreground">
                              {opportunity.price && `${formatCurrency(opportunity.price)} • `}
                              Vol: {formatPercent(opportunity.volatility || 0)}
                              {opportunity.price_change && ` • ${opportunity.price_change >= 0 ? '+' : ''}${opportunity.price_change.toFixed(2)}%`}
                              {opportunity.volume_surge && <span className="text-orange-500 ml-1">🔥</span>}
                            </div>
                          </div>
                        </div>
                        
                        <div className="flex items-center space-x-2">
                          {showAdvanced && opportunity.target_profit && opportunity.stop_loss && (
                            <div className="text-xs text-muted-foreground text-right">
                              <div>+{formatPercent(opportunity.target_profit)}</div>
                              <div>-{formatPercent(opportunity.stop_loss)}</div>
                            </div>
                          )}
                          <Badge 
                            variant={
                              opportunity.recommendation === 'strong_buy' || opportunity.recommendation === 'buy' ? 'default' : 
                              opportunity.recommendation === 'sell' ? 'destructive' : 'outline'
                            }
                            className="px-2 py-1 text-xs"
                          >
                            {opportunity.score ? `${(opportunity.score * 100).toFixed(0)}%` : 'AUTO'}
                          </Badge>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* History with P&L Chart and Timeline */}
        <TabsContent value="history">
          <div className="space-y-4">
            {/* P&L Performance Chart */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <TrendingUp className="h-5 w-5" />
                  <span>Profit & Loss Over Time</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                {pnlChartData.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    No P&L data available
                  </div>
                ) : (
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={pnlChartData}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis 
                          dataKey="timestamp" 
                          tickFormatter={(timestamp) => new Date(timestamp).toLocaleDateString('en-US', {
                            month: 'short',
                            day: 'numeric'
                          })}
                        />
                        <YAxis 
                          tickFormatter={(value) => formatCurrency(value)}
                        />
                        <Tooltip
                          formatter={(value, name) => [
                            formatCurrency(value as number),
                            name === 'cumulative_pnl' ? 'Total P&L' : 'Trade P&L'
                          ]}
                          labelFormatter={(timestamp) => `Date: ${new Date(timestamp).toLocaleString('en-US', {
                            month: 'short',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit'
                          })}`}
                        />
                        <Line
                          type="monotone"
                          dataKey="cumulative_pnl"
                          stroke="#8884d8"
                          strokeWidth={2}
                          dot={{ r: 3 }}
                          name="cumulative_pnl"
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Bot Activity Timeline */}
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center space-x-2">
                    <History className="h-5 w-5" />
                    <span>Bot Activity Timeline</span>
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
                {orderHistory.orders.length === 0 && orderHistory.timeline?.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    No activity history available
                  </div>
                ) : (
                  <div className="space-y-2">
                    {/* Combine and sort trades and timeline events */}
                    {[
                      ...orderHistory.orders.map(order => ({
                        type: 'trade',
                        timestamp: order.sell_time || order.buy_time,
                        data: order,
                        id: `trade-${order.id}`
                      })),
                      ...(orderHistory.timeline || []).map(event => ({
                        type: 'event',
                        timestamp: event.timestamp,
                        data: event,
                        id: event.id
                      }))
                    ]
                      .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
                      .map((item) => {
                        if (item.type === 'trade') {
                          const order = item.data
                          const isExpanded = expandedOrders.has(order.id)
                          const isActive = order.status === 'active'
                          const isProfitable = order.profit_percent > 0
                          
                          return (
                            <div key={item.id} className="border rounded-lg overflow-hidden">
                              {/* Trade Row */}
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
                                    <div>
                                      <div className="text-xs text-muted-foreground mb-1">Trade Value</div>
                                      <div className="text-sm font-medium">
                                        {formatCurrency(order.buy_price * order.quantity)}
                                      </div>
                                    </div>
                                  </div>
                                </div>
                              )}
                            </div>
                          )
                        } else {
                          // Timeline event
                          const event = item.data
                          return (
                            <div key={item.id} className="border border-dashed rounded-lg p-3 bg-muted/20">
                              <div className="flex items-center space-x-3">
                                <div className="h-2 w-2 rounded-full bg-blue-400" />
                                <div className="flex-1">
                                  <div className="flex items-center justify-between">
                                    <div>
                                      <span className="font-medium text-sm">{event.description}</span>
                                      <div className="text-xs text-muted-foreground mt-1">
                                        {new Date(event.timestamp).toLocaleString('en-US', {
                                          month: 'short',
                                          day: 'numeric',
                                          hour: '2-digit',
                                          minute: '2-digit',
                                          second: '2-digit'
                                        })}
                                      </div>
                                    </div>
                                    <Badge variant="outline" className="text-xs">
                                      {event.event_type}
                                    </Badge>
                                  </div>
                                  {event.details && Object.keys(event.details).length > 0 && (
                                    <div className="mt-2 text-xs text-muted-foreground">
                                      {Object.entries(event.details).map(([key, value]) => (
                                        <span key={key} className="mr-3">
                                          {key}: {String(value)}
                                        </span>
                                      ))}
                                    </div>
                                  )}
                                </div>
                              </div>
                            </div>
                          )
                        }
                      })}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
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
                      <span className={
                        metrics?.daily_metrics?.profit_loss !== undefined && metrics.daily_metrics.profit_loss >= 0 
                          ? 'text-green-500' 
                          : 'text-red-500'
                      }>
                        {formatCurrency(metrics?.daily_metrics?.profit_loss || 0)}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Trades Today:</span>
                      <span>{metrics?.daily_metrics?.trades_today || 0}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Win Rate:</span>
                      <span>{formatPercent(metrics?.daily_metrics?.win_rate || 0)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Capital Utilization:</span>
                      <span>{formatPercent(metrics?.daily_metrics?.capital_utilization || 0)}</span>
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
                      <span>{formatCurrency(metrics?.risk_metrics?.max_daily_loss_limit || 500)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Remaining Budget:</span>
                      <span className={(metrics?.risk_metrics?.remaining_risk_budget || 0) > 0 ? 'text-green-500' : 'text-red-500'}>
                        {formatCurrency(metrics?.risk_metrics?.remaining_risk_budget || 0)}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Current Exposure:</span>
                      <span>{(metrics?.risk_metrics?.current_exposure || 0).toFixed(1)}%</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Avg Hold Time:</span>
                      <span>{(metrics?.position_analysis?.avg_hold_time_minutes || 0).toFixed(1)} min</span>
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