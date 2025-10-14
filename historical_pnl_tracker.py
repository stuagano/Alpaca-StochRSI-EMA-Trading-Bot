#!/usr/bin/env python3
"""
Historical P&L Tracker with Local Storage
Builds P&L history over time since Alpaca doesn't provide it
"""

import json
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from flask import Flask, jsonify, render_template_string
from flask_cors import CORS
import alpaca_trade_api as tradeapi
import pandas as pd

# Load Alpaca credentials
with open('AUTH/authAlpaca.txt') as f:
    creds = json.load(f)

# Initialize Alpaca API
api = tradeapi.REST(
    creds['APCA-API-KEY-ID'],
    creds['APCA-API-SECRET-KEY'],
    creds['BASE-URL'],
    api_version='v2'
)

# Initialize Flask
app = Flask(__name__)
CORS(app)

# Database setup
DB_PATH = 'pnl_history.db'

def init_database():
    """Initialize SQLite database for P&L history"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Main P&L history table
    c.execute('''CREATE TABLE IF NOT EXISTS pnl_snapshots
                 (timestamp TEXT PRIMARY KEY,
                  total_pnl REAL,
                  unrealized_pnl REAL,
                  portfolio_value REAL,
                  buying_power REAL,
                  cash REAL,
                  positions_json TEXT)''')

    # Daily summary table
    c.execute('''CREATE TABLE IF NOT EXISTS daily_pnl
                 (date TEXT PRIMARY KEY,
                  open_value REAL,
                  close_value REAL,
                  high_value REAL,
                  low_value REAL,
                  daily_pnl REAL,
                  trades_count INTEGER)''')

    conn.commit()
    conn.close()

init_database()

# HTML Dashboard
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Historical P&L Tracker</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'SF Pro Display', -apple-system, sans-serif;
            background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%);
            color: #e0e0e0;
            padding: 20px;
        }
        .container {
            max-width: 1600px;
            margin: 0 auto;
        }
        h1 {
            text-align: center;
            font-size: 2.5em;
            margin-bottom: 30px;
            background: linear-gradient(45deg, #00ff88, #00bbff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            padding: 15px;
            text-align: center;
        }
        .stat-label {
            font-size: 0.9em;
            color: #888;
            margin-bottom: 5px;
        }
        .stat-value {
            font-size: 1.8em;
            font-weight: bold;
        }
        .profit { color: #00ff88; }
        .loss { color: #ff4444; }
        .chart-container {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            height: 400px;
        }
        .time-selector {
            text-align: center;
            margin-bottom: 20px;
        }
        .time-btn {
            padding: 8px 20px;
            margin: 0 5px;
            background: rgba(0, 255, 136, 0.1);
            border: 1px solid #00ff88;
            color: #00ff88;
            border-radius: 5px;
            cursor: pointer;
            transition: all 0.3s;
        }
        .time-btn:hover, .time-btn.active {
            background: #00ff88;
            color: #000;
        }
        .data-table {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            padding: 20px;
            overflow-x: auto;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th {
            background: rgba(0, 255, 136, 0.1);
            padding: 10px;
            text-align: left;
            color: #ffcc00;
        }
        td {
            padding: 10px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📈 HISTORICAL P&L TRACKER</h1>

        <div class="stats-grid" id="statsGrid">
            <div class="stat-card">
                <div class="stat-label">Today's P&L</div>
                <div class="stat-value" id="todayPnL">Loading...</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">7 Day P&L</div>
                <div class="stat-value" id="weekPnL">Loading...</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">30 Day P&L</div>
                <div class="stat-value" id="monthPnL">Loading...</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">All Time P&L</div>
                <div class="stat-value" id="allTimePnL">Loading...</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Current P&L</div>
                <div class="stat-value" id="currentPnL">Loading...</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Data Points</div>
                <div class="stat-value" id="dataPoints">0</div>
            </div>
        </div>

        <div class="time-selector">
            <button class="time-btn active" onclick="changeTimeframe('1D')">1 Day</button>
            <button class="time-btn" onclick="changeTimeframe('1W')">1 Week</button>
            <button class="time-btn" onclick="changeTimeframe('1M')">1 Month</button>
            <button class="time-btn" onclick="changeTimeframe('3M')">3 Months</button>
            <button class="time-btn" onclick="changeTimeframe('ALL')">All Time</button>
        </div>

        <div class="chart-container">
            <canvas id="pnlChart"></canvas>
        </div>

        <div class="chart-container">
            <canvas id="portfolioChart"></canvas>
        </div>

        <div class="data-table">
            <h3>Recent P&L History</h3>
            <table id="historyTable">
                <thead>
                    <tr>
                        <th>Time</th>
                        <th>Total P&L</th>
                        <th>Unrealized P&L</th>
                        <th>Portfolio Value</th>
                        <th>Positions</th>
                    </tr>
                </thead>
                <tbody id="historyBody">
                    <tr><td colspan="5">Loading...</td></tr>
                </tbody>
            </table>
        </div>
    </div>

    <script>
        let pnlChart, portfolioChart;
        let currentTimeframe = '1D';

        // Initialize charts
        const pnlCtx = document.getElementById('pnlChart').getContext('2d');
        pnlChart = new Chart(pnlCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'P&L',
                    data: [],
                    borderColor: '#00ff88',
                    backgroundColor: 'rgba(0, 255, 136, 0.1)',
                    borderWidth: 2,
                    tension: 0.1,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'P&L Over Time',
                        color: '#e0e0e0'
                    },
                    legend: {
                        display: false
                    }
                },
                scales: {
                    x: {
                        grid: { color: 'rgba(255, 255, 255, 0.1)' },
                        ticks: { color: '#888' }
                    },
                    y: {
                        grid: { color: 'rgba(255, 255, 255, 0.1)' },
                        ticks: {
                            color: '#888',
                            callback: function(value) {
                                return '$' + value.toFixed(0);
                            }
                        }
                    }
                }
            }
        });

        const portfolioCtx = document.getElementById('portfolioChart').getContext('2d');
        portfolioChart = new Chart(portfolioCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Portfolio Value',
                    data: [],
                    borderColor: '#00bbff',
                    backgroundColor: 'rgba(0, 187, 255, 0.1)',
                    borderWidth: 2,
                    tension: 0.1,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Portfolio Value Over Time',
                        color: '#e0e0e0'
                    },
                    legend: {
                        display: false
                    }
                },
                scales: {
                    x: {
                        grid: { color: 'rgba(255, 255, 255, 0.1)' },
                        ticks: { color: '#888' }
                    },
                    y: {
                        grid: { color: 'rgba(255, 255, 255, 0.1)' },
                        ticks: {
                            color: '#888',
                            callback: function(value) {
                                return '$' + value.toFixed(0);
                            }
                        }
                    }
                }
            }
        });

        function changeTimeframe(timeframe) {
            currentTimeframe = timeframe;
            $('.time-btn').removeClass('active');
            $(event.target).addClass('active');
            updateDashboard();
        }

        function formatCurrency(value) {
            const sign = value >= 0 ? '+' : '';
            return sign + '$' + Math.abs(value).toFixed(2);
        }

        function updateDashboard() {
            fetch('/api/historical-pnl?timeframe=' + currentTimeframe)
                .then(response => response.json())
                .then(data => {
                    // Update stats
                    $('#todayPnL').text(formatCurrency(data.stats.today_pnl || 0))
                        .removeClass('profit loss')
                        .addClass((data.stats.today_pnl || 0) >= 0 ? 'profit' : 'loss');

                    $('#weekPnL').text(formatCurrency(data.stats.week_pnl || 0))
                        .removeClass('profit loss')
                        .addClass((data.stats.week_pnl || 0) >= 0 ? 'profit' : 'loss');

                    $('#monthPnL').text(formatCurrency(data.stats.month_pnl || 0))
                        .removeClass('profit loss')
                        .addClass((data.stats.month_pnl || 0) >= 0 ? 'profit' : 'loss');

                    $('#allTimePnL').text(formatCurrency(data.stats.all_time_pnl || 0))
                        .removeClass('profit loss')
                        .addClass((data.stats.all_time_pnl || 0) >= 0 ? 'profit' : 'loss');

                    $('#currentPnL').text(formatCurrency(data.stats.current_pnl || 0))
                        .removeClass('profit loss')
                        .addClass((data.stats.current_pnl || 0) >= 0 ? 'profit' : 'loss');

                    $('#dataPoints').text(data.history.length);

                    // Update charts
                    if (data.history.length > 0) {
                        pnlChart.data.labels = data.history.map(h => h.time);
                        pnlChart.data.datasets[0].data = data.history.map(h => h.total_pnl);
                        pnlChart.update();

                        portfolioChart.data.labels = data.history.map(h => h.time);
                        portfolioChart.data.datasets[0].data = data.history.map(h => h.portfolio_value);
                        portfolioChart.update();
                    }

                    // Update table
                    if (data.recent.length > 0) {
                        let tableHtml = '';
                        data.recent.forEach(row => {
                            const pnlClass = row.total_pnl >= 0 ? 'profit' : 'loss';
                            tableHtml += `
                                <tr>
                                    <td>${row.time}</td>
                                    <td class="${pnlClass}">${formatCurrency(row.total_pnl)}</td>
                                    <td class="${pnlClass}">${formatCurrency(row.unrealized_pnl)}</td>
                                    <td>$${row.portfolio_value.toFixed(2)}</td>
                                    <td>${row.positions_count} positions</td>
                                </tr>
                            `;
                        });
                        $('#historyBody').html(tableHtml);
                    }
                });
        }

        // Update every 10 seconds
        setInterval(updateDashboard, 10000);
        updateDashboard();
    </script>
</body>
</html>
"""

def record_pnl_snapshot():
    """Record current P&L snapshot to database"""
    try:
        # Get account and positions
        account = api.get_account()
        positions = api.list_positions()

        # Calculate total P&L
        total_pnl = sum(float(pos.unrealized_pl or 0) for pos in positions)

        # Prepare positions data
        positions_data = []
        for pos in positions:
            positions_data.append({
                'symbol': pos.symbol,
                'qty': float(pos.qty),
                'pnl': float(pos.unrealized_pl or 0),
                'pnl_pct': float(pos.unrealized_plpc or 0) * 100
            })

        # Save to database
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        timestamp = datetime.now().isoformat()
        c.execute('''INSERT OR REPLACE INTO pnl_snapshots VALUES (?, ?, ?, ?, ?, ?, ?)''',
                  (timestamp,
                   total_pnl,
                   total_pnl,  # All unrealized for now
                   float(account.portfolio_value),
                   float(account.buying_power),
                   float(account.cash),
                   json.dumps(positions_data)))

        conn.commit()
        conn.close()

        return True
    except Exception as e:
        print(f"Error recording snapshot: {e}")
        return False

def background_recorder():
    """Background thread to record P&L snapshots"""
    while True:
        record_pnl_snapshot()
        time.sleep(30)  # Record every 30 seconds

@app.route('/')
def index():
    return render_template_string(DASHBOARD_TEMPLATE)

@app.route('/api/historical-pnl')
def get_historical_pnl():
    """Get historical P&L data"""
    from flask import request
    timeframe = request.args.get('timeframe', '1D')

    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        # Determine time range
        now = datetime.now()
        if timeframe == '1D':
            start_time = now - timedelta(days=1)
        elif timeframe == '1W':
            start_time = now - timedelta(weeks=1)
        elif timeframe == '1M':
            start_time = now - timedelta(days=30)
        elif timeframe == '3M':
            start_time = now - timedelta(days=90)
        else:  # ALL
            start_time = datetime(2020, 1, 1)

        # Get historical data
        c.execute('''SELECT timestamp, total_pnl, unrealized_pnl, portfolio_value, positions_json
                     FROM pnl_snapshots
                     WHERE timestamp > ?
                     ORDER BY timestamp''',
                  (start_time.isoformat(),))

        rows = c.fetchall()

        # Get current P&L
        account = api.get_account()
        positions = api.list_positions()
        current_pnl = sum(float(pos.unrealized_pl or 0) for pos in positions)

        # Format history
        history = []
        for row in rows:
            timestamp = datetime.fromisoformat(row[0])
            positions_data = json.loads(row[4]) if row[4] else []
            history.append({
                'time': timestamp.strftime('%H:%M' if timeframe == '1D' else '%m/%d %H:%M'),
                'total_pnl': row[1],
                'unrealized_pnl': row[2],
                'portfolio_value': row[3],
                'positions_count': len(positions_data)
            })

        # Calculate stats
        stats = {
            'current_pnl': current_pnl,
            'today_pnl': 0,
            'week_pnl': 0,
            'month_pnl': 0,
            'all_time_pnl': 0
        }

        # Calculate period P&L if we have data
        if rows:
            # Today's P&L
            c.execute('''SELECT MIN(total_pnl), MAX(total_pnl) FROM pnl_snapshots
                         WHERE timestamp > ?''',
                      ((now - timedelta(days=1)).isoformat(),))
            today_data = c.fetchone()
            if today_data and today_data[0] is not None:
                stats['today_pnl'] = current_pnl - today_data[0]

            # Week P&L
            c.execute('''SELECT MIN(total_pnl) FROM pnl_snapshots
                         WHERE timestamp > ?''',
                      ((now - timedelta(weeks=1)).isoformat(),))
            week_data = c.fetchone()
            if week_data and week_data[0] is not None:
                stats['week_pnl'] = current_pnl - week_data[0]

            # Month P&L
            c.execute('''SELECT MIN(total_pnl) FROM pnl_snapshots
                         WHERE timestamp > ?''',
                      ((now - timedelta(days=30)).isoformat(),))
            month_data = c.fetchone()
            if month_data and month_data[0] is not None:
                stats['month_pnl'] = current_pnl - month_data[0]

            # All time P&L
            c.execute('SELECT MIN(total_pnl) FROM pnl_snapshots')
            all_time_data = c.fetchone()
            if all_time_data and all_time_data[0] is not None:
                stats['all_time_pnl'] = current_pnl - all_time_data[0]

        conn.close()

        return jsonify({
            'history': history,
            'recent': history[-20:] if history else [],
            'stats': stats
        })

    except Exception as e:
        print(f"Error getting historical data: {e}")
        return jsonify({
            'history': [],
            'recent': [],
            'stats': {}
        })

@app.route('/api/get-alpaca-history')
def get_alpaca_history():
    """Get portfolio history from Alpaca API"""
    try:
        # Get portfolio history for last 30 days
        portfolio_history = api.get_portfolio_history(
            period='1M',
            timeframe='1D'
        )

        # Format for response
        history_data = {
            'timestamps': portfolio_history.timestamp,
            'equity': portfolio_history.equity,
            'profit_loss': portfolio_history.profit_loss,
            'profit_loss_pct': portfolio_history.profit_loss_pct
        }

        return jsonify(history_data)

    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    print("=" * 60)
    print("📈 HISTORICAL P&L TRACKER")
    print("=" * 60)
    print("📊 Dashboard URL: http://localhost:5006")
    print("📝 Recording P&L snapshots every 30 seconds")
    print("💾 Storing history in local database")
    print("=" * 60)

    # Start background recorder
    recorder = threading.Thread(target=background_recorder, daemon=True)
    recorder.start()

    # Record initial snapshot
    record_pnl_snapshot()
    print("✅ Initial snapshot recorded")

    app.run(host='0.0.0.0', port=5006, debug=False)