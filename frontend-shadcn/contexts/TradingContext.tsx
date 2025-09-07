"use client"

import React, { createContext, useContext, useEffect, useState, useRef, ReactNode } from 'react'
import { unifiedAPIClient } from '@/lib/api/client'

interface Trade {
  id: string
  symbol: string
  side: 'buy' | 'sell'
  qty: number
  price: number
  value: number
  profit?: number
  profitPercent?: number
  timestamp: string
  status: 'filled' | 'pending' | 'cancelled'
}

interface ScalpingMetrics {
  trades_per_hour: number
  avg_trade_duration: string
  avg_profit_per_trade: number
  win_rate: number
  total_trades_today: number
  current_streak: number
  best_streak: number
  active_signals: number
  session_profit: number
  win_count: number
  loss_count: number
}

interface TradingContextType {
  trades: Trade[]
  metrics: ScalpingMetrics
  isLoading: boolean
  wsConnected: boolean
  refreshTrades: () => Promise<void>
}

const TradingContext = createContext<TradingContextType | undefined>(undefined)

interface TradingProviderProps {
  children: ReactNode
}

export function TradingProvider({ children }: TradingProviderProps) {
  const [trades, setTrades] = useState<Trade[]>([])
  const [metrics, setMetrics] = useState<ScalpingMetrics>({
    trades_per_hour: 0,
    avg_trade_duration: '0m',
    avg_profit_per_trade: 0,
    win_rate: 0,
    total_trades_today: 0,
    current_streak: 0,
    best_streak: 0,
    active_signals: 0,
    session_profit: 0,
    win_count: 0,
    loss_count: 0
  })
  const [isLoading, setIsLoading] = useState(false)
  const [wsConnected, setWsConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  const refreshTrades = async () => {
    try {
      setIsLoading(true)
      console.log('🔄 TradingContext: Fetching trade log...')
      const response = await fetch('http://localhost:9000/api/trade-log')
      const data = await response.json()
      console.log('✅ TradingContext: Trade log response:', data)
      
      if (data.trades && Array.isArray(data.trades)) {
        const formattedTrades = data.trades.map((trade: any, index: number) => ({
          id: trade.id || `trade-${index}`,
          symbol: trade.symbol,
          side: trade.side,
          qty: parseFloat(trade.qty) || 0,
          price: parseFloat(trade.price) || 0,
          value: parseFloat(trade.value) || (trade.qty * trade.price),
          profit: parseFloat(trade.profit) || 0,
          profitPercent: parseFloat(trade.profit_percent) || 0,
          timestamp: trade.timestamp || new Date().toISOString(),
          status: trade.status || 'filled'
        }))
        
        // Sort by timestamp descending (newest first)
        const sortedTrades = formattedTrades.sort((a: Trade, b: Trade) => 
          new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
        )
        
        setTrades(sortedTrades.slice(0, 50)) // Keep last 50 trades
        
        console.log('✅ TradingContext: Processed', sortedTrades.length, 'trades')
        console.log('📊 TradingContext: Sample trade:', sortedTrades[0])
        
        // Calculate metrics from real trade data
        const now = new Date()
        const hourAgo = new Date(now.getTime() - 60 * 60 * 1000)
        const dayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate())
        
        // Trades in the last hour
        const recentTrades = sortedTrades.filter((t: Trade) => 
          new Date(t.timestamp) >= hourAgo
        )
        
        // Trades today
        const todayTrades = sortedTrades.filter((t: Trade) => 
          new Date(t.timestamp) >= dayStart
        )
        
        // Profitable trades
        const profitableTrades = sortedTrades.filter((t: Trade) => 
          t.profit !== undefined && t.profit > 0
        )
        
        const lossTrades = sortedTrades.filter((t: Trade) => 
          t.profit !== undefined && t.profit < 0
        )
        
        // Session profit
        const sessionProfit = sortedTrades.reduce((sum: number, t: Trade) => 
          sum + (t.profit || 0), 0
        )
        
        // Average trade duration (mock based on trade frequency)
        const avgDuration = recentTrades.length > 1 
          ? Math.max(30, Math.floor(3600 / recentTrades.length)) // seconds
          : 120 // default 2 minutes
        
        const formatDuration = (seconds: number) => {
          if (seconds < 60) return `${seconds}s`
          const minutes = Math.floor(seconds / 60)
          const remainingSeconds = seconds % 60
          return remainingSeconds > 0 ? `${minutes}m ${remainingSeconds}s` : `${minutes}m`
        }
        
        // Calculate current winning/losing streak
        let currentStreak = 0
        for (let i = 0; i < sortedTrades.length; i++) {
          const trade = sortedTrades[i]
          if (trade.profit === undefined) break
          
          if (i === 0) {
            currentStreak = trade.profit > 0 ? 1 : trade.profit < 0 ? -1 : 0
          } else {
            const prevTrade = sortedTrades[i - 1]
            if (trade.profit > 0 && prevTrade.profit > 0) {
              currentStreak++
            } else if (trade.profit < 0 && prevTrade.profit < 0) {
              currentStreak--
            } else {
              break
            }
          }
        }
        
        setMetrics({
          trades_per_hour: recentTrades.length,
          avg_trade_duration: formatDuration(avgDuration),
          avg_profit_per_trade: profitableTrades.length > 0 
            ? profitableTrades.reduce((sum: number, t: Trade) => sum + (t.profit || 0), 0) / profitableTrades.length
            : 0,
          win_rate: sortedTrades.length > 0 
            ? profitableTrades.length / sortedTrades.filter(t => t.profit !== undefined).length
            : 0,
          total_trades_today: todayTrades.length,
          current_streak: Math.abs(currentStreak),
          best_streak: Math.max(...Array.from({length: Math.min(20, sortedTrades.length)}, (_, i) => {
            let streak = 0
            for (let j = i; j < sortedTrades.length; j++) {
              if (sortedTrades[j].profit > 0) streak++
              else break
            }
            return streak
          })),
          active_signals: 0, // This would come from signal generation
          session_profit: sessionProfit,
          win_count: profitableTrades.length,
          loss_count: lossTrades.length
        })
      }
    } catch (error) {
      console.error('Failed to fetch trades:', error)
    } finally {
      setIsLoading(false)
    }
  }

  // WebSocket connection management
  const connectWebSocket = () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return
    
    console.log('🔌 TradingContext: Connecting to WebSocket...')
    const ws = new WebSocket('ws://localhost:9000/ws/trading')
    
    ws.onopen = () => {
      console.log('✅ TradingContext: WebSocket connected')
      setWsConnected(true)
      // Clear any reconnect timeout
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
        reconnectTimeoutRef.current = null
      }
    }
    
    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data)
        console.log('📨 TradingContext: WebSocket message:', message)
        
        if (message.type === 'trade_update' && message.data) {
          // Add new trade to the front of the list
          setTrades(prev => {
            const newTrades = [message.data, ...prev].slice(0, 50)
            console.log('📊 TradingContext: Updated trades list with new trade')
            return newTrades
          })
          
          // Update metrics if profit data is available
          if (message.data.profit !== null && message.data.profit !== undefined) {
            setMetrics(prev => {
              const newMetrics = { ...prev }
              newMetrics.session_profit += message.data.profit
              if (message.data.profit > 0) {
                newMetrics.win_count++
              } else {
                newMetrics.loss_count++
              }
              newMetrics.total_trades_today++
              if (newMetrics.win_count + newMetrics.loss_count > 0) {
                newMetrics.win_rate = newMetrics.win_count / (newMetrics.win_count + newMetrics.loss_count)
              }
              return newMetrics
            })
          }
        }
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error)
      }
    }
    
    ws.onerror = (error) => {
      console.error('❌ TradingContext: WebSocket error:', error)
      setWsConnected(false)
    }
    
    ws.onclose = () => {
      console.log('🔌 TradingContext: WebSocket disconnected')
      setWsConnected(false)
      wsRef.current = null
      
      // Attempt to reconnect after 3 seconds
      reconnectTimeoutRef.current = setTimeout(() => {
        console.log('🔄 TradingContext: Attempting to reconnect...')
        connectWebSocket()
      }, 3000)
    }
    
    wsRef.current = ws
  }
  
  // Initialize WebSocket and fetch initial data
  useEffect(() => {
    refreshTrades() // Get initial data
    connectWebSocket() // Connect to WebSocket
    
    // Also poll every 5 seconds as fallback
    const interval = setInterval(refreshTrades, 5000)
    
    return () => {
      clearInterval(interval)
      if (wsRef.current) {
        wsRef.current.close()
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
    }
  }, [])

  const value = {
    trades,
    metrics,
    isLoading,
    wsConnected,
    refreshTrades
  }

  return (
    <TradingContext.Provider value={value}>
      {children}
    </TradingContext.Provider>
  )
}

export function useTradingContext() {
  const context = useContext(TradingContext)
  if (context === undefined) {
    throw new Error('useTradingContext must be used within a TradingProvider')
  }
  return context
}