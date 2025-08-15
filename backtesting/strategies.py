import pandas as pd
import numpy as np
import ta
from typing import Dict, Any, Tuple, List
import logging

class BacktestingStrategies:
    """
    Collection of trading strategies adapted for backtesting
    """
    
    def __init__(self):
        self.logger = logging.getLogger('backtesting.strategies')
    
    @staticmethod
    def stochastic_rsi_strategy(data: pd.DataFrame, **params) -> pd.Series:
        """
        StochRSI-based trading strategy
        
        Parameters:
        - rsi_period: RSI calculation period (default: 14)
        - stoch_period: Stochastic calculation period (default: 14)
        - k_period: %K smoothing period (default: 3)
        - d_period: %D smoothing period (default: 3)
        - oversold_threshold: Oversold level (default: 35)
        - overbought_threshold: Overbought level (default: 80)
        """
        
        # Default parameters
        rsi_period = params.get('rsi_period', 14)
        stoch_period = params.get('stoch_period', 14)
        k_period = params.get('k_period', 3)
        d_period = params.get('d_period', 3)
        oversold_threshold = params.get('oversold_threshold', 35)
        overbought_threshold = params.get('overbought_threshold', 80)
        
        # Calculate RSI
        rsi = ta.momentum.RSIIndicator(data['close'], window=rsi_period).rsi()
        
        # Calculate Stochastic of RSI
        rsi_high = rsi.rolling(window=stoch_period).max()
        rsi_low = rsi.rolling(window=stoch_period).min()
        
        # Calculate %K
        k_percent = 100 * (rsi - rsi_low) / (rsi_high - rsi_low)
        k_percent = k_percent.rolling(window=k_period).mean()
        
        # Calculate %D
        d_percent = k_percent.rolling(window=d_period).mean()
        
        # Generate signals
        signals = pd.Series(0, index=data.index)
        
        # Buy signal: %K crosses above %D and both are below oversold threshold
        buy_condition = (
            (k_percent > d_percent) & 
            (k_percent.shift(1) <= d_percent.shift(1)) &
            (k_percent < oversold_threshold)
        )
        
        # Sell signal: %K crosses below %D and both are above overbought threshold
        sell_condition = (
            (k_percent < d_percent) & 
            (k_percent.shift(1) >= d_percent.shift(1)) &
            (k_percent > overbought_threshold)
        )
        
        signals[buy_condition] = 1
        signals[sell_condition] = -1
        
        return signals
    
    @staticmethod
    def ema_strategy(data: pd.DataFrame, **params) -> pd.Series:
        """
        EMA-based trading strategy
        
        Parameters:
        - fast_period: Fast EMA period (default: 9)
        - slow_period: Slow EMA period (default: 21)
        - signal_period: Signal line period (default: 9)
        """
        
        fast_period = params.get('fast_period', 9)
        slow_period = params.get('slow_period', 21)
        
        # Calculate EMAs
        ema_fast = ta.trend.EMAIndicator(data['close'], window=fast_period).ema_indicator()
        ema_slow = ta.trend.EMAIndicator(data['close'], window=slow_period).ema_indicator()
        
        # Generate signals
        signals = pd.Series(0, index=data.index)
        
        # Buy signal: Fast EMA crosses above Slow EMA
        buy_condition = (
            (ema_fast > ema_slow) & 
            (ema_fast.shift(1) <= ema_slow.shift(1))
        )
        
        # Sell signal: Fast EMA crosses below Slow EMA
        sell_condition = (
            (ema_fast < ema_slow) & 
            (ema_fast.shift(1) >= ema_slow.shift(1))
        )
        
        signals[buy_condition] = 1
        signals[sell_condition] = -1
        
        return signals
    
    @staticmethod
    def stochastic_strategy(data: pd.DataFrame, **params) -> pd.Series:
        """
        Traditional Stochastic oscillator strategy
        
        Parameters:
        - k_period: %K period (default: 14)
        - d_period: %D smoothing period (default: 3)
        - oversold: Oversold threshold (default: 35)
        - overbought: Overbought threshold (default: 80)
        """
        
        k_period = params.get('k_period', 14)
        d_period = params.get('d_period', 3)
        oversold = params.get('oversold', 35)
        overbought = params.get('overbought', 80)
        
        # Calculate Stochastic oscillator
        stoch = ta.momentum.StochasticOscillator(
            high=data['high'], 
            low=data['low'], 
            close=data['close'], 
            window=k_period, 
            smooth_window=d_period
        )
        
        k_percent = stoch.stoch()
        d_percent = stoch.stoch_signal()
        
        # Generate signals
        signals = pd.Series(0, index=data.index)
        
        # Buy signal: %K > %D in oversold region
        buy_condition = (
            (k_percent > d_percent) & 
            (k_percent < oversold)
        )
        
        # Sell signal: %K < %D in overbought region
        sell_condition = (
            (k_percent < d_percent) & 
            (k_percent > overbought)
        )
        
        signals[buy_condition] = 1
        signals[sell_condition] = -1
        
        return signals
    
    @staticmethod
    def macd_strategy(data: pd.DataFrame, **params) -> pd.Series:
        """
        MACD-based trading strategy
        
        Parameters:
        - fast_period: Fast EMA period (default: 12)
        - slow_period: Slow EMA period (default: 26)
        - signal_period: Signal line period (default: 9)
        """
        
        fast_period = params.get('fast_period', 12)
        slow_period = params.get('slow_period', 26)
        signal_period = params.get('signal_period', 9)
        
        # Calculate MACD
        macd_indicator = ta.trend.MACD(
            close=data['close'],
            window_fast=fast_period,
            window_slow=slow_period,
            window_sign=signal_period
        )
        
        macd = macd_indicator.macd()
        macd_signal = macd_indicator.macd_signal()
        macd_histogram = macd_indicator.macd_diff()
        
        # Generate signals
        signals = pd.Series(0, index=data.index)
        
        # Buy signal: MACD crosses above signal line
        buy_condition = (
            (macd > macd_signal) & 
            (macd.shift(1) <= macd_signal.shift(1))
        )
        
        # Sell signal: MACD crosses below signal line
        sell_condition = (
            (macd < macd_signal) & 
            (macd.shift(1) >= macd_signal.shift(1))
        )
        
        signals[buy_condition] = 1
        signals[sell_condition] = -1
        
        return signals
    
    @staticmethod
    def rsi_strategy(data: pd.DataFrame, **params) -> pd.Series:
        """
        RSI-based trading strategy
        
        Parameters:
        - period: RSI period (default: 14)
        - oversold: Oversold threshold (default: 30)
        - overbought: Overbought threshold (default: 70)
        """
        
        period = params.get('period', 14)
        oversold = params.get('oversold', 30)
        overbought = params.get('overbought', 70)
        
        # Calculate RSI
        rsi = ta.momentum.RSIIndicator(data['close'], window=period).rsi()
        
        # Generate signals
        signals = pd.Series(0, index=data.index)
        
        # Buy signal: RSI crosses above oversold level
        buy_condition = (
            (rsi > oversold) & 
            (rsi.shift(1) <= oversold)
        )
        
        # Sell signal: RSI crosses below overbought level
        sell_condition = (
            (rsi < overbought) & 
            (rsi.shift(1) >= overbought)
        )
        
        signals[buy_condition] = 1
        signals[sell_condition] = -1
        
        return signals
    
    @staticmethod
    def bollinger_bands_strategy(data: pd.DataFrame, **params) -> pd.Series:
        """
        Bollinger Bands mean reversion strategy
        
        Parameters:
        - period: Moving average period (default: 20)
        - std_dev: Standard deviation multiplier (default: 2)
        """
        
        period = params.get('period', 20)
        std_dev = params.get('std_dev', 2)
        
        # Calculate Bollinger Bands
        bb = ta.volatility.BollingerBands(close=data['close'], window=period, window_dev=std_dev)
        
        bb_upper = bb.bollinger_hband()
        bb_lower = bb.bollinger_lband()
        bb_middle = bb.bollinger_mavg()
        
        # Generate signals
        signals = pd.Series(0, index=data.index)
        
        # Buy signal: Price touches lower band and moves back up
        buy_condition = (
            (data['close'] <= bb_lower) & 
            (data['close'].shift(1) > bb_lower.shift(1))
        )
        
        # Sell signal: Price touches upper band and moves back down
        sell_condition = (
            (data['close'] >= bb_upper) & 
            (data['close'].shift(1) < bb_upper.shift(1))
        )
        
        signals[buy_condition] = 1
        signals[sell_condition] = -1
        
        return signals
    
    @staticmethod
    def combined_strategy(data: pd.DataFrame, **params) -> pd.Series:
        """
        Combined multi-indicator strategy
        
        Parameters:
        - Use parameters for individual strategies with prefixes:
          - stoch_rsi_*: StochRSI parameters
          - ema_*: EMA parameters  
          - rsi_*: RSI parameters
        - min_signals: Minimum number of confirming signals (default: 2)
        """
        
        min_signals = params.get('min_signals', 2)
        
        # Extract parameters for each strategy
        stoch_rsi_params = {k.replace('stoch_rsi_', ''): v for k, v in params.items() if k.startswith('stoch_rsi_')}
        ema_params = {k.replace('ema_', ''): v for k, v in params.items() if k.startswith('ema_')}
        rsi_params = {k.replace('rsi_', ''): v for k, v in params.items() if k.startswith('rsi_')}
        
        # Get signals from individual strategies
        stoch_rsi_signals = BacktestingStrategies.stochastic_rsi_strategy(data, **stoch_rsi_params)
        ema_signals = BacktestingStrategies.ema_strategy(data, **ema_params)
        rsi_signals = BacktestingStrategies.rsi_strategy(data, **rsi_params)
        
        # Combine signals
        combined_signals = pd.Series(0, index=data.index)
        
        # Count positive signals
        buy_signals_count = (
            (stoch_rsi_signals == 1).astype(int) +
            (ema_signals == 1).astype(int) +
            (rsi_signals == 1).astype(int)
        )
        
        # Count negative signals
        sell_signals_count = (
            (stoch_rsi_signals == -1).astype(int) +
            (ema_signals == -1).astype(int) +
            (rsi_signals == -1).astype(int)
        )
        
        # Generate combined signals
        combined_signals[buy_signals_count >= min_signals] = 1
        combined_signals[sell_signals_count >= min_signals] = -1
        
        return combined_signals

