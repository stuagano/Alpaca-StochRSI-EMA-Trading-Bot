-- Trading Bot Database Initialization Script
-- This script sets up the initial database schema and indexes

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Create schemas
CREATE SCHEMA IF NOT EXISTS trading;
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE SCHEMA IF NOT EXISTS monitoring;

-- Set search path
SET search_path TO trading, public;

-- =====================================================
-- TRADING TABLES
-- =====================================================

-- Accounts table
CREATE TABLE IF NOT EXISTS accounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    account_id VARCHAR(50) UNIQUE NOT NULL,
    account_type VARCHAR(20) NOT NULL DEFAULT 'paper',
    buying_power DECIMAL(15,2),
    cash DECIMAL(15,2),
    portfolio_value DECIMAL(15,2),
    day_trade_buying_power DECIMAL(15,2),
    max_day_trade_buying_power DECIMAL(15,2),
    status VARCHAR(20),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Positions table
CREATE TABLE IF NOT EXISTS positions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    account_id VARCHAR(50) NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    qty DECIMAL(15,6) NOT NULL,
    side VARCHAR(10) NOT NULL, -- 'long' or 'short'
    market_value DECIMAL(15,2),
    cost_basis DECIMAL(15,2),
    unrealized_pl DECIMAL(15,2),
    unrealized_plpc DECIMAL(8,4),
    avg_entry_price DECIMAL(15,4),
    current_price DECIMAL(15,4),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(account_id, symbol)
);

-- Orders table
CREATE TABLE IF NOT EXISTS orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id VARCHAR(50) UNIQUE NOT NULL,
    account_id VARCHAR(50) NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    qty DECIMAL(15,6) NOT NULL,
    filled_qty DECIMAL(15,6) DEFAULT 0,
    side VARCHAR(10) NOT NULL, -- 'buy' or 'sell'
    order_type VARCHAR(20) NOT NULL,
    time_in_force VARCHAR(10) NOT NULL,
    limit_price DECIMAL(15,4),
    stop_price DECIMAL(15,4),
    status VARCHAR(20) NOT NULL,
    filled_avg_price DECIMAL(15,4),
    submitted_at TIMESTAMP WITH TIME ZONE,
    filled_at TIMESTAMP WITH TIME ZONE,
    expired_at TIMESTAMP WITH TIME ZONE,
    canceled_at TIMESTAMP WITH TIME ZONE,
    failed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Market data (OHLCV) table
CREATE TABLE IF NOT EXISTS market_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol VARCHAR(10) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    open_price DECIMAL(15,4) NOT NULL,
    high_price DECIMAL(15,4) NOT NULL,
    low_price DECIMAL(15,4) NOT NULL,
    close_price DECIMAL(15,4) NOT NULL,
    volume BIGINT NOT NULL,
    trade_count INTEGER,
    vwap DECIMAL(15,4),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(symbol, timeframe, timestamp)
);

-- Trading signals table
CREATE TABLE IF NOT EXISTS trading_signals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol VARCHAR(10) NOT NULL,
    strategy VARCHAR(50) NOT NULL,
    signal_type VARCHAR(20) NOT NULL, -- 'buy', 'sell', 'hold'
    strength DECIMAL(5,2), -- Signal strength 0-100
    indicators JSONB,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Strategy performance table
CREATE TABLE IF NOT EXISTS strategy_performance (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    strategy_name VARCHAR(50) NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    total_return DECIMAL(15,4) DEFAULT 0,
    max_drawdown DECIMAL(15,4) DEFAULT 0,
    sharpe_ratio DECIMAL(8,4),
    win_rate DECIMAL(5,2),
    avg_trade_return DECIMAL(15,4),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- ANALYTICS TABLES
-- =====================================================

-- Risk metrics table
CREATE TABLE IF NOT EXISTS analytics.risk_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol VARCHAR(10) NOT NULL,
    portfolio_weight DECIMAL(5,2),
    var_95 DECIMAL(15,4), -- Value at Risk 95%
    expected_shortfall DECIMAL(15,4),
    beta DECIMAL(8,4),
    volatility DECIMAL(8,4),
    correlation_matrix JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Performance analytics table
CREATE TABLE IF NOT EXISTS analytics.performance_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_name VARCHAR(50) NOT NULL,
    metric_value DECIMAL(15,4),
    metric_metadata JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- MONITORING TABLES
-- =====================================================

-- System health table
CREATE TABLE IF NOT EXISTS monitoring.system_health (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    component VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    response_time_ms INTEGER,
    error_count INTEGER DEFAULT 0,
    metadata JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Error logs table
CREATE TABLE IF NOT EXISTS monitoring.error_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    component VARCHAR(50) NOT NULL,
    error_type VARCHAR(50),
    error_message TEXT,
    stack_trace TEXT,
    context JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- INDEXES
-- =====================================================

-- Market data indexes
CREATE INDEX IF NOT EXISTS idx_market_data_symbol_timeframe ON market_data(symbol, timeframe);
CREATE INDEX IF NOT EXISTS idx_market_data_timestamp ON market_data(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_market_data_symbol_timestamp ON market_data(symbol, timestamp DESC);

-- Orders indexes
CREATE INDEX IF NOT EXISTS idx_orders_account_id ON orders(account_id);
CREATE INDEX IF NOT EXISTS idx_orders_symbol ON orders(symbol);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_submitted_at ON orders(submitted_at DESC);

-- Positions indexes
CREATE INDEX IF NOT EXISTS idx_positions_account_id ON positions(account_id);
CREATE INDEX IF NOT EXISTS idx_positions_symbol ON positions(symbol);

-- Trading signals indexes
CREATE INDEX IF NOT EXISTS idx_trading_signals_symbol ON trading_signals(symbol);
CREATE INDEX IF NOT EXISTS idx_trading_signals_timestamp ON trading_signals(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_trading_signals_processed ON trading_signals(processed);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_strategy_performance_strategy ON strategy_performance(strategy_name);
CREATE INDEX IF NOT EXISTS idx_strategy_performance_symbol ON strategy_performance(symbol);
CREATE INDEX IF NOT EXISTS idx_strategy_performance_period ON strategy_performance(period_start, period_end);

-- Analytics indexes
CREATE INDEX IF NOT EXISTS idx_risk_metrics_symbol ON analytics.risk_metrics(symbol);
CREATE INDEX IF NOT EXISTS idx_risk_metrics_timestamp ON analytics.risk_metrics(timestamp DESC);

-- Monitoring indexes
CREATE INDEX IF NOT EXISTS idx_system_health_component ON monitoring.system_health(component);
CREATE INDEX IF NOT EXISTS idx_system_health_timestamp ON monitoring.system_health(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_error_logs_component ON monitoring.error_logs(component);
CREATE INDEX IF NOT EXISTS idx_error_logs_timestamp ON monitoring.error_logs(timestamp DESC);

-- =====================================================
-- TRIGGERS FOR UPDATED_AT
-- =====================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply triggers to relevant tables
CREATE TRIGGER update_accounts_updated_at BEFORE UPDATE ON accounts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_positions_updated_at BEFORE UPDATE ON positions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_orders_updated_at BEFORE UPDATE ON orders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- INITIAL DATA
-- =====================================================

-- Insert default system health record
INSERT INTO monitoring.system_health (component, status, response_time_ms, metadata)
VALUES ('database', 'healthy', 0, '{"initialization": true}')
ON CONFLICT DO NOTHING;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA trading TO tradingbot;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA analytics TO tradingbot;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA monitoring TO tradingbot;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA trading TO tradingbot;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA analytics TO tradingbot;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA monitoring TO tradingbot;