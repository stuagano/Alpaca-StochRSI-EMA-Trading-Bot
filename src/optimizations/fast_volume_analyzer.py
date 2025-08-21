"""
Fast Volume Confirmation System
==============================

Optimized volume analysis with pre-computed metrics and incremental updates.
Target: <25ms validation time (vs current 50-100ms)

Performance Features:
- Pre-computed rolling volume statistics
- O(1) volume metric updates
- Cached relative volume calculations
- Fast signal confirmation logic
"""

import time
import math
import numpy as np
from collections import deque
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class VolumeConfirmationResult:
    """Fast volume confirmation result."""
    confirmed: bool
    relative_volume: float
    volume_percentile: float
    confidence: float
    threshold_used: float
    processing_time_ms: float
    reason: str


@dataclass
class VolumeMetrics:
    """Pre-computed volume metrics for fast access."""
    avg_volume: float
    volume_std: float
    median_volume: float
    p75_volume: float
    p90_volume: float
    last_update: float


class FastVolumeAnalyzer:
    """
    High-performance volume analyzer with incremental updates.
    
    Performance targets:
    - Volume metric update: <5ms
    - Signal confirmation: <10ms
    - Total processing: <25ms
    """
    
    def __init__(self, lookback_period: int = 20, percentile_period: int = 100):
        """
        Initialize fast volume analyzer.
        
        Args:
            lookback_period: Period for rolling volume average
            percentile_period: Period for volume percentile calculations
        """
        self.lookback_period = lookback_period
        self.percentile_period = percentile_period
        
        # Efficient circular buffers
        self.volume_buffer = deque(maxlen=lookback_period)
        self.extended_volume_buffer = deque(maxlen=percentile_period)
        
        # Pre-computed metrics for O(1) access
        self.volume_sum = 0.0
        self.volume_sum_sq = 0.0  # For variance calculation
        self.metrics = VolumeMetrics(0, 0, 0, 0, 0, 0)
        
        # Cached percentiles (updated periodically)
        self.percentile_cache = {}
        self.last_percentile_update = 0
        self.percentile_update_interval = 5.0  # seconds
        
        # Performance tracking
        self.update_times = deque(maxlen=100)
        self.confirmation_times = deque(maxlen=100)
        self.total_confirmations = 0
        
        # Configuration thresholds
        self.buy_threshold = 1.2  # 20% above average for buy signals
        self.sell_threshold = 1.5  # 50% above average for sell signals
        self.high_confidence_threshold = 2.0  # 100% above average
        
        logger.info(f"FastVolumeAnalyzer initialized: lookback={lookback_period}, "
                   f"percentile_period={percentile_period}")
    
    def update_volume_metrics(self, new_volume: float, timestamp: Optional[float] = None) -> VolumeMetrics:
        """
        Update volume metrics incrementally with O(1) performance.
        
        Args:
            new_volume: New volume value
            timestamp: Optional timestamp
            
        Returns:
            Updated volume metrics
        """
        start_time = time.perf_counter()
        
        try:
            current_time = timestamp or time.time()
            
            # Handle buffer overflow (remove oldest volume)
            if len(self.volume_buffer) == self.lookback_period:
                old_volume = self.volume_buffer[0]
                self.volume_sum -= old_volume
                self.volume_sum_sq -= old_volume * old_volume
            
            # Add new volume
            self.volume_buffer.append(new_volume)
            self.extended_volume_buffer.append(new_volume)
            self.volume_sum += new_volume
            self.volume_sum_sq += new_volume * new_volume
            
            # Update basic metrics (O(1) operations)
            n = len(self.volume_buffer)
            if n > 0:
                self.metrics.avg_volume = self.volume_sum / n
                
                # Calculate standard deviation incrementally
                if n > 1:
                    variance = (self.volume_sum_sq - (self.volume_sum * self.volume_sum / n)) / (n - 1)
                    self.metrics.volume_std = math.sqrt(max(0, variance))
                else:
                    self.metrics.volume_std = 0
            
            # Update percentiles periodically (not every update for performance)
            if current_time - self.last_percentile_update > self.percentile_update_interval:
                self._update_percentiles_cached()
                self.last_percentile_update = current_time
            
            self.metrics.last_update = current_time
            
            # Track performance
            update_time = (time.perf_counter() - start_time) * 1000
            self.update_times.append(update_time)
            
            return self.metrics
            
        except Exception as e:
            logger.error(f"Error updating volume metrics: {e}")
            return self.metrics
    
    def _update_percentiles_cached(self):
        """Update cached percentiles from extended buffer."""
        if len(self.extended_volume_buffer) < 10:
            return
        
        try:
            volumes = np.array(list(self.extended_volume_buffer))
            
            # Calculate key percentiles
            self.percentile_cache = {
                'p25': np.percentile(volumes, 25),
                'p50': np.percentile(volumes, 50),  # median
                'p75': np.percentile(volumes, 75),
                'p90': np.percentile(volumes, 90),
                'p95': np.percentile(volumes, 95)
            }
            
            # Update metrics object
            self.metrics.median_volume = self.percentile_cache['p50']
            self.metrics.p75_volume = self.percentile_cache['p75']
            self.metrics.p90_volume = self.percentile_cache['p90']
            
        except Exception as e:
            logger.warning(f"Error updating percentiles: {e}")
    
    def quick_volume_confirmation(self, current_volume: float, signal_type: str,
                                signal_strength: float = 1.0) -> VolumeConfirmationResult:
        """
        Fast volume confirmation for trading signals.
        
        Args:
            current_volume: Current volume to check
            signal_type: 'BUY', 'SELL', 'OVERSOLD', 'OVERBOUGHT', etc.
            signal_strength: Signal strength (0.0 to 1.0)
            
        Returns:
            Volume confirmation result
        """
        start_time = time.perf_counter()
        self.total_confirmations += 1
        
        try:
            # Quick validation
            if self.metrics.avg_volume <= 0:
                return VolumeConfirmationResult(
                    confirmed=False,
                    relative_volume=0,
                    volume_percentile=0,
                    confidence=0,
                    threshold_used=0,
                    processing_time_ms=0,
                    reason="insufficient_volume_history"
                )
            
            # Calculate relative volume (fast O(1) operation)
            relative_volume = current_volume / self.metrics.avg_volume
            
            # Determine threshold based on signal type
            if signal_type in ['BUY', 'OVERSOLD']:
                threshold = self.buy_threshold
            elif signal_type in ['SELL', 'OVERBOUGHT']:
                threshold = self.sell_threshold
            else:
                threshold = self.buy_threshold  # Default
            
            # Adjust threshold based on signal strength
            adjusted_threshold = threshold * (0.8 + 0.4 * signal_strength)
            
            # Quick confirmation check
            confirmed = relative_volume >= adjusted_threshold
            
            # Calculate volume percentile (using cached values)
            volume_percentile = self._get_volume_percentile_fast(current_volume)
            
            # Calculate confidence score
            if confirmed:
                confidence = min(relative_volume / adjusted_threshold, 2.0)
                if relative_volume >= self.high_confidence_threshold:
                    confidence *= 1.2  # Boost for very high volume
            else:
                confidence = 0.0
            
            # Determine reason
            if confirmed:
                if relative_volume >= self.high_confidence_threshold:
                    reason = "high_volume_confirmed"
                else:
                    reason = "volume_confirmed"
            else:
                reason = f"volume_below_threshold_{adjusted_threshold:.2f}"
            
            # Track performance
            processing_time = (time.perf_counter() - start_time) * 1000
            self.confirmation_times.append(processing_time)
            
            return VolumeConfirmationResult(
                confirmed=confirmed,
                relative_volume=relative_volume,
                volume_percentile=volume_percentile,
                confidence=confidence,
                threshold_used=adjusted_threshold,
                processing_time_ms=processing_time,
                reason=reason
            )
            
        except Exception as e:
            logger.error(f"Error in volume confirmation: {e}")
            return VolumeConfirmationResult(
                confirmed=False,
                relative_volume=0,
                volume_percentile=0,
                confidence=0,
                threshold_used=0,
                processing_time_ms=0,
                reason=f"error_{str(e)}"
            )
    
    def _get_volume_percentile_fast(self, volume: float) -> float:
        """
        Get volume percentile using cached percentiles for fast lookup.
        
        Args:
            volume: Volume to get percentile for
            
        Returns:
            Estimated percentile (0-100)
        """
        if not self.percentile_cache:
            return 50.0  # Default to median
        
        try:
            # Use cached percentiles for fast estimation
            cache = self.percentile_cache
            
            if volume <= cache['p25']:
                return 25.0 * (volume / cache['p25']) if cache['p25'] > 0 else 0
            elif volume <= cache['p50']:
                ratio = (volume - cache['p25']) / (cache['p50'] - cache['p25'])
                return 25.0 + 25.0 * ratio
            elif volume <= cache['p75']:
                ratio = (volume - cache['p50']) / (cache['p75'] - cache['p50'])
                return 50.0 + 25.0 * ratio
            elif volume <= cache['p90']:
                ratio = (volume - cache['p75']) / (cache['p90'] - cache['p75'])
                return 75.0 + 15.0 * ratio
            elif volume <= cache['p95']:
                ratio = (volume - cache['p90']) / (cache['p95'] - cache['p90'])
                return 90.0 + 5.0 * ratio
            else:
                return 95.0 + 5.0 * min((volume - cache['p95']) / cache['p95'], 1.0)
                
        except Exception as e:
            logger.warning(f"Error calculating volume percentile: {e}")
            return 50.0
    
    def batch_confirm_signals(self, signals: List[Dict]) -> List[VolumeConfirmationResult]:
        """
        Batch process multiple signals for efficiency.
        
        Args:
            signals: List of signal dictionaries with 'volume', 'type', 'strength'
            
        Returns:
            List of confirmation results
        """
        start_time = time.perf_counter()
        results = []
        
        for signal in signals:
            volume = signal.get('volume', 0)
            signal_type = signal.get('type', 'BUY')
            strength = signal.get('strength', 1.0)
            
            result = self.quick_volume_confirmation(volume, signal_type, strength)
            results.append(result)
        
        batch_time = (time.perf_counter() - start_time) * 1000
        logger.debug(f"Batch processed {len(signals)} signals in {batch_time:.2f}ms")
        
        return results
    
    def get_performance_stats(self) -> Dict:
        """Get performance statistics for the analyzer."""
        if not self.update_times and not self.confirmation_times:
            return {'status': 'no_data'}
        
        update_times = list(self.update_times)
        confirmation_times = list(self.confirmation_times)
        
        stats = {
            'total_confirmations': self.total_confirmations,
            'buffer_sizes': {
                'volume_buffer': len(self.volume_buffer),
                'extended_buffer': len(self.extended_volume_buffer)
            },
            'current_metrics': {
                'avg_volume': self.metrics.avg_volume,
                'volume_std': self.metrics.volume_std,
                'last_update': self.metrics.last_update
            }
        }
        
        if update_times:
            stats['update_performance'] = {
                'avg_update_time_ms': sum(update_times) / len(update_times),
                'max_update_time_ms': max(update_times),
                'p95_update_time_ms': np.percentile(update_times, 95),
                'target_met': sum(update_times) / len(update_times) < 5.0  # <5ms target
            }
        
        if confirmation_times:
            avg_confirmation_time = sum(confirmation_times) / len(confirmation_times)
            stats['confirmation_performance'] = {
                'avg_confirmation_time_ms': avg_confirmation_time,
                'max_confirmation_time_ms': max(confirmation_times),
                'p95_confirmation_time_ms': np.percentile(confirmation_times, 95),
                'target_met': avg_confirmation_time < 25.0  # <25ms target
            }
        
        # Overall performance assessment
        total_avg_time = 0
        if update_times and confirmation_times:
            total_avg_time = (sum(update_times) / len(update_times) + 
                            sum(confirmation_times) / len(confirmation_times))
            stats['overall_target_met'] = total_avg_time < 25.0
            stats['speedup_vs_target'] = 25.0 / total_avg_time if total_avg_time > 0 else 0
        
        return stats
    
    def reset(self):
        """Reset analyzer state for new data series."""
        self.volume_buffer.clear()
        self.extended_volume_buffer.clear()
        
        self.volume_sum = 0.0
        self.volume_sum_sq = 0.0
        self.metrics = VolumeMetrics(0, 0, 0, 0, 0, 0)
        
        self.percentile_cache.clear()
        self.last_percentile_update = 0
        
        self.update_times.clear()
        self.confirmation_times.clear()
        self.total_confirmations = 0
        
        logger.info("FastVolumeAnalyzer reset")
    
    def set_thresholds(self, buy_threshold: float = None, sell_threshold: float = None,
                      high_confidence_threshold: float = None):
        """
        Update confirmation thresholds.
        
        Args:
            buy_threshold: Relative volume threshold for buy signals
            sell_threshold: Relative volume threshold for sell signals
            high_confidence_threshold: Threshold for high confidence signals
        """
        if buy_threshold is not None:
            self.buy_threshold = buy_threshold
        if sell_threshold is not None:
            self.sell_threshold = sell_threshold
        if high_confidence_threshold is not None:
            self.high_confidence_threshold = high_confidence_threshold
        
        logger.info(f"Thresholds updated: buy={self.buy_threshold}, "
                   f"sell={self.sell_threshold}, high_conf={self.high_confidence_threshold}")


