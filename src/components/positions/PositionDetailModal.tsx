import React from 'react';
import { Position } from '../../types/position';
import { PnLCalculator } from '../../utils/calculations';
import { X, TrendingUp, TrendingDown, DollarSign, Clock, Building } from 'lucide-react';

interface PositionDetailModalProps {
  position: Position;
  isOpen: boolean;
  onClose: () => void;
}

export const PositionDetailModal: React.FC<PositionDetailModalProps> = ({
  position,
  isOpen,
  onClose
}) => {
  if (!isOpen) return null;

  const dayChange = PnLCalculator.calculateDayChange(position);
  const costBasis = position.avg_entry_price * Math.abs(position.qty);

  const details = [
    {
      label: 'Symbol',
      value: position.symbol,
      icon: Building
    },
    {
      label: 'Side',
      value: position.side.toUpperCase(),
      valueColor: position.side === 'long' ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
    },
    {
      label: 'Quantity',
      value: Math.abs(position.qty).toLocaleString(),
      icon: DollarSign
    },
    {
      label: 'Average Entry Price',
      value: PnLCalculator.formatCurrency(position.avg_entry_price, 4)
    },
    {
      label: 'Current Price',
      value: PnLCalculator.formatCurrency(position.current_price, 4),
      icon: Clock
    },
    {
      label: 'Market Value',
      value: PnLCalculator.formatCurrency(position.market_value),
      icon: DollarSign
    },
    {
      label: 'Cost Basis',
      value: PnLCalculator.formatCurrency(costBasis)
    },
    {
      label: 'Unrealized P&L',
      value: PnLCalculator.formatCurrency(position.unrealized_pl),
      valueColor: PnLCalculator.getPnLColorClass(position.unrealized_pl),
      icon: position.unrealized_pl >= 0 ? TrendingUp : TrendingDown
    },
    {
      label: 'Unrealized P&L %',
      value: PnLCalculator.formatPercent(position.unrealized_plpc),
      valueColor: PnLCalculator.getPnLColorClass(position.unrealized_plpc)
    },
    {
      label: 'Day Change',
      value: PnLCalculator.formatCurrency(dayChange.amount),
      valueColor: PnLCalculator.getPnLColorClass(dayChange.amount),
      icon: dayChange.amount >= 0 ? TrendingUp : TrendingDown
    },
    {
      label: 'Day Change %',
      value: PnLCalculator.formatPercent(dayChange.percent),
      valueColor: PnLCalculator.getPnLColorClass(dayChange.percent)
    },
    {
      label: 'Asset Class',
      value: position.asset_class.replace('_', ' ').toUpperCase()
    },
    {
      label: 'Exchange',
      value: position.exchange.toUpperCase()
    }
  ];

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        {/* Background overlay */}
        <div 
          className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"
          onClick={onClose}
        ></div>

        {/* Modal panel */}
        <div className="inline-block align-bottom bg-white dark:bg-gray-800 rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
          <div className="bg-white dark:bg-gray-800 px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
            <div className="flex justify-between items-start mb-4">
              <h3 className="text-lg leading-6 font-medium text-gray-900 dark:text-white">
                Position Details - {position.symbol}
              </h3>
              <button
                onClick={onClose}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              >
                <X size={24} />
              </button>
            </div>

            <div className="space-y-4">
              {/* Summary Cards */}
              <div className="grid grid-cols-2 gap-4">
                <div className={`p-4 rounded-lg border ${
                  position.unrealized_pl >= 0 
                    ? 'bg-green-50 border-green-200 dark:bg-green-900/20 dark:border-green-800'
                    : 'bg-red-50 border-red-200 dark:bg-red-900/20 dark:border-red-800'
                }`}>
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-600 dark:text-gray-300">
                        Unrealized P&L
                      </p>
                      <p className={`text-lg font-semibold ${PnLCalculator.getPnLColorClass(position.unrealized_pl)}`}>
                        {PnLCalculator.formatCurrency(position.unrealized_pl)}
                      </p>
                      <p className={`text-sm ${PnLCalculator.getPnLColorClass(position.unrealized_plpc)}`}>
                        {PnLCalculator.formatPercent(position.unrealized_plpc)}
                      </p>
                    </div>
                    <div className={PnLCalculator.getPnLColorClass(position.unrealized_pl)}>
                      {position.unrealized_pl >= 0 ? <TrendingUp size={24} /> : <TrendingDown size={24} />}
                    </div>
                  </div>
                </div>

                <div className={`p-4 rounded-lg border ${
                  dayChange.amount >= 0 
                    ? 'bg-green-50 border-green-200 dark:bg-green-900/20 dark:border-green-800'
                    : 'bg-red-50 border-red-200 dark:bg-red-900/20 dark:border-red-800'
                }`}>
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-600 dark:text-gray-300">
                        Day Change
                      </p>
                      <p className={`text-lg font-semibold ${PnLCalculator.getPnLColorClass(dayChange.amount)}`}>
                        {PnLCalculator.formatCurrency(dayChange.amount)}
                      </p>
                      <p className={`text-sm ${PnLCalculator.getPnLColorClass(dayChange.percent)}`}>
                        {PnLCalculator.formatPercent(dayChange.percent)}
                      </p>
                    </div>
                    <div className={PnLCalculator.getPnLColorClass(dayChange.amount)}>
                      {dayChange.amount >= 0 ? <TrendingUp size={24} /> : <TrendingDown size={24} />}
                    </div>
                  </div>
                </div>
              </div>

              {/* Detailed Information */}
              <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4">
                <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-3">
                  Position Information
                </h4>
                <div className="space-y-3">
                  {details.map((detail, index) => (
                    <div key={index} className="flex justify-between items-center">
                      <div className="flex items-center space-x-2">
                        {detail.icon && (
                          <detail.icon size={16} className="text-gray-400" />
                        )}
                        <span className="text-sm text-gray-600 dark:text-gray-300">
                          {detail.label}
                        </span>
                      </div>
                      <span className={`text-sm font-medium ${
                        detail.valueColor || 'text-gray-900 dark:text-white'
                      }`}>
                        {detail.value}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Performance Metrics */}
              <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4">
                <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-3">
                  Performance Metrics
                </h4>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-600 dark:text-gray-300">Price Change:</span>
                    <div className={`font-medium ${PnLCalculator.getPnLColorClass(position.current_price - position.avg_entry_price)}`}>
                      {PnLCalculator.formatCurrency(position.current_price - position.avg_entry_price, 4)}
                    </div>
                  </div>
                  <div>
                    <span className="text-gray-600 dark:text-gray-300">Price Change %:</span>
                    <div className={`font-medium ${PnLCalculator.getPnLColorClass(position.current_price - position.avg_entry_price)}`}>
                      {PnLCalculator.formatPercent(((position.current_price - position.avg_entry_price) / position.avg_entry_price) * 100)}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-gray-50 dark:bg-gray-700 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
            <button
              type="button"
              className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-blue-600 text-base font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:ml-3 sm:w-auto sm:text-sm"
              onClick={onClose}
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};