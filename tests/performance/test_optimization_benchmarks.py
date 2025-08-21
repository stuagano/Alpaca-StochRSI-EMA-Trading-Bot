"""
Performance Optimization Benchmarks
===================================

Comprehensive performance tests for Epic 1 Signal Quality Enhancement optimizations.
Tests all optimization targets to ensure performance goals are met.
"""

import time
import pytest
import asyncio
import numpy as np
import pandas as pd
from unittest.mock import MagicMock
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.optimizations.incremental_stochrsi import IncrementalStochRSI, create_optimized_stochrsi
from src.optimizations.fast_volume_analyzer import FastVolumeAnalyzer, create_fast_volume_analyzer
from src.optimizations.parallel_consensus_engine import ParallelConsensusEngine, create_parallel_consensus_engine


class TestIncrementalStochRSIPerformance:
    """Test suite for incremental StochRSI performance optimizations."""
    
    def setup_method(self):
        """Set up test environment."""
        self.calculator = create_optimized_stochrsi()
        self.target_update_time = 50.0  # ms
        self.test_data_size = 1000
    
    def test_incremental_update_performance(self):
        """Test that incremental updates meet the <50ms target."""
        # Generate test price data
        base_price = 100.0
        prices = []
        update_times = []
        
        for i in range(self.test_data_size):
            # Simulate realistic price movement
            change = np.random.normal(0, 0.02)  # 2% volatility
            base_price *= (1 + change)
            prices.append(base_price)
            
            # Measure update time
            start_time = time.perf_counter()
            result = self.calculator.update(base_price)
            update_time = (time.perf_counter() - start_time) * 1000  # ms
            
            update_times.append(update_time)
            
            # After initial period, verify results are returned
            if i > 50 and result:
                assert 'rsi' in result
                assert 'stoch_k' in result
                assert 'stoch_d' in result
                assert 0 <= result['rsi'] <= 100
                assert 0 <= result['stoch_k'] <= 100
                assert 0 <= result['stoch_d'] <= 100
        
        # Performance validation
        avg_update_time = np.mean(update_times[50:])  # Exclude initialization period
        p95_update_time = np.percentile(update_times[50:], 95)
        max_update_time = np.max(update_times[50:])
        
        print(f"\nStochRSI Performance Results:")
        print(f"Average update time: {avg_update_time:.2f}ms")
        print(f"P95 update time: {p95_update_time:.2f}ms")
        print(f"Max update time: {max_update_time:.2f}ms")
        print(f"Target: <{self.target_update_time}ms")
        
        # Assertions
        assert avg_update_time < self.target_update_time, f"Average update time {avg_update_time:.2f}ms exceeds target {self.target_update_time}ms"
        assert p95_update_time < self.target_update_time * 1.5, f"P95 update time {p95_update_time:.2f}ms too slow"
        
        # Get performance stats
        stats = self.calculator.get_performance_stats()
        assert stats['target_met'], "Performance target not met according to calculator stats"
    
    def test_memory_efficiency(self):
        """Test memory efficiency of sliding window approach."""
        initial_buffer_sizes = self.calculator.get_performance_stats()['buffer_sizes']
        
        # Add many data points
        for i in range(5000):
            price = 100 + np.sin(i / 100) * 10  # Sine wave pattern
            self.calculator.update(price)
        
        final_buffer_sizes = self.calculator.get_performance_stats()['buffer_sizes']
        
        print(f"\nMemory Efficiency Results:")
        print(f"Initial buffer sizes: {initial_buffer_sizes}")
        print(f"Final buffer sizes: {final_buffer_sizes}")
        
        # Buffers should not grow beyond their maxlen
        for buffer_name, size in final_buffer_sizes.items():
            assert size <= 50, f"Buffer {buffer_name} size {size} exceeds expected maximum"
    
    def test_accuracy_validation(self):
        """Test that incremental calculation maintains accuracy."""
        self.calculator.enable_validation_mode(True)
        
        # Generate test data
        np.random.seed(42)  # For reproducible results
        prices = 100 + np.cumsum(np.random.normal(0, 1, 200))
        
        # Process data
        results = []
        for price in prices:
            result = self.calculator.update(price)
            if result:
                results.append(result)
        
        # Should have results without validation errors
        assert len(results) > 100, "Insufficient results generated"
        
        # All results should be valid
        for result in results[-50:]:  # Check last 50 results
            assert 0 <= result['rsi'] <= 100
            assert 0 <= result['stoch_k'] <= 100
            assert 0 <= result['stoch_d'] <= 100


