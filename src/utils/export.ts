import { Position, PortfolioSnapshot, ExportData } from '../types/position';
import { PnLCalculator } from './calculations';

export class ExportManager {
  /**
   * Export positions and portfolio data to CSV
   */
  static exportToCSV(data: ExportData): void {
    const csvContent = this.generateCSVContent(data);
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    
    if (link.download !== undefined) {
      const url = URL.createObjectURL(blob);
      link.setAttribute('href', url);
      link.setAttribute('download', `positions_${data.exportDate}.csv`);
      link.style.visibility = 'hidden';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  }

  /**
   * Generate CSV content from positions data
   */
  private static generateCSVContent(data: ExportData): string {
    const headers = [
      'Symbol',
      'Side',
      'Quantity',
      'Avg Entry Price',
      'Current Price',
      'Market Value',
      'Cost Basis',
      'Unrealized P&L',
      'Unrealized P&L %',
      'Day Change',
      'Day Change %',
      'Asset Class',
      'Exchange'
    ];

    const rows = data.positions.map(position => {
      const dayChange = PnLCalculator.calculateDayChange(position);
      const costBasis = position.avg_entry_price * Math.abs(position.qty);
      
      return [
        position.symbol,
        position.side,
        position.qty.toString(),
        position.avg_entry_price.toFixed(4),
        position.current_price.toFixed(4),
        position.market_value.toFixed(2),
        costBasis.toFixed(2),
        position.unrealized_pl.toFixed(2),
        position.unrealized_plpc.toFixed(2),
        dayChange.amount.toFixed(2),
        dayChange.percent.toFixed(2),
        position.asset_class,
        position.exchange
      ];
    });

    // Add portfolio summary at the end
    const portfolioRows = [
      [''],
      ['PORTFOLIO SUMMARY'],
      ['Total Portfolio Value', '', '', '', '', data.portfolio.portfolio_value.toFixed(2)],
      ['Total Equity', '', '', '', '', data.portfolio.equity.toFixed(2)],
      ['Cash', '', '', '', '', data.portfolio.cash.toFixed(2)],
      ['Total P&L', '', '', '', '', data.portfolio.total_pl.toFixed(2)],
      ['Total P&L %', '', '', '', '', data.portfolio.total_pl_percent.toFixed(2)],
      ['Day P&L', '', '', '', '', data.portfolio.day_pl.toFixed(2)],
      ['Day P&L %', '', '', '', '', data.portfolio.day_pl_percent.toFixed(2)],
      ['Buying Power', '', '', '', '', data.portfolio.buying_power.toFixed(2)],
      ['Export Date', '', '', '', '', data.exportDate]
    ];

    const allRows = [headers, ...rows, ...portfolioRows];
    return allRows.map(row => row.map(cell => `"${cell}"`).join(',')).join('\n');
  }

  /**
   * Export to JSON format
   */
  static exportToJSON(data: ExportData): void {
    const jsonContent = JSON.stringify(data, null, 2);
    const blob = new Blob([jsonContent], { type: 'application/json;charset=utf-8;' });
    const link = document.createElement('a');
    
    if (link.download !== undefined) {
      const url = URL.createObjectURL(blob);
      link.setAttribute('href', url);
      link.setAttribute('download', `positions_${data.exportDate}.json`);
      link.style.visibility = 'hidden';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  }
}