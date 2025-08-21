#!/usr/bin/env python3
"""
Enhanced WebSocket Handler for Professional Trading Dashboard
Provides real-time market data, position updates, and Epic 1 signals
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from threading import Thread, Event
import pandas as pd

from flask_socketio import SocketIO, emit, join_room, leave_room
from services.unified_data_manager import UnifiedDataManager
from config.unified_config import get_config

logger = logging.getLogger(__name__)

class EnhancedWebSocketHandler:
    """Enhanced WebSocket handler for real-time trading data"""
    
    def __init__(self, socketio: SocketIO, data_manager: UnifiedDataManager):
        self.socketio = socketio
        self.data_manager = data_manager
        self.config = get_config()
        
        # Client management
        self.connected_clients = set()
        self.client_subscriptions = {}
        
        # Streaming control
        self.streaming_active = False
        self.streaming_thread = None
        self.stop_event = Event()
        
        # Performance tracking
        self.last_update_time = {}
        self.message_count = 0
        self.start_time = time.time()
        
        # Market data cache
        self.market_data_cache = {}
        self.last_prices = {}
        
        # Setup event handlers
        self.setup_socketio_events()
        
        logger.info("Enhanced WebSocket handler initialized")
    
    def setup_socketio_events(self):
        """Setup SocketIO event handlers"""
        
        @self.socketio.on('connect')
        def handle_connect():
            client_id = self.get_client_id()
            self.connected_clients.add(client_id)
            self.client_subscriptions[client_id] = {
                'symbols': set(),
                'timeframes': set(),
                'update_frequency': 1.0  # seconds
            }
            
            logger.info(f"Client {client_id} connected. Total clients: {len(self.connected_clients)}")
            
            # Send initial market status
            emit('market_status', self.get_market_status())
            
            # Start streaming if not already active
            if not self.streaming_active:
                self.start_real_time_streaming()
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            client_id = self.get_client_id()
            if client_id in self.connected_clients:
                self.connected_clients.remove(client_id)
                if client_id in self.client_subscriptions:
                    del self.client_subscriptions[client_id]
                
                logger.info(f"Client {client_id} disconnected. Total clients: {len(self.connected_clients)}")
                
                # Stop streaming if no clients
                if not self.connected_clients:
                    self.stop_real_time_streaming()
        
        @self.socketio.on('subscribe')
        def handle_subscribe(data):
            client_id = self.get_client_id()
            if client_id in self.client_subscriptions:
                symbol = data.get('symbol', '').upper()
                timeframe = data.get('timeframe', '15Min')
                
                self.client_subscriptions[client_id]['symbols'].add(symbol)
                self.client_subscriptions[client_id]['timeframes'].add(timeframe)
                
                # Join room for symbol updates
                join_room(f"symbol_{symbol}")
                
                logger.info(f"Client {client_id} subscribed to {symbol} on {timeframe}")
                
                # Send initial data for the symbol
                self.send_initial_data(symbol, timeframe)
        
        @self.socketio.on('unsubscribe')
        def handle_unsubscribe(data):
            client_id = self.get_client_id()
            if client_id in self.client_subscriptions:
                symbol = data.get('symbol', '').upper()
                
                if symbol in self.client_subscriptions[client_id]['symbols']:
                    self.client_subscriptions[client_id]['symbols'].remove(symbol)
                
                # Leave room
                leave_room(f"symbol_{symbol}")
                
                logger.info(f"Client {client_id} unsubscribed from {symbol}")
        
        @self.socketio.on('reduce_frequency')
        def handle_reduce_frequency():
            client_id = self.get_client_id()
            if client_id in self.client_subscriptions:
                self.client_subscriptions[client_id]['update_frequency'] = 5.0  # Reduce to 5 seconds
        
        @self.socketio.on('resume_frequency')
        def handle_resume_frequency():
            client_id = self.get_client_id()
            if client_id in self.client_subscriptions:
                self.client_subscriptions[client_id]['update_frequency'] = 1.0  # Back to 1 second
    
    def get_client_id(self):
        """Get unique client identifier"""
        from flask import request
        return f"{request.sid}_{int(time.time())}"
    
    def start_real_time_streaming(self):
        """Start real-time data streaming thread"""
        if not self.streaming_active:
            self.streaming_active = True
            self.stop_event.clear()
            self.streaming_thread = Thread(target=self._streaming_loop, daemon=True)
            self.streaming_thread.start()
            logger.info("Real-time streaming started")
    
    def stop_real_time_streaming(self):
        """Stop real-time data streaming"""
        if self.streaming_active:
            self.streaming_active = False
            self.stop_event.set()
            if self.streaming_thread:
                self.streaming_thread.join(timeout=5)
            logger.info("Real-time streaming stopped")
    
    def _streaming_loop(self):
        """Main streaming loop"""
        while self.streaming_active and not self.stop_event.is_set():
            try:
                # Get all subscribed symbols
                all_symbols = set()
                for client_subs in self.client_subscriptions.values():
                    all_symbols.update(client_subs['symbols'])
                
                if all_symbols:
                    # Update market data for all symbols
                    for symbol in all_symbols:
                        self.update_symbol_data(symbol)
                    
                    # Update account and position data
                    self.update_account_data()
                    self.update_positions_data()
                    
                    # Update Epic 1 signals
                    self.update_epic1_signals()
                
                # Sleep with configurable frequency
                min_frequency = min([
                    subs.get('update_frequency', 1.0) 
                    for subs in self.client_subscriptions.values()
                ] or [1.0])
                
                self.stop_event.wait(min_frequency)
                
            except Exception as e:
                logger.error(f"Error in streaming loop: {e}")
                self.stop_event.wait(1.0)
    
    def update_symbol_data(self, symbol: str):
        """Update real-time data for a symbol"""
        try:
            # Get latest price data
            current_price = self.data_manager.get_latest_price(symbol)
            if current_price is None:
                return
            
            # Check if price has changed significantly
            last_price = self.last_prices.get(symbol, 0)
            price_change = abs(current_price - last_price) if last_price else float('inf')
            price_change_pct = (price_change / last_price * 100) if last_price else float('inf')
            
            # Only broadcast if significant change or every 30 seconds
            should_update = (
                price_change_pct >= 0.01 or  # 0.01% change
                time.time() - self.last_update_time.get(symbol, 0) >= 30
            )
            
            if should_update:
                # Get candlestick data
                end_time = datetime.now()
                start_time = end_time - timedelta(minutes=1)
                
                bars = self.data_manager.get_historical_data(
                    symbol=symbol,
                    timeframe='1Min',
                    start=start_time,
                    end=end_time,
                    limit=1
                )
                
                if bars and not bars.empty:
                    latest_bar = bars.iloc[-1]
                    
                    market_data = {
                        'symbol': symbol,
                        'timestamp': datetime.now().isoformat(),
                        'price': current_price,
                        'change': current_price - last_price,
                        'change_percent': price_change_pct,
                        'candlestick': {
                            'time': latest_bar.name.timestamp(),
                            'open': float(latest_bar['open']),
                            'high': float(latest_bar['high']),
                            'low': float(latest_bar['low']),
                            'close': float(latest_bar['close']),
                            'volume': int(latest_bar.get('volume', 0))
                        }
                    }
                    
                    # Broadcast to subscribed clients
                    self.socketio.emit('market_data', market_data, room=f"symbol_{symbol}")
                    
                    # Update cache
                    self.last_prices[symbol] = current_price
                    self.last_update_time[symbol] = time.time()
                    self.message_count += 1
                    
                    logger.debug(f"Broadcasted market data for {symbol}: ${current_price:.2f}")
        
        except Exception as e:
            logger.error(f"Error updating symbol data for {symbol}: {e}")
    
    def update_account_data(self):
        """Update account information"""
        try:
            account_info = self.data_manager.get_account_info()
            if account_info:
                self.socketio.emit('account_update', {
                    'timestamp': datetime.now().isoformat(),
                    'account': account_info
                })
        except Exception as e:
            logger.error(f"Error updating account data: {e}")
    
    def update_positions_data(self):
        """Update positions information"""
        try:
            positions = self.data_manager.get_positions()
            if positions is not None:
                self.socketio.emit('position_update', {
                    'timestamp': datetime.now().isoformat(),
                    'positions': positions
                })
        except Exception as e:
            logger.error(f"Error updating positions data: {e}")
    
    def update_epic1_signals(self):
        """Update Epic 1 enhanced signals"""
        try:
            # Get all subscribed symbols
            all_symbols = set()
            for client_subs in self.client_subscriptions.values():
                all_symbols.update(client_subs['symbols'])
            
            for symbol in all_symbols:
                # Try to get Epic 1 enhanced signal
                try:
                    from src.utils.epic1_integration_helpers import get_epic1_enhanced_signal
                    epic1_signal = get_epic1_enhanced_signal(symbol, self.data_manager)
                    
                    if epic1_signal:
                        self.socketio.emit('signal_update', {
                            'timestamp': datetime.now().isoformat(),
                            'symbol': symbol,
                            'signal': epic1_signal.get('signal', 'HOLD'),
                            'confidence': epic1_signal.get('confidence', 0.5),
                            'epic1_enhanced': True,
                            'features': {
                                'dynamic_stochrsi': epic1_signal.get('dynamic_stochrsi', {}),
                                'volume_confirmation': epic1_signal.get('volume_confirmation', {}),
                                'multi_timeframe': epic1_signal.get('multi_timeframe', {})
                            }
                        }, room=f"symbol_{symbol}")
                        
                except Exception as e:
                    logger.debug(f"Epic 1 signal not available for {symbol}: {e}")
                    # Fallback to basic signal
                    basic_signal = self._get_basic_signal(symbol)
                    if basic_signal:
                        self.socketio.emit('signal_update', {
                            'timestamp': datetime.now().isoformat(),
                            'symbol': symbol,
                            'signal': basic_signal,
                            'epic1_enhanced': False
                        }, room=f"symbol_{symbol}")
        
        except Exception as e:
            logger.error(f"Error updating Epic 1 signals: {e}")
    
    def _get_basic_signal(self, symbol: str) -> str:
        """Get basic trading signal fallback"""
        try:
            # Simple price-based signal
            current_price = self.data_manager.get_latest_price(symbol)
            if current_price is None:
                return 'HOLD'
            
            # Get recent price history
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=1)
            
            bars = self.data_manager.get_historical_data(
                symbol=symbol,
                timeframe='5Min',
                start=start_time,
                end=end_time,
                limit=12
            )
            
            if bars is None or bars.empty:
                return 'HOLD'
            
            # Simple moving average crossover
            if len(bars) >= 10:
                short_ma = bars['close'].tail(5).mean()
                long_ma = bars['close'].tail(10).mean()
                
                if current_price > short_ma > long_ma:
                    return 'BUY'
                elif current_price < short_ma < long_ma:
                    return 'SELL'
            
            return 'HOLD'
            
        except Exception as e:
            logger.error(f"Error getting basic signal for {symbol}: {e}")
            return 'HOLD'
    
    def send_initial_data(self, symbol: str, timeframe: str):
        """Send initial data when client subscribes"""
        try:
            # Send historical chart data
            end_time = datetime.now()
            start_time = end_time - timedelta(days=1)
            
            bars = self.data_manager.get_historical_data(
                symbol=symbol,
                timeframe=timeframe,
                start=start_time,
                end=end_time,
                limit=1000
            )
            
            if bars is not None and not bars.empty:
                chart_data = []
                for timestamp, row in bars.iterrows():
                    chart_data.append({
                        'time': timestamp.timestamp(),
                        'open': float(row['open']),
                        'high': float(row['high']),
                        'low': float(row['low']),
                        'close': float(row['close']),
                        'volume': int(row.get('volume', 0))
                    })
                
                self.socketio.emit('initial_chart_data', {
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'data': chart_data
                })
        
        except Exception as e:
            logger.error(f"Error sending initial data for {symbol}: {e}")
    
    def get_market_status(self) -> Dict[str, Any]:
        """Get current market status"""
        now = datetime.now()
        # Convert to ET
        import pytz
        et_tz = pytz.timezone('America/New_York')
        et_time = now.astimezone(et_tz)
        
        hour = et_time.hour
        minute = et_time.minute
        current_minutes = hour * 60 + minute
        
        market_open = 9 * 60 + 30  # 9:30 AM
        market_close = 16 * 60  # 4:00 PM
        pre_market_start = 4 * 60  # 4:00 AM
        after_hours_end = 20 * 60  # 8:00 PM
        
        if current_minutes >= market_open and current_minutes < market_close:
            status = 'open'
            next_event = 'Market closes'
            next_time = f"{4}:00 PM ET"
        elif current_minutes >= pre_market_start and current_minutes < market_open:
            status = 'premarket'
            next_event = 'Market opens'
            next_time = f"{9}:30 AM ET"
        elif current_minutes >= market_close and current_minutes < after_hours_end:
            status = 'afterhours'
            next_event = 'After hours ends'
            next_time = f"{8}:00 PM ET"
        else:
            status = 'closed'
            next_event = 'Pre-market starts'
            next_time = f"{4}:00 AM ET"
        
        return {
            'status': status,
            'current_time': et_time.strftime('%H:%M:%S ET'),
            'next_event': next_event,
            'next_time': next_time,
            'trading_day': et_time.strftime('%Y-%m-%d')
        }
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get WebSocket connection statistics"""
        uptime = time.time() - self.start_time
        
        return {
            'connected_clients': len(self.connected_clients),
            'total_subscriptions': sum(len(subs['symbols']) for subs in self.client_subscriptions.values()),
            'messages_sent': self.message_count,
            'uptime_seconds': uptime,
            'streaming_active': self.streaming_active,
            'symbols_tracked': len(set().union(*[subs['symbols'] for subs in self.client_subscriptions.values()]))
        }