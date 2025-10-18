#!/usr/bin/env python3
"""
Flask Application Runner
Main entry point for the refactored Flask application
"""

import argparse
import logging
import os

from . import create_app, socketio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main entry point for Flask application"""
    parser = argparse.ArgumentParser(description='Run the Trading Bot Flask Application')
    parser.add_argument('--host', default='localhost', help='Host to run on')
    parser.add_argument('--port', type=int, default=5001, help='Port to run on')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    parser.add_argument('--env', default='development',
                       choices=['development', 'production', 'testing'],
                       help='Environment to run in')

    args = parser.parse_args()

    # Create Flask app
    app = create_app(config_name=args.env)

    # Log startup information
    logger.info("=" * 60)
    logger.info("TRADING BOT DASHBOARD STARTING")
    logger.info("=" * 60)
    logger.info(f"Environment: {args.env}")
    logger.info(f"URL: http://{args.host}:{args.port}")
    logger.info(f"Debug Mode: {args.debug}")
    logger.info("=" * 60)

    # API endpoints
    logger.info("Available API Endpoints:")
    logger.info("  Dashboard:")
    logger.info(f"    GET  http://{args.host}:{args.port}/")
    logger.info(f"    GET  http://{args.host}:{args.port}/simple")
    logger.info(f"    GET  http://{args.host}:{args.port}/advanced")

    logger.info("  Core API:")
    logger.info(f"    GET  http://{args.host}:{args.port}/api/v1/status")
    logger.info(f"    GET  http://{args.host}:{args.port}/api/v1/account")
    logger.info(f"    GET  http://{args.host}:{args.port}/api/v1/positions")
    logger.info(f"    GET  http://{args.host}:{args.port}/api/v1/signals")
    logger.info(f"    GET  http://{args.host}:{args.port}/api/v1/orders")

    logger.info("  Trading:")
    logger.info(f"    POST http://{args.host}:{args.port}/api/v1/trading/start")
    logger.info(f"    POST http://{args.host}:{args.port}/api/v1/trading/stop")
    logger.info(f"    POST http://{args.host}:{args.port}/api/v1/trading/buy")
    logger.info(f"    POST http://{args.host}:{args.port}/api/v1/trading/sell")

    logger.info("  P&L:")
    logger.info(f"    GET  http://{args.host}:{args.port}/api/v1/pnl/current")
    logger.info(f"    GET  http://{args.host}:{args.port}/api/v1/pnl/history")
    logger.info(f"    GET  http://{args.host}:{args.port}/api/v1/pnl/chart-data")
    logger.info(f"    GET  http://{args.host}:{args.port}/api/v1/pnl/statistics")
    logger.info(f"    GET  http://{args.host}:{args.port}/api/v1/pnl/export")
    logger.info("=" * 60)

    # Run with SocketIO if available, otherwise standard Flask
    try:
        socketio.run(app, host=args.host, port=args.port, debug=args.debug)
    except:
        app.run(host=args.host, port=args.port, debug=args.debug)

if __name__ == '__main__':
    main()
