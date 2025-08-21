import { Position, PortfolioSnapshot } from '../types/position';

export class PnLCalculator {
  /**
   * Calculate unrealized P&L for a position
   */
  static calculateUnrealizedPnL(position: Position): number {
    const marketValue = position.current_price * Math.abs(position.qty);
    const costBasis = position.avg_entry_price * Math.abs(position.qty);
    
    if (position.side === 'long') {
      return marketValue - costBasis;
    } else {
      return costBasis - marketValue;
    }
  }

  /**
   * Calculate unrealized P&L percentage
   */
  static calculateUnrealizedPnLPercent(position: Position): number {
    const costBasis = position.avg_entry_price * Math.abs(position.qty);
    if (costBasis === 0) return 0;
    
    const unrealizedPnL = this.calculateUnrealizedPnL(position);
    return (unrealizedPnL / costBasis) * 100;
  }

  /**
   * Calculate daily change for a position
   */
  static calculateDayChange(position: Position): { amount: number; percent: number } {
    const currentValue = position.current_price * Math.abs(position.qty);
    const previousValue = position.lastday_price * Math.abs(position.qty);
    
    const amount = currentValue - previousValue;
    const percent = previousValue !== 0 ? (amount / previousValue) * 100 : 0;
    
    return { amount, percent };
  }

  /**
   * Calculate portfolio totals
   */
  static calculatePortfolioTotals(positions: Position[]): {
    totalValue: number;
    totalUnrealizedPnL: number;
    totalDayChange: number;
    totalDayChangePercent: number;
  } {
    const totals = positions.reduce(
      (acc, position) => {
        const marketValue = position.current_price * Math.abs(position.qty);
        const unrealizedPnL = this.calculateUnrealizedPnL(position);
        const dayChange = this.calculateDayChange(position);
        
        acc.totalValue += marketValue;
        acc.totalUnrealizedPnL += unrealizedPnL;
        acc.totalDayChange += dayChange.amount;
        
        return acc;
      },
      { totalValue: 0, totalUnrealizedPnL: 0, totalDayChange: 0, totalDayChangePercent: 0 }
    );

    // Calculate overall day change percentage
    const previousValue = totals.totalValue - totals.totalDayChange;
    totals.totalDayChangePercent = previousValue !== 0 ? (totals.totalDayChange / previousValue) * 100 : 0;

    return totals;
  }

  /**
   * Format currency value
   */
  static formatCurrency(value: number, decimals: number = 2): string {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    }).format(value);
  }

  /**
   * Format percentage value
   */
  static formatPercent(value: number, decimals: number = 2): string {
    return `${value >= 0 ? '+' : ''}${value.toFixed(decimals)}%`;
  }

  /**
   * Get color class for P&L values
   */
  static getPnLColorClass(value: number): string {
    if (value > 0) return 'text-green-600 dark:text-green-400';
    if (value < 0) return 'text-red-600 dark:text-red-400';
    return 'text-gray-600 dark:text-gray-400';
  }
}