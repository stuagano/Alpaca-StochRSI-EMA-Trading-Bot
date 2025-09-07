"use client"

import { useState, useEffect, useRef } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { 
  TrendingUp, TrendingDown, DollarSign, Clock,
  Activity, CheckCircle, XCircle, Wifi, WifiOff
} from "lucide-react"
import { formatCurrency, formatPercent } from '@/lib/utils'
import { createChart, ColorType, IChartApi, ISeriesApi } from 'lightweight-charts'
import { useTradingContext } from '@/contexts/TradingContext'

// Trade interface now defined in TradingContext

interface LiveTradeFeedProps {
  marketType?: 'stocks' | 'crypto'
}

export function LiveTradeFeed({ marketType = 'crypto' }: LiveTradeFeedProps) {
  const { trades, metrics, wsConnected } = useTradingContext()
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const seriesRef = useRef<ISeriesApi<"Line"> | null>(null)
  const volumeSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null)

  // Data now comes from TradingContext - no need to fetch here

  // Initialize profit chart
  useEffect(() => {
    if (!chartContainerRef.current) return

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 300,
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#D1D5DB',
        fontSize: 12,
      },
      grid: {
        vertLines: { color: 'rgba(42, 46, 57, 0.3)' },
        horzLines: { color: 'rgba(42, 46, 57, 0.3)' },
      },
      rightPriceScale: {
        borderColor: 'rgba(42, 46, 57, 0.3)',
        scaleMargins: {
          top: 0.1,
          bottom: 0.1,
        },
      },
      timeScale: {
        timeVisible: true,
        secondsVisible: true,
        borderColor: 'rgba(42, 46, 57, 0.3)',
      },
    })

    // Add a line series for cumulative profit
    const lineSeries = chart.addLineSeries({
      color: '#10B981',
      lineWidth: 2,
      priceFormat: {
        type: 'price',
        precision: 2,
        minMove: 0.01,
      },
    })

    // Add a histogram series for individual trade profits
    const histogramSeries = chart.addHistogramSeries({
      color: '#10B981',
      priceFormat: {
        type: 'price',
        precision: 2,
        minMove: 0.01,
      },
    })

    chartRef.current = chart
    seriesRef.current = lineSeries
    volumeSeriesRef.current = histogramSeries

    // Handle resize
    const handleResize = () => {
      if (chartContainerRef.current && chart) {
        chart.applyOptions({ 
          width: chartContainerRef.current.clientWidth 
        })
      }
    }
    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      chart.remove()
    }
  }, [])

  // Update chart with trade data
  useEffect(() => {
    if (!seriesRef.current || !volumeSeriesRef.current || trades.length === 0) return

    // Sort trades by timestamp
    const sortedTrades = [...trades].sort((a, b) => 
      new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    )

    // Calculate cumulative profit over time
    let cumulativeProfit = 0
    const lineData: any[] = []
    const histogramData: any[] = []
    const usedTimestamps = new Set<number>()

    sortedTrades.forEach((trade, index) => {
      let time = Math.floor(new Date(trade.timestamp).getTime() / 1000)
      
      // Ensure unique timestamps by adding small increments if duplicate
      while (usedTimestamps.has(time)) {
        time += 1  // Add 1 second if timestamp already exists
      }
      usedTimestamps.add(time)
      
      // Add to cumulative profit if this trade has profit (sell trades)
      if (trade.side === 'sell' && trade.profit !== null && trade.profit !== undefined) {
        cumulativeProfit += trade.profit
        
        // Add histogram bar for this trade's profit
        histogramData.push({
          time: time as any,
          value: trade.profit,
          color: trade.profit >= 0 ? '#10B981' : '#EF4444'
        })
      }
      
      // Add cumulative profit point for all trades
      lineData.push({
        time: time as any,
        value: cumulativeProfit
      })
    })

    // Filter out any remaining duplicates and sort
    const uniqueLineData = lineData.filter((item, index, self) => 
      index === self.findIndex(t => t.time === item.time)
    ).sort((a, b) => a.time - b.time)
    
    const uniqueHistogramData = histogramData.filter((item, index, self) => 
      index === self.findIndex(t => t.time === item.time)
    ).sort((a, b) => a.time - b.time)

    // Update both series
    if (uniqueLineData.length > 0) {
      seriesRef.current.setData(uniqueLineData)
    }
    
    if (uniqueHistogramData.length > 0) {
      volumeSeriesRef.current.setData(uniqueHistogramData)
    }
  }, [trades])

  return (
    <div className="space-y-6">
      {/* Session Profit Chart */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Session Profit Chart</CardTitle>
              <CardDescription>Cumulative P&L (line) and individual trades (bars)</CardDescription>
            </div>
            <div className="flex items-center gap-4 text-sm">
              <div className="flex items-center gap-1">
                <div className="w-3 h-3 bg-green-500 rounded-full" />
                <span>Wins: {metrics.win_count}</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="w-3 h-3 bg-red-500 rounded-full" />
                <span>Losses: {metrics.loss_count}</span>
              </div>
              <Badge variant={metrics.session_profit >= 0 ? "default" : "destructive"} className="text-lg px-3 py-1">
                {metrics.session_profit >= 0 ? '+' : ''}{formatCurrency(metrics.session_profit)}
              </Badge>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div ref={chartContainerRef} className="w-full" />
        </CardContent>
      </Card>

      {/* Live Trade Feed */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Live Trade Activity</CardTitle>
              <CardDescription className="flex items-center gap-2">
                Recent executed trades
                {wsConnected ? (
                  <span className="flex items-center gap-1 text-green-500">
                    <Wifi className="h-3 w-3" />
                    <span className="text-xs">Live</span>
                  </span>
                ) : (
                  <span className="flex items-center gap-1 text-yellow-500">
                    <WifiOff className="h-3 w-3" />
                    <span className="text-xs">Reconnecting...</span>
                  </span>
                )}
              </CardDescription>
            </div>
            <Activity className="h-5 w-5 text-muted-foreground animate-pulse" />
          </div>
        </CardHeader>
        <CardContent>
          <ScrollArea className="h-[400px] pr-4">
            <div className="space-y-2">
              {trades.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  No trades executed yet. Waiting for signals...
                </div>
              ) : (
                trades.map((trade) => (
                  <div
                    key={trade.id}
                    className={`flex items-center justify-between p-3 rounded-lg border transition-all ${
                      // Only color SELL orders based on profit/loss
                      trade.side === 'sell' && trade.profit > 0 ? 'bg-green-500/5 border-green-500/20' : 
                      trade.side === 'sell' && trade.profit < 0 ? 'bg-red-500/5 border-red-500/20' : 
                      'bg-card border-border'  // Neutral for BUY orders
                    } hover:bg-accent/10`}
                  >
                    <div className="flex items-center gap-3">
                      {trade.side === 'buy' ? (
                        <div className="p-2 rounded-full bg-blue-500/10">
                          <TrendingUp className="h-4 w-4 text-blue-500" />
                        </div>
                      ) : (
                        <div className={`p-2 rounded-full ${
                          trade.profit >= 0 ? 'bg-green-500/10' : 'bg-red-500/10'
                        }`}>
                          <TrendingDown className={`h-4 w-4 ${
                            trade.profit >= 0 ? 'text-green-500' : 'text-red-500'
                          }`} />
                        </div>
                      )}
                      
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-semibold">{trade.symbol}</span>
                          <Badge 
                            variant={trade.side === 'buy' ? 'outline' : 
                                    (trade.profit >= 0 ? 'default' : 'destructive')}
                            className={trade.side === 'buy' ? 'border-blue-500 text-blue-500' : ''}
                          >
                            {trade.side.toUpperCase()}
                          </Badge>
                        </div>
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                          <span>{trade.qty} @ {formatCurrency(trade.price)}</span>
                          <span>•</span>
                          <Clock className="h-3 w-3" />
                          <span>{new Date(trade.timestamp).toLocaleTimeString()}</span>
                        </div>
                      </div>
                    </div>

                    <div className="text-right">
                      <div className="font-semibold">
                        {formatCurrency(trade.value)}
                      </div>
                      {/* Only show profit/loss for SELL orders */}
                      {trade.side === 'sell' && trade.profit !== undefined && (
                        <div className={`text-sm flex items-center gap-1 justify-end ${
                          trade.profit >= 0 ? 'text-green-500' : 'text-red-500'
                        }`}>
                          {trade.profit >= 0 ? (
                            <CheckCircle className="h-3 w-3" />
                          ) : (
                            <XCircle className="h-3 w-3" />
                          )}
                          <span>
                            {trade.profit >= 0 ? '+' : ''}{formatCurrency(trade.profit)}
                            {trade.profitPercent !== undefined && (
                              <span className="ml-1">
                                ({formatPercent(trade.profitPercent / 100)})
                              </span>
                            )}
                          </span>
                        </div>
                      )}
                      {/* Show "Entry" text for BUY orders */}
                      {trade.side === 'buy' && (
                        <div className="text-sm text-muted-foreground">
                          Entry
                        </div>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>
    </div>
  )
}