class TestFastVolumeAnalyzerPerformance:
    """Test suite for fast volume analyzer performance."""
    
    def setup_method(self):
        """Set up test environment."""
        self.analyzer = create_fast_volume_analyzer()
        self.target_confirmation_time = 25.0  # ms
        self.target_update_time = 5.0  # ms
    
    def test_volume_update_performance(self):
        """Test volume metric updates meet <5ms target."""
        update_times = []
        
        # Test volume updates
        for i in range(1000):
            volume = np.random.uniform(500000, 2000000)  # Random volume
            
            start_time = time.perf_counter()
            metrics = self.analyzer.update_volume_metrics(volume)
            update_time = (time.perf_counter() - start_time) * 1000  # ms
            
            update_times.append(update_time)
            
            # Verify metrics are updated
            if i > 20:  # After initial period
                assert metrics.avg_volume > 0
                assert metrics.last_update > 0
        
        avg_update_time = np.mean(update_times[20:])  # Exclude initialization
        p95_update_time = np.percentile(update_times[20:], 95)
        
        print(f"\nVolume Update Performance Results:")
        print(f"Average update time: {avg_update_time:.2f}ms")
        print(f"P95 update time: {p95_update_time:.2f}ms")
        print(f"Target: <{self.target_update_time}ms")
        
        assert avg_update_time < self.target_update_time, f"Update time {avg_update_time:.2f}ms exceeds target"
    
    def test_volume_confirmation_performance(self):
        """Test volume confirmation meets <25ms target."""
        # Initialize with some volume data
        for i in range(50):
            volume = np.random.uniform(800000, 1200000)
            self.analyzer.update_volume_metrics(volume)
        
        confirmation_times = []
        signal_types = ['BUY', 'SELL', 'OVERSOLD', 'OVERBOUGHT']
        
        # Test confirmations
        for i in range(500):
            volume = np.random.uniform(500000, 3000000)
            signal_type = np.random.choice(signal_types)
            strength = np.random.uniform(0.5, 1.0)
            
            start_time = time.perf_counter()
            result = self.analyzer.quick_volume_confirmation(volume, signal_type, strength)
            confirmation_time = (time.perf_counter() - start_time) * 1000  # ms
            
            confirmation_times.append(confirmation_time)
            
            # Verify result structure
            assert isinstance(result.confirmed, bool)
            assert result.relative_volume >= 0
            assert 0 <= result.confidence <= 2.0
            assert result.processing_time_ms >= 0
        
        avg_confirmation_time = np.mean(confirmation_times)
        p95_confirmation_time = np.percentile(confirmation_times, 95)
        max_confirmation_time = np.max(confirmation_times)
        
        print(f"\nVolume Confirmation Performance Results:")
        print(f"Average confirmation time: {avg_confirmation_time:.2f}ms")
        print(f"P95 confirmation time: {p95_confirmation_time:.2f}ms")
        print(f"Max confirmation time: {max_confirmation_time:.2f}ms")
        print(f"Target: <{self.target_confirmation_time}ms")
        
        assert avg_confirmation_time < self.target_confirmation_time, f"Confirmation time {avg_confirmation_time:.2f}ms exceeds target"
        
        # Get analyzer performance stats
        stats = self.analyzer.get_performance_stats()
        if 'confirmation_performance' in stats:
            assert stats['confirmation_performance']['target_met'], "Analyzer reports target not met"
    
    def test_batch_processing_efficiency(self):
        """Test batch processing performance."""
        # Prepare batch of signals
        signals = []
        for _ in range(100):
            signals.append({
                'volume': np.random.uniform(500000, 2000000),
                'type': np.random.choice(['BUY', 'SELL']),
                'strength': np.random.uniform(0.5, 1.0)
            })
        
        # Initialize analyzer
        for i in range(50):
            self.analyzer.update_volume_metrics(np.random.uniform(800000, 1200000))
        
        # Test batch processing
        start_time = time.perf_counter()
        results = self.analyzer.batch_confirm_signals(signals)
        batch_time = (time.perf_counter() - start_time) * 1000  # ms
        
        avg_time_per_signal = batch_time / len(signals)
        
        print(f"\nBatch Processing Results:")
        print(f"Total batch time: {batch_time:.2f}ms")
        print(f"Average per signal: {avg_time_per_signal:.2f}ms")
        print(f"Signals processed: {len(results)}")
        
        assert len(results) == len(signals), "Not all signals were processed"
        assert avg_time_per_signal < self.target_confirmation_time, "Batch processing too slow"


