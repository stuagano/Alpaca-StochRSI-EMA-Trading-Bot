#!/usr/bin/env python3
"""
Enhanced Position Manager with risk controls and portfolio tracking
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import json
import pandas as pd
import alpaca_trade_api as tradeapi

logger = logging.getLogger(__name__)

@dataclass
class Position:
    """Position data class"""
    symbol: str
    qty: int
    side: str  # 'long' or 'short'
    entry_price: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    entry_time: datetime
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    risk_amount: Optional[float] = None
    strategy: str = 'unknown'
    
    @property
    def is_profitable(self) -> bool:
        return self.unrealized_pnl > 0
    
    @property
    def risk_reward_ratio(self) -> float:
        if self.stop_loss and self.take_profit:
            risk = abs(self.entry_price - self.stop_loss)
            reward = abs(self.take_profit - self.entry_price)
            return reward / risk if risk > 0 else 0
        return 0

@dataclass
class PositionMetrics:
    """Portfolio position metrics"""
    total_positions: int
    long_positions: int
    short_positions: int
    total_market_value: float
    total_unrealized_pnl: float
    total_unrealized_pnl_pct: float
    largest_position: float
    portfolio_concentration: float
    win_rate: float
    avg_hold_time: timedelta

class PositionManager:
    """
    Comprehensive position management system with risk controls
    """
    
    def __init__(self, api: tradeapi.REST, config: Dict):
        self.api = api
        self.config = config
        self.db_path = 'database/positions.db'
        self._init_database()
        
        # Risk management settings
        self.max_positions = config.get('max_positions', 10)
        self.max_portfolio_risk = config.get('max_portfolio_risk', 0.02)  # 2%
        self.max_position_size = config.get('max_position_size_pct', 0.10)  # 10%
        self.max_sector_concentration = config.get('max_sector_concentration', 0.30)  # 30%
        self.default_stop_loss_pct = config.get('default_stop_loss_pct', 0.02)  # 2%
        self.default_take_profit_pct = config.get('default_take_profit_pct', 0.04)  # 4%
        
        logger.info(f"✅ Position Manager initialized with {self.max_positions} max positions")
    
    def _init_database(self):
        """Initialize position tracking database"""
        import os
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Position tracking table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                qty INTEGER NOT NULL,
                side TEXT NOT NULL,
                entry_price REAL NOT NULL,
                entry_time TEXT NOT NULL,
                stop_loss REAL,
                take_profit REAL,
                risk_amount REAL,
                strategy TEXT,
                status TEXT DEFAULT 'open',
                exit_price REAL,
                exit_time TEXT,
                realized_pnl REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Position updates table for tracking changes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS position_updates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                position_id INTEGER,
                price REAL,
                market_value REAL,
                unrealized_pnl REAL,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (position_id) REFERENCES positions (id)
            )
        ''')
        
        # Risk events table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS risk_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                symbol TEXT,
                description TEXT,
                severity TEXT,
                triggered_at TEXT DEFAULT CURRENT_TIMESTAMP,
                resolved_at TEXT,
                action_taken TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        
        logger.info("📊 Position tracking database initialized")
    
    async def get_all_positions(self) -> List[Position]:
        """Get all current positions from broker and database"""
        try:
            # Get live positions from Alpaca
            alpaca_positions = self.api.list_positions()
            positions = []
            
            for pos in alpaca_positions:
                # Get additional data from our database
                db_data = self._get_position_from_db(pos.symbol)
                
                position = Position(
                    symbol=pos.symbol,
                    qty=int(pos.qty),
                    side=pos.side,
                    entry_price=float(pos.avg_entry_price),
                    current_price=float(pos.current_price) if pos.current_price else 0,
                    market_value=float(pos.market_value),
                    unrealized_pnl=float(pos.unrealized_pl),
                    unrealized_pnl_pct=float(pos.unrealized_plpc) * 100,
                    entry_time=datetime.fromisoformat(db_data.get('entry_time', datetime.now().isoformat())),
                    stop_loss=db_data.get('stop_loss'),
                    take_profit=db_data.get('take_profit'),
                    risk_amount=db_data.get('risk_amount'),
                    strategy=db_data.get('strategy', 'unknown')
                )
                
                positions.append(position)
                
                # Update position in database
                self._update_position_in_db(position)
            
            return positions
            
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    async def add_position(self, symbol: str, qty: int, side: str, 
                          entry_price: float, strategy: str = 'manual',
                          stop_loss: Optional[float] = None, 
                          take_profit: Optional[float] = None) -> bool:
        """Add a new position to tracking"""
        try:
            # Validate position limits
            if not await self._validate_new_position(symbol, qty, entry_price):
                return False
            
            # Calculate risk management levels if not provided
            if not stop_loss:
                stop_loss = self._calculate_stop_loss(entry_price, side)
            
            if not take_profit:
                take_profit = self._calculate_take_profit(entry_price, side)
            
            # Calculate risk amount
            risk_amount = abs(entry_price - stop_loss) * qty
            
            # Store in database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO positions 
                (symbol, qty, side, entry_price, entry_time, stop_loss, take_profit, risk_amount, strategy)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                symbol, qty, side, entry_price, datetime.now().isoformat(),
                stop_loss, take_profit, risk_amount, strategy
            ))
            
            position_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            logger.info(f"📈 Added position: {qty} {symbol} @ ${entry_price:.2f}")
            
            # Check risk limits
            await self._check_risk_limits()
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding position for {symbol}: {e}")
            return False
    
    async def update_position_levels(self, symbol: str, stop_loss: Optional[float] = None,
                                   take_profit: Optional[float] = None) -> bool:
        """Update stop loss and take profit levels for a position"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            updates = []
            params = []
            
            if stop_loss is not None:
                updates.append("stop_loss = ?")
                params.append(stop_loss)
            
            if take_profit is not None:
                updates.append("take_profit = ?")
                params.append(take_profit)
            
            if updates:
                updates.append("updated_at = ?")
                params.extend([datetime.now().isoformat(), symbol])
                
                cursor.execute(f'''
                    UPDATE positions 
                    SET {", ".join(updates)}
                    WHERE symbol = ? AND status = 'open'
                ''', params)
                
                conn.commit()
            
            conn.close()
            
            logger.info(f"📊 Updated levels for {symbol}: SL={stop_loss}, TP={take_profit}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating position levels for {symbol}: {e}")
            return False
    
    async def close_position(self, symbol: str, exit_price: float, reason: str = 'manual') -> bool:
        """Close a position and record the exit"""
        try:
            # Get position data
            position_data = self._get_position_from_db(symbol)
            if not position_data:
                logger.warning(f"No position found for {symbol}")
                return False
            
            # Calculate realized P&L
            entry_price = position_data['entry_price']
            qty = position_data['qty']
            side = position_data['side']
            
            if side == 'long':
                realized_pnl = (exit_price - entry_price) * qty
            else:  # short
                realized_pnl = (entry_price - exit_price) * qty
            
            # Update database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE positions 
                SET status = 'closed', exit_price = ?, exit_time = ?, 
                    realized_pnl = ?, updated_at = ?
                WHERE symbol = ? AND status = 'open'
            ''', (
                exit_price, datetime.now().isoformat(), realized_pnl,
                datetime.now().isoformat(), symbol
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"🔒 Closed position: {symbol} @ ${exit_price:.2f}, P&L: ${realized_pnl:.2f}")
            
            # Log risk event if significant loss
            if realized_pnl < -position_data.get('risk_amount', 100):
                await self._log_risk_event('position_loss', symbol, 
                                         f"Position closed with loss: ${realized_pnl:.2f}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error closing position for {symbol}: {e}")
            return False
    
    async def get_portfolio_metrics(self) -> PositionMetrics:
        """Calculate comprehensive portfolio metrics"""
        try:
            positions = await self.get_all_positions()
            
            if not positions:
                return PositionMetrics(
                    total_positions=0, long_positions=0, short_positions=0,
                    total_market_value=0, total_unrealized_pnl=0, total_unrealized_pnl_pct=0,
                    largest_position=0, portfolio_concentration=0, win_rate=0,
                    avg_hold_time=timedelta(0)
                )
            
            # Basic metrics
            total_positions = len(positions)
            long_positions = sum(1 for p in positions if p.side == 'long')
            short_positions = total_positions - long_positions
            
            total_market_value = sum(p.market_value for p in positions)
            total_unrealized_pnl = sum(p.unrealized_pnl for p in positions)
            total_unrealized_pnl_pct = (total_unrealized_pnl / total_market_value * 100) if total_market_value > 0 else 0
            
            # Risk metrics
            largest_position = max(p.market_value for p in positions) if positions else 0
            portfolio_concentration = (largest_position / total_market_value) if total_market_value > 0 else 0
            
            # Performance metrics
            win_rate = await self._calculate_win_rate()
            avg_hold_time = await self._calculate_avg_hold_time()
            
            return PositionMetrics(
                total_positions=total_positions,
                long_positions=long_positions,
                short_positions=short_positions,
                total_market_value=total_market_value,
                total_unrealized_pnl=total_unrealized_pnl,
                total_unrealized_pnl_pct=total_unrealized_pnl_pct,
                largest_position=largest_position,
                portfolio_concentration=portfolio_concentration,
                win_rate=win_rate,
                avg_hold_time=avg_hold_time
            )
            
        except Exception as e:
            logger.error(f"Error calculating portfolio metrics: {e}")
            return PositionMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0, timedelta(0))
    
    async def check_stop_losses(self) -> List[str]:
        """Check all positions for stop loss triggers"""
        try:
            positions = await self.get_all_positions()
            triggered_symbols = []
            
            for position in positions:
                if position.stop_loss:
                    should_trigger = False
                    
                    if position.side == 'long' and position.current_price <= position.stop_loss:
                        should_trigger = True
                    elif position.side == 'short' and position.current_price >= position.stop_loss:
                        should_trigger = True
                    
                    if should_trigger:
                        triggered_symbols.append(position.symbol)
                        
                        # Log risk event
                        await self._log_risk_event(
                            'stop_loss_triggered', 
                            position.symbol,
                            f"Stop loss triggered at ${position.current_price:.2f} (SL: ${position.stop_loss:.2f})"
                        )
                        
                        logger.warning(f"🛑 Stop loss triggered for {position.symbol} @ ${position.current_price:.2f}")
            
            return triggered_symbols
            
        except Exception as e:
            logger.error(f"Error checking stop losses: {e}")
            return []
    
    async def check_take_profits(self) -> List[str]:
        """Check all positions for take profit triggers"""
        try:
            positions = await self.get_all_positions()
            triggered_symbols = []
            
            for position in positions:
                if position.take_profit:
                    should_trigger = False
                    
                    if position.side == 'long' and position.current_price >= position.take_profit:
                        should_trigger = True
                    elif position.side == 'short' and position.current_price <= position.take_profit:
                        should_trigger = True
                    
                    if should_trigger:
                        triggered_symbols.append(position.symbol)
                        logger.info(f"🎯 Take profit triggered for {position.symbol} @ ${position.current_price:.2f}")
            
            return triggered_symbols
            
        except Exception as e:
            logger.error(f"Error checking take profits: {e}")
            return []
    
    async def get_risk_report(self) -> Dict:
        """Generate comprehensive risk report"""
        try:
            positions = await self.get_all_positions()
            metrics = await self.get_portfolio_metrics()
            
            # Get account info
            account = self.api.get_account()
            account_value = float(account.equity)
            
            # Calculate risk metrics
            total_risk = sum(pos.risk_amount or 0 for pos in positions)
            portfolio_risk_pct = (total_risk / account_value) * 100 if account_value > 0 else 0
            
            # Position size analysis
            position_sizes = [pos.market_value / account_value for pos in positions] if account_value > 0 else []
            max_position_size_pct = max(position_sizes) * 100 if position_sizes else 0
            
            # Sector concentration (simplified)
            symbols = [pos.symbol for pos in positions]
            sector_concentration = len(set(symbols)) / len(symbols) if symbols else 1
            
            # Recent risk events
            recent_events = self._get_recent_risk_events(days=7)
            
            return {
                'account_value': account_value,
                'total_risk_amount': total_risk,
                'portfolio_risk_pct': portfolio_risk_pct,
                'max_position_size_pct': max_position_size_pct,
                'position_count': len(positions),
                'sector_diversification': sector_concentration,
                'unrealized_pnl': metrics.total_unrealized_pnl,
                'win_rate': metrics.win_rate,
                'avg_hold_time_hours': metrics.avg_hold_time.total_seconds() / 3600,
                'risk_warnings': self._generate_risk_warnings(
                    portfolio_risk_pct, max_position_size_pct, len(positions)
                ),
                'recent_events': recent_events,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating risk report: {e}")
            return {}
    
    # Private helper methods
    
    def _get_position_from_db(self, symbol: str) -> Dict:
        """Get position data from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM positions 
                WHERE symbol = ? AND status = 'open'
                ORDER BY entry_time DESC LIMIT 1
            ''', (symbol,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
            
            return {}
            
        except Exception as e:
            logger.error(f"Error getting position from DB for {symbol}: {e}")
            return {}
    
    def _update_position_in_db(self, position: Position):
        """Update position data in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Update position updates table
            cursor.execute('''
                INSERT INTO position_updates (position_id, price, market_value, unrealized_pnl)
                SELECT id, ?, ?, ? FROM positions 
                WHERE symbol = ? AND status = 'open'
            ''', (position.current_price, position.market_value, position.unrealized_pnl, position.symbol))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error updating position in DB: {e}")
    
    async def _validate_new_position(self, symbol: str, qty: int, price: float) -> bool:
        """Validate if new position meets risk criteria"""
        try:
            # Check position count limit
            current_positions = await self.get_all_positions()
            if len(current_positions) >= self.max_positions:
                logger.warning(f"❌ Position limit reached: {len(current_positions)}/{self.max_positions}")
                return False
            
            # Check position size limit
            account = self.api.get_account()
            account_value = float(account.equity)
            position_value = qty * price
            position_size_pct = position_value / account_value
            
            if position_size_pct > self.max_position_size:
                logger.warning(f"❌ Position size too large: {position_size_pct:.1%} > {self.max_position_size:.1%}")
                return False
            
            # Check portfolio risk
            total_risk = sum(pos.risk_amount or 0 for pos in current_positions)
            new_risk = position_value * self.default_stop_loss_pct
            total_risk_pct = (total_risk + new_risk) / account_value
            
            if total_risk_pct > self.max_portfolio_risk:
                logger.warning(f"❌ Portfolio risk too high: {total_risk_pct:.1%} > {self.max_portfolio_risk:.1%}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating position: {e}")
            return False
    
    def _calculate_stop_loss(self, entry_price: float, side: str) -> float:
        """Calculate stop loss price"""
        if side == 'long':
            return entry_price * (1 - self.default_stop_loss_pct)
        else:  # short
            return entry_price * (1 + self.default_stop_loss_pct)
    
    def _calculate_take_profit(self, entry_price: float, side: str) -> float:
        """Calculate take profit price"""
        if side == 'long':
            return entry_price * (1 + self.default_take_profit_pct)
        else:  # short
            return entry_price * (1 - self.default_take_profit_pct)
    
    async def _check_risk_limits(self):
        """Check various risk limits and log warnings"""
        try:
            positions = await self.get_all_positions()
            
            # Check position count
            if len(positions) >= self.max_positions * 0.8:
                await self._log_risk_event(
                    'position_limit_warning', None,
                    f"Approaching position limit: {len(positions)}/{self.max_positions}"
                )
            
            # Check portfolio risk
            account = self.api.get_account()
            account_value = float(account.equity)
            total_risk = sum(pos.risk_amount or 0 for pos in positions)
            risk_pct = total_risk / account_value
            
            if risk_pct >= self.max_portfolio_risk * 0.8:
                await self._log_risk_event(
                    'portfolio_risk_warning', None,
                    f"High portfolio risk: {risk_pct:.1%}"
                )
                
        except Exception as e:
            logger.error(f"Error checking risk limits: {e}")
    
    async def _log_risk_event(self, event_type: str, symbol: Optional[str], 
                            description: str, severity: str = 'medium'):
        """Log a risk management event"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO risk_events (event_type, symbol, description, severity)
                VALUES (?, ?, ?, ?)
            ''', (event_type, symbol, description, severity))
            
            conn.commit()
            conn.close()
            
            logger.info(f"⚠️ Risk event logged: {event_type} - {description}")
            
        except Exception as e:
            logger.error(f"Error logging risk event: {e}")
    
    async def _calculate_win_rate(self) -> float:
        """Calculate win rate from closed positions"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) as wins
                FROM positions 
                WHERE status = 'closed' AND realized_pnl IS NOT NULL
            ''')
            
            row = cursor.fetchone()
            conn.close()
            
            if row and row[0] > 0:
                return (row[1] / row[0]) * 100
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Error calculating win rate: {e}")
            return 0.0
    
    async def _calculate_avg_hold_time(self) -> timedelta:
        """Calculate average holding time for closed positions"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT entry_time, exit_time 
                FROM positions 
                WHERE status = 'closed' AND exit_time IS NOT NULL
            ''')
            
            rows = cursor.fetchall()
            conn.close()
            
            if rows:
                total_seconds = 0
                for entry_str, exit_str in rows:
                    entry_time = datetime.fromisoformat(entry_str)
                    exit_time = datetime.fromisoformat(exit_str)
                    hold_time = exit_time - entry_time
                    total_seconds += hold_time.total_seconds()
                
                avg_seconds = total_seconds / len(rows)
                return timedelta(seconds=avg_seconds)
            
            return timedelta(0)
            
        except Exception as e:
            logger.error(f"Error calculating average hold time: {e}")
            return timedelta(0)
    
    def _get_recent_risk_events(self, days: int = 7) -> List[Dict]:
        """Get recent risk events"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            since_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            cursor.execute('''
                SELECT event_type, symbol, description, severity, triggered_at
                FROM risk_events 
                WHERE triggered_at >= ?
                ORDER BY triggered_at DESC
                LIMIT 10
            ''', (since_date,))
            
            rows = cursor.fetchall()
            conn.close()
            
            events = []
            for row in rows:
                events.append({
                    'event_type': row[0],
                    'symbol': row[1],
                    'description': row[2],
                    'severity': row[3],
                    'triggered_at': row[4]
                })
            
            return events
            
        except Exception as e:
            logger.error(f"Error getting recent risk events: {e}")
            return []
    
    def _generate_risk_warnings(self, portfolio_risk: float, max_position_size: float, 
                               position_count: int) -> List[str]:
        """Generate risk warnings based on current state"""
        warnings = []
        
        if portfolio_risk > self.max_portfolio_risk * 100:
            warnings.append(f"Portfolio risk ({portfolio_risk:.1f}%) exceeds limit ({self.max_portfolio_risk*100:.1f}%)")
        
        if max_position_size > self.max_position_size * 100:
            warnings.append(f"Position size ({max_position_size:.1f}%) exceeds limit ({self.max_position_size*100:.1f}%)")
        
        if position_count >= self.max_positions:
            warnings.append(f"Position count ({position_count}) at maximum ({self.max_positions})")
        
        if position_count >= self.max_positions * 0.9:
            warnings.append(f"Approaching position limit ({position_count}/{self.max_positions})")
        
        return warnings