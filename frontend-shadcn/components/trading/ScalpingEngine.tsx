"use client"

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { formatCurrency, formatPercent } from '@/lib/utils'
import { 
  Zap, TrendingUp, TrendingDown, Clock, Target,
  Activity, BarChart3, RefreshCw, Play, Pause
} from 'lucide-react'
import { MarketMode } from '@/lib/api/client'
import { useTradingContext } from '@/contexts/TradingContext'

interface ScalpingSignal {
  id: string
  symbol: string
  direction: 'BUY' | 'SELL'
  entry_price: number
  target_price: number
  stop_price: number
  profit_target: number // in percentage (0.1-0.5%)
  confidence: number
  timestamp: string
  reason: string
  timeframe: '15s' | '1m' | '5m'
}

// Remove local ScalpingMetrics interface - now using from context

interface ScalpingEngineProps {
  marketType: MarketMode
  selectedSymbol: string
  isActive: boolean
  onToggleActive: () => void
  onExecuteSignal?: (signal: ScalpingSignal) => void
}

export function ScalpingEngine({
  marketType,
  selectedSymbol,
  isActive,
  onToggleActive,
  onExecuteSignal
}: ScalpingEngineProps) {
  const { metrics, isLoading } = useTradingContext()
  const [signals, setSignals] = useState<ScalpingSignal[]>([])
  const [lastSignalTime, setLastSignalTime] = useState<Date | null>(null)

  // Generate rapid scalping signals
  const generateScalpingSignal = (): ScalpingSignal | null => {
    // Simulate rapid price movements and volume spikes
    const basePrice = 45000 + Math.random() * 10000 // Mock price
    const volatility = 0.001 + Math.random() * 0.004 // 0.1-0.5% volatility
    const direction = Math.random() > 0.5 ? 'BUY' : 'SELL'
    
    // Very small profit targets for scalping
    const profitTarget = 0.001 + Math.random() * 0.004 // 0.1-0.5%
    const stopLoss = 0.0005 + Math.random() * 0.002 // 0.05-0.25%
    
    const entryPrice = basePrice * (1 + (Math.random() - 0.5) * 0.002)
    const targetPrice = direction === 'BUY' 
      ? entryPrice * (1 + profitTarget)
      : entryPrice * (1 - profitTarget)
    const stopPrice = direction === 'BUY'
      ? entryPrice * (1 - stopLoss)
      : entryPrice * (1 + stopLoss)

    // Scalping reasons (simple and fast)
    const reasons = [
      'Volume spike detected',
      'Price momentum shift',
      'Quick bounce off support',
      'Rapid breakout pattern',
      'Micro trend reversal',
      'Volatility expansion',
      'Order flow imbalance',
      'Fast EMA cross'
    ]

    return {
      id: `scalp_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      symbol: selectedSymbol,
      direction,
      entry_price: entryPrice,
      target_price: targetPrice,
      stop_price: stopPrice,
      profit_target: profitTarget * 100,
      confidence: 0.6 + Math.random() * 0.3, // 60-90% confidence
      timestamp: new Date().toISOString(),
      reason: reasons[Math.floor(Math.random() * reasons.length)],
      timeframe: ['15s', '1m', '5m'][Math.floor(Math.random() * 3)] as '15s' | '1m' | '5m'
    }
  }

  // Metrics now come from unified context - no need to mock them

  // Rapid signal generation (every 5-15 seconds when active)
  useEffect(() => {
    if (!isActive) return

    const generateSignals = () => {
      // Generate 1-3 signals rapidly
      const numSignals = 1 + Math.floor(Math.random() * 3)
      const newSignals: ScalpingSignal[] = []

      for (let i = 0; i < numSignals; i++) {
        const signal = generateScalpingSignal()
        if (signal) {
          newSignals.push(signal)
        }
      }

      if (newSignals.length > 0) {
        setSignals(prev => [...newSignals, ...prev].slice(0, 10)) // Keep latest 10
        setLastSignalTime(new Date())
      }
    }

    // Initial signal
    generateSignals()

    // Rapid signal generation every 5-15 seconds
    const signalInterval = setInterval(() => {
      if (Math.random() > 0.3) { // 70% chance to generate signal
        generateSignals()
      }
    }, 5000 + Math.random() * 10000) // 5-15 second intervals

    return () => clearInterval(signalInterval)
  }, [isActive, selectedSymbol])

  // Metrics auto-update from context - no manual updates needed

  return (
    <Card className="w-full">
      <CardHeader className="flex flex-row items-center space-y-0 pb-2">
        <div className="flex items-center space-x-2">
          <Zap className={`h-4 w-4 ${isActive ? 'text-green-500 animate-pulse' : 'text-gray-400'}`} />
          <CardTitle className="text-base">
            High-Frequency Scalping Engine
          </CardTitle>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <Badge variant={isActive ? "default" : "secondary"} className="animate-pulse">
            {isActive ? 'ACTIVE' : 'PAUSED'}
          </Badge>
          <Button
            variant={isActive ? "destructive" : "default"}
            size="sm"
            onClick={onToggleActive}
          >
            {isActive ? <Pause className="h-3 w-3 mr-1" /> : <Play className="h-3 w-3 mr-1" />}
            {isActive ? 'Pause' : 'Start'}
          </Button>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Scalping Metrics Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 p-3 bg-gradient-to-r from-green-500/10 to-blue-500/10 rounded-lg">
          <div className="text-center">
            <div className="text-lg font-bold text-green-600">
              {metrics.trades_per_hour}
            </div>
            <div className="text-xs text-muted-foreground">Trades/Hour</div>
          </div>
          <div className="text-center">
            <div className="text-lg font-bold text-blue-600">
              {formatPercent(metrics.win_rate)}
            </div>
            <div className="text-xs text-muted-foreground">Win Rate</div>
          </div>
          <div className="text-center">
            <div className="text-lg font-bold text-purple-600">
              {formatCurrency(metrics.avg_profit_per_trade)}
            </div>
            <div className="text-xs text-muted-foreground">Avg Profit</div>
          </div>
          <div className="text-center">
            <div className="text-lg font-bold text-orange-600">
              {metrics.avg_trade_duration}
            </div>
            <div className="text-xs text-muted-foreground">Avg Duration</div>
          </div>
        </div>

        {/* Daily Stats */}
        <div className="flex items-center justify-between p-2 bg-muted/30 rounded text-xs">
          <span>Today: <strong>{metrics.total_trades_today}</strong> trades</span>
          <span>Current Streak: <strong>{metrics.current_streak}</strong></span>
          <span>Best Streak: <strong>{metrics.best_streak}</strong></span>
          {lastSignalTime && (
            <span>Last Signal: <strong>{Math.floor((Date.now() - lastSignalTime.getTime()) / 1000)}s</strong> ago</span>
          )}
        </div>

        {/* Signals hidden but still processing in background */}
        {false && (
          <div className="space-y-2 max-h-80 overflow-y-auto">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold flex items-center gap-1">
                <Activity className="h-3 w-3" />
                Live Scalping Signals ({signals.length})
              </h3>
              <Badge variant="outline" className="text-xs">
                Target: 0.1-0.5% per trade
              </Badge>
            </div>

            {signals.length === 0 ? (
              <div className="text-center py-6 text-muted-foreground">
                {isActive ? (
                  <div className="flex items-center justify-center space-x-2">
                    <RefreshCw className="h-4 w-4 animate-spin" />
                    <span>Scanning for scalping opportunities...</span>
                  </div>
                ) : (
                  'Start the engine to see rapid scalping signals'
                )}
              </div>
            ) : (
              signals.map((signal) => (
              <div
                key={signal.id}
                className={`flex items-center justify-between p-3 rounded-lg border transition-all ${
                  signal.direction === 'BUY' 
                    ? 'bg-green-500/5 border-green-500/20' 
                    : 'bg-red-500/5 border-red-500/20'
                } hover:bg-opacity-20 cursor-pointer`}
                onClick={() => onExecuteSignal?.(signal)}
              >
                {/* Left: Direction and Symbol */}
                <div className="flex items-center space-x-2">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold text-white ${
                    signal.direction === 'BUY' ? 'bg-green-500' : 'bg-red-500'
                  }`}>
                    {signal.direction === 'BUY' ? '↑' : '↓'}
                  </div>
                  <div>
                    <div className="font-semibold text-sm">{signal.symbol}</div>
                    <div className="text-xs text-muted-foreground">{signal.timeframe}</div>
                  </div>
                </div>

                {/* Center: Prices and Targets */}
                <div className="text-center">
                  <div className="text-sm font-medium">
                    {formatCurrency(signal.entry_price)}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Target: {formatPercent(signal.profit_target / 100)}
                  </div>
                </div>

                {/* Right: Confidence and Reason */}
                <div className="text-right">
                  <Badge variant="outline" className="text-xs mb-1">
                    {Math.round(signal.confidence * 100)}%
                  </Badge>
                  <div className="text-xs text-muted-foreground max-w-20 truncate">
                    {signal.reason}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
        )}

        {/* Scalping Strategy Info */}
        <div className="mt-4 p-3 bg-gradient-to-r from-yellow-500/10 to-orange-500/10 rounded-lg border border-yellow-500/20">
          <div className="text-sm font-semibold text-yellow-700 mb-1">⚡ Scalping Strategy Active</div>
          <div className="text-xs text-muted-foreground space-y-1">
            <p>• <strong>Profit Targets:</strong> 0.1-0.5% per trade</p>
            <p>• <strong>Stop Loss:</strong> 0.05-0.25% risk</p>
            <p>• <strong>Trade Frequency:</strong> 15-40 trades per hour</p>
            <p>• <strong>Hold Time:</strong> 30 seconds to 3 minutes</p>
            <p>• <strong>Focus:</strong> Rapid entries on volume spikes & momentum</p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}