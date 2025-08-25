"use client"

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { formatCurrency } from '@/lib/utils'
import { toast } from 'sonner'

interface OrderFormProps {
  defaultSymbol: string
  buyingPower: number
  onSubmit: (order: any) => void
}

export function OrderForm({ defaultSymbol, buyingPower, onSubmit }: OrderFormProps) {
  const [symbol, setSymbol] = useState(defaultSymbol)
  const [quantity, setQuantity] = useState('10')
  const [orderType, setOrderType] = useState<'market' | 'limit' | 'stop' | 'stop_limit'>('market')
  const [side, setSide] = useState<'buy' | 'sell'>('buy')
  const [timeInForce, setTimeInForce] = useState<'day' | 'gtc' | 'ioc' | 'fok'>('day')
  const [limitPrice, setLimitPrice] = useState('')
  const [stopPrice, setStopPrice] = useState('')
  const [extendedHours, setExtendedHours] = useState(false)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!symbol || !quantity) {
      toast.error('Please fill in all required fields')
      return
    }

    const order: any = {
      symbol: symbol.toUpperCase(),
      qty: parseInt(quantity),
      side,
      type: orderType,
      time_in_force: timeInForce,
      extended_hours: extendedHours
    }

    if (orderType === 'limit' || orderType === 'stop_limit') {
      if (!limitPrice) {
        toast.error('Limit price is required for limit orders')
        return
      }
      order.limit_price = parseFloat(limitPrice)
    }

    if (orderType === 'stop' || orderType === 'stop_limit') {
      if (!stopPrice) {
        toast.error('Stop price is required for stop orders')
        return
      }
      order.stop_price = parseFloat(stopPrice)
    }

    onSubmit(order)
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="symbol">Symbol</Label>
          <Input
            id="symbol"
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            placeholder="AAPL"
            className="uppercase"
          />
        </div>
        
        <div className="space-y-2">
          <Label htmlFor="quantity">Quantity</Label>
          <Input
            id="quantity"
            type="number"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            placeholder="10"
            min="1"
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label>Side</Label>
          <Select value={side} onValueChange={(value: 'buy' | 'sell') => setSide(value)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="buy">Buy</SelectItem>
              <SelectItem value="sell">Sell</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label>Order Type</Label>
          <Select value={orderType} onValueChange={(value: any) => setOrderType(value)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="market">Market</SelectItem>
              <SelectItem value="limit">Limit</SelectItem>
              <SelectItem value="stop">Stop</SelectItem>
              <SelectItem value="stop_limit">Stop Limit</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {(orderType === 'limit' || orderType === 'stop_limit') && (
        <div className="space-y-2">
          <Label htmlFor="limitPrice">Limit Price</Label>
          <Input
            id="limitPrice"
            type="number"
            value={limitPrice}
            onChange={(e) => setLimitPrice(e.target.value)}
            placeholder="0.00"
            step="0.01"
          />
        </div>
      )}

      {(orderType === 'stop' || orderType === 'stop_limit') && (
        <div className="space-y-2">
          <Label htmlFor="stopPrice">Stop Price</Label>
          <Input
            id="stopPrice"
            type="number"
            value={stopPrice}
            onChange={(e) => setStopPrice(e.target.value)}
            placeholder="0.00"
            step="0.01"
          />
        </div>
      )}

      <div className="space-y-2">
        <Label>Time in Force</Label>
        <Select value={timeInForce} onValueChange={(value: any) => setTimeInForce(value)}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="day">Day</SelectItem>
            <SelectItem value="gtc">Good Till Cancelled</SelectItem>
            <SelectItem value="ioc">Immediate or Cancel</SelectItem>
            <SelectItem value="fok">Fill or Kill</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Switch
            id="extended"
            checked={extendedHours}
            onCheckedChange={setExtendedHours}
          />
          <Label htmlFor="extended">Extended Hours</Label>
        </div>
        <div className="text-sm text-muted-foreground">
          Buying Power: {formatCurrency(buyingPower)}
        </div>
      </div>

      <Button type="submit" className="w-full" variant={side === 'buy' ? 'default' : 'destructive'}>
        {side === 'buy' ? 'Buy' : 'Sell'} {quantity} {symbol}
      </Button>
    </form>
  )
}