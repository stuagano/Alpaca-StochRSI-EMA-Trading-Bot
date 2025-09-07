"use client"

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Switch } from "@/components/ui/switch"
import { 
  TrendingUp, TrendingDown, Search, Zap, Activity, DollarSign,
  Volume2, RefreshCw, CheckCircle, XCircle, AlertCircle
} from "lucide-react"
import { formatCurrency, formatPercent, cn } from '@/lib/utils'
import { toast } from 'sonner'

interface CryptoAsset {
  symbol: string
  name: string
  current_price: number
  price_change_24h: number
  price_change_pct_24h: number
  volume_24h: number
  market_cap?: number
  high_24h: number
  low_24h: number
  trading_enabled: boolean
  volatility: number
  last_updated?: string
}

interface CryptoMarketScreenerProps {
  onSymbolSelect?: (symbol: string) => void
  onTradingToggle?: (symbol: string, enabled: boolean) => void
}

export function CryptoMarketScreener({ onSymbolSelect, onTradingToggle }: CryptoMarketScreenerProps) {
  const [assets, setAssets] = useState<CryptoAsset[]>([])
  const [topGainers, setTopGainers] = useState<CryptoAsset[]>([])
  const [topLosers, setTopLosers] = useState<CryptoAsset[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [lastUpdated, setLastUpdated] = useState<string>('')
  const [marketOverview, setMarketOverview] = useState<any>({})

  const fetchMarketData = async () => {
    setLoading(true)
    try {
      // Fetch all crypto assets
      const marketResponse = await fetch('http://localhost:9000/api/crypto/market')
      const marketData = await marketResponse.json()
      
      if (marketData.market) {
        setAssets(marketData.market)
        setLastUpdated(marketData.timestamp || new Date().toISOString())
      }

      // Fetch top movers
      const moversResponse = await fetch('http://localhost:9000/api/crypto/movers?limit=10')
      const moversData = await moversResponse.json()
      
      if (moversData.movers) {
        // Split movers into gainers and losers based on price change
        const allMovers = moversData.movers
        const gainers = allMovers.filter((asset: CryptoAsset) => asset.price_change_pct_24h > 0)
          .sort((a: CryptoAsset, b: CryptoAsset) => b.price_change_pct_24h - a.price_change_pct_24h)
          .slice(0, 10)
        const losers = allMovers.filter((asset: CryptoAsset) => asset.price_change_pct_24h < 0)
          .sort((a: CryptoAsset, b: CryptoAsset) => a.price_change_pct_24h - b.price_change_pct_24h)
          .slice(0, 10)
        
        setTopGainers(gainers)
        setTopLosers(losers)
        setMarketOverview({
          total_assets: allMovers.length,
          trading_enabled_count: allMovers.filter(asset => asset.trading_enabled).length,
          gainers_count: gainers.length,
          losers_count: losers.length
        })
      }

    } catch (error) {
      console.error('Failed to fetch market data:', error)
      toast.error('Failed to load crypto market data')
    } finally {
      setLoading(false)
    }
  }

  const toggleTrading = async (symbol: string, enabled: boolean) => {
    try {
      const endpoint = enabled 
        ? 'http://localhost:9000/api/crypto/enable-trading'
        : 'http://localhost:9000/api/crypto/disable-trading'
      
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbols: [symbol] })
      })

      const result = await response.json()
      
      if (result.success) {
        // Update local state
        setAssets(prev => prev.map(asset => 
          asset.symbol === symbol 
            ? { ...asset, trading_enabled: enabled }
            : asset
        ))
        
        // Update top movers if present
        setTopGainers(prev => prev.map(asset => 
          asset.symbol === symbol 
            ? { ...asset, trading_enabled: enabled }
            : asset
        ))
        setTopLosers(prev => prev.map(asset => 
          asset.symbol === symbol 
            ? { ...asset, trading_enabled: enabled }
            : asset
        ))

        toast.success(`Trading ${enabled ? 'enabled' : 'disabled'} for ${symbol}`)
        
        if (onTradingToggle) {
          onTradingToggle(symbol, enabled)
        }
      } else {
        toast.error(`Failed to ${enabled ? 'enable' : 'disable'} trading for ${symbol}`)
      }
    } catch (error) {
      console.error('Failed to toggle trading:', error)
      toast.error('Failed to update trading settings')
    }
  }

  useEffect(() => {
    fetchMarketData()
    
    // Auto-refresh every 60 seconds
    const interval = setInterval(fetchMarketData, 60000)
    return () => clearInterval(interval)
  }, [])

  // Filter assets based on search query
  const filteredAssets = assets.filter(asset => 
    asset.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
    asset.name.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const AssetRow = ({ asset, showTradingToggle = true }: { asset: CryptoAsset; showTradingToggle?: boolean }) => (
    <div className="flex items-center justify-between p-4 border rounded-lg hover:bg-muted/50">
      <div className="flex items-center space-x-4">
        <div className="w-8 h-8 bg-gradient-to-r from-orange-500 to-yellow-500 rounded-full flex items-center justify-center text-white font-bold text-sm">
          {asset.name.slice(0, 2).toUpperCase()}
        </div>
        <div>
          <div className="font-medium">{asset.symbol}</div>
          <div className="text-sm text-muted-foreground">{asset.name}</div>
        </div>
      </div>
      
      <div className="flex items-center space-x-4">
        <div className="text-right">
          <div className="font-medium">{formatCurrency(asset.current_price)}</div>
          <div className={cn("text-sm flex items-center space-x-1", 
            asset.price_change_pct_24h >= 0 ? "text-green-500" : "text-red-500"
          )}>
            {asset.price_change_pct_24h >= 0 ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
            <span>{formatPercent(asset.price_change_pct_24h / 100)}</span>
          </div>
        </div>
        
        <div className="text-right">
          <div className="text-sm text-muted-foreground">Volume</div>
          <div className="font-medium">{formatCurrency(asset.volume_24h)}</div>
        </div>
        
        <div className="text-right">
          <div className="text-sm text-muted-foreground">Volatility</div>
          <div className="font-medium">{formatPercent(asset.volatility)}</div>
        </div>

        {showTradingToggle && (
          <div className="flex items-center space-x-2">
            <Switch
              checked={asset.trading_enabled}
              onCheckedChange={(checked) => toggleTrading(asset.symbol, checked)}
            />
            <div className="text-xs text-muted-foreground">
              {asset.trading_enabled ? 'Active' : 'Inactive'}
            </div>
          </div>
        )}
        
        <Button
          size="sm"
          variant="outline"
          onClick={() => onSymbolSelect && onSymbolSelect(asset.symbol)}
        >
          View
        </Button>
      </div>
    </div>
  )

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Crypto Market Screener</h2>
          <p className="text-muted-foreground">
            {assets.length} assets • Last updated: {new Date(lastUpdated).toLocaleTimeString()}
          </p>
        </div>
        <Button 
          onClick={fetchMarketData} 
          disabled={loading}
          variant="outline"
          size="sm"
        >
          <RefreshCw className={cn("h-4 w-4 mr-2", loading && "animate-spin")} />
          {loading ? 'Updating...' : 'Refresh'}
        </Button>
      </div>

      {/* Market Overview */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <Activity className="h-4 w-4 text-blue-500" />
              <div className="text-sm text-muted-foreground">Total Assets</div>
            </div>
            <div className="text-2xl font-bold">{marketOverview.total_assets || assets.length}</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <Zap className="h-4 w-4 text-green-500" />
              <div className="text-sm text-muted-foreground">Trading Enabled</div>
            </div>
            <div className="text-2xl font-bold">{marketOverview.trading_enabled_count || 0}</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <TrendingUp className="h-4 w-4 text-green-500" />
              <div className="text-sm text-muted-foreground">Gainers</div>
            </div>
            <div className="text-2xl font-bold text-green-500">{marketOverview.gainers_count || 0}</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <TrendingDown className="h-4 w-4 text-red-500" />
              <div className="text-sm text-muted-foreground">Losers</div>
            </div>
            <div className="text-2xl font-bold text-red-500">{marketOverview.losers_count || 0}</div>
          </CardContent>
        </Card>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4" />
        <Input
          placeholder="Search cryptocurrencies..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-10"
        />
      </div>

      {/* Market Data Tabs */}
      <Tabs defaultValue="top-movers" className="space-y-4">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="top-movers">Top Movers</TabsTrigger>
          <TabsTrigger value="all-assets">All Assets</TabsTrigger>
          <TabsTrigger value="active-trading">Active Trading</TabsTrigger>
        </TabsList>

        <TabsContent value="top-movers" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            {/* Top Gainers */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <TrendingUp className="h-4 w-4 text-green-500" />
                  <span>Top 10 Gainers</span>
                </CardTitle>
                <CardDescription>Biggest winners in the last 24 hours</CardDescription>
              </CardHeader>
              <CardContent className="space-y-2">
                {loading ? (
                  <div className="text-center py-4 text-muted-foreground">Loading...</div>
                ) : topGainers.length > 0 ? (
                  topGainers.map((asset) => (
                    <AssetRow key={asset.symbol} asset={asset} />
                  ))
                ) : (
                  <div className="text-center py-4 text-muted-foreground">No data available</div>
                )}
              </CardContent>
            </Card>

            {/* Top Losers */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <TrendingDown className="h-4 w-4 text-red-500" />
                  <span>Top 10 Losers</span>
                </CardTitle>
                <CardDescription>Biggest losers in the last 24 hours</CardDescription>
              </CardHeader>
              <CardContent className="space-y-2">
                {loading ? (
                  <div className="text-center py-4 text-muted-foreground">Loading...</div>
                ) : topLosers.length > 0 ? (
                  topLosers.map((asset) => (
                    <AssetRow key={asset.symbol} asset={asset} />
                  ))
                ) : (
                  <div className="text-center py-4 text-muted-foreground">No data available</div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="all-assets" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>All Crypto Assets ({filteredAssets.length})</CardTitle>
              <CardDescription>Complete list of available cryptocurrencies</CardDescription>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="text-center py-8 text-muted-foreground">Loading assets...</div>
              ) : filteredAssets.length > 0 ? (
                <div className="space-y-2 max-h-96 overflow-y-auto">
                  {filteredAssets.map((asset) => (
                    <AssetRow key={asset.symbol} asset={asset} />
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  {searchQuery ? 'No assets match your search' : 'No assets available'}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="active-trading" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Zap className="h-4 w-4 text-green-500" />
                <span>Active Trading Assets</span>
              </CardTitle>
              <CardDescription>Cryptocurrencies currently enabled for automated trading</CardDescription>
            </CardHeader>
            <CardContent>
              {(() => {
                const activeAssets = filteredAssets.filter(asset => asset.trading_enabled)
                return loading ? (
                  <div className="text-center py-8 text-muted-foreground">Loading...</div>
                ) : activeAssets.length > 0 ? (
                  <div className="space-y-2">
                    {activeAssets.map((asset) => (
                      <AssetRow key={asset.symbol} asset={asset} showTradingToggle={false} />
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-muted-foreground">
                    <AlertCircle className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
                    <p>No assets currently enabled for trading</p>
                    <p className="text-sm">Use the switches in the "All Assets" tab to enable trading</p>
                  </div>
                )
              })()}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}