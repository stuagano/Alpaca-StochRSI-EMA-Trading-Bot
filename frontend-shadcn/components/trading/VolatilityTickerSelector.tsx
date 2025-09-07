"use client"

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { formatPercent, formatCurrency } from '@/lib/utils'
import { 
  TrendingUp, TrendingDown, Zap, RefreshCw, 
  Target, Activity, BarChart3 
} from 'lucide-react'
import { MarketMode } from '@/lib/api/client'

interface VolatileTicker {
  symbol: string
  name: string
  price: number
  change_24h: number
  change_percent: number
  volume_24h: number
  volatility: number
  market_cap?: number
  last_updated: string
}

interface VolatilityTickerSelectorProps {
  marketType: MarketMode
  currentSymbol: string
  onSymbolChange: (symbol: string) => void
  onAutoSelectMostVolatile?: (symbol: string) => void
}

export function VolatilityTickerSelector({
  marketType,
  currentSymbol,
  onSymbolChange,
  onAutoSelectMostVolatile
}: VolatilityTickerSelectorProps) {
  const [volatileTickers, setVolatileTickers] = useState<VolatileTicker[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [autoSelectEnabled, setAutoSelectEnabled] = useState(false)
  const [lastUpdate, setLastUpdate] = useState<string>('')

  // Fetch volatile tickers from real API
  const fetchVolatileTickers = async () => {
    setIsLoading(true)
    try {
      if (marketType === 'crypto') {
        // Fetch crypto market data
        const response = await fetch('http://localhost:9000/api/crypto/movers?limit=8')
        const data = await response.json()
        
        if (data.movers && Array.isArray(data.movers)) {
          const tickers = data.movers.map((mover: any) => ({
            symbol: mover.symbol,
            name: mover.name || mover.symbol.replace('USD', ''),
            price: mover.current_price || mover.price,
            change_24h: mover.price_change_24h || 0,
            change_percent: mover.price_change_pct_24h || 0,
            volume_24h: mover.volume_24h || 0,
            volatility: Math.abs(mover.price_change_pct_24h || 0) / 100,
            market_cap: mover.market_cap,
            last_updated: mover.last_updated || new Date().toISOString()
          })).sort((a: VolatileTicker, b: VolatileTicker) => b.volatility - a.volatility).slice(0, 5)
          
          setVolatileTickers(tickers)
          setLastUpdate(new Date().toLocaleTimeString())
          
          // Auto-select most volatile if enabled
          if (autoSelectEnabled && tickers.length > 0 && onAutoSelectMostVolatile) {
            onAutoSelectMostVolatile(tickers[0].symbol)
          }
        }
      } else {
        // For stocks, use positions data to determine volatility
        const response = await fetch('http://localhost:9000/api/positions?market_mode=stocks')
        const data = await response.json()
        
        if (data.positions && Array.isArray(data.positions)) {
          const tickers = data.positions.map((position: any) => ({
            symbol: position.symbol,
            name: position.symbol, // Could be enhanced with company name lookup
            price: parseFloat(position.current_price),
            change_24h: parseFloat(position.unrealized_intraday_pl) / parseFloat(position.qty),
            change_percent: parseFloat(position.change_today) * 100,
            volume_24h: 1000000, // Mock volume for stocks
            volatility: Math.abs(parseFloat(position.change_today || '0')),
            last_updated: new Date().toISOString()
          })).sort((a: VolatileTicker, b: VolatileTicker) => b.volatility - a.volatility).slice(0, 5)
          
          setVolatileTickers(tickers)
          setLastUpdate(new Date().toLocaleTimeString())
          
          // Auto-select most volatile if enabled
          if (autoSelectEnabled && tickers.length > 0 && onAutoSelectMostVolatile) {
            onAutoSelectMostVolatile(tickers[0].symbol)
          }
        }
      }
    } catch (error) {
      console.error('Failed to fetch volatile tickers:', error)
      // Fallback to empty list - no fake data
      setVolatileTickers([])
    } finally {
      setIsLoading(false)
    }
  }

  // Initial fetch and periodic updates
  useEffect(() => {
    fetchVolatileTickers()
    const interval = setInterval(fetchVolatileTickers, 30000) // Update every 30 seconds
    return () => clearInterval(interval)
  }, [marketType, autoSelectEnabled])

  return (
    <Card className="w-full">
      <CardHeader className="flex flex-row items-center space-y-0 pb-2">
        <div className="flex items-center space-x-2">
          <Zap className="h-4 w-4 text-orange-500" />
          <CardTitle className="text-base">
            Top 5 Most Volatile {marketType === 'crypto' ? 'Crypto' : 'Stocks'}
          </CardTitle>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <Button
            variant={autoSelectEnabled ? "default" : "outline"}
            size="sm"
            onClick={() => setAutoSelectEnabled(!autoSelectEnabled)}
            className="text-xs"
          >
            <Target className="h-3 w-3 mr-1" />
            Auto-Select
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={fetchVolatileTickers}
            disabled={isLoading}
          >
            <RefreshCw className={`h-3 w-3 ${isLoading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </CardHeader>

      <CardContent className="space-y-2">
        {/* Last update time */}
        {lastUpdate && (
          <div className="text-xs text-muted-foreground text-center">
            Last updated: {lastUpdate}
          </div>
        )}

        {isLoading ? (
          <div className="text-center py-4">
            <RefreshCw className="h-4 w-4 animate-spin mx-auto mb-2" />
            <p className="text-sm text-muted-foreground">Scanning for volatility...</p>
          </div>
        ) : (
          <div className="space-y-2">
            {volatileTickers.map((ticker, index) => (
              <div
                key={ticker.symbol}
                className={`flex items-center justify-between p-3 rounded-lg border cursor-pointer transition-colors ${
                  currentSymbol === ticker.symbol
                    ? 'bg-primary/10 border-primary/20'
                    : 'hover:bg-muted/50'
                }`}
                onClick={() => onSymbolChange(ticker.symbol)}
              >
                {/* Left side: Rank, Symbol, Name */}
                <div className="flex items-center space-x-3">
                  <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                    index === 0 ? 'bg-yellow-500 text-white' :
                    index === 1 ? 'bg-gray-400 text-white' :
                    index === 2 ? 'bg-orange-600 text-white' :
                    'bg-muted text-muted-foreground'
                  }`}>
                    {index + 1}
                  </div>
                  <div>
                    <div className="flex items-center space-x-2">
                      <span className="font-semibold text-sm">{ticker.symbol}</span>
                      {currentSymbol === ticker.symbol && (
                        <Badge variant="default" className="text-xs">
                          Current
                        </Badge>
                      )}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {ticker.name}
                    </div>
                  </div>
                </div>

                {/* Center: Price and Change */}
                <div className="text-center">
                  <div className="text-sm font-medium">
                    {formatCurrency(ticker.price)}
                  </div>
                  <div className={`text-xs flex items-center justify-center ${
                    ticker.change_percent >= 0 ? 'text-green-500' : 'text-red-500'
                  }`}>
                    {ticker.change_percent >= 0 ? (
                      <TrendingUp className="h-3 w-3 mr-1" />
                    ) : (
                      <TrendingDown className="h-3 w-3 mr-1" />
                    )}
                    {formatPercent(ticker.change_percent / 100)}
                  </div>
                </div>

                {/* Right side: Volatility and Volume */}
                <div className="text-right">
                  <div className="flex items-center text-xs">
                    <Activity className="h-3 w-3 mr-1 text-orange-500" />
                    <span className="font-medium text-orange-600">
                      {formatPercent(ticker.volatility)}
                    </span>
                  </div>
                  <div className="text-xs text-muted-foreground flex items-center">
                    <BarChart3 className="h-3 w-3 mr-1" />
                    {marketType === 'crypto' ? (
                      `${(ticker.volume_24h / 1000000).toFixed(1)}M`
                    ) : (
                      `${(ticker.volume_24h / 1000000).toFixed(0)}M`
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Strategy info */}
        <div className="mt-4 pt-3 border-t">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>Strategy: Multi-Indicator Analysis</span>
            <span>Target: Highest Volatility</span>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}