"""
Enhanced Chart API Routes for TradingView Lightweight Charts
Provides optimized endpoints for real-time chart data with StochRSI indicators
"""

from flask import Blueprint, jsonify, request
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional

from indicators.stoch_rsi_enhanced import (
    StochRSIIndicator, 
    calculate_stoch_rsi_for_chart,
    get_signal_markers_for_chart
)

logger = logging.getLogger(__name__)

# Create blueprint for chart routes
chart_bp = Blueprint('enhanced_charts', __name__, url_prefix='/api/v2')


def format_ohlcv_for_charts(data: pd.DataFrame) -> List[Dict]:
    """
    Format OHLCV data for TradingView Lightweight Charts.
    
    Args:
        data: DataFrame with OHLCV data
        
    Returns:
        List of candlestick data points
    """
    try:
        candlesticks = []
        
        for timestamp, row in data.iterrows():
            # Convert timestamp to UNIX seconds
            time_unix = int(timestamp.timestamp())
            
            candlestick = {
                'time': time_unix,
                'open': round(float(row['open']), 4),
                'high': round(float(row['high']), 4),
                'low': round(float(row['low']), 4),
                'close': round(float(row['close']), 4)
            }
            
            # Add volume if available
            if 'volume' in row and not pd.isna(row['volume']):
                candlestick['volume'] = int(row['volume'])
            
            candlesticks.append(candlestick)
        
        # Sort by time to ensure chronological order
        candlesticks.sort(key=lambda x: x['time'])
        
        return candlesticks
        
    except Exception as e:
        logger.error(f"Error formatting OHLCV data: {e}")
        return []


def format_volume_for_charts(data: pd.DataFrame) -> List[Dict]:
    """
    Format volume data for TradingView Lightweight Charts.
    
    Args:
        data: DataFrame with OHLCV data
        
    Returns:
        List of volume data points
    """
    try:
        volume_data = []
        
        for timestamp, row in data.iterrows():
            time_unix = int(timestamp.timestamp())
            
            # Color volume bars based on price movement
            color = '#26a64180' if row['close'] >= row['open'] else '#f8514980'
            
            volume_point = {
                'time': time_unix,
                'value': int(row.get('volume', 0)),
                'color': color
            }
            
            volume_data.append(volume_point)
        
        volume_data.sort(key=lambda x: x['time'])
        return volume_data
        
    except Exception as e:
        logger.error(f"Error formatting volume data: {e}")
        return []


def calculate_ema(prices: pd.Series, period: int = 20) -> pd.Series:
    """
    Calculate Exponential Moving Average.
    
    Args:
        prices: Series of closing prices
        period: EMA period
        
    Returns:
        EMA values as pandas Series
    """
    return prices.ewm(span=period, adjust=False).mean()


@chart_bp.route('/chart/<symbol>')
def get_enhanced_chart_data(symbol):
    """
    Get enhanced chart data with all indicators for a symbol.
    
    Returns complete dataset for TradingView Lightweight Charts including:
    - OHLCV candlestick data
    - StochRSI indicator data
    - EMA data
    - Volume data
    - Signal markers
    """
    try:
        # Get data manager from current app context
        from flask import current_app
        data_manager = current_app.config.get('data_manager')
        if not data_manager:
            return jsonify({'success': False, 'error': 'Data manager not available'})
        
        # Parse parameters
        timeframe = request.args.get('timeframe', '1Min')
        limit = int(request.args.get('limit', 200))
        
        logger.info(f"Fetching enhanced chart data for {symbol.upper()} - {timeframe}, limit {limit}")
        
        # Get historical data
        data = data_manager.get_historical_data(symbol.upper(), timeframe, limit=limit)
        
        if data.empty:
            return jsonify({
                'success': False,
                'error': 'No data available',
                'symbol': symbol.upper()
            })
        
        # Format basic chart data
        candlesticks = format_ohlcv_for_charts(data)
        volume_data = format_volume_for_charts(data)
        
        # Calculate EMA
        ema_period = 20  # Default EMA period
        ema_values = calculate_ema(data['close'], ema_period)
        ema_data = [
            {'time': int(ts.timestamp()), 'value': round(float(val), 4)}
            for ts, val in zip(data.index, ema_values)
            if not pd.isna(val)
        ]
        
        # Calculate StochRSI indicators
        config = {
            'indicators': {
                'stochRSI_params': {
                    'rsi_length': 14,
                    'stoch_length': 14,
                    'K': 3,
                    'D': 3
                }
            }
        }
        
        stoch_rsi_result = calculate_stoch_rsi_for_chart(data, config)
        
        # Generate signal markers
        markers = []
        if 'chart_data' in stoch_rsi_result and stoch_rsi_result['chart_data']:
            try:
                # Extract StochRSI series for marker generation
                stoch_rsi_indicator = StochRSIIndicator()
                indicators = stoch_rsi_indicator.calculate_full_stoch_rsi(data['close'])
                markers = get_signal_markers_for_chart(
                    data, 
                    indicators['StochRSI_K'], 
                    indicators['StochRSI_D']
                )
            except Exception as e:
                logger.warning(f"Error generating markers: {e}")
        
        # Prepare response
        response_data = {
            'success': True,
            'symbol': symbol.upper(),
            'timeframe': timeframe,
            'data_points': len(candlesticks),
            'last_update': datetime.now().isoformat(),
            'candlesticks': candlesticks,
            'volume': volume_data,
            'ema': ema_data,
            'indicators': {
                'stochRSI': stoch_rsi_result.get('chart_data', {}),
                'current_signals': stoch_rsi_result.get('current_signals', {})
            },
            'markers': markers,
            'config': {
                'ema_period': ema_period,
                'stochRSI_params': config['indicators']['stochRSI_params']
            }
        }
        
        logger.info(f"Enhanced chart data prepared: {len(candlesticks)} candles, {len(markers)} markers")
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error getting enhanced chart data for {symbol}: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'symbol': symbol.upper()
        })


