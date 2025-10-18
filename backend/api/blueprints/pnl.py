#!/usr/bin/env python3
"""
P&L Blueprint
Profit and Loss tracking, history, and analytics
Consolidated from realtime_pnl_dashboard.py and other P&L features
"""

from flask import Blueprint, jsonify, request, send_file, current_app
from datetime import datetime, timedelta
import pandas as pd
import io

from ..services.pnl_service import PnLService
from ..utils.decorators import handle_errors

pnl_bp = Blueprint('pnl', __name__)

@pnl_bp.route('/current')
@handle_errors
def current_pnl():
    """Get current P&L data"""
    service = current_app.pnl_service
    pnl_data = service.get_current_pnl()

    return jsonify({
        'daily_pnl': pnl_data.get('daily_pnl', 0),
        'total_pnl': pnl_data.get('total_pnl', 0),
        'realized_pnl': pnl_data.get('realized_pnl', 0),
        'unrealized_pnl': pnl_data.get('unrealized_pnl', 0),
        'win_rate': pnl_data.get('win_rate', 0),
        'best_trade': pnl_data.get('best_trade'),
        'worst_trade': pnl_data.get('worst_trade'),
        'positions': pnl_data.get('positions', []),
        'timestamp': datetime.now().isoformat()
    })

@pnl_bp.route('/history')
@handle_errors
def pnl_history():
    """Get P&L history data"""
    service = current_app.pnl_service

    # Get query parameters
    days = int(request.args.get('days', 30))
    interval = request.args.get('interval', 'daily')  # daily, hourly, 5min

    history = service.get_pnl_history(days=days, interval=interval)

    return jsonify({
        'history': history,
        'days': days,
        'interval': interval,
        'count': len(history)
    })

@pnl_bp.route('/chart-data')
@handle_errors
def pnl_chart_data():
    """Get P&L data formatted for Chart.js"""
    service = current_app.pnl_service
    days = int(request.args.get('days', 7))

    chart_data = service.get_chart_data(days=days)

    return jsonify({
        'labels': chart_data.get('labels', []),
        'datasets': [
            {
                'label': 'Daily P&L',
                'data': chart_data.get('daily_pnl', []),
                'borderColor': 'rgb(75, 192, 192)',
                'backgroundColor': 'rgba(75, 192, 192, 0.2)',
                'tension': 0.1
            },
            {
                'label': 'Cumulative P&L',
                'data': chart_data.get('cumulative_pnl', []),
                'borderColor': 'rgb(255, 99, 132)',
                'backgroundColor': 'rgba(255, 99, 132, 0.2)',
                'tension': 0.1
            }
        ]
    })

@pnl_bp.route('/statistics')
@handle_errors
def pnl_statistics():
    """Get comprehensive P&L statistics"""
    service = current_app.pnl_service
    days = int(request.args.get('days', 30))

    stats = service.calculate_statistics(days=days)

    return jsonify({
        'total_trades': stats.get('total_trades', 0),
        'winning_trades': stats.get('winning_trades', 0),
        'losing_trades': stats.get('losing_trades', 0),
        'win_rate': stats.get('win_rate', 0),
        'average_win': stats.get('average_win', 0),
        'average_loss': stats.get('average_loss', 0),
        'profit_factor': stats.get('profit_factor', 0),
        'sharpe_ratio': stats.get('sharpe_ratio', 0),
        'max_drawdown': stats.get('max_drawdown', 0),
        'best_day': stats.get('best_day'),
        'worst_day': stats.get('worst_day'),
        'current_streak': stats.get('current_streak', 0),
        'max_streak': stats.get('max_streak', 0)
    })

@pnl_bp.route('/export')
@handle_errors
def export_pnl():
    """Export P&L data to CSV"""
    service = current_app.pnl_service

    # Get export parameters
    format = request.args.get('format', 'csv')
    days = int(request.args.get('days', 30))
    include_trades = request.args.get('include_trades', 'true').lower() == 'true'

    # Get data
    data = service.get_export_data(days=days, include_trades=include_trades)

    if format == 'csv':
        # Create DataFrame and convert to CSV
        df = pd.DataFrame(data)
        output = io.StringIO()
        df.to_csv(output, index=False)
        output.seek(0)

        # Create response
        response = send_file(
            io.BytesIO(output.getvalue().encode()),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'pnl_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )
        return response

    elif format == 'json':
        return jsonify(data)

    else:
        return jsonify({'error': 'Unsupported format'}), 400

@pnl_bp.route('/trades')
@handle_errors
def recent_trades():
    """Get recent trades with P&L"""
    service = current_app.pnl_service
    limit = int(request.args.get('limit', 50))

    trades = service.get_recent_trades(limit=limit)

    return jsonify({
        'trades': trades,
        'count': len(trades),
        'total_pnl': sum(t.get('pnl', 0) for t in trades)
    })

@pnl_bp.route('/performance')
@handle_errors
def performance_metrics():
    """Get performance metrics by symbol"""
    service = current_app.pnl_service

    metrics = service.get_performance_by_symbol()

    return jsonify({
        'symbols': metrics,
        'best_performer': max(metrics.items(), key=lambda x: x[1].get('pnl', 0))[0] if metrics else None,
        'worst_performer': min(metrics.items(), key=lambda x: x[1].get('pnl', 0))[0] if metrics else None
    })
