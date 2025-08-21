#!/usr/bin/env python3
"""
Base Strategy Class for Epic 2 Backtesting
==========================================

Abstract base class for all trading strategies used in Epic 2 backtesting engine.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Any, Optional
import pandas as pd


class Strategy(ABC):
    """Abstract base class for trading strategies"""
    
    def __init__(self, name: str = None):
        """Initialize strategy"""
        self.name = name or self.__class__.__name__
        self.parameters = {}
        self.signals_history = []
        
    @abstractmethod
    def generate_signals(self, historical_data: Dict[str, pd.DataFrame], timestamp: datetime) -> List[Dict[str, Any]]:
        """
        Generate trading signals based on historical data
        
        Args:
            historical_data: Dictionary of symbol -> DataFrame with OHLCV data
            timestamp: Current timestamp for signal generation
            
        Returns:
            List of signal dictionaries with keys: symbol, action, confidence, etc.
        """
        pass
    
    def get_parameters(self) -> Dict[str, Any]:
        """Get strategy parameters"""
        return self.parameters
    
    def set_parameters(self, parameters: Dict[str, Any]):
        """Set strategy parameters"""
        self.parameters.update(parameters)
    
    def get_signals_history(self) -> List[Dict[str, Any]]:
        """Get historical signals generated"""
        return self.signals_history
    
    def reset(self):
        """Reset strategy state"""
        self.signals_history = []


class SimpleMovingAverageStrategy(Strategy):
    """Simple Moving Average Crossover Strategy for testing"""
    
    def __init__(self, short_period: int = 10, long_period: int = 20):
        super().__init__("Simple MA Crossover")
        self.short_period = short_period
        self.long_period = long_period
        self.parameters = {
            'short_period': short_period,
            'long_period': long_period
        }
    
    def generate_signals(self, historical_data: Dict[str, pd.DataFrame], timestamp: datetime) -> List[Dict[str, Any]]:
        """Generate MA crossover signals"""
        signals = []
        
        for symbol, data in historical_data.items():
            if len(data) < self.long_period:
                continue
                
            # Calculate moving averages
            short_ma = data['close'].rolling(self.short_period).mean()
            long_ma = data['close'].rolling(self.long_period).mean()
            
            # Get current values
            current_short = short_ma.iloc[-1]
            current_long = long_ma.iloc[-1]
            prev_short = short_ma.iloc[-2] if len(short_ma) > 1 else current_short
            prev_long = long_ma.iloc[-2] if len(long_ma) > 1 else current_long
            
            # Detect crossover
            signal = None
            if prev_short <= prev_long and current_short > current_long:
                signal = {
                    'symbol': symbol,
                    'action': 'buy',
                    'confidence': 0.7,
                    'price': data['close'].iloc[-1],
                    'timestamp': timestamp,
                    'strategy': self.name,
                    'reason': 'MA bullish crossover'
                }
            elif prev_short >= prev_long and current_short < current_long:
                signal = {
                    'symbol': symbol,
                    'action': 'sell',
                    'confidence': 0.7,
                    'price': data['close'].iloc[-1],
                    'timestamp': timestamp,
                    'strategy': self.name,
                    'reason': 'MA bearish crossover'
                }
            
            if signal:
                signals.append(signal)
                self.signals_history.append(signal)
        
        return signals


def get_strategy_by_name(name: str, **kwargs) -> Strategy:
    """Factory function to get strategy by name"""
    strategies = {
        'ma_crossover': SimpleMovingAverageStrategy,
        'simple_ma': SimpleMovingAverageStrategy,
    }
    
    strategy_class = strategies.get(name.lower())
    if strategy_class:
        return strategy_class(**kwargs)
    else:
        # Default to simple MA strategy
        return SimpleMovingAverageStrategy(**kwargs)