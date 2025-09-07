"use client"

import React, { useEffect, useState } from 'react'
import { AlertCircle, CheckCircle, Loader2, WifiOff, Wifi } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'

type ConnectionState = 'disconnected' | 'connecting' | 'connected' | 'reconnecting' | 'error'

interface ConnectionStats {
  messagesReceived: number
  messagesSent: number
  reconnections: number
  errors: number
  uptime: number
  lastError: string | null
  latency: number
}

interface ConnectionStatusProps {
  url?: string
  compact?: boolean
  showDetails?: boolean
  onReconnect?: () => void
}

export function ConnectionStatus({
  url = 'ws://localhost:9000/ws/trading',
  compact = false,
  showDetails = true,
  onReconnect
}: ConnectionStatusProps) {
  const [state, setState] = useState<ConnectionState>('disconnected')
  const [stats, setStats] = useState<ConnectionStats>({
    messagesReceived: 0,
    messagesSent: 0,
    reconnections: 0,
    errors: 0,
    uptime: 0,
    lastError: null,
    latency: 0
  })
  const [ws, setWs] = useState<WebSocket | null>(null)
  const [reconnectTimer, setReconnectTimer] = useState<NodeJS.Timeout | null>(null)
  const [reconnectDelay, setReconnectDelay] = useState(1000)
  const [lastPingTime, setLastPingTime] = useState<number>(0)

  // Connection management
  useEffect(() => {
    connect()
    
    return () => {
      if (ws) {
        ws.close()
      }
      if (reconnectTimer) {
        clearTimeout(reconnectTimer)
      }
    }
  }, [url])

  const connect = () => {
    setState('connecting')
    
    try {
      const websocket = new WebSocket(url)
      
      websocket.onopen = () => {
        console.log('WebSocket connected')
        setState('connected')
        setReconnectDelay(1000) // Reset delay on successful connection
        setStats(prev => ({ ...prev, errors: 0 }))
        
        // Start heartbeat
        startHeartbeat(websocket)
      }
      
      websocket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          
          // Handle pong for latency calculation
          if (data.type === 'pong') {
            const latency = Date.now() - lastPingTime
            setStats(prev => ({ ...prev, latency }))
          }
          
          setStats(prev => ({ ...prev, messagesReceived: prev.messagesReceived + 1 }))
        } catch (e) {
          console.error('Error parsing message:', e)
        }
      }
      
      websocket.onerror = (error) => {
        console.error('WebSocket error:', error)
        setState('error')
        setStats(prev => ({ 
          ...prev, 
          errors: prev.errors + 1,
          lastError: 'Connection error'
        }))
      }
      
      websocket.onclose = () => {
        console.log('WebSocket disconnected')
        setState('disconnected')
        setWs(null)
        
        // Attempt reconnection with exponential backoff
        scheduleReconnect()
      }
      
      setWs(websocket)
      
    } catch (error) {
      console.error('Failed to create WebSocket:', error)
      setState('error')
      setStats(prev => ({ 
        ...prev, 
        errors: prev.errors + 1,
        lastError: error instanceof Error ? error.message : 'Unknown error'
      }))
      scheduleReconnect()
    }
  }

  const startHeartbeat = (websocket: WebSocket) => {
    const interval = setInterval(() => {
      if (websocket.readyState === WebSocket.OPEN) {
        const pingTime = Date.now()
        setLastPingTime(pingTime)
        websocket.send(JSON.stringify({ type: 'ping' }))
        setStats(prev => ({ ...prev, messagesSent: prev.messagesSent + 1 }))
      }
    }, 30000) // Ping every 30 seconds
    
    // Store interval ID for cleanup
    ;(websocket as any).heartbeatInterval = interval
  }

  const scheduleReconnect = () => {
    setState('reconnecting')
    setStats(prev => ({ ...prev, reconnections: prev.reconnections + 1 }))
    
    const timer = setTimeout(() => {
      connect()
      // Exponential backoff with max delay of 30 seconds
      setReconnectDelay(prev => Math.min(prev * 2, 30000))
    }, reconnectDelay)
    
    setReconnectTimer(timer)
  }

  const handleManualReconnect = () => {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
    }
    
    if (ws) {
      ws.close()
    }
    
    connect()
    
    if (onReconnect) {
      onReconnect()
    }
  }

  const getStatusIcon = () => {
    switch (state) {
      case 'connected':
        return <Wifi className="h-4 w-4 text-green-500" />
      case 'connecting':
      case 'reconnecting':
        return <Loader2 className="h-4 w-4 animate-spin text-yellow-500" />
      case 'error':
        return <AlertCircle className="h-4 w-4 text-red-500" />
      case 'disconnected':
      default:
        return <WifiOff className="h-4 w-4 text-gray-500" />
    }
  }

  const getStatusColor = () => {
    switch (state) {
      case 'connected':
        return 'bg-green-500'
      case 'connecting':
      case 'reconnecting':
        return 'bg-yellow-500'
      case 'error':
        return 'bg-red-500'
      case 'disconnected':
      default:
        return 'bg-gray-500'
    }
  }

  const getStatusText = () => {
    switch (state) {
      case 'connected':
        return 'Connected'
      case 'connecting':
        return 'Connecting...'
      case 'reconnecting':
        return `Reconnecting (${stats.reconnections})...`
      case 'error':
        return 'Connection Error'
      case 'disconnected':
      default:
        return 'Disconnected'
    }
  }

  const formatUptime = (seconds: number) => {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    const secs = seconds % 60
    
    if (hours > 0) {
      return `${hours}h ${minutes}m`
    } else if (minutes > 0) {
      return `${minutes}m ${secs}s`
    } else {
      return `${secs}s`
    }
  }

  // Update uptime counter
  useEffect(() => {
    if (state === 'connected') {
      const interval = setInterval(() => {
        setStats(prev => ({ ...prev, uptime: prev.uptime + 1 }))
      }, 1000)
      
      return () => clearInterval(interval)
    }
  }, [state])

  if (compact) {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <div className="flex items-center gap-2 cursor-pointer">
              {getStatusIcon()}
              <div className={cn(
                "h-2 w-2 rounded-full animate-pulse",
                getStatusColor()
              )} />
            </div>
          </TooltipTrigger>
          <TooltipContent>
            <div className="text-sm">
              <p className="font-semibold">{getStatusText()}</p>
              {stats.latency > 0 && (
                <p>Latency: {stats.latency}ms</p>
              )}
            </div>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    )
  }

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="ghost" className="h-auto p-1">
          <div className="flex items-center gap-2">
            {getStatusIcon()}
            <span className="text-sm font-medium">{getStatusText()}</span>
            {state === 'connected' && stats.latency > 0 && (
              <Badge variant="secondary" className="text-xs">
                {stats.latency}ms
              </Badge>
            )}
          </div>
        </Button>
      </PopoverTrigger>
      
      {showDetails && (
        <PopoverContent className="w-80">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="font-semibold">Connection Details</h4>
              <div className={cn(
                "h-2 w-2 rounded-full",
                getStatusColor()
              )} />
            </div>
            
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Status</span>
                <span className="font-medium">{getStatusText()}</span>
              </div>
              
              <div className="flex justify-between">
                <span className="text-muted-foreground">Endpoint</span>
                <span className="font-mono text-xs truncate max-w-[150px]" title={url}>
                  {url.replace('ws://', '').replace('wss://', '')}
                </span>
              </div>
              
              {state === 'connected' && (
                <>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Uptime</span>
                    <span className="font-medium">{formatUptime(stats.uptime)}</span>
                  </div>
                  
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Latency</span>
                    <span className="font-medium">
                      {stats.latency > 0 ? `${stats.latency}ms` : 'Measuring...'}
                    </span>
                  </div>
                </>
              )}
              
              <div className="flex justify-between">
                <span className="text-muted-foreground">Messages</span>
                <span className="font-medium">
                  ↓ {stats.messagesReceived} / ↑ {stats.messagesSent}
                </span>
              </div>
              
              {stats.reconnections > 0 && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Reconnections</span>
                  <span className="font-medium">{stats.reconnections}</span>
                </div>
              )}
              
              {stats.errors > 0 && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Errors</span>
                  <span className="font-medium text-red-500">{stats.errors}</span>
                </div>
              )}
              
              {stats.lastError && (
                <div className="pt-2 border-t">
                  <p className="text-xs text-red-500">
                    Last error: {stats.lastError}
                  </p>
                </div>
              )}
            </div>
            
            {(state === 'disconnected' || state === 'error') && (
              <Button
                onClick={handleManualReconnect}
                size="sm"
                className="w-full"
                variant="outline"
              >
                Reconnect Now
              </Button>
            )}
          </div>
        </PopoverContent>
      )}
    </Popover>
  )
}

// Simplified status indicator for headers
export function ConnectionIndicator({ url }: { url?: string }) {
  return <ConnectionStatus url={url} compact />
}

// Full status card for dashboards
export function ConnectionStatusCard({ url }: { url?: string }) {
  return (
    <Card className="p-4">
      <ConnectionStatus url={url} showDetails={false} />
    </Card>
  )
}