"""Health check and resilience status API endpoints."""

from flask import Blueprint, jsonify, current_app
from core.service_registry import get_service_registry
from core.resilience import get_resilience_status

health_bp = Blueprint('health', __name__, url_prefix='/api/v1/health')


@health_bp.route('/', methods=['GET'])
@health_bp.route('', methods=['GET'])
def health_check():
    """
    Basic health check endpoint.

    Returns:
        JSON with health status
    """
    registry = get_service_registry()
    health_report = registry.get_health_report()

    # Determine overall health
    if health_report['failed_services'] > 0:
        status = 'unhealthy'
        http_code = 503
    elif health_report['degraded_services'] > 0:
        status = 'degraded'
        http_code = 200
    else:
        status = 'healthy'
        http_code = 200

    return jsonify({
        'status': status,
        'services': health_report,
    }), http_code


@health_bp.route('/ready', methods=['GET'])
def readiness_check():
    """
    Readiness probe for Kubernetes/orchestrator.

    Returns:
        200 if ready to serve traffic, 503 otherwise
    """
    registry = get_service_registry()

    # Check critical services
    critical_services = ['alpaca_client', 'trading_service', 'scanner_service']
    missing = []

    for service in critical_services:
        if not registry.has(service):
            missing.append(service)

    if missing:
        return jsonify({
            'ready': False,
            'missing_services': missing,
        }), 503

    return jsonify({
        'ready': True,
        'services': critical_services,
    }), 200


@health_bp.route('/live', methods=['GET'])
def liveness_check():
    """
    Liveness probe - just confirms the process is running.

    Returns:
        200 always (if reachable, we're alive)
    """
    return jsonify({
        'alive': True,
    }), 200


@health_bp.route('/resilience', methods=['GET'])
def resilience_status():
    """
    Get detailed resilience system status.

    Returns:
        JSON with circuit breaker and rate limiter states
    """
    status = get_resilience_status()

    # Add resilient client status if available
    registry = get_service_registry()
    resilient_client = registry.get_optional('resilient_client')
    if resilient_client:
        status['resilient_client'] = resilient_client.get_status()
        status['client_healthy'] = resilient_client.is_healthy()

    # Add position reconciler status
    reconciler = registry.get_optional('position_reconciler')
    if reconciler:
        status['position_reconciler'] = reconciler.get_status()

    return jsonify(status), 200


@health_bp.route('/services', methods=['GET'])
def services_status():
    """
    Get detailed status of all registered services.

    Returns:
        JSON with service states and health information
    """
    registry = get_service_registry()
    return jsonify(registry.get_health_report()), 200


@health_bp.route('/circuit-breaker/reset', methods=['POST'])
def reset_circuit_breaker():
    """
    Manually reset the circuit breaker (emergency use only).

    Returns:
        JSON confirmation
    """
    registry = get_service_registry()
    resilient_client = registry.get_optional('resilient_client')

    if not resilient_client:
        return jsonify({
            'success': False,
            'error': 'Resilient client not available',
        }), 404

    resilient_client.reset_circuit_breaker()

    return jsonify({
        'success': True,
        'message': 'Circuit breaker reset',
        'status': resilient_client.get_status(),
    }), 200
