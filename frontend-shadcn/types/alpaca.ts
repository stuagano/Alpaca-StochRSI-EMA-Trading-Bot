// Alpaca Trading Types

export interface Account {
  id: string
  account_number: string
  status: string
  currency: string
  buying_power: string
  cash: string
  portfolio_value: string
  equity: string
  last_equity: string
  long_market_value: string
  short_market_value: string
  initial_margin: string
  maintenance_margin: string
  sma: string
  daytrade_count: number
  balance_asof: string
  created_at: string
  trade_suspended_by_user: boolean
  trading_blocked: boolean
  transfers_blocked: boolean
  account_blocked: boolean
  pattern_day_trader: boolean
  daytrading_buying_power: string
  regt_buying_power: string
  multiplier: string
}

export interface Position {
  asset_id: string
  symbol: string
  exchange: string
  asset_class: string
  avg_entry_price: string
  qty: string
  qty_available: string
  side: 'long' | 'short'
  market_value: string
  cost_basis: string
  unrealized_pl: string
  unrealized_plpc: string
  unrealized_intraday_pl: string
  unrealized_intraday_plpc: string
  current_price: string
  lastday_price: string
  change_today: string
}

export interface Order {
  id: string
  client_order_id: string
  created_at: string
  updated_at: string
  submitted_at: string
  filled_at: string | null
  expired_at: string | null
  canceled_at: string | null
  failed_at: string | null
  replaced_at: string | null
  replaced_by: string | null
  replaces: string | null
  asset_id: string
  symbol: string
  asset_class: string
  notional: string | null
  qty: string
  filled_qty: string
  filled_avg_price: string | null
  order_class: string
  order_type: string
  type: string
  side: 'buy' | 'sell'
  time_in_force: string
  limit_price: string | null
  stop_price: string | null
  status: string
  extended_hours: boolean
  legs: Order[] | null
  trail_percent: string | null
  trail_price: string | null
  hwm: string | null
}

export interface Bar {
  t: string // timestamp
  o: number // open
  h: number // high
  l: number // low
  c: number // close
  v: number // volume
  n: number // trade count
  vw: number // volume weighted average price
}

export interface Quote {
  symbol: string
  bid: number
  bid_size: number
  ask: number
  ask_size: number
  last: number
  last_size: number
  timestamp: string
}

export interface Trade {
  symbol: string
  price: number
  size: number
  timestamp: string
  conditions: string[]
}

export interface Signal {
  symbol: string
  signal_type: 'buy' | 'sell' | 'hold'
  strength: number
  indicator: 'stochRSI' | 'ema' | 'combined'
  price: number
  timestamp: string
  metadata: {
    stoch_k?: number
    stoch_d?: number
    ema_short?: number
    ema_long?: number
  }
}

export interface PortfolioHistory {
  timestamp: string[]
  equity: number[]
  profit_loss: number[]
  profit_loss_pct: number[]
  base_value: number
  timeframe: string
}

export interface RiskMetrics {
  portfolio_risk: number
  position_risks: Record<string, number>
  var_95: number
  max_position_size: number
  current_exposure: number
  risk_score?: number
  recommendations?: string[]
}