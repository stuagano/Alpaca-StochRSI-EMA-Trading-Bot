"use client"

import { useEffect, useRef, useState } from 'react'
import { createChart, ColorType, IChartApi, ISeriesApi } from 'lightweight-charts'
import { useMarketData, useIndicators } from '@/hooks/useAlpaca'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'

interface TradingChartProps {
  symbol: string
  realtimeData?: any
}

export function TradingChart({ symbol, realtimeData }: TradingChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const candlestickSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null)
  const emaShortSeriesRef = useRef<ISeriesApi<'Line'> | null>(null)
  const emaLongSeriesRef = useRef<ISeriesApi<'Line'> | null>(null)
  
  const [timeframe, setTimeframe] = useState<'1Min' | '5Min' | '15Min' | '1Hour' | '1Day'>('5Min')
  const { data: marketData, isLoading } = useMarketData(symbol, timeframe)
  const { data: indicators } = useIndicators(symbol)

  useEffect(() => {
    if (!chartContainerRef.current || !marketData) return

    // Create chart
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
      height: 400,
      timeScale: {
        borderColor: '#2a2e39',
        timeVisible: true,
        secondsVisible: false,
      },
      rightPriceScale: {
        borderColor: '#2a2e39',
      },
    })

    // Add candlestick series
    const candlestickSeries = chart.addCandlestickSeries({
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderVisible: false,
      wickUpColor: '#26a69a',
      wickDownColor: '#ef5350',
    })

    // Add volume series
    const volumeSeries = chart.addHistogramSeries({
      color: '#26a69a',
      priceFormat: {
        type: 'volume',
      },
      priceScaleId: '',
    })

    // Add EMA lines
    const emaShortSeries = chart.addLineSeries({
      color: '#2962FF',
      lineWidth: 2,
      title: 'EMA 9',
    })

    const emaLongSeries = chart.addLineSeries({
      color: '#FF6D00',
      lineWidth: 2,
      title: 'EMA 21',
    })

    // Set price scale
    chart.priceScale('').applyOptions({
      scaleMargins: {
        top: 0.8,
        bottom: 0,
      },
    })

    // Format and set data
    // Sort data by time in ascending order (oldest first)
    const sortedData = [...marketData].sort((a, b) => 
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

    candlestickSeries.setData(candleData)
    volumeSeries.setData(volumeData)

    // Calculate and set EMA data
    const calculateEMA = (data: number[], period: number) => {
      const k = 2 / (period + 1)
      const ema = [data[0]]
      for (let i = 1; i < data.length; i++) {
        ema.push(data[i] * k + ema[i - 1] * (1 - k))
      }
      return ema
    }

    const closes = sortedData.map(bar => bar.c)
    const emaShort = calculateEMA(closes, 9)
    const emaLong = calculateEMA(closes, 21)

    const emaShortData = sortedData.map((bar, i) => ({
      time: new Date(bar.t).getTime() / 1000 as any,
      value: emaShort[i],
    }))

    const emaLongData = sortedData.map((bar, i) => ({
      time: new Date(bar.t).getTime() / 1000 as any,
      value: emaLong[i],
    }))

    emaShortSeries.setData(emaShortData)
    emaLongSeries.setData(emaLongData)

    // Store refs
    chartRef.current = chart
    candlestickSeriesRef.current = candlestickSeries
    volumeSeriesRef.current = volumeSeries
    emaShortSeriesRef.current = emaShortSeries
    emaLongSeriesRef.current = emaLongSeries

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
      chart.remove()
    }
  }, [marketData, symbol])

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

  return (
    <div className="space-y-4" data-testid="trading-chart">
      {/* Chart Controls */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          {(['1Min', '5Min', '15Min', '1Hour', '1Day'] as const).map((tf) => (
            <Button
              key={tf}
              size="sm"
              variant={timeframe === tf ? 'default' : 'outline'}
              onClick={() => setTimeframe(tf)}
              data-testid={`timeframe-${tf}`}
            >
              {tf}
            </Button>
          ))}
        </div>
        
        {indicators && (
          <div className="flex items-center space-x-2" data-testid="indicators-panel">
            <Badge variant="outline" data-testid="stochrsi-value">
              StochRSI: {indicators.stochastic_rsi?.k?.toFixed(2) || '0'}/{indicators.stochastic_rsi?.d?.toFixed(2) || '0'}
            </Badge>
            <Badge 
              variant={indicators.stochastic_rsi?.signal === 'BUY' ? 'default' : 
                      indicators.stochastic_rsi?.signal === 'SELL' ? 'destructive' : 'secondary'}
              data-testid="stochrsi-signal"
            >
              {indicators.stochastic_rsi?.signal || 'NEUTRAL'}
            </Badge>
          </div>
        )}
      </div>

      {/* Chart Container */}
      <div className="relative">
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-background/80 z-10" data-testid="chart-loading">
            <div className="text-muted-foreground">Loading chart data...</div>
          </div>
        )}
        
        {/* Error State */}
        {!isLoading && !marketData && (
          <div className="absolute inset-0 flex items-center justify-center bg-background/80 z-10" data-testid="chart-error">
            <div className="text-red-500">Failed to load chart data</div>
          </div>
        )}
        
        {/* Empty State */}
        {!isLoading && marketData && marketData.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center bg-background/80 z-10" data-testid="chart-empty-state">
            <div className="text-muted-foreground">No chart data available</div>
          </div>
        )}
        
        <div ref={chartContainerRef} className="w-full" data-testid="chart-container" />
      </div>

      {/* Indicator Panel */}
      {indicators && (
        <div className="grid grid-cols-3 gap-4 p-4 bg-muted/50 rounded-lg">
          <div>
            <div className="text-sm text-muted-foreground">StochRSI Signal</div>
            <div className={`font-medium ${
              indicators.stochastic_rsi?.signal === 'BUY' ? 'text-green-500' : 
              indicators.stochastic_rsi?.signal === 'SELL' ? 'text-red-500' : 
              'text-gray-500'
            }`}>
              {indicators.stochastic_rsi?.signal || 'NEUTRAL'}
            </div>
          </div>
          <div>
            <div className="text-sm text-muted-foreground">RSI</div>
            <div className={`font-medium ${
              indicators.rsi?.current > 70 ? 'text-red-500' : 
              indicators.rsi?.current < 30 ? 'text-green-500' : 
              'text-gray-500'
            }`} data-testid="rsi-value">
              {indicators.rsi?.current?.toFixed(2) || 'N/A'}
            </div>
          </div>
          <div>
            <div className="text-sm text-muted-foreground">MACD</div>
            <div className={`font-medium ${
              indicators.macd?.histogram > 0 ? 'text-green-500' : 
              indicators.macd?.histogram < 0 ? 'text-red-500' : 
              'text-gray-500'
            }`}>
              {indicators.macd?.histogram?.toFixed(4) || 'N/A'}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}