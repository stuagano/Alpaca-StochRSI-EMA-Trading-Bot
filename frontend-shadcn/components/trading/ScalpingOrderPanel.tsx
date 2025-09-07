"use client"

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Separator } from "@/components/ui/separator"
import { Badge } from "@/components/ui/badge"
import { 
  Target, DollarSign, Percent, Clock, TrendingUp, 
  TrendingDown, Settings, AlertCircle 
} from "lucide-react"
import { formatCurrency } from '@/lib/utils'
import { useSubmitOrder } from '@/hooks/useAlpaca'
import { toast } from 'sonner'

interface ScalpingOrderPanelProps {
  selectedSymbol: string
  onSymbolChange: (symbol: string) => void
  realtimePrice?: number
  maxPositionSize: number
}

const CRYPTO_SYMBOLS = [
  'BTCUSD', 'ETHUSD', 'LTCUSD', 'BCHUSD',
  'UNIUSD', 'LINKUSD', 'AAVEUSD', 'MKRUSD',
  'SOLUSD', 'AVAXUSD', 'ADAUSD', 'MATICUSD',
  'DOGEUSD', 'SHIBUSD', 'XRPUSD'
]

export function ScalpingOrderPanel({
  selectedSymbol,
  onSymbolChange,
  realtimePrice = 45000,
  maxPositionSize
}: ScalpingOrderPanelProps) {
  
  const [orderType, setOrderType] = useState<'market' | 'limit'>('market')
  const [quantity, setQuantity] = useState(0.01)
  const [limitPrice, setLimitPrice] = useState(realtimePrice)
  const [takeProfitPct, setTakeProfitPct] = useState(0.5) // 0.5%
  const [stopLossPct, setStopLossPct] = useState(0.3) // 0.3%
  
  const submitOrder = useSubmitOrder('crypto')
  
  const calculateOrderValue = () => quantity * (orderType === 'limit' ? limitPrice : realtimePrice)
  const calculateTakeProfit = (side: 'buy' | 'sell') => {
    const basePrice = orderType === 'limit' ? limitPrice : realtimePrice
    return side === 'buy' 
      ? basePrice * (1 + takeProfitPct / 100)
      : basePrice * (1 - takeProfitPct / 100)
  }
  const calculateStopLoss = (side: 'buy' | 'sell') => {
    const basePrice = orderType === 'limit' ? limitPrice : realtimePrice
    return side === 'buy'
      ? basePrice * (1 - stopLossPct / 100) 
      : basePrice * (1 + stopLossPct / 100)
  }

  const placeBracketOrder = async (side: 'buy' | 'sell') => {
    try {
      const orderData = {
        symbol: selectedSymbol,
        qty: quantity,
        side,
        type: orderType,
        time_in_force: 'gtc' as const,
        ...(orderType === 'limit' && { limit_price: limitPrice }),
        // Add bracket orders for take profit and stop loss
        order_class: 'bracket' as const,
        take_profit: { limit_price: calculateTakeProfit(side) },
        stop_loss: { stop_price: calculateStopLoss(side) }
      }
      
      await submitOrder.mutateAsync(orderData)
      toast.success(`Bracket ${side.toUpperCase()} order placed for ${selectedSymbol}`)
    } catch (error) {
      toast.error(`Failed to place ${side} order`)
      console.error('Order placement failed:', error)
    }
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-base">
          <Target className="h-4 w-4" />
          Order Panel
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        
        {/* Symbol Selection */}
        <div className="space-y-2">
          <Label className="text-sm">Symbol</Label>
          <Select value={selectedSymbol} onValueChange={onSymbolChange}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {CRYPTO_SYMBOLS.map(symbol => (
                <SelectItem key={symbol} value={symbol}>
                  {symbol}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>Current Price:</span>
            <span className="font-mono">{formatCurrency(realtimePrice)}</span>
          </div>
        </div>

        <Separator />

        {/* Order Type */}
        <div className="space-y-2">
          <Label className="text-sm">Order Type</Label>
          <Tabs value={orderType} onValueChange={(value) => setOrderType(value as 'market' | 'limit')}>
            <TabsList className="grid grid-cols-2 w-full">
              <TabsTrigger value="market">Market</TabsTrigger>
              <TabsTrigger value="limit">Limit</TabsTrigger>
            </TabsList>
          </Tabs>
        </div>

        {/* Quantity */}
        <div className="space-y-2">
          <Label className="text-sm">Quantity</Label>
          <div className="flex gap-2">
            <Input
              type="number"
              value={quantity}
              onChange={(e) => setQuantity(parseFloat(e.target.value) || 0)}
              min="0.001"
              step="0.001"
              className="font-mono"
            />
            <Button
              variant="outline"
              size="sm"
              onClick={() => setQuantity(maxPositionSize / realtimePrice)}
            >
              Max
            </Button>
          </div>
          <div className="text-xs text-muted-foreground">
            Order Value: {formatCurrency(calculateOrderValue())}
          </div>
        </div>

        {/* Limit Price (if limit order) */}
        {orderType === 'limit' && (
          <div className="space-y-2">
            <Label className="text-sm">Limit Price</Label>
            <Input
              type="number"
              value={limitPrice}
              onChange={(e) => setLimitPrice(parseFloat(e.target.value) || realtimePrice)}
              min="0"
              step="0.01"
              className="font-mono"
            />
          </div>
        )}

        <Separator />

        {/* Scalping Targets */}
        <div className="space-y-3">
          <Label className="text-sm">Scalping Targets</Label>
          
          <div className="grid grid-cols-2 gap-2">
            <div className="space-y-1">
              <Label className="text-xs text-green-600">Take Profit %</Label>
              <Input
                type="number"
                value={takeProfitPct}
                onChange={(e) => setTakeProfitPct(parseFloat(e.target.value) || 0.5)}
                min="0.1"
                max="2"
                step="0.1"
                className="text-xs"
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs text-red-600">Stop Loss %</Label>
              <Input
                type="number"
                value={stopLossPct}
                onChange={(e) => setStopLossPct(parseFloat(e.target.value) || 0.3)}
                min="0.05"
                max="1"
                step="0.05"
                className="text-xs"
              />
            </div>
          </div>

          <div className="p-2 bg-muted/30 rounded text-xs space-y-1">
            <div className="flex justify-between text-green-600">
              <span>Buy TP:</span>
              <span className="font-mono">{formatCurrency(calculateTakeProfit('buy'))}</span>
            </div>
            <div className="flex justify-between text-red-600">
              <span>Buy SL:</span>
              <span className="font-mono">{formatCurrency(calculateStopLoss('buy'))}</span>
            </div>
          </div>
        </div>

        <Separator />

        {/* Order Buttons */}
        <div className="space-y-2">
          <Button
            onClick={() => placeBracketOrder('buy')}
            className="w-full bg-green-600 hover:bg-green-700"
            disabled={submitOrder.isPending}
          >
            <TrendingUp className="mr-2 h-4 w-4" />
            BUY with Bracket
          </Button>
          
          <Button
            onClick={() => placeBracketOrder('sell')}
            variant="destructive"
            className="w-full"
            disabled={submitOrder.isPending}
          >
            <TrendingDown className="mr-2 h-4 w-4" />
            SELL with Bracket
          </Button>
        </div>

        {/* Risk Info */}
        <div className="p-2 bg-yellow-500/10 border border-yellow-500/20 rounded">
          <div className="flex items-center gap-2 text-yellow-600">
            <AlertCircle className="h-3 w-3" />
            <span className="text-xs font-medium">Scalping Mode Active</span>
          </div>
          <p className="text-xs text-yellow-600/80 mt-1">
            Orders include automatic take profit and stop loss
          </p>
        </div>

      </CardContent>
    </Card>
  )
}