# Factory function for easy integration
def create_fast_volume_analyzer(lookback_period: int = 20, 
                               percentile_period: int = 100) -> FastVolumeAnalyzer:
    """
    Create a fast volume analyzer.
    
    Args:
        lookback_period: Period for rolling volume statistics
        percentile_period: Period for percentile calculations
        
    Returns:
        Configured FastVolumeAnalyzer instance
    """
    analyzer = FastVolumeAnalyzer(lookback_period, percentile_period)
    logger.info(f"Created fast volume analyzer with target <25ms processing")
    return analyzer


# Performance benchmark utility
def benchmark_volume_performance(analyzer: FastVolumeAnalyzer, 
                                num_updates: int = 1000) -> Dict:
    """
    Benchmark volume analyzer performance.
    
    Args:
        analyzer: Volume analyzer instance
        num_updates: Number of volume updates to test
        
    Returns:
        Performance benchmark results
    """
    import random
    
    analyzer.reset()
    start_time = time.perf_counter()
    
    # Generate realistic volume data
    base_volume = 1000000  # 1M shares
    
    for i in range(num_updates):
        # Simulate volume spikes and normal trading
        if random.random() < 0.1:  # 10% chance of volume spike
            volume = base_volume * random.uniform(2.0, 5.0)
        else:
            volume = base_volume * random.uniform(0.5, 1.5)
        
        # Update metrics
        analyzer.update_volume_metrics(volume)
        
        # Test confirmation every 10 updates
        if i % 10 == 0:
            signal_type = random.choice(['BUY', 'SELL'])
            strength = random.uniform(0.5, 1.0)
            result = analyzer.quick_volume_confirmation(volume, signal_type, strength)
            
            if i % 100 == 0:
                logger.debug(f"Update {i}: Volume={volume:.0f}, "
                           f"Confirmed={result.confirmed}, "
                           f"RelVol={result.relative_volume:.2f}")
    
    total_time = (time.perf_counter() - start_time) * 1000  # ms
    
    stats = analyzer.get_performance_stats()
    stats.update({
        'benchmark_total_time_ms': total_time,
        'benchmark_avg_per_update_ms': total_time / num_updates,
        'target_achieved': stats.get('overall_target_met', False),
        'total_operations': num_updates + analyzer.total_confirmations
    })
    
    return stats


if __name__ == "__main__":
    # Example usage and performance test
    print("Fast Volume Analyzer Performance Test")
    print("=" * 40)
    
    # Create analyzer
    analyzer = create_fast_volume_analyzer()
    
    # Run performance benchmark
    results = benchmark_volume_performance(analyzer, 1000)
    
    print(f"Performance Results:")
    if 'update_performance' in results:
        print(f"- Update time: {results['update_performance']['avg_update_time_ms']:.2f}ms")
        print(f"- Update target (<5ms): {'✅' if results['update_performance']['target_met'] else '❌'}")
    
    if 'confirmation_performance' in results:
        print(f"- Confirmation time: {results['confirmation_performance']['avg_confirmation_time_ms']:.2f}ms")
        print(f"- Confirmation target (<25ms): {'✅' if results['confirmation_performance']['target_met'] else '❌'}")
    
    print(f"- Overall target: {'✅ ACHIEVED' if results.get('target_achieved') else '❌ MISSED'}")
    print(f"- Total confirmations: {results['total_confirmations']}")