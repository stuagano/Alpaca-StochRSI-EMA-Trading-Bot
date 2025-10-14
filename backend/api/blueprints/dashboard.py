#!/usr/bin/env python3
"""
Dashboard Blueprint
Consolidated dashboard routes from multiple dashboard files
"""

from flask import Blueprint, render_template, send_from_directory, current_app
from pathlib import Path

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
def index():
    """Main dashboard view - consolidated version"""
    return send_from_directory(current_app.config['STATIC_FOLDER'], 'dashboard.html')


@dashboard_bp.route('/dashboard.html')
def dashboard_alias():
    """Alias for canonical dashboard."""
    return send_from_directory(current_app.config['STATIC_FOLDER'], 'dashboard.html')

@dashboard_bp.route('/simple')
def simple_dashboard():
    """Simplified dashboard view (from simple_pnl_dashboard.py)"""
    return send_from_directory(current_app.config['STATIC_FOLDER'], 'simple.html')

@dashboard_bp.route('/advanced')
def advanced_dashboard():
    """Advanced dashboard view with all features"""
    return send_from_directory(current_app.config['STATIC_FOLDER'], 'advanced.html')

@dashboard_bp.route('/frontend/<path:filename>')
def frontend_files(filename):
    """Serve frontend static files"""
    return send_from_directory(current_app.config['STATIC_FOLDER'], filename)
