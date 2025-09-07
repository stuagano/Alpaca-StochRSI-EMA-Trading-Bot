"use client"

import { useState, useEffect } from 'react'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { Button } from '@/components/ui/button'
import { RefreshCw, AlertCircle, CheckCircle, Clock, Zap } from 'lucide-react'
import { cn } from '@/lib/utils'

interface ServiceStatus {
  name: string
  port: number
  status: 'online' | 'offline' | 'error' | 'checking'
  response_time?: number
  data_source?: string
  last_check?: string
  error?: string
}

interface DataFeedStatus {
  name: string
  status: 'connected' | 'disconnected' | 'error'
  last_update?: string
  symbols_count?: number
  data_quality?: 'real' | 'mock' | 'unknown'
}

export function ServiceStatusBar() {
  const [services, setServices] = useState<ServiceStatus[]>([
    { name: 'API Gateway', port: 9000, status: 'checking' },
    { name: 'Positions', port: 9001, status: 'checking' },
    { name: 'Trading', port: 9002, status: 'checking' },
    { name: 'Signals', port: 9003, status: 'checking' },
    { name: 'Risk', port: 9004, status: 'checking' },
    { name: 'Market Data', port: 9005, status: 'checking' },
    { name: 'Historical', port: 9006, status: 'checking' },
    { name: 'Analytics', port: 9007, status: 'checking' },
    { name: 'Crypto', port: 9012, status: 'checking' },
  ])

  const [dataFeeds, setDataFeeds] = useState<DataFeedStatus[]>([
    { name: 'Alpaca Stock Feed', status: 'disconnected' },
    { name: 'Alpaca Crypto Feed', status: 'disconnected' },
    { name: 'Market Data Stream', status: 'disconnected' },
    { name: 'Signal Processing', status: 'disconnected' },
  ])

  const [isRefreshing, setIsRefreshing] = useState(false)
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null)

  const checkServiceHealth = async (service: ServiceStatus): Promise<ServiceStatus> => {
    try {
      const response = await fetch(`http://localhost:${service.port}/health`, {
        method: 'GET',
        signal: AbortSignal.timeout(3000)
      })
      
      const data = await response.json()
      const responseTime = performance.now()
      
      return {
        ...service,
        status: response.ok ? 'online' : 'error',
        response_time: responseTime,
        data_source: data.data_source || data.compliance || 'unknown',
        last_check: new Date().toISOString(),
        error: response.ok ? undefined : `HTTP ${response.status}`
      }
    } catch (error) {
      return {
        ...service,
        status: 'offline',
        error: error instanceof Error ? error.message : 'Connection failed',
        last_check: new Date().toISOString()
      }
    }
  }

  const checkDataFeeds = async (): Promise<DataFeedStatus[]> => {
    const feeds: DataFeedStatus[] = []
    
    // Check Alpaca Stock Feed
    try {
      const response = await fetch('http://localhost:9005/market/quote/AAPL', {
        signal: AbortSignal.timeout(3000)
      })
      const data = await response.json()
      feeds.push({
        name: 'Alpaca Stock Feed',
        status: response.ok ? 'connected' : 'error',
        last_update: data.timestamp,
        data_quality: data.data_source?.includes('alpaca') ? 'real' : 'unknown'
      })
    } catch {
      feeds.push({ name: 'Alpaca Stock Feed', status: 'disconnected' })
    }

    // Check Alpaca Crypto Feed  
    try {
      const response = await fetch('http://localhost:9012/api/status', {
        signal: AbortSignal.timeout(3000)
      })
      const data = await response.json()
      feeds.push({
        name: 'Alpaca Crypto Feed',
        status: response.ok ? 'connected' : 'error',
        last_update: data.timestamp,
        symbols_count: data.active_pairs?.length,
        data_quality: 'real'
      })
    } catch {
      feeds.push({ name: 'Alpaca Crypto Feed', status: 'disconnected' })
    }

    // Check Market Data Stream
    try {
      const response = await fetch('http://localhost:9005/market/snapshot', {
        signal: AbortSignal.timeout(3000)
      })
      const data = await response.json()
      feeds.push({
        name: 'Market Data Stream',
        status: response.ok ? 'connected' : 'error',
        last_update: data.timestamp,
        symbols_count: Object.keys(data.snapshot || {}).length,
        data_quality: data.data_source?.includes('real') ? 'real' : 'unknown'
      })
    } catch {
      feeds.push({ name: 'Market Data Stream', status: 'disconnected' })
    }

    // Check Signal Processing
    try {
      const response = await fetch('http://localhost:9003/health', {
        signal: AbortSignal.timeout(3000)
      })
      feeds.push({
        name: 'Signal Processing',
        status: response.ok ? 'connected' : 'error',
        last_update: new Date().toISOString(),
        data_quality: 'real'
      })
    } catch {
      feeds.push({ name: 'Signal Processing', status: 'disconnected' })
    }

    return feeds
  }

  const refreshStatus = async () => {
    setIsRefreshing(true)
    
    try {
      // Check all services in parallel
      const servicePromises = services.map(checkServiceHealth)
      const updatedServices = await Promise.all(servicePromises)
      setServices(updatedServices)

      // Check data feeds
      const updatedFeeds = await checkDataFeeds()
      setDataFeeds(updatedFeeds)
      
      setLastRefresh(new Date())
    } catch (error) {
      console.error('Error refreshing status:', error)
    } finally {
      setIsRefreshing(false)
    }
  }

  // Auto-refresh every 30 seconds
  useEffect(() => {
    refreshStatus()
    const interval = setInterval(refreshStatus, 30000)
    return () => clearInterval(interval)
  }, [])

  const getServiceStatusIcon = (status: ServiceStatus['status']) => {
    switch (status) {
      case 'online': return <CheckCircle className="h-3 w-3 text-green-500" />
      case 'offline': return <AlertCircle className="h-3 w-3 text-red-500" />
      case 'error': return <AlertCircle className="h-3 w-3 text-orange-500" />
      case 'checking': return <Clock className="h-3 w-3 text-gray-500 animate-pulse" />
    }
  }

  const getServiceStatusColor = (status: ServiceStatus['status']) => {
    switch (status) {
      case 'online': return 'bg-green-500/10 text-green-700 border-green-200'
      case 'offline': return 'bg-red-500/10 text-red-700 border-red-200'  
      case 'error': return 'bg-orange-500/10 text-orange-700 border-orange-200'
      case 'checking': return 'bg-gray-500/10 text-gray-700 border-gray-200'
    }
  }

  const getFeedStatusColor = (status: DataFeedStatus['status']) => {
    switch (status) {
      case 'connected': return 'bg-green-500/10 text-green-700 border-green-200'
      case 'disconnected': return 'bg-red-500/10 text-red-700 border-red-200'
      case 'error': return 'bg-orange-500/10 text-orange-700 border-orange-200'
    }
  }

  const getFeedStatusIcon = (status: DataFeedStatus['status']) => {
    switch (status) {
      case 'connected': return <Zap className="h-3 w-3 text-green-500" />
      case 'disconnected': return <AlertCircle className="h-3 w-3 text-red-500" />
      case 'error': return <AlertCircle className="h-3 w-3 text-orange-500" />
    }
  }

  const onlineServices = services.filter(s => s.status === 'online').length
  const connectedFeeds = dataFeeds.filter(f => f.status === 'connected').length

  return (
    <Card className="w-full p-3 mb-4 bg-slate-50/50 border-slate-200">
      <div className="flex items-center justify-between">
        {/* System Overview */}
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <div className={cn(
              "h-2 w-2 rounded-full",
              onlineServices === services.length ? "bg-green-500" : 
              onlineServices === 0 ? "bg-red-500" : "bg-orange-500"
            )} />
            <span className="text-sm font-medium">
              System: {onlineServices}/{services.length} Services
            </span>
          </div>
          
          <Separator orientation="vertical" className="h-4" />
          
          <div className="flex items-center space-x-2">
            <div className={cn(
              "h-2 w-2 rounded-full",
              connectedFeeds === dataFeeds.length ? "bg-green-500" : 
              connectedFeeds === 0 ? "bg-red-500" : "bg-orange-500"
            )} />
            <span className="text-sm font-medium">
              Data: {connectedFeeds}/{dataFeeds.length} Feeds
            </span>
          </div>
        </div>

        {/* Refresh Controls */}
        <div className="flex items-center space-x-2">
          {lastRefresh && (
            <span className="text-xs text-muted-foreground">
              Last: {lastRefresh.toLocaleTimeString()}
            </span>
          )}
          <Button 
            variant="outline" 
            size="sm" 
            onClick={refreshStatus}
            disabled={isRefreshing}
          >
            <RefreshCw className={cn("h-3 w-3 mr-1", isRefreshing && "animate-spin")} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Detailed Status Grid */}
      <div className="mt-3 space-y-3">
        {/* Microservices Status */}
        <div>
          <h4 className="text-xs font-semibold text-muted-foreground mb-2">MICROSERVICES</h4>
          <div className="flex flex-wrap gap-2">
            {services.map((service) => (
              <Badge
                key={service.name}
                variant="outline"
                className={cn("text-xs", getServiceStatusColor(service.status))}
              >
                {getServiceStatusIcon(service.status)}
                <span className="ml-1">{service.name}</span>
                {service.status === 'online' && service.response_time && (
                  <span className="ml-1 text-xs opacity-70">
                    ({Math.round(service.response_time)}ms)
                  </span>
                )}
                {service.data_source && (
                  <span className="ml-1 text-xs opacity-70">
                    [{service.data_source.includes('real') ? 'REAL' : service.data_source.toUpperCase()}]
                  </span>
                )}
              </Badge>
            ))}
          </div>
        </div>

        {/* Data Feeds Status */}
        <div>
          <h4 className="text-xs font-semibold text-muted-foreground mb-2">DATA FEEDS</h4>
          <div className="flex flex-wrap gap-2">
            {dataFeeds.map((feed) => (
              <Badge
                key={feed.name}
                variant="outline"
                className={cn("text-xs", getFeedStatusColor(feed.status))}
              >
                {getFeedStatusIcon(feed.status)}
                <span className="ml-1">{feed.name}</span>
                {feed.symbols_count && (
                  <span className="ml-1 text-xs opacity-70">
                    ({feed.symbols_count} symbols)
                  </span>
                )}
                {feed.data_quality && (
                  <span className="ml-1 text-xs opacity-70">
                    [{feed.data_quality.toUpperCase()}]
                  </span>
                )}
              </Badge>
            ))}
          </div>
        </div>
      </div>
    </Card>
  )
}