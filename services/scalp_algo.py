#!/usr/bin/env python3
"""
Scalping Algorithm with State Machine
Based on Alpaca's official example-scalping repository
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)

class AlgoState(Enum):
    """Trading states for the algorithm"""
    TO_BUY = "TO_BUY"  # Looking for buy signal
    BUY_SUBMITTED = "BUY_SUBMITTED"  # Buy order placed
    TO_SELL = "TO_SELL"  # Holding position, looking to sell
    SELL_SUBMITTED = "SELL_SUBMITTED"  # Sell order placed
    
class ScalpAlgo:
    """
    Scalping algorithm for a single symbol
    Implements proper state machine for order management
    """
    
    def __init__(self, api, symbol: str, lot_size: float = 100):
        self.api = api
        self.symbol = symbol
        self.lot_size = lot_size  # Dollar amount per trade
        
        # State management
        self.state = AlgoState.TO_BUY
        self.last_order_id = None
        self.position = None
        
        # Price tracking
        self.entry_price = 0
        self.last_price = 0
        self.bars = []  # Recent price bars
        
        # Timing
        self.buy_time = None
        self.max_hold_time = 300  # 5 minutes max hold
        self.order_timeout = 120  # 2 minutes order timeout
        
        # Risk management
        self.stop_loss_pct = 0.5  # 0.5% stop loss
        self.take_profit_pct = 0.3  # 0.3% take profit
        self.min_profit_pct = 0.1  # Minimum profit to exit
        
        # Statistics
        self.trades_won = 0
        self.trades_lost = 0
        self.total_pnl = 0
        
    async def initialize(self):
        """Initialize the algorithm with current position/order state"""
        try:
            # Check for existing position
            positions = self.api.list_positions()
            for pos in positions:
                if pos.symbol == self.symbol:
                    self.position = pos
                    self.entry_price = float(pos.avg_entry_price)
                    self.state = AlgoState.TO_SELL
                    logger.info(f"{self.symbol}: Found existing position {pos.qty} @ ${self.entry_price:.2f}")
                    break
            
            # Check for pending orders
            orders = self.api.list_orders(status='open')
            for order in orders:
                if order.symbol == self.symbol:
                    if order.side == 'buy':
                        self.state = AlgoState.BUY_SUBMITTED
                        self.last_order_id = order.id
                        logger.info(f"{self.symbol}: Found pending buy order {order.id}")
                    elif order.side == 'sell':
                        self.state = AlgoState.SELL_SUBMITTED
                        self.last_order_id = order.id
                        logger.info(f"{self.symbol}: Found pending sell order {order.id}")
                    break
                    
        except Exception as e:
            logger.error(f"{self.symbol}: Failed to initialize: {e}")
    
    def update_price(self, price: float):
        """Update the latest price"""
        self.last_price = price
        self.bars.append({'price': price, 'time': datetime.now()})
        # Keep only last 20 bars
        if len(self.bars) > 20:
            self.bars.pop(0)
    
    def calculate_buy_signal(self) -> bool:
        """Calculate if we should buy"""
        if len(self.bars) < 20:
            return False
        
        # Simple momentum strategy
        prices = [bar['price'] for bar in self.bars]
        sma_20 = sum(prices) / len(prices)
        sma_5 = sum(prices[-5:]) / 5
        
        # Buy when short MA crosses above long MA
        return sma_5 > sma_20 and self.last_price > sma_20
    
    def calculate_sell_signal(self) -> bool:
        """Calculate if we should sell"""
        if not self.position or self.entry_price == 0:
            return False
        
        current_pnl_pct = (self.last_price - self.entry_price) / self.entry_price * 100
        
        # Check stop loss
        if current_pnl_pct <= -self.stop_loss_pct:
            logger.info(f"{self.symbol}: Stop loss triggered at {current_pnl_pct:.2f}%")
            return True
        
        # Check take profit
        if current_pnl_pct >= self.take_profit_pct:
            logger.info(f"{self.symbol}: Take profit triggered at {current_pnl_pct:.2f}%")
            return True
        
        # Check max hold time
        if self.buy_time and (datetime.now() - self.buy_time).seconds > self.max_hold_time:
            if current_pnl_pct >= self.min_profit_pct:
                logger.info(f"{self.symbol}: Max hold time reached, exiting at {current_pnl_pct:.2f}%")
                return True
        
        return False
    
    async def check_and_cancel_old_order(self):
        """Cancel old orders that haven't filled"""
        if self.last_order_id:
            try:
                order = self.api.get_order(self.last_order_id)
                if order.status == 'pending_new' or order.status == 'accepted':
                    order_age = (datetime.now() - order.created_at).seconds
                    if order_age > self.order_timeout:
                        self.api.cancel_order(self.last_order_id)
                        logger.info(f"{self.symbol}: Cancelled old order {self.last_order_id}")
                        self.last_order_id = None
                        
                        # Reset state
                        if self.state == AlgoState.BUY_SUBMITTED:
                            self.state = AlgoState.TO_BUY
                        elif self.state == AlgoState.SELL_SUBMITTED:
                            self.state = AlgoState.TO_SELL
            except Exception as e:
                logger.error(f"{self.symbol}: Error checking order: {e}")
    
    async def run_step(self):
        """Run one step of the algorithm"""
        try:
            # State machine logic
            if self.state == AlgoState.TO_BUY:
                if self.calculate_buy_signal():
                    await self.submit_buy_order()
                    
            elif self.state == AlgoState.BUY_SUBMITTED:
                # Wait for fill or timeout
                await self.check_and_cancel_old_order()
                
            elif self.state == AlgoState.TO_SELL:
                if self.calculate_sell_signal():
                    await self.submit_sell_order()
                    
            elif self.state == AlgoState.SELL_SUBMITTED:
                # Wait for fill
                await self.check_and_cancel_old_order()
                
        except Exception as e:
            logger.error(f"{self.symbol}: Error in run_step: {e}")
    
    async def submit_buy_order(self):
        """Submit a buy order"""
        try:
            # Calculate quantity based on lot size
            qty = self.lot_size / self.last_price
            
            # Submit limit order slightly above current price
            limit_price = self.last_price * 1.001  # 0.1% above
            
            order = self.api.submit_order(
                symbol=self.symbol,
                qty=round(qty, 8),
                side='buy',
                type='limit',
                limit_price=round(limit_price, 2),
                time_in_force='gtc'
            )
            
            self.last_order_id = order.id
            self.state = AlgoState.BUY_SUBMITTED
            self.buy_time = datetime.now()
            
            logger.info(f"{self.symbol}: Buy order submitted - {qty:.4f} @ ${limit_price:.2f}")
            
        except Exception as e:
            logger.error(f"{self.symbol}: Failed to submit buy order: {e}")
    
    async def submit_sell_order(self):
        """Submit a sell order"""
        try:
            if not self.position:
                logger.error(f"{self.symbol}: No position to sell")
                return
            
            # Use limit order at or above entry price
            limit_price = max(self.entry_price * (1 + self.min_profit_pct/100), self.last_price)
            
            order = self.api.submit_order(
                symbol=self.symbol,
                qty=self.position.qty,
                side='sell',
                type='limit',
                limit_price=round(limit_price, 2),
                time_in_force='gtc'
            )
            
            self.last_order_id = order.id
            self.state = AlgoState.SELL_SUBMITTED
            
            logger.info(f"{self.symbol}: Sell order submitted - {self.position.qty} @ ${limit_price:.2f}")
            
        except Exception as e:
            logger.error(f"{self.symbol}: Failed to submit sell order: {e}")
    
    async def on_order_update(self, event: str, order: Any):
        """Handle order updates from websocket"""
        if order.id != self.last_order_id:
            return
        
        if event == 'fill':
            if order.side == 'buy':
                self.entry_price = float(order.filled_avg_price)
                self.state = AlgoState.TO_SELL
                logger.info(f"{self.symbol}: Buy filled at ${self.entry_price:.2f}")
                
            elif order.side == 'sell':
                exit_price = float(order.filled_avg_price)
                pnl = (exit_price - self.entry_price) * float(order.filled_qty)
                self.total_pnl += pnl
                
                if pnl > 0:
                    self.trades_won += 1
                else:
                    self.trades_lost += 1
                
                logger.info(f"{self.symbol}: Sell filled at ${exit_price:.2f}, P&L: ${pnl:.2f}")
                
                # Reset for next trade
                self.state = AlgoState.TO_BUY
                self.position = None
                self.entry_price = 0
                self.buy_time = None
                
        elif event == 'canceled' or event == 'rejected':
            logger.info(f"{self.symbol}: Order {event}: {order.id}")
            
            # Reset state
            if order.side == 'buy':
                self.state = AlgoState.TO_BUY
            else:
                self.state = AlgoState.TO_SELL
            
            self.last_order_id = None
    
    def get_status(self) -> Dict:
        """Get current status of the algorithm"""
        position_qty = float(self.position.qty) if self.position else 0
        current_pnl = 0
        
        if self.position and self.last_price > 0 and self.entry_price > 0:
            current_pnl = (self.last_price - self.entry_price) * position_qty
        
        return {
            'symbol': self.symbol,
            'state': self.state.value,
            'position': position_qty,
            'entry_price': self.entry_price,
            'last_price': self.last_price,
            'current_pnl': current_pnl,
            'total_pnl': self.total_pnl,
            'trades_won': self.trades_won,
            'trades_lost': self.trades_lost,
            'win_rate': self.trades_won / (self.trades_won + self.trades_lost) * 100 if (self.trades_won + self.trades_lost) > 0 else 0
        }