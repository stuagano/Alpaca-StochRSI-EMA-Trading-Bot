import { useState, useEffect, useCallback, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import unifiedAPIClient, { MarketMode } from '@/lib/api/client'
// Removed alpacaAPI import - using UnifiedAPIClient directly
import { Position, Order, Account, Signal, Bar } from '@/types/alpaca'
import { toast } from 'sonner'

// Account Hook
export function useAccount(marketMode: MarketMode = 'stocks') {
  return useQuery({
    queryKey: ['account', marketMode],
    queryFn: async () => {
      console.log(`📊 Fetching account data for ${marketMode}...`)
      const data = await unifiedAPIClient.getAccount(marketMode)
      console.log(`✅ Account data received:`, data)
      return data
    },
    refetchInterval: 60000, // Refresh every 60 seconds (reduced from 30s)
  })
}

// Positions Hook
export function usePositions(marketMode: MarketMode = 'stocks') {
  return useQuery({
    queryKey: ['positions', marketMode],
    queryFn: async () => {
      console.log(`📈 Fetching positions for ${marketMode}...`)
      let data
      // Use unified API client for both stocks and crypto
      data = await unifiedAPIClient.getPositions(marketMode)
      console.log(`✅ Positions received (${marketMode}):`, data?.length || 0, 'positions')
      return data
    },
    refetchInterval: 30000, // Refresh every 30 seconds (was 5s - causing performance issues)
  })
}

// Orders Hook
export function useOrders(status?: 'open' | 'closed' | 'all', marketMode: MarketMode = 'stocks') {
  return useQuery({
    queryKey: ['orders', status, marketMode],
    queryFn: async () => {
      return unifiedAPIClient.getOrders(status, marketMode)
    },
    refetchInterval: 30000, // Refresh every 30 seconds (was 5s)
  })
}

// Market Data Hook
export function useMarketData(
  symbol: string,
  timeframe: '1Min' | '5Min' | '15Min' | '1Hour' | '1Day' = '5Min',
  marketMode: MarketMode = 'stocks'
) {
  return useQuery({
    queryKey: ['marketData', symbol, timeframe, marketMode],
    queryFn: () => unifiedAPIClient.getBars(symbol, timeframe, 100, marketMode),
    refetchInterval: 120000, // Refresh every 2 minutes (was 1 minute)
    enabled: !!symbol,
  })
}

// Trading Signals Hook
export function useSignals(symbols?: string[], marketMode: MarketMode = 'stocks') {
  return useQuery({
    queryKey: ['signals', symbols, marketMode],
    queryFn: async () => {
      return unifiedAPIClient.getSignals(symbols, marketMode)
    },
    refetchInterval: 30000, // Refresh every 30 seconds (was 10s)
  })
}

// Indicators Hook
export function useIndicators(symbol: string, marketMode: MarketMode = 'stocks') {
  return useQuery({
    queryKey: ['indicators', symbol, marketMode],
    queryFn: () => unifiedAPIClient.getIndicators(symbol, marketMode),
    refetchInterval: 60000, // Refresh every minute (was 5s - causing performance issues)
    enabled: !!symbol,
  })
}

// Performance Metrics Hook
export function usePerformanceMetrics(marketMode: MarketMode = 'stocks') {
  return useQuery({
    queryKey: ['performanceMetrics', marketMode],
    queryFn: async () => {
      console.log(`📊 Fetching performance metrics for ${marketMode}...`)
      const data = await unifiedAPIClient.getPerformanceMetrics(marketMode)
      console.log(`✅ Performance metrics received:`, data)
      return data
    },
    refetchInterval: 120000, // Refresh every 2 minutes
  })
}

// Trading History Hook
export function useTradingHistory(marketMode: MarketMode = 'stocks') {
  return useQuery({
    queryKey: ['tradingHistory', marketMode],
    queryFn: async () => {
      console.log(`📜 Fetching trading history for ${marketMode}...`)
      const data = await unifiedAPIClient.getTradingHistory(marketMode)
      console.log(`✅ Trading history received:`, data)
      return data
    },
    refetchInterval: 300000, // Refresh every 5 minutes
  })
}

// P&L Chart Hook
export function usePnlChart(marketMode: MarketMode = 'stocks') {
  return useQuery({
    queryKey: ['pnlChart', marketMode],
    queryFn: async () => {
      console.log(`📈 Fetching P&L chart for ${marketMode}...`)
      const data = await unifiedAPIClient.getPnlChart(marketMode)
      console.log(`✅ P&L chart data received:`, data)
      return data
    },
    refetchInterval: 60000, // Refresh every minute
  })
}

// Trading Metrics Hook
export function useTradingMetrics(marketMode: MarketMode = 'stocks') {
  return useQuery({
    queryKey: ['tradingMetrics', marketMode],
    queryFn: async () => {
      console.log(`📊 Fetching trading metrics for ${marketMode}...`)
      const data = await unifiedAPIClient.getMetrics(marketMode)
      console.log(`✅ Trading metrics received:`, data)
      return data
    },
    refetchInterval: 60000, // Refresh every minute
  })
}

// Trading Strategies Hook
export function useTradingStrategies(marketMode: MarketMode = 'stocks') {
  return useQuery({
    queryKey: ['tradingStrategies', marketMode],
    queryFn: async () => {
      console.log(`🎯 Fetching trading strategies for ${marketMode}...`)
      const data = await unifiedAPIClient.getStrategies(marketMode)
      console.log(`✅ Trading strategies received:`, data)
      return data
    },
    refetchInterval: 300000, // Refresh every 5 minutes
  })
}

// Risk Metrics Hook
export function useRiskMetrics(marketMode: MarketMode = 'stocks') {
  return useQuery({
    queryKey: ['riskMetrics', marketMode],
    queryFn: async () => {
      return unifiedAPIClient.getRiskMetrics(marketMode)
    },
    refetchInterval: 60000, // Refresh every minute (was 30s)
  })
}

// Submit Order Hook
export function useSubmitOrder(marketMode: MarketMode = 'stocks') {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (orderData: any) => unifiedAPIClient.submitOrder(orderData, marketMode),
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
export function useCancelOrder(marketMode: MarketMode = 'stocks') {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (orderId: string) => unifiedAPIClient.cancelOrder(orderId, marketMode),
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
export function useClosePosition(marketMode: MarketMode = 'stocks') {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (symbol: string) => unifiedAPIClient.closePosition(symbol, marketMode),
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

// WebSocket Hook for Real-time Data - Fixed for React StrictMode with proper cleanup
export function useWebSocket(symbols: string[], onMessage: (data: any) => void, marketMode: MarketMode = 'stocks') {
  const [ws, setWs] = useState<WebSocket | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const isIntentionallyClosedRef = useRef(false)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (symbols.length === 0) return

    // Prevent duplicate connections during React StrictMode
    if (wsRef.current && wsRef.current.readyState === WebSocket.CONNECTING) {
      return
    }

    isIntentionallyClosedRef.current = false

    const connect = () => {
      if (isIntentionallyClosedRef.current) return
      
      // Close existing connection if any
      if (wsRef.current && wsRef.current.readyState !== WebSocket.CLOSED) {
        wsRef.current.close(1000, 'Reconnecting')
      }
      
      try {
        const websocket = unifiedAPIClient.connectToStream((data) => {
          onMessage(data)
        }, symbols, marketMode)

        websocket.onopen = () => {
          if (!isIntentionallyClosedRef.current) {
            setIsConnected(true)
            console.log(`${marketMode} WebSocket connected`)
            // Clear any pending reconnect
            if (reconnectTimeoutRef.current) {
              clearTimeout(reconnectTimeoutRef.current)
              reconnectTimeoutRef.current = null
            }
          }
        }

        websocket.onclose = (event) => {
          setIsConnected(false)
          console.log(`${marketMode} WebSocket disconnected`, event.code, event.reason)
          
          // Only reconnect for unexpected closures, not during development or intentional closes
          const shouldReconnect = !isIntentionallyClosedRef.current && 
                                 event.code !== 1000 && 
                                 event.code !== 1001 && // Going away
                                 !event.reason?.includes('unmounting')
          
          if (shouldReconnect && !reconnectTimeoutRef.current) {
            reconnectTimeoutRef.current = setTimeout(() => {
              console.log(`Attempting to reconnect ${marketMode} WebSocket...`)
              reconnectTimeoutRef.current = null
              connect()
            }, 5000)
          }
        }

        websocket.onerror = (error) => {
          setIsConnected(false)
          console.error(`${marketMode} WebSocket error:`, error)
        }

        wsRef.current = websocket
        setWs(websocket)
      } catch (error) {
        console.error(`Failed to create ${marketMode} WebSocket:`, error)
        setIsConnected(false)
      }
    }

    connect()

    // Cleanup function
    return () => {
      isIntentionallyClosedRef.current = true
      
      // Clear reconnect timeout
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
        reconnectTimeoutRef.current = null
      }
      
      // Close WebSocket connection
      if (wsRef.current) {
        if (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING) {
          wsRef.current.close(1000, 'Component unmounting')
        }
        wsRef.current = null
        setWs(null)
        setIsConnected(false)
      }
    }
  }, [symbols.join(','), marketMode]) // Removed onMessage from dependencies to prevent infinite loops

  return { ws, isConnected }
}

// Portfolio History Hook
export function usePortfolioHistory(period: '1D' | '1W' | '1M' | '3M' | '1Y' = '1M', marketMode: MarketMode = 'stocks') {
  return useQuery({
    queryKey: ['portfolioHistory', period, marketMode],
    queryFn: () => unifiedAPIClient.getPortfolioHistory(period, marketMode),
    refetchInterval: 300000, // Refresh every 5 minutes
  })
}

// Multi-Symbol Quotes Hook
export function useMultipleQuotes(symbols: string[], marketMode: MarketMode = 'stocks') {
  return useQuery({
    queryKey: ['quotes', symbols, marketMode],
    queryFn: () => {
      if (marketMode === 'crypto') {
        // For crypto, fetch individual quotes and combine
        return Promise.all(symbols.map(symbol => 
          unifiedAPIClient.getQuote(symbol, marketMode).then(quote => ({ [symbol]: quote }))
        )).then(quotes => Object.assign({}, ...quotes))
      } else {
        // Use unified client for stocks
        return Promise.all(symbols.map(symbol => 
          unifiedAPIClient.getQuote(symbol, marketMode).then(quote => ({ [symbol]: quote }))
        )).then(quotes => Object.assign({}, ...quotes))
      }
    },
    refetchInterval: 30000, // Refresh every 30 seconds (was 5s)
    enabled: symbols.length > 0,
  })
}

// Crypto Trading Hooks - Now using unified client
export function useCryptoAssets() {
  return useQuery({
    queryKey: ['cryptoAssets'],
    queryFn: async () => {
      return unifiedAPIClient.getCryptoAssets()
    },
    refetchInterval: 300000, // Refresh every 5 minutes
  })
}

export function useCryptoStatus() {
  return useQuery({
    queryKey: ['cryptoStatus'],
    queryFn: async () => {
      return unifiedAPIClient.getCryptoStatus()
    },
    refetchInterval: 30000, // Refresh every 30 seconds (was 5s - causing performance issues)
  })
}

export function useCryptoOpportunities() {
  return useQuery({
    queryKey: ['cryptoOpportunities'],
    queryFn: async () => {
      return unifiedAPIClient.getCryptoOpportunities()
    },
    refetchInterval: 45000, // Refresh every 45 seconds (was 15s)
  })
}

// Crypto WebSocket Hook - Now using unified client with proper cleanup
export function useCryptoWebSocket(onMessage: (data: any) => void) {
  const [isConnected, setIsConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const isClosingRef = useRef(false)

  useEffect(() => {
    isClosingRef.current = false
    
    try {
      const ws = unifiedAPIClient.connectToStream((data) => {
        onMessage(data)
      }, [], 'crypto')

      ws.onopen = () => {
        if (!isClosingRef.current) {
          setIsConnected(true)
        }
      }

      ws.onclose = () => {
        setIsConnected(false)
      }

      ws.onerror = () => {
        setIsConnected(false)
      }

      wsRef.current = ws

      return () => {
        isClosingRef.current = true
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.close(1000, 'Component unmounting')
        }
        wsRef.current = null
      }
    } catch (error) {
      setIsConnected(false)
      return () => {}
    }
  }, []) // Removed onMessage dependency to prevent reconnection loops

  return { isConnected }
}