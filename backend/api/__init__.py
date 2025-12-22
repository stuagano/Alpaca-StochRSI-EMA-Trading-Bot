#!/usr/bin/env python3
"""
Flask Application Factory Pattern
Centralized Flask app configuration and initialization
"""

import logging
import os
from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO

# Initialize extensions
socketio = SocketIO(cors_allowed_origins="*")

def create_app(config_name='development'):
    """
    Application factory pattern for Flask

    Args:
        config_name: Configuration environment (development, production, testing)

    Returns:
        Flask application instance
    """
    # Load configuration first so we can use the configured static directory
    from .flask_config import config
    config_obj = config[config_name]

    # Create the Flask application with the frontend directory as its static root
    app = Flask(
        __name__,
        static_folder=config_obj.STATIC_FOLDER,
        static_url_path='/'
    )

    # Apply configuration
    app.config.from_object(config_obj)

    # Initialize extensions
    CORS(app)
    socketio.init_app(app, async_mode='threading')

    # Configure logging
    logging.basicConfig(
        level=app.config.get('LOG_LEVEL', logging.INFO),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Register blueprints
    from .blueprints import (
        dashboard_bp,
        trading_bp,
        api_bp,
        pnl_bp,
        websocket_bp,
        activity_bp
    )

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(trading_bp, url_prefix='/api/v1/trading')
    app.register_blueprint(api_bp, url_prefix='/api/v1')
    app.register_blueprint(pnl_bp, url_prefix='/api/v1/pnl')
    app.register_blueprint(activity_bp, url_prefix='/api/v1/activity')

    # Register WebSocket handlers
    from .blueprints.websocket_events import register_socketio_handlers
    register_socketio_handlers(socketio)

    # Register error handlers
    from .utils.error_handlers import register_error_handlers
    register_error_handlers(app)

    # Initialize services unless explicitly disabled (used for import smoke tests)
    if os.environ.get('DISABLE_BACKEND_SERVICE_INIT') != '1':
        with app.app_context():
            from .services import init_services
            init_services(app)

    @app.before_request
    def before_request():
        """Pre-request processing"""
        pass

    @app.after_request
    def after_request(response):
        """Post-request processing"""
        response.headers.add('X-Content-Type-Options', 'nosniff')
        response.headers.add('X-Frame-Options', 'DENY')
        return response

    return app