class ParameterOptimizer:
    """
    Parameter optimization for trading strategies
    """
    
    def __init__(self):
        self.logger = logging.getLogger('backtesting.optimizer')
    
    def optimize_stoch_rsi_parameters(self, data: pd.DataFrame, 
                                    strategy_func) -> Dict[str, Any]:
        """
        Optimize StochRSI parameters using grid search
        """
        
        param_ranges = {
            'rsi_period': range(10, 21, 2),
            'stoch_period': range(10, 21, 2), 
            'k_period': range(2, 6),
            'oversold_threshold': range(20, 41, 5),
            'overbought_threshold': range(70, 91, 5)
        }
        
        return self._grid_search_optimization(data, strategy_func, param_ranges)
    
    def optimize_ema_parameters(self, data: pd.DataFrame, 
                              strategy_func) -> Dict[str, Any]:
        """
        Optimize EMA parameters
        """
        
        param_ranges = {
            'fast_period': range(5, 16, 2),
            'slow_period': range(15, 31, 3)
        }
        
        return self._grid_search_optimization(data, strategy_func, param_ranges)
    
    def optimize_combined_parameters(self, data: pd.DataFrame, 
                                   strategy_func) -> Dict[str, Any]:
        """
        Optimize combined strategy parameters
        """
        
        param_ranges = {
            'stoch_rsi_rsi_period': range(12, 17, 2),
            'stoch_rsi_oversold_threshold': range(25, 41, 5),
            'ema_fast_period': range(7, 13, 2),
            'ema_slow_period': range(18, 25, 3),
            'rsi_period': range(12, 17, 2),
            'rsi_oversold': range(25, 36, 5),
            'min_signals': range(2, 4)
        }
        
        return self._grid_search_optimization(data, strategy_func, param_ranges)
    
    def _grid_search_optimization(self, data: pd.DataFrame, 
                                strategy_func, 
                                param_ranges: Dict[str, range]) -> Dict[str, Any]:
        """
        Perform grid search optimization
        """
        from backtesting.backtesting_engine import BacktestingEngine
        
        best_params = {}
        best_metric = -float('inf')
        
        # Generate all parameter combinations
        from itertools import product
        param_names = list(param_ranges.keys())
        param_values = list(param_ranges.values())
        
        total_combinations = np.prod([len(values) for values in param_values])
        self.logger.info(f"Starting grid search with {total_combinations} combinations")
        
        tested_combinations = 0
        
        for combination in product(*param_values):
            params = dict(zip(param_names, combination))
            
            try:
                # Run backtest with these parameters
                engine = BacktestingEngine(initial_capital=100000)
                result = engine.run_backtest(data, strategy_func, params)
                
                # Use Sharpe ratio as optimization metric
                # Could be customized to use other metrics
                metric = result.sharpe_ratio
                
                if metric > best_metric:
                    best_metric = metric
                    best_params = params.copy()
                
                tested_combinations += 1
                
                if tested_combinations % 100 == 0:
                    self.logger.info(f"Tested {tested_combinations}/{total_combinations} combinations")
                
            except Exception as e:
                self.logger.warning(f"Optimization failed for params {params}: {e}")
        
        self.logger.info(f"Optimization completed. Best Sharpe ratio: {best_metric:.2f}")
        self.logger.info(f"Best parameters: {best_params}")
        
        return best_params
    
    def walk_forward_optimization(self, data: pd.DataFrame, 
                                strategy_func,
                                param_ranges: Dict[str, range],
                                window_size: int = 252,
                                optimization_window: int = 126) -> List[Dict[str, Any]]:
        """
        Walk-forward optimization
        """
        
        optimization_results = []
        
        for start_idx in range(0, len(data) - window_size, optimization_window):
            end_idx = start_idx + window_size
            
            if end_idx >= len(data):
                break
            
            # Get optimization window data
            opt_data = data.iloc[start_idx:start_idx + optimization_window]
            
            # Optimize parameters
            best_params = self._grid_search_optimization(opt_data, strategy_func, param_ranges)
            
            # Test on subsequent data
            test_data = data.iloc[start_idx + optimization_window:end_idx]
            
            if len(test_data) > 20:  # Minimum test period
                from backtesting.backtesting_engine import BacktestingEngine
                engine = BacktestingEngine()
                result = engine.run_backtest(test_data, strategy_func, best_params)
                
                optimization_results.append({
                    'period': f"{test_data.index[0]} to {test_data.index[-1]}",
                    'optimal_params': best_params,
                    'result': result
                })
        
        return optimization_results