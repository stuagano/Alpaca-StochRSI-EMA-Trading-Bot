#!/usr/bin/env python3
"""
Historical Chart Routes for 24/7 Data Access
Provides chart data regardless of market hours
"""

from flask import Blueprint, jsonify, request
import logging
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional

from services.historical_data_service import get_historical_data_service
from services.unified_data_manager import UnifiedDataManager
from utils.enhanced_logging_config import get_logger, LoggingContext, log_performance_metric

logger = get_logger(__name__)

# Create Blueprint
bp = Blueprint('historical_charts', __name__, url_prefix='/api/historical')

def init_historical_routes(app, data_manager: UnifiedDataManager):
    """Initialize historical chart routes with app context"""
    
    # Get historical data service
    try:
        historical_service = get_historical_data_service()
        logger.info("📊 Historical chart routes initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize historical service: {e}")
        historical_service = None
    
    @bp.route('/chart-data/<symbol>')
    def get_historical_chart_data(symbol):
        """
        Get chart data with historical fallback for 24/7 access
        Always returns data regardless of market hours
        """
        with LoggingContext(logger, f"get_historical_chart_data_{symbol}"):
            try:
                symbol = symbol.upper()
                
                # Get parameters
                timeframe = request.args.get('timeframe', '15Min')
                days = int(request.args.get('days', 7))
                limit = int(request.args.get('limit', 1000))
                
                # Check market status
                market_open = False
                market_status = "closed"
                
                try:
                    # Try to get market status from Alpaca
                    if historical_service:
                        clock = historical_service.api.get_clock()
                        market_open = clock.is_open
                        
                        if market_open:
                            market_status = "open"
                        elif datetime.now().hour < 9 or datetime.now().hour >= 16:
                            market_status = "closed"
                        else:
                            market_status = "pre-market" if datetime.now().hour < 9.5 else "after-hours"
                except:
                    pass
                
                # Get data - use hybrid approach
                if historical_service:
                    # Use historical service for 24/7 data
                    data = historical_service.get_hybrid_data(
                        symbol=symbol,
                        timeframe=timeframe,
                        lookback_days=days,
                        use_cache=True
                    )
                else:
                    # Fallback to data manager
                    end_time = datetime.now()
                    start_time = end_time - timedelta(days=days)
                    
                    data = data_manager.get_historical_data(
                        symbol=symbol,
                        timeframe=timeframe,
                        start=start_time,
                        end=end_time,
                        limit=limit
                    )
                
                if data is None or data.empty:
                    # No data available
                    return jsonify({
                        'success': False,
                        'error': 'No data available',
                        'symbol': symbol,
                        'market_status': market_status
                    })
                
                # Format data for charts
                chart_data = []
                for timestamp, row in data.iterrows():
                    chart_data.append({
                        'timestamp': timestamp.isoformat() if hasattr(timestamp, 'isoformat') else str(timestamp),
                        'time': int(timestamp.timestamp()) if hasattr(timestamp, 'timestamp') else 0,
                        'open': float(row.get('open', 0)),
                        'high': float(row.get('high', 0)),
                        'low': float(row.get('low', 0)),
                        'close': float(row.get('close', 0)),
                        'volume': int(row.get('volume', 0))
                    })
                
                # Calculate indicators if requested
                indicators = {}
                if request.args.get('indicators', 'false').lower() == 'true':
                    indicators = calculate_indicators(data)
                
                # Get data statistics
                stats = {
                    'total_bars': len(chart_data),
                    'earliest_data': chart_data[0]['timestamp'] if chart_data else None,
                    'latest_data': chart_data[-1]['timestamp'] if chart_data else None,
                    'data_source': 'live' if market_open else 'historical',
                    'cache_age_minutes': 0  # Will be updated if from cache
                }
                
                # Log performance metrics
                log_performance_metric("historical_chart_data_served", len(chart_data), {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "market_status": market_status
                })
                
                return jsonify({
                    'success': True,
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'market_status': market_status,
                    'market_open': market_open,
                    'candlestick_data': chart_data,
                    'indicators': indicators,
                    'statistics': stats,
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"❌ Error getting historical chart data: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e),
                    'symbol': symbol
                })
    
    @bp.route('/prefetch/<symbol>')
    def prefetch_historical_data(symbol):
        """Prefetch and cache historical data for a symbol"""
        with LoggingContext(logger, f"prefetch_data_{symbol}"):
            try:
                symbol = symbol.upper()
                timeframes = request.args.get('timeframes', '15Min,1Hour,1Day').split(',')
                days = int(request.args.get('days', 30))
                
                if not historical_service:
                    return jsonify({
                        'success': False,
                        'error': 'Historical service not available'
                    })
                
                results = {}
                for timeframe in timeframes:
                    try:
                        data = historical_service.fetch_historical_data(
                            symbol=symbol,
                            timeframe=timeframe,
                            start=datetime.now() - timedelta(days=days),
                            limit=5000
                        )
                        results[timeframe] = {
                            'success': True,
                            'bars_fetched': len(data) if data is not None else 0
                        }
                    except Exception as e:
                        results[timeframe] = {
                            'success': False,
                            'error': str(e)
                        }
                
                return jsonify({
                    'success': True,
                    'symbol': symbol,
                    'results': results,
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"❌ Error prefetching data: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                })
    
    @bp.route('/cache/stats')
    def get_cache_statistics():
        """Get statistics about cached historical data"""
        try:
            if not historical_service:
                return jsonify({
                    'success': False,
                    'error': 'Historical service not available'
                })
            
            stats = historical_service.get_data_stats()
            
            return jsonify({
                'success': True,
                'statistics': stats,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"❌ Error getting cache stats: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            })
    
    @bp.route('/cache/clear', methods=['POST'])
    def clear_cache():
        """Clear cached historical data"""
        try:
            if not historical_service:
                return jsonify({
                    'success': False,
                    'error': 'Historical service not available'
                })
            
            # Clear memory cache
            historical_service.memory_cache.clear()
            
            return jsonify({
                'success': True,
                'message': 'Cache cleared successfully',
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"❌ Error clearing cache: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            })
    
    @bp.route('/sync/start', methods=['POST'])
    def start_background_sync():
        """Start background data synchronization"""
        try:
            if not historical_service:
                return jsonify({
                    'success': False,
                    'error': 'Historical service not available'
                })
            
            data = request.get_json() or {}
            symbols = data.get('symbols', ['AAPL', 'GOOGL', 'MSFT'])
            timeframes = data.get('timeframes', ['15Min', '1Hour', '1Day'])
            
            historical_service.start_background_sync(symbols, timeframes)
            
            return jsonify({
                'success': True,
                'message': 'Background sync started',
                'symbols': symbols,
                'timeframes': timeframes,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"❌ Error starting sync: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            })
    
    @bp.route('/sync/stop', methods=['POST'])
    def stop_background_sync():
        """Stop background data synchronization"""
        try:
            if not historical_service:
                return jsonify({
                    'success': False,
                    'error': 'Historical service not available'
                })
            
            historical_service.stop_background_sync()
            
            return jsonify({
                'success': True,
                'message': 'Background sync stopped',
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"❌ Error stopping sync: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            })
    
    # Register blueprint with app
    app.register_blueprint(bp)
    
    # Start background sync for common symbols
    if historical_service:
        try:
            # Get symbols from config or use defaults
            default_symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN']
            historical_service.start_background_sync(default_symbols)
            logger.info(f"🔄 Started background sync for {default_symbols}")
        except Exception as e:
            logger.warning(f"⚠️ Could not start background sync: {e}")
    
    return bp

def calculate_indicators(data: pd.DataFrame) -> Dict[str, Any]:
    """Calculate technical indicators for the data"""
    try:
        indicators = {}
        
        if len(data) >= 20:
            # Simple Moving Averages
            indicators['sma_20'] = data['close'].rolling(window=20).mean().iloc[-1]
            
            if len(data) >= 50:
                indicators['sma_50'] = data['close'].rolling(window=50).mean().iloc[-1]
            
            if len(data) >= 200:
                indicators['sma_200'] = data['close'].rolling(window=200).mean().iloc[-1]
            
            # Volume metrics
            indicators['volume_avg'] = data['volume'].rolling(window=20).mean().iloc[-1]
            indicators['volume_ratio'] = data['volume'].iloc[-1] / indicators['volume_avg'] if indicators['volume_avg'] > 0 else 1.0
            
            # Price change
            indicators['price_change'] = data['close'].iloc[-1] - data['close'].iloc[-2]
            indicators['price_change_pct'] = (indicators['price_change'] / data['close'].iloc[-2] * 100) if data['close'].iloc[-2] > 0 else 0
            
            # High/Low
            indicators['day_high'] = data['high'].iloc[-1]
            indicators['day_low'] = data['low'].iloc[-1]
            indicators['day_range'] = indicators['day_high'] - indicators['day_low']
        
        return indicators
        
    except Exception as e:
        logger.error(f"Error calculating indicators: {e}")
        return {}