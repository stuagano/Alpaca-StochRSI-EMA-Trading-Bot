import { useState, useEffect, useRef, useCallback } from 'react';
import { Position, PortfolioSnapshot, PositionUpdate, SortConfig } from '../types/position';
import { PnLCalculator } from '../utils/calculations';

interface UsePositionsReturn {
  positions: Position[];
  portfolio: PortfolioSnapshot | null;
  sortConfig: SortConfig;
  isConnected: boolean;
  lastUpdate: string;
  setSortConfig: (config: SortConfig) => void;
  refreshData: () => void;
}

export const usePositions = (wsUrl?: string): UsePositionsReturn => {
  const [positions, setPositions] = useState<Position[]>([]);
  const [portfolio, setPortfolio] = useState<PortfolioSnapshot | null>(null);
  const [sortConfig, setSortConfig] = useState<SortConfig>({ key: 'none', direction: 'asc' });
  const [isConnected, setIsConnected] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<string>('');
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;

  const connectWebSocket = useCallback(() => {
    if (!wsUrl) return;

    try {
      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onopen = () => {
        console.log('WebSocket connected for positions');
        setIsConnected(true);
        reconnectAttempts.current = 0;
        
        // Subscribe to position updates
        wsRef.current?.send(JSON.stringify({
          action: 'subscribe',
          streams: ['positions', 'portfolio']
        }));
      };

      wsRef.current.onmessage = (event) => {
        try {
          const update: PositionUpdate = JSON.parse(event.data);
          setLastUpdate(new Date().toISOString());

          if (update.type === 'position_update') {
            const positionData = update.data as Position;
            
            setPositions(prev => {
              const existingIndex = prev.findIndex(p => p.symbol === positionData.symbol);
              
              if (existingIndex >= 0) {
                const updated = [...prev];
                updated[existingIndex] = {
                  ...positionData,
                  unrealized_pl: PnLCalculator.calculateUnrealizedPnL(positionData),
                  unrealized_plpc: PnLCalculator.calculateUnrealizedPnLPercent(positionData)
                };
                return updated;
              } else {
                return [...prev, {
                  ...positionData,
                  unrealized_pl: PnLCalculator.calculateUnrealizedPnL(positionData),
                  unrealized_plpc: PnLCalculator.calculateUnrealizedPnLPercent(positionData)
                }];
              }
            });
          } else if (update.type === 'portfolio_update') {
            setPortfolio(update.data as PortfolioSnapshot);
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      wsRef.current.onclose = () => {
        console.log('WebSocket disconnected');
        setIsConnected(false);
        
        // Attempt to reconnect
        if (reconnectAttempts.current < maxReconnectAttempts) {
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttempts.current++;
            console.log(`Attempting to reconnect (${reconnectAttempts.current}/${maxReconnectAttempts})`);
            connectWebSocket();
          }, Math.pow(2, reconnectAttempts.current) * 1000); // Exponential backoff
        }
      };

      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        setIsConnected(false);
      };
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      setIsConnected(false);
    }
  }, [wsUrl]);

  const refreshData = useCallback(async () => {
    try {
      // Fetch initial positions data
      const response = await fetch('/api/positions');
      if (response.ok) {
        const data = await response.json();
        setPositions(data.positions || []);
        setPortfolio(data.portfolio || null);
        setLastUpdate(new Date().toISOString());
      }
    } catch (error) {
      console.error('Error fetching positions data:', error);
    }
  }, []);

  // Sort positions based on current sort configuration
  const sortedPositions = React.useMemo(() => {
    if (sortConfig.key === 'none') return positions;

    return [...positions].sort((a, b) => {
      const aValue = a[sortConfig.key as keyof Position];
      const bValue = b[sortConfig.key as keyof Position];

      if (typeof aValue === 'string' && typeof bValue === 'string') {
        const comparison = aValue.localeCompare(bValue);
        return sortConfig.direction === 'asc' ? comparison : -comparison;
      }

      if (typeof aValue === 'number' && typeof bValue === 'number') {
        const comparison = aValue - bValue;
        return sortConfig.direction === 'asc' ? comparison : -comparison;
      }

      return 0;
    });
  }, [positions, sortConfig]);

  useEffect(() => {
    if (wsUrl) {
      connectWebSocket();
    } else {
      // Fallback to polling if no WebSocket URL
      refreshData();
      const interval = setInterval(refreshData, 5000); // Poll every 5 seconds
      return () => clearInterval(interval);
    }

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [wsUrl, connectWebSocket, refreshData]);

  return {
    positions: sortedPositions,
    portfolio,
    sortConfig,
    isConnected,
    lastUpdate,
    setSortConfig,
    refreshData
  };
};