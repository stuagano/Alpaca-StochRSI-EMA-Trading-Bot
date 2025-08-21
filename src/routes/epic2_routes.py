#!/usr/bin/env python3
"""
Epic 2 API Routes - Historical Data & Backtesting
=================================================

API endpoints for Epic 2's comprehensive historical data and backtesting features:
- Historical data access with 24/7 availability
- Backtesting engine integration
- Performance analytics
- Data export and reporting
- Chart data for visualization
"""

from flask import Blueprint, request, jsonify, send_file
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import json
import io
import asyncio
from typing import Dict, List, Any, Optional
import logging
from functools import wraps

from services.historical_data_service import get_historical_data_service
from services.epic2_backtesting_engine import get_backtest_engine, BacktestConfig
from strategies.stoch_rsi_strategy import StochRSIStrategy
from utils.auth_manager import require_auth

logger = logging.getLogger(__name__)

# Create Epic 2 blueprint
epic2_bp = Blueprint('epic2', __name__, url_prefix='/api/epic2')


def async_route(f):
    """Decorator to handle async routes in Flask"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(f(*args, **kwargs))
        finally:
            loop.close()
    return decorated_function


@epic2_bp.route('/status', methods=['GET'])
def epic2_status():
    """Get Epic 2 system status"""
    try:
        # Get historical service instance
        hist_service = get_historical_data_service()
        
        # Check data availability
        stats = hist_service.get_data_stats()
        
        # Check if market is open (fallback if API not available)
        try:
            clock = hist_service.api.get_clock()
            market_open = clock.is_open
        except:
            market_open = False
        
        return jsonify({
            'status': 'online',
            'epic': 'Epic 2 - Historical Data & Backtesting',
            'version': '1.0.0',
            'market_open': market_open,
            'features': {
                'historical_data': True,
                'backtesting': True,
                'performance_analytics': True,
                'data_export': True,
                '24_7_charts': True
            },
            'data_stats': stats,
            'supported_timeframes': ['1Min', '5Min', '15Min', '30Min', '1Hour', '4Hour', '1Day', '1Week'],
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Epic 2 status error: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


@epic2_bp.route('/historical/<symbol>', methods=['GET'])
@async_route
async def get_historical_data(symbol):
    """
    Get historical data for a symbol with 24/7 availability
    
    Query Parameters:
    - timeframe: 1Min, 5Min, 15Min, 30Min, 1Hour, 4Hour, 1Day, 1Week (default: 1Day)
    - start_date: Start date (YYYY-MM-DD or ISO format)
    - end_date: End date (YYYY-MM-DD or ISO format)
    - limit: Maximum number of bars (default: 1000)
    - use_cache: Whether to use cached data (default: true)
    """
    try:
        # Parse parameters
        timeframe = request.args.get('timeframe', '1Day')
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        limit = int(request.args.get('limit', 1000))
        use_cache = request.args.get('use_cache', 'true').lower() == 'true'
        
        # Parse dates
        end_date = datetime.now()
        if end_date_str:
            try:
                end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
            except:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        
        start_date = end_date - timedelta(days=30)  # Default 30 days
        if start_date_str:
            try:
                start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
            except:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        
        # Get historical service
        hist_service = get_historical_data_service()
        
        # Check if we should use hybrid data (live + cached)
        if use_cache:
            data = hist_service.get_hybrid_data(
                symbol=symbol.upper(),
                timeframe=timeframe,
                lookback_days=(end_date - start_date).days
            )
        else:
            data = hist_service.fetch_historical_data(
                symbol=symbol.upper(),
                timeframe=timeframe,
                start=start_date,
                end=end_date,
                limit=limit
            )
        
        if data.empty:
            return jsonify({
                'error': f'No data available for {symbol}',
                'symbol': symbol,
                'timeframe': timeframe,
                'requested_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                }
            }), 404
        
        # Convert to JSON-friendly format
        data_dict = {
            'symbol': symbol.upper(),
            'timeframe': timeframe,
            'data_source': 'live' if hist_service.api.get_clock().is_open else 'historical',
            'total_bars': len(data),
            'date_range': {
                'start': data.index.min().isoformat(),
                'end': data.index.max().isoformat()
            },
            'bars': []
        }
        
        # Convert DataFrame to list of dictionaries
        for timestamp, row in data.iterrows():
            bar = {
                'timestamp': timestamp.isoformat(),
                'open': float(row.get('open', 0)),
                'high': float(row.get('high', 0)),
                'low': float(row.get('low', 0)),
                'close': float(row.get('close', 0)),
                'volume': int(row.get('volume', 0))
            }
            
            # Add additional fields if available
            if 'vwap' in row:
                bar['vwap'] = float(row['vwap'])
            if 'trade_count' in row:
                bar['trade_count'] = int(row['trade_count'])
            
            data_dict['bars'].append(bar)
        
        return jsonify(data_dict)
    
    except Exception as e:
        logger.error(f"Historical data error for {symbol}: {e}")
        return jsonify({
            'error': f'Failed to fetch historical data: {str(e)}',
            'symbol': symbol
        }), 500


@epic2_bp.route('/historical/<symbol>/range', methods=['GET'])
@async_route
async def get_historical_data_range(symbol):
    """
    Get historical data for a specific date range
    Optimized for large date ranges with pagination
    """
    try:
        # Parse parameters
        timeframe = request.args.get('timeframe', '1Day')
        start_date = datetime.fromisoformat(request.args.get('start_date'))
        end_date = datetime.fromisoformat(request.args.get('end_date'))
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 1000))
        
        # Calculate pagination
        total_days = (end_date - start_date).days
        offset = (page - 1) * page_size
        
        # Adjust date range for pagination
        adjusted_start = start_date + timedelta(days=offset)
        adjusted_end = min(adjusted_start + timedelta(days=page_size), end_date)
        
        hist_service = get_historical_data_service()
        data = hist_service.fetch_historical_data(
            symbol=symbol.upper(),
            timeframe=timeframe,
            start=adjusted_start,
            end=adjusted_end
        )
        
        # Pagination info
        total_pages = (total_days + page_size - 1) // page_size
        
        result = {
            'symbol': symbol.upper(),
            'timeframe': timeframe,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_pages': total_pages,
                'has_next': page < total_pages,
                'has_previous': page > 1
            },
            'data': data.to_dict('records') if not data.empty else []
        }
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Historical range error: {e}")
        return jsonify({'error': str(e)}), 500


@epic2_bp.route('/availability/<symbol>', methods=['GET'])
def get_data_availability(symbol):
    """Get data availability information for a symbol"""
    try:
        timeframe = request.args.get('timeframe', '1Day')
        
        hist_service = get_historical_data_service()
        stats = hist_service.get_data_stats(symbol.upper())
        
        # Check market status
        clock = hist_service.api.get_clock()
        
        availability = {
            'symbol': symbol.upper(),
            'timeframe': timeframe,
            'available_24_7': True,
            'market_open': clock.is_open,
            'data_source': 'live' if clock.is_open else 'historical',
            'coverage': stats,
            'next_market_open': clock.next_open.isoformat() if hasattr(clock, 'next_open') else None,
            'next_market_close': clock.next_close.isoformat() if hasattr(clock, 'next_close') else None
        }
        
        return jsonify(availability)
    
    except Exception as e:
        logger.error(f"Availability check error: {e}")
        return jsonify({'error': str(e)}), 500


@epic2_bp.route('/backtest/run', methods=['POST'])
@async_route
async def run_backtest():
    """
    Run a comprehensive backtest
    
    Request Body:
    {
        "strategy": "stochrsi",
        "symbols": ["AAPL", "MSFT"],
        "start_date": "2023-01-01",
        "end_date": "2024-01-01",
        "timeframe": "1Day",
        "config": {
            "initial_capital": 100000,
            "commission_rate": 0.001,
            "position_size": 0.2
        }
    }
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['strategy', 'symbols', 'start_date', 'end_date']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Parse dates
        start_date = datetime.fromisoformat(data['start_date'])
        end_date = datetime.fromisoformat(data['end_date'])
        
        # Get strategy instance
        strategy_name = data['strategy'].lower()
        if strategy_name == 'stochrsi':
            strategy = StochRSIStrategy()
        else:
            return jsonify({'error': f'Unknown strategy: {strategy_name}'}), 400
        
        # Create backtest config
        config_data = data.get('config', {})
        config = BacktestConfig(
            initial_capital=config_data.get('initial_capital', 100000),
            commission_rate=config_data.get('commission_rate', 0.001),
            position_size=config_data.get('position_size', 0.2),
            max_positions=config_data.get('max_positions', 5),
            stop_loss_pct=config_data.get('stop_loss_pct', 0.02),
            take_profit_pct=config_data.get('take_profit_pct', 0.06)
        )
        
        # Run backtest
        engine = get_backtest_engine(config)
        results = await engine.run_backtest(
            strategy=strategy,
            symbols=data['symbols'],
            start_date=start_date,
            end_date=end_date,
            timeframe=data.get('timeframe', '1Day')
        )
        
        # Convert results to JSON-serializable format
        json_results = {
            'backtest_id': f"bt_{int(datetime.now().timestamp())}",
            'strategy': results['strategy'],
            'symbols': results['symbols'],
            'period': {
                'start': results['period']['start'].isoformat(),
                'end': results['period']['end'].isoformat()
            },
            'timeframe': results['timeframe'],
            'config': {
                'initial_capital': config.initial_capital,
                'commission_rate': config.commission_rate,
                'position_size': config.position_size,
                'max_positions': config.max_positions
            },
            'metrics': {
                'total_return': results['metrics'].total_return,
                'annualized_return': results['metrics'].annualized_return,
                'total_trades': results['metrics'].total_trades,
                'win_rate': results['metrics'].win_rate,
                'profit_factor': results['metrics'].profit_factor,
                'max_drawdown': results['metrics'].max_drawdown,
                'sharpe_ratio': results['metrics'].sharpe_ratio,
                'sortino_ratio': results['metrics'].sortino_ratio,
                'volatility': results['metrics'].volatility
            },
            'trade_count': len(results['trades']),
            'equity_curve_points': len(results['equity_curve'])
        }
        
        return jsonify(json_results)
    
    except Exception as e:
        logger.error(f"Backtest error: {e}")
        return jsonify({'error': f'Backtest failed: {str(e)}'}), 500


@epic2_bp.route('/backtest/results/<backtest_id>', methods=['GET'])
def get_backtest_results(backtest_id):
    """Get detailed backtest results"""
    # This would typically load from a database
    # For now, return a placeholder
    return jsonify({
        'error': 'Backtest result storage not yet implemented',
        'backtest_id': backtest_id,
        'note': 'Use /backtest/run endpoint for immediate results'
    }), 501


@epic2_bp.route('/export/<symbol>', methods=['GET'])
@async_route
async def export_historical_data(symbol):
    """
    Export historical data in various formats
    
    Query Parameters:
    - format: csv, json, excel (default: csv)
    - timeframe: Data timeframe
    - start_date, end_date: Date range
    """
    try:
        # Parse parameters
        export_format = request.args.get('format', 'csv').lower()
        timeframe = request.args.get('timeframe', '1Day')
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        
        # Parse dates
        end_date = datetime.now()
        if end_date_str:
            end_date = datetime.fromisoformat(end_date_str)
        
        start_date = end_date - timedelta(days=365)  # Default 1 year
        if start_date_str:
            start_date = datetime.fromisoformat(start_date_str)
        
        # Get data
        hist_service = get_historical_data_service()
        data = hist_service.get_hybrid_data(
            symbol=symbol.upper(),
            timeframe=timeframe,
            lookback_days=(end_date - start_date).days
        )
        
        if data.empty:
            return jsonify({'error': f'No data available for {symbol}'}), 404
        
        # Create file-like object
        output = io.BytesIO()
        
        # Export in requested format
        if export_format == 'csv':
            data.to_csv(output)
            mimetype = 'text/csv'
            filename = f"{symbol}_{timeframe}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"
        
        elif export_format == 'json':
            data.to_json(output, orient='index', date_format='iso')
            mimetype = 'application/json'
            filename = f"{symbol}_{timeframe}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.json"
        
        elif export_format == 'excel':
            data.to_excel(output, engine='openpyxl')
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            filename = f"{symbol}_{timeframe}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.xlsx"
        
        else:
            return jsonify({'error': f'Unsupported format: {export_format}'}), 400
        
        output.seek(0)
        
        return send_file(
            output,
            mimetype=mimetype,
            as_attachment=True,
            download_name=filename
        )
    
    except Exception as e:
        logger.error(f"Export error: {e}")
        return jsonify({'error': str(e)}), 500


@epic2_bp.route('/chart-data/<symbol>', methods=['GET'])
@async_route
async def get_chart_data(symbol):
    """
    Get optimized chart data for visualization
    Returns data in TradingView-compatible format
    """
    try:
        timeframe = request.args.get('timeframe', '1Day')
        limit = int(request.args.get('limit', 500))
        
        hist_service = get_historical_data_service()
        data = hist_service.get_hybrid_data(
            symbol=symbol.upper(),
            timeframe=timeframe,
            lookback_days=limit if timeframe == '1Day' else limit // 24
        )
        
        if data.empty:
            return jsonify({
                'symbol': symbol,
                'bars': [],
                'market_status': 'No data available'
            })
        
        # Format for charts (TradingView compatible)
        bars = []
        for timestamp, row in data.tail(limit).iterrows():
            bars.append({
                'time': int(timestamp.timestamp()),
                'open': float(row.get('open', 0)),
                'high': float(row.get('high', 0)),
                'low': float(row.get('low', 0)),
                'close': float(row.get('close', 0)),
                'volume': int(row.get('volume', 0))
            })
        
        # Market status
        clock = hist_service.api.get_clock()
        market_status = 'open' if clock.is_open else 'closed'
        
        return jsonify({
            'symbol': symbol.upper(),
            'timeframe': timeframe,
            'bars': bars,
            'market_status': market_status,
            'data_source': 'live' if clock.is_open else 'historical',
            'last_update': datetime.now().isoformat(),
            'total_bars': len(bars)
        })
    
    except Exception as e:
        logger.error(f"Chart data error: {e}")
        return jsonify({'error': str(e)}), 500


