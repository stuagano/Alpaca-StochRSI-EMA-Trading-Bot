#!/usr/bin/env python3
"""
Frontend Service

Serves the web-based dashboard and user interface for the trading system.
Provides a React-based single-page application with real-time updates.

Features:
- Trading dashboard
- Real-time portfolio view
- Market data visualization
- Risk monitoring
- Configuration management
- Alert notifications
"""

import os
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Configuration - Use API Gateway for microservices architecture
API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://localhost:9000")
WEBSOCKET_URL = os.getenv("WEBSOCKET_URL", "ws://localhost:9000/ws")
TRAINING_SERVICE_URL = os.getenv("TRAINING_SERVICE_URL", "http://localhost:9011")

# FastAPI application
app = FastAPI(
    title="Trading Dashboard Frontend",
    description="Web-based trading system dashboard",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup templates - use absolute path to project templates
project_root = Path(__file__).parent.parent.parent.parent.parent  # Go up to project root
templates_dir = project_root / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

# Setup static files directory
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "service": "frontend",
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "api_gateway_url": API_GATEWAY_URL
    }

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main trading dashboard."""
    return templates.TemplateResponse("dashboard_content.html", get_unified_context(
        request, "dashboard", "Trading Dashboard", 
        "Real-time market data, positions, and automated trading with StochRSI and volume confirmation", "speedometer2",
        [
            {"url": "/trading", "label": "Place Order", "icon": "plus-circle", "class": "btn-primary"},
            {"url": "/portfolio", "label": "Portfolio", "icon": "briefcase", "class": "btn-secondary"}
        ]
    ))

@app.get("/portfolio", response_class=HTMLResponse)
async def portfolio(request: Request):
    """Portfolio management page."""
    return templates.TemplateResponse("unified_master_dashboard.html", get_unified_context(
        request, "portfolio", "Portfolio Management", 
        "Track positions, P&L, and portfolio performance across all your holdings", "briefcase",
        [
            {"url": "/analytics", "label": "Analytics", "icon": "bar-chart", "class": "btn-primary"},
            {"url": "/trading", "label": "New Trade", "icon": "plus", "class": "btn-secondary"}
        ]
    ))

@app.get("/trading", response_class=HTMLResponse)  
async def trading_page(request: Request):
    """Trading execution page."""
    return templates.TemplateResponse("unified_master_dashboard.html", get_unified_context(
        request, "trading", "Trading Execution", 
        "Execute trades, manage orders, and monitor real-time market conditions", "graph-up",
        [
            {"url": "/dashboard", "label": "Dashboard", "icon": "speedometer2", "class": "btn-secondary"},
            {"url": "/portfolio", "label": "Portfolio", "icon": "briefcase", "class": "btn-secondary"}
        ]
    ))

@app.get("/analytics", response_class=HTMLResponse)
async def analytics(request: Request):
    """Analytics and reporting page."""
    return templates.TemplateResponse("unified_master_dashboard.html", get_unified_context(
        request, "analytics", "Analytics & Reports", 
        "Performance metrics, strategy analysis, and comprehensive reporting", "bar-chart",
        [
            {"url": "/backtesting", "label": "Backtest", "icon": "clock-history", "class": "btn-primary"},
            {"url": "/dashboard", "label": "Dashboard", "icon": "speedometer2", "class": "btn-secondary"}
        ]
    ))

@app.get("/backtesting", response_class=HTMLResponse)
async def backtesting(request: Request):
    """Backtesting dashboard page."""
    return templates.TemplateResponse("unified_master_dashboard.html", get_unified_context(
        request, "backtesting", "Strategy Backtesting", 
        "Test trading strategies against historical data with comprehensive performance analysis", "clock-history",
        [
            {"url": "/training", "label": "AI Training", "icon": "mortarboard", "class": "btn-primary"},
            {"url": "/analytics", "label": "Analytics", "icon": "bar-chart", "class": "btn-secondary"}
        ]
    ))

@app.get("/config", response_class=HTMLResponse)
async def configuration(request: Request):
    """Configuration management page."""
    return templates.TemplateResponse("unified_master_dashboard.html", get_unified_context(
        request, "config", "System Configuration", 
        "Manage system settings, trading parameters, and service configurations", "gear",
        [
            {"url": "/monitoring", "label": "Monitoring", "icon": "activity", "class": "btn-primary"},
            {"url": "/dashboard", "label": "Dashboard", "icon": "speedometer2", "class": "btn-secondary"}
        ]
    ))

@app.get("/afterhours", response_class=HTMLResponse)
async def afterhours_page(request: Request):
    """After-hours trading experience page."""
    return templates.TemplateResponse("afterhours_dashboard.html", {
        "request": request,
        "current_page": "afterhours",
        "api_gateway_url": API_GATEWAY_URL,
        "training_service_url": TRAINING_SERVICE_URL
    })

@app.get("/futures", response_class=HTMLResponse)
async def futures_page(request: Request):
    """Futures and risk management dashboard."""
    return templates.TemplateResponse("futures_risk_dashboard.html", {
        "request": request,
        "current_page": "futures",
        "api_gateway_url": API_GATEWAY_URL,
        "training_service_url": TRAINING_SERVICE_URL
    })

@app.get("/monitoring", response_class=HTMLResponse)
async def monitoring(request: Request):
    """System monitoring page."""
    return templates.TemplateResponse("unified_master_dashboard.html", get_unified_context(
        request, "monitoring", "System Monitoring", 
        "Monitor system health, service status, and performance metrics across all components", "activity",
        [
            {"url": "/config", "label": "Configuration", "icon": "gear", "class": "btn-secondary"},
            {"url": "/dashboard", "label": "Dashboard", "icon": "speedometer2", "class": "btn-secondary"}
        ]
    ))

@app.get("/training", response_class=HTMLResponse)
async def training_dashboard(request: Request):
    """AI Training Dashboard with collaborative features."""
    return templates.TemplateResponse("unified_master_dashboard.html", get_unified_context(
        request, "training", "AI Training Platform", 
        "Collaborative human-AI trading strategy development with real-time analysis and learning scenarios", "mortarboard",
        [
            {"url": "/backtesting", "label": "Backtest", "icon": "clock-history", "class": "btn-primary"},
            {"url": "http://localhost:9011/docs", "label": "API Docs", "icon": "book", "class": "btn-secondary"}
        ]
    ))

@app.get("/navigation", response_class=HTMLResponse)
async def navigation_hub(request: Request):
    """Navigation hub for all services."""
    return templates.TemplateResponse("unified_master_dashboard.html", get_unified_context(
        request, "navigation", "Trading Platform Hub", 
        "Comprehensive access to all trading services and dashboards", "house-door",
        [
            {"url": "/dashboard", "label": "Dashboard", "icon": "speedometer2", "class": "btn-primary"},
            {"url": "/training", "label": "AI Training", "icon": "mortarboard", "class": "btn-secondary"}
        ]
    ))

# Unified template helper function
def get_unified_context(request: Request, page_name: str, page_title: str, page_description: str, page_icon: str, page_actions: list = None):
    """Generate unified context for all pages"""
    return {
        "request": request,
        "api_gateway_url": API_GATEWAY_URL,
        "websocket_url": WEBSOCKET_URL,
        "training_service_url": TRAINING_SERVICE_URL,
        "current_page": page_name,
        "page_title": page_title,
        "page_description": page_description,
        "page_icon": page_icon,
        "page_actions": page_actions or []
    }

# Redirect root to navigation hub for better UX
@app.get("/", response_class=HTMLResponse)
async def root_redirect(request: Request):
    """Main entry point - Navigation Hub."""
    return templates.TemplateResponse("navigation_content.html", get_unified_context(
        request, "navigation", "Trading Platform Hub", 
        "Comprehensive access to all trading services and dashboards", "house-door",
        [
            {"url": "/training", "label": "AI Training", "icon": "mortarboard", "class": "btn-primary"},
            {"url": "/dashboard", "label": "Dashboard", "icon": "speedometer2", "class": "btn-secondary"},
            {"url": "http://localhost:9011/docs", "label": "API Docs", "icon": "book", "class": "btn-secondary"}
        ]
    ))

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=9100,
        reload=True
    )