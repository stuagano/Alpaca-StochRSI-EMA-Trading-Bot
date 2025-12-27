#!/usr/bin/env python3
"""
API Blueprint
Core API endpoints for account, positions, and signals
"""

from flask import Blueprint, jsonify, current_app, request
from ..utils.decorators import handle_errors, require_auth

api_bp = Blueprint('api', __name__)


def _get_trading_service():
    """Get trading service with null-safety check."""
    service = current_app.trading_service
    if not service:
        return None
    return service


def _service_unavailable_response():
    """Standard response when trading service is unavailable."""
    return jsonify({'error': 'Trading service not initialized'}), 503

@api_bp.route('/status')
@handle_errors
def api_status():
    """Get system status"""
    cfg = current_app.config['TRADING_CONFIG']
    service = _get_trading_service()

    services_state = {}
    last_update = None
    market_status = 'UNKNOWN'

    if service:
        try:
            status = service.get_system_status()
            services_state = status.get('services', {})
            last_update = status.get('last_update')
            market_status = status.get('market_status')
        except Exception as exc:  # pragma: no cover - defensive fallback
            current_app.logger.error("Status check failed: %s", exc, exc_info=True)

    return jsonify({
        'status': 'running' if service else 'degraded',
        'last_update': last_update,
        'market_status': market_status,
        'services': services_state,
        'trading_mode': getattr(cfg, 'market_type', 'crypto')
    })

@api_bp.route('/account')
@handle_errors
def api_account():
    """Get account information"""
    service = _get_trading_service()
    if not service:
        return _service_unavailable_response()

    account_data = service.get_account_data()
    return jsonify(account_data)

@api_bp.route('/positions')
@handle_errors
def api_positions():
    """Get current crypto positions"""
    service = _get_trading_service()
    if not service:
        return _service_unavailable_response()

    positions = service.get_positions()
    return jsonify(positions)

@api_bp.route('/signals')
@handle_errors
def api_signals():
    """Get current trading signals"""
    service = _get_trading_service()
    if not service:
        return _service_unavailable_response()

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

@api_bp.route('/signals/analysis')
@handle_errors
def api_signals_analysis():
    """Get detailed signal analysis with scoring breakdown for all symbols"""
    from datetime import datetime
    from core.service_registry import get_service_registry

    service = _get_trading_service()
    if not service:
        return _service_unavailable_response()

    # Get scanner from registry or trading bot
    scanner = None
    try:
        registry = get_service_registry()
        scanner = registry.get('scanner_service')
    except (ValueError, KeyError):
        if service.trading_bot:
            if hasattr(service.trading_bot, 'scanner'):
                scanner = service.trading_bot.scanner
            elif hasattr(service.trading_bot, 'strategy') and hasattr(service.trading_bot.strategy, 'scanner'):
                scanner = service.trading_bot.strategy.scanner

    if not scanner:
        return jsonify({'error': 'Scanner not available', 'signals': []}), 200

    analysis = []
    min_score = 3  # Same as in strategy

    symbols = list(scanner.price_data.keys()) if hasattr(scanner, 'price_data') else []

    for symbol in symbols:
        try:
            indicators = scanner.get_indicators(symbol) if hasattr(scanner, 'get_indicators') else {}
            if not indicators:
                continue

            prices = scanner.price_data.get(symbol, [])
            volumes = scanner.volume_data.get(symbol, [])
            current_price = prices[-1] if prices else 0

            # Calculate scores (matching strategy logic)
            rsi = indicators.get('rsi', 50)
            macd_hist = indicators.get('macd_histogram', 0)
            stoch_k = indicators.get('stoch_k', 50)
            ema_cross = indicators.get('ema_cross', 'neutral')

            # Volume surge check
            volume_surge = False
            if len(volumes) >= 20:
                avg_vol = sum(volumes[-20:]) / 20
                volume_surge = volumes[-1] > avg_vol * 1.5 if avg_vol > 0 else False

            # Calculate buy score
            buy_score = 0
            buy_reasons = []

            if rsi < 25:
                buy_score += 3
                buy_reasons.append(f"RSI very low ({rsi:.1f})")
            elif rsi < 30:
                buy_score += 2
                buy_reasons.append(f"RSI oversold ({rsi:.1f})")
            elif rsi < 35:
                buy_score += 1
                buy_reasons.append(f"RSI low ({rsi:.1f})")

            if macd_hist > 0:
                buy_score += 1
                buy_reasons.append("MACD positive")

            if stoch_k < 20:
                buy_score += 3
                buy_reasons.append(f"StochRSI very low ({stoch_k:.1f})")
            elif stoch_k < 30:
                buy_score += 2
                buy_reasons.append(f"StochRSI oversold ({stoch_k:.1f})")

            if ema_cross == 'bullish':
                buy_score += 2
                buy_reasons.append("EMA bullish cross")

            if volume_surge:
                buy_score += 1
                buy_reasons.append("Volume surge")

            # Calculate sell score
            sell_score = 0
            sell_reasons = []

            if rsi > 75:
                sell_score += 3
                sell_reasons.append(f"RSI very high ({rsi:.1f})")
            elif rsi > 70:
                sell_score += 2
                sell_reasons.append(f"RSI overbought ({rsi:.1f})")
            elif rsi > 65:
                sell_score += 1
                sell_reasons.append(f"RSI high ({rsi:.1f})")

            if macd_hist < 0:
                sell_score += 1
                sell_reasons.append("MACD negative")

            if stoch_k > 80:
                sell_score += 3
                sell_reasons.append(f"StochRSI very high ({stoch_k:.1f})")
            elif stoch_k > 70:
                sell_score += 2
                sell_reasons.append(f"StochRSI overbought ({stoch_k:.1f})")

            if ema_cross == 'bearish':
                sell_score += 2
                sell_reasons.append("EMA bearish cross")

            if volume_surge:
                sell_score += 1
                sell_reasons.append("Volume confirmation")

            # Determine action
            if buy_score >= min_score and buy_score > sell_score:
                action = 'BUY'
                reasons = buy_reasons
            elif sell_score >= min_score and sell_score > buy_score:
                action = 'SELL'
                reasons = sell_reasons
            else:
                action = 'HOLD'
                reasons = [f"Scores too weak/tied (buy={buy_score}, sell={sell_score}, need {min_score})"]

            analysis.append({
                'symbol': symbol,
                'action': action,
                'buy_score': buy_score,
                'sell_score': sell_score,
                'min_required': min_score,
                'price': round(current_price, 4),
                'indicators': {
                    'rsi': round(rsi, 2),
                    'stoch_k': round(stoch_k, 2),
                    'macd_histogram': round(macd_hist, 4),
                    'ema_cross': ema_cross,
                    'volume_surge': volume_surge
                },
                'reasons': reasons,
                'would_trade': action in ('BUY', 'SELL'),
                'timestamp': datetime.now().isoformat()
            })

        except Exception as e:
            current_app.logger.error(f"Error analyzing {symbol}: {e}")

    # Sort by highest combined score
    analysis.sort(key=lambda x: max(x['buy_score'], x['sell_score']), reverse=True)

    return jsonify({
        'count': len(analysis),
        'min_score_required': min_score,
        'timestamp': datetime.now().isoformat(),
        'signals': analysis
    })


@api_bp.route('/orders')
@handle_errors
def api_orders():
    """Get recent orders"""
    service = _get_trading_service()
    if not service:
        return _service_unavailable_response()

    order_status = request.args.get('status', 'all')
    limit = int(request.args.get('limit', 50))

    orders = service.get_orders(status=order_status, limit=limit)
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
    service = _get_trading_service()
    if not service:
        return jsonify({
            'status': 'unavailable',
            'message': 'Trading service not initialized',
            'bot': None
        }), 503

    if service.trading_bot and hasattr(service.trading_bot, 'get_status'):
        bot_status = service.trading_bot.get_status()
        current_app.logger.debug(
            "Bot status: running=%s, positions=%d, trades=%d",
            bot_status.get('is_running'),
            len(bot_status.get('positions', [])),
            bot_status.get('total_trades', 0)
        )
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
    service = _get_trading_service()
    if not service:
        return _service_unavailable_response()

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
    service = _get_trading_service()
    if not service:
        return _service_unavailable_response()

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
    service = _get_trading_service()
    if not service:
        return _service_unavailable_response()

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
    service = _get_trading_service()
    if not service:
        return _service_unavailable_response()

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
    service = _get_trading_service()
    if not service:
        return _service_unavailable_response()

    if not service.trading_bot or not hasattr(service.trading_bot, 'scanner'):
        return jsonify({'error': 'Bot not running'}), 400

    indicators = service.trading_bot.scanner.get_indicators(symbol)
    if not indicators:
        return jsonify({'error': f'No data available for {symbol}'}), 404

    return jsonify({
        'symbol': symbol,
        'indicators': indicators
    })