@chart_bp.route('/indicators/<symbol>')
def get_indicator_data(symbol):
    """
    Get indicator data separately for real-time updates.
    
    This endpoint provides just the indicator values without the full chart data,
    optimized for real-time updates.
    """
    try:
        from flask import current_app
        data_manager = current_app.config.get('data_manager')
        if not data_manager:
            return jsonify({'success': False, 'error': 'Data manager not available'})
        
        # Get recent data for indicator calculation
        data = data_manager.get_historical_data(symbol.upper(), '1Min', limit=100)
        
        if data.empty:
            return jsonify({
                'success': False,
                'error': 'No data available',
                'symbol': symbol.upper()
            })
        
        # Calculate indicators
        config = {
            'indicators': {
                'stochRSI_params': {
                    'rsi_length': 14,
                    'stoch_length': 14,
                    'K': 3,
                    'D': 3
                }
            }
        }
        
        stoch_rsi_result = calculate_stoch_rsi_for_chart(data, config)
        
        # Calculate EMA
        ema_values = calculate_ema(data['close'], 20)
        current_ema = float(ema_values.iloc[-1]) if len(ema_values) > 0 else None
        
        # Get current price
        current_price = data_manager.get_latest_price(symbol.upper())
        
        response_data = {
            'success': True,
            'symbol': symbol.upper(),
            'timestamp': datetime.now().isoformat(),
            'current_values': {
                'price': current_price,
                'ema': current_ema,
                **stoch_rsi_result.get('current_signals', {})
            },
            'chart_updates': {
                'latest_time': int(data.index[-1].timestamp()) if len(data) > 0 else None,
                'indicators': stoch_rsi_result.get('chart_data', {})
            }
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error getting indicator data for {symbol}: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'symbol': symbol.upper()
        })


@chart_bp.route('/realtime/<symbol>')
def get_realtime_update(symbol):
    """
    Get real-time price and indicator updates.
    
    This endpoint provides the latest price bar and indicator values
    for real-time chart updates.
    """
    try:
        from flask import current_app
        data_manager = current_app.config.get('data_manager')
        if not data_manager:
            return jsonify({'success': False, 'error': 'Data manager not available'})
        
        # Get latest bars
        data = data_manager.get_historical_data(symbol.upper(), '1Min', limit=50)
        
        if data.empty:
            return jsonify({
                'success': False,
                'error': 'No data available',
                'symbol': symbol.upper()
            })
        
        # Get latest bar
        latest_bar = data.iloc[-1]
        latest_time = int(data.index[-1].timestamp())
        
        # Format latest candlestick
        latest_candle = {
            'time': latest_time,
            'open': round(float(latest_bar['open']), 4),
            'high': round(float(latest_bar['high']), 4),
            'low': round(float(latest_bar['low']), 4),
            'close': round(float(latest_bar['close']), 4)
        }
        
        # Add volume if available
        if 'volume' in latest_bar and not pd.isna(latest_bar['volume']):
            latest_candle['volume'] = int(latest_bar['volume'])
        
        # Calculate current indicators
        stoch_rsi_indicator = StochRSIIndicator()
        current_signals = stoch_rsi_indicator.get_current_signals(data['close'])
        
        # Calculate current EMA
        ema_values = calculate_ema(data['close'], 20)
        current_ema = float(ema_values.iloc[-1]) if len(ema_values) > 0 else None
        
        response_data = {
            'success': True,
            'symbol': symbol.upper(),
            'timestamp': datetime.now().isoformat(),
            'latest_candle': latest_candle,
            'indicators': {
                'ema': current_ema,
                **current_signals
            },
            'is_new_minute': self._is_new_minute(latest_time),
            'market_status': self._get_market_status()
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error getting realtime update for {symbol}: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'symbol': symbol.upper()
        })


