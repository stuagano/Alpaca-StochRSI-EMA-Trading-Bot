"use client"

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { 
  TrendingUp, TrendingDown, Activity, DollarSign, 
  Zap, AlertCircle, Clock
} from "lucide-react"
import { formatCurrency, formatPercent } from '@/lib/utils'
import unifiedAPIClient from '@/lib/api/client'

interface CryptoSignal {
  symbol: string
  action: string
  confidence: number
  price: number
  volatility: number
  volume_surge: boolean
  momentum: number
  target_profit: number
  stop_loss: number
  timestamp: string
}

interface CryptoActiveSidebarProps {
  marketMode: 'stocks' | 'crypto'
  signals: any[]
  onExecute: any
}

export function CryptoActiveSidebar({ marketMode, signals, onExecute }: CryptoActiveSidebarProps) {
  const [cryptoSignals, setCryptoSignals] = useState<CryptoSignal[]>([])
  const [loading, setLoading] = useState(false)

  // Fetch crypto signals when in crypto mode
  useEffect(() => {
    if (marketMode === 'crypto') {
      fetchCryptoSignals()
      const interval = setInterval(fetchCryptoSignals, 10000) // Update every 10 seconds
      return () => clearInterval(interval)
    }
  }, [marketMode])

  const fetchCryptoSignals = async () => {
    try {
      setLoading(true)
      const response = await fetch('http://localhost:9100/api/crypto/signals')
      if (response.ok) {
        const data = await response.json()
        setCryptoSignals(Array.isArray(data) ? data.slice(0, 5) : data.signals ? data.signals.slice(0, 5) : [])
      }
    } catch (error) {
      // Silently fail - endpoint may not exist
    } finally {
      setLoading(false)
    }
  }

  const displaySignals = marketMode === 'crypto' ? cryptoSignals : (Array.isArray(signals) ? signals.slice(0, 5) : signals ? [signals] : [])

  const getSignalIcon = (signal: any) => {
    if (marketMode === 'crypto') {
      return signal.action === 'buy' ? 
        <TrendingUp className="h-4 w-4 text-green-500" /> :
        <TrendingDown className="h-4 w-4 text-red-500" />
    } else {
      return signal.signal === 'BUY' ? 
        <TrendingUp className="h-4 w-4 text-green-500" /> :
        <TrendingDown className="h-4 w-4 text-red-500" />
    }
  }

  const getConfidence = (signal: any) => {
    if (marketMode === 'crypto') {
      return Math.round(signal.confidence * 100)
    } else {
      return signal.confidence
    }
  }

  const getSignalText = (signal: any) => {
    if (marketMode === 'crypto') {
      return signal?.action?.toUpperCase() || 'HOLD'
    } else {
      return signal?.signal || 'HOLD'
    }
  }

  // Manual execution only for stocks - crypto is fully automated
  const handleExecute = (signal: any) => {
    // Stock mode allows manual execution
    if (marketMode === 'stocks') {
      onExecute.mutate({
        symbol: signal.symbol,
        qty: 10,
        side: signal.signal_type === 'buy' ? 'buy' : 'sell',
        type: 'market',
        time_in_force: 'day'
      })
    }
    // Crypto mode: No manual execution - fully automated by bot
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          {marketMode === 'crypto' ? (
            <>
              <Zap className="h-4 w-4 text-yellow-500" />
              <span>Active Crypto Signals</span>
            </>
          ) : (
            <>
              <Activity className="h-4 w-4 text-primary" />
              <span>Active Signals</span>
            </>
          )}
        </CardTitle>
        <CardDescription>
          {marketMode === 'crypto' ? 'High-volatility crypto opportunities' : 'Top trading opportunities'}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-2">
        {loading && marketMode === 'crypto' ? (
          <div className="text-center py-4">
            <div className="animate-spin h-6 w-6 border-2 border-primary rounded-full border-t-transparent mx-auto"></div>
            <p className="text-sm text-muted-foreground mt-2">Scanning markets...</p>
          </div>
        ) : displaySignals.length === 0 ? (
          <div className="text-center py-4">
            <AlertCircle className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
            <p className="text-sm text-muted-foreground">
              {marketMode === 'crypto' ? 'No crypto signals detected' : 'No active signals'}
            </p>
          </div>
        ) : (
          displaySignals.map((signal: any, idx: number) => (
            <div key={idx} className="flex items-center justify-between p-2 rounded-lg bg-muted/50">
              <div className="flex items-center space-x-2">
                {getSignalIcon(signal)}
                <span className="font-medium">{signal.symbol}</span>
                {marketMode === 'crypto' && signal.volume_surge && (
                  <Badge variant="secondary" className="text-xs">
                    Volume Surge
                  </Badge>
                )}
              </div>
              <div className="flex items-center space-x-2">
                <Badge 
                  variant="outline" 
                  className={`text-xs ${
                    getConfidence(signal) >= 80 ? 'bg-green-500/10 text-green-500' :
                    getConfidence(signal) >= 60 ? 'bg-yellow-500/10 text-yellow-500' :
                    'bg-red-500/10 text-red-500'
                  }`}
                >
                  {getConfidence(signal)}%
                </Badge>
                {marketMode === 'crypto' && (
                  <Badge variant="outline" className="text-xs">
                    {formatPercent(signal.volatility)}
                  </Badge>
                )}
                {marketMode === 'crypto' ? (
                  // Crypto: Show signal as badge only (no manual execution)
                  <Badge 
                    variant={getSignalText(signal) === 'BUY' || getSignalText(signal) === 'buy' ? 'default' : 'destructive'}
                    className="text-xs px-2 py-1"
                  >
                    {getSignalText(signal)} AUTO
                  </Badge>
                ) : (
                  // Stocks: Allow manual execution
                  <Button 
                    size="sm" 
                    variant={getSignalText(signal) === 'BUY' || getSignalText(signal) === 'buy' ? 'default' : 'destructive'}
                    onClick={() => handleExecute(signal)}
                    className="text-xs px-2 py-1"
                  >
                    {getSignalText(signal)}
                  </Button>
                )}
              </div>
            </div>
          ))
        )}
        
        {marketMode === 'crypto' && displaySignals.length > 0 && (
          <div className="mt-4 p-2 bg-yellow-500/10 rounded-lg">
            <div className="flex items-center space-x-2 text-yellow-600">
              <Clock className="h-4 w-4" />
              <span className="text-xs font-medium">24/7 Trading Active</span>
            </div>
            <p className="text-xs text-yellow-600/80 mt-1">
              Crypto markets never close - signals update in real-time
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}