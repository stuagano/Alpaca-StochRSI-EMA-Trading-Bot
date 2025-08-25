"use client"

import { Order } from '@/types/alpaca'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { formatCurrency } from '@/lib/utils'
import { X, Clock, CheckCircle, XCircle } from 'lucide-react'

interface OrdersTableProps {
  orders: Order[]
  onCancel: (orderId: string) => void
}

export function OrdersTable({ orders, onCancel }: OrdersTableProps) {
  if (orders.length === 0) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          No pending orders
        </CardContent>
      </Card>
    )
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'pending':
      case 'new':
        return <Clock className="h-4 w-4 text-yellow-500" />
      case 'filled':
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'cancelled':
      case 'rejected':
        return <XCircle className="h-4 w-4 text-red-500" />
      default:
        return null
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending':
      case 'new':
        return 'default'
      case 'filled':
        return 'success'
      case 'cancelled':
      case 'rejected':
        return 'destructive'
      default:
        return 'secondary'
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Orders</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {orders.map((order) => (
            <div 
              key={order.id}
              className="flex items-center justify-between p-4 border rounded-lg"
            >
              <div className="flex items-center space-x-4">
                <div className="flex flex-col">
                  <div className="flex items-center space-x-2">
                    <span className="font-semibold">{order.symbol}</span>
                    <Badge variant={order.side === 'buy' ? 'default' : 'destructive'}>
                      {order.side.toUpperCase()}
                    </Badge>
                    <Badge variant="outline">
                      {order.order_type}
                    </Badge>
                  </div>
                  <div className="flex items-center space-x-4 text-sm text-muted-foreground">
                    <span>{order.qty} shares</span>
                    {order.limit_price && (
                      <span>Limit: {formatCurrency(parseFloat(order.limit_price))}</span>
                    )}
                    {order.stop_price && (
                      <span>Stop: {formatCurrency(parseFloat(order.stop_price))}</span>
                    )}
                    <span>TIF: {order.time_in_force}</span>
                  </div>
                </div>
              </div>

              <div className="flex items-center space-x-4">
                <div className="flex items-center space-x-2">
                  {getStatusIcon(order.status)}
                  <Badge variant={getStatusColor(order.status) as any}>
                    {order.status}
                  </Badge>
                </div>
                {['pending', 'new', 'partially_filled'].includes(order.status) && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => onCancel(order.id)}
                  >
                    <X className="h-4 w-4" />
                    Cancel
                  </Button>
                )}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}