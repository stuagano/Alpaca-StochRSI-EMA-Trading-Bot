#!/usr/bin/env python3
"""
Error Handlers
Global error handlers for Flask application
"""

import logging
from flask import jsonify
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)

def register_error_handlers(app):
    """
    Register error handlers with Flask app

    Args:
        app: Flask application instance
    """

    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors"""
        return jsonify({
            'error': 'Not Found',
            'message': 'The requested resource was not found'
        }), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        """Handle 405 errors"""
        return jsonify({
            'error': 'Method Not Allowed',
            'message': 'The method is not allowed for the requested URL'
        }), 405

    @app.errorhandler(400)
    def bad_request(error):
        """Handle 400 errors"""
        return jsonify({
            'error': 'Bad Request',
            'message': 'The request could not be understood or was missing required parameters'
        }), 400

    @app.errorhandler(401)
    def unauthorized(error):
        """Handle 401 errors"""
        return jsonify({
            'error': 'Unauthorized',
            'message': 'Authentication is required and has failed or has not been provided'
        }), 401

    @app.errorhandler(403)
    def forbidden(error):
        """Handle 403 errors"""
        return jsonify({
            'error': 'Forbidden',
            'message': 'You do not have permission to access this resource'
        }), 403

    @app.errorhandler(429)
    def too_many_requests(error):
        """Handle 429 errors"""
        return jsonify({
            'error': 'Too Many Requests',
            'message': 'You have exceeded the rate limit'
        }), 429

    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors"""
        logger.error(f"Internal server error: {error}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred'
        }), 500

    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        """Handle all HTTP exceptions"""
        return jsonify({
            'error': error.name,
            'message': error.description
        }), error.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        """Handle unexpected exceptions"""
        logger.error(f"Unexpected error: {error}", exc_info=True)
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred'
        }), 500