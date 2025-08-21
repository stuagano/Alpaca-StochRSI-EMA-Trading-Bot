import React from 'react';
import { PortfolioSnapshot } from '../../types/position';
import { PnLCalculator } from '../../utils/calculations';
import { TrendingUp, TrendingDown, DollarSign, Wallet, Activity } from 'lucide-react';

interface PortfolioSummaryProps {
  portfolio: PortfolioSnapshot | null;
  isConnected: boolean;
  lastUpdate: string;
}

export const PortfolioSummary: React.FC<PortfolioSummaryProps> = ({
  portfolio,
  isConnected,
  lastUpdate
}) => {
  if (!portfolio) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/4 mb-4"></div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-20 bg-gray-200 dark:bg-gray-700 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  const cards = [
    {
      title: 'Portfolio Value',
      value: PnLCalculator.formatCurrency(portfolio.portfolio_value),
      icon: DollarSign,
      color: 'text-blue-600 dark:text-blue-400',
      bgColor: 'bg-blue-50 dark:bg-blue-900/20'
    },
    {
      title: 'Total P&L',
      value: PnLCalculator.formatCurrency(portfolio.total_pl),
      subValue: PnLCalculator.formatPercent(portfolio.total_pl_percent),
      icon: portfolio.total_pl >= 0 ? TrendingUp : TrendingDown,
      color: PnLCalculator.getPnLColorClass(portfolio.total_pl),
      bgColor: portfolio.total_pl >= 0 ? 'bg-green-50 dark:bg-green-900/20' : 'bg-red-50 dark:bg-red-900/20'
    },
    {
      title: 'Day P&L',
      value: PnLCalculator.formatCurrency(portfolio.day_pl),
      subValue: PnLCalculator.formatPercent(portfolio.day_pl_percent),
      icon: portfolio.day_pl >= 0 ? TrendingUp : TrendingDown,
      color: PnLCalculator.getPnLColorClass(portfolio.day_pl),
      bgColor: portfolio.day_pl >= 0 ? 'bg-green-50 dark:bg-green-900/20' : 'bg-red-50 dark:bg-red-900/20'
    },
    {
      title: 'Buying Power',
      value: PnLCalculator.formatCurrency(portfolio.buying_power),
      icon: Wallet,
      color: 'text-purple-600 dark:text-purple-400',
      bgColor: 'bg-purple-50 dark:bg-purple-900/20'
    }
  ];

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
          Portfolio Summary
        </h2>
        <div className="flex items-center space-x-2">
          <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
          <span className="text-sm text-gray-500 dark:text-gray-400">
            {isConnected ? 'Live' : 'Disconnected'}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
        {cards.map((card, index) => (
          <div
            key={index}
            className={`${card.bgColor} rounded-lg p-4 border border-gray-200 dark:border-gray-700`}
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-300">
                  {card.title}
                </p>
                <p className={`text-lg font-semibold ${card.color}`}>
                  {card.value}
                </p>
                {card.subValue && (
                  <p className={`text-sm ${card.color}`}>
                    {card.subValue}
                  </p>
                )}
              </div>
              <div className={`${card.color}`}>
                <card.icon size={24} />
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
        <div>
          <p className="text-gray-500 dark:text-gray-400">Cash</p>
          <p className="font-medium text-gray-900 dark:text-white">
            {PnLCalculator.formatCurrency(portfolio.cash)}
          </p>
        </div>
        <div>
          <p className="text-gray-500 dark:text-gray-400">Equity</p>
          <p className="font-medium text-gray-900 dark:text-white">
            {PnLCalculator.formatCurrency(portfolio.equity)}
          </p>
        </div>
        <div>
          <p className="text-gray-500 dark:text-gray-400">Day Trading BP</p>
          <p className="font-medium text-gray-900 dark:text-white">
            {PnLCalculator.formatCurrency(portfolio.daytrading_buying_power)}
          </p>
        </div>
        <div>
          <p className="text-gray-500 dark:text-gray-400">Last Update</p>
          <p className="font-medium text-gray-900 dark:text-white">
            {lastUpdate ? new Date(lastUpdate).toLocaleTimeString() : 'Never'}
          </p>
        </div>
      </div>
    </div>
  );
};