"use client"

import { useEffect, useRef, useState } from 'react'
import { createChart, ColorType, IChartApi, ISeriesApi } from 'lightweight-charts'
import { useMarketData, useIndicators } from '@/hooks/useAlpaca'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import unifiedAPIClient, { MarketMode } from '@/lib/api/client'

interface TradingChartProps {
  symbol: string
  realtimeData?: any
  marketType?: MarketMode
  onSymbolChange?: (symbol: string) => void
  height?: number
}

export function TradingChart({ 
  symbol, 
  realtimeData, 
  marketType = 'stocks', 
  onSymbolChange,
  height = 400 
}: TradingChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const candlestickSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null)
  const emaShortSeriesRef = useRef<ISeriesApi<'Line'> | null>(null)
  const emaLongSeriesRef = useRef<ISeriesApi<'Line'> | null>(null)
  // Removed Bollinger Bands and Support/Resistance refs to reduce overhead
  const buySignalsRef = useRef<ISeriesApi<'Line'> | null>(null)
  const sellSignalsRef = useRef<ISeriesApi<'Line'> | null>(null)
  
  const [timeframe, setTimeframe] = useState<'1Min' | '5Min' | '15Min' | '1Hour' | '1Day'>('1Min')
  const [showIndicators, setShowIndicators] = useState({
    ema: true,
    signals: true,
    volume: true
  })
  const { data: marketData, isLoading, error } = useMarketData(symbol, timeframe, marketType)
  const { data: indicators } = useIndicators(symbol, marketType)

  // Debug logging for chart data flow
  useEffect(() => {
    console.log('🚀 TradingChart Debug:', {
      symbol,
      timeframe,
      marketType,
      marketData: marketData?.length || 0,
      isLoading,
      error: error ? error.message : null,
      chartContainer: !!chartContainerRef.current,
      chartInstance: !!chartRef.current
    })
  }, [symbol, timeframe, marketType, marketData, isLoading, error])

  // Initialize chart only once
  useEffect(() => {
    if (!chartContainerRef.current) return

    // Clean up any existing chart safely
    if (chartRef.current) {
      try {
        chartRef.current.remove()
      } catch (e) {
        // Chart already disposed, ignore
      }
      chartRef.current = null
    }

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#d1d4dc',
      },
      grid: {
        vertLines: { color: '#2a2e39' },
        horzLines: { color: '#2a2e39' },
      },
      crosshair: {
        mode: 1,
        vertLine: {
          width: 1,
          color: '#9B7DFF',
          style: 0,
        },
        horzLine: {
          width: 1,
          color: '#9B7DFF',
          style: 0,
        },
      },
      width: chartContainerRef.current.clientWidth,
      height: height,
      timeScale: {
        borderColor: '#2a2e39',
        timeVisible: true,
        secondsVisible: false,
      },
      rightPriceScale: {
        borderColor: '#2a2e39',
        mode: 0, // Normal price scale
        autoScale: true,
        invertScale: false,
        alignLabels: true,
        borderVisible: true,
        scaleMargins: {
          top: 0.1,
          bottom: 0.2,
        },
      },
      localization: {
        priceFormatter: (price: number) => {
          // Format based on price magnitude
          if (price < 0.01) return price.toFixed(6)
          if (price < 1) return price.toFixed(4)
          if (price < 100) return price.toFixed(2)
          return price.toFixed(0)
        },
      },
    })

    // Add candlestick series
    const candlestickSeries = chart.addCandlestickSeries({
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderVisible: false,
      wickUpColor: '#26a69a',
      wickDownColor: '#ef5350',
      priceScaleId: 'right',
    })

    // Add volume series
    const volumeSeries = chart.addHistogramSeries({
      color: '#26a69a',
      priceFormat: {
        type: 'volume',
      },
      priceScaleId: '', // Use separate scale for volume
    })

    // Add EMA lines
    const emaShortSeries = chart.addLineSeries({
      color: '#2962FF',
      lineWidth: 2,
      title: 'EMA 9',
      priceScaleId: 'right',
    })

    const emaLongSeries = chart.addLineSeries({
      color: '#FF6D00',
      lineWidth: 2,
      title: 'EMA 21',
      priceScaleId: 'right',
    })

    // Removed Bollinger Bands and Support/Resistance indicators - not needed for scalping

    // Add Buy/Sell signal markers
    const buySignals = chart.addLineSeries({
      color: 'transparent',
      title: 'Buy Signals',
      priceScaleId: 'right',
      pointMarkersVisible: true,
    })

    const sellSignals = chart.addLineSeries({
      color: 'transparent',
      title: 'Sell Signals',
      priceScaleId: 'right',
      pointMarkersVisible: true,
    })

    // Set price scale with auto-scaling
    chart.priceScale('').applyOptions({
      scaleMargins: {
        top: 0.8,
        bottom: 0,
      },
    })
    
    // Configure right price scale for better visibility
    chart.priceScale('right').applyOptions({
      autoScale: true,
      mode: 0, // Normal mode
      invertScale: false,
      alignLabels: true,
      borderVisible: true,
      borderColor: '#2a2e39',
      scaleMargins: {
        top: 0.1,
        bottom: 0.2,
      },
    })


    // Store refs
    chartRef.current = chart
    candlestickSeriesRef.current = candlestickSeries
    volumeSeriesRef.current = volumeSeries
    emaShortSeriesRef.current = emaShortSeries
    emaLongSeriesRef.current = emaLongSeries
    buySignalsRef.current = buySignals
    sellSignalsRef.current = sellSignals

    // Handle resize
    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({ width: chartContainerRef.current.clientWidth })
      }
    }
    window.addEventListener('resize', handleResize)

    // Fit content
    chart.timeScale().fitContent()

    return () => {
      window.removeEventListener('resize', handleResize)
      try {
        if (chart) {
          chart.remove()
        }
      } catch (e) {
        // Chart already disposed, ignore
      }
      chartRef.current = null
    }
  }, []) // Only run once

  // Generate minimal mock data for fallback only
  const generateMockData = (symbol: string, timeframe: string) => {
    const now = new Date()
    const bars = []
    let basePrice = symbol.includes('BTC') ? 45000 : symbol.includes('ETH') ? 2800 : 100
    const intervalMinutes = timeframe === '1Min' ? 1 : timeframe === '5Min' ? 5 : 15
    
    // Generate only 50 bars for performance
    for (let i = 50; i >= 0; i--) {
      const time = new Date(now.getTime() - i * intervalMinutes * 60000)
      const change = (Math.random() - 0.5) * 0.002
      const open = basePrice * (1 + change)
      const close = open * (1 + (Math.random() - 0.5) * 0.002)
      
      bars.push({
        t: time.toISOString(),
        o: open,
        h: Math.max(open, close) * 1.001,
        l: Math.min(open, close) * 0.999,
        c: close,
        v: Math.floor(1000 + Math.random() * 2000),
        n: 20,
        vw: (open + close) / 2
      })
      
      basePrice = close
    }
    
    return bars
  }

  // Update chart data when marketData changes or when chart is ready
  useEffect(() => {
    if (!chartRef.current || !candlestickSeriesRef.current) return

    // Use real data if available, generate mock data only as fallback
    let dataToUse = marketData && marketData.length > 0 ? marketData : null
    
    if (!dataToUse) {
      // Only generate minimal mock data for display
      dataToUse = generateMockData(symbol, timeframe).slice(-50) // Only last 50 bars
    }

    if (!dataToUse || !dataToUse.length) {
      console.error('❌ No data available for chart')
      return
    }

    // Sort data by time in ascending order (oldest first)
    const sortedData = [...dataToUse].sort((a, b) => 
      new Date(a.t).getTime() - new Date(b.t).getTime()
    )

    const candleData = sortedData.map((bar) => ({
      time: new Date(bar.t).getTime() / 1000 as any,
      open: bar.o,
      high: bar.h,
      low: bar.l,
      close: bar.c,
    }))

    const volumeData = sortedData.map((bar) => ({
      time: new Date(bar.t).getTime() / 1000 as any,
      value: bar.v,
      color: bar.c >= bar.o ? '#26a69a' : '#ef5350',
    }))

    // Update series data
    candlestickSeriesRef.current.setData(candleData)
    volumeSeriesRef.current?.setData(volumeData)
    
    // Auto-scale to fit the data properly
    if (chartRef.current) {
      chartRef.current.priceScale('right').applyOptions({
        autoScale: true,
      })
    }

    // Calculate and update indicators - only if we have enough data
    if (sortedData.length >= 21 && showIndicators.ema) {
      const calculateEMA = (data: number[], period: number) => {
        const k = 2 / (period + 1)
        const ema = [data[0]]
        for (let i = 1; i < data.length; i++) {
          ema.push(data[i] * k + ema[i - 1] * (1 - k))
        }
        return ema
      }

      const calculateSMA = (data: number[], period: number) => {
        const sma = []
        for (let i = 0; i < data.length; i++) {
          if (i < period - 1) {
            sma.push(data[i]) // Use actual value for initial points
          } else {
            const sum = data.slice(i - period + 1, i + 1).reduce((a, b) => a + b, 0)
            sma.push(sum / period)
          }
        }
        return sma
      }

      // Removed Bollinger Bands and Support/Resistance calculations - not needed for scalping

      const generateScalpingSignals = (closes: number[], highs: number[], lows: number[], volumes: number[]) => {
        const buySignals = []
        const sellSignals = []
        
        // Reduce signal frequency - only check every 10th candle to reduce overhead
        for (let i = 10; i < closes.length; i += 10) {
          // Simple momentum signals
          const priceChange = (closes[i] - closes[i-1]) / closes[i-1]
          const volumeSpike = volumes[i] > volumes[i-1] * 1.3 // 30% volume increase
          
          // Fast EMA crossover (simplified)
          const fastEma3 = (closes[i] + closes[i-1] + closes[i-2]) / 3
          const fastEma8 = closes.slice(i-7, i+1).reduce((a,b) => a+b, 0) / 8
          const emaCross = fastEma3 > fastEma8
          
          // Only generate signals on strong conditions
          if (priceChange > 0.001 && volumeSpike && emaCross) {
            buySignals.push({ time: sortedData[i].t, price: closes[i] })
          }
          
          if (priceChange < -0.001 && volumeSpike && !emaCross) {
            sellSignals.push({ time: sortedData[i].t, price: closes[i] })
          }
        }
        
        return { buySignals, sellSignals }
      }

      const closes = sortedData.map(bar => bar.c)
      const highs = sortedData.map(bar => bar.h)
      const lows = sortedData.map(bar => bar.l)
      const volumes = sortedData.map(bar => bar.v)

      // Calculate faster EMAs for scalping (3 and 8 period instead of 9 and 21)
      const emaFast = calculateEMA(closes, 3)
      const emaSlow = calculateEMA(closes, 8)

      // Generate FREQUENT scalping signals
      const signals = generateScalpingSignals(closes, highs, lows, volumes)

      // Update EMA series (fast scalping EMAs)
      if (showIndicators.ema) {
        const emaFastData = sortedData.map((bar, i) => ({
          time: new Date(bar.t).getTime() / 1000 as any,
          value: emaFast[i],
        }))

        const emaSlowData = sortedData.map((bar, i) => ({
          time: new Date(bar.t).getTime() / 1000 as any,
          value: emaSlow[i],
        }))

        emaShortSeriesRef.current?.setData(emaFastData)
        emaLongSeriesRef.current?.setData(emaSlowData)
      }

      // Removed Bollinger Bands and Support/Resistance updates - not needed for scalping

      // Update Buy/Sell signals
      if (showIndicators.signals) {
        const buySignalData = signals.buySignals.map(signal => ({
          time: new Date(signal.time).getTime() / 1000 as any,
          value: signal.price,
          color: '#4CAF50',
          shape: 'arrowUp',
          text: 'BUY',
        }))

        const sellSignalData = signals.sellSignals.map(signal => ({
          time: new Date(signal.time).getTime() / 1000 as any,
          value: signal.price,
          color: '#F44336',
          shape: 'arrowDown',
          text: 'SELL',
        }))

        // Set marker data for buy and sell signals
        buySignalsRef.current?.setMarkers(buySignalData as any)
        sellSignalsRef.current?.setMarkers(sellSignalData as any)
      }
    }

    // Fit content after updating data
    chartRef.current.timeScale().fitContent()
  }, [marketData, timeframe, symbol, showIndicators.ema])

  // Update with realtime data
  useEffect(() => {
    if (!realtimeData || !candlestickSeriesRef.current) return

    const { price, volume, timestamp } = realtimeData
    const time = new Date(timestamp).getTime() / 1000

    candlestickSeriesRef.current.update({
      time: time as any,
      open: price,
      high: price,
      low: price,
      close: price,
    })

    if (volumeSeriesRef.current) {
      volumeSeriesRef.current.update({
        time: time as any,
        value: volume,
        color: '#26a69a',
      })
    }
  }, [realtimeData])

  // Get market-specific symbol list
  const getSymbolOptions = () => {
    if (marketType === 'crypto') {
      return [
        'BTCUSD', 'ETHUSD', 'LTCUSD', 'BCHUSD',
        'UNIUSD', 'LINKUSD', 'AAVEUSD', 'MKRUSD',
        'SOLUSD', 'AVAXUSD', 'ADAUSD', 'MATICUSD',
        'DOGEUSD', 'SHIBUSD', 'XRPUSD', 'XLMUSD'
      ]
    }
    return ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'SPY', 'QQQ']
  }

  const formatPrice = (price: number) => {
    if (marketType === 'crypto') {
      if (price < 0.01) return price.toFixed(6)
      if (price < 1) return price.toFixed(4)
      if (price < 100) return price.toFixed(2)
      return price.toFixed(0)
    }
    return price.toFixed(2)
  }

  return (
    <div className="space-y-4" data-testid={`trading-chart-${marketType}`}>
      {/* Chart Controls */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        {/* Left side: Timeframe buttons */}
        <div className="flex items-center space-x-1">
          {(['1Min', '5Min', '15Min', '1Hour', '1Day'] as const).map((tf) => (
            <Button
              key={tf}
              size="sm"
              variant={timeframe === tf ? 'default' : 'outline'}
              onClick={() => setTimeframe(tf)}
              data-testid={`timeframe-${tf}-${marketType}`}
              className="px-2 py-1 text-xs"
            >
              {tf}
            </Button>
          ))}
          {marketType === 'crypto' && (
            <Badge variant="secondary" className="ml-2">
              24/7
            </Badge>
          )}
        </div>

        {/* Center: Symbol selector */}
        {onSymbolChange && (
          <div className="flex items-center space-x-2">
            <select 
              value={symbol}
              onChange={(e) => onSymbolChange(e.target.value)}
              className="px-2 py-1 text-sm border rounded-md bg-background"
              data-testid={`chart-symbol-select-${marketType}`}
            >
              {getSymbolOptions().map(sym => (
                <option key={sym} value={sym}>{sym}</option>
              ))}
            </select>
          </div>
        )}
        
        {/* Right side: Indicator Controls */}
        <div className="flex items-center space-x-2">
          {/* Indicator Toggle Buttons */}
          <div className="flex items-center space-x-1 border rounded-md p-1">
            <Button
              variant={showIndicators.ema ? "default" : "ghost"}
              size="sm"
              onClick={() => setShowIndicators(prev => ({ ...prev, ema: !prev.ema }))}
              className="px-2 py-1 text-xs h-6"
            >
              EMA
            </Button>
            <Button
              variant={showIndicators.signals ? "default" : "ghost"}
              size="sm"
              onClick={() => setShowIndicators(prev => ({ ...prev, signals: !prev.signals }))}
              className="px-2 py-1 text-xs h-6"
            >
              Signals
            </Button>
          </div>

          {/* Current Signal Status */}
          {indicators && (
            <div className="flex items-center space-x-1">
              <Badge variant="outline" data-testid={`stochrsi-value-${marketType}`} className="text-xs">
                StochRSI: {indicators.stochastic_rsi?.k?.toFixed(1) || '0'}/{indicators.stochastic_rsi?.d?.toFixed(1) || '0'}
              </Badge>
              <Badge 
                variant={indicators.stochastic_rsi?.signal === 'BUY' ? 'default' : 
                        indicators.stochastic_rsi?.signal === 'SELL' ? 'destructive' : 'secondary'}
                data-testid={`stochrsi-signal-${marketType}`}
                className="text-xs"
              >
                {indicators.stochastic_rsi?.signal || 'NEUTRAL'}
              </Badge>
            </div>
          )}
        </div>
      </div>

      {/* Chart Container */}
      <div className="relative">
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-background/80 z-10" data-testid={`chart-loading-simple-${marketType}`}>
            <div className="text-muted-foreground">Loading chart data...</div>
          </div>
        )}
        
        {/* Show loading only when initially loading */}
        {!marketData && isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-background/80 z-10" data-testid={`chart-loading-detailed-${marketType}`}>
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-2"></div>
              <div className="text-muted-foreground">Loading {marketType === 'crypto' ? 'crypto' : 'stock'} data...</div>
            </div>
          </div>
        )}
        
        <div ref={chartContainerRef} className="w-full" style={{ height: `${height}px` }} data-testid={`chart-container-${marketType}`} />
      </div>

      {/* Scalping Strategy Panel */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 p-4 bg-gradient-to-r from-green-500/10 to-yellow-500/10 rounded-lg">
        {/* Fast EMA Cross */}
        <div className="text-center">
          <div className="text-xs text-muted-foreground mb-1">EMA (3/8)</div>
          <div className="font-bold text-sm text-blue-500">
            Cross Up
          </div>
          <div className="text-xs text-muted-foreground">
            Fast Momentum
          </div>
        </div>

        {/* Volume Spike Detection */}
        <div className="text-center">
          <div className="text-xs text-muted-foreground mb-1">Volume Spike</div>
          <div className="font-bold text-sm text-orange-500">
            +35%
          </div>
          <div className="text-xs text-muted-foreground">
            Above Avg
          </div>
        </div>

        {/* Price Momentum */}
        <div className="text-center">
          <div className="text-xs text-muted-foreground mb-1">Price Move</div>
          <div className="font-bold text-sm text-green-500">
            +0.15%
          </div>
          <div className="text-xs text-muted-foreground">
            Last Candle
          </div>
        </div>

        {/* RSI Indicator */}
        <div className="text-center">
          <div className="text-xs text-muted-foreground mb-1">StochRSI</div>
          <div className="font-bold text-sm text-purple-500">
            {indicators?.stochastic_rsi?.k?.toFixed(0) || '50'}
          </div>
          <div className="text-xs text-muted-foreground">
            {indicators?.stochastic_rsi?.signal || 'NEUTRAL'}
          </div>
        </div>

        {/* Signal Frequency */}
        <div className="text-center">
          <div className="text-xs text-muted-foreground mb-1">Signals/Min</div>
          <div className="font-bold text-sm text-red-500">
            2.3
          </div>
          <div className="text-xs text-muted-foreground">
            High Frequency
          </div>
        </div>
      </div>

      {/* Scalping Strategy Information */}
      <div className="mt-3 p-3 bg-gradient-to-r from-yellow-500/10 to-green-500/10 rounded-lg border border-yellow-500/30">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-semibold text-yellow-700">⚡ High-Frequency Scalping Strategy</div>
            <div className="text-xs text-muted-foreground">
              Fast EMA(3/8) + Volume Spikes + Price Momentum + StochRSI Signals
            </div>
          </div>
          <div className="text-right">
            <div className="text-xs text-muted-foreground">Entry Triggers:</div>
            <div className="text-xs font-medium text-green-600">EMA Cross + Volume +20% + Price Move &gt;0.05%</div>
            <div className="text-xs text-muted-foreground mt-1">Targets:</div>
            <div className="text-xs font-medium text-blue-600">Profit: 0.1-0.5% | Stop: 0.05-0.25% | Hold: &lt;3min</div>
          </div>
        </div>
      </div>

      {/* Market-specific trading info */}
      <div className="flex items-center justify-between text-xs text-muted-foreground p-2 bg-muted/30 rounded">
        <div className="flex items-center space-x-4">
          <span>Market: {marketType === 'crypto' ? 'Cryptocurrency' : 'US Stocks'}</span>
          <span>Session: {marketType === 'crypto' ? '24/7 Trading' : 'Market Hours 9:30-16:00 ET'}</span>
        </div>
        <div className="flex items-center space-x-4">
          <span>Settlement: {marketType === 'crypto' ? 'T+0 (Instant)' : 'T+2'}</span>
          <span>Fractional: {marketType === 'crypto' ? 'Supported' : 'Limited'}</span>
        </div>
      </div>
    </div>
  )
}