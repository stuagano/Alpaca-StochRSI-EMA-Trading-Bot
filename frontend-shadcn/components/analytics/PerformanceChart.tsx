"use client"

import { usePortfolioHistory } from '@/hooks/useAlpaca'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { formatCurrency, formatPercent } from '@/lib/utils'
import { useState } from 'react'

export function PerformanceChart() {
  const [period, setPeriod] = useState<'1D' | '1W' | '1M' | '3M' | '1Y'>('1M')
  const { data: portfolioHistory, isLoading } = usePortfolioHistory(period)

  if (isLoading) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          Loading performance data...
        </CardContent>
      </Card>
    )
  }

  if (!portfolioHistory) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          No performance data available
        </CardContent>
      </Card>
    )
  }

  // Format data for chart
  const chartData = portfolioHistory.timestamp.map((time: string, index: number) => ({
    time: new Date(time).toLocaleDateString(),
    equity: portfolioHistory.equity[index],
    pnl: portfolioHistory.profit_loss[index],
    pnlPercent: portfolioHistory.profit_loss_pct[index] * 100
  }))

  const totalReturn = chartData.length > 0 ? 
    ((chartData[chartData.length - 1].equity - chartData[0].equity) / chartData[0].equity) * 100 : 0

  return (
    <div className="space-y-4">
      {/* Summary Cards */}
      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Total Return</CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-lg font-bold ${totalReturn >= 0 ? 'text-green-500' : 'text-red-500'}`}>
              {formatPercent(totalReturn / 100)}
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Current Equity</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-lg font-bold">
              {formatCurrency(chartData[chartData.length - 1]?.equity || 0)}
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Total P&L</CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-lg font-bold ${
              chartData[chartData.length - 1]?.pnl >= 0 ? 'text-green-500' : 'text-red-500'
            }`}>
              {formatCurrency(chartData[chartData.length - 1]?.pnl || 0)}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Chart */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Portfolio Performance</CardTitle>
            <div className="flex space-x-2">
              {(['1D', '1W', '1M', '3M', '1Y'] as const).map((p) => (
                <Button
                  key={p}
                  size="sm"
                  variant={period === p ? 'default' : 'outline'}
                  onClick={() => setPeriod(p)}
                >
                  {p}
                </Button>
              ))}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" />
              <YAxis />
              <Tooltip
                formatter={(value, name) => [
                  name === 'equity' ? formatCurrency(value as number) :
                  name === 'pnl' ? formatCurrency(value as number) :
                  formatPercent((value as number) / 100),
                  name === 'equity' ? 'Equity' :
                  name === 'pnl' ? 'P&L' : 'P&L %'
                ]}
                labelFormatter={(label) => `Date: ${label}`}
              />
              <Line
                type="monotone"
                dataKey="equity"
                stroke="#8884d8"
                strokeWidth={2}
                dot={false}
                name="equity"
              />
              <Line
                type="monotone"
                dataKey="pnl"
                stroke="#82ca9d"
                strokeWidth={2}
                dot={false}
                name="pnl"
              />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  )
}