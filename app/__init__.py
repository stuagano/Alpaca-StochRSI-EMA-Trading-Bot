"""
Modular Flask Application Factory
Creates organized, maintainable Flask application structure
"""

from flask import Flask
from flask_cors import CORS
import logging
from utils.secure_config_manager import get_secure_config
from services.redis_cache_service import get_redis_cache

logger = logging.getLogger(__name__)

def create_app(config_name='production'):
    """Application factory function"""
    app = Flask(__name__)
    
    # Load configuration
    config = get_secure_config()
    flask_config = config.get_flask_config()
    
    app.config.update(flask_config)
    
    # Initialize CORS
    CORS(app, origins=["*"])
    
    # Initialize cache
    app.cache = get_redis_cache()
    
    # Register blueprints
    from app.api import api_bp
    from app.trading import trading_bp
    from app.websocket import websocket_bp
    from app.dashboard import dashboard_bp
    
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(trading_bp, url_prefix='/trading')
    app.register_blueprint(websocket_bp, url_prefix='/ws')
    app.register_blueprint(dashboard_bp, url_prefix='/')
    
    # Initialize error handlers
    from app.error_handlers import register_error_handlers
    register_error_handlers(app)
    
    # Initialize logging
    from utils.enhanced_logging_config import setup_enhanced_logging
    setup_enhanced_logging()
    
    logger.info(f"Flask application created with {config_name} configuration")
    
    return app