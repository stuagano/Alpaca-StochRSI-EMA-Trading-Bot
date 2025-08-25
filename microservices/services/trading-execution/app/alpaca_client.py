#!/usr/bin/env python3
"""
Alpaca Trading API Client for Trading Execution Service
"""

import os
import logging
import asyncio
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
import alpaca_trade_api as tradeapi
from alpaca_trade_api.rest import APIError, TimeFrame, TimeFrameUnit
from alpaca_trade_api.entity import Order as AlpacaOrder, Position as AlpacaPosition, Account as AlpacaAccount
from alpaca_trade_api.stream import Stream
import pandas as pd
import json

from .models import Order, OrderCreate, OrderUpdate, OrderStatus, OrderType, TimeInForce, OrderSide, AccountInfo, MarketDataQuote

logger = logging.getLogger(__name__)

class AlpacaClient:
    """Alpaca Trading API client with comprehensive functionality"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        base_url: Optional[str] = None,
        paper_trading: bool = True
    ):
        # Get credentials from environment if not provided
        self.api_key = api_key or os.getenv('APCA_API_KEY_ID')
        self.secret_key = secret_key or os.getenv('APCA_API_SECRET_KEY')
        self.base_url = base_url or os.getenv('APCA_BASE_URL', 'https://paper-api.alpaca.markets')
        self.paper_trading = paper_trading
        
        if not self.api_key or not self.secret_key:
            raise ValueError("Alpaca API credentials not provided")
        
        # Initialize REST API client
        self.api = tradeapi.REST(
            key_id=self.api_key,
            secret_key=self.secret_key,
            base_url=self.base_url,
            api_version='v2'
        )
        
        # Initialize streaming client
        self.stream = None
        self._stream_callbacks = {}
        
        logger.info(f"Alpaca client initialized for {'paper' if paper_trading else 'live'} trading")
    
    async def connect_stream(self):
        """Connect to Alpaca streaming API"""
        try:
            if not self.stream:
                self.stream = Stream(
                    key_id=self.api_key,
                    secret_key=self.secret_key,
                    base_url=self.base_url.replace('api', 'stream'),
                    data_feed='iex' if self.paper_trading else 'sip'
                )
            
            await self.stream._run_forever()
            logger.info("Connected to Alpaca streaming API")
            
        except Exception as e:
            logger.error(f"Failed to connect to Alpaca streaming: {e}")
            raise
    
    def disconnect_stream(self):
        """Disconnect from Alpaca streaming API"""
        if self.stream:
            self.stream.stop()
            logger.info("Disconnected from Alpaca streaming API")
    
    # Order Management Methods
    def submit_order(self, order_data: OrderCreate, user_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Submit order to Alpaca"""
        try:
            # Prepare order parameters
            order_params = self._prepare_order_params(order_data)
            
            # Submit to Alpaca
            alpaca_order = self.api.submit_order(**order_params)
            
            # Convert Alpaca order to our format
            order_dict = self._convert_alpaca_order(alpaca_order)
            order_dict['user_id'] = user_id
            
            logger.info(f"Order submitted successfully: {alpaca_order.id}")
            
            return True, {
                'alpaca_order': alpaca_order,
                'order_data': order_dict,
                'message': 'Order submitted successfully'
            }
            
        except APIError as e:
            error_msg = f"Alpaca API error: {e.message}"
            logger.error(error_msg)
            return False, {
                'error': error_msg,
                'code': e.code,
                'message': str(e)
            }
        except Exception as e:
            error_msg = f"Unexpected error submitting order: {str(e)}"
            logger.error(error_msg)
            return False, {
                'error': error_msg,
                'message': str(e)
            }
    
    def cancel_order(self, alpaca_order_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Cancel order in Alpaca"""
        try:
            self.api.cancel_order(alpaca_order_id)
            logger.info(f"Order canceled successfully: {alpaca_order_id}")
            return True, {'message': 'Order canceled successfully'}
            
        except APIError as e:
            error_msg = f"Failed to cancel order {alpaca_order_id}: {e.message}"
            logger.error(error_msg)
            return False, {
                'error': error_msg,
                'code': e.code,
                'message': str(e)
            }
        except Exception as e:
            error_msg = f"Unexpected error canceling order: {str(e)}"
            logger.error(error_msg)
            return False, {
                'error': error_msg,
                'message': str(e)
            }
    
    def replace_order(self, alpaca_order_id: str, updates: OrderUpdate) -> Tuple[bool, Dict[str, Any]]:
        """Replace/modify order in Alpaca"""
        try:
            # Prepare replacement parameters
            replace_params = {}
            
            if updates.quantity is not None:
                replace_params['qty'] = updates.quantity
            if updates.limit_price is not None:
                replace_params['limit_price'] = updates.limit_price
            if updates.stop_price is not None:
                replace_params['stop_price'] = updates.stop_price
            if updates.time_in_force is not None:
                replace_params['time_in_force'] = updates.time_in_force
            
            # Replace order
            alpaca_order = self.api.replace_order(alpaca_order_id, **replace_params)
            order_dict = self._convert_alpaca_order(alpaca_order)
            
            logger.info(f"Order replaced successfully: {alpaca_order_id}")
            return True, {
                'alpaca_order': alpaca_order,
                'order_data': order_dict,
                'message': 'Order replaced successfully'
            }
            
        except APIError as e:
            error_msg = f"Failed to replace order {alpaca_order_id}: {e.message}"
            logger.error(error_msg)
            return False, {
                'error': error_msg,
                'code': e.code,
                'message': str(e)
            }
        except Exception as e:
            error_msg = f"Unexpected error replacing order: {str(e)}"
            logger.error(error_msg)
            return False, {
                'error': error_msg,
                'message': str(e)
            }
    
    def get_order(self, alpaca_order_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Get order details from Alpaca"""
        try:
            alpaca_order = self.api.get_order(alpaca_order_id)
            order_dict = self._convert_alpaca_order(alpaca_order)
            
            return True, {
                'order_data': order_dict,
                'alpaca_order': alpaca_order
            }
            
        except APIError as e:
            error_msg = f"Failed to get order {alpaca_order_id}: {e.message}"
            logger.error(error_msg)
            return False, {
                'error': error_msg,
                'code': e.code,
                'message': str(e)
            }
        except Exception as e:
            error_msg = f"Unexpected error getting order: {str(e)}"
            logger.error(error_msg)
            return False, {
                'error': error_msg,
                'message': str(e)
            }
    
    def get_orders(
        self, 
        status: Optional[str] = None,
        limit: int = 50,
        after: Optional[datetime] = None,
        until: Optional[datetime] = None,
        direction: str = 'desc',
        nested: bool = True,
        symbols: Optional[List[str]] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """Get orders from Alpaca with filtering"""
        try:
            # Prepare parameters
            params = {
                'status': status,
                'limit': limit,
                'direction': direction,
                'nested': nested
            }
            
            if after:
                params['after'] = after.isoformat()
            if until:
                params['until'] = until.isoformat()
            if symbols:
                params['symbols'] = ','.join(symbols)
            
            # Remove None values
            params = {k: v for k, v in params.items() if v is not None}
            
            alpaca_orders = self.api.list_orders(**params)
            orders_data = [self._convert_alpaca_order(order) for order in alpaca_orders]
            
            return True, {
                'orders': orders_data,
                'count': len(orders_data)
            }
            
        except APIError as e:
            error_msg = f"Failed to get orders: {e.message}"
            logger.error(error_msg)
            return False, {
                'error': error_msg,
                'code': e.code,
                'message': str(e)
            }
        except Exception as e:
            error_msg = f"Unexpected error getting orders: {str(e)}"
            logger.error(error_msg)
            return False, {
                'error': error_msg,
                'message': str(e)
            }
    
    # Account Methods
    def get_account(self) -> Tuple[bool, Dict[str, Any]]:
        """Get account information from Alpaca"""
        try:
            alpaca_account = self.api.get_account()
            account_dict = self._convert_alpaca_account(alpaca_account)
            
            return True, {
                'account': account_dict,
                'alpaca_account': alpaca_account
            }
            
        except APIError as e:
            error_msg = f"Failed to get account: {e.message}"
            logger.error(error_msg)
            return False, {
                'error': error_msg,
                'code': e.code,
                'message': str(e)
            }
        except Exception as e:
            error_msg = f"Unexpected error getting account: {str(e)}"
            logger.error(error_msg)
            return False, {
                'error': error_msg,
                'message': str(e)
            }
    
    def get_positions(self) -> Tuple[bool, Dict[str, Any]]:
        """Get all positions from Alpaca"""
        try:
            alpaca_positions = self.api.list_positions()
            positions_data = [self._convert_alpaca_position(pos) for pos in alpaca_positions]
            
            return True, {
                'positions': positions_data,
                'count': len(positions_data)
            }
            
        except APIError as e:
            error_msg = f"Failed to get positions: {e.message}"
            logger.error(error_msg)
            return False, {
                'error': error_msg,
                'code': e.code,
                'message': str(e)
            }
        except Exception as e:
            error_msg = f"Unexpected error getting positions: {str(e)}"
            logger.error(error_msg)
            return False, {
                'error': error_msg,
                'message': str(e)
            }
    
    def get_position(self, symbol: str) -> Tuple[bool, Dict[str, Any]]:
        """Get specific position from Alpaca"""
        try:
            alpaca_position = self.api.get_position(symbol)
            position_data = self._convert_alpaca_position(alpaca_position)
            
            return True, {
                'position': position_data,
                'alpaca_position': alpaca_position
            }
            
        except APIError as e:
            if e.code == 40410000:  # Position not found
                return True, {'position': None, 'message': 'Position not found'}
            
            error_msg = f"Failed to get position {symbol}: {e.message}"
            logger.error(error_msg)
            return False, {
                'error': error_msg,
                'code': e.code,
                'message': str(e)
            }
        except Exception as e:
            error_msg = f"Unexpected error getting position: {str(e)}"
            logger.error(error_msg)
            return False, {
                'error': error_msg,
                'message': str(e)
            }
    
    def close_position(self, symbol: str, qty: Optional[str] = None, percentage: Optional[str] = None) -> Tuple[bool, Dict[str, Any]]:
        """Close position in Alpaca"""
        try:
            params = {}
            if qty:
                params['qty'] = qty
            if percentage:
                params['percentage'] = percentage
            
            alpaca_order = self.api.close_position(symbol, **params)
            order_dict = self._convert_alpaca_order(alpaca_order)
            
            logger.info(f"Position closed successfully: {symbol}")
            return True, {
                'order_data': order_dict,
                'message': 'Position closed successfully'
            }
            
        except APIError as e:
            error_msg = f"Failed to close position {symbol}: {e.message}"
            logger.error(error_msg)
            return False, {
                'error': error_msg,
                'code': e.code,
                'message': str(e)
            }
        except Exception as e:
            error_msg = f"Unexpected error closing position: {str(e)}"
            logger.error(error_msg)
            return False, {
                'error': error_msg,
                'message': str(e)
            }
    
    # Market Data Methods
    def get_latest_quote(self, symbol: str) -> Tuple[bool, Dict[str, Any]]:
        """Get latest quote for symbol"""
        try:
            latest_quote = self.api.get_latest_quote(symbol)
            quote_data = {
                'symbol': symbol,
                'bid_price': float(latest_quote.bidprice) if latest_quote.bidprice else None,
                'ask_price': float(latest_quote.askprice) if latest_quote.askprice else None,
                'bid_size': int(latest_quote.bidsize) if latest_quote.bidsize else None,
                'ask_size': int(latest_quote.asksize) if latest_quote.asksize else None,
                'timestamp': latest_quote.timestamp
            }
            
            return True, {'quote': quote_data}
            
        except APIError as e:
            error_msg = f"Failed to get quote for {symbol}: {e.message}"
            logger.error(error_msg)
            return False, {
                'error': error_msg,
                'code': e.code,
                'message': str(e)
            }
        except Exception as e:
            error_msg = f"Unexpected error getting quote: {str(e)}"
            logger.error(error_msg)
            return False, {
                'error': error_msg,
                'message': str(e)
            }
    
    def get_latest_trade(self, symbol: str) -> Tuple[bool, Dict[str, Any]]:
        """Get latest trade for symbol"""
        try:
            latest_trade = self.api.get_latest_trade(symbol)
            trade_data = {
                'symbol': symbol,
                'price': float(latest_trade.price) if latest_trade.price else None,
                'size': int(latest_trade.size) if latest_trade.size else None,
                'timestamp': latest_trade.timestamp,
                'conditions': getattr(latest_trade, 'conditions', [])
            }
            
            return True, {'trade': trade_data}
            
        except APIError as e:
            error_msg = f"Failed to get trade for {symbol}: {e.message}"
            logger.error(error_msg)
            return False, {
                'error': error_msg,
                'code': e.code,
                'message': str(e)
            }
        except Exception as e:
            error_msg = f"Unexpected error getting trade: {str(e)}"
            logger.error(error_msg)
            return False, {
                'error': error_msg,
                'message': str(e)
            }
    
    def get_bars(
        self,
        symbols: List[str],
        timeframe: str = '1Day',
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """Get historical bars for symbols"""
        try:
            # Convert timeframe string to TimeFrame object
            timeframe_obj = TimeFrame.Day if timeframe == '1Day' else TimeFrame.Minute
            
            # Get bars
            bars = self.api.get_bars(
                symbols,
                timeframe_obj,
                start=start,
                end=end,
                limit=limit,
                adjustment='raw'
            )
            
            # Convert to more usable format
            bars_data = {}
            for symbol in symbols:
                if symbol in bars:
                    bars_data[symbol] = [
                        {
                            'timestamp': bar.timestamp,
                            'open': float(bar.open),
                            'high': float(bar.high),
                            'low': float(bar.low),
                            'close': float(bar.close),
                            'volume': int(bar.volume),
                            'trade_count': getattr(bar, 'trade_count', None),
                            'vwap': float(getattr(bar, 'vwap', 0)) if getattr(bar, 'vwap', None) else None
                        }
                        for bar in bars[symbol]
                    ]
                else:
                    bars_data[symbol] = []
            
            return True, {'bars': bars_data}
            
        except APIError as e:
            error_msg = f"Failed to get bars: {e.message}"
            logger.error(error_msg)
            return False, {
                'error': error_msg,
                'code': e.code,
                'message': str(e)
            }
        except Exception as e:
            error_msg = f"Unexpected error getting bars: {str(e)}"
            logger.error(error_msg)
            return False, {
                'error': error_msg,
                'message': str(e)
            }
    
    # Utility Methods
    def _prepare_order_params(self, order_data: OrderCreate) -> Dict[str, Any]:
        """Prepare order parameters for Alpaca API"""
        params = {
            'symbol': order_data.symbol,
            'side': order_data.side.value,
            'type': order_data.order_type.value,
            'time_in_force': order_data.time_in_force.value,
        }
        
        # Quantity or notional
        if order_data.quantity:
            params['qty'] = order_data.quantity
        elif order_data.notional:
            params['notional'] = order_data.notional
        
        # Price parameters
        if order_data.limit_price:
            params['limit_price'] = order_data.limit_price
        if order_data.stop_price:
            params['stop_price'] = order_data.stop_price
        if order_data.trail_price:
            params['trail_price'] = order_data.trail_price
        if order_data.trail_percent:
            params['trail_percent'] = order_data.trail_percent
        
        # Extended hours
        if order_data.extended_hours:
            params['extended_hours'] = order_data.extended_hours
        
        # Client order ID
        if order_data.client_order_id:
            params['client_order_id'] = order_data.client_order_id
        
        # Order class (bracket, oco, etc.)
        if order_data.order_class and order_data.order_class != 'simple':
            params['order_class'] = order_data.order_class.value
            
            # Bracket order parameters
            if order_data.take_profit_limit_price:
                params['take_profit'] = {'limit_price': order_data.take_profit_limit_price}
            
            if order_data.stop_loss_stop_price:
                stop_loss_params = {'stop_price': order_data.stop_loss_stop_price}
                if order_data.stop_loss_limit_price:
                    stop_loss_params['limit_price'] = order_data.stop_loss_limit_price
                params['stop_loss'] = stop_loss_params
        
        return params
    
    def _convert_alpaca_order(self, alpaca_order: AlpacaOrder) -> Dict[str, Any]:
        """Convert Alpaca order to our order format"""
        return {
            'alpaca_order_id': alpaca_order.id,
            'client_order_id': alpaca_order.client_order_id,
            'symbol': alpaca_order.symbol,
            'asset_id': alpaca_order.asset_id,
            'asset_class': alpaca_order.asset_class,
            'quantity': int(alpaca_order.qty) if alpaca_order.qty else None,
            'notional': float(alpaca_order.notional) if getattr(alpaca_order, 'notional', None) else None,
            'side': alpaca_order.side,
            'order_type': alpaca_order.order_type,
            'time_in_force': alpaca_order.time_in_force,
            'limit_price': float(alpaca_order.limit_price) if alpaca_order.limit_price else None,
            'stop_price': float(alpaca_order.stop_price) if alpaca_order.stop_price else None,
            'trail_price': float(alpaca_order.trail_price) if getattr(alpaca_order, 'trail_price', None) else None,
            'trail_percent': float(alpaca_order.trail_percent) if getattr(alpaca_order, 'trail_percent', None) else None,
            'filled_qty': int(alpaca_order.filled_qty) if alpaca_order.filled_qty else 0,
            'filled_avg_price': float(alpaca_order.filled_avg_price) if alpaca_order.filled_avg_price else None,
            'status': alpaca_order.status,
            'created_at': alpaca_order.created_at,
            'updated_at': alpaca_order.updated_at,
            'submitted_at': alpaca_order.submitted_at,
            'filled_at': alpaca_order.filled_at,
            'canceled_at': alpaca_order.canceled_at,
            'expired_at': alpaca_order.expired_at,
            'extended_hours': alpaca_order.extended_hours,
            'order_class': getattr(alpaca_order, 'order_class', 'simple'),
        }
    
    def _convert_alpaca_account(self, alpaca_account: AlpacaAccount) -> Dict[str, Any]:
        """Convert Alpaca account to our account format"""
        return {
            'id': alpaca_account.id,
            'account_number': alpaca_account.account_number,
            'status': alpaca_account.status,
            'currency': alpaca_account.currency,
            'buying_power': float(alpaca_account.buying_power),
            'regt_buying_power': float(alpaca_account.regt_buying_power),
            'daytrading_buying_power': float(alpaca_account.daytrading_buying_power),
            'cash': float(alpaca_account.cash),
            'portfolio_value': float(alpaca_account.portfolio_value),
            'equity': float(alpaca_account.equity),
            'last_equity': float(alpaca_account.last_equity),
            'multiplier': int(alpaca_account.multiplier),
            'day_trade_count': int(alpaca_account.day_trade_count),
            'pattern_day_trader': bool(alpaca_account.pattern_day_trader),
            'trading_blocked': bool(alpaca_account.trading_blocked),
            'transfers_blocked': bool(alpaca_account.transfers_blocked),
            'account_blocked': bool(alpaca_account.account_blocked),
            'created_at': alpaca_account.created_at,
            'trade_suspended_by_user': bool(alpaca_account.trade_suspended_by_user),
            'shorting_enabled': bool(alpaca_account.shorting_enabled),
            'long_market_value': float(alpaca_account.long_market_value),
            'short_market_value': float(alpaca_account.short_market_value),
            'accrued_fees': float(alpaca_account.accrued_fees),
            'pending_transfer_in': float(alpaca_account.pending_transfer_in) if getattr(alpaca_account, 'pending_transfer_in', None) else None
        }
    
    def _convert_alpaca_position(self, alpaca_position: AlpacaPosition) -> Dict[str, Any]:
        """Convert Alpaca position to our position format"""
        return {
            'symbol': alpaca_position.symbol,
            'asset_id': alpaca_position.asset_id,
            'asset_class': alpaca_position.asset_class,
            'quantity': int(alpaca_position.qty),
            'side': 'long' if int(alpaca_position.qty) > 0 else 'short',
            'market_value': float(alpaca_position.market_value),
            'cost_basis': float(alpaca_position.cost_basis),
            'unrealized_pnl': float(alpaca_position.unrealized_pl),
            'unrealized_pnl_percent': float(alpaca_position.unrealized_plpc),
            'avg_entry_price': float(alpaca_position.avg_entry_price),
            'current_price': float(alpaca_position.current_price) if getattr(alpaca_position, 'current_price', None) else None,
            'lastday_price': float(alpaca_position.lastday_price) if getattr(alpaca_position, 'lastday_price', None) else None,
            'change_today': float(alpaca_position.change_today) if getattr(alpaca_position, 'change_today', None) else None
        }
    
    def health_check(self) -> bool:
        """Check if Alpaca API is accessible"""
        try:
            self.api.get_account()
            return True
        except Exception as e:
            logger.error(f"Alpaca health check failed: {e}")
            return False

# Singleton instance
alpaca_client = AlpacaClient()