"use client"

import { Signal } from '@/types/alpaca'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { TrendingUp, TrendingDown, Zap, Activity } from 'lucide-react'
import { formatCurrency } from '@/lib/utils'

interface SignalsPanelProps {
  signals: Signal[]
  onExecute: (signal: Signal) => void
}

export function SignalsPanel({ signals, onExecute }: SignalsPanelProps) {
  if (!signals || signals.length === 0) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          No active signals at the moment
        </CardContent>
      </Card>
    )
  }

  const getSignalIcon = (type: string) => {
    return type === 'buy' ? 
      <TrendingUp className="h-5 w-5 text-green-500" /> : 
      <TrendingDown className="h-5 w-5 text-red-500" />
  }

  const getIndicatorColor = (indicator: string) => {
    switch (indicator) {
      case 'stochRSI':
        return 'bg-blue-500'
      case 'ema':
        return 'bg-purple-500'
      case 'combined':
        return 'bg-gradient-to-r from-blue-500 to-purple-500'
      default:
        return 'bg-gray-500'
    }
  }

  return (
    <div className="grid gap-4 md:grid-cols-2">
      {signals.map((signal, idx) => (
        <Card key={idx} className="overflow-hidden">
          <CardHeader className="pb-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                {getSignalIcon(signal.signal_type)}
                <CardTitle className="text-lg">{signal.symbol}</CardTitle>
                <Badge 
                  variant={signal.signal_type === 'buy' ? 'default' : 'destructive'}
                  className="uppercase"
                >
                  {signal.signal_type}
                </Badge>
              </div>
              <Badge variant="outline" className="flex items-center space-x-1">
                <Zap className="h-3 w-3" />
                <span>{Math.round(signal.strength * 100)}%</span>
              </Badge>
            </div>
            <CardDescription className="mt-2">
              Current Price: {formatCurrency(signal.price)}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Signal Strength Bar */}
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Signal Strength</span>
                <span className="font-medium">{Math.round(signal.strength * 100)}%</span>
              </div>
              <Progress value={signal.strength * 100} className="h-2" />
            </div>

            {/* Indicator Details */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Indicator</span>
                <div className="flex items-center space-x-2">
                  <div className={`w-2 h-2 rounded-full ${getIndicatorColor(signal.indicator)}`} />
                  <span className="font-medium capitalize">{signal.indicator}</span>
                </div>
              </div>
              
              {signal.metadata && (
                <div className="grid grid-cols-2 gap-2 text-sm">
                  {signal.metadata.stoch_k && (
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Stoch K:</span>
                      <span>{signal.metadata.stoch_k.toFixed(2)}</span>
                    </div>
                  )}
                  {signal.metadata.stoch_d && (
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Stoch D:</span>
                      <span>{signal.metadata.stoch_d.toFixed(2)}</span>
                    </div>
                  )}
                  {signal.metadata.ema_short && (
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">EMA Short:</span>
                      <span>{signal.metadata.ema_short.toFixed(2)}</span>
                    </div>
                  )}
                  {signal.metadata.ema_long && (
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">EMA Long:</span>
                      <span>{signal.metadata.ema_long.toFixed(2)}</span>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Action Button */}
            <Button 
              className="w-full"
              variant={signal.signal_type === 'buy' ? 'default' : 'destructive'}
              onClick={() => onExecute(signal)}
            >
              <Activity className="mr-2 h-4 w-4" />
              Execute {signal.signal_type.toUpperCase()} Order
            </Button>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}