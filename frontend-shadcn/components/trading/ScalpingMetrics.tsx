"use client"

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Separator } from "@/components/ui/separator"
import { 
  Zap, TrendingUp, Clock, Target, Activity, 
  DollarSign, Percent, BarChart3, Timer,
  Flame, Trophy, TrendingDown
} from "lucide-react"
import { formatCurrency, formatPercent } from '@/lib/utils'

interface ScalpingMetricsProps {
  isActive: boolean
  selectedSymbol: string
}

interface ScalpingStats {
  tradesPerHour: number
  avgHoldTime: string
  winRate: number
  avgProfitPerTrade: number
  totalTradesCount: number
  currentStreak: number
  bestStreak: number
  dailyPnL: number
  sessionPnL: number
  sharpeRatio: number
  maxDrawdown: number
  profitFactor: number
}

export function ScalpingMetrics({ isActive, selectedSymbol }: ScalpingMetricsProps) {
  const [metrics, setMetrics] = useState<ScalpingStats>({
    tradesPerHour: 0,
    avgHoldTime: "0m 0s",
    winRate: 0,
    avgProfitPerTrade: 0,
    totalTradesCount: 0,
    currentStreak: 0,
    bestStreak: 0,
    dailyPnL: 0,
    sessionPnL: 0,
    sharpeRatio: 0,
    maxDrawdown: 0,
    profitFactor: 0
  })

  const [liveMetrics, setLiveMetrics] = useState({
    tradesInLastHour: 0,
    avgExecutionTime: 120,
    lastTradeTime: null as Date | null,
    activeTime: 0 // minutes
  })

  // Simulate real-time metrics updates
  useEffect(() => {
    if (!isActive) return

    const interval = setInterval(() => {
      // Simulate scalping activity metrics
      setMetrics(prev => ({
        ...prev,
        tradesPerHour: 25 + Math.floor(Math.random() * 30), // 25-55 trades/hour
        avgHoldTime: `${Math.floor(Math.random() * 3)}m ${Math.floor(Math.random() * 60)}s`,
        winRate: 0.65 + Math.random() * 0.2, // 65-85% win rate
        avgProfitPerTrade: 2.5 + Math.random() * 5, // $2.5-7.5 avg profit
        totalTradesCount: prev.totalTradesCount + (Math.random() > 0.7 ? 1 : 0),
        currentStreak: Math.floor(Math.random() * 10) - 2, // -2 to +7
        bestStreak: Math.max(prev.bestStreak, Math.floor(Math.random() * 15)),
        dailyPnL: -50 + Math.random() * 200, // -$50 to +$150
        sessionPnL: prev.sessionPnL + (Math.random() - 0.4) * 10, // Slight upward bias
        sharpeRatio: 1.5 + Math.random() * 1.5, // 1.5-3.0
        maxDrawdown: -(Math.random() * 5), // 0-5% drawdown
        profitFactor: 1.1 + Math.random() * 0.8 // 1.1-1.9
      }))

      setLiveMetrics(prev => ({
        ...prev,
        tradesInLastHour: Math.floor(Math.random() * 45),
        avgExecutionTime: 80 + Math.random() * 200, // 80-280ms
        activeTime: prev.activeTime + 0.05 // 3 seconds in minutes
      }))
    }, 3000) // Update every 3 seconds

    return () => clearInterval(interval)
  }, [isActive])

  const getMetricColor = (value: number, thresholds: { good: number; excellent: number }) => {
    if (value >= thresholds.excellent) return "text-green-600"
    if (value >= thresholds.good) return "text-yellow-600"
    return "text-red-600"
  }

  return (
    <Card className="border-2 border-orange-500/20">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-base">
            <Zap className={`h-4 w-4 ${isActive ? 'text-orange-500 animate-pulse' : 'text-gray-400'}`} />
            Scalping Performance
          </CardTitle>
          <div className="flex items-center gap-2">
            <Badge variant={isActive ? "default" : "secondary"} className={isActive ? "animate-pulse" : ""}>
              {isActive ? "ACTIVE" : "PAUSED"}
            </Badge>
            {isActive && (
              <Badge variant="outline" className="text-xs">
                <Flame className="mr-1 h-3 w-3" />
                {Math.floor(liveMetrics.activeTime)}m
              </Badge>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        
        {/* Core Scalping Metrics */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="text-center p-2 bg-gradient-to-b from-green-500/10 to-green-500/5 rounded">
            <div className={`text-lg font-bold ${getMetricColor(metrics.tradesPerHour, { good: 20, excellent: 40 })}`}>
              {metrics.tradesPerHour}
            </div>
            <div className="text-xs text-muted-foreground">Trades/Hour</div>
          </div>
          
          <div className="text-center p-2 bg-gradient-to-b from-blue-500/10 to-blue-500/5 rounded">
            <div className={`text-lg font-bold ${getMetricColor(metrics.winRate * 100, { good: 60, excellent: 75 })}`}>
              {formatPercent(metrics.winRate)}
            </div>
            <div className="text-xs text-muted-foreground">Win Rate</div>
          </div>
          
          <div className="text-center p-2 bg-gradient-to-b from-purple-500/10 to-purple-500/5 rounded">
            <div className="text-lg font-bold text-purple-600">
              {formatCurrency(metrics.avgProfitPerTrade)}
            </div>
            <div className="text-xs text-muted-foreground">Avg Profit</div>
          </div>
          
          <div className="text-center p-2 bg-gradient-to-b from-orange-500/10 to-orange-500/5 rounded">
            <div className="text-lg font-bold text-orange-600">
              {metrics.avgHoldTime}
            </div>
            <div className="text-xs text-muted-foreground">Avg Hold</div>
          </div>
        </div>

        <Separator />

        {/* Performance Stats */}
        <div className="space-y-3">
          <div className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-muted-foreground" />
              <span>Session P&L</span>
            </div>
            <div className={`font-mono font-bold ${
              metrics.sessionPnL >= 0 ? 'text-green-500' : 'text-red-500'
            }`}>
              {metrics.sessionPnL >= 0 ? '+' : ''}{formatCurrency(metrics.sessionPnL)}
            </div>
          </div>

          <div className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-2">
              <DollarSign className="h-4 w-4 text-muted-foreground" />
              <span>Daily P&L</span>
            </div>
            <div className={`font-mono font-bold ${
              metrics.dailyPnL >= 0 ? 'text-green-500' : 'text-red-500'
            }`}>
              {metrics.dailyPnL >= 0 ? '+' : ''}{formatCurrency(metrics.dailyPnL)}
            </div>
          </div>

          <div className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-2">
              <Trophy className="h-4 w-4 text-muted-foreground" />
              <span>Current Streak</span>
            </div>
            <div className={`font-bold ${
              metrics.currentStreak > 0 ? 'text-green-500' : 
              metrics.currentStreak < 0 ? 'text-red-500' : 'text-muted-foreground'
            }`}>
              {metrics.currentStreak > 0 ? `+${metrics.currentStreak}` : metrics.currentStreak} 
              <span className="text-xs text-muted-foreground ml-1">
                (Best: {metrics.bestStreak})
              </span>
            </div>
          </div>

          <div className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-muted-foreground" />
              <span>Total Trades</span>
            </div>
            <div className="font-mono">
              {metrics.totalTradesCount}
            </div>
          </div>
        </div>

        <Separator />

        {/* Advanced Metrics */}
        <div className="grid grid-cols-3 gap-3 text-xs">
          <div className="text-center">
            <p className="text-muted-foreground">Sharpe Ratio</p>
            <p className={`font-bold ${getMetricColor(metrics.sharpeRatio, { good: 1, excellent: 2 })}`}>
              {metrics.sharpeRatio.toFixed(2)}
            </p>
          </div>
          
          <div className="text-center">
            <p className="text-muted-foreground">Profit Factor</p>
            <p className={`font-bold ${getMetricColor(metrics.profitFactor, { good: 1.2, excellent: 1.5 })}`}>
              {metrics.profitFactor.toFixed(2)}
            </p>
          </div>
          
          <div className="text-center">
            <p className="text-muted-foreground">Max Drawdown</p>
            <p className="font-bold text-red-600">
              {formatPercent(Math.abs(metrics.maxDrawdown) / 100)}
            </p>
          </div>
        </div>

        {/* Live Activity Indicator */}
        {isActive && (
          <>
            <Separator />
            <div className="p-2 bg-gradient-to-r from-orange-500/10 to-red-500/10 rounded border border-orange-500/20">
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-orange-500 rounded-full animate-pulse" />
                  <span className="font-medium">Live Scalping</span>
                </div>
                <span className="text-muted-foreground">
                  Exec: {liveMetrics.avgExecutionTime.toFixed(0)}ms
                </span>
              </div>
              
              <div className="mt-2 flex items-center gap-4 text-xs">
                <span>Last Hour: <strong>{liveMetrics.tradesInLastHour}</strong> trades</span>
                <span>Symbol: <strong>{selectedSymbol}</strong></span>
              </div>
              
              {/* Activity Progress Bar */}
              <div className="mt-2">
                <Progress 
                  value={(liveMetrics.tradesInLastHour / 50) * 100}
                  className="h-1"
                />
                <div className="flex justify-between text-xs text-muted-foreground mt-1">
                  <span>Activity Level</span>
                  <span>{Math.round((liveMetrics.tradesInLastHour / 50) * 100)}%</span>
                </div>
              </div>
            </div>
          </>
        )}

      </CardContent>
    </Card>
  )
}