"use client"

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { 
  Activity, TrendingUp, TrendingDown, AlertCircle, 
  CheckCircle, XCircle, Zap, Clock, DollarSign
} from "lucide-react"
import { formatCurrency } from '@/lib/utils'

interface TradeLogEntry {
  type: 'BOT_ACTIVATED' | 'BOT_DEACTIVATED' | 'ORDER_SUBMITTED' | 'ORDER_FILLED' | 'ORDER_FAILED' | 'SIGNAL_GENERATED'
  symbol?: string
  side?: string
  qty?: number
  price?: number
  message: string
  timestamp: string
  market?: string
  order_id?: string
  error?: string
}

interface TradeActivityLogProps {
  marketType: 'stocks' | 'crypto'
}

export function TradeActivityLog({ marketType }: TradeActivityLogProps) {
  const [tradeLog, setTradeLog] = useState<TradeLogEntry[]>([])
  const [signals, setSignals] = useState<any[]>([])
  const [botStatus, setBotStatus] = useState<Record<string, boolean>>({})
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetchTradeLog()
    const interval = setInterval(fetchTradeLog, 2000) // Update every 2 seconds for real-time feel
    return () => clearInterval(interval)
  }, [])

  const fetchTradeLog = async () => {
    try {
      const response = await fetch('/api/trade-log')
      if (response.ok) {
        const data = await response.json()
        setTradeLog(data.trades || [])
        setSignals(data.signals || [])
        setBotStatus(data.bot_status || {})
      }
    } catch (error) {
      console.error('Failed to fetch trade log:', error)
    }
  }

  const getIcon = (type: string) => {
    switch (type) {
      case 'BOT_ACTIVATED':
        return <Zap className="h-4 w-4 text-green-500" />
      case 'BOT_DEACTIVATED':
        return <XCircle className="h-4 w-4 text-red-500" />
      case 'ORDER_SUBMITTED':
        return <Clock className="h-4 w-4 text-yellow-500" />
      case 'ORDER_FILLED':
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'ORDER_FAILED':
        return <AlertCircle className="h-4 w-4 text-red-500" />
      case 'SIGNAL_GENERATED':
        return <Activity className="h-4 w-4 text-blue-500" />
      default:
        return <Activity className="h-4 w-4 text-gray-500" />
    }
  }

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'BOT_ACTIVATED':
      case 'ORDER_FILLED':
        return 'bg-green-500/10 text-green-500'
      case 'BOT_DEACTIVATED':
      case 'ORDER_FAILED':
        return 'bg-red-500/10 text-red-500'
      case 'ORDER_SUBMITTED':
        return 'bg-yellow-500/10 text-yellow-500'
      case 'SIGNAL_GENERATED':
        return 'bg-blue-500/10 text-blue-500'
      default:
        return 'bg-gray-500/10 text-gray-500'
    }
  }

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp)
    return date.toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit', 
      second: '2-digit' 
    })
  }

  // Filter logs by market type
  const filteredLogs = tradeLog.filter(log => 
    !log.market || log.market === marketType || 
    (marketType === 'crypto' && log.symbol?.includes('USD')) ||
    (marketType === 'stocks' && !log.symbol?.includes('USD'))
  )

  return (
    <Card className="h-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Activity className="h-5 w-5 text-primary" />
            <div>
              <CardTitle>Live Trading Activity</CardTitle>
              <CardDescription>Real-time bot actions and trade executions</CardDescription>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <Badge variant={botStatus[marketType] ? "default" : "outline"}>
              {botStatus[marketType] ? "BOT ACTIVE" : "BOT INACTIVE"}
            </Badge>
            {filteredLogs.length > 0 && (
              <Badge variant="secondary">{filteredLogs.length} events</Badge>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[400px] pr-4">
          {filteredLogs.length === 0 ? (
            <div className="text-center py-8">
              <Activity className="h-12 w-12 text-muted-foreground mx-auto mb-2" />
              <p className="text-sm text-muted-foreground">No trading activity yet</p>
              <p className="text-xs text-muted-foreground mt-1">
                Activate the {marketType} bot to start trading
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {filteredLogs.slice().reverse().map((log, index) => (
                <div
                  key={index}
                  className="flex items-start space-x-3 p-3 rounded-lg bg-muted/50 hover:bg-muted/70 transition-colors"
                >
                  <div className="mt-0.5">{getIcon(log.type)}</div>
                  <div className="flex-1 space-y-1">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <Badge variant="outline" className={`text-xs ${getTypeColor(log.type)}`}>
                          {log.type.replace(/_/g, ' ')}
                        </Badge>
                        {log.symbol && (
                          <Badge variant="secondary" className="text-xs">
                            {log.symbol}
                          </Badge>
                        )}
                        {log.side && (
                          <Badge 
                            variant="outline" 
                            className={`text-xs ${
                              log.side === 'buy' ? 'text-green-500' : 'text-red-500'
                            }`}
                          >
                            {log.side.toUpperCase()}
                          </Badge>
                        )}
                      </div>
                      <span className="text-xs text-muted-foreground">
                        {formatTime(log.timestamp)}
                      </span>
                    </div>
                    <p className="text-sm">{log.message}</p>
                    {log.qty && (
                      <p className="text-xs text-muted-foreground">
                        Quantity: {log.qty} {log.symbol?.replace('USD', '')}
                      </p>
                    )}
                    {log.error && (
                      <p className="text-xs text-red-500">Error: {log.error}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </ScrollArea>

        {/* Recent Signals */}
        {signals.length > 0 && (
          <div className="mt-4 pt-4 border-t">
            <h4 className="text-sm font-medium mb-2">Recent Signals</h4>
            <div className="grid grid-cols-2 gap-2">
              {signals.slice(0, 4).map((signal, index) => (
                <div key={index} className="flex items-center justify-between p-2 bg-muted/30 rounded text-xs">
                  <div className="flex items-center space-x-2">
                    {signal.action === 'buy' ? 
                      <TrendingUp className="h-3 w-3 text-green-500" /> :
                      <TrendingDown className="h-3 w-3 text-red-500" />
                    }
                    <span className="font-medium">{signal.symbol}</span>
                  </div>
                  <Badge variant="outline" className="text-xs">
                    {Math.round(signal.confidence * 100)}%
                  </Badge>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}