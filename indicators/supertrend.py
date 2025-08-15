"""
SuperTrend Indicator Implementation
Based on TradingView's SuperTrend indicator
"""

import pandas as pd
import numpy as np


def calculate_supertrend(df, period=10, multiplier=3.0):
    """
    Calculate SuperTrend indicator
    
    Args:
        df: DataFrame with OHLC data
        period: ATR period (default: 10)
        multiplier: ATR multiplier factor (default: 3.0)
    
    Returns:
        DataFrame with SuperTrend values and signals
    """
    
    # Calculate ATR
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    atr = true_range.rolling(period).mean()
    
    # Calculate basic bands
    hl_avg = (df['high'] + df['low']) / 2
    upper_band = hl_avg + (multiplier * atr)
    lower_band = hl_avg - (multiplier * atr)
    
    # Initialize SuperTrend values
    supertrend = pd.Series(index=df.index, dtype=float)
    direction = pd.Series(index=df.index, dtype=int)
    
    for i in range(period, len(df)):
        # Current close price
        curr_close = df['close'].iloc[i]
        
        # Previous values
        if i == period:
            # First calculation
            if curr_close <= upper_band.iloc[i]:
                supertrend.iloc[i] = upper_band.iloc[i]
                direction.iloc[i] = -1
            else:
                supertrend.iloc[i] = lower_band.iloc[i]
                direction.iloc[i] = 1
        else:
            prev_direction = direction.iloc[i-1]
            
            # Calculate current bands with proper logic
            if prev_direction == 1:
                # Previous trend was up
                if curr_close <= lower_band.iloc[i]:
                    supertrend.iloc[i] = upper_band.iloc[i]
                    direction.iloc[i] = -1
                else:
                    supertrend.iloc[i] = max(lower_band.iloc[i], supertrend.iloc[i-1])
                    direction.iloc[i] = 1
            else:
                # Previous trend was down
                if curr_close >= upper_band.iloc[i]:
                    supertrend.iloc[i] = lower_band.iloc[i]
                    direction.iloc[i] = 1
                else:
                    supertrend.iloc[i] = min(upper_band.iloc[i], supertrend.iloc[i-1])
                    direction.iloc[i] = -1
    
    # Create result DataFrame
    result = pd.DataFrame(index=df.index)
    result['supertrend'] = supertrend
    result['direction'] = direction
    result['upper_band'] = upper_band
    result['lower_band'] = lower_band
    result['atr'] = atr
    
    # Generate signals
    result['signal'] = 0
    result.loc[result['direction'] == 1, 'signal'] = 1  # Buy signal
    result.loc[result['direction'] == -1, 'signal'] = -1  # Sell signal
    
    # Identify signal changes
    result['signal_change'] = result['direction'].diff()
    result['buy_signal'] = (result['signal_change'] == 2)  # Change from -1 to 1
    result['sell_signal'] = (result['signal_change'] == -2)  # Change from 1 to -1
    
    return result


def get_current_signal(df, period=10, multiplier=3.0):
    """
    Get the current SuperTrend signal
    
    Args:
        df: DataFrame with OHLC data
        period: ATR period
        multiplier: ATR multiplier
    
    Returns:
        dict with current signal and trend information
    """
    
    if len(df) < period + 1:
        return {
            'signal': 0,
            'trend': 'neutral',
            'supertrend_value': None,
            'current_price': None,
            'message': 'Insufficient data'
        }
    
    # Calculate SuperTrend
    st_data = calculate_supertrend(df, period, multiplier)
    
    # Get latest values
    latest_idx = -1
    while pd.isna(st_data['signal'].iloc[latest_idx]) and abs(latest_idx) < len(st_data):
        latest_idx -= 1
    
    current_signal = st_data['signal'].iloc[latest_idx]
    current_st = st_data['supertrend'].iloc[latest_idx]
    current_price = df['close'].iloc[latest_idx]
    
    # Check for recent signal changes
    recent_buy = False
    recent_sell = False
    
    for i in range(max(-5, -len(st_data)), 0):
        if st_data['buy_signal'].iloc[i]:
            recent_buy = True
            break
        if st_data['sell_signal'].iloc[i]:
            recent_sell = True
            break
    
    # Determine trend
    if current_signal == 1:
        trend = 'bullish'
        action = 'BUY' if recent_buy else 'HOLD'
    elif current_signal == -1:
        trend = 'bearish'
        action = 'SELL' if recent_sell else 'WAIT'
    else:
        trend = 'neutral'
        action = 'NEUTRAL'
    
    return {
        'signal': int(current_signal) if not pd.isna(current_signal) else 0,
        'trend': trend,
        'action': action,
        'supertrend_value': float(current_st) if not pd.isna(current_st) else None,
        'current_price': float(current_price),
        'upper_band': float(st_data['upper_band'].iloc[latest_idx]) if not pd.isna(st_data['upper_band'].iloc[latest_idx]) else None,
        'lower_band': float(st_data['lower_band'].iloc[latest_idx]) if not pd.isna(st_data['lower_band'].iloc[latest_idx]) else None,
        'atr': float(st_data['atr'].iloc[latest_idx]) if not pd.isna(st_data['atr'].iloc[latest_idx]) else None,
        'recent_signal_change': recent_buy or recent_sell
    }


def calculate_multi_timeframe_supertrend(symbol, data_manager, timeframes=['1Min', '5Min', '15Min'], period=10, multiplier=3.0):
    """
    Calculate SuperTrend across multiple timeframes for stronger signals
    
    Args:
        symbol: Stock symbol
        data_manager: Data manager instance
        timeframes: List of timeframes to analyze
        period: ATR period
        multiplier: ATR multiplier
    
    Returns:
        dict with multi-timeframe analysis
    """
    
    results = {}
    signals = []
    
    for tf in timeframes:
        # Get historical data for timeframe
        df = data_manager.get_historical_data(symbol, tf, limit=200)
        
        if not df.empty and len(df) > period:
            signal_data = get_current_signal(df, period, multiplier)
            results[tf] = signal_data
            signals.append(signal_data['signal'])
    
    # Determine overall signal
    if len(signals) > 0:
        avg_signal = np.mean(signals)
        
        if avg_signal > 0.5:
            overall_signal = 1
            overall_trend = 'bullish'
            confidence = avg_signal
        elif avg_signal < -0.5:
            overall_signal = -1
            overall_trend = 'bearish'
            confidence = abs(avg_signal)
        else:
            overall_signal = 0
            overall_trend = 'neutral'
            confidence = 1 - abs(avg_signal)
    else:
        overall_signal = 0
        overall_trend = 'neutral'
        confidence = 0
    
    return {
        'symbol': symbol,
        'timeframe_signals': results,
        'overall_signal': overall_signal,
        'overall_trend': overall_trend,
        'confidence': confidence,
        'signal_alignment': all(s == signals[0] for s in signals) if signals else False
    }