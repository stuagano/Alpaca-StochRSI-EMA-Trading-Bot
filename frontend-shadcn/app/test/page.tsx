"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useAccount, usePositions, useOrders, useSignals, usePerformanceMetrics, useRiskMetrics } from '@/hooks/useAlpaca'
import { formatCurrency, formatPercent } from '@/lib/utils'
import { Badge } from "@/components/ui/badge"
import { DollarSign, TrendingUp, TrendingDown, Activity, Target, Shield } from "lucide-react"

export default function TestPage() {
  const { data: account, isLoading: accountLoading, error: accountError } = useAccount()
  const { data: positions = [], isLoading: positionsLoading, error: positionsError } = usePositions()
  const { data: orders = [], isLoading: ordersLoading } = useOrders('open')
  const { data: signals = [], isLoading: signalsLoading } = useSignals()
  const { data: performance, isLoading: perfLoading } = usePerformanceMetrics()
  const { data: riskMetrics, isLoading: riskLoading } = useRiskMetrics()

  // Calculate stats
  const totalPL = positions.reduce((sum, pos) => 
    sum + parseFloat(pos.unrealized_pl || '0'), 0
  )
  const totalValue = parseFloat(account?.portfolio_value || '0')
  const buyingPower = parseFloat(account?.buying_power || '0')
  const dayChange = positions.reduce((sum, pos) => 
    sum + parseFloat(pos.unrealized_intraday_pl || '0'), 0
  )

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="container mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold">Trading Dashboard Test</h1>
          <Badge variant="outline">Demo Mode</Badge>
        </div>

        {/* Account Information */}
        <Card>
          <CardHeader>
            <CardTitle>Account Information</CardTitle>
          </CardHeader>
          <CardContent>
            {accountLoading ? (
              <p>Loading account data...</p>
            ) : accountError ? (
              <p className="text-red-500">Error: {accountError.message}</p>
            ) : (
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <div className="text-center">
                  <div className="text-2xl font-bold">{formatCurrency(totalValue)}</div>
                  <div className="text-sm text-muted-foreground">Portfolio Value</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold">{formatCurrency(buyingPower)}</div>
                  <div className="text-sm text-muted-foreground">Buying Power</div>
                </div>
                <div className="text-center">
                  <div className={`text-2xl font-bold ${dayChange >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                    {formatCurrency(dayChange)}
                  </div>
                  <div className="text-sm text-muted-foreground">Day P&L</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold">{formatCurrency(parseFloat(account?.cash || '0'))}</div>
                  <div className="text-sm text-muted-foreground">Cash</div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Positions */}
        <Card>
          <CardHeader>
            <CardTitle>Positions ({positions.length})</CardTitle>
          </CardHeader>
          <CardContent>
            {positionsLoading ? (
              <p>Loading positions...</p>
            ) : positionsError ? (
              <p className="text-red-500">Error: {positionsError.message}</p>
            ) : positions.length === 0 ? (
              <p className="text-muted-foreground">No positions found</p>
            ) : (
              <div className="space-y-2">
                {positions.map((position) => (
                  <div key={position.symbol} className="flex items-center justify-between p-3 border rounded-lg">
                    <div className="flex items-center space-x-3">
                      <div className="font-medium">{position.symbol}</div>
                      <Badge variant="outline">{position.qty} shares</Badge>
                    </div>
                    <div className="text-right">
                      <div className="font-medium">{formatCurrency(parseFloat(position.market_value))}</div>
                      <div className={`text-sm ${parseFloat(position.unrealized_pl) >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                        {formatCurrency(parseFloat(position.unrealized_pl))} 
                        ({formatPercent(parseFloat(position.unrealized_plpc))})
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Orders */}
        <Card>
          <CardHeader>
            <CardTitle>Open Orders ({orders.length})</CardTitle>
          </CardHeader>
          <CardContent>
            {ordersLoading ? (
              <p>Loading orders...</p>
            ) : orders.length === 0 ? (
              <p className="text-muted-foreground">No open orders</p>
            ) : (
              <div className="space-y-2">
                {orders.map((order) => (
                  <div key={order.id} className="flex items-center justify-between p-3 border rounded-lg">
                    <div className="flex items-center space-x-3">
                      <div className="font-medium">{order.symbol}</div>
                      <Badge variant={order.side === 'buy' ? 'default' : 'destructive'}>
                        {order.side.toUpperCase()}
                      </Badge>
                      <span className="text-sm text-muted-foreground">{order.qty} shares</span>
                    </div>
                    <div className="text-right">
                      <div className="font-medium">{formatCurrency(parseFloat(order.limit_price || '0'))}</div>
                      <div className="text-sm text-muted-foreground">{order.status}</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Trading Signals */}
        <Card>
          <CardHeader>
            <CardTitle>Trading Signals ({signals.length})</CardTitle>
          </CardHeader>
          <CardContent>
            {signalsLoading ? (
              <p>Loading signals...</p>
            ) : signals.length === 0 ? (
              <p className="text-muted-foreground">No signals available</p>
            ) : (
              <div className="space-y-2">
                {signals.map((signal: any, idx: number) => (
                  <div key={idx} className="flex items-center justify-between p-3 border rounded-lg">
                    <div className="flex items-center space-x-3">
                      {signal.signal === 'BUY' ? 
                        <TrendingUp className="h-4 w-4 text-green-500" /> :
                        <TrendingDown className="h-4 w-4 text-red-500" />
                      }
                      <div className="font-medium">{signal.symbol}</div>
                      <Badge variant={signal.signal === 'BUY' ? 'default' : 'destructive'}>
                        {signal.signal}
                      </Badge>
                    </div>
                    <div className="text-right">
                      <div className="font-medium">{signal.confidence}% confidence</div>
                      <div className="text-sm text-muted-foreground">{formatCurrency(parseFloat(signal.price))}</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Performance Metrics */}
        <div className="grid gap-4 md:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Performance</CardTitle>
            </CardHeader>
            <CardContent>
              {perfLoading ? (
                <p>Loading performance...</p>
              ) : (
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span>Win Rate:</span>
                    <span className="font-medium">{formatPercent(performance?.win_rate || 0)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Total Return:</span>
                    <span className="font-medium">{formatPercent(performance?.total_return || 0)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Sharpe Ratio:</span>
                    <span className="font-medium">{performance?.sharpe_ratio?.toFixed(2) || '0.00'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Total Trades:</span>
                    <span className="font-medium">{performance?.total_trades || 0}</span>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Risk Metrics</CardTitle>
            </CardHeader>
            <CardContent>
              {riskLoading ? (
                <p>Loading risk metrics...</p>
              ) : (
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span>Risk Score:</span>
                    <span className="font-medium">{(riskMetrics as any)?.risk_score || 'N/A'}/10</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Portfolio Risk:</span>
                    <span className="font-medium">{formatPercent(riskMetrics?.portfolio_risk || 0)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>VaR (95%):</span>
                    <span className="font-medium">{formatCurrency(riskMetrics?.var_95 || 0)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Current Exposure:</span>
                    <span className="font-medium">{formatPercent(riskMetrics?.current_exposure || 0)}</span>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Debug Information */}
        <Card>
          <CardHeader>
            <CardTitle>Debug Information</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex justify-between">
              <span>Account Loading:</span>
              <span>{accountLoading ? 'Yes' : 'No'}</span>
            </div>
            <div className="flex justify-between">
              <span>Positions Loading:</span>
              <span>{positionsLoading ? 'Yes' : 'No'}</span>
            </div>
            <div className="flex justify-between">
              <span>Account Error:</span>
              <span className="text-red-500">{accountError?.message || 'None'}</span>
            </div>
            <div className="flex justify-between">
              <span>Positions Error:</span>
              <span className="text-red-500">{positionsError?.message || 'None'}</span>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}