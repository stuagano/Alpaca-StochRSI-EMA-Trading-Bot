"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Shield, AlertTriangle, TrendingUp, DollarSign } from 'lucide-react'
import { formatCurrency, formatPercent } from '@/lib/utils'

interface RiskPanelProps {
  riskMetrics?: {
    portfolio_risk: number
    position_risks: Record<string, number>
    var_95: number
    max_position_size: number
    current_exposure: number
    risk_score?: number
    recommendations?: string[]
  }
  positions: any[]
}

export function RiskPanel({ riskMetrics, positions }: RiskPanelProps) {
  if (!riskMetrics) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Risk Management</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center text-muted-foreground">
            Loading risk metrics...
          </div>
        </CardContent>
      </Card>
    )
  }

  const getRiskLevel = (score: number) => {
    if (score <= 3) return { label: 'Low', color: 'text-green-500', bg: 'bg-green-500' }
    if (score <= 6) return { label: 'Medium', color: 'text-yellow-500', bg: 'bg-yellow-500' }
    return { label: 'High', color: 'text-red-500', bg: 'bg-red-500' }
  }

  const riskLevel = getRiskLevel(riskMetrics.risk_score || 5)

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Risk Management</CardTitle>
            <CardDescription>Portfolio risk analysis</CardDescription>
          </div>
          <Shield className="h-5 w-5 text-muted-foreground" />
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Overall Risk Score */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Risk Score</span>
            <Badge className={riskLevel.bg}>
              {riskLevel.label} ({riskMetrics.risk_score || 5}/10)
            </Badge>
          </div>
          <Progress value={(riskMetrics.risk_score || 5) * 10} className="h-2" />
        </div>

        {/* Key Metrics */}
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">Portfolio Risk</div>
            <div className="font-medium">{formatPercent(riskMetrics.portfolio_risk)}</div>
          </div>
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">VaR (95%)</div>
            <div className="font-medium">{formatCurrency(riskMetrics.var_95)}</div>
          </div>
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">Exposure</div>
            <div className="font-medium">{formatPercent(riskMetrics.current_exposure)}</div>
          </div>
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">Max Position</div>
            <div className="font-medium">{formatCurrency(riskMetrics.max_position_size)}</div>
          </div>
        </div>

        {/* Position Risks */}
        {Object.keys(riskMetrics.position_risks || {}).length > 0 && (
          <div className="space-y-2">
            <div className="text-sm font-medium">Position Risks</div>
            <div className="space-y-1">
              {Object.entries(riskMetrics.position_risks).slice(0, 3).map(([symbol, risk]) => (
                <div key={symbol} className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">{symbol}</span>
                  <Badge variant="outline" className="text-xs">
                    {formatPercent(risk)}
                  </Badge>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Recommendations */}
        {riskMetrics.recommendations && riskMetrics.recommendations.length > 0 && (
          <Alert>
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription className="text-xs">
              {riskMetrics.recommendations[0]}
            </AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  )
}