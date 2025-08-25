"use client"

import { Position } from '@/types/alpaca'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { formatCurrency, formatPercent } from '@/lib/utils'
import { X, TrendingUp, TrendingDown } from 'lucide-react'

interface PositionsTableProps {
  positions: Position[]
  onClose: (symbol: string) => void
  onSelect: (symbol: string) => void
  realtimeData: Record<string, any>
}

export function PositionsTable({ 
  positions, 
  onClose, 
  onSelect,
  realtimeData 
}: PositionsTableProps) {
  if (positions.length === 0) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          No open positions
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Open Positions</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {positions.map((position, index) => {
            const pl = parseFloat(position.unrealized_pl)
            const plPercent = parseFloat(position.unrealized_plpc)
            const isProfit = pl >= 0
            const realtime = realtimeData[position.symbol]

            return (
              <div 
                key={position.asset_id || position.symbol || `position-${index}`}
                className="flex items-center justify-between p-4 border rounded-lg hover:bg-muted/50 cursor-pointer transition-colors"
                onClick={() => onSelect(position.symbol)}
              >
                <div className="flex items-center space-x-4">
                  <div className="flex flex-col">
                    <div className="flex items-center space-x-2">
                      <span className="font-semibold text-lg">{position.symbol}</span>
                      <Badge variant={position.side === 'long' ? 'default' : 'destructive'}>
                        {position.side.toUpperCase()}
                      </Badge>
                      {realtime && (
                        <Badge variant="outline" className="ml-2">
                          LIVE
                        </Badge>
                      )}
                    </div>
                    <div className="flex items-center space-x-4 text-sm text-muted-foreground">
                      <span>{position.qty} shares</span>
                      <span>Avg: {formatCurrency(parseFloat(position.avg_entry_price))}</span>
                      <span>Current: {formatCurrency(parseFloat(position.current_price))}</span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center space-x-4">
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
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={(e) => {
                      e.stopPropagation()
                      onClose(position.symbol)
                    }}
                  >
                    <X className="h-4 w-4" />
                    Close
                  </Button>
                </div>
              </div>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}