def _is_new_minute(timestamp: int) -> bool:
    """
    Check if the given timestamp represents a new minute.
    
    Args:
        timestamp: UNIX timestamp
        
    Returns:
        True if this is a new minute
    """
    try:
        current_time = datetime.now()
        bar_time = datetime.fromtimestamp(timestamp)
        
        # Check if the bar time is within the current minute
        current_minute = current_time.replace(second=0, microsecond=0)
        bar_minute = bar_time.replace(second=0, microsecond=0)
        
        return bar_minute == current_minute
        
    except Exception:
        return False


def _get_market_status() -> str:
    """
    Get current market status.
    
    Returns:
        Market status string
    """
    try:
        from datetime import time
        
        current_time = datetime.now().time()
        
        # US market hours (9:30 AM - 4:00 PM ET)
        market_open = time(9, 30)
        market_close = time(16, 0)
        
        if market_open <= current_time <= market_close:
            return 'OPEN'
        else:
            return 'CLOSED'
            
    except Exception:
        return 'UNKNOWN'


@chart_bp.route('/signals/<symbol>')
def get_trading_signals(symbol):
    """
    Get comprehensive trading signals for a symbol.
    
    This endpoint provides detailed signal analysis including:
    - StochRSI signals
    - EMA trend
    - Signal strength
    - Market conditions
    """
    try:
        from flask import current_app
        data_manager = current_app.config.get('data_manager')
        if not data_manager:
            return jsonify({'success': False, 'error': 'Data manager not available'})
        
        # Get historical data for signal calculation
        data = data_manager.get_historical_data(symbol.upper(), '1Min', limit=100)
        
        if data.empty:
            return jsonify({
                'success': False,
                'error': 'No data available',
                'symbol': symbol.upper()
            })
        
        # Calculate StochRSI signals
        stoch_rsi_indicator = StochRSIIndicator()
        current_signals = stoch_rsi_indicator.get_current_signals(data['close'])
        
        # Calculate EMA trend
        ema_values = calculate_ema(data['close'], 20)
        current_price = float(data['close'].iloc[-1])
        current_ema = float(ema_values.iloc[-1]) if len(ema_values) > 0 else None
        
        # Determine EMA trend
        ema_trend = 'NEUTRAL'
        if current_ema:
            if current_price > current_ema:
                ema_trend = 'BULLISH'
            elif current_price < current_ema:
                ema_trend = 'BEARISH'
        
        # Combine signals for overall assessment
        overall_signal = 'NEUTRAL'
        signal_strength = 0.0
        
        if current_signals.get('stochRSI', {}).get('signal') == 1 and ema_trend == 'BULLISH':
            overall_signal = 'STRONG_BUY'
            signal_strength = 0.8
        elif current_signals.get('stochRSI', {}).get('signal') == 1:
            overall_signal = 'BUY'
            signal_strength = 0.6
        elif current_signals.get('stochRSI', {}).get('signal') == -1 and ema_trend == 'BEARISH':
            overall_signal = 'STRONG_SELL'
            signal_strength = 0.8
        elif current_signals.get('stochRSI', {}).get('signal') == -1:
            overall_signal = 'SELL'
            signal_strength = 0.6
        
        response_data = {
            'success': True,
            'symbol': symbol.upper(),
            'timestamp': datetime.now().isoformat(),
            'current_price': current_price,
            'overall_signal': overall_signal,
            'signal_strength': signal_strength,
            'indicators': {
                'stochRSI': current_signals.get('stochRSI', {}),
                'ema': {
                    'value': current_ema,
                    'trend': ema_trend,
                    'above_ema': current_price > current_ema if current_ema else None
                },
                'rsi': current_signals.get('rsi')
            },
            'market_status': _get_market_status()
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error getting trading signals for {symbol}: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'symbol': symbol.upper()
        })


# Error handlers for the blueprint
@chart_bp.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Endpoint not found',
        'message': 'The requested chart endpoint does not exist'
    }), 404


@chart_bp.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Internal server error',
        'message': 'An error occurred while processing the chart request'
    }), 500