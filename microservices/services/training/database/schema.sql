-- Trading Training Database Schema
-- Comprehensive system for backtesting, learning, and strategy development

-- Historical market data storage
CREATE TABLE historical_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol VARCHAR(10) NOT NULL,
    timestamp DATETIME NOT NULL,
    open DECIMAL(10,4) NOT NULL,
    high DECIMAL(10,4) NOT NULL,
    low DECIMAL(10,4) NOT NULL,
    close DECIMAL(10,4) NOT NULL,
    volume INTEGER NOT NULL,
    timeframe VARCHAR(10) NOT NULL, -- 1m, 5m, 1h, 1d
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, timestamp, timeframe)
);

-- Trading strategies definitions
CREATE TABLE strategies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    parameters JSON, -- Strategy-specific parameters
    type VARCHAR(50), -- 'technical', 'fundamental', 'hybrid'
    complexity_level INTEGER DEFAULT 1, -- 1-5 difficulty
    created_by VARCHAR(50), -- 'human', 'ai', 'collaborative'
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    active BOOLEAN DEFAULT 1
);

-- Backtesting sessions
CREATE TABLE backtests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_id INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    initial_capital DECIMAL(12,2) DEFAULT 10000.00,
    status VARCHAR(20) DEFAULT 'pending', -- pending, running, completed, failed
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    total_return DECIMAL(8,4) DEFAULT 0.0,
    max_drawdown DECIMAL(8,4) DEFAULT 0.0,
    sharpe_ratio DECIMAL(6,4) DEFAULT 0.0,
    win_rate DECIMAL(6,4) DEFAULT 0.0,
    avg_trade_return DECIMAL(8,4) DEFAULT 0.0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    FOREIGN KEY (strategy_id) REFERENCES strategies(id)
);

-- Individual trades from backtests
CREATE TABLE backtest_trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    backtest_id INTEGER NOT NULL,
    trade_number INTEGER NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    entry_timestamp DATETIME NOT NULL,
    exit_timestamp DATETIME,
    entry_price DECIMAL(10,4) NOT NULL,
    exit_price DECIMAL(10,4),
    quantity INTEGER NOT NULL,
    trade_type VARCHAR(10) NOT NULL, -- 'long', 'short'
    status VARCHAR(20) DEFAULT 'open', -- open, closed, stopped_out
    pnl DECIMAL(12,4) DEFAULT 0.0,
    pnl_percent DECIMAL(8,4) DEFAULT 0.0,
    stop_loss DECIMAL(10,4),
    take_profit DECIMAL(10,4),
    exit_reason VARCHAR(50), -- 'signal', 'stop_loss', 'take_profit', 'timeout'
    confidence_score DECIMAL(3,2), -- 0.0-1.0 AI confidence
    human_input TEXT, -- Human reasoning/notes
    ai_reasoning TEXT, -- AI decision explanation
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (backtest_id) REFERENCES backtests(id)
);

-- Real-time collaborative decisions
CREATE TABLE decision_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_name VARCHAR(100) NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    timestamp DATETIME NOT NULL,
    current_price DECIMAL(10,4) NOT NULL,
    market_data JSON, -- Current indicators, volume, etc.
    human_decision VARCHAR(20), -- 'buy', 'sell', 'hold', 'wait'
    human_reasoning TEXT,
    human_confidence DECIMAL(3,2), -- 0.0-1.0
    ai_decision VARCHAR(20),
    ai_reasoning TEXT,
    ai_confidence DECIMAL(3,2),
    final_action VARCHAR(20), -- Collaborative decision
    outcome_tracking_id INTEGER, -- Link to actual trade result
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Learning patterns and insights
CREATE TABLE learning_insights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    insight_type VARCHAR(50), -- 'pattern', 'mistake', 'success', 'correlation'
    subject VARCHAR(100), -- What we learned about
    description TEXT NOT NULL,
    data_points JSON, -- Supporting evidence/data
    confidence_level DECIMAL(3,2),
    validated BOOLEAN DEFAULT 0,
    source VARCHAR(20), -- 'human', 'ai', 'system'
    tags JSON, -- Searchable tags
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_validated DATETIME
);

-- Performance tracking over time
CREATE TABLE performance_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    strategy_id INTEGER,
    metric_type VARCHAR(50), -- 'daily_pnl', 'win_rate', 'sharpe', etc.
    metric_value DECIMAL(12,4) NOT NULL,
    benchmark_value DECIMAL(12,4), -- S&P 500 or other benchmark
    human_contribution DECIMAL(3,2), -- How much human input helped
    ai_contribution DECIMAL(3,2), -- How much AI input helped
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (strategy_id) REFERENCES strategies(id)
);

