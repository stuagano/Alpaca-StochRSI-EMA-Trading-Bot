"""Paper-trading smoke test that submits and cancels a tiny crypto order."""

from __future__ import annotations

from datetime import datetime

import alpaca_trade_api as tradeapi
import pytest

from config.unified_config import get_config
from utils.alpaca import load_alpaca_credentials


@pytest.mark.paper_trading
@pytest.mark.slow
def test_execute_minimal_crypto_trade():
    """Submit a $1 market buy and cancel it to prove paper trading works."""

    config = get_config()
    creds = load_alpaca_credentials(config)

    if "paper" not in creds.base_url.lower():
        pytest.skip("Paper trading endpoint not configured")

    api = tradeapi.REST(creds.key_id, creds.secret_key, creds.base_url)
    account = api.get_account()

    assert account.account_blocked is False, "Paper account blocked"
    assert account.trading_blocked is False, "Trading blocked on paper account"

    # Use first configured symbol, normalise to Alpaca's crypto format (BTCUSD, etc.).
    raw_symbol = config.symbols[0]
    alpaca_symbol = raw_symbol.replace("/", "")

    order = api.submit_order(
        symbol=alpaca_symbol,
        notional=10,  # Alpaca requires >= $10 cost basis for crypto
        side="buy",
        type="market",
        time_in_force="gtc",
    )

    try:
        fetched = api.get_order(order.id)
        assert fetched.status.lower() not in {"rejected", "canceled"}, f"Order rejected: {fetched.status}"

    finally:
        # Always try to cancel so we leave no open orders behind
        try:
            api.cancel_order(order.id)
        except Exception:
            pass

        # If the order filled, close the tiny position to reset the paper account state
        try:
            api.close_position(alpaca_symbol)
        except Exception:
            pass