class TestParallelConsensusEnginePerformance:
    """Test suite for parallel consensus engine performance."""
    
    def setup_method(self):
        """Set up test environment."""
        self.engine = create_parallel_consensus_engine()
        self.target_processing_time = 150.0  # ms
    
    @pytest.mark.asyncio
    async def test_consensus_validation_performance(self):
        """Test consensus validation meets <150ms target."""
        processing_times = []
        symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA']
        signal_types = ['BUY', 'SELL', 'OVERSOLD', 'OVERBOUGHT']
        
        # Test multiple validations
        for i in range(50):
            signal = {
                'type': np.random.choice(signal_types),
                'strength': np.random.uniform(0.4, 1.0),
                'timestamp': time.time()
            }
            symbol = np.random.choice(symbols)
            
            start_time = time.perf_counter()
            result = await self.engine.validate_signal_consensus(signal, symbol)
            processing_time = (time.perf_counter() - start_time) * 1000  # ms
            
            processing_times.append(processing_time)
            
            # Verify result structure
            assert isinstance(result.approved, bool)
            assert isinstance(result.consensus_achieved, bool)
            assert 0 <= result.agreement_ratio <= 1.0
            assert 0 <= result.confidence <= 1.0
            assert result.processing_time_ms > 0
        
        avg_processing_time = np.mean(processing_times)
        p95_processing_time = np.percentile(processing_times, 95)
        max_processing_time = np.max(processing_times)
        
        print(f"\nConsensus Engine Performance Results:")
        print(f"Average processing time: {avg_processing_time:.1f}ms")
        print(f"P95 processing time: {p95_processing_time:.1f}ms")
        print(f"Max processing time: {max_processing_time:.1f}ms")
        print(f"Target: <{self.target_processing_time}ms")
        
        assert avg_processing_time < self.target_processing_time, f"Processing time {avg_processing_time:.1f}ms exceeds target"
        
        # Check engine performance stats
        stats = self.engine.get_performance_stats()
        if 'performance' in stats:
            assert stats['performance']['target_met'], "Engine reports target not met"
    
    @pytest.mark.asyncio
    async def test_caching_effectiveness(self):
        """Test that caching improves performance."""
        symbol = 'AAPL'
        signal = {'type': 'BUY', 'strength': 0.8}
        
        # First validation (cache miss)
        start_time = time.perf_counter()
        result1 = await self.engine.validate_signal_consensus(signal, symbol)
        first_time = (time.perf_counter() - start_time) * 1000
        
        # Second validation immediately (should hit cache)
        start_time = time.perf_counter()
        result2 = await self.engine.validate_signal_consensus(signal, symbol)
        second_time = (time.perf_counter() - start_time) * 1000
        
        print(f"\nCaching Performance:")
        print(f"First validation (cache miss): {first_time:.1f}ms")
        print(f"Second validation (cache hit): {second_time:.1f}ms")
        print(f"Speedup: {first_time / second_time:.1f}x")
        
        # Cache hit should be faster
        assert second_time < first_time, "Cache hit not faster than cache miss"
        
        # Check cache stats
        stats = self.engine.get_performance_stats()
        if 'cache_performance' in stats:
            assert stats['cache_performance']['hits'] > 0, "No cache hits recorded"
    
    def teardown_method(self):
        """Clean up after tests."""
        self.engine.shutdown()


class TestIntegratedPerformance:
    """Test integrated performance of all optimizations together."""
    
    def setup_method(self):
        """Set up integrated test environment."""
        self.stochrsi = create_optimized_stochrsi()
        self.volume_analyzer = create_fast_volume_analyzer()
        self.consensus_engine = create_parallel_consensus_engine()
        
        # Overall performance targets
        self.target_total_latency = 100.0  # ms total signal processing
    
    @pytest.mark.asyncio
    async def test_end_to_end_signal_processing_performance(self):
        """Test complete signal processing pipeline performance."""
        total_times = []
        
        # Test multiple complete signal processing cycles
        for i in range(20):
            start_time = time.perf_counter()
            
            # Step 1: Generate signal with StochRSI (target: <50ms)
            price = 100 + np.sin(i / 10) * 5
            volume = np.random.uniform(1000000, 2000000)
            
            stochrsi_result = self.stochrsi.update(price)
            if not stochrsi_result:
                continue
                
            # Step 2: Update volume metrics and confirm (target: <25ms)
            self.volume_analyzer.update_volume_metrics(volume)
            volume_result = self.volume_analyzer.quick_volume_confirmation(
                volume, 'BUY', 0.8
            )
            
            # Step 3: Validate consensus (target: <150ms, but we want <25ms for remaining budget)
            if stochrsi_result['stoch_k'] < 30:  # Oversold condition
                signal = {
                    'type': 'OVERSOLD',
                    'strength': 0.8,
                    'indicators': stochrsi_result,
                    'volume_confirmed': volume_result.confirmed
                }
                
                consensus_result = await self.consensus_engine.validate_signal_consensus(
                    signal, 'AAPL'
                )
            else:
                consensus_result = None
            
            total_time = (time.perf_counter() - start_time) * 1000  # ms
            total_times.append(total_time)
            
            if i % 5 == 0:
                print(f"Cycle {i}: {total_time:.1f}ms")
        
        if total_times:
            avg_total_time = np.mean(total_times)
            p95_total_time = np.percentile(total_times, 95)
            max_total_time = np.max(total_times)
            
            print(f"\nIntegrated Performance Results:")
            print(f"Average total processing time: {avg_total_time:.1f}ms")
            print(f"P95 total processing time: {p95_total_time:.1f}ms")
            print(f"Max total processing time: {max_total_time:.1f}ms")
            print(f"Target: <{self.target_total_latency}ms")
            
            # This is the key performance test
            assert avg_total_time < self.target_total_latency, f"Total processing time {avg_total_time:.1f}ms exceeds target {self.target_total_latency}ms"
    
    def test_memory_usage_under_load(self):
        """Test memory usage remains controlled under sustained load."""
        import psutil
        import gc
        
        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Run sustained load
        for i in range(2000):
            price = 100 + np.random.normal(0, 5)
            volume = np.random.uniform(500000, 2000000)
            
            # Update all components
            self.stochrsi.update(price)
            self.volume_analyzer.update_volume_metrics(volume)
            
            if i % 100 == 0:
                gc.collect()  # Force garbage collection
        
        # Get final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        memory_increase_percent = (memory_increase / initial_memory) * 100
        
        print(f"\nMemory Usage Results:")
        print(f"Initial memory: {initial_memory:.1f}MB")
        print(f"Final memory: {final_memory:.1f}MB")
        print(f"Memory increase: {memory_increase:.1f}MB ({memory_increase_percent:.1f}%)")
        print(f"Target: <20% increase")
        
        # Memory increase should be less than 20%
        assert memory_increase_percent < 20.0, f"Memory increase {memory_increase_percent:.1f}% exceeds 20% target"
    
    def teardown_method(self):
        """Clean up after integrated tests."""
        self.consensus_engine.shutdown()


if __name__ == "__main__":
    # Run performance benchmarks
    pytest.main([__file__, "-v", "-s"])