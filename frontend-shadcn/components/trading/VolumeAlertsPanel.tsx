"use client"

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { 
  Volume2, TrendingUp, TrendingDown, Zap, Bell, 
  AlertTriangle, Activity, Target, Clock, Eye
} from "lucide-react"
import { formatCurrency, formatPercent, cn } from '@/lib/utils'
import { toast } from 'sonner'

interface Signal {
  symbol: string
  signal_type: 'buy' | 'sell'
  strength: number
  price: number
  timestamp: string
}

interface VolumeAlert {
  id: string
  symbol: string
  alertType: 'volume_spike' | 'price_breakout' | 'momentum_shift' | 'volatility_expansion'
  severity: 'low' | 'medium' | 'high' | 'critical'
  message: string
  price: number
  volume: number
  volumeRatio: number // Current volume / average volume
  priceChange: number
  timestamp: Date
  isActive: boolean
}

interface VolumeAlertsPanelProps {
  selectedSymbol: string
  signals: Signal[]
  onSymbolSelect: (symbol: string) => void
}

export function VolumeAlertsPanel({
  selectedSymbol,
  signals,
  onSymbolSelect
}: VolumeAlertsPanelProps) {
  
  const [alerts, setAlerts] = useState<VolumeAlert[]>([])
  const [soundEnabled, setSoundEnabled] = useState(true)

  // Generate mock volume alerts for scalping opportunities
  useEffect(() => {
    const generateAlert = (): VolumeAlert => {
      const symbols = ['BTCUSD', 'ETHUSD', 'LTCUSD', 'DOGEUSD', 'SOLUSD', 'AVAXUSD']
      const alertTypes: VolumeAlert['alertType'][] = ['volume_spike', 'price_breakout', 'momentum_shift', 'volatility_expansion']
      const severities: VolumeAlert['severity'][] = ['low', 'medium', 'high', 'critical']
      
      const symbol = symbols[Math.floor(Math.random() * symbols.length)]
      const alertType = alertTypes[Math.floor(Math.random() * alertTypes.length)]
      const severity = severities[Math.floor(Math.random() * severities.length)]
      
      const basePrice = symbol.includes('BTC') ? 45000 : symbol.includes('ETH') ? 2800 : symbol.includes('DOGE') ? 0.08 : 100
      const price = basePrice * (1 + (Math.random() - 0.5) * 0.02)
      const volumeRatio = 1.5 + Math.random() * 4 // 1.5x to 5.5x average volume
      const priceChange = (Math.random() - 0.5) * 0.06 // ±3%
      
      const messages = {
        volume_spike: `Volume surge detected: ${volumeRatio.toFixed(1)}x average`,
        price_breakout: `Price breakout: ${priceChange > 0 ? 'Above' : 'Below'} key level`,
        momentum_shift: `Momentum shift detected: ${priceChange > 0 ? 'Bullish' : 'Bearish'} acceleration`,
        volatility_expansion: `Volatility expansion: Increased price movement range`
      }
      
      return {
        id: `alert_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        symbol,
        alertType,
        severity,
        message: messages[alertType],
        price,
        volume: Math.random() * 10000000,
        volumeRatio,
        priceChange,
        timestamp: new Date(),
        isActive: true
      }
    }

    const interval = setInterval(() => {
      // Generate new alerts every 5-15 seconds
      if (Math.random() > 0.4) { // 60% chance
        const newAlert = generateAlert()
        
        setAlerts(prev => {
          const updated = [newAlert, ...prev.slice(0, 9)] // Keep latest 10 alerts
          
          // Play sound for high/critical alerts
          if ((newAlert.severity === 'high' || newAlert.severity === 'critical') && soundEnabled) {
            // In a real app, you'd play an actual sound
            console.log(`🔊 Alert sound: ${newAlert.severity} ${newAlert.alertType}`)
          }
          
          return updated
        })

        // Show toast for critical alerts
        if (newAlert.severity === 'critical') {
          toast(newAlert.message, {
            description: `${newAlert.symbol}: ${formatCurrency(newAlert.price)}`,
            action: {
              label: "Trade",
              onClick: () => onSymbolSelect(newAlert.symbol)
            }
          })
        }
      }
    }, 7000) // Every 7 seconds

    return () => clearInterval(interval)
  }, [soundEnabled, onSymbolSelect])

  // Auto-expire alerts after 2 minutes
  useEffect(() => {
    const interval = setInterval(() => {
      setAlerts(prev => prev.map(alert => ({
        ...alert,
        isActive: (Date.now() - alert.timestamp.getTime()) < 120000 // 2 minutes
      })))
    }, 10000)

    return () => clearInterval(interval)
  }, [])

  const getSeverityColor = (severity: VolumeAlert['severity']) => {
    switch (severity) {
      case 'critical': return 'border-red-500 bg-red-500/10'
      case 'high': return 'border-orange-500 bg-orange-500/10'
      case 'medium': return 'border-yellow-500 bg-yellow-500/10'
      case 'low': return 'border-blue-500 bg-blue-500/10'
    }
  }

  const getSeverityIcon = (alertType: VolumeAlert['alertType']) => {
    switch (alertType) {
      case 'volume_spike': return <Volume2 className="h-4 w-4" />
      case 'price_breakout': return <TrendingUp className="h-4 w-4" />
      case 'momentum_shift': return <Zap className="h-4 w-4" />
      case 'volatility_expansion': return <Activity className="h-4 w-4" />
    }
  }

  const activeAlerts = alerts.filter(alert => alert.isActive)
  const criticalAlerts = activeAlerts.filter(alert => alert.severity === 'critical' || alert.severity === 'high')

  return (
    <Card className="border-2 border-blue-500/20">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-base">
            <Bell className="h-4 w-4 text-blue-500" />
            Volume Alerts ({activeAlerts.length})
          </CardTitle>
          <div className="flex items-center gap-2">
            {criticalAlerts.length > 0 && (
              <Badge variant="destructive" className="animate-pulse">
                {criticalAlerts.length} Critical
              </Badge>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={() => setSoundEnabled(!soundEnabled)}
              className="p-1 h-6 w-6"
            >
              {soundEnabled ? '🔊' : '🔇'}
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        
        {/* Quick Stats */}
        <div className="grid grid-cols-2 gap-2 p-2 bg-muted/30 rounded text-xs">
          <div className="text-center">
            <p className="text-muted-foreground">High Priority</p>
            <p className="font-bold text-orange-500">{criticalAlerts.length}</p>
          </div>
          <div className="text-center">
            <p className="text-muted-foreground">Watching</p>
            <p className="font-bold">{selectedSymbol}</p>
          </div>
        </div>

        {/* Alert List */}
        <div className="space-y-2 max-h-80 overflow-y-auto">
          {activeAlerts.length === 0 ? (
            <div className="text-center py-6 text-muted-foreground">
              <Eye className="h-8 w-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">Monitoring volume patterns...</p>
              <p className="text-xs">Alerts will appear here</p>
            </div>
          ) : (
            activeAlerts.map((alert) => (
              <div
                key={alert.id}
                className={cn(
                  "p-3 border rounded-lg cursor-pointer transition-all hover:shadow-md",
                  getSeverityColor(alert.severity),
                  !alert.isActive && "opacity-50"
                )}
                onClick={() => onSymbolSelect(alert.symbol)}
              >
                {/* Alert Header */}
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    {getSeverityIcon(alert.alertType)}
                    <span className="font-medium text-sm">{alert.symbol}</span>
                    <Badge variant="outline" className="text-xs">
                      {alert.severity.toUpperCase()}
                    </Badge>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {Math.floor((Date.now() - alert.timestamp.getTime()) / 1000)}s ago
                  </span>
                </div>

                {/* Alert Content */}
                <p className="text-sm mb-2">{alert.message}</p>

                {/* Alert Details */}
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <span className="text-muted-foreground">Price:</span>
                    <span className="font-mono ml-1">{formatCurrency(alert.price)}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Change:</span>
                    <span className={cn(
                      "font-mono ml-1",
                      alert.priceChange >= 0 ? "text-green-500" : "text-red-500"
                    )}>
                      {alert.priceChange >= 0 ? '+' : ''}{formatPercent(alert.priceChange)}
                    </span>
                  </div>
                </div>

                {/* Volume Info */}
                <div className="mt-2 flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">Volume Ratio:</span>
                  <div className="flex items-center gap-1">
                    <span className="font-mono font-bold text-blue-600">
                      {alert.volumeRatio.toFixed(1)}x
                    </span>
                    {alert.volumeRatio > 3 && (
                      <Badge variant="outline" className="text-xs bg-red-500/10 text-red-600">
                        Extreme
                      </Badge>
                    )}
                  </div>
                </div>

                {/* Quick Action */}
                <div className="mt-2 pt-2 border-t border-muted/30">
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full h-6 text-xs"
                    onClick={(e) => {
                      e.stopPropagation()
                      onSymbolSelect(alert.symbol)
                      toast.success(`Switched to ${alert.symbol}`)
                    }}
                  >
                    <Target className="mr-1 h-3 w-3" />
                    Trade {alert.symbol}
                  </Button>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Alert Settings */}
        {activeAlerts.length > 0 && (
          <>
            <Separator />
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Sound alerts:</span>
              <Badge 
                variant={soundEnabled ? "default" : "outline"}
                className="cursor-pointer"
                onClick={() => setSoundEnabled(!soundEnabled)}
              >
                {soundEnabled ? "ON" : "OFF"}
              </Badge>
            </div>
            
            <Button
              variant="outline"
              size="sm"
              className="w-full"
              onClick={() => setAlerts([])}
            >
              Clear All Alerts
            </Button>
          </>
        )}

        {/* Help Text */}
        <div className="p-2 bg-muted/20 rounded text-xs text-muted-foreground">
          <p>Click any alert to switch to that symbol. Critical alerts will show notifications.</p>
        </div>
      </CardContent>
    </Card>
  )
}