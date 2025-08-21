import React, { useState } from 'react';
import { Position, SortConfig } from '../../types/position';
import { PnLCalculator } from '../../utils/calculations';
import { ChevronUp, ChevronDown, ArrowUpDown, Eye, Download } from 'lucide-react';
import { PositionDetailModal } from './PositionDetailModal';

interface PositionsTableProps {
  positions: Position[];
  sortConfig: SortConfig;
  onSort: (config: SortConfig) => void;
  onExport: () => void;
}

export const PositionsTable: React.FC<PositionsTableProps> = ({
  positions,
  sortConfig,
  onSort,
  onExport
}) => {
  const [selectedPosition, setSelectedPosition] = useState<Position | null>(null);

  const getSortIcon = (columnKey: keyof Position) => {
    if (sortConfig.key !== columnKey) {
      return <ArrowUpDown size={16} className="text-gray-400" />;
    }
    return sortConfig.direction === 'asc' 
      ? <ChevronUp size={16} className="text-blue-600" />
      : <ChevronDown size={16} className="text-blue-600" />;
  };

  const handleSort = (columnKey: keyof Position) => {
    const direction = 
      sortConfig.key === columnKey && sortConfig.direction === 'asc' 
        ? 'desc' 
        : 'asc';
    onSort({ key: columnKey, direction });
  };

  const columns = [
    { key: 'symbol' as keyof Position, label: 'Symbol', sortable: true },
    { key: 'side' as keyof Position, label: 'Side', sortable: true },
    { key: 'qty' as keyof Position, label: 'Quantity', sortable: true },
    { key: 'avg_entry_price' as keyof Position, label: 'Avg Price', sortable: true },
    { key: 'current_price' as keyof Position, label: 'Current Price', sortable: true },
    { key: 'market_value' as keyof Position, label: 'Market Value', sortable: true },
    { key: 'unrealized_pl' as keyof Position, label: 'Unrealized P&L', sortable: true },
    { key: 'unrealized_plpc' as keyof Position, label: 'Unrealized P&L %', sortable: true },
    { key: 'change_today' as keyof Position, label: 'Day Change', sortable: true }
  ];

  if (positions.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-8">
        <div className="text-center">
          <div className="text-gray-400 dark:text-gray-600 mb-4">
            <Eye size={48} className="mx-auto" />
          </div>
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
            No positions found
          </h3>
          <p className="text-gray-500 dark:text-gray-400">
            You don't have any open positions at the moment.
          </p>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
              Positions ({positions.length})
            </h2>
            <button
              onClick={onExport}
              className="inline-flex items-center px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              <Download size={16} className="mr-2" />
              Export CSV
            </button>
          </div>
        </div>

        {/* Desktop Table */}
        <div className="hidden lg:block overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead className="bg-gray-50 dark:bg-gray-900">
              <tr>
                {columns.map((column) => (
                  <th
                    key={column.key}
                    className={`px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider ${
                      column.sortable ? 'cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800' : ''
                    }`}
                    onClick={() => column.sortable && handleSort(column.key)}
                  >
                    <div className="flex items-center space-x-1">
                      <span>{column.label}</span>
                      {column.sortable && getSortIcon(column.key)}
                    </div>
                  </th>
                ))}
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
              {positions.map((position, index) => {
                const dayChange = PnLCalculator.calculateDayChange(position);
                return (
                  <tr key={`${position.symbol}-${index}`} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className="font-medium text-gray-900 dark:text-white">
                          {position.symbol}
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                        position.side === 'long' 
                          ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                          : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                      }`}>
                        {position.side.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                      {Math.abs(position.qty).toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                      {PnLCalculator.formatCurrency(position.avg_entry_price, 4)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                      {PnLCalculator.formatCurrency(position.current_price, 4)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                      {PnLCalculator.formatCurrency(position.market_value)}
                    </td>
                    <td className={`px-6 py-4 whitespace-nowrap text-sm font-medium ${PnLCalculator.getPnLColorClass(position.unrealized_pl)}`}>
                      {PnLCalculator.formatCurrency(position.unrealized_pl)}
                    </td>
                    <td className={`px-6 py-4 whitespace-nowrap text-sm font-medium ${PnLCalculator.getPnLColorClass(position.unrealized_plpc)}`}>
                      {PnLCalculator.formatPercent(position.unrealized_plpc)}
                    </td>
                    <td className={`px-6 py-4 whitespace-nowrap text-sm font-medium ${PnLCalculator.getPnLColorClass(dayChange.amount)}`}>
                      <div>
                        <div>{PnLCalculator.formatCurrency(dayChange.amount)}</div>
                        <div className="text-xs">
                          {PnLCalculator.formatPercent(dayChange.percent)}
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      <button
                        onClick={() => setSelectedPosition(position)}
                        className="text-blue-600 hover:text-blue-900 dark:text-blue-400 dark:hover:text-blue-300"
                      >
                        <Eye size={16} />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Mobile Cards */}
        <div className="lg:hidden">
          {positions.map((position, index) => {
            const dayChange = PnLCalculator.calculateDayChange(position);
            return (
              <div key={`${position.symbol}-${index}`} className="p-4 border-b border-gray-200 dark:border-gray-700">
                <div className="flex justify-between items-start mb-2">
                  <div className="flex items-center space-x-2">
                    <span className="font-medium text-gray-900 dark:text-white">
                      {position.symbol}
                    </span>
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                      position.side === 'long' 
                        ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                        : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                    }`}>
                      {position.side.toUpperCase()}
                    </span>
                  </div>
                  <button
                    onClick={() => setSelectedPosition(position)}
                    className="text-blue-600 hover:text-blue-900 dark:text-blue-400 dark:hover:text-blue-300"
                  >
                    <Eye size={16} />
                  </button>
                </div>
                
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div>
                    <span className="text-gray-500 dark:text-gray-400">Quantity:</span>
                    <span className="ml-1 font-medium text-gray-900 dark:text-white">
                      {Math.abs(position.qty).toLocaleString()}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-500 dark:text-gray-400">Market Value:</span>
                    <span className="ml-1 font-medium text-gray-900 dark:text-white">
                      {PnLCalculator.formatCurrency(position.market_value)}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-500 dark:text-gray-400">Unrealized P&L:</span>
                    <span className={`ml-1 font-medium ${PnLCalculator.getPnLColorClass(position.unrealized_pl)}`}>
                      {PnLCalculator.formatCurrency(position.unrealized_pl)}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-500 dark:text-gray-400">Day Change:</span>
                    <span className={`ml-1 font-medium ${PnLCalculator.getPnLColorClass(dayChange.amount)}`}>
                      {PnLCalculator.formatCurrency(dayChange.amount)}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {selectedPosition && (
        <PositionDetailModal
          position={selectedPosition}
          isOpen={selectedPosition !== null}
          onClose={() => setSelectedPosition(null)}
        />
      )}
    </>
  );
};