@epic2_bp.route('/performance/summary', methods=['GET'])
def get_performance_summary():
    """Get Epic 2 system performance summary"""
    try:
        hist_service = get_historical_data_service()
        stats = hist_service.get_data_stats()
        
        summary = {
            'epic2_status': 'operational',
            'data_coverage': {
                'total_records': stats.get('total_records', 0),
                'symbols_covered': stats.get('symbols', 0),
                'earliest_data': stats.get('earliest_data'),
                'latest_data': stats.get('latest_data'),
                'cache_size_mb': stats.get('cache_size_mb', 0)
            },
            'features_status': {
                'historical_data_service': 'active',
                'backtesting_engine': 'active',
                '24_7_chart_access': 'active',
                'data_export': 'active',
                'performance_analytics': 'active'
            },
            'capabilities': {
                'supports_weekend_access': True,
                'real_time_when_market_open': True,
                'multiple_timeframes': True,
                'advanced_backtesting': True,
                'export_formats': ['csv', 'json', 'excel']
            }
        }
        
        return jsonify(summary)
    
    except Exception as e:
        logger.error(f"Performance summary error: {e}")
        return jsonify({'error': str(e)}), 500


def register_epic2_routes(app):
    """Register Epic 2 routes with the Flask app"""
    app.register_blueprint(epic2_bp)
    logger.info("✅ Epic 2 routes registered successfully")


if __name__ == "__main__":
    # Test the routes
    from flask import Flask
    app = Flask(__name__)
    register_epic2_routes(app)
    print("Epic 2 routes registered for testing")