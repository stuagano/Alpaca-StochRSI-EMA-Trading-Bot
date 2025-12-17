#!/usr/bin/env python3
"""
API Blueprint
Core API endpoints for account, positions, and signals
"""

from flask import Blueprint, jsonify, current_app, request
from ..services.trading_service import TradingService
from ..utils.decorators import handle_errors, require_auth

api_bp = Blueprint('api', __name__)

@api_bp.route('/status')
@handle_errors
def api_status():
    """Get system status"""
    cfg = current_app.config['TRADING_CONFIG']
    service = current_app.trading_service

    try:
        status = service.get_system_status()
        services_state = status.get('services', {})
        last_update = status.get('last_update')
        market_status = status.get('market_status')
    except Exception as exc:  # pragma: no cover - defensive fallback
        current_app.logger.error("Status check failed: %s", exc, exc_info=True)
        services_state = {}
        last_update = None
        market_status = 'UNKNOWN'

    return jsonify({
        'status': 'running',
        'last_update': last_update,
        'market_status': market_status,
        'services': services_state,
        'trading_mode': getattr(cfg, 'market_type', 'crypto')
    })

@api_bp.route('/account')
@handle_errors
def api_account():
    """Get account information"""
    service = current_app.trading_service
    account_data = service.get_account_data()
    return jsonify(account_data)

@api_bp.route('/positions')
@handle_errors
def api_positions():
    """Get current crypto positions"""
    service = current_app.trading_service
    positions = service.get_positions()
    return jsonify(positions)

@api_bp.route('/signals')
@handle_errors
def api_signals():
    """Get current trading signals"""
    service = current_app.trading_service
    config = current_app.config['TRADING_CONFIG']
    symbols = request.args.getlist('symbols')

    if not symbols:
        symbols_param = request.args.get('symbols')
        if symbols_param:
            symbols = [symbol.strip() for symbol in symbols_param.split(',') if symbol.strip()]

    # If no symbols provided, pass None to service to let it resolve via config/scanner
    if not symbols:
        symbols = None

    signals = service.calculate_signals(symbols)
    return jsonify(signals)

@api_bp.route('/orders')
@handle_errors
def api_orders():
    """Get recent orders"""
    service = current_app.trading_service
    status = request.args.get('status', 'all')
    limit = int(request.args.get('limit', 50))

    orders = service.get_orders(status=status, limit=limit)
    return jsonify(orders)

@api_bp.route('/symbols')
@handle_errors
def api_symbols():
    """Get tracked symbols"""
    config = current_app.config['TRADING_CONFIG']

    symbols = list(getattr(config, 'symbols', []) or [])
    mode = getattr(config, 'market_type', 'crypto')

    return jsonify({
        'symbols': symbols,
        'mode': mode or 'crypto'
    })

@api_bp.route('/bot/status')
@handle_errors
def api_bot_status():
    """Get detailed trading bot status including active positions with P&L"""
    service = current_app.trading_service

    if service.trading_bot and hasattr(service.trading_bot, 'get_status'):
        bot_status = service.trading_bot.get_status()
        return jsonify({
            'status': 'running' if bot_status.get('is_running') else 'stopped',
            'bot': bot_status
        })
    else:
        return jsonify({
            'status': 'not_started',
            'message': 'Trading bot has not been started yet',
            'bot': None
        })

@api_bp.route('/bot/thresholds', methods=['GET', 'POST'])
@handle_errors
def api_bot_thresholds():
    """Get or update bot trading thresholds"""
    service = current_app.trading_service

    if not service.trading_bot:
        return jsonify({'error': 'Bot not started'}), 400

    if request.method == 'GET':
        return jsonify({
            'stop_loss_pct': getattr(service.trading_bot, 'stop_loss_pct', 0.015),
            'take_profit_pct': getattr(service.trading_bot, 'take_profit_pct', 0.02),
            'trailing_stop_pct': getattr(service.trading_bot, 'trailing_stop_pct', 0.01),
            'max_hold_time_seconds': getattr(service.trading_bot, 'max_hold_time_seconds', 3600)
        })
    else:
        data = request.get_json() or {}
        if 'stop_loss_pct' in data:
            service.trading_bot.stop_loss_pct = float(data['stop_loss_pct'])
        if 'take_profit_pct' in data:
            service.trading_bot.take_profit_pct = float(data['take_profit_pct'])
        if 'trailing_stop_pct' in data:
            service.trading_bot.trailing_stop_pct = float(data['trailing_stop_pct'])
        if 'max_hold_time_seconds' in data:
            service.trading_bot.max_hold_time_seconds = int(data['max_hold_time_seconds'])

        # Also update position thresholds for existing positions
        if hasattr(service.trading_bot, 'active_positions'):
            for symbol, pos in service.trading_bot.active_positions.items():
                entry = pos['entry_price']
                side = pos['side']
                if 'stop_loss_pct' in data:
                    pos['stop_price'] = entry * (1 - service.trading_bot.stop_loss_pct) if side == 'buy' else entry * (1 + service.trading_bot.stop_loss_pct)
                if 'take_profit_pct' in data:
                    pos['target_price'] = entry * (1 + service.trading_bot.take_profit_pct) if side == 'buy' else entry * (1 - service.trading_bot.take_profit_pct)

        return jsonify({
            'message': 'Thresholds updated',
            'stop_loss_pct': service.trading_bot.stop_loss_pct,
            'take_profit_pct': service.trading_bot.take_profit_pct,
            'trailing_stop_pct': service.trading_bot.trailing_stop_pct,
            'max_hold_time_seconds': service.trading_bot.max_hold_time_seconds
        })

@api_bp.route('/bot/liquidate/<symbol>', methods=['POST'])
@handle_errors
def api_liquidate_position(symbol):
    """Force liquidate a specific position"""
    service = current_app.trading_service

    result = service.close_position(symbol)
    if result:
        # Also remove from bot's active_positions if present
        if service.trading_bot and hasattr(service.trading_bot, 'active_positions'):
            if symbol in service.trading_bot.active_positions:
                del service.trading_bot.active_positions[symbol]
        return jsonify({'message': f'Position {symbol} closed', 'order': result})
    else:
        return jsonify({'error': f'Failed to close position {symbol}'}), 400

@api_bp.route('/bot/liquidate-all', methods=['POST'])
@handle_errors
def api_liquidate_all():
    """Force liquidate all positions"""
    service = current_app.trading_service

    results = service.close_all_positions()

    # Clear bot's active_positions
    if service.trading_bot and hasattr(service.trading_bot, 'active_positions'):
        service.trading_bot.active_positions.clear()

    return jsonify({
        'message': f'Closed {len(results)} positions',
        'orders': results
    })

@api_bp.route('/bot/reset-daily', methods=['POST'])
@handle_errors
def api_reset_daily_limits():
    """Reset daily trading limits to allow trading to resume"""
    service = current_app.trading_service

    if not service.trading_bot:
        return jsonify({'error': 'Bot not started'}), 400

    if hasattr(service.trading_bot, 'reset_daily_limits'):
        result = service.trading_bot.reset_daily_limits()
        return jsonify({
            'message': 'Daily limits reset successfully',
            'result': result
        })
    else:
        return jsonify({'error': 'Bot does not support daily limit reset'}), 400

@api_bp.route('/bot/indicators/<symbol>')
@handle_errors
def api_get_indicators(symbol):
    """Get current technical indicators for a symbol"""
    service = current_app.trading_service

    if not service.trading_bot or not hasattr(service.trading_bot, 'scanner'):
        return jsonify({'error': 'Bot not running'}), 400

    indicators = service.trading_bot.scanner.get_indicators(symbol)
    if not indicators:
        return jsonify({'error': f'No data available for {symbol}'}), 404

    return jsonify({
        'symbol': symbol,
        'indicators': indicators
    })
