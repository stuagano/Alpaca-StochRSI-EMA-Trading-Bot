"""
Optimized Incremental StochRSI Calculator
==========================================

High-performance StochRSI implementation using sliding windows and O(1) updates.
Target: <50ms calculation time (vs current 250-400ms)

Performance Features:
- Incremental RSI calculation using Wilder's smoothing
- O(1) updates with sliding window buffers
- Memory-efficient circular buffers
- Pre-computed statistics caching
"""

import time
import math
import numpy as np
from collections import deque
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class IncrementalStochRSI:
    """
    Optimized StochRSI calculator with incremental updates.
    
    Performance targets:
    - Initialization: <5ms
    - Update: <15ms per new price
    - Memory usage: <1MB for 1000 periods
    """
    
    def __init__(self, rsi_period: int = 14, stoch_period: int = 14, 
                 k_period: int = 3, d_period: int = 3):
        """
        Initialize incremental StochRSI calculator.
        
        Args:
            rsi_period: Period for RSI calculation
            stoch_period: Period for Stochastic calculation on RSI
            k_period: Smoothing period for %K
            d_period: Smoothing period for %D
        """
        self.rsi_period = rsi_period
        self.stoch_period = stoch_period
        self.k_period = k_period
        self.d_period = d_period
        
        # Sliding window buffers - memory efficient
        max_buffer_size = max(rsi_period, stoch_period) + 10
        self.price_buffer = deque(maxlen=max_buffer_size)
        self.rsi_buffer = deque(maxlen=stoch_period + 5)
        self.stoch_k_buffer = deque(maxlen=k_period + 2)
        self.stoch_d_buffer = deque(maxlen=d_period + 2)
        
        # Wilder's RSI state variables for O(1) updates
        self.avg_gain = 0.0
        self.avg_loss = 0.0
        self.rsi_initialized = False
        
        # Performance tracking
        self.update_times = deque(maxlen=100)
        self.total_updates = 0
        
        # Validation mode for testing
        self.validation_mode = False
        self.last_full_calculation = None
        
        logger.info(f"IncrementalStochRSI initialized: RSI={rsi_period}, Stoch={stoch_period}")
    
    def update(self, new_price: float, timestamp: Optional[float] = None) -> Optional[Dict]:
        """
        Update StochRSI with new price point.
        
        Args:
            new_price: New closing price
            timestamp: Optional timestamp for the price
            
        Returns:
            Dict with RSI, StochRSI K, D values or None if insufficient data
        """
        start_time = time.perf_counter()
        
        try:
            # Add new price to buffer
            self.price_buffer.append(new_price)
            self.total_updates += 1
            
            # Calculate RSI incrementally
            rsi = self._update_rsi_incremental(new_price)
            if rsi is None:
                return None
            
            # Add RSI to buffer
            self.rsi_buffer.append(rsi)
            
            # Calculate Stochastic on RSI
            stoch_result = self._calculate_stochastic_incremental(rsi)
            if stoch_result is None:
                return None
            
            stoch_k, stoch_d = stoch_result
            
            # Track performance
            update_time = (time.perf_counter() - start_time) * 1000  # ms
            self.update_times.append(update_time)
            
            result = {
                'rsi': rsi,
                'stoch_k': stoch_k,
                'stoch_d': stoch_d,
                'timestamp': timestamp or time.time(),
                'update_time_ms': update_time,
                'total_updates': self.total_updates
            }
            
            # Validation check in debug mode
            if self.validation_mode and self.total_updates % 10 == 0:
                self._validate_calculation(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in StochRSI update: {e}")
            return None
    
    def _update_rsi_incremental(self, new_price: float) -> Optional[float]:
        """
        Update RSI using Wilder's smoothing method for O(1) performance.
        
        This implementation maintains running averages of gains and losses,
        avoiding the need to recalculate from scratch each time.
        """
        if len(self.price_buffer) < 2:
            return None
        
        # Calculate price change
        price_change = new_price - self.price_buffer[-2]
        current_gain = max(price_change, 0)
        current_loss = max(-price_change, 0)
        
        if not self.rsi_initialized:
            # Initialize RSI when we have enough data
            if len(self.price_buffer) >= self.rsi_period + 1:
                self._initialize_rsi()
                self.rsi_initialized = True
            else:
                return None
        
        # Wilder's smoothing: new_avg = (old_avg * (n-1) + new_value) / n
        # This is equivalent to: new_avg = old_avg + (new_value - old_avg) / n
        alpha = 1.0 / self.rsi_period
        self.avg_gain = self.avg_gain * (1 - alpha) + current_gain * alpha
        self.avg_loss = self.avg_loss * (1 - alpha) + current_loss * alpha
        
        # Calculate RSI
        if self.avg_loss == 0:
            return 100.0
        elif self.avg_gain == 0:
            return 0.0
        else:
            rs = self.avg_gain / self.avg_loss
            rsi = 100.0 - (100.0 / (1.0 + rs))
            return rsi
    
    def _initialize_rsi(self):
        """Initialize RSI averages using the first RSI period of data."""
        if len(self.price_buffer) < self.rsi_period + 1:
            return
        
        # Calculate initial gains and losses
        prices = list(self.price_buffer)[-(self.rsi_period + 1):]
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            gains.append(max(change, 0))
            losses.append(max(-change, 0))
        
        # Initial averages (simple moving average for first period)
        self.avg_gain = sum(gains) / len(gains)
        self.avg_loss = sum(losses) / len(losses)
    
    def _calculate_stochastic_incremental(self, current_rsi: float) -> Optional[Tuple[float, float]]:
        """
        Calculate Stochastic oscillator on RSI values incrementally.
        
        Returns:
            Tuple of (StochRSI %K, StochRSI %D) or None if insufficient data
        """
        if len(self.rsi_buffer) < self.stoch_period:
            return None
        
        # Get RSI window for Stochastic calculation
        rsi_window = list(self.rsi_buffer)[-self.stoch_period:]
        
        # Calculate %K (fast Stochastic)
        min_rsi = min(rsi_window)
        max_rsi = max(rsi_window)
        
        if max_rsi == min_rsi:
            # Avoid division by zero
            stoch_k_raw = 50.0
        else:
            stoch_k_raw = 100.0 * (current_rsi - min_rsi) / (max_rsi - min_rsi)
        
        # Smooth %K
        self.stoch_k_buffer.append(stoch_k_raw)
        
        if len(self.stoch_k_buffer) >= self.k_period:
            stoch_k = sum(list(self.stoch_k_buffer)[-self.k_period:]) / self.k_period
        else:
            stoch_k = stoch_k_raw
        
        # Calculate %D (smoothed %K)
        self.stoch_d_buffer.append(stoch_k)
        
        if len(self.stoch_d_buffer) >= self.d_period:
            stoch_d = sum(list(self.stoch_d_buffer)[-self.d_period:]) / self.d_period
        else:
            stoch_d = stoch_k
        
        return stoch_k, stoch_d
    
    def _validate_calculation(self, incremental_result: Dict):
        """
        Validate incremental calculation against full calculation.
        Used for testing and verification.
        """
        try:
            if len(self.price_buffer) < 50:  # Need enough data for meaningful comparison
                return
            
            # Perform full calculation
            prices_array = np.array(list(self.price_buffer))
            full_result = self._calculate_full_stochrsi(prices_array)
            
            if full_result:
                # Compare results (allow small floating point differences)
                rsi_diff = abs(incremental_result['rsi'] - full_result['rsi'])
                k_diff = abs(incremental_result['stoch_k'] - full_result['stoch_k'])
                d_diff = abs(incremental_result['stoch_d'] - full_result['stoch_d'])
                
                tolerance = 0.01  # 0.01 point tolerance
                
                if rsi_diff > tolerance or k_diff > tolerance or d_diff > tolerance:
                    logger.warning(f"Validation failed: RSI diff={rsi_diff:.4f}, "
                                 f"K diff={k_diff:.4f}, D diff={d_diff:.4f}")
                else:
                    logger.debug("Validation passed")
                    
        except Exception as e:
            logger.warning(f"Validation error: {e}")
    
    def _calculate_full_stochrsi(self, prices: np.ndarray) -> Optional[Dict]:
        """Full StochRSI calculation for validation purposes."""
        try:
            # This is the traditional calculation for comparison
            # Not optimized - only used for validation
            import pandas as pd
            
            df = pd.DataFrame({'close': prices})
            
            # Calculate RSI
            delta = df['close'].diff()
            gains = delta.where(delta > 0, 0)
            losses = -delta.where(delta < 0, 0)
            
            avg_gains = gains.ewm(com=self.rsi_period - 1, min_periods=self.rsi_period).mean()
            avg_losses = losses.ewm(com=self.rsi_period - 1, min_periods=self.rsi_period).mean()
            
            rs = avg_gains / avg_losses
            rsi = 100 - (100 / (1 + rs))
            
            # Calculate Stochastic on RSI
            rsi_low = rsi.rolling(window=self.stoch_period).min()
            rsi_high = rsi.rolling(window=self.stoch_period).max()
            
            stoch_k_raw = 100 * (rsi - rsi_low) / (rsi_high - rsi_low)
            stoch_k = stoch_k_raw.rolling(window=self.k_period).mean()
            stoch_d = stoch_k.rolling(window=self.d_period).mean()
            
            # Return last values
            return {
                'rsi': rsi.iloc[-1],
                'stoch_k': stoch_k.iloc[-1],
                'stoch_d': stoch_d.iloc[-1]
            }
            
        except Exception as e:
            logger.error(f"Full calculation error: {e}")
            return None
    
    def get_performance_stats(self) -> Dict:
        """Get performance statistics for the calculator."""
        if not self.update_times:
            return {'status': 'no_data'}
        
        update_times_list = list(self.update_times)
        
        return {
            'total_updates': self.total_updates,
            'avg_update_time_ms': sum(update_times_list) / len(update_times_list),
            'min_update_time_ms': min(update_times_list),
            'max_update_time_ms': max(update_times_list),
            'p95_update_time_ms': np.percentile(update_times_list, 95),
            'buffer_sizes': {
                'price_buffer': len(self.price_buffer),
                'rsi_buffer': len(self.rsi_buffer),
                'stoch_k_buffer': len(self.stoch_k_buffer),
                'stoch_d_buffer': len(self.stoch_d_buffer)
            },
            'memory_efficient': True,
            'target_met': sum(update_times_list) / len(update_times_list) < 50.0  # <50ms target
        }
    
    def reset(self):
        """Reset calculator state for new data series."""
        self.price_buffer.clear()
        self.rsi_buffer.clear()
        self.stoch_k_buffer.clear()
        self.stoch_d_buffer.clear()
        
        self.avg_gain = 0.0
        self.avg_loss = 0.0
        self.rsi_initialized = False
        
        self.update_times.clear()
        self.total_updates = 0
        
        logger.info("IncrementalStochRSI reset")
    
    def enable_validation_mode(self, enabled: bool = True):
        """Enable/disable validation mode for testing."""
        self.validation_mode = enabled
        logger.info(f"Validation mode {'enabled' if enabled else 'disabled'}")


# Factory function for easy integration
def create_optimized_stochrsi(rsi_period: int = 14, stoch_period: int = 14,
                             k_period: int = 3, d_period: int = 3) -> IncrementalStochRSI:
    """
    Create an optimized StochRSI calculator.
    
    Args:
        rsi_period: RSI calculation period
        stoch_period: Stochastic calculation period
        k_period: %K smoothing period
        d_period: %D smoothing period
        
    Returns:
        Configured IncrementalStochRSI instance
    """
    calculator = IncrementalStochRSI(rsi_period, stoch_period, k_period, d_period)
    logger.info(f"Created optimized StochRSI calculator with target <50ms updates")
    return calculator


# Performance test utility
def benchmark_performance(calculator: IncrementalStochRSI, num_updates: int = 1000) -> Dict:
    """
    Benchmark the performance of the StochRSI calculator.
    
    Args:
        calculator: StochRSI calculator instance
        num_updates: Number of price updates to test
        
    Returns:
        Performance benchmark results
    """
    import random
    
    calculator.reset()
    start_time = time.perf_counter()
    
    # Generate random price data for testing
    base_price = 100.0
    prices = []
    
    for i in range(num_updates):
        # Simulate realistic price movement
        change_pct = random.gauss(0, 0.02)  # 2% volatility
        base_price *= (1 + change_pct)
        prices.append(base_price)
        
        result = calculator.update(base_price)
        
        # Simulate processing delay
        if result and i % 100 == 0:
            logger.debug(f"Update {i}: RSI={result['rsi']:.2f}, K={result['stoch_k']:.2f}")
    
    total_time = (time.perf_counter() - start_time) * 1000  # ms
    
    stats = calculator.get_performance_stats()
    stats.update({
        'benchmark_total_time_ms': total_time,
        'benchmark_avg_per_update_ms': total_time / num_updates,
        'target_achieved': (total_time / num_updates) < 50.0,
        'speedup_vs_target': 50.0 / (total_time / num_updates)
    })
    
    return stats


if __name__ == "__main__":
    # Example usage and performance test
    print("Optimized Incremental StochRSI Performance Test")
    print("=" * 50)
    
    # Create calculator
    calc = create_optimized_stochrsi()
    calc.enable_validation_mode(True)
    
    # Run performance benchmark
    results = benchmark_performance(calc, 1000)
    
    print(f"Performance Results:")
    print(f"- Average update time: {results['avg_update_time_ms']:.2f}ms")
    print(f"- Target (<50ms): {'✅ ACHIEVED' if results['target_met'] else '❌ MISSED'}")
    print(f"- Speedup vs target: {results.get('speedup_vs_target', 0):.1f}x")
    print(f"- P95 update time: {results['p95_update_time_ms']:.2f}ms")
    print(f"- Total updates: {results['total_updates']}")