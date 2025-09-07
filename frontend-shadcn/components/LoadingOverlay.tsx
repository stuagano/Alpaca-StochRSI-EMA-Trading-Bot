"use client"

import { useEffect, useState } from 'react'
import { CheckCircle, XCircle, Loader2, AlertTriangle, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Card } from '@/components/ui/card'

interface ServiceStatus {
  name: string
  port: number
  status: 'pending' | 'checking' | 'online' | 'offline' | 'error'
  endpoint: string
  description: string
  critical: boolean
  retryCount: number
}

interface LoadingOverlayProps {
  onServicesReady: () => void
  minLoadTime?: number
}

export function LoadingOverlay({ onServicesReady, minLoadTime = 3000 }: LoadingOverlayProps) {
  const [services, setServices] = useState<ServiceStatus[]>([
    {
      name: 'Backend API',
      port: 9000,
      status: 'pending',
      endpoint: '/health',
      description: 'Main trading API',
      critical: true,
      retryCount: 0
    },
    {
      name: 'Alpaca Connection',
      port: 9000,
      status: 'pending',
      endpoint: '/api/account',
      description: 'Trading account access',
      critical: true,
      retryCount: 0
    },
    {
      name: 'Market Data Feed',
      port: 9000,
      status: 'pending',
      endpoint: '/api/market/status',
      description: 'Real-time market data',
      critical: false,
      retryCount: 0
    },
    {
      name: 'WebSocket Stream',
      port: 9100,
      status: 'pending',
      endpoint: '/api/stream',
      description: 'Live price updates',
      critical: false,
      retryCount: 0
    }
  ])

  const [progress, setProgress] = useState(0)
  const [currentCheck, setCurrentCheck] = useState('')
  const [startTime] = useState(Date.now())
  const [isRetrying, setIsRetrying] = useState(false)
  const [canProceed, setCanProceed] = useState(false)

  // Check individual service health
  const checkService = async (service: ServiceStatus): Promise<ServiceStatus> => {
    try {
      setCurrentCheck(`Checking ${service.name}...`)
      
      // Update to checking status
      setServices(prev => prev.map(s => 
        s.port === service.port ? { ...s, status: 'checking' } : s
      ))

      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 3000)

      const response = await fetch(`http://localhost:${service.port}${service.endpoint}`, {
        method: 'GET',
        signal: controller.signal,
        headers: {
          'Accept': 'application/json'
        }
      })

      clearTimeout(timeoutId)

      if (response.ok) {
        return { ...service, status: 'online', retryCount: 0 }
      } else {
        return { ...service, status: 'error', retryCount: service.retryCount + 1 }
      }
    } catch (error) {
      // Service is offline or unreachable
      return { ...service, status: 'offline', retryCount: service.retryCount + 1 }
    }
  }

  // Check all services
  const checkAllServices = async () => {
    setIsRetrying(false)
    
    // Reset all services to pending
    setServices(prev => prev.map(s => ({ ...s, status: 'pending' })))
    
    // Check services in parallel batches to avoid overwhelming the system
    const batchSize = 3
    const updatedServices: ServiceStatus[] = []
    
    for (let i = 0; i < services.length; i += batchSize) {
      const batch = services.slice(i, i + batchSize)
      const results = await Promise.all(batch.map(checkService))
      updatedServices.push(...results)
      
      // Update progress
      const progressValue = ((i + batchSize) / services.length) * 100
      setProgress(Math.min(progressValue, 100))
      
      // Update services state with results
      setServices(prev => {
        const newServices = [...prev]
        results.forEach(result => {
          const index = newServices.findIndex(s => s.port === result.port)
          if (index !== -1) {
            newServices[index] = result
          }
        })
        return newServices
      })
    }

    // Check if critical services are ready
    const criticalServicesReady = updatedServices
      .filter(s => s.critical)
      .every(s => s.status === 'online')

    // Check if enough time has passed
    const timeElapsed = Date.now() - startTime
    const minTimeReached = timeElapsed >= minLoadTime

    if (criticalServicesReady && minTimeReached) {
      setCanProceed(true)
      setTimeout(() => {
        onServicesReady()
      }, 500)
    } else if (!criticalServicesReady) {
      // Some critical services failed, show retry option
      setIsRetrying(true)
      setCanProceed(true) // Allow proceeding anyway
      setCurrentCheck('Some critical services are offline. Please check backend services.')
    } else {
      // Wait for minimum time
      setTimeout(() => {
        setCanProceed(true)
        onServicesReady()
      }, minLoadTime - timeElapsed)
    }
  }

  // Initial check on mount
  useEffect(() => {
    checkAllServices()
  }, [])

  // Calculate statistics
  const onlineCount = services.filter(s => s.status === 'online').length
  const offlineCount = services.filter(s => s.status === 'offline' || s.status === 'error').length
  const criticalOffline = services.filter(s => s.critical && (s.status === 'offline' || s.status === 'error'))

  const getStatusIcon = (status: ServiceStatus['status']) => {
    switch (status) {
      case 'online':
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'offline':
      case 'error':
        return <XCircle className="h-4 w-4 text-red-500" />
      case 'checking':
        return <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
      default:
        return <div className="h-4 w-4 rounded-full bg-gray-300" />
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/95 backdrop-blur-sm">
      <Card className="w-full max-w-2xl mx-4 p-8 shadow-2xl">
        <div className="space-y-6">
          {/* Header */}
          <div className="text-center space-y-2">
            <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-500 to-purple-500 bg-clip-text text-transparent">
              Alpaca Trading System
            </h1>
            <p className="text-muted-foreground">Initializing services and data feeds...</p>
          </div>

          {/* Progress Bar */}
          <div className="space-y-2">
            <Progress value={progress} className="h-2" />
            <p className="text-sm text-center text-muted-foreground">
              {currentCheck || `Loading... ${Math.round(progress)}%`}
            </p>
          </div>

          {/* Service Status Grid */}
          <div className="space-y-3 max-h-96 overflow-y-auto pr-2">
            <div className="flex items-center justify-between text-sm text-muted-foreground mb-2">
              <span>Service Status</span>
              <span>{onlineCount} / {services.length} Online</span>
            </div>
            
            <div className="grid grid-cols-2 gap-3">
              {services.map(service => (
                <div
                  key={service.port}
                  className={`flex items-center justify-between p-3 rounded-lg border ${
                    service.status === 'online' 
                      ? 'bg-green-500/10 border-green-500/30'
                      : service.status === 'offline' || service.status === 'error'
                      ? 'bg-red-500/10 border-red-500/30'
                      : service.status === 'checking'
                      ? 'bg-blue-500/10 border-blue-500/30'
                      : 'bg-muted'
                  }`}
                >
                  <div className="flex items-center space-x-2">
                    {getStatusIcon(service.status)}
                    <div>
                      <p className="text-sm font-medium">
                        {service.name}
                        {service.critical && (
                          <span className="ml-1 text-xs text-yellow-500">*</span>
                        )}
                      </p>
                      <p className="text-xs text-muted-foreground">{service.description}</p>
                    </div>
                  </div>
                  <span className="text-xs text-muted-foreground">:{service.port}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Status Summary */}
          {criticalOffline.length > 0 && (
            <div className="p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/30">
              <div className="flex items-center space-x-2">
                <AlertTriangle className="h-4 w-4 text-yellow-500" />
                <p className="text-sm">
                  {criticalOffline.length} critical service{criticalOffline.length > 1 ? 's' : ''} offline
                </p>
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                Critical services marked with * must be running for trading
              </p>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex items-center justify-between">
            <p className="text-xs text-muted-foreground">
              * Critical services required for trading
            </p>
            <div className="flex space-x-2">
              {isRetrying && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={checkAllServices}
                  className="flex items-center space-x-1"
                >
                  <RefreshCw className="h-3 w-3" />
                  <span>Retry</span>
                </Button>
              )}
              {canProceed && (
                <Button
                  size="sm"
                  onClick={onServicesReady}
                  className="flex items-center space-x-1"
                >
                  <span>Continue Anyway</span>
                </Button>
              )}
            </div>
          </div>
        </div>
      </Card>
    </div>
  )
}