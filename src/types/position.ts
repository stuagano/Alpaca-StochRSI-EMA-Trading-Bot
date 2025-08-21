export interface Position {
  symbol: string;
  side: 'long' | 'short';
  qty: number;
  market_value: number;
  cost_basis: number;
  unrealized_pl: number;
  unrealized_plpc: number;
  current_price: number;
  lastday_price: number;
  change_today: number;
  avg_entry_price: number;
  asset_class: 'us_equity' | 'crypto';
  asset_id: string;
  exchange: string;
}

export interface PortfolioSnapshot {
  portfolio_value: number;
  equity: number;
  last_equity: number;
  total_pl: number;
  total_pl_percent: number;
  day_pl: number;
  day_pl_percent: number;
  buying_power: number;
  regt_buying_power: number;
  daytrading_buying_power: number;
  cash: number;
  timestamp: string;
}

export interface PositionUpdate {
  type: 'position_update' | 'portfolio_update';
  data: Position | PortfolioSnapshot;
  timestamp: string;
}

export interface SortConfig {
  key: keyof Position | 'none';
  direction: 'asc' | 'desc';
}

export interface ExportData {
  positions: Position[];
  portfolio: PortfolioSnapshot;
  exportDate: string;
}