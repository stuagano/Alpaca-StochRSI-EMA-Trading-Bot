"""
Common calculation utilities for trading strategies.

Provides DRY-compliant functions for P&L calculations, position sizing,
and price target calculations.
"""

from decimal import Decimal
from typing import Union

Number = Union[int, float, Decimal]


def to_decimal(value: Number) -> Decimal:
    """
    Convert a number to Decimal for precise financial calculations.

    Args:
        value: Number to convert (int, float, or Decimal)

    Returns:
        Decimal representation of the value
    """
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def calculate_position_pnl(
    entry_price: Number,
    current_price: Number,
    quantity: Number,
    side: str = 'buy'
) -> float:
    """
    Calculate realized or unrealized P&L for a position.

    Args:
        entry_price: Price at which position was entered
        current_price: Current market price
        quantity: Position size
        side: 'buy' for long positions, 'sell' for short positions

    Returns:
        P&L amount (positive for profit, negative for loss)
    """
    entry = float(entry_price)
    current = float(current_price)
    qty = float(quantity)

    if side.lower() == 'buy':
        return (current - entry) * qty
    else:
        return (entry - current) * qty


def calculate_pnl_percentage(
    entry_price: Number,
    current_price: Number,
    side: str = 'buy'
) -> float:
    """
    Calculate P&L as a percentage of entry price.

    Args:
        entry_price: Price at which position was entered
        current_price: Current market price
        side: 'buy' for long positions, 'sell' for short positions

    Returns:
        P&L percentage (e.g., 0.05 for 5% profit)
    """
    entry = float(entry_price)
    current = float(current_price)

    if entry == 0:
        return 0.0

    if side.lower() == 'buy':
        return (current - entry) / entry
    else:
        return (entry - current) / entry


def calculate_target_price(
    entry_price: Number,
    take_profit_pct: Number,
    side: str = 'buy'
) -> float:
    """
    Calculate take-profit target price.

    Args:
        entry_price: Price at which position was entered
        take_profit_pct: Take profit percentage (e.g., 0.015 for 1.5%)
        side: 'buy' for long positions, 'sell' for short positions

    Returns:
        Target price for take-profit
    """
    entry = float(entry_price)
    pct = float(take_profit_pct)

    if side.lower() == 'buy':
        return entry * (1 + pct)
    else:
        return entry * (1 - pct)


def calculate_stop_price(
    entry_price: Number,
    stop_loss_pct: Number,
    side: str = 'buy'
) -> float:
    """
    Calculate stop-loss price.

    Args:
        entry_price: Price at which position was entered
        stop_loss_pct: Stop loss percentage (e.g., 0.015 for 1.5%)
        side: 'buy' for long positions, 'sell' for short positions

    Returns:
        Stop price for stop-loss
    """
    entry = float(entry_price)
    pct = float(stop_loss_pct)

    if side.lower() == 'buy':
        return entry * (1 - pct)
    else:
        return entry * (1 + pct)


def calculate_position_size(
    capital: Number,
    price: Number,
    max_position_pct: float = 0.03,
    max_position_value: float = 100.0
) -> float:
    """
    Calculate position size based on risk rules.

    Args:
        capital: Available capital
        price: Current asset price
        max_position_pct: Maximum percentage of capital per position
        max_position_value: Maximum absolute position value

    Returns:
        Quantity to purchase
    """
    cap = float(capital)
    p = float(price)

    if p <= 0:
        return 0.0

    # Calculate based on percentage of capital
    pct_based = cap * max_position_pct

    # Apply max absolute value
    max_value = min(pct_based, max_position_value)

    return max_value / p
