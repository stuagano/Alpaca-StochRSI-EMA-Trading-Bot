import React, { useState } from 'react';
import { usePositions } from '../../hooks/usePositions';
import { PnLCalculator } from '../../utils/calculations';
import { TrendingUp, TrendingDown, Eye, EyeOff, RefreshCw } from 'lucide-react';

interface PositionsWidgetProps {
  wsUrl?: string;
  maxItems?: number;
  showControls?: boolean;
  className?: string;
}

export const PositionsWidget: React.FC<PositionsWidgetProps> = ({
  wsUrl,
  maxItems = 5,
  showControls = true,
  className = ''
}) => {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const {
    positions,
    portfolio,
    isConnected,
    lastUpdate,
    refreshData
  } = usePositions(wsUrl);

  const displayPositions = positions.slice(0, maxItems);
  const totalPositions = positions.length;

  if (isCollapsed) {
    return (
      <div className={`bg-white dark:bg-gray-800 rounded-lg shadow-md p-4 ${className}`}>
        <div className="flex justify-between items-center">
          <span className="text-sm font-medium text-gray-600 dark:text-gray-300">
            Positions ({totalPositions})
          </span>
          <button
            onClick={() => setIsCollapsed(false)}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            <Eye size={16} />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-white dark:bg-gray-800 rounded-lg shadow-md ${className}`}>
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex justify-between items-center">
          <div className="flex items-center space-x-2">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white">
              Positions
            </h3>
            <span className="text-sm text-gray-500 dark:text-gray-400">
              ({totalPositions})
            </span>
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
          </div>
          
          {showControls && (
            <div className="flex items-center space-x-2">
              <button
                onClick={refreshData}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                title="Refresh"
              >
                <RefreshCw size={16} />
              </button>
              <button
                onClick={() => setIsCollapsed(true)}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                title="Collapse"
              >
                <EyeOff size={16} />
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Portfolio Summary */}
      {portfolio && (
        <div className="p-4 border-b border-gray-200 dark:border-gray-700">
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-gray-500 dark:text-gray-400">Portfolio Value</p>
              <p className="font-semibold text-gray-900 dark:text-white">
                {PnLCalculator.formatCurrency(portfolio.portfolio_value)}
              </p>
            </div>
            <div>
              <p className="text-gray-500 dark:text-gray-400">Day P&L</p>
              <p className={`font-semibold ${PnLCalculator.getPnLColorClass(portfolio.day_pl)}`}>
                {PnLCalculator.formatCurrency(portfolio.day_pl)}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Positions List */}
      <div className="max-h-80 overflow-y-auto">
        {displayPositions.length === 0 ? (
          <div className="p-4 text-center text-gray-500 dark:text-gray-400">
            No positions found
          </div>
        ) : (
          displayPositions.map((position, index) => {
            const dayChange = PnLCalculator.calculateDayChange(position);
            return (
              <div
                key={`${position.symbol}-${index}`}
                className="p-3 border-b border-gray-100 dark:border-gray-700 last:border-b-0 hover:bg-gray-50 dark:hover:bg-gray-700"
              >
                <div className="flex justify-between items-start">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2">
                      <span className="font-medium text-gray-900 dark:text-white">
                        {position.symbol}
                      </span>
                      <span className={`inline-flex px-1.5 py-0.5 text-xs font-medium rounded ${
                        position.side === 'long' 
                          ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
                          : 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300'
                      }`}>
                        {position.side.charAt(0).toUpperCase()}
                      </span>
                    </div>
                    
                    <div className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                      {Math.abs(position.qty).toLocaleString()} @ {PnLCalculator.formatCurrency(position.current_price, 2)}
                    </div>
                  </div>
                  
                  <div className="text-right ml-2">
                    <div className={`text-sm font-medium ${PnLCalculator.getPnLColorClass(position.unrealized_pl)}`}>
                      {PnLCalculator.formatCurrency(position.unrealized_pl)}
                    </div>
                    <div className={`text-xs ${PnLCalculator.getPnLColorClass(position.unrealized_plpc)}`}>
                      {PnLCalculator.formatPercent(position.unrealized_plpc)}
                    </div>
                  </div>
                </div>
                
                <div className="mt-2 flex justify-between items-center text-xs">
                  <span className="text-gray-500 dark:text-gray-400">
                    Market: {PnLCalculator.formatCurrency(position.market_value)}
                  </span>
                  <div className={`flex items-center space-x-1 ${PnLCalculator.getPnLColorClass(dayChange.amount)}`}>
                    {dayChange.amount >= 0 ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
                    <span>{PnLCalculator.formatCurrency(dayChange.amount)}</span>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Footer */}
      {totalPositions > maxItems && (
        <div className="p-3 border-t border-gray-200 dark:border-gray-700 text-center">
          <span className="text-xs text-gray-500 dark:text-gray-400">
            Showing {maxItems} of {totalPositions} positions
          </span>
        </div>
      )}

      {lastUpdate && (
        <div className="px-4 py-2 bg-gray-50 dark:bg-gray-900 text-xs text-gray-500 dark:text-gray-400">
          Last update: {new Date(lastUpdate).toLocaleTimeString()}
        </div>
      )}
    </div>
  );
};