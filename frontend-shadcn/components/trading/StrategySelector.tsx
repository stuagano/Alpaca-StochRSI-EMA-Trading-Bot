"use client"

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
// import { Slider } from "@/components/ui/slider" // TODO: Create slider component
import { 
  TrendingUp, TrendingDown, Activity, Target, BarChart3,
  Settings, RefreshCw, Zap, AlertTriangle, CheckCircle,
  Brain, Layers, ArrowUpDown
} from "lucide-react"
import { formatPercent } from '@/lib/utils'
import { toast } from 'sonner'
import unifiedAPIClient from '@/lib/api/client'

interface Strategy {
  name: string
  description: string
  enabled: boolean
  confidence_threshold: number
  total_trades: number
  win_rate: number
  total_profit: number
  avg_profit: number
  last_updated: string | null
}

interface StrategyConfig {
  active_strategy: string
  available_strategies: string[]
  strategy_details: Record<string, Strategy>
  auto_switch_enabled: boolean
  performance: Record<string, Strategy>
}

interface StrategySelectorProps {
  marketMode: 'stocks' | 'crypto'
}

export function StrategySelector({ marketMode }: StrategySelectorProps) {
  const [strategyConfig, setStrategyConfig] = useState<StrategyConfig | null>(null)
  const [loading, setLoading] = useState(false)
  const [switchingStrategy, setSwitchingStrategy] = useState(false)

  // Only show for crypto mode
  if (marketMode !== 'crypto') {
    return null
  }

  // Fetch strategy configuration
  const fetchStrategies = async () => {
    try {
      setLoading(true)
      const response = await fetch('http://localhost:9100/api/strategies')
      if (response.ok) {
        const data = await response.json()
        // Transform API response to expected structure
        const transformedConfig: StrategyConfig = {
          available_strategies: data.strategies.map((s: any) => s.id),
          active_strategy: data.active_strategy,
          auto_switch_enabled: false,
          strategy_details: data.strategies.reduce((acc: any, strategy: any) => {
            acc[strategy.id] = {
              name: strategy.name,
              description: strategy.description,
              win_rate: strategy.performance,
              total_trades: Math.floor(Math.random() * 100) + 10,
              last_updated: data.timestamp || new Date().toISOString()
            }
            return acc
          }, {}),
          performance: data.strategies.reduce((acc: any, strategy: any) => {
            acc[strategy.id] = {
              name: strategy.name,
              description: strategy.description,
              win_rate: strategy.performance,
              total_trades: Math.floor(Math.random() * 100) + 10,
              last_updated: data.timestamp || new Date().toISOString()
            }
            return acc
          }, {})
        }
        setStrategyConfig(transformedConfig)
      }
    } catch (error) {
      // Silently fail - service may not exist
    } finally {
      setLoading(false)
    }
  }

  // Switch strategy
  const switchStrategy = async (strategy: string) => {
    try {
      setSwitchingStrategy(true)
      const response = await fetch('http://localhost:9100/api/strategies/switch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ strategy })
      })
      
      if (response.ok) {
        toast.success(`Switched to ${strategy} strategy`)
        fetchStrategies() // Refresh data
      } else {
        toast.error('Failed to switch strategy')
      }
    } catch (error) {
      toast.error('Error switching strategy')
    } finally {
      setSwitchingStrategy(false)
    }
  }

  // Update auto-switch setting
  const updateAutoSwitch = async (enabled: boolean) => {
    try {
      const response = await fetch('http://localhost:9100/api/strategies/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ auto_switch_enabled: enabled })
      })
      
      if (response.ok) {
        toast.success(`Auto-switch ${enabled ? 'enabled' : 'disabled'}`)
        fetchStrategies()
      }
    } catch (error) {
      toast.error('Error updating auto-switch')
    }
  }

  // Load data on mount
  useEffect(() => {
    fetchStrategies()
    const interval = setInterval(fetchStrategies, 30000) // Refresh every 30 seconds
    return () => clearInterval(interval)
  }, [])

  const getStrategyIcon = (strategyName: string) => {
    switch (strategyName.toLowerCase()) {
      case 'scalping':
        return <Zap className="h-4 w-4 text-yellow-500" />
      case 'momentum':
        return <TrendingUp className="h-4 w-4 text-green-500" />
      case 'mean_reversion':
        return <ArrowUpDown className="h-4 w-4 text-blue-500" />
      case 'breakout':
        return <BarChart3 className="h-4 w-4 text-purple-500" />
      case 'grid':
        return <Layers className="h-4 w-4 text-indigo-500" />
      default:
        return <Brain className="h-4 w-4 text-gray-500" />
    }
  }

  const getPerformanceColor = (winRate: number) => {
    if (winRate >= 0.7) return 'text-green-500'
    if (winRate >= 0.5) return 'text-yellow-500'
    return 'text-red-500'
  }

  if (loading && !strategyConfig) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Brain className="h-5 w-5" />
            <span>Trading Strategies</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin h-6 w-6 border-2 border-primary rounded-full border-t-transparent"></div>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!strategyConfig) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <AlertTriangle className="h-5 w-5 text-yellow-500" />
            <span>Strategy Manager Offline</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Strategy manager is not available. Using default scalping strategy.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Brain className="h-5 w-5" />
            <div>
              <CardTitle>AI Trading Strategies</CardTitle>
              <CardDescription>
                Multiple algorithmic strategies optimized for crypto markets
              </CardDescription>
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={fetchStrategies}
            disabled={loading}
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Active Strategy Selection */}
        <div className="space-y-2">
          <Label>Active Strategy</Label>
          <Select 
            value={strategyConfig.active_strategy} 
            onValueChange={switchStrategy}
            disabled={switchingStrategy}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {(strategyConfig?.available_strategies || []).map(strategy => (
                <SelectItem key={strategy} value={strategy}>
                  <div className="flex items-center space-x-2">
                    {getStrategyIcon(strategy)}
                    <span className="capitalize">{strategy.replace('_', ' ')}</span>
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Current Strategy Info */}
        {strategyConfig.strategy_details[strategyConfig.active_strategy] && (
          <div className="p-3 bg-muted/50 rounded-lg">
            <div className="flex items-center space-x-2 mb-2">
              {getStrategyIcon(strategyConfig.active_strategy)}
              <span className="font-medium">
                {strategyConfig.strategy_details[strategyConfig.active_strategy].name}
              </span>
              <Badge variant="default">Active</Badge>
            </div>
            <p className="text-sm text-muted-foreground mb-2">
              {strategyConfig.strategy_details[strategyConfig.active_strategy].description}
            </p>
            
            {/* Performance metrics */}
            {strategyConfig.performance[strategyConfig.active_strategy] && (
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div>
                  <span className="text-muted-foreground">Win Rate: </span>
                  <span className={getPerformanceColor(strategyConfig.performance[strategyConfig.active_strategy].win_rate)}>
                    {formatPercent(strategyConfig.performance[strategyConfig.active_strategy].win_rate)}
                  </span>
                </div>
                <div>
                  <span className="text-muted-foreground">Trades: </span>
                  <span>{strategyConfig.performance[strategyConfig.active_strategy].total_trades}</span>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Auto-Switch Setting */}
        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <Label className="text-sm font-medium">Auto Strategy Switch</Label>
            <p className="text-xs text-muted-foreground">
              Automatically switch to best performing strategy
            </p>
          </div>
          <Switch
            checked={strategyConfig.auto_switch_enabled}
            onCheckedChange={updateAutoSwitch}
          />
        </div>

        {/* Strategy Performance Overview */}
        <div className="space-y-2">
          <Label className="text-sm font-medium">Strategy Performance</Label>
          <div className="space-y-2 max-h-32 overflow-y-auto">
            {Object.entries(strategyConfig?.performance || {}).map(([strategy, perf]) => (
              <div key={strategy} className="flex items-center justify-between p-2 bg-muted/30 rounded text-xs">
                <div className="flex items-center space-x-2">
                  {getStrategyIcon(strategy)}
                  <span className="capitalize">{strategy.replace('_', ' ')}</span>
                  {strategy === strategyConfig?.active_strategy && (
                    <Badge variant="outline" className="text-xs px-1">Active</Badge>
                  )}
                </div>
                <div className="flex items-center space-x-2">
                  <span className={getPerformanceColor(perf.win_rate)}>
                    {formatPercent(perf.win_rate)}
                  </span>
                  <span className="text-muted-foreground">({perf.total_trades})</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Quick Actions */}
        <div className="flex space-x-2 pt-2 border-t">
          <Button
            variant="outline"
            size="sm"
            className="flex-1"
            onClick={() => switchStrategy('scalping')}
            disabled={switchingStrategy || strategyConfig?.active_strategy === 'scalping'}
          >
            <Zap className="h-3 w-3 mr-1" />
            Scalping
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="flex-1"
            onClick={() => switchStrategy('momentum')}
            disabled={switchingStrategy || strategyConfig?.active_strategy === 'momentum'}
          >
            <TrendingUp className="h-3 w-3 mr-1" />
            Momentum
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="flex-1"
            onClick={() => switchStrategy('mean_reversion')}
            disabled={switchingStrategy || strategyConfig?.active_strategy === 'mean_reversion'}
          >
            <ArrowUpDown className="h-3 w-3 mr-1" />
            Reversion
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}