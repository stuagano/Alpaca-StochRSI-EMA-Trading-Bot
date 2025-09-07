"""
Multi-Strategy Trading Manager
Provides multiple trading strategies with performance tracking and automatic switching
"""

import numpy as np
import pandas as pd
import asyncio
import websocket
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import logging
from threading import Lock
from enum import Enum

logger = logging.getLogger(__name__)

class StrategyType(Enum):
    SCALPING = "scalping"
    MOMENTUM = "momentum" 
    MEAN_REVERSION = "mean_reversion"
    BREAKOUT = "breakout"
    GRID = "grid"
    ARBITRAGE = "arbitrage"

@dataclass
class TradingSignal:
    symbol: str
    action: str  # 'buy', 'sell', 'hold'
    confidence: float
    price: float
    volatility: float
    volume_surge: bool
    momentum: float
    target_profit: float
    stop_loss: float
    strategy: str
    timestamp: datetime
    reason: str

@dataclass
class StrategyPerformance:
    total_trades: int = 0
    profitable_trades: int = 0
    total_profit: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    avg_profit: float = 0.0
    sharpe_ratio: float = 0.0
    last_updated: datetime = None

class BaseStrategy:
    """Base class for all trading strategies"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.performance = StrategyPerformance()
        self.enabled = True
        self.confidence_threshold = 0.6
        
    def analyze_market(self, market_data: Dict) -> Optional[TradingSignal]:
        """Override in child classes"""
        raise NotImplementedError
        
    def update_performance(self, trade_result: Dict):
        """Update strategy performance metrics"""
        self.performance.total_trades += 1
        profit = trade_result.get('profit', 0)
        self.performance.total_profit += profit
        
        if profit > 0:
            self.performance.profitable_trades += 1
            
        self.performance.win_rate = self.performance.profitable_trades / self.performance.total_trades
        self.performance.avg_profit = self.performance.total_profit / self.performance.total_trades
        self.performance.last_updated = datetime.now()

class ScalpingStrategy(BaseStrategy):
    """Ultra-short term scalping strategy"""
    
    def __init__(self):
        super().__init__(
            "High-Frequency Scalping",
            "Ultra-short term trades targeting 0.1-0.5% profits within minutes"
        )
        self.min_volatility = 0.003  # 0.3%
        self.target_profit_range = (0.001, 0.005)  # 0.1% to 0.5%
        self.max_hold_time = 300  # 5 minutes max
        
    def analyze_market(self, market_data: Dict) -> Optional[TradingSignal]:
        symbol = market_data['symbol']
        price = market_data['price']
        volatility = market_data.get('volatility', 0)
        volume_surge = market_data.get('volume_surge', False)
        momentum = market_data.get('momentum', 0.5)
        
        if volatility < self.min_volatility:
            return None
            
        # Scalping signals - quick in/out based on micro-trends
        confidence = 0.0
        action = 'hold'
        reason = ""
        
        # Strong momentum with volume spike
        if momentum > 0.75 and volume_surge and volatility > 0.005:
            action = 'buy'
            confidence = min(0.95, volatility * 20 + 0.3)
            reason = "Strong momentum + volume spike"
            
        elif momentum < 0.25 and volume_surge and volatility > 0.005:
            action = 'sell'
            confidence = min(0.95, volatility * 20 + 0.3)
            reason = "Bearish momentum + volume spike"
            
        # Quick reversals on oversold/overbought
        elif momentum > 0.85 and volatility > 0.008:
            action = 'sell'  # Fade the move
            confidence = 0.7
            reason = "Overbought reversal"
            
        elif momentum < 0.15 and volatility > 0.008:
            action = 'buy'  # Fade the move
            confidence = 0.7  
            reason = "Oversold bounce"
            
        if action != 'hold' and confidence >= self.confidence_threshold:
            return TradingSignal(
                symbol=symbol,
                action=action,
                confidence=confidence,
                price=price,
                volatility=volatility,
                volume_surge=volume_surge,
                momentum=momentum,
                target_profit=0.002,  # 0.2% target
                stop_loss=0.001,      # 0.1% stop
                strategy=self.name,
                timestamp=datetime.now(),
                reason=reason
            )
        return None

class MomentumStrategy(BaseStrategy):
    """Momentum-based strategy following strong trends"""
    
    def __init__(self):
        super().__init__(
            "Momentum Following", 
            "Follows strong directional moves with trend confirmation"
        )
        self.min_momentum_threshold = 0.7
        self.min_volatility = 0.01  # 1%
        
    def analyze_market(self, market_data: Dict) -> Optional[TradingSignal]:
        symbol = market_data['symbol']
        price = market_data['price']
        volatility = market_data.get('volatility', 0)
        volume_surge = market_data.get('volume_surge', False)
        momentum = market_data.get('momentum', 0.5)
        
        if volatility < self.min_volatility:
            return None
            
        confidence = 0.0
        action = 'hold'
        reason = ""
        
        # Strong bullish momentum
        if momentum > self.min_momentum_threshold:
            action = 'buy'
            confidence = min(0.9, momentum * 0.8 + (0.2 if volume_surge else 0))
            reason = f"Strong bullish momentum ({momentum:.2%})"
            
        # Strong bearish momentum
        elif momentum < (1 - self.min_momentum_threshold):
            action = 'sell'
            confidence = min(0.9, (1-momentum) * 0.8 + (0.2 if volume_surge else 0))
            reason = f"Strong bearish momentum ({1-momentum:.2%})"
            
        if action != 'hold' and confidence >= self.confidence_threshold:
            return TradingSignal(
                symbol=symbol,
                action=action,
                confidence=confidence,
                price=price,
                volatility=volatility,
                volume_surge=volume_surge,
                momentum=momentum,
                target_profit=volatility * 0.8,  # 80% of volatility
                stop_loss=volatility * 0.3,     # 30% of volatility
                strategy=self.name,
                timestamp=datetime.now(),
                reason=reason
            )
        return None

class MeanReversionStrategy(BaseStrategy):
    """Mean reversion strategy for overextended moves"""
    
    def __init__(self):
        super().__init__(
            "Mean Reversion",
            "Trades against overextended moves expecting price to return to mean"
        )
        self.overbought_threshold = 0.9
        self.oversold_threshold = 0.1
        
    def analyze_market(self, market_data: Dict) -> Optional[TradingSignal]:
        symbol = market_data['symbol']
        price = market_data['price']
        volatility = market_data.get('volatility', 0)
        volume_surge = market_data.get('volume_surge', False)
        momentum = market_data.get('momentum', 0.5)
        
        confidence = 0.0
        action = 'hold'
        reason = ""
        
        # Overbought - expect reversal down
        if momentum > self.overbought_threshold and volatility > 0.015:
            action = 'sell'
            confidence = min(0.85, (momentum - 0.8) * 5 + (0.1 if volume_surge else 0))
            reason = "Overbought reversal expected"
            
        # Oversold - expect bounce up
        elif momentum < self.oversold_threshold and volatility > 0.015:
            action = 'buy'
            confidence = min(0.85, (0.2 - momentum) * 5 + (0.1 if volume_surge else 0))
            reason = "Oversold bounce expected"
            
        if action != 'hold' and confidence >= self.confidence_threshold:
            return TradingSignal(
                symbol=symbol,
                action=action,
                confidence=confidence,
                price=price,
                volatility=volatility,
                volume_surge=volume_surge,
                momentum=momentum,
                target_profit=volatility * 0.6,
                stop_loss=volatility * 0.4,
                strategy=self.name,
                timestamp=datetime.now(),
                reason=reason
            )
        return None

class BreakoutStrategy(BaseStrategy):
    """Breakout strategy for range breaks with volume"""
    
    def __init__(self):
        super().__init__(
            "Volume Breakout",
            "Trades breakouts from consolidation ranges with volume confirmation"
        )
        self.min_volume_multiplier = 2.0
        
    def analyze_market(self, market_data: Dict) -> Optional[TradingSignal]:
        symbol = market_data['symbol']
        price = market_data['price']
        volatility = market_data.get('volatility', 0)
        volume_surge = market_data.get('volume_surge', False)
        momentum = market_data.get('momentum', 0.5)
        
        # Only trade on volume surges (breakout confirmation)
        if not volume_surge:
            return None
            
        confidence = 0.0
        action = 'hold'
        reason = ""
        
        # Breakout up with volume
        if momentum > 0.6 and volatility > 0.01:
            action = 'buy'
            confidence = min(0.88, volatility * 10 + momentum * 0.5)
            reason = "Upward breakout with volume"
            
        # Breakdown with volume
        elif momentum < 0.4 and volatility > 0.01:
            action = 'sell'
            confidence = min(0.88, volatility * 10 + (1-momentum) * 0.5)
            reason = "Downward breakdown with volume"
            
        if action != 'hold' and confidence >= self.confidence_threshold:
            return TradingSignal(
                symbol=symbol,
                action=action,
                confidence=confidence,
                price=price,
                volatility=volatility,
                volume_surge=volume_surge,
                momentum=momentum,
                target_profit=volatility * 1.2,  # Larger target for breakouts
                stop_loss=volatility * 0.5,
                strategy=self.name,
                timestamp=datetime.now(),
                reason=reason
            )
        return None

class GridStrategy(BaseStrategy):
    """Grid trading strategy for ranging markets"""
    
    def __init__(self):
        super().__init__(
            "Grid Trading",
            "Places buy/sell orders at regular intervals in ranging markets"
        )
        self.max_volatility = 0.02  # Only trade in lower volatility
        self.grid_spacing = 0.005   # 0.5% grid spacing
        
    def analyze_market(self, market_data: Dict) -> Optional[TradingSignal]:
        symbol = market_data['symbol']
        price = market_data['price']
        volatility = market_data.get('volatility', 0)
        volume_surge = market_data.get('volume_surge', False)
        momentum = market_data.get('momentum', 0.5)
        
        # Only trade in ranging (low volatility) markets
        if volatility > self.max_volatility:
            return None
            
        # Grid works best in sideways markets (momentum near 0.5)
        if abs(momentum - 0.5) > 0.3:
            return None
            
        confidence = 0.0
        action = 'hold'
        reason = ""
        
        # Buy at support levels (lower momentum in range)
        if 0.3 <= momentum <= 0.45:
            action = 'buy'
            confidence = 0.65
            reason = "Grid buy at support level"
            
        # Sell at resistance levels (higher momentum in range)
        elif 0.55 <= momentum <= 0.7:
            action = 'sell'
            confidence = 0.65
            reason = "Grid sell at resistance level"
            
        if action != 'hold' and confidence >= self.confidence_threshold:
            return TradingSignal(
                symbol=symbol,
                action=action,
                confidence=confidence,
                price=price,
                volatility=volatility,
                volume_surge=volume_surge,
                momentum=momentum,
                target_profit=self.grid_spacing,
                stop_loss=self.grid_spacing * 2,
                strategy=self.name,
                timestamp=datetime.now(),
                reason=reason
            )
        return None

class MultiStrategyManager:
    """Manages multiple trading strategies and selects best signals"""
    
    def __init__(self):
        self.strategies = {
            StrategyType.SCALPING: ScalpingStrategy(),
            StrategyType.MOMENTUM: MomentumStrategy(), 
            StrategyType.MEAN_REVERSION: MeanReversionStrategy(),
            StrategyType.BREAKOUT: BreakoutStrategy(),
            StrategyType.GRID: GridStrategy(),
        }
        
        self.active_strategy = StrategyType.SCALPING  # Default
        self.strategy_weights = {
            StrategyType.SCALPING: 0.3,
            StrategyType.MOMENTUM: 0.25,
            StrategyType.MEAN_REVERSION: 0.2,
            StrategyType.BREAKOUT: 0.15,
            StrategyType.GRID: 0.1,
        }
        
        self.performance_tracking = {}
        self.auto_switch_enabled = True
        self.switch_threshold = 0.1  # Switch if performance drops 10% below best
        
    def get_trading_signals(self, market_data: Dict) -> List[TradingSignal]:
        """Get signals from all enabled strategies"""
        signals = []
        
        if self.active_strategy == StrategyType.SCALPING:
            # Single strategy mode
            strategy = self.strategies[self.active_strategy]
            signal = strategy.analyze_market(market_data)
            if signal:
                signals.append(signal)
        else:
            # Multi-strategy mode - get signals from all strategies
            for strategy_type, strategy in self.strategies.items():
                if strategy.enabled:
                    signal = strategy.analyze_market(market_data)
                    if signal:
                        signals.append(signal)
        
        # Sort by confidence and return top signals
        signals.sort(key=lambda x: x.confidence, reverse=True)
        return signals[:3]  # Top 3 signals
        
    def set_active_strategy(self, strategy_type: StrategyType):
        """Set the active trading strategy"""
        if strategy_type in self.strategies:
            self.active_strategy = strategy_type
            logger.info(f"Switched to strategy: {self.strategies[strategy_type].name}")
        
    def get_strategy_performance(self) -> Dict[str, Dict]:
        """Get performance metrics for all strategies"""
        performance = {}
        for strategy_type, strategy in self.strategies.items():
            performance[strategy_type.value] = {
                'name': strategy.name,
                'description': strategy.description,
                'total_trades': strategy.performance.total_trades,
                'win_rate': strategy.performance.win_rate,
                'total_profit': strategy.performance.total_profit,
                'avg_profit': strategy.performance.avg_profit,
                'enabled': strategy.enabled,
                'last_updated': strategy.performance.last_updated.isoformat() if strategy.performance.last_updated else None
            }
        return performance
        
    def update_strategy_performance(self, strategy_name: str, trade_result: Dict):
        """Update performance for a specific strategy"""
        for strategy in self.strategies.values():
            if strategy.name == strategy_name:
                strategy.update_performance(trade_result)
                break
                
    def auto_switch_strategy(self):
        """Automatically switch to best performing strategy"""
        if not self.auto_switch_enabled:
            return
            
        best_strategy = None
        best_performance = -999999
        
        for strategy_type, strategy in self.strategies.items():
            if strategy.performance.total_trades >= 10:  # Need minimum trades
                performance_score = (
                    strategy.performance.win_rate * 0.6 + 
                    strategy.performance.avg_profit * 0.4
                )
                if performance_score > best_performance:
                    best_performance = performance_score
                    best_strategy = strategy_type
                    
        if best_strategy and best_strategy != self.active_strategy:
            current_performance = (
                self.strategies[self.active_strategy].performance.win_rate * 0.6 +
                self.strategies[self.active_strategy].performance.avg_profit * 0.4
            )
            
            if best_performance > current_performance * (1 + self.switch_threshold):
                self.set_active_strategy(best_strategy)
                logger.info(f"Auto-switched to better performing strategy: {best_strategy.value}")
                
    def get_strategy_config(self) -> Dict:
        """Get current strategy configuration"""
        return {
            'active_strategy': self.active_strategy.value,
            'available_strategies': [s.value for s in StrategyType],
            'strategy_details': {
                s.value: {
                    'name': strategy.name,
                    'description': strategy.description,
                    'enabled': strategy.enabled,
                    'confidence_threshold': strategy.confidence_threshold
                }
                for s, strategy in self.strategies.items()
            },
            'auto_switch_enabled': self.auto_switch_enabled,
            'performance': self.get_strategy_performance()
        }
        
    def update_strategy_config(self, config: Dict):
        """Update strategy configuration"""
        if 'active_strategy' in config:
            try:
                new_strategy = StrategyType(config['active_strategy'])
                self.set_active_strategy(new_strategy)
            except ValueError:
                logger.error(f"Invalid strategy type: {config['active_strategy']}")
                
        if 'auto_switch_enabled' in config:
            self.auto_switch_enabled = config['auto_switch_enabled']
            
        # Update individual strategy settings
        for strategy_name, settings in config.get('strategies', {}).items():
            try:
                strategy_type = StrategyType(strategy_name)
                if strategy_type in self.strategies:
                    strategy = self.strategies[strategy_type]
                    if 'enabled' in settings:
                        strategy.enabled = settings['enabled']
                    if 'confidence_threshold' in settings:
                        strategy.confidence_threshold = settings['confidence_threshold']
            except ValueError:
                continue