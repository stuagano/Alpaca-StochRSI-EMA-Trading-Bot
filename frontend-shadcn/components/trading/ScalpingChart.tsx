"use client"

import { useState, useEffect, useRef } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { 
  TrendingUp, TrendingDown, Activity, BarChart3, 
  Maximize2, Settings, RefreshCw 
} from "lucide-react"
import { formatCurrency } from '@/lib/utils'

interface ScalpingChartProps {
  symbol: string
  realtimeData?: {
    price: number
    volume: number
    timestamp: string
    high?: number
    low?: number
  }
  height?: number
}

interface ChartDataPoint {
  timestamp: string
  price: number
  volume: number
  high: number
  low: number
  open: number
  close: number
}

export function ScalpingChart({
  symbol,
  realtimeData,
  height = 400
}: ScalpingChartProps) {
  
  const chartRef = useRef<HTMLDivElement>(null)
  const [timeframe, setTimeframe] = useState<'15s' | '1m' | '5m'>('1m')
  const [chartData, setChartData] = useState<ChartDataPoint[]>([])
  const [isFullscreen, setIsFullscreen] = useState(false)

  // Mock chart data generation for demo
  useEffect(() => {
    const generateMockData = () => {
      const data: ChartDataPoint[] = []
      const basePrice = realtimeData?.price || 45000
      let currentPrice = basePrice
      
      for (let i = 100; i >= 0; i--) {
        const timestamp = new Date(Date.now() - i * (timeframe === '15s' ? 15000 : timeframe === '1m' ? 60000 : 300000)).toISOString()
        
        // Generate realistic OHLC data
        const open = currentPrice
        const volatility = 0.002 + Math.random() * 0.003 // 0.2-0.5% volatility
        const change = (Math.random() - 0.5) * volatility
        const close = open * (1 + change)
        const high = Math.max(open, close) * (1 + Math.random() * volatility * 0.5)
        const low = Math.min(open, close) * (1 - Math.random() * volatility * 0.5)
        const volume = 1000000 + Math.random() * 5000000
        
        data.push({
          timestamp,
          price: close,
          volume,
          high,
          low,
          open,
          close
        })
        
        currentPrice = close
      }
      
      return data
    }
    
    setChartData(generateMockData())
  }, [symbol, timeframe, realtimeData])

  // Update chart with real-time data
  useEffect(() => {
    if (realtimeData && chartData.length > 0) {
      const lastCandle = chartData[chartData.length - 1]
      const timeDiff = Date.now() - new Date(lastCandle.timestamp).getTime()
      const candleInterval = timeframe === '15s' ? 15000 : timeframe === '1m' ? 60000 : 300000
      
      if (timeDiff >= candleInterval) {
        // Start new candle
        const newCandle: ChartDataPoint = {
          timestamp: realtimeData.timestamp,
          price: realtimeData.price,
          volume: realtimeData.volume || 0,
          high: realtimeData.high || realtimeData.price,
          low: realtimeData.low || realtimeData.price,
          open: realtimeData.price,
          close: realtimeData.price
        }
        
        setChartData(prev => [...prev.slice(-99), newCandle])
      } else {
        // Update current candle
        setChartData(prev => {
          const updated = [...prev]
          const currentCandle = updated[updated.length - 1]
          updated[updated.length - 1] = {
            ...currentCandle,
            close: realtimeData.price,
            high: Math.max(currentCandle.high, realtimeData.price),
            low: Math.min(currentCandle.low, realtimeData.price),
            volume: currentCandle.volume + (realtimeData.volume || 0)
          }
          return updated
        })
      }
    }
  }, [realtimeData, chartData, timeframe])

  const currentPrice = realtimeData?.price || chartData[chartData.length - 1]?.close || 0
  const priceChange = chartData.length > 1 ? currentPrice - chartData[chartData.length - 2].close : 0
  const priceChangePercent = chartData.length > 1 ? (priceChange / chartData[chartData.length - 2].close) * 100 : 0

  return (
    <Card className={isFullscreen ? "fixed inset-0 z-50 m-4" : ""}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <CardTitle className="text-base">{symbol} Chart</CardTitle>
            <div className="flex items-center gap-2">
              <span className="font-mono text-lg font-bold">
                {formatCurrency(currentPrice)}
              </span>
              <div className="flex items-center gap-1">
                {priceChange >= 0 ? 
                  <TrendingUp className="h-4 w-4 text-green-500" /> :
                  <TrendingDown className="h-4 w-4 text-red-500" />
                }
                <span className={`text-sm font-medium ${
                  priceChange >= 0 ? 'text-green-500' : 'text-red-500'
                }`}>
                  {priceChange >= 0 ? '+' : ''}{priceChangePercent.toFixed(3)}%
                </span>
              </div>
            </div>
            <Badge variant={realtimeData ? "default" : "secondary"} className="animate-pulse">
              {realtimeData ? "LIVE" : "DELAYED"}
            </Badge>
          </div>
          
          <div className="flex items-center gap-2">
            <Tabs value={timeframe} onValueChange={(value) => setTimeframe(value as '15s' | '1m' | '5m')}>
              <TabsList className="grid grid-cols-3 w-32">
                <TabsTrigger value="15s" className="text-xs">15s</TabsTrigger>
                <TabsTrigger value="1m" className="text-xs">1m</TabsTrigger>
                <TabsTrigger value="5m" className="text-xs">5m</TabsTrigger>
              </TabsList>
            </Tabs>
            
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsFullscreen(!isFullscreen)}
            >
              <Maximize2 className="h-4 w-4" />
            </Button>
            
            <Button variant="outline" size="sm">
              <Settings className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="p-0">
        <div 
          ref={chartRef}
          className="relative bg-gradient-to-b from-background to-muted/10"
          style={{ height: isFullscreen ? 'calc(100vh - 120px)' : height }}
        >
          {/* Chart Placeholder - In a real implementation, you'd use TradingView, Lightweight Charts, or similar */}
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <BarChart3 className="h-16 w-16 mx-auto mb-4 opacity-50" />
              <p className="text-lg font-medium mb-2">Scalping Chart - {symbol}</p>
              <p className="text-sm text-muted-foreground mb-4">
                Timeframe: {timeframe} • Data Points: {chartData.length}
              </p>
              
              {/* Mock chart visualization */}
              <div className="w-full max-w-md mx-auto h-32 border rounded bg-muted/20 relative overflow-hidden">
                <div className="absolute inset-0 flex items-end justify-between px-1">
                  {chartData.slice(-20).map((point, index) => (
                    <div
                      key={index}
                      className={`w-1 transition-all duration-300 ${
                        point.close > point.open ? 'bg-green-500' : 'bg-red-500'
                      }`}
                      style={{
                        height: `${((point.close - Math.min(...chartData.slice(-20).map(p => p.low))) / 
                          (Math.max(...chartData.slice(-20).map(p => p.high)) - Math.min(...chartData.slice(-20).map(p => p.low)))) * 100}%`
                      }}
                    />
                  ))}
                </div>
                
                {/* Current price line */}
                <div 
                  className="absolute w-full border-t-2 border-dashed border-blue-500 opacity-50"
                  style={{
                    bottom: `${((currentPrice - Math.min(...chartData.slice(-20).map(p => p.low))) / 
                      (Math.max(...chartData.slice(-20).map(p => p.high)) - Math.min(...chartData.slice(-20).map(p => p.low)))) * 100}%`
                  }}
                />
              </div>
              
              <div className="mt-4 grid grid-cols-2 gap-4 max-w-xs mx-auto">
                <div className="text-center">
                  <p className="text-xs text-muted-foreground">Volume</p>
                  <p className="text-sm font-mono">
                    {((realtimeData?.volume || 0) / 1000000).toFixed(1)}M
                  </p>
                </div>
                <div className="text-center">
                  <p className="text-xs text-muted-foreground">Last Update</p>
                  <p className="text-sm font-mono">
                    {realtimeData?.timestamp ? 
                      new Date(realtimeData.timestamp).toLocaleTimeString() : 
                      'N/A'
                    }
                  </p>
                </div>
              </div>
            </div>
          </div>
          
          {/* Chart overlays for scalping levels */}
          <div className="absolute top-4 left-4 space-y-1">
            <Badge variant="outline" className="text-xs bg-green-500/10 text-green-600">
              TP: +0.5%
            </Badge>
            <Badge variant="outline" className="text-xs bg-red-500/10 text-red-600">
              SL: -0.3%
            </Badge>
            <Badge variant="outline" className="text-xs bg-blue-500/10 text-blue-600">
              Entry Zone
            </Badge>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}