import { useState, useEffect, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import alpacaAPI from '@/lib/api/alpaca'
import { Position, Order, Account, Signal, Bar } from '@/types/alpaca'
import { toast } from 'sonner'

// Account Hook
export function useAccount() {
  return useQuery({
    queryKey: ['account'],
    queryFn: () => alpacaAPI.getAccount(),
    refetchInterval: 30000, // Refresh every 30 seconds
  })
}

// Positions Hook
export function usePositions() {
  return useQuery({
    queryKey: ['positions'],
    queryFn: () => alpacaAPI.getPositions(),
    refetchInterval: 5000, // Refresh every 5 seconds
  })
}

// Orders Hook
export function useOrders(status?: 'open' | 'closed' | 'all') {
  return useQuery({
    queryKey: ['orders', status],
    queryFn: () => alpacaAPI.getOrders(status),
    refetchInterval: 5000,
  })
}

// Market Data Hook
export function useMarketData(
  symbol: string,
  timeframe: '1Min' | '5Min' | '15Min' | '1Hour' | '1Day' = '5Min'
) {
  return useQuery({
    queryKey: ['marketData', symbol, timeframe],
    queryFn: () => alpacaAPI.getBars(symbol, timeframe, 100),
    refetchInterval: 60000, // Refresh every minute
    enabled: !!symbol,
  })
}

// Trading Signals Hook
export function useSignals(symbols?: string[]) {
  return useQuery({
    queryKey: ['signals', symbols],
    queryFn: () => alpacaAPI.getSignals(symbols),
    refetchInterval: 10000, // Refresh every 10 seconds
  })
}

// Indicators Hook
export function useIndicators(symbol: string) {
  return useQuery({
    queryKey: ['indicators', symbol],
    queryFn: () => alpacaAPI.getIndicators(symbol),
    refetchInterval: 5000,
    enabled: !!symbol,
  })
}

// Performance Metrics Hook
export function usePerformanceMetrics() {
  return useQuery({
    queryKey: ['performanceMetrics'],
    queryFn: () => alpacaAPI.getPerformanceMetrics(),
    refetchInterval: 60000,
  })
}

// Risk Metrics Hook
export function useRiskMetrics() {
  return useQuery({
    queryKey: ['riskMetrics'],
    queryFn: () => alpacaAPI.getRiskMetrics(),
    refetchInterval: 30000,
  })
}

// Submit Order Hook
export function useSubmitOrder() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: alpacaAPI.submitOrder,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['orders'] })
      queryClient.invalidateQueries({ queryKey: ['positions'] })
      queryClient.invalidateQueries({ queryKey: ['account'] })
      toast.success(`Order submitted: ${data.side.toUpperCase()} ${data.qty} ${data.symbol}`)
    },
    onError: (error: Error) => {
      toast.error(`Order failed: ${error.message}`)
    },
  })
}

// Cancel Order Hook
export function useCancelOrder() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: alpacaAPI.cancelOrder,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['orders'] })
      toast.success('Order cancelled')
    },
    onError: (error: Error) => {
      toast.error(`Failed to cancel order: ${error.message}`)
    },
  })
}

// Close Position Hook
export function useClosePosition() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: alpacaAPI.closePosition,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['positions'] })
      queryClient.invalidateQueries({ queryKey: ['account'] })
      toast.success(`Position closed: ${data.symbol}`)
    },
    onError: (error: Error) => {
      toast.error(`Failed to close position: ${error.message}`)
    },
  })
}

// WebSocket Hook for Real-time Data
export function useWebSocket(symbols: string[], onMessage: (data: any) => void) {
  const [ws, setWs] = useState<any>(null)
  const [isConnected, setIsConnected] = useState(false)

  useEffect(() => {
    if (symbols.length === 0) return

    const websocket = alpacaAPI.connectToStream((data) => {
      onMessage(data)
      setIsConnected(true)
    }, symbols)

    // Handle both WebSocket and mock connection types
    if ('onopen' in websocket) {
      websocket.onopen = () => {
        setIsConnected(true)
        console.log('WebSocket connected')
      }

      websocket.onclose = () => {
        setIsConnected(false)
        console.log('WebSocket disconnected')
      }

      websocket.onerror = () => {
        setIsConnected(false)
        console.log('WebSocket error')
      }
    } else {
      // Mock connection - assume connected
      setIsConnected(true)
    }

    setWs(websocket)

    return () => {
      if (websocket && websocket.close) {
        websocket.close()
      }
    }
  }, [symbols.join(',')]) // Re-connect when symbols change

  return { ws, isConnected }
}

