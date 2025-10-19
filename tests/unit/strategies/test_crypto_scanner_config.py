import pytest

from config.unified_config import CryptoScannerConfig, TradingConfig
from strategies.crypto_scalping_strategy import CryptoVolatilityScanner, create_crypto_day_trader


def test_scanner_uses_thresholds_from_config():
    scanner_config = CryptoScannerConfig(
        universe=["BTCUSD", "ETHUSD"],
        min_24h_volume=250000,
        min_volatility=0.002,
        max_spread=0.005,
    )

    scanner = CryptoVolatilityScanner(config=scanner_config)

    assert scanner.min_24h_volume == 250000
    assert scanner.min_volatility == pytest.approx(0.002)
    assert scanner.max_spread == pytest.approx(0.005)
    assert scanner.get_enabled_symbols() == ["BTCUSD", "ETHUSD"]


def test_update_enabled_symbols_merges_defaults_with_overrides():
    scanner_config = CryptoScannerConfig(universe=["BTCUSD", "ETHUSD"])
    scanner = CryptoVolatilityScanner(config=scanner_config)

    scanner.update_enabled_symbols(["SOLUSD", "ETHUSD"])

    assert scanner.get_enabled_symbols() == ["BTCUSD", "ETHUSD", "SOLUSD"]


def test_create_crypto_day_trader_injects_scanner_configuration():
    trading_config = TradingConfig(
        investment_amount=5000,
        max_trades_active=3,
        symbols=["DOGEUSD"],
        crypto_scanner=CryptoScannerConfig(universe=["BTCUSD"]),
    )

    bot = create_crypto_day_trader(object(), trading_config)

    assert bot.scanner.get_enabled_symbols() == ["BTCUSD", "DOGEUSD"]
    expected_position_size = trading_config.investment_amount * trading_config.risk_management.max_position_size
    assert bot.max_position_size == pytest.approx(expected_position_size)
    assert bot.max_concurrent_positions == trading_config.max_trades_active
    expected_daily_loss = trading_config.investment_amount * trading_config.risk_management.max_daily_loss
    assert bot.max_daily_loss == pytest.approx(expected_daily_loss)
