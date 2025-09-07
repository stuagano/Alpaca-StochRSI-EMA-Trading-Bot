"use client"

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Separator } from "@/components/ui/separator"
import { 
  TrendingUp, TrendingDown, X, Clock, Target, 
  DollarSign, Percent, Activity, Timer
} from "lucide-react"
import { formatCurrency, formatPercent, cn } from '@/lib/utils'

interface Position {
  symbol: string
  qty: string | number
  side: 'long' | 'short'
  avg_entry_price: string | number
  unrealized_pl: string | number
  unrealized_plpc: string | number
  market_value: string | number
}

interface ScalpingPositionTrackerProps {
  positions: Position[]
  realtimeData: { [symbol: string]: { price: number; timestamp: string } }
  onClosePosition: (symbol: string) => Promise<void>
}

interface PositionWithMetrics extends Position {
  currentPrice: number
  pnl: number
  pnlPercent: number
  holdTime: string
  timeToTarget: string
  riskRewardRatio: number
}

export function ScalpingPositionTracker({
  positions,
  realtimeData,
  onClosePosition
}: ScalpingPositionTrackerProps) {
  
  const [positionsWithMetrics, setPositionsWithMetrics] = useState<PositionWithMetrics[]>([])
  
  useEffect(() => {
    const enrichedPositions = positions.map(position => {
      const symbol = position.symbol
      const entryPrice = parseFloat(position.avg_entry_price.toString())
      const currentPrice = realtimeData[symbol]?.price || entryPrice
      const pnl = parseFloat(position.unrealized_pl.toString())
      const pnlPercent = parseFloat(position.unrealized_plpc.toString())
      
      // Calculate hold time (mock for now - would need entry timestamp in real data)
      const holdTime = "2m 34s" // Mock hold time
      const timeToTarget = "45s" // Mock time to target
      const riskRewardRatio = Math.abs(pnl) / Math.max(Math.abs(pnl) * 0.6, 1) // Mock R:R
      
      return {
        ...position,
        currentPrice,
        pnl,
        pnlPercent,
        holdTime,
        timeToTarget,
        riskRewardRatio
      }
    })
    
    setPositionsWithMetrics(enrichedPositions)
  }, [positions, realtimeData])

  const totalPnL = positionsWithMetrics.reduce((sum, pos) => sum + pos.pnl, 0)
  const totalValue = positionsWithMetrics.reduce((sum, pos) => 
    sum + parseFloat(pos.market_value.toString()), 0)

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-base">
            <Activity className="h-4 w-4" />
            Active Positions ({positions.length})
          </CardTitle>
          {totalPnL !== 0 && (
            <Badge variant={totalPnL >= 0 ? "default" : "destructive"} className="font-mono">
              {totalPnL >= 0 ? '+' : ''}{formatCurrency(totalPnL)}
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        
        {/* Summary Stats */}
        {positions.length > 0 && (
          <>
            <div className="grid grid-cols-2 gap-2 p-2 bg-muted/30 rounded">
              <div className="text-center">
                <p className="text-xs text-muted-foreground">Total Value</p>
                <p className="text-sm font-bold">{formatCurrency(totalValue)}</p>
              </div>
              <div className="text-center">
                <p className="text-xs text-muted-foreground">Total P&L</p>
                <p className={cn(
                  "text-sm font-bold",
                  totalPnL >= 0 ? "text-green-500" : "text-red-500"
                )}>
                  {formatCurrency(totalPnL)}
                </p>
              </div>
            </div>
            <Separator />
          </>
        )}

        {/* Position List */}
        {positionsWithMetrics.length === 0 ? (
          <div className="text-center py-6 text-muted-foreground">
            <Activity className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">No active positions</p>
            <p className="text-xs">Start scalping to see positions here</p>
          </div>
        ) : (
          <div className="space-y-3 max-h-96 overflow-y-auto">
            {positionsWithMetrics.map((position) => (
              <div
                key={position.symbol}
                className="p-3 border rounded-lg space-y-2"
              >
                {/* Position Header */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className={cn(
                      "w-2 h-2 rounded-full",
                      position.side === 'long' ? "bg-green-500" : "bg-red-500"
                    )} />
                    <span className="font-medium text-sm">{position.symbol}</span>
                    <Badge variant="outline" className="text-xs">
                      {position.side.toUpperCase()}
                    </Badge>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => onClosePosition(position.symbol)}
                    className="h-6 px-2"
                  >
                    <X className="h-3 w-3" />
                  </Button>
                </div>

                {/* Position Details */}
                <div className="grid grid-cols-3 gap-2 text-xs">
                  <div>
                    <p className="text-muted-foreground">Qty</p>
                    <p className="font-mono">{parseFloat(position.qty.toString()).toFixed(4)}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Entry</p>
                    <p className="font-mono">{formatCurrency(parseFloat(position.avg_entry_price.toString()))}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Current</p>
                    <p className="font-mono">{formatCurrency(position.currentPrice)}</p>
                  </div>
                </div>

                {/* P&L and Progress */}
                <div className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <span>P&L</span>
                    <div className="flex items-center gap-2">
                      <span className={cn(
                        "font-mono font-medium",
                        position.pnl >= 0 ? "text-green-500" : "text-red-500"
                      )}>
                        {position.pnl >= 0 ? '+' : ''}{formatCurrency(position.pnl)}
                      </span>
                      <span className={cn(
                        "text-xs",
                        position.pnl >= 0 ? "text-green-500" : "text-red-500"
                      )}>
                        ({position.pnlPercent >= 0 ? '+' : ''}{position.pnlPercent.toFixed(2)}%)
                      </span>
                    </div>
                  </div>
                  
                  {/* Progress bar for P&L */}
                  <Progress 
                    value={Math.min(Math.abs(position.pnlPercent) * 10, 100)}
                    className={cn(
                      "h-1",
                      position.pnl >= 0 ? "bg-green-500/20" : "bg-red-500/20"
                    )}
                  />
                </div>

                {/* Scalping Metrics */}
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="flex items-center gap-1">
                    <Timer className="h-3 w-3 text-muted-foreground" />
                    <span className="text-muted-foreground">Hold:</span>
                    <span className="font-mono">{position.holdTime}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Target className="h-3 w-3 text-muted-foreground" />
                    <span className="text-muted-foreground">R:R:</span>
                    <span className="font-mono">{position.riskRewardRatio.toFixed(1)}</span>
                  </div>
                </div>

                {/* Quick Actions */}
                <div className="flex gap-1 pt-1">
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-6 px-2 text-xs"
                    onClick={() => {
                      // Mock function - would adjust stop loss
                      console.log('Adjust stop loss for', position.symbol)
                    }}
                  >
                    Adjust SL
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-6 px-2 text-xs"
                    onClick={() => {
                      // Mock function - would adjust take profit
                      console.log('Adjust take profit for', position.symbol)
                    }}
                  >
                    Adjust TP
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-6 px-2 text-xs flex-1"
                    onClick={() => onClosePosition(position.symbol)}
                  >
                    Close Now
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Quick Close All */}
        {positions.length > 1 && (
          <>
            <Separator />
            <Button
              variant="destructive"
              size="sm"
              className="w-full"
              onClick={async () => {
                for (const position of positions) {
                  await onClosePosition(position.symbol)
                }
              }}
            >
              <X className="mr-2 h-4 w-4" />
              Close All Positions
            </Button>
          </>
        )}
      </CardContent>
    </Card>
  )
}