-- Strategy evolution tracking
CREATE TABLE strategy_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_id INTEGER NOT NULL,
    version_number INTEGER NOT NULL,
    changes_description TEXT,
    parameter_changes JSON,
    performance_before JSON,
    performance_after JSON,
    change_reason VARCHAR(100), -- 'human_insight', 'ai_optimization', 'market_change'
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (strategy_id) REFERENCES strategies(id)
);

-- Educational scenarios and challenges
CREATE TABLE training_scenarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    difficulty_level INTEGER DEFAULT 1,
    scenario_type VARCHAR(50), -- 'trend_following', 'mean_reversion', 'breakout'
    market_conditions VARCHAR(100), -- 'bull_market', 'bear_market', 'sideways', 'volatile'
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    symbols JSON, -- Array of symbols to trade
    success_criteria JSON, -- What constitutes success
    learning_objectives TEXT,
    active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- User progress and achievements
CREATE TABLE user_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_type VARCHAR(20), -- 'human', 'ai'
    scenario_id INTEGER,
    strategy_id INTEGER,
    completion_status VARCHAR(20), -- 'started', 'in_progress', 'completed', 'mastered'
    score DECIMAL(8,4),
    time_spent_minutes INTEGER,
    mistakes_count INTEGER,
    insights_learned INTEGER,
    achievements JSON, -- Array of unlocked achievements
    notes TEXT,
    completed_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (scenario_id) REFERENCES training_scenarios(id),
    FOREIGN KEY (strategy_id) REFERENCES strategies(id)
);

-- Create indexes for performance
CREATE INDEX idx_historical_data_symbol_time ON historical_data(symbol, timestamp, timeframe);
CREATE INDEX idx_backtests_strategy ON backtests(strategy_id);
CREATE INDEX idx_backtest_trades_backtest ON backtest_trades(backtest_id);
CREATE INDEX idx_decision_sessions_symbol_time ON decision_sessions(symbol, timestamp);
CREATE INDEX idx_performance_metrics_date_strategy ON performance_metrics(date, strategy_id);

-- Insert some initial strategies
INSERT INTO strategies (name, description, parameters, type, complexity_level, created_by) VALUES
('StochRSI + EMA Crossover', 'Original strategy using StochRSI oversold/overbought with EMA trend confirmation', 
 '{"stoch_period": 14, "ema_fast": 9, "ema_slow": 21, "rsi_oversold": 20, "rsi_overbought": 80}', 
 'technical', 2, 'human'),
 
('Mean Reversion Bollinger', 'Buy when price touches lower Bollinger Band, sell at upper band',
 '{"bb_period": 20, "bb_std": 2, "rsi_filter": 30}',
 'technical', 1, 'collaborative'),
 
('Momentum Breakout', 'Trade breakouts above/below significant support/resistance levels',
 '{"volume_threshold": 1.5, "breakout_percentage": 2.0, "confirmation_candles": 2}',
 'technical', 3, 'ai'),
 
('Multi-Timeframe Trend', 'Confirm trend on multiple timeframes before entering',
 '{"timeframes": ["1h", "4h", "1d"], "ema_periods": [20, 50, 200]}',
 'technical', 4, 'collaborative');

-- Insert training scenarios
INSERT INTO training_scenarios (name, description, difficulty_level, scenario_type, market_conditions, start_date, end_date, symbols, success_criteria, learning_objectives) VALUES
('Bull Market Basics', 'Learn to identify and trade trending markets during bull runs', 1, 'trend_following', 'bull_market', '2023-01-01', '2023-06-30', '["AAPL", "MSFT", "GOOGL"]', '{"min_return": 15, "max_drawdown": 10}', 'Understanding trend identification, entry/exit timing, position sizing'),

('Volatile Market Mastery', 'Navigate high volatility periods with proper risk management', 3, 'volatility_trading', 'volatile', '2022-01-01', '2022-12-31', '["SPY", "QQQ", "IWM"]', '{"min_sharpe": 1.2, "max_drawdown": 15}', 'Risk management, position sizing, stop losses'),

('Bear Market Survival', 'Protect capital and find opportunities during market downturns', 4, 'defensive_trading', 'bear_market', '2008-09-01', '2009-03-31', '["SPY", "GLD", "TLT"]', '{"min_return": -5, "outperform_spy": 10}', 'Capital preservation, short selling, hedging strategies');