// Portfolio History Hook
export function usePortfolioHistory(period: '1D' | '1W' | '1M' | '3M' | '1Y' = '1M') {
  return useQuery({
    queryKey: ['portfolioHistory', period],
    queryFn: () => alpacaAPI.getPortfolioHistory(period),
    refetchInterval: 300000, // Refresh every 5 minutes
  })
}

// Multi-Symbol Quotes Hook
export function useMultipleQuotes(symbols: string[]) {
  return useQuery({
    queryKey: ['quotes', symbols],
    queryFn: () => alpacaAPI.getMultipleQuotes(symbols),
    refetchInterval: 5000,
    enabled: symbols.length > 0,
  })
}

// Crypto Trading Hooks
export function useCryptoAssets() {
  return useQuery({
    queryKey: ['cryptoAssets'],
    queryFn: async () => {
      const response = await fetch('http://localhost:9000/api/crypto/assets')
      return response.json()
    },
    refetchInterval: 300000, // Refresh every 5 minutes
  })
}

export function useCryptoPositions() {
  return useQuery({
    queryKey: ['cryptoPositions'],
    queryFn: async () => {
      const response = await fetch('http://localhost:9000/api/crypto/positions')
      return response.json()
    },
    refetchInterval: 5000, // Refresh every 5 seconds
  })
}

export function useCryptoQuote(symbol: string) {
  return useQuery({
    queryKey: ['cryptoQuote', symbol],
    queryFn: async () => {
      // Convert symbol format (BTC/USD -> BTC/USD)
      const response = await fetch(`http://localhost:9000/api/crypto/quotes/${symbol.replace('/', '/')}`)
      return response.json()
    },
    refetchInterval: 1000, // Refresh every second for crypto
    enabled: !!symbol,
  })
}

export function useCryptoSignals(symbol: string) {
  return useQuery({
    queryKey: ['cryptoSignals', symbol],
    queryFn: async () => {
      const response = await fetch(`http://localhost:9000/api/crypto/signals/${symbol}`)
      return response.json()
    },
    refetchInterval: 5000,
    enabled: !!symbol,
  })
}

export function useSubmitCryptoOrder() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async (orderData: any) => {
      const response = await fetch('http://localhost:9000/api/crypto/orders', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(orderData),
      })
      
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Order failed')
      }
      
      return response.json()
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['cryptoPositions'] })
      queryClient.invalidateQueries({ queryKey: ['account'] })
      toast.success(`Crypto order submitted: ${data.side.toUpperCase()} ${data.symbol}`)
    },
    onError: (error: Error) => {
      toast.error(`Crypto order failed: ${error.message}`)
    },
  })
}

// Crypto WebSocket Hook
export function useCryptoWebSocket(onMessage: (data: any) => void) {
  const [isConnected, setIsConnected] = useState(false)

  useEffect(() => {
    // Connect to crypto trading service WebSocket
    const wsUrl = `ws://localhost:9012/ws/trading`
    
    try {
      const ws = new WebSocket(wsUrl)

      ws.onopen = () => {
        setIsConnected(true)
        console.log('Crypto WebSocket connected')
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          onMessage(data)
        } catch (error) {
          console.error('Error parsing WebSocket message:', error)
        }
      }

      ws.onclose = () => {
        setIsConnected(false)
        // Silent close - no console log for expected disconnections
      }

      ws.onerror = () => {
        setIsConnected(false)
        // Silent error - WebSocket connection is optional for crypto tab
        // The tab will still work with polling via REST API
      }

      return () => {
        ws.close()
      }
    } catch (error) {
      // If WebSocket fails to create, just use polling instead
      setIsConnected(false)
      return () => {}
    }
  }, [])

  return { isConnected }
}