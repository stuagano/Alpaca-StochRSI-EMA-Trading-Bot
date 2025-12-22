from typing import Any, Dict, Type
from strategies.base_strategy import Strategy, SimpleMovingAverageStrategy, BaseStrategy
from strategies.stoch_rsi_strategy import StochRSIStrategy
from strategies.ma_crossover_strategy import MACrossoverStrategy
from strategies.position_manager import Position, PositionManager
from strategies.trading_metrics import TradeLog, TradingMetrics, RiskManager

__all__ = [
    'Strategy',
    'BaseStrategy',
    'SimpleMovingAverageStrategy',
    'StochRSIStrategy',
    'MACrossoverStrategy',
    'Position',
    'PositionManager',
    'TradeLog',
    'TradingMetrics',
    'RiskManager',
    'get_strategy',
]

def get_strategy(strategy_name: str, config: Any) -> Strategy:
    """
    Centralized factory function to create strategy instances.
    
    Args:
        strategy_name: Name of the strategy to instantiate
        config: Configuration object
        
    Returns:
        Strategy instance
    """
    strategies: Dict[str, Type[Strategy]] = {
        'stochrsi': StochRSIStrategy,
        'macrossover': MACrossoverStrategy,
        'ma_crossover': MACrossoverStrategy,
        'simple_ma': SimpleMovingAverageStrategy,
    }
    
    # Normalize name for lookup
    name_key = strategy_name.lower().replace('_', '').replace('-', '')
    
    # Try direct mapping or normalized mapping
    strategy_class = strategies.get(strategy_name.lower()) or strategies.get(name_key)
    
    if not strategy_class:
        # Check if it matches any keys by normalized name
        for key in strategies:
            if key.replace('_', '') == name_key:
                strategy_class = strategies[key]
                break
                
    if not strategy_class:
        raise ValueError(f"Unknown strategy: {strategy_name}. Available: {list(strategies.keys())}")
        
    return strategy_class(config)
