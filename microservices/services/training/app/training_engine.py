"""
Trading Training Engine
Collaborative learning system for developing and testing trading strategies
"""

import sqlite3
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import yfinance as yf
from dataclasses import dataclass
import ta
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TradeSignal:
    """Represents a trading signal with reasoning"""
    action: str  # 'buy', 'sell', 'hold'
    confidence: float  # 0.0 to 1.0
    reasoning: str
    price: float
    timestamp: datetime
    indicators: Dict[str, float]

@dataclass
class Trade:
    """Represents a completed trade"""
    entry_time: datetime
    exit_time: Optional[datetime]
    entry_price: float
    exit_price: Optional[float]
    quantity: int
    trade_type: str  # 'long', 'short'
    pnl: float = 0.0
    pnl_percent: float = 0.0
    exit_reason: str = ''

class TrainingDatabase:
    """Handles all database operations for the training system"""
    
    def __init__(self, db_path: str = "training/database/trading_training.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database with schema"""
        # Create directory if it doesn't exist
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
            
        conn = sqlite3.connect(self.db_path)
        
        # Always use basic schema (since the full schema.sql has CREATE TABLE without IF NOT EXISTS)
        self._create_basic_schema(conn)
            
        conn.commit()
        conn.close()
        logger.info(f"Database initialized at {self.db_path}")
    
    def _create_basic_schema(self, conn):
        """Create basic database schema if schema.sql is not found"""
        basic_schema = '''
        CREATE TABLE IF NOT EXISTS historical_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol VARCHAR(10) NOT NULL,
            timestamp DATETIME NOT NULL,
            open DECIMAL(10,4) NOT NULL,
            high DECIMAL(10,4) NOT NULL,
            low DECIMAL(10,4) NOT NULL,
            close DECIMAL(10,4) NOT NULL,
            volume INTEGER NOT NULL,
            timeframe VARCHAR(10) NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(symbol, timestamp, timeframe)
        );
        
        CREATE TABLE IF NOT EXISTS strategies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100) NOT NULL UNIQUE,
            description TEXT,
            parameters JSON,
            type VARCHAR(50),
            complexity_level INTEGER DEFAULT 1,
            created_by VARCHAR(50),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            active BOOLEAN DEFAULT 1
        );
        
        CREATE TABLE IF NOT EXISTS backtests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            strategy_id INTEGER NOT NULL,
            name VARCHAR(100) NOT NULL,
            symbol VARCHAR(10) NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            initial_capital DECIMAL(12,2) DEFAULT 10000.00,
            total_trades INTEGER DEFAULT 0,
            winning_trades INTEGER DEFAULT 0,
            total_return DECIMAL(8,4) DEFAULT 0.0,
            win_rate DECIMAL(6,4) DEFAULT 0.0,
            sharpe_ratio DECIMAL(6,4) DEFAULT 0.0,
            max_drawdown DECIMAL(8,4) DEFAULT 0.0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS backtest_trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            backtest_id INTEGER NOT NULL,
            symbol VARCHAR(10) NOT NULL,
            entry_timestamp DATETIME NOT NULL,
            exit_timestamp DATETIME,
            entry_price DECIMAL(10,4) NOT NULL,
            exit_price DECIMAL(10,4),
            quantity INTEGER NOT NULL,
            trade_type VARCHAR(10) NOT NULL,
            pnl DECIMAL(12,4) DEFAULT 0.0,
            pnl_percent DECIMAL(8,4) DEFAULT 0.0,
            exit_reason VARCHAR(50),
            human_input TEXT,
            ai_reasoning TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        
        INSERT OR IGNORE INTO strategies (name, description, type, complexity_level, created_by) VALUES
        ('stoch_rsi_ema', 'StochRSI + EMA Crossover Strategy', 'technical', 2, 'system'),
        ('bollinger_mean_reversion', 'Bollinger Bands Mean Reversion', 'technical', 1, 'system'),
        ('momentum_breakout', 'Momentum Breakout Strategy', 'technical', 3, 'system'),
        ('multi_timeframe_trend', 'Multi-Timeframe Trend Strategy', 'technical', 4, 'system');
        '''
        
        conn.executescript(basic_schema)
    
    def store_historical_data(self, symbol: str, data: pd.DataFrame, timeframe: str):
        """Store historical market data"""
        conn = sqlite3.connect(self.db_path)
        
        # Handle multi-level columns from yfinance
        df = data.copy()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
        
        for index, row in df.iterrows():
            # Convert pandas values to Python scalars
            open_price = float(row['Open']) if 'Open' in row else float(row['open'])
            high_price = float(row['High']) if 'High' in row else float(row['high'])
            low_price = float(row['Low']) if 'Low' in row else float(row['low'])
            close_price = float(row['Close']) if 'Close' in row else float(row['close'])
            volume = int(row['Volume']) if 'Volume' in row else int(row['volume'])
            
            conn.execute("""
                INSERT OR IGNORE INTO historical_data 
                (symbol, timestamp, open, high, low, close, volume, timeframe)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (symbol, str(index), open_price, high_price, low_price, close_price, volume, timeframe))
        
        conn.commit()
        conn.close()
        logger.info(f"Stored {len(data)} bars for {symbol} ({timeframe})")
    
    def get_historical_data(self, symbol: str, start_date: str, end_date: str, timeframe: str = '1d') -> pd.DataFrame:
        """Retrieve historical data from database"""
        conn = sqlite3.connect(self.db_path)
        
        query = """
            SELECT timestamp, open, high, low, close, volume
            FROM historical_data 
            WHERE symbol = ? AND timeframe = ? AND timestamp BETWEEN ? AND ?
            ORDER BY timestamp
        """
        
        df = pd.read_sql_query(query, conn, params=(symbol, timeframe, start_date, end_date))
        conn.close()
        
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        
        return df
    
    def create_backtest(self, strategy_id: int, name: str, symbol: str, 
                       start_date: str, end_date: str, initial_capital: float = 10000) -> int:
        """Create new backtest session"""
        conn = sqlite3.connect(self.db_path)
        
        cursor = conn.execute("""
            INSERT INTO backtests (strategy_id, name, symbol, start_date, end_date, initial_capital)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (strategy_id, name, symbol, start_date, end_date, initial_capital))
        
        backtest_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"Created backtest {backtest_id} for {symbol}")
        return backtest_id
    
    def store_trade(self, backtest_id: int, trade: Trade, trade_number: int, human_input: str = '', ai_reasoning: str = ''):
        """Store individual trade result"""
        conn = sqlite3.connect(self.db_path)
        
        conn.execute("""
            INSERT INTO backtest_trades 
            (backtest_id, trade_number, symbol, entry_timestamp, exit_timestamp, entry_price, exit_price,
             quantity, trade_type, status, pnl, pnl_percent, exit_reason, human_input, ai_reasoning)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (backtest_id, trade_number, 'AAPL', str(trade.entry_time), str(trade.exit_time), float(trade.entry_price),
              float(trade.exit_price), int(trade.quantity), str(trade.trade_type), 'closed', float(trade.pnl),
              float(trade.pnl_percent), str(trade.exit_reason), human_input, ai_reasoning))
        
        conn.commit()
        conn.close()
    
    def store_decision(self, session_name: str, symbol: str, timestamp: datetime,
                      current_price: float, market_data: Dict, human_decision: str,
                      human_reasoning: str, ai_decision: str, ai_reasoning: str,
                      final_action: str) -> int:
        """Store collaborative decision"""
        conn = sqlite3.connect(self.db_path)
        
        cursor = conn.execute("""
            INSERT INTO decision_sessions 
            (session_name, symbol, timestamp, current_price, market_data, human_decision,
             human_reasoning, ai_decision, ai_reasoning, final_action)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (session_name, symbol, timestamp, current_price, json.dumps(market_data),
              human_decision, human_reasoning, ai_decision, ai_reasoning, final_action))
        
        decision_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return decision_id

class StrategyEngine:
    """Implements various trading strategies with technical indicators"""
    
    def __init__(self):
        self.strategies = {
            'stoch_rsi_ema': self.stoch_rsi_ema_strategy,
            'bollinger_mean_reversion': self.bollinger_mean_reversion,
            'momentum_breakout': self.momentum_breakout,
            'multi_timeframe_trend': self.multi_timeframe_trend
        }
    
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate all technical indicators using simple implementations"""
        df = data.copy()
        
        # Handle multi-level column names from yfinance
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
        
        # Ensure we have the right column names
        expected_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        for col in expected_columns:
            if col not in df.columns:
                # Try to find similar column
                for actual_col in df.columns:
                    if col.lower() in actual_col.lower():
                        df[col] = df[actual_col]
                        break
        
        # EMA indicators using pandas
        df['EMA_9'] = df['Close'].ewm(span=9).mean()
        df['EMA_21'] = df['Close'].ewm(span=21).mean()
        df['EMA_50'] = df['Close'].ewm(span=50).mean()
        df['EMA_200'] = df['Close'].ewm(span=200).mean()
        
        # Simple RSI calculation
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # StochRSI approximation
        rsi = df['RSI']
        stoch_rsi = ((rsi - rsi.rolling(14).min()) / 
                    (rsi.rolling(14).max() - rsi.rolling(14).min())) * 100
        df['StochRSI_K'] = stoch_rsi
        df['StochRSI_D'] = stoch_rsi.rolling(3).mean()
        
        # Bollinger Bands
        bb_period = 20
        bb_std = 2
        df['BB_Middle'] = df['Close'].rolling(window=bb_period).mean()
        bb_std_dev = df['Close'].rolling(window=bb_period).std()
        df['BB_Upper'] = df['BB_Middle'] + (bb_std_dev * bb_std)
        df['BB_Lower'] = df['BB_Middle'] - (bb_std_dev * bb_std)
        
        # Simple MACD
        ema12 = df['Close'].ewm(span=12).mean()
        ema26 = df['Close'].ewm(span=26).mean()
        df['MACD'] = ema12 - ema26
        df['MACD_Signal'] = df['MACD'].ewm(span=9).mean()
        df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
        
        # Volume indicators
        df['Volume_SMA'] = df['Volume'].rolling(window=20).mean()
        
        # Simple ATR
        high_low = df['High'] - df['Low']
        high_close = np.abs(df['High'] - df['Close'].shift())
        low_close = np.abs(df['Low'] - df['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['ATR'] = ranges.rolling(14).mean()
        
        return df
    
    def stoch_rsi_ema_strategy(self, data: pd.DataFrame, params: Dict) -> List[TradeSignal]:
        """Original StochRSI + EMA strategy"""
        signals = []
        df = self.calculate_indicators(data)
        
        for i, (timestamp, row) in enumerate(df.iterrows()):
            if i < 50:  # Need enough data for indicators
                continue
            
            # Extract parameters
            stoch_oversold = params.get('rsi_oversold', 20)
            stoch_overbought = params.get('rsi_overbought', 80)
            
            # Check for buy signal
            if (row['StochRSI_K'] < stoch_oversold and 
                row['Close'] > row['EMA_21'] and 
                row['EMA_9'] > row['EMA_21']):
                
                confidence = self._calculate_confidence([
                    row['StochRSI_K'] / 100,  # Lower is better for oversold
                    (row['Close'] - row['EMA_21']) / row['Close'],  # Price above EMA
                    row['Volume'] / row['Volume_SMA'] if row['Volume_SMA'] > 0 else 1
                ])
                
                signals.append(TradeSignal(
                    action='buy',
                    confidence=confidence,
                    reasoning=f"StochRSI oversold ({row['StochRSI_K']:.1f}), price above EMA21, bullish EMA crossover",
                    price=row['Close'],
                    timestamp=timestamp,
                    indicators={
                        'stoch_k': row['StochRSI_K'],
                        'ema_9': row['EMA_9'],
                        'ema_21': row['EMA_21'],
                        'rsi': row['RSI']
                    }
                ))
            
            # Check for sell signal
            elif (row['StochRSI_K'] > stoch_overbought or 
                  row['Close'] < row['EMA_21']):
                
                confidence = self._calculate_confidence([
                    (100 - row['StochRSI_K']) / 100,  # Higher is better for overbought
                    abs(row['Close'] - row['EMA_21']) / row['Close']  # Distance from EMA
                ])
                
                signals.append(TradeSignal(
                    action='sell',
                    confidence=confidence,
                    reasoning=f"StochRSI overbought ({row['StochRSI_K']:.1f}) or price below EMA21",
                    price=row['Close'],
                    timestamp=timestamp,
                    indicators={
                        'stoch_k': row['StochRSI_K'],
                        'ema_21': row['EMA_21'],
                        'rsi': row['RSI']
                    }
                ))
        
        return signals
    
    def bollinger_mean_reversion(self, data: pd.DataFrame, params: Dict) -> List[TradeSignal]:
        """Bollinger Bands mean reversion strategy"""
        signals = []
        df = self.calculate_indicators(data)
        
        for i, (timestamp, row) in enumerate(df.iterrows()):
            if i < 20:
                continue
            
            # Buy when price touches lower band and RSI is oversold
            if (row['Close'] <= row['BB_Lower'] and 
                row['RSI'] < params.get('rsi_filter', 30)):
                
                signals.append(TradeSignal(
                    action='buy',
                    confidence=0.7,
                    reasoning=f"Price at lower Bollinger Band ({row['Close']:.2f} vs {row['BB_Lower']:.2f}), RSI oversold ({row['RSI']:.1f})",
                    price=row['Close'],
                    timestamp=timestamp,
                    indicators={'bb_lower': row['BB_Lower'], 'rsi': row['RSI']}
                ))
            
            # Sell when price touches upper band
            elif row['Close'] >= row['BB_Upper']:
                signals.append(TradeSignal(
                    action='sell',
                    confidence=0.6,
                    reasoning=f"Price at upper Bollinger Band ({row['Close']:.2f} vs {row['BB_Upper']:.2f})",
                    price=row['Close'],
                    timestamp=timestamp,
                    indicators={'bb_upper': row['BB_Upper']}
                ))
        
        return signals
    
    def momentum_breakout(self, data: pd.DataFrame, params: Dict) -> List[TradeSignal]:
        """Momentum breakout strategy"""
        signals = []
        df = self.calculate_indicators(data)
        
        # Calculate support/resistance levels
        df['Resistance'] = df['High'].rolling(window=20).max()
        df['Support'] = df['Low'].rolling(window=20).min()
        
        for i, (timestamp, row) in enumerate(df.iterrows()):
            if i < 20:
                continue
            
            breakout_pct = params.get('breakout_percentage', 2.0) / 100
            volume_threshold = params.get('volume_threshold', 1.5)
            
            # Bullish breakout
            if (row['Close'] > row['Resistance'] * (1 + breakout_pct) and
                row['Volume'] > row['Volume_SMA'] * volume_threshold):
                
                signals.append(TradeSignal(
                    action='buy',
                    confidence=0.8,
                    reasoning=f"Bullish breakout above resistance ({row['Close']:.2f} > {row['Resistance']:.2f}), high volume",
                    price=row['Close'],
                    timestamp=timestamp,
                    indicators={'resistance': row['Resistance'], 'volume_ratio': row['Volume'] / row['Volume_SMA']}
                ))
            
            # Bearish breakdown
            elif (row['Close'] < row['Support'] * (1 - breakout_pct) and
                  row['Volume'] > row['Volume_SMA'] * volume_threshold):
                
                signals.append(TradeSignal(
                    action='sell',
                    confidence=0.8,
                    reasoning=f"Bearish breakdown below support ({row['Close']:.2f} < {row['Support']:.2f}), high volume",
                    price=row['Close'],
                    timestamp=timestamp,
                    indicators={'support': row['Support'], 'volume_ratio': row['Volume'] / row['Volume_SMA']}
                ))
        
        return signals
    
    def multi_timeframe_trend(self, data: pd.DataFrame, params: Dict) -> List[TradeSignal]:
        """Multi-timeframe trend confirmation strategy"""
        signals = []
        df = self.calculate_indicators(data)
        
        for i, (timestamp, row) in enumerate(df.iterrows()):
            if i < 200:  # Need enough data for 200 EMA
                continue
            
            # All EMAs aligned for bullish trend
            if (row['EMA_9'] > row['EMA_21'] > row['EMA_50'] > row['EMA_200'] and
                row['Close'] > row['EMA_9']):
                
                signals.append(TradeSignal(
                    action='buy',
                    confidence=0.9,
                    reasoning="Strong bullish trend - all EMAs aligned, price above short-term EMA",
                    price=row['Close'],
                    timestamp=timestamp,
                    indicators={
                        'ema_9': row['EMA_9'],
                        'ema_21': row['EMA_21'],
                        'ema_50': row['EMA_50'],
                        'ema_200': row['EMA_200']
                    }
                ))
            
            # EMA alignment breaking down
            elif (row['EMA_9'] < row['EMA_21'] or row['Close'] < row['EMA_21']):
                signals.append(TradeSignal(
                    action='sell',
                    confidence=0.7,
                    reasoning="Trend weakening - EMA alignment breaking or price below EMA21",
                    price=row['Close'],
                    timestamp=timestamp,
                    indicators={'ema_9': row['EMA_9'], 'ema_21': row['EMA_21']}
                ))
        
        return signals
    
    def _calculate_confidence(self, factors: List[float]) -> float:
        """Calculate overall confidence based on multiple factors"""
        # Normalize factors and calculate weighted average
        normalized_factors = [max(0, min(1, abs(f))) for f in factors]
        return sum(normalized_factors) / len(normalized_factors)

class BacktestEngine:
    """Runs backtests and calculates performance metrics"""
    
    def __init__(self, db: TrainingDatabase):
        self.db = db
        self.strategy_engine = StrategyEngine()
    
    def run_backtest(self, strategy_name: str, symbol: str, start_date: str, end_date: str,
                    strategy_params: Dict, initial_capital: float = 10000) -> Dict:
        """Run complete backtest for a strategy"""
        
        # Get historical data
        data = self.db.get_historical_data(symbol, start_date, end_date)
        if data.empty:
            # Fetch from Yahoo Finance if not in database
            data = yf.download(symbol, start=start_date, end=end_date)
            self.db.store_historical_data(symbol, data, '1d')
        
        # Generate signals
        strategy_func = self.strategy_engine.strategies.get(strategy_name)
        if not strategy_func:
            raise ValueError(f"Unknown strategy: {strategy_name}")
        
        signals = strategy_func(data, strategy_params)
        
        # Execute trades based on signals
        trades = self._execute_signals(signals, initial_capital)
        
        # Calculate performance metrics
        performance = self._calculate_performance(trades, initial_capital)
        
        # Store results in database
        backtest_id = self.db.create_backtest(
            strategy_id=1,  # For now, use default strategy ID
            name=f"{strategy_name}_{symbol}_{start_date}",
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital
        )
        
        for trade_num, trade in enumerate(trades, 1):
            self.db.store_trade(backtest_id, trade, trade_num)
        
        performance['backtest_id'] = backtest_id
        performance['symbol'] = symbol
        performance['strategy'] = strategy_name
        performance['signals_count'] = len(signals)
        
        return performance
    
    def _execute_signals(self, signals: List[TradeSignal], initial_capital: float) -> List[Trade]:
        """Convert signals into actual trades"""
        trades = []
        position = None
        capital = initial_capital
        
        for signal in signals:
            if signal.action == 'buy' and position is None:
                # Open long position
                shares = int(capital * 0.95 / signal.price)  # Use 95% of capital
                if shares > 0:
                    position = Trade(
                        entry_time=signal.timestamp,
                        exit_time=None,
                        entry_price=signal.price,
                        exit_price=None,
                        quantity=shares,
                        trade_type='long'
                    )
                    capital -= shares * signal.price
            
            elif signal.action == 'sell' and position is not None:
                # Close position
                position.exit_time = signal.timestamp
                position.exit_price = signal.price
                position.pnl = (signal.price - position.entry_price) * position.quantity
                position.pnl_percent = (signal.price / position.entry_price - 1) * 100
                position.exit_reason = 'signal'
                
                capital += position.quantity * signal.price
                trades.append(position)
                position = None
        
        # Close any open position at the end
        if position is not None:
            position.exit_time = signals[-1].timestamp if signals else datetime.now()
            position.exit_price = signals[-1].price if signals else position.entry_price
            position.pnl = (position.exit_price - position.entry_price) * position.quantity
            position.pnl_percent = (position.exit_price / position.entry_price - 1) * 100
            position.exit_reason = 'end_of_period'
            trades.append(position)
        
        return trades
    
    def _calculate_performance(self, trades: List[Trade], initial_capital: float) -> Dict:
        """Calculate comprehensive performance metrics"""
        if not trades:
            return {
                'total_return': 0.0,
                'total_trades': 0,
                'winning_trades': 0,
                'win_rate': 0.0,
                'avg_trade_return': 0.0,
                'max_drawdown': 0.0,
                'sharpe_ratio': 0.0
            }
        
        total_pnl = sum(trade.pnl for trade in trades)
        total_return = (total_pnl / initial_capital) * 100
        winning_trades = sum(1 for trade in trades if trade.pnl > 0)
        win_rate = (winning_trades / len(trades)) * 100
        avg_trade_return = sum(trade.pnl_percent for trade in trades) / len(trades)
        
        # Calculate drawdown
        running_pnl = 0
        peak = 0
        max_drawdown = 0
        
        for trade in trades:
            running_pnl += trade.pnl
            if running_pnl > peak:
                peak = running_pnl
            drawdown = (peak - running_pnl) / initial_capital * 100
            max_drawdown = max(max_drawdown, drawdown)
        
        # Simple Sharpe ratio calculation
        returns = [trade.pnl_percent for trade in trades]
        if len(returns) > 1 and np.std(returns) > 0:
            sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252)  # Annualized
        else:
            sharpe_ratio = 0.0
        
        return {
            'total_return': total_return,
            'total_trades': len(trades),
            'winning_trades': winning_trades,
            'win_rate': win_rate,
            'avg_trade_return': avg_trade_return,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'total_pnl': total_pnl
        }

class CollaborativeLearning:
    """Handles human-AI collaborative decision making and learning"""
    
    def __init__(self, db: TrainingDatabase):
        self.db = db
        self.strategy_engine = StrategyEngine()
    
    def analyze_current_market(self, symbol: str, data: pd.DataFrame = None) -> Dict:
        """Analyze current market conditions for collaborative decision"""
        if data is None:
            # Get recent data
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=100)).strftime('%Y-%m-%d')
            data = yf.download(symbol, start=start_date, end=end_date)
        
        # Calculate indicators
        df = self.strategy_engine.calculate_indicators(data)
        latest = df.iloc[-1]
        
        # Generate AI analysis
        ai_analysis = self._generate_ai_analysis(df, latest)
        
        return {
            'symbol': symbol,
            'current_price': latest['Close'],
            'timestamp': df.index[-1],
            'indicators': {
                'rsi': latest['RSI'],
                'stoch_k': latest['StochRSI_K'],
                'stoch_d': latest['StochRSI_D'],
                'ema_9': latest['EMA_9'],
                'ema_21': latest['EMA_21'],
                'ema_50': latest['EMA_50'],
                'bb_upper': latest['BB_Upper'],
                'bb_lower': latest['BB_Lower'],
                'macd': latest['MACD'],
                'volume_ratio': latest['Volume'] / latest['Volume_SMA'] if latest['Volume_SMA'] > 0 else 1
            },
            'ai_analysis': ai_analysis,
            'trend_strength': self._assess_trend_strength(df),
            'volatility': latest['ATR'] / latest['Close'] * 100
        }
    
    def _generate_ai_analysis(self, df: pd.DataFrame, latest: pd.Series) -> Dict:
        """Generate AI analysis of current market conditions"""
        analysis = {
            'recommendation': 'hold',
            'confidence': 0.5,
            'reasoning': [],
            'risk_factors': [],
            'opportunity_factors': []
        }
        
        confidence_factors = []
        
        # RSI Analysis
        if latest['RSI'] < 30:
            analysis['reasoning'].append(f"RSI oversold at {latest['RSI']:.1f}")
            analysis['opportunity_factors'].append("Oversold conditions may present buying opportunity")
            confidence_factors.append(0.7)
        elif latest['RSI'] > 70:
            analysis['reasoning'].append(f"RSI overbought at {latest['RSI']:.1f}")
            analysis['risk_factors'].append("Overbought conditions suggest potential decline")
            confidence_factors.append(0.7)
        
        # StochRSI Analysis
        if latest['StochRSI_K'] < 20:
            analysis['reasoning'].append(f"StochRSI oversold at {latest['StochRSI_K']:.1f}")
            analysis['opportunity_factors'].append("StochRSI suggests oversold bounce potential")
            confidence_factors.append(0.6)
        elif latest['StochRSI_K'] > 80:
            analysis['reasoning'].append(f"StochRSI overbought at {latest['StochRSI_K']:.1f}")
            analysis['risk_factors'].append("StochRSI suggests overbought pullback risk")
            confidence_factors.append(0.6)
        
        # Trend Analysis
        if latest['EMA_9'] > latest['EMA_21'] > latest['EMA_50']:
            analysis['reasoning'].append("Bullish EMA alignment")
            analysis['opportunity_factors'].append("Strong uptrend confirmed by EMAs")
            analysis['recommendation'] = 'buy'
            confidence_factors.append(0.8)
        elif latest['EMA_9'] < latest['EMA_21'] < latest['EMA_50']:
            analysis['reasoning'].append("Bearish EMA alignment")
            analysis['risk_factors'].append("Downtrend confirmed by EMAs")
            analysis['recommendation'] = 'sell'
            confidence_factors.append(0.8)
        
        # Volume Analysis
        volume_ratio = latest['Volume'] / latest['Volume_SMA'] if latest['Volume_SMA'] > 0 else 1
        if volume_ratio > 1.5:
            analysis['reasoning'].append(f"High volume ({volume_ratio:.1f}x average)")
            analysis['opportunity_factors'].append("High volume supports price movement")
            confidence_factors.append(0.6)
        elif volume_ratio < 0.7:
            analysis['risk_factors'].append("Low volume may indicate weak price movement")
        
        # Calculate overall confidence
        if confidence_factors:
            analysis['confidence'] = sum(confidence_factors) / len(confidence_factors)
        
        return analysis
    
    def _assess_trend_strength(self, df: pd.DataFrame) -> float:
        """Assess overall trend strength (0-1 scale)"""
        latest = df.iloc[-1]
        
        # Calculate trend factors
        ema_trend = 0
        if latest['EMA_9'] > latest['EMA_21']:
            ema_trend += 0.25
        if latest['EMA_21'] > latest['EMA_50']:
            ema_trend += 0.25
        if latest['EMA_50'] > latest['EMA_200']:
            ema_trend += 0.25
        if latest['Close'] > latest['EMA_9']:
            ema_trend += 0.25
        
        # MACD confirmation
        macd_trend = 0.5 if latest['MACD'] > latest['MACD_Signal'] else 0
        
        # Price momentum (20-day)
        if len(df) >= 20:
            price_change = (latest['Close'] / df['Close'].iloc[-20] - 1)
            momentum_trend = min(1, max(0, (price_change + 0.1) / 0.2))  # Normalize around ±10%
        else:
            momentum_trend = 0.5
        
        return (ema_trend * 0.5 + macd_trend * 0.3 + momentum_trend * 0.2)
    
    def create_decision_session(self, session_name: str, symbol: str) -> Dict:
        """Create a new collaborative decision session"""
        market_analysis = self.analyze_current_market(symbol)
        
        return {
            'session_name': session_name,
            'market_analysis': market_analysis,
            'awaiting_human_input': True,
            'session_id': None  # Will be set when decision is stored
        }
    
    def process_human_decision(self, session_data: Dict, human_decision: str, 
                             human_reasoning: str, human_confidence: float) -> Dict:
        """Process human input and create collaborative decision"""
        market_data = session_data['market_analysis']
        ai_analysis = market_data['ai_analysis']
        
        # Store collaborative decision
        session_id = self.db.store_decision(
            session_name=session_data['session_name'],
            symbol=market_data['symbol'],
            timestamp=market_data['timestamp'],
            current_price=market_data['current_price'],
            market_data=market_data['indicators'],
            human_decision=human_decision,
            human_reasoning=human_reasoning,
            ai_decision=ai_analysis['recommendation'],
            ai_reasoning='; '.join(ai_analysis['reasoning']),
            final_action=self._resolve_decision_conflict(human_decision, ai_analysis['recommendation'], 
                                                       human_confidence, ai_analysis['confidence'])
        )
        
        return {
            'session_id': session_id,
            'human_decision': human_decision,
            'human_reasoning': human_reasoning,
            'human_confidence': human_confidence,
            'ai_decision': ai_analysis['recommendation'],
            'ai_reasoning': ai_analysis['reasoning'],
            'ai_confidence': ai_analysis['confidence'],
            'final_action': session_data.get('final_action'),
            'learning_opportunities': self._identify_learning_opportunities(
                human_decision, ai_analysis['recommendation'], market_data
            )
        }
    
    def _resolve_decision_conflict(self, human_decision: str, ai_decision: str, 
                                 human_confidence: float, ai_confidence: float) -> str:
        """Resolve conflicts between human and AI decisions"""
        if human_decision == ai_decision:
            return human_decision
        
        # If confidences are similar, default to human decision
        if abs(human_confidence - ai_confidence) < 0.2:
            return human_decision
        
        # Higher confidence wins
        return human_decision if human_confidence > ai_confidence else ai_decision
    
    def _identify_learning_opportunities(self, human_decision: str, ai_decision: str, market_data: Dict) -> List[str]:
        """Identify learning opportunities from decision differences"""
        opportunities = []
        
        if human_decision != ai_decision:
            opportunities.append("Decision conflict - opportunity to learn from different perspectives")
            opportunities.append("Compare reasoning: human intuition vs. technical indicators")
        
        # Check for extreme indicator readings
        indicators = market_data['indicators']
        if indicators['rsi'] < 20 or indicators['rsi'] > 80:
            opportunities.append("Extreme RSI reading - good case study for reversal vs. continuation")
        
        if indicators['stoch_k'] < 10 or indicators['stoch_k'] > 90:
            opportunities.append("Extreme StochRSI - analyze momentum exhaustion signals")
        
        if market_data['volatility'] > 3:
            opportunities.append("High volatility environment - test risk management strategies")
        
        return opportunities

def main():
    """Example usage of the training system"""
    # Initialize system
    db = TrainingDatabase()
    backtest_engine = BacktestEngine(db)
    collaborative_learning = CollaborativeLearning(db)
    
    # Example 1: Run a backtest
    print("Running backtest...")
    performance = backtest_engine.run_backtest(
        strategy_name='stoch_rsi_ema',
        symbol='AAPL',
        start_date='2023-01-01',
        end_date='2023-12-31',
        strategy_params={'rsi_oversold': 20, 'rsi_overbought': 80},
        initial_capital=10000
    )
    
    print(f"Backtest Results:")
    print(f"Total Return: {performance['total_return']:.2f}%")
    print(f"Win Rate: {performance['win_rate']:.1f}%")
    print(f"Sharpe Ratio: {performance['sharpe_ratio']:.2f}")
    print(f"Max Drawdown: {performance['max_drawdown']:.2f}%")
    
    # Example 2: Collaborative decision session
    print("\nStarting collaborative decision session...")
    session = collaborative_learning.create_decision_session("Morning Analysis", "AAPL")
    
    print(f"AI Recommendation: {session['market_analysis']['ai_analysis']['recommendation']}")
    print(f"AI Confidence: {session['market_analysis']['ai_analysis']['confidence']:.2f}")
    print(f"AI Reasoning: {'; '.join(session['market_analysis']['ai_analysis']['reasoning'])}")
    
    print("\n" + "="*50)
    print("Training system initialized successfully!")
    print("Database:", db.db_path)
    print("Ready for collaborative learning and backtesting.")

if __name__ == "__main__":
    main()