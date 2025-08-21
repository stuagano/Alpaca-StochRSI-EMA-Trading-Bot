"""
Parallel Multi-Timeframe Consensus Engine
=========================================

Optimized consensus validation with parallel processing and intelligent caching.
Target: <150ms consensus time (vs current 200-400ms)

Performance Features:
- Parallel timeframe data fetching
- Intelligent caching with TTL
- Fast-path validation for high-confidence signals
- Adaptive timeout management
"""

import time
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import deque
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import logging
import json

logger = logging.getLogger(__name__)


@dataclass
class TimeframeData:
    """Timeframe-specific data container."""
    symbol: str
    timeframe: str
    trend_direction: str
    trend_strength: float
    confidence: float
    timestamp: float
    indicators: Dict[str, float]
    fetch_time_ms: float


@dataclass
class ConsensusResult:
    """Consensus validation result."""
    approved: bool
    consensus_achieved: bool
    agreement_ratio: float
    confidence: float
    aligned_timeframes: List[str]
    conflicting_timeframes: List[str]
    processing_time_ms: float
    cache_hits: int
    reason: str


class ParallelConsensusEngine:
    """
    High-performance consensus engine with parallel processing.
    
    Performance targets:
    - Data fetching: <80ms per timeframe (parallel)
    - Consensus calculation: <30ms
    - Total processing: <150ms
    """
    
    def __init__(self, timeframes: List[str] = None, max_workers: int = 3):
        """
        Initialize parallel consensus engine.
        
        Args:
            timeframes: List of timeframes to analyze
            max_workers: Maximum concurrent workers for parallel processing
        """
        self.timeframes = timeframes or ['15m', '1h', '1d']
        self.max_workers = min(max_workers, len(self.timeframes))
        
        # Thread pool for parallel operations
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        
        # Intelligent caching system
        self.data_cache = {}
        self.cache_timestamps = {}
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'expired': 0
        }
        
        # Cache TTL configuration (in seconds)
        self.cache_ttl = {
            '15m': 30,    # 30 seconds
            '1h': 300,    # 5 minutes
            '1d': 1800,   # 30 minutes
            'default': 60
        }
        
        # Performance tracking
        self.processing_times = deque(maxlen=100)
        self.fetch_times = deque(maxlen=300)  # Track individual fetches
        self.total_validations = 0
        
        # Consensus thresholds
        self.consensus_threshold = 0.75
        self.minimum_timeframes = 2
        self.high_confidence_threshold = 0.9
        
        # Adaptive timeout management
        self.base_timeout = 0.08  # 80ms base timeout
        self.adaptive_timeout = True
        self.timeout_buffer = 0.02  # 20ms buffer
        
        logger.info(f"ParallelConsensusEngine initialized: timeframes={self.timeframes}, "
                   f"workers={self.max_workers}")
    
    async def validate_signal_consensus(self, signal: Dict, symbol: str) -> ConsensusResult:
        """
        Validate signal consensus across multiple timeframes in parallel.
        
        Args:
            signal: Signal dictionary with type, strength, etc.
            symbol: Trading symbol
            
        Returns:
            Consensus validation result
        """
        start_time = time.perf_counter()
        self.total_validations += 1
        
        try:
            # Step 1: Fetch timeframe data in parallel
            timeframe_data = await self._fetch_parallel_timeframe_data(symbol)
            
            # Step 2: Fast consensus calculation
            consensus = self._calculate_fast_consensus(signal, timeframe_data)
            
            # Step 3: Determine final approval
            approval_result = self._determine_approval(signal, consensus, timeframe_data)
            
            # Track performance
            processing_time = (time.perf_counter() - start_time) * 1000
            self.processing_times.append(processing_time)
            
            return ConsensusResult(
                approved=approval_result['approved'],
                consensus_achieved=consensus['achieved'],
                agreement_ratio=consensus['agreement_ratio'],
                confidence=approval_result['confidence'],
                aligned_timeframes=consensus['aligned_timeframes'],
                conflicting_timeframes=consensus['conflicting_timeframes'],
                processing_time_ms=processing_time,
                cache_hits=self.cache_stats['hits'],
                reason=approval_result['reason']
            )
            
        except Exception as e:
            logger.error(f"Error in consensus validation: {e}")
            return ConsensusResult(
                approved=False,
                consensus_achieved=False,
                agreement_ratio=0.0,
                confidence=0.0,
                aligned_timeframes=[],
                conflicting_timeframes=self.timeframes,
                processing_time_ms=(time.perf_counter() - start_time) * 1000,
                cache_hits=self.cache_stats['hits'],
                reason=f"validation_error: {str(e)}"
            )
    
    async def _fetch_parallel_timeframe_data(self, symbol: str) -> Dict[str, Optional[TimeframeData]]:
        """
        Fetch timeframe data in parallel with intelligent caching.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Dictionary of timeframe data
        """
        # Create parallel tasks
        tasks = []
        loop = asyncio.get_event_loop()
        
        for timeframe in self.timeframes:
            task = loop.run_in_executor(
                self.executor, 
                self._fetch_timeframe_data_cached, 
                symbol, 
                timeframe
            )
            tasks.append((timeframe, task))
        
        # Collect results with adaptive timeout
        timeframe_data = {}
        timeout = self._get_adaptive_timeout()
        
        try:
            # Wait for all tasks to complete with timeout
            for timeframe, task in tasks:
                try:
                    data = await asyncio.wait_for(task, timeout=timeout)
                    timeframe_data[timeframe] = data
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout fetching {timeframe} data for {symbol}")
                    timeframe_data[timeframe] = None
                except Exception as e:
                    logger.warning(f"Error fetching {timeframe} data for {symbol}: {e}")
                    timeframe_data[timeframe] = None
        
        except Exception as e:
            logger.error(f"Error in parallel data fetch: {e}")
        
        return timeframe_data
    
    def _fetch_timeframe_data_cached(self, symbol: str, timeframe: str) -> Optional[TimeframeData]:
        """
        Fetch timeframe data with intelligent caching.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe to fetch
            
        Returns:
            TimeframeData or None if fetch fails
        """
        fetch_start = time.perf_counter()
        
        try:
            cache_key = f"{symbol}_{timeframe}"
            current_time = time.time()
            
            # Check cache validity
            if self._is_cache_valid(cache_key, timeframe, current_time):
                self.cache_stats['hits'] += 1
                cached_data = self.data_cache[cache_key]
                # Update fetch time for performance tracking
                self.fetch_times.append(1.0)  # Cache hit is ~1ms
                return cached_data
            
            # Cache miss - fetch fresh data
            self.cache_stats['misses'] += 1
            data = self._simulate_timeframe_fetch(symbol, timeframe)
            
            # Update cache
            if data:
                self.data_cache[cache_key] = data
                self.cache_timestamps[cache_key] = current_time
            
            # Track fetch performance
            fetch_time = (time.perf_counter() - fetch_start) * 1000
            self.fetch_times.append(fetch_time)
            
            return data
            
        except Exception as e:
            logger.error(f"Error fetching {timeframe} data for {symbol}: {e}")
            return None
    
    def _is_cache_valid(self, cache_key: str, timeframe: str, current_time: float) -> bool:
        """Check if cached data is still valid."""
        if cache_key not in self.cache_timestamps:
            return False
        
        cache_time = self.cache_timestamps[cache_key]
        ttl = self.cache_ttl.get(timeframe, self.cache_ttl['default'])
        
        if current_time - cache_time > ttl:
            self.cache_stats['expired'] += 1
            return False
        
        return cache_key in self.data_cache
    
    def _simulate_timeframe_fetch(self, symbol: str, timeframe: str) -> Optional[TimeframeData]:
        """
        Simulate timeframe data fetch (replace with actual API calls).
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe to fetch
            
        Returns:
            Simulated TimeframeData
        """
        import random
        
        # Simulate network delay
        time.sleep(random.uniform(0.02, 0.06))  # 20-60ms delay
        
        # Simulate trend analysis
        directions = ['bullish', 'bearish', 'neutral']
        trend_direction = random.choice(directions)
        
        return TimeframeData(
            symbol=symbol,
            timeframe=timeframe,
            trend_direction=trend_direction,
            trend_strength=random.uniform(0.4, 0.9),
            confidence=random.uniform(0.6, 0.95),
            timestamp=time.time(),
            indicators={
                'ema': random.uniform(-1, 1),
                'rsi': random.uniform(30, 70),
                'macd': random.uniform(-0.5, 0.5)
            },
            fetch_time_ms=random.uniform(20, 60)
        )
    
    def _calculate_fast_consensus(self, signal: Dict, 
                                timeframe_data: Dict[str, Optional[TimeframeData]]) -> Dict:
        """
        Fast consensus calculation using optimized algorithms.
        
        Args:
            signal: Signal to validate
            timeframe_data: Fetched timeframe data
            
        Returns:
            Consensus analysis result
        """
        # Filter valid timeframe data
        valid_data = {tf: data for tf, data in timeframe_data.items() if data is not None}
        
        if len(valid_data) < self.minimum_timeframes:
            return {
                'achieved': False,
                'agreement_ratio': 0.0,
                'aligned_timeframes': [],
                'conflicting_timeframes': list(timeframe_data.keys()),
                'reason': 'insufficient_timeframe_data'
            }
        
        # Determine target direction from signal
        signal_type = signal.get('type', 'BUY')
        target_direction = 'bullish' if signal_type in ['BUY', 'OVERSOLD'] else 'bearish'
        
        # Calculate alignment with weighted scoring
        aligned_timeframes = []
        conflicting_timeframes = []
        total_weight = 0.0
        aligned_weight = 0.0
        
        # Timeframe weights (higher timeframes get more weight)
        weights = {'15m': 1.0, '1h': 1.5, '1d': 2.0}
        
        for timeframe, data in valid_data.items():
            weight = weights.get(timeframe, 1.0)
            total_weight += weight
            
            # Check alignment
            if data.trend_direction == target_direction:
                aligned_timeframes.append(timeframe)
                # Weight by confidence
                aligned_weight += weight * data.confidence
            elif data.trend_direction != 'neutral':
                conflicting_timeframes.append(timeframe)
        
        # Calculate agreement ratio
        agreement_ratio = aligned_weight / total_weight if total_weight > 0 else 0.0
        
        # Determine if consensus is achieved
        consensus_achieved = (
            agreement_ratio >= self.consensus_threshold and
            len(aligned_timeframes) >= self.minimum_timeframes
        )
        
        return {
            'achieved': consensus_achieved,
            'agreement_ratio': agreement_ratio,
            'aligned_timeframes': aligned_timeframes,
            'conflicting_timeframes': conflicting_timeframes,
            'target_direction': target_direction,
            'total_weight': total_weight,
            'aligned_weight': aligned_weight
        }
    
    def _determine_approval(self, signal: Dict, consensus: Dict, 
                          timeframe_data: Dict) -> Dict:
        """
        Determine final signal approval based on consensus and signal strength.
        
        Args:
            signal: Original signal
            consensus: Consensus analysis
            timeframe_data: Timeframe data
            
        Returns:
            Approval decision with confidence and reason
        """
        signal_strength = signal.get('strength', 0.5)
        
        # Base approval on consensus achievement
        if consensus['achieved']:
            # Calculate confidence score
            confidence = min(
                consensus['agreement_ratio'] * signal_strength * 1.2,
                1.0
            )
            
            # High confidence boost
            if consensus['agreement_ratio'] >= self.high_confidence_threshold:
                confidence *= 1.1
                reason = "high_confidence_consensus"
            else:
                reason = "consensus_achieved"
            
            return {
                'approved': True,
                'confidence': confidence,
                'reason': reason
            }
        else:
            # Check for partial consensus or high signal strength
            if (consensus['agreement_ratio'] >= 0.6 and 
                signal_strength >= 0.8):
                return {
                    'approved': True,
                    'confidence': consensus['agreement_ratio'] * signal_strength,
                    'reason': "partial_consensus_high_strength"
                }
            else:
                return {
                    'approved': False,
                    'confidence': 0.0,
                    'reason': f"consensus_failed_ratio_{consensus['agreement_ratio']:.2f}"
                }
    
    def _get_adaptive_timeout(self) -> float:
        """Get adaptive timeout based on recent performance."""
        if not self.adaptive_timeout or not self.fetch_times:
            return self.base_timeout
        
        # Use 95th percentile of recent fetch times + buffer
        recent_times = list(self.fetch_times)[-50:]  # Last 50 fetches
        if recent_times:
            p95_time = sorted(recent_times)[int(len(recent_times) * 0.95)]
            # Convert to seconds and add buffer
            adaptive_timeout = (p95_time / 1000.0) + self.timeout_buffer
            return min(adaptive_timeout, self.base_timeout * 2)  # Cap at 2x base
        
        return self.base_timeout
    
    def get_performance_stats(self) -> Dict:
        """Get comprehensive performance statistics."""
        if not self.processing_times:
            return {'status': 'no_data'}
        
        processing_times = list(self.processing_times)
        fetch_times = list(self.fetch_times)
        
        # Cache performance
        total_cache_ops = sum(self.cache_stats.values())
        cache_hit_rate = (self.cache_stats['hits'] / total_cache_ops * 100) if total_cache_ops > 0 else 0
        
        stats = {
            'total_validations': self.total_validations,
            'performance': {
                'avg_processing_time_ms': sum(processing_times) / len(processing_times),
                'p95_processing_time_ms': sorted(processing_times)[int(len(processing_times) * 0.95)],
                'max_processing_time_ms': max(processing_times),
                'target_met': sum(processing_times) / len(processing_times) < 150.0
            },
            'cache_performance': {
                'hit_rate_percent': cache_hit_rate,
                'hits': self.cache_stats['hits'],
                'misses': self.cache_stats['misses'],
                'expired': self.cache_stats['expired']
            },
            'fetch_performance': {
                'avg_fetch_time_ms': sum(fetch_times) / len(fetch_times) if fetch_times else 0,
                'cache_fetch_ratio': self.cache_stats['hits'] / len(fetch_times) if fetch_times else 0
            },
            'configuration': {
                'timeframes': self.timeframes,
                'max_workers': self.max_workers,
                'consensus_threshold': self.consensus_threshold,
                'adaptive_timeout': self._get_adaptive_timeout()
            }
        }
        
        return stats
    
    def clear_cache(self):
        """Clear all cached data."""
        self.data_cache.clear()
        self.cache_timestamps.clear()
        self.cache_stats = {'hits': 0, 'misses': 0, 'expired': 0}
        logger.info("Cache cleared")
    
    def shutdown(self):
        """Shutdown the consensus engine."""
        self.executor.shutdown(wait=True)
        self.clear_cache()
        logger.info("ParallelConsensusEngine shutdown")


# Factory function
def create_parallel_consensus_engine(timeframes: List[str] = None, 
                                   max_workers: int = 3) -> ParallelConsensusEngine:
    """
    Create a parallel consensus engine.
    
    Args:
        timeframes: List of timeframes to analyze
        max_workers: Maximum concurrent workers
        
    Returns:
        Configured ParallelConsensusEngine instance
    """
    engine = ParallelConsensusEngine(timeframes, max_workers)
    logger.info(f"Created parallel consensus engine with target <150ms processing")
    return engine


# Performance benchmark
async def benchmark_consensus_performance(engine: ParallelConsensusEngine, 
                                        num_validations: int = 100) -> Dict:
    """
    Benchmark consensus engine performance.
    
    Args:
        engine: Consensus engine instance
        num_validations: Number of validations to test
        
    Returns:
        Performance benchmark results
    """
    import random
    
    symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN']
    signal_types = ['BUY', 'SELL', 'OVERSOLD', 'OVERBOUGHT']
    
    start_time = time.perf_counter()
    results = []
    
    for i in range(num_validations):
        # Generate random signal
        signal = {
            'type': random.choice(signal_types),
            'strength': random.uniform(0.4, 1.0),
            'timestamp': time.time()
        }
        
        symbol = random.choice(symbols)
        
        # Validate consensus
        result = await engine.validate_signal_consensus(signal, symbol)
        results.append(result)
        
        if i % 25 == 0:
            logger.debug(f"Validation {i}: {symbol} {signal['type']} - "
                        f"Approved={result.approved}, Time={result.processing_time_ms:.1f}ms")
    
    total_time = (time.perf_counter() - start_time) * 1000
    
    # Calculate benchmark stats
    processing_times = [r.processing_time_ms for r in results]
    approvals = [r.approved for r in results]
    
    stats = engine.get_performance_stats()
    stats.update({
        'benchmark_total_time_ms': total_time,
        'benchmark_avg_per_validation_ms': total_time / num_validations,
        'approval_rate_percent': sum(approvals) / len(approvals) * 100,
        'target_achieved': sum(processing_times) / len(processing_times) < 150.0,
        'speedup_vs_target': 150.0 / (sum(processing_times) / len(processing_times))
    })
    
    return stats


if __name__ == "__main__":
    # Example usage and performance test
    async def main():
        print("Parallel Consensus Engine Performance Test")
        print("=" * 45)
        
        # Create engine
        engine = create_parallel_consensus_engine()
        
        try:
            # Run performance benchmark
            results = await benchmark_consensus_performance(engine, 100)
            
            print(f"Performance Results:")
            if 'performance' in results:
                perf = results['performance']
                print(f"- Avg processing time: {perf['avg_processing_time_ms']:.1f}ms")
                print(f"- P95 processing time: {perf['p95_processing_time_ms']:.1f}ms")
                print(f"- Target (<150ms): {'✅' if perf['target_met'] else '❌'}")
            
            if 'cache_performance' in results:
                cache = results['cache_performance']
                print(f"- Cache hit rate: {cache['hit_rate_percent']:.1f}%")
            
            print(f"- Approval rate: {results.get('approval_rate_percent', 0):.1f}%")
            print(f"- Speedup vs target: {results.get('speedup_vs_target', 0):.1f}x")
            
        finally:
            engine.shutdown()
    
    # Run the async main function
    asyncio.run(main())