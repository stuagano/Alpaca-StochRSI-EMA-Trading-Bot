-- Trading Bot Seed Data Script
-- This script populates the database with initial development data

SET search_path TO trading, public;

-- =====================================================
-- DEVELOPMENT SEED DATA
-- =====================================================

-- Insert sample market data for popular stocks
INSERT INTO market_data (symbol, timeframe, timestamp, open_price, high_price, low_price, close_price, volume, trade_count, vwap)
VALUES 
    -- AAPL sample data
    ('AAPL', '1Min', NOW() - INTERVAL '60 minutes', 175.50, 176.25, 175.30, 176.00, 125000, 890, 175.85),
    ('AAPL', '1Min', NOW() - INTERVAL '59 minutes', 176.00, 176.80, 175.90, 176.70, 135000, 920, 176.35),
    ('AAPL', '1Min', NOW() - INTERVAL '58 minutes', 176.70, 177.20, 176.40, 177.10, 140000, 950, 176.85),
    ('AAPL', '1Min', NOW() - INTERVAL '57 minutes', 177.10, 177.50, 176.80, 177.25, 130000, 880, 177.15),
    ('AAPL', '1Min', NOW() - INTERVAL '56 minutes', 177.25, 177.90, 177.00, 177.60, 155000, 1020, 177.45),
    
    -- MSFT sample data
    ('MSFT', '1Min', NOW() - INTERVAL '60 minutes', 340.25, 341.50, 339.90, 341.20, 85000, 650, 340.80),
    ('MSFT', '1Min', NOW() - INTERVAL '59 minutes', 341.20, 342.10, 340.80, 341.85, 90000, 680, 341.50),
    ('MSFT', '1Min', NOW() - INTERVAL '58 minutes', 341.85, 342.75, 341.60, 342.40, 95000, 710, 342.15),
    ('MSFT', '1Min', NOW() - INTERVAL '57 minutes', 342.40, 343.20, 342.10, 342.90, 88000, 690, 342.65),
    ('MSFT', '1Min', NOW() - INTERVAL '56 minutes', 342.90, 343.80, 342.60, 343.50, 105000, 750, 343.20),
    
    -- GOOGL sample data
    ('GOOGL', '1Min', NOW() - INTERVAL '60 minutes', 138.75, 139.25, 138.50, 139.10, 45000, 320, 138.90),
    ('GOOGL', '1Min', NOW() - INTERVAL '59 minutes', 139.10, 139.80, 138.95, 139.65, 48000, 340, 139.38),
    ('GOOGL', '1Min', NOW() - INTERVAL '58 minutes', 139.65, 140.20, 139.40, 140.05, 52000, 370, 139.83),
    ('GOOGL', '1Min', NOW() - INTERVAL '57 minutes', 140.05, 140.60, 139.90, 140.35, 49000, 350, 140.23),
    ('GOOGL', '1Min', NOW() - INTERVAL '56 minutes', 140.35, 141.00, 140.10, 140.75, 55000, 390, 140.55),
    
    -- TSLA sample data
    ('TSLA', '1Min', NOW() - INTERVAL '60 minutes', 245.80, 247.20, 245.30, 246.90, 180000, 1250, 246.55),
    ('TSLA', '1Min', NOW() - INTERVAL '59 minutes', 246.90, 248.50, 246.60, 248.20, 195000, 1340, 247.80),
    ('TSLA', '1Min', NOW() - INTERVAL '58 minutes', 248.20, 249.10, 247.80, 248.75, 210000, 1420, 248.46),
    ('TSLA', '1Min', NOW() - INTERVAL '57 minutes', 248.75, 249.90, 248.40, 249.60, 205000, 1380, 249.16),
    ('TSLA', '1Min', NOW() - INTERVAL '56 minutes', 249.60, 250.80, 249.30, 250.45, 225000, 1500, 250.04),
    
    -- NVDA sample data
    ('NVDA', '1Min', NOW() - INTERVAL '60 minutes', 485.20, 487.80, 484.90, 487.30, 220000, 1600, 486.55),
    ('NVDA', '1Min', NOW() - INTERVAL '59 minutes', 487.30, 489.50, 486.80, 489.10, 240000, 1750, 488.43),
    ('NVDA', '1Min', NOW() - INTERVAL '58 minutes', 489.10, 491.20, 488.70, 490.85, 260000, 1850, 489.96),
    ('NVDA', '1Min', NOW() - INTERVAL '57 minutes', 490.85, 492.60, 490.40, 492.25, 255000, 1820, 491.53),
    ('NVDA', '1Min', NOW() - INTERVAL '56 minutes', 492.25, 494.10, 491.90, 493.75, 275000, 1950, 493.00)
ON CONFLICT (symbol, timeframe, timestamp) DO NOTHING;

-- Insert sample trading signals
INSERT INTO trading_signals (symbol, strategy, signal_type, strength, indicators, timestamp, processed)
VALUES 
    ('AAPL', 'StochRSI', 'buy', 85.5, '{"stochRSI_K": 25.4, "stochRSI_D": 18.7, "RSI": 35.2, "EMA": 175.80}', NOW() - INTERVAL '10 minutes', true),
    ('MSFT', 'StochRSI', 'hold', 45.2, '{"stochRSI_K": 55.8, "stochRSI_D": 52.3, "RSI": 58.7, "EMA": 341.50}', NOW() - INTERVAL '8 minutes', true),
    ('GOOGL', 'StochRSI', 'buy', 78.9, '{"stochRSI_K": 22.1, "stochRSI_D": 19.5, "RSI": 33.8, "EMA": 139.25}', NOW() - INTERVAL '5 minutes', false),
    ('TSLA', 'StochRSI', 'sell', 92.3, '{"stochRSI_K": 88.7, "stochRSI_D": 85.4, "RSI": 78.9, "EMA": 248.90}', NOW() - INTERVAL '3 minutes', false),
    ('NVDA', 'StochRSI', 'buy', 82.1, '{"stochRSI_K": 19.8, "stochRSI_D": 16.2, "RSI": 31.5, "EMA": 488.75}', NOW() - INTERVAL '1 minute', false)
ON CONFLICT DO NOTHING;

-- Insert sample account data
INSERT INTO accounts (account_id, account_type, buying_power, cash, portfolio_value, day_trade_buying_power, max_day_trade_buying_power, status)
VALUES 
    ('paper_account_123', 'paper', 100000.00, 50000.00, 150000.00, 200000.00, 200000.00, 'ACTIVE')
ON CONFLICT (account_id) DO UPDATE SET
    buying_power = EXCLUDED.buying_power,
    cash = EXCLUDED.cash,
    portfolio_value = EXCLUDED.portfolio_value,
    updated_at = NOW();

-- Insert sample positions
INSERT INTO positions (account_id, symbol, qty, side, market_value, cost_basis, unrealized_pl, unrealized_plpc, avg_entry_price, current_price)
VALUES 
    ('paper_account_123', 'AAPL', 50.000000, 'long', 8800.00, 8500.00, 300.00, 3.53, 170.00, 176.00),
    ('paper_account_123', 'MSFT', 25.000000, 'long', 8587.50, 8250.00, 337.50, 4.09, 330.00, 343.50),
    ('paper_account_123', 'GOOGL', 75.000000, 'long', 10556.25, 10125.00, 431.25, 4.26, 135.00, 140.75),
    ('paper_account_123', 'TSLA', 40.000000, 'long', 10018.00, 9800.00, 218.00, 2.22, 245.00, 250.45),
    ('paper_account_123', 'NVDA', 20.000000, 'long', 9875.00, 9600.00, 275.00, 2.86, 480.00, 493.75)
ON CONFLICT (account_id, symbol) DO UPDATE SET
    qty = EXCLUDED.qty,
    market_value = EXCLUDED.market_value,
    cost_basis = EXCLUDED.cost_basis,
    unrealized_pl = EXCLUDED.unrealized_pl,
    unrealized_plpc = EXCLUDED.unrealized_plpc,
    current_price = EXCLUDED.current_price,
    updated_at = NOW();

-- Insert sample orders
INSERT INTO orders (order_id, account_id, symbol, qty, filled_qty, side, order_type, time_in_force, limit_price, status, filled_avg_price, submitted_at, filled_at)
VALUES 
    ('order_001', 'paper_account_123', 'AAPL', 10.000000, 10.000000, 'buy', 'limit', 'gtc', 175.00, 'filled', 174.85, NOW() - INTERVAL '2 hours', NOW() - INTERVAL '2 hours'),
    ('order_002', 'paper_account_123', 'MSFT', 5.000000, 5.000000, 'buy', 'market', 'day', null, 'filled', 342.50, NOW() - INTERVAL '1 hour', NOW() - INTERVAL '1 hour'),
    ('order_003', 'paper_account_123', 'GOOGL', 15.000000, 0.000000, 'buy', 'limit', 'gtc', 138.00, 'pending_new', null, NOW() - INTERVAL '30 minutes', null),
    ('order_004', 'paper_account_123', 'TSLA', 8.000000, 8.000000, 'sell', 'limit', 'day', 250.00, 'filled', 249.75, NOW() - INTERVAL '15 minutes', NOW() - INTERVAL '15 minutes')
ON CONFLICT (order_id) DO NOTHING;

-- Insert sample strategy performance data
INSERT INTO strategy_performance (strategy_name, symbol, period_start, period_end, total_trades, winning_trades, losing_trades, total_return, max_drawdown, sharpe_ratio, win_rate, avg_trade_return)
VALUES 
    ('StochRSI', 'AAPL', NOW() - INTERVAL '30 days', NOW(), 25, 18, 7, 12.5, -3.2, 1.45, 72.00, 0.50),
    ('StochRSI', 'MSFT', NOW() - INTERVAL '30 days', NOW(), 22, 15, 7, 10.8, -2.8, 1.38, 68.18, 0.49),
    ('StochRSI', 'GOOGL', NOW() - INTERVAL '30 days', NOW(), 20, 14, 6, 15.2, -4.1, 1.52, 70.00, 0.76),
    ('StochRSI', 'TSLA', NOW() - INTERVAL '30 days', NOW(), 35, 23, 12, 18.7, -6.5, 1.28, 65.71, 0.53),
    ('StochRSI', 'NVDA', NOW() - INTERVAL '30 days', NOW(), 28, 20, 8, 22.3, -5.8, 1.67, 71.43, 0.80)
ON CONFLICT DO NOTHING;

-- =====================================================
-- ANALYTICS SEED DATA
-- =====================================================

-- Insert sample risk metrics
INSERT INTO analytics.risk_metrics (symbol, portfolio_weight, var_95, expected_shortfall, beta, volatility, correlation_matrix)
VALUES 
    ('AAPL', 18.50, -1250.50, -1650.75, 1.12, 0.285, '{"MSFT": 0.72, "GOOGL": 0.68, "TSLA": 0.45, "NVDA": 0.58}'),
    ('MSFT', 18.10, -1180.25, -1580.40, 0.98, 0.265, '{"AAPL": 0.72, "GOOGL": 0.75, "TSLA": 0.42, "NVDA": 0.65}'),
    ('GOOGL', 22.20, -1420.80, -1890.60, 1.05, 0.295, '{"AAPL": 0.68, "MSFT": 0.75, "TSLA": 0.48, "NVDA": 0.62}'),
    ('TSLA', 21.10, -2180.40, -2890.55, 1.65, 0.485, '{"AAPL": 0.45, "MSFT": 0.42, "GOOGL": 0.48, "NVDA": 0.52}'),
    ('NVDA', 20.10, -1950.30, -2580.90, 1.45, 0.425, '{"AAPL": 0.58, "MSFT": 0.65, "GOOGL": 0.62, "TSLA": 0.52}')
ON CONFLICT DO NOTHING;

-- Insert sample performance metrics
INSERT INTO analytics.performance_metrics (metric_name, metric_value, metric_metadata)
VALUES 
    ('portfolio_return_1d', 2.34, '{"period": "1day", "benchmark": "SPY", "outperformance": 0.8}'),
    ('portfolio_return_7d', 8.76, '{"period": "7days", "benchmark": "SPY", "outperformance": 2.1}'),
    ('portfolio_return_30d', 15.42, '{"period": "30days", "benchmark": "SPY", "outperformance": 3.8}'),
    ('sharpe_ratio', 1.48, '{"period": "30days", "risk_free_rate": 0.045}'),
    ('max_drawdown', -4.85, '{"period": "30days", "drawdown_duration_days": 5}'),
    ('volatility', 0.31, '{"period": "30days", "annualized": true}'),
    ('beta', 1.18, '{"benchmark": "SPY", "period": "30days"}'),
    ('alpha', 0.045, '{"benchmark": "SPY", "period": "30days", "annualized": true}')
ON CONFLICT DO NOTHING;

-- =====================================================
-- MONITORING SEED DATA
-- =====================================================

-- Insert sample system health data
INSERT INTO monitoring.system_health (component, status, response_time_ms, error_count, metadata)
VALUES 
    ('database', 'healthy', 25, 0, '{"connections": 5, "pool_size": 20}'),
    ('redis_cache', 'healthy', 8, 0, '{"memory_usage": "45%", "hit_rate": "87%"}'),
    ('alpaca_api', 'healthy', 150, 0, '{"rate_limit_remaining": 180, "last_request": "2024-01-01T10:30:00Z"}'),
    ('flask_app', 'healthy', 35, 0, '{"active_connections": 12, "memory_usage": "320MB"}'),
    ('websocket_server', 'healthy', 45, 0, '{"active_connections": 3, "messages_per_minute": 120}')
ON CONFLICT DO NOTHING;

-- Success message
INSERT INTO monitoring.system_health (component, status, response_time_ms, metadata)
VALUES ('seed_data', 'completed', 0, '{"message": "Development seed data loaded successfully", "timestamp": "' || NOW() || '"}');

-- Log completion
DO $$
BEGIN
    RAISE NOTICE 'Seed data script completed successfully at %', NOW();
END $$;