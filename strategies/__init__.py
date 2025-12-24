from typing import Any, Dict, Optional, Type
from strategies.base_strategy import Strategy, SimpleMovingAverageStrategy, BaseStrategy
from strategies.stoch_rsi_strategy import StochRSIStrategy
from strategies.ma_crossover_strategy import MACrossoverStrategy
from strategies.crypto_scalping_strategy import CryptoDayTradingBot
from strategies.position_manager import Position, PositionManager
from strategies.trading_metrics import TradeLog, TradingMetrics, RiskManager

__all__ = [
    'Strategy',
    'BaseStrategy',
    'SimpleMovingAverageStrategy',
    'StochRSIStrategy',
    'MACrossoverStrategy',
    'CryptoDayTradingBot',
    'Position',
    'PositionManager',
    'TradeLog',
    'TradingMetrics',
    'RiskManager',
    'get_strategy',
]

def get_strategy(
    strategy_name: str,
    config: Any,
    alpaca_client: Optional[Any] = None,
    scanner_service: Optional[Any] = None,
) -> Strategy:
    """
    Centralized factory function to create strategy instances.

    Args:
        strategy_name: Name of the strategy to instantiate
        config: Configuration object
        alpaca_client: Optional Alpaca client (required for CryptoDayTradingBot)
        scanner_service: Optional shared ScannerService for centralized data

    Returns:
        Strategy instance
    """
    strategies: Dict[str, Type[Strategy]] = {
        'stochrsi': StochRSIStrategy,
        'macrossover': MACrossoverStrategy,
        'ma_crossover': MACrossoverStrategy,
        'simple_ma': SimpleMovingAverageStrategy,
        'crypto_scalping': CryptoDayTradingBot,
        'cryptoscalping': CryptoDayTradingBot,
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

    # CryptoDayTradingBot requires alpaca_client as first arg
    if strategy_class == CryptoDayTradingBot:
        # Try to get dependencies from service registry if not provided
        try:
            from core.service_registry import get_service_registry
            registry = get_service_registry()
            if alpaca_client is None:
                alpaca_client = registry.get('alpaca_client')
            if scanner_service is None:
                try:
                    scanner_service = registry.get('scanner_service')
                except ValueError:
                    pass  # ScannerService not registered yet
        except Exception:
            pass

        if alpaca_client is None:
            raise ValueError("CryptoDayTradingBot requires alpaca_client")

        # Extract symbols from config
        symbols = getattr(config, 'symbols', None)
        return CryptoDayTradingBot(
            alpaca_client=alpaca_client,
            scanner=scanner_service,  # Inject shared scanner
            enabled_symbols=symbols
        )

    return strategy_class(config)
