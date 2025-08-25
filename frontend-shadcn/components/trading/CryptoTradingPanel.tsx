"use client"

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { formatCurrency, formatPercent } from '@/lib/utils'
import { Bitcoin, TrendingUp, TrendingDown, Clock, DollarSign } from 'lucide-react'
import { toast } from 'sonner'
import { useCryptoAssets, useCryptoPositions, useCryptoQuote, useSubmitCryptoOrder, useCryptoWebSocket } from '@/hooks/useAlpaca'

interface CryptoAsset {
  symbol: string
  name: string
  tradable: boolean
  fractionable: boolean
  min_order_size?: number
}

interface CryptoPosition {
  symbol: string
  qty: string
  market_value: string
  cost_basis: string
  unrealized_pl: string
  unrealized_plpc: string
  current_price: string
  lastday_price?: string
  change_today?: string
}

interface CryptoQuote {
  symbol: string
  bid: number
  ask: number
  last: number
  timestamp: string
}

export function CryptoTradingPanel() {
  const [selectedSymbol, setSelectedSymbol] = useState<string>('BTC/USD')
  const [orderType, setOrderType] = useState<'market' | 'limit'>('market')
  const [orderSide, setOrderSide] = useState<'buy' | 'sell'>('buy')
  const [quantity, setQuantity] = useState<string>('')
  const [notionalAmount, setNotionalAmount] = useState<string>('')
  const [limitPrice, setLimitPrice] = useState<string>('')
  const [useNotional, setUseNotional] = useState<boolean>(true)
  const [realtimeData, setRealtimeData] = useState<any>({})

  // Data hooks
  const { data: assetsData, isLoading: assetsLoading } = useCryptoAssets()
  const { data: positionsData, isLoading: positionsLoading } = useCryptoPositions()
  const { data: currentQuote, isLoading: quoteLoading } = useCryptoQuote(selectedSymbol)
  const submitCryptoOrder = useSubmitCryptoOrder()

  // WebSocket for real-time data
  const { isConnected } = useCryptoWebSocket((data: any) => {
    setRealtimeData((prev: any) => ({
      ...prev,
      [data.symbol]: data
    }))
  })

  const assets = assetsData?.assets || []
  const positions = positionsData?.positions || []

  // Set default symbol when assets load
  useEffect(() => {
    if (assets.length > 0 && !selectedSymbol) {
      setSelectedSymbol(assets[0].symbol)
    }
  }, [assets, selectedSymbol])

  const handleSubmitOrder = async () => {
    if (!selectedSymbol) {
      toast.error('Please select a crypto asset')
      return
    }

    if (!useNotional && !quantity) {
      toast.error('Please enter quantity')
      return
    }

    if (useNotional && !notionalAmount) {
      toast.error('Please enter dollar amount')
      return
    }

    if (orderType === 'limit' && !limitPrice) {
      toast.error('Please enter limit price')
      return
    }

    try {
      const orderData = {
        symbol: selectedSymbol,
        side: orderSide,
        type: orderType,
        time_in_force: 'gtc',
        ...(useNotional 
          ? { notional: parseFloat(notionalAmount) }
          : { qty: parseFloat(quantity) }
        ),
        ...(orderType === 'limit' && { limit_price: parseFloat(limitPrice) })
      }

      await submitCryptoOrder.mutateAsync(orderData)
      
      // Show success toast with test ID
      const toastElement = document.createElement('div')
      toastElement.setAttribute('data-testid', 'success-toast')
      toast.success('Order submitted successfully')
      
      // Clear form
      setQuantity('')
      setNotionalAmount('')
      setLimitPrice('')
      
    } catch (error) {
      // Error handling is done in the mutation hook
    }
  }

  return (
    <Card className="w-full">
      <CardHeader className="flex flex-row items-center space-y-0 pb-2">
        <CardTitle className="flex items-center gap-2">
          <Bitcoin className="h-5 w-5 text-orange-500" />
          Cryptocurrency Trading
        </CardTitle>
        <div className="ml-auto flex items-center gap-2">
          <Badge variant="outline" className="flex items-center gap-1" data-testid="crypto-247-indicator">
            <Clock className="h-3 w-3" />
            24/7
          </Badge>
          <Badge variant={isConnected ? "default" : "destructive"} data-testid="crypto-connection-status">
            {isConnected ? "Live" : "Disconnected"}
          </Badge>
        </div>
      </CardHeader>

      <CardContent>
        <Tabs defaultValue="trade" className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="trade">Trade</TabsTrigger>
            <TabsTrigger value="positions" data-testid="crypto-positions-tab">Positions</TabsTrigger>
            <TabsTrigger value="market" data-testid="crypto-market-tab">Market</TabsTrigger>
          </TabsList>

          <TabsContent value="trade" className="space-y-4">
            {/* Asset Selection */}
            <div className="space-y-2">
              <Label htmlFor="crypto-symbol">Crypto Asset</Label>
              <Select value={selectedSymbol} onValueChange={setSelectedSymbol}>
                <SelectTrigger data-testid="crypto-symbol-select">
                  <SelectValue placeholder="Select crypto asset" />
                </SelectTrigger>
                <SelectContent data-testid="crypto-asset-selector">
                  {assets.map((asset) => (
                    <SelectItem key={asset.symbol} value={asset.symbol}>
                      {asset.symbol} - {asset.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Current Quote */}
            {currentQuote && (
              <Card className="p-3 bg-muted/50">
                <div className="flex items-center justify-between">
                  <div className="space-y-1">
                    <div className="text-sm text-muted-foreground">Current Price</div>
                    <div className="text-lg font-semibold" data-testid="crypto-current-price">
                      {formatCurrency(currentQuote.last)}
                    </div>
                  </div>
                  <div className="text-right space-y-1">
                    <div className="text-sm text-muted-foreground">Bid/Ask</div>
                    <div className="text-sm">
                      {formatCurrency(currentQuote.bid)} / {formatCurrency(currentQuote.ask)}
                    </div>
                  </div>
                </div>
              </Card>
            )}

            {/* Order Form */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Order Side</Label>
                <div className="flex gap-2">
                  <Button
                    variant={orderSide === 'buy' ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setOrderSide('buy')}
                    className="flex-1"
                    data-testid="crypto-buy-button"
                  >
                    Buy
                  </Button>
                  <Button
                    variant={orderSide === 'sell' ? 'destructive' : 'outline'}
                    size="sm"
                    onClick={() => setOrderSide('sell')}
                    className="flex-1"
                  >
                    Sell
                  </Button>
                </div>
              </div>

              <div className="space-y-2">
                <Label>Order Type</Label>
                <Select value={orderType} onValueChange={(value: 'market' | 'limit') => setOrderType(value)}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="market">Market</SelectItem>
                    <SelectItem value="limit">Limit</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Quantity/Notional Toggle */}
            <div className="flex items-center space-x-4">
              <Button
                variant={useNotional ? 'default' : 'outline'}
                size="sm"
                onClick={() => setUseNotional(true)}
                data-testid="dollar-mode-button"
              >
                <DollarSign className="h-4 w-4 mr-1" />
                Dollar Amount
              </Button>
              <Button
                variant={!useNotional ? 'default' : 'outline'}
                size="sm"
                onClick={() => setUseNotional(false)}
                data-testid="quantity-mode-button"
              >
                Quantity
              </Button>
            </div>

            {/* Amount Input */}
            {useNotional ? (
              <div className="space-y-2">
                <Label htmlFor="notional">Dollar Amount</Label>
                <Input
                  id="notional"
                  type="number"
                  placeholder="1000.00"
                  value={notionalAmount}
                  onChange={(e) => setNotionalAmount(e.target.value)}
                  data-testid="crypto-notional-input"
                />
                {parseFloat(notionalAmount) > 200000 && notionalAmount !== '' && (
                  <div className="text-red-500 text-sm" data-testid="notional-error">
                    Maximum dollar amount is $200,000
                  </div>
                )}
                <div className="text-xs text-muted-foreground">
                  Max: $200,000 per order
                </div>
              </div>
            ) : (
              <div className="space-y-2">
                <Label htmlFor="quantity">Quantity</Label>
                <Input
                  id="quantity"
                  type="number"
                  placeholder="0.1"
                  step="0.0001"
                  value={quantity}
                  onChange={(e) => setQuantity(e.target.value)}
                  data-testid="crypto-quantity-input"
                />
                {parseFloat(quantity) < 0.0001 && quantity !== '' && (
                  <div className="text-red-500 text-sm" data-testid="quantity-error">
                    Minimum quantity is 0.0001
                  </div>
                )}
                <div className="text-xs text-muted-foreground">
                  Min: 0.0001 (fractional orders supported)
                </div>
              </div>
            )}

            {/* Limit Price */}
            {orderType === 'limit' && (
              <div className="space-y-2">
                <Label htmlFor="limit-price">Limit Price</Label>
                <Input
                  id="limit-price"
                  type="number"
                  placeholder="60000.00"
                  value={limitPrice}
                  onChange={(e) => setLimitPrice(e.target.value)}
                />
              </div>
            )}

            {/* Submit Button */}
            <Button 
              onClick={handleSubmitOrder}
              disabled={submitCryptoOrder.isPending}
              className="w-full"
              variant={orderSide === 'buy' ? 'default' : 'destructive'}
              data-testid="crypto-submit-order-button"
            >
              {submitCryptoOrder.isPending ? 'Submitting...' : `${orderSide.toUpperCase()} ${selectedSymbol}`}
            </Button>

            {/* Trading Rules */}
            <Card className="p-3 bg-muted/50" data-testid="crypto-rules">
              <div className="space-y-2">
                <div className="font-medium">Crypto Trading Rules</div>
                <ul className="text-sm text-muted-foreground space-y-1">
                  <li data-testid="no-margin-notice">• No margin trading available</li>
                  <li data-testid="no-shorting-notice">• No short selling allowed</li>
                  <li data-testid="instant-settlement">• T+0 settlement (instant)</li>
                  <li>• Fractional shares supported</li>
                  <li>• 24/7 trading availability</li>
                </ul>
              </div>
            </Card>
          </TabsContent>

          <TabsContent value="positions" className="space-y-4" data-testid="crypto-positions-tab">
            <div data-testid="crypto-positions-container">
              {positions.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  No crypto positions
                </div>
              ) : (
              <div className="space-y-3">
                {positions.map((position, index) => {
                  const pl = parseFloat(position.unrealized_pl)
                  const plPercent = parseFloat(position.unrealized_plpc)
                  const isProfit = pl >= 0

                  return (
                    <Card key={index} className="p-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-semibold">{position.symbol}</span>
                            <Badge variant="outline">24/7</Badge>
                          </div>
                          <div className="text-sm text-muted-foreground">
                            {parseFloat(position.qty).toFixed(8)} @ {formatCurrency(parseFloat(position.cost_basis) / parseFloat(position.qty))}
                          </div>
                        </div>
                        <div className="text-right">
                          <div className={`font-semibold ${isProfit ? 'text-green-500' : 'text-red-500'}`}>
                            <span className="flex items-center">
                              {isProfit ? <TrendingUp className="h-4 w-4 mr-1" /> : <TrendingDown className="h-4 w-4 mr-1" />}
                              {formatCurrency(pl)}
                            </span>
                          </div>
                          <div className="text-sm text-muted-foreground">
                            {formatPercent(plPercent / 100)}
                          </div>
                        </div>
                      </div>
                    </Card>
                  )
                })}
                </div>
              )}
            </div>
          </TabsContent>

          <TabsContent value="market" className="space-y-4" data-testid="crypto-market-tab">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4" data-testid="crypto-market-grid">
              {assets.slice(0, 6).map((asset) => (
                <Card key={asset.symbol} className="p-4 cursor-pointer hover:bg-muted/50 transition-colors"
                      onClick={() => setSelectedSymbol(asset.symbol)}
                      data-testid={`crypto-pair-${asset.symbol}`}>
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-semibold">{asset.symbol}</div>
                      <div className="text-sm text-muted-foreground">{asset.name}</div>
                    </div>
                    <div className="flex items-center gap-1">
                      {asset.tradable && <Badge variant="outline" data-testid="tradable-badge">Tradable</Badge>}
                      {asset.fractionable && <Badge variant="secondary" data-testid="fractional-badge">Fractional</Badge>}
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}