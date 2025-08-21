#!/usr/bin/env python3
"""
Enhanced Trading Dashboard Launcher
Starts the Flask app with enhanced TradingView Lightweight Charts
"""

import os
import sys
import logging
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set environment variables for testing
os.environ['FLASK_ENV'] = 'development'
os.environ['FLASK_DEBUG'] = '1'

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    """Main entry point for enhanced dashboard."""
    try:
        logger.info("🚀 Starting Enhanced Trading Dashboard...")
        
        # Import and configure Flask app
        from flask_app import app, socketio
        
        # Print available routes
        logger.info("📋 Available routes:")
        logger.info("  Main Dashboard: http://localhost:9765/")
        logger.info("  Enhanced Dashboard: http://localhost:9765/enhanced")
        logger.info("  Test Charts: http://localhost:9765/test_enhanced")
        logger.info("  API v2 Routes: http://localhost:9765/api/v2/")
        
        # Start the application
        logger.info("🌐 Starting server on http://localhost:9765")
        socketio.run(
            app, 
            host='0.0.0.0', 
            port=9765,
            debug=True,
            use_reloader=False  # Disable reloader to prevent double startup
        )
        
    except KeyboardInterrupt:
        logger.info("🛑 Server stopped by user")
    except Exception as e:
        logger.error(f"❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()