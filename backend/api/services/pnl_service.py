#!/usr/bin/env python3
"""
P&L Service
Profit and Loss tracking and analytics service
Consolidated from multiple P&L dashboard implementations
"""

import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

class PnLService:
    """
    Service for P&L tracking, history, and analytics
    """

    def __init__(self, alpaca_client, db_path: str = 'database/trading_data.db'):
        """
        Initialize P&L service

        Args:
            alpaca_client: Alpaca API client
            db_path: Path to SQLite database
        """
        self.client = alpaca_client
        self.api = alpaca_client.api
        self.db_path = db_path

        # Initialize database
        self._init_database()

        # Cache for performance
        self._cache = {}
        self._cache_timestamp = None

    def _init_database(self):
        """Initialize database tables for P&L tracking"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Create P&L history table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS pnl_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    daily_pnl REAL,
                    total_pnl REAL,
                    realized_pnl REAL,
                    unrealized_pnl REAL,
                    positions_count INTEGER,
                    account_value REAL
                )
            ''')

            # Create trades history table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trade_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    symbol TEXT,
                    side TEXT,
                    qty REAL,
                    price REAL,
                    pnl REAL,
                    order_id TEXT UNIQUE
                )
            ''')

            # Create performance metrics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE UNIQUE,
                    win_rate REAL,
                    sharpe_ratio REAL,
                    max_drawdown REAL,
                    profit_factor REAL,
                    total_trades INTEGER,
                    winning_trades INTEGER,
                    losing_trades INTEGER
                )
            ''')

            conn.commit()
            conn.close()
            logger.info("Database initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing database: {e}")

    def get_current_pnl(self) -> Dict:
        """Get current P&L data"""
        try:
            account = self.api.get_account()
            positions = self.api.list_positions()

            # Calculate P&L
            daily_pnl = self._calculate_daily_pnl()
            total_pnl = self._calculate_total_pnl()
            unrealized_pnl = sum(float(p.unrealized_pl) for p in positions)

            # Calculate win rate
            trades = self._get_recent_trades(days=30)
            win_rate = self._calculate_win_rate(trades)

            # Get best and worst trades
            best_trade = max(trades, key=lambda x: x.get('pnl', 0), default=None) if trades else None
            worst_trade = min(trades, key=lambda x: x.get('pnl', 0), default=None) if trades else None

            # Format positions data
            positions_data = [
                {
                    'symbol': p.symbol,
                    'qty': float(p.qty),
                    'unrealized_pl': float(p.unrealized_pl),
                    'unrealized_plpc': float(p.unrealized_plpc) * 100
                }
                for p in positions
            ]

            # Store in database
            self._store_pnl_snapshot(
                daily_pnl, total_pnl, 0, unrealized_pnl,
                len(positions), float(account.portfolio_value)
            )

            return {
                'daily_pnl': round(daily_pnl, 2),
                'total_pnl': round(total_pnl, 2),
                'realized_pnl': round(total_pnl - unrealized_pnl, 2),
                'unrealized_pnl': round(unrealized_pnl, 2),
                'win_rate': round(win_rate, 2),
                'best_trade': best_trade,
                'worst_trade': worst_trade,
                'positions': positions_data,
                'account_value': float(account.portfolio_value)
            }

        except Exception as e:
            logger.error(f"Error getting current P&L: {e}")
            return {
                'daily_pnl': 0,
                'total_pnl': 0,
                'realized_pnl': 0,
                'unrealized_pnl': 0,
                'win_rate': 0,
                'positions': []
            }

    def get_pnl_history(self, days: int = 30, interval: str = 'daily') -> List[Dict]:
        """Get P&L history data"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            start_date = datetime.now() - timedelta(days=days)

            if interval == 'daily':
                query = '''
                    SELECT DATE(timestamp) as date,
                           MAX(total_pnl) as total_pnl,
                           SUM(daily_pnl) as daily_pnl
                    FROM pnl_history
                    WHERE timestamp >= ?
                    GROUP BY DATE(timestamp)
                    ORDER BY date
                '''
            elif interval == 'hourly':
                query = '''
                    SELECT strftime('%Y-%m-%d %H:00', timestamp) as hour,
                           AVG(total_pnl) as total_pnl,
                           SUM(daily_pnl) as daily_pnl
                    FROM pnl_history
                    WHERE timestamp >= ?
                    GROUP BY strftime('%Y-%m-%d %H', timestamp)
                    ORDER BY hour
                '''
            else:  # 5min
                query = '''
                    SELECT timestamp,
                           total_pnl,
                           daily_pnl
                    FROM pnl_history
                    WHERE timestamp >= ?
                    ORDER BY timestamp
                '''

            cursor.execute(query, (start_date,))
            rows = cursor.fetchall()
            conn.close()

            return [
                {
                    'timestamp': row[0],
                    'total_pnl': round(row[1], 2),
                    'daily_pnl': round(row[2], 2)
                }
                for row in rows
            ]

        except Exception as e:
            logger.error(f"Error getting P&L history: {e}")
            return []

    def get_chart_data(self, days: int = 7) -> Dict:
        """Get P&L data formatted for Chart.js"""
        history = self.get_pnl_history(days=days, interval='daily')

        labels = []
        daily_pnl = []
        cumulative_pnl = []

        for entry in history:
            labels.append(entry['timestamp'])
            daily_pnl.append(entry['daily_pnl'])
            cumulative_pnl.append(entry['total_pnl'])

        return {
            'labels': labels,
            'daily_pnl': daily_pnl,
            'cumulative_pnl': cumulative_pnl
        }

    def calculate_statistics(self, days: int = 30) -> Dict:
        """Calculate comprehensive P&L statistics"""
        try:
            trades = self._get_recent_trades(days=days)
            history = self.get_pnl_history(days=days, interval='daily')

            # Basic statistics
            total_trades = len(trades)
            winning_trades = len([t for t in trades if t.get('pnl', 0) > 0])
            losing_trades = len([t for t in trades if t.get('pnl', 0) < 0])
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

            # Average win/loss
            wins = [t['pnl'] for t in trades if t.get('pnl', 0) > 0]
            losses = [abs(t['pnl']) for t in trades if t.get('pnl', 0) < 0]

            average_win = np.mean(wins) if wins else 0
            average_loss = np.mean(losses) if losses else 0

            # Profit factor
            total_wins = sum(wins) if wins else 0
            total_losses = sum(losses) if losses else 0
            profit_factor = (total_wins / total_losses) if total_losses > 0 else 0

            # Sharpe ratio (simplified)
            returns = [h['daily_pnl'] for h in history]
            sharpe_ratio = self._calculate_sharpe_ratio(returns)

            # Max drawdown
            cumulative = [h['total_pnl'] for h in history]
            max_drawdown = self._calculate_max_drawdown(cumulative)

            # Best/worst days
            best_day = max(history, key=lambda x: x['daily_pnl'], default=None) if history else None
            worst_day = min(history, key=lambda x: x['daily_pnl'], default=None) if history else None

            # Streaks
            current_streak, max_streak = self._calculate_streaks(trades)

            return {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': round(win_rate, 2),
                'average_win': round(average_win, 2),
                'average_loss': round(average_loss, 2),
                'profit_factor': round(profit_factor, 2),
                'sharpe_ratio': round(sharpe_ratio, 2),
                'max_drawdown': round(max_drawdown, 2),
                'best_day': best_day,
                'worst_day': worst_day,
                'current_streak': current_streak,
                'max_streak': max_streak
            }

        except Exception as e:
            logger.error(f"Error calculating statistics: {e}")
            return {}

    def get_export_data(self, days: int = 30, include_trades: bool = True) -> List[Dict]:
        """Get data for export"""
        data = []

        # Get P&L history
        history = self.get_pnl_history(days=days, interval='daily')
        for entry in history:
            data.append({
                'type': 'pnl',
                'date': entry['timestamp'],
                'daily_pnl': entry['daily_pnl'],
                'total_pnl': entry['total_pnl']
            })

        # Get trades if requested
        if include_trades:
            trades = self._get_recent_trades(days=days)
            for trade in trades:
                data.append({
                    'type': 'trade',
                    'date': trade['timestamp'],
                    'symbol': trade['symbol'],
                    'side': trade['side'],
                    'qty': trade['qty'],
                    'price': trade['price'],
                    'pnl': trade['pnl']
                })

        return data

    def get_recent_trades(self, limit: int = 50) -> List[Dict]:
        """Get recent trades with P&L"""
        return self._get_recent_trades(limit=limit)

    def get_performance_by_symbol(self) -> Dict:
        """Get performance metrics grouped by symbol"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            query = '''
                SELECT symbol,
                       COUNT(*) as trade_count,
                       SUM(pnl) as total_pnl,
                       AVG(pnl) as avg_pnl,
                       SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                       SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losses
                FROM trade_history
                GROUP BY symbol
                ORDER BY total_pnl DESC
            '''

            cursor.execute(query)
            rows = cursor.fetchall()
            conn.close()

            metrics = {}
            for row in rows:
                symbol = row[0]
                trade_count = row[1]
                win_rate = (row[4] / trade_count * 100) if trade_count > 0 else 0

                metrics[symbol] = {
                    'trade_count': trade_count,
                    'pnl': round(row[2], 2),
                    'avg_pnl': round(row[3], 2),
                    'wins': row[4],
                    'losses': row[5],
                    'win_rate': round(win_rate, 2)
                }

            return metrics

        except Exception as e:
            logger.error(f"Error getting performance by symbol: {e}")
            return {}

    # Private helper methods
    def _calculate_daily_pnl(self) -> float:
        """Calculate today's P&L"""
        # Implementation depends on your specific requirements
        # This is a simplified version
        trades_today = self._get_recent_trades(days=1)
        return sum(t.get('pnl', 0) for t in trades_today)

    def _calculate_total_pnl(self) -> float:
        """Calculate total P&L"""
        all_trades = self._get_recent_trades(days=365)
        return sum(t.get('pnl', 0) for t in all_trades)

    def _get_recent_trades(self, days: Optional[int] = None, limit: Optional[int] = None) -> List[Dict]:
        """Get recent trades from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            if days:
                start_date = datetime.now() - timedelta(days=days)
                query = '''
                    SELECT * FROM trade_history
                    WHERE timestamp >= ?
                    ORDER BY timestamp DESC
                '''
                cursor.execute(query, (start_date,))
            elif limit:
                query = '''
                    SELECT * FROM trade_history
                    ORDER BY timestamp DESC
                    LIMIT ?
                '''
                cursor.execute(query, (limit,))
            else:
                query = 'SELECT * FROM trade_history ORDER BY timestamp DESC'
                cursor.execute(query)

            rows = cursor.fetchall()
            conn.close()

            trades = []
            for row in rows:
                trades.append({
                    'id': row[0],
                    'timestamp': row[1],
                    'symbol': row[2],
                    'side': row[3],
                    'qty': row[4],
                    'price': row[5],
                    'pnl': row[6],
                    'order_id': row[7]
                })

            return trades

        except Exception as e:
            logger.error(f"Error getting recent trades: {e}")
            return []

    def _store_pnl_snapshot(self, daily_pnl, total_pnl, realized_pnl,
                           unrealized_pnl, positions_count, account_value):
        """Store P&L snapshot in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO pnl_history
                (daily_pnl, total_pnl, realized_pnl, unrealized_pnl, positions_count, account_value)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (daily_pnl, total_pnl, realized_pnl, unrealized_pnl, positions_count, account_value))

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"Error storing P&L snapshot: {e}")

    def _calculate_win_rate(self, trades: List[Dict]) -> float:
        """Calculate win rate from trades"""
        if not trades:
            return 0
        wins = len([t for t in trades if t.get('pnl', 0) > 0])
        return (wins / len(trades)) * 100

    def _calculate_sharpe_ratio(self, returns: List[float], risk_free_rate: float = 0.02) -> float:
        """Calculate simplified Sharpe ratio"""
        if not returns or len(returns) < 2:
            return 0

        avg_return = np.mean(returns)
        std_return = np.std(returns)

        if std_return == 0:
            return 0

        # Annualized Sharpe ratio (assuming daily returns)
        return ((avg_return - risk_free_rate/252) / std_return) * np.sqrt(252)

    def _calculate_max_drawdown(self, cumulative_pnl: List[float]) -> float:
        """Calculate maximum drawdown"""
        if not cumulative_pnl:
            return 0

        peak = cumulative_pnl[0]
        max_dd = 0

        for value in cumulative_pnl:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak if peak != 0 else 0
            max_dd = max(max_dd, drawdown)

        return max_dd * 100

    def _calculate_streaks(self, trades: List[Dict]) -> tuple:
        """Calculate current and maximum winning streaks"""
        if not trades:
            return 0, 0

        current_streak = 0
        max_streak = 0

        for trade in trades:
            if trade.get('pnl', 0) > 0:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 0

        return current_streak, max_streak
