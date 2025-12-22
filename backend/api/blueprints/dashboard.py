#!/usr/bin/env python3
"""
Dashboard Blueprint
Consolidated dashboard routes from multiple dashboard files
"""

from flask import Blueprint, current_app, abort

dashboard_bp = Blueprint('dashboard', __name__)

_DASHBOARD_TEMPLATES = {
    'root': 'dashboard.html',
    'simple': 'dashboard.html',
    'advanced': 'dashboard.html',
}


def _serve_dashboard(template_key: str):
    """Serve the requested dashboard file from the static folder."""
    template_name = _DASHBOARD_TEMPLATES.get(template_key)
    if not template_name:
        abort(404)
    return current_app.send_static_file(template_name)


@dashboard_bp.route('/')
def index():
    """Main dashboard view - consolidated version"""
    return _serve_dashboard('root')


@dashboard_bp.route('/dashboard.html')
def dashboard_alias():
    """Alias for canonical dashboard."""
    return _serve_dashboard('root')


@dashboard_bp.route('/simple')
def simple_dashboard():
    """Simplified dashboard view (served from index.html)."""
    return _serve_dashboard('simple')


@dashboard_bp.route('/advanced')
def advanced_dashboard():
    """Advanced dashboard view with all features."""
    return _serve_dashboard('advanced')


@dashboard_bp.route('/favicon.ico')
def favicon():
    """Suppress favicon 404s."""
    return '', 204
