import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import threading
import time

class TrailingStopType(Enum):
    """Types of trailing stop mechanisms"""
    PERCENTAGE = "percentage"
    ATR_BASED = "atr_based"
    VOLATILITY_BASED = "volatility_based"
    SUPPORT_RESISTANCE = "support_resistance"
    ADAPTIVE = "adaptive"

@dataclass
class TrailingStopConfig:
    """Configuration for trailing stop"""
    stop_type: TrailingStopType
    initial_distance: float  # Initial stop distance (percentage or ATR multiplier)
    trail_distance: float    # Trailing distance
    activation_threshold: float  # Profit threshold to activate trailing (percentage)
    min_distance: float = 0.005  # Minimum 0.5% stop distance
    max_distance: float = 0.20   # Maximum 20% stop distance
    atr_period: int = 14
    atr_multiplier: float = 2.0
    update_frequency: int = 30  # Update frequency in seconds

@dataclass
class TrailingStopState:
    """State tracking for a trailing stop"""
    symbol: str
    entry_price: float
    current_price: float
    stop_price: float
    highest_price: float
    activation_price: float
    is_activated: bool = False
    last_update: datetime = field(default_factory=datetime.now)
    config: TrailingStopConfig = None
    position_size: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0

class TrailingStopManager:
    """
    Advanced trailing stop management with multiple strategies and safety features
    """
    
    def __init__(self):
        self.logger = logging.getLogger('risk.trailing_stop')
        self.active_stops: Dict[str, TrailingStopState] = {}
        self.price_history: Dict[str, List[Tuple[datetime, float]]] = {}
        self.running = False
        self.update_thread = None
        self.lock = threading.Lock()
        
        # Default configuration
        self.default_config = TrailingStopConfig(
            stop_type=TrailingStopType.PERCENTAGE,
            initial_distance=0.05,  # 5%
            trail_distance=0.02,    # 2%
            activation_threshold=0.03,  # 3% profit to activate
            min_distance=0.005,     # 0.5%
            max_distance=0.20,      # 20%
            update_frequency=30     # 30 seconds
        )
        
        self.logger.info("Trailing Stop Manager initialized")
    
    def add_trailing_stop(self, symbol: str, entry_price: float, 
                         position_size: float, config: TrailingStopConfig = None) -> bool:
        """
        Add a new trailing stop for a position
        
        Args:
            symbol: Trading symbol
            entry_price: Position entry price
            position_size: Position size (positive for long, negative for short)
            config: Trailing stop configuration
            
        Returns:
            Success flag
        """
        
        try:
            with self.lock:
                # Input validation
                if not symbol or entry_price <= 0 or position_size == 0:
                    self.logger.error(f"Invalid inputs: symbol='{symbol}', entry={entry_price}, size={position_size}")
                    return False
                
                if symbol in self.active_stops:
                    self.logger.warning(f"Trailing stop for {symbol} already exists, updating")
                
                # Use provided config or default
                if config is None:
                    config = self.default_config
                
                # Validate configuration
                config = self._validate_config(config)
                
                # Calculate initial stop price
                initial_stop = self._calculate_initial_stop(entry_price, position_size, config)
                
                # Calculate activation price
                activation_price = self._calculate_activation_price(entry_price, position_size, config)
                
                # Create trailing stop state
                stop_state = TrailingStopState(
                    symbol=symbol,
                    entry_price=entry_price,
                    current_price=entry_price,
                    stop_price=initial_stop,
                    highest_price=entry_price if position_size > 0 else entry_price,
                    activation_price=activation_price,
                    is_activated=False,
                    config=config,
                    position_size=position_size
                )
                
                self.active_stops[symbol] = stop_state
                
                # Initialize price history
                if symbol not in self.price_history:
                    self.price_history[symbol] = []
                
                self.logger.info(f"Trailing stop added for {symbol}: entry={entry_price:.4f}, "
                               f"initial_stop={initial_stop:.4f}, activation={activation_price:.4f}")
                
                # Start monitoring thread if not running
                if not self.running:
                    self.start_monitoring()
                
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to add trailing stop for {symbol}: {e}")
            return False
    
    def update_price(self, symbol: str, price: float) -> Optional[Dict[str, Any]]:
        """
        Update price for a symbol and check if stop should trigger
        
        Args:
            symbol: Trading symbol
            price: Current market price
            
        Returns:
            Stop trigger information if triggered, None otherwise
        """
        
        try:
            with self.lock:
                if symbol not in self.active_stops:
                    return None
                
                if price <= 0:
                    self.logger.error(f"Invalid price for {symbol}: {price}")
                    return None
                
                stop_state = self.active_stops[symbol]
                old_stop_price = stop_state.stop_price
                
                # Update current price
                stop_state.current_price = price
                stop_state.last_update = datetime.now()
                
                # Update price history
                self.price_history[symbol].append((datetime.now(), price))
                
                # Keep only recent price history (last 1000 points)
                if len(self.price_history[symbol]) > 1000:
                    self.price_history[symbol] = self.price_history[symbol][-1000:]
                
                # Update highest/lowest price based on position direction
                if stop_state.position_size > 0:  # Long position
                    if price > stop_state.highest_price:
                        stop_state.highest_price = price
                else:  # Short position
                    if price < stop_state.highest_price:  # For shorts, we track lowest price
                        stop_state.highest_price = price
                
                # Update P&L
                if stop_state.position_size > 0:
                    stop_state.unrealized_pnl = (price - stop_state.entry_price) * abs(stop_state.position_size)
                    stop_state.unrealized_pnl_pct = (price - stop_state.entry_price) / stop_state.entry_price * 100
                else:
                    stop_state.unrealized_pnl = (stop_state.entry_price - price) * abs(stop_state.position_size)
                    stop_state.unrealized_pnl_pct = (stop_state.entry_price - price) / stop_state.entry_price * 100
                
                # Check if trailing should be activated
                if not stop_state.is_activated:
                    should_activate = self._should_activate_trailing(stop_state)
                    if should_activate:
                        stop_state.is_activated = True
                        self.logger.info(f"Trailing stop activated for {symbol} at price {price:.4f}")
                
                # Update stop price if trailing is active
                if stop_state.is_activated:
                    new_stop_price = self._calculate_trailing_stop(stop_state)
                    if new_stop_price != stop_state.stop_price:
                        self.logger.info(f"Trailing stop updated for {symbol}: {stop_state.stop_price:.4f} -> {new_stop_price:.4f}")
                        stop_state.stop_price = new_stop_price
                
                # Check if stop should trigger
                stop_triggered = self._should_trigger_stop(stop_state)
                
                if stop_triggered:
                    trigger_info = {
                        'symbol': symbol,
                        'trigger_price': price,
                        'stop_price': stop_state.stop_price,
                        'entry_price': stop_state.entry_price,
                        'position_size': stop_state.position_size,
                        'unrealized_pnl': stop_state.unrealized_pnl,
                        'unrealized_pnl_pct': stop_state.unrealized_pnl_pct,
                        'highest_price': stop_state.highest_price,
                        'was_trailing': stop_state.is_activated,
                        'trigger_time': datetime.now().isoformat()
                    }
                    
                    # Remove from active stops
                    del self.active_stops[symbol]
                    
                    self.logger.info(f"Trailing stop triggered for {symbol}: "
                                   f"price={price:.4f}, stop={stop_state.stop_price:.4f}, "
                                   f"pnl={stop_state.unrealized_pnl_pct:.2f}%")
                    
                    return trigger_info
                
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to update price for {symbol}: {e}")
            return None
    
    def remove_trailing_stop(self, symbol: str) -> bool:
        """Remove trailing stop for a symbol"""
        
        try:
            with self.lock:
                if symbol in self.active_stops:
                    del self.active_stops[symbol]
                    self.logger.info(f"Trailing stop removed for {symbol}")
                    return True
                else:
                    self.logger.warning(f"No trailing stop found for {symbol}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Failed to remove trailing stop for {symbol}: {e}")
            return False
    
    def get_stop_status(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current status of trailing stop for a symbol"""
        
        try:
            with self.lock:
                if symbol not in self.active_stops:
                    return None
                
                stop_state = self.active_stops[symbol]
                
                return {
                    'symbol': symbol,
                    'entry_price': stop_state.entry_price,
                    'current_price': stop_state.current_price,
                    'stop_price': stop_state.stop_price,
                    'highest_price': stop_state.highest_price,
                    'activation_price': stop_state.activation_price,
                    'is_activated': stop_state.is_activated,
                    'position_size': stop_state.position_size,
                    'unrealized_pnl': stop_state.unrealized_pnl,
                    'unrealized_pnl_pct': stop_state.unrealized_pnl_pct,
                    'last_update': stop_state.last_update.isoformat(),
                    'stop_type': stop_state.config.stop_type.value,
                    'trail_distance': stop_state.config.trail_distance
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get stop status for {symbol}: {e}")
            return None
    
    def get_all_stops_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all active trailing stops"""
        
        try:
            with self.lock:
                status = {}
                for symbol in self.active_stops:
                    status[symbol] = self.get_stop_status(symbol)
                return status
                
        except Exception as e:
            self.logger.error(f"Failed to get all stops status: {e}")
            return {}
    
    def start_monitoring(self):
        """Start the monitoring thread"""
        
        if self.running:
            return
        
        self.running = True
        self.update_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.update_thread.start()
        self.logger.info("Trailing stop monitoring started")
    
    def stop_monitoring(self):
        """Stop the monitoring thread"""
        
        self.running = False
        if self.update_thread:
            self.update_thread.join(timeout=5)
        self.logger.info("Trailing stop monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        
        while self.running:
            try:
                # This is just a heartbeat - actual price updates come from external sources
                with self.lock:
                    active_count = len(self.active_stops)
                
                if active_count > 0:
                    self.logger.debug(f"Monitoring {active_count} trailing stops")
                
                time.sleep(self.default_config.update_frequency)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(5)  # Wait before retrying
    
    def _validate_config(self, config: TrailingStopConfig) -> TrailingStopConfig:
        """Validate and bound configuration parameters"""
        
        # Ensure distances are within reasonable bounds
        config.initial_distance = max(config.initial_distance, 0.001)  # Min 0.1%
        config.initial_distance = min(config.initial_distance, 0.50)   # Max 50%
        
        config.trail_distance = max(config.trail_distance, 0.001)      # Min 0.1%
        config.trail_distance = min(config.trail_distance, config.initial_distance)  # Can't trail more than initial
        
        config.activation_threshold = max(config.activation_threshold, 0.001)  # Min 0.1%
        config.activation_threshold = min(config.activation_threshold, 1.0)    # Max 100%
        
        config.min_distance = max(config.min_distance, 0.001)  # Min 0.1%
        config.max_distance = min(config.max_distance, 0.50)   # Max 50%
        
        if config.min_distance >= config.max_distance:
            config.min_distance = 0.005
            config.max_distance = 0.20
        
        config.atr_period = max(config.atr_period, 5)   # Min 5 periods
        config.atr_period = min(config.atr_period, 50)  # Max 50 periods
        
        config.atr_multiplier = max(config.atr_multiplier, 0.5)  # Min 0.5x
        config.atr_multiplier = min(config.atr_multiplier, 10.0) # Max 10x
        
        config.update_frequency = max(config.update_frequency, 5)    # Min 5 seconds
        config.update_frequency = min(config.update_frequency, 300)  # Max 5 minutes
        
        return config
    
    def _calculate_initial_stop(self, entry_price: float, position_size: float, 
                              config: TrailingStopConfig) -> float:
        """Calculate initial stop loss price"""
        
        try:
            if config.stop_type == TrailingStopType.PERCENTAGE:
                if position_size > 0:  # Long position
                    return entry_price * (1 - config.initial_distance)
                else:  # Short position
                    return entry_price * (1 + config.initial_distance)
            
            # For other types, start with percentage and refine later
            # TODO: Implement ATR-based, volatility-based, etc.
            if position_size > 0:
                return entry_price * (1 - config.initial_distance)
            else:
                return entry_price * (1 + config.initial_distance)
                
        except Exception as e:
            self.logger.error(f"Failed to calculate initial stop: {e}")
            # Fallback
            if position_size > 0:
                return entry_price * 0.95  # 5% stop for long
            else:
                return entry_price * 1.05  # 5% stop for short
    
    def _calculate_activation_price(self, entry_price: float, position_size: float, 
                                  config: TrailingStopConfig) -> float:
        """Calculate price at which trailing should activate"""
        
        if position_size > 0:  # Long position
            return entry_price * (1 + config.activation_threshold)
        else:  # Short position
            return entry_price * (1 - config.activation_threshold)
    
    def _should_activate_trailing(self, stop_state: TrailingStopState) -> bool:
        """Check if trailing should be activated"""
        
        if stop_state.position_size > 0:  # Long position
            return stop_state.current_price >= stop_state.activation_price
        else:  # Short position
            return stop_state.current_price <= stop_state.activation_price
    
    def _calculate_trailing_stop(self, stop_state: TrailingStopState) -> float:
        """Calculate new trailing stop price"""
        
        try:
            config = stop_state.config
            
            if config.stop_type == TrailingStopType.PERCENTAGE:
                if stop_state.position_size > 0:  # Long position
                    # Trail from highest price
                    new_stop = stop_state.highest_price * (1 - config.trail_distance)
                    # Only move stop up, never down
                    return max(new_stop, stop_state.stop_price)
                else:  # Short position
                    # Trail from lowest price (stored in highest_price for shorts)
                    new_stop = stop_state.highest_price * (1 + config.trail_distance)
                    # Only move stop down, never up
                    return min(new_stop, stop_state.stop_price)
            
            # TODO: Implement other trailing types
            return stop_state.stop_price
            
        except Exception as e:
            self.logger.error(f"Failed to calculate trailing stop: {e}")
            return stop_state.stop_price
    
    def _should_trigger_stop(self, stop_state: TrailingStopState) -> bool:
        """Check if stop should trigger"""
        
        try:
            if stop_state.position_size > 0:  # Long position
                return stop_state.current_price <= stop_state.stop_price
            else:  # Short position
                return stop_state.current_price >= stop_state.stop_price
                
        except Exception as e:
            self.logger.error(f"Failed to check stop trigger: {e}")
            return False

# Global trailing stop manager instance
_trailing_stop_manager = None

def get_trailing_stop_manager() -> TrailingStopManager:
    """Get singleton trailing stop manager instance"""
    global _trailing_stop_manager
    if _trailing_stop_manager is None:
        _trailing_stop_manager = TrailingStopManager()
    return _trailing_stop_manager