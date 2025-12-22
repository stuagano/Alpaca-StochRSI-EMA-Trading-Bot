"""
Activity API Blueprint
Provides endpoints for bot activity feed and scanner status
"""

from flask import Blueprint, jsonify, request

from backend.api.services.activity_service import get_activity_service

activity_bp = Blueprint('activity', __name__)


@activity_bp.route('/feed')
def get_activity_feed():
    """Get recent bot activity entries"""
    try:
        service = get_activity_service()
        limit = int(request.args.get('limit', 50))
        limit = min(limit, 200)  # Cap at 200

        activity = service.get_recent_activity(limit=limit)

        return jsonify({
            'activity': activity,
            'count': len(activity)
        })
    except Exception as e:
        return jsonify({
            'error': str(e),
            'activity': []
        }), 500


@activity_bp.route('/signals')
def get_signal_cache():
    """Get cached signals for all symbols"""
    try:
        service = get_activity_service()
        signals = service.get_signal_cache()

        # Format for frontend
        formatted = []
        for symbol, data in signals.items():
            formatted.append({
                'symbol': symbol,
                **data
            })

        # Sort by timestamp descending
        formatted.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        return jsonify({
            'signals': formatted,
            'count': len(formatted)
        })
    except Exception as e:
        return jsonify({
            'error': str(e),
            'signals': []
        }), 500


@activity_bp.route('/scanner')
def get_scanner_status():
    """Get scanner statistics"""
    try:
        service = get_activity_service()
        stats = service.get_scanner_stats()

        return jsonify({
            'status': 'active',
            **stats
        })
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500


@activity_bp.route('/summary')
def get_activity_summary():
    """Get combined activity summary for dashboard"""
    try:
        service = get_activity_service()

        return jsonify({
            'activity': service.get_recent_activity(limit=30),
            'signals': list(service.get_signal_cache().values()),
            'scanner': service.get_scanner_stats()
        })
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500
