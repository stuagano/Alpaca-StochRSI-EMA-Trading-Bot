"""
Core API routes
"""

from flask import jsonify, request, current_app
from . import api_bp
from utils.input_validator import InputValidator, ValidationError
from services.redis_cache_service import get_trading_cache, cache_result
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@api_bp.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '2.0.0',
        'features': {
            'redis_cache': current_app.cache.client is not None,
            'secure_config': True,
            'input_validation': True,
            'modular_architecture': True
        }
    })

@api_bp.route('/status')
def system_status():
    """System status with performance metrics"""
    try:
        cache = get_trading_cache()
        cache_stats = cache.get_cache_summary()
        
        from utils.thread_manager import thread_manager
        thread_stats = thread_manager.get_thread_status()
        
        return jsonify({
            'success': True,
            'system': {
                'status': 'operational',
                'uptime': 'calculated_in_production',
                'threads': {
                    'active': len([t for t in thread_stats.values() if t['is_alive']]),
                    'total': len(thread_stats),
                    'details': thread_stats
                },
                'cache': cache_stats,
                'memory': 'monitoring_enabled'
            },
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        return jsonify({
            'success': False,
            'error': 'System status unavailable',
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@api_bp.route('/cache/stats')
def cache_statistics():
    """Get cache performance statistics"""
    try:
        cache = get_trading_cache()
        stats = cache.get_cache_summary()
        
        return jsonify({
            'success': True,
            'cache_stats': stats,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/cache/clear', methods=['POST'])
def clear_cache():
    """Clear cache data"""
    try:
        data = request.get_json() or {}
        category = data.get('category', 'all')
        
        cache = get_trading_cache()
        
        if category == 'all':
            result = cache.cache.flush_all()
        else:
            result = cache.cache.clear_category(category)
        
        return jsonify({
            'success': result,
            'category': category,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500