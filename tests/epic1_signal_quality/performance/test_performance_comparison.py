"""
Performance Comparison Tests for Epic 1 Signal Quality Enhancements

Compares performance metrics between legacy and enhanced signal processing:
- Processing speed benchmarks
- Memory usage analysis
- Signal accuracy improvements
- Latency measurements
- Throughput comparisons
"""

import pytest
import pandas as pd
import numpy as np
import time
import psutil
import gc
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
import sys
import os
from typing import Dict, List, Tuple
import threading
import queue

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from indicators.stoch_rsi_enhanced import StochRSIIndicator
from tests.epic1_signal_quality.fixtures.epic1_test_fixtures import (
    epic1_config, performance_baseline_metrics, volatile_market_data
)


class LegacyStochRSIIndicator:
    """Legacy StochRSI implementation for performance comparison."""
    
    def __init__(self, rsi_length: int = 14, stoch_length: int = 14):
        self.rsi_length = rsi_length
        self.stoch_length = stoch_length
        self.oversold_threshold = 20
        self.overbought_threshold = 80
    
    def calculate_rsi(self, prices: pd.Series) -> pd.Series:
        """Simple RSI calculation without optimizations."""
        delta = prices.diff()
        gains = delta.where(delta > 0, 0)
        losses = -delta.where(delta < 0, 0)
        
        # Simple moving average (less efficient than EWM)
        avg_gains = gains.rolling(window=self.rsi_length).mean()
        avg_losses = losses.rolling(window=self.rsi_length).mean()
        
        rs = avg_gains / avg_losses
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_stochastic(self, rsi: pd.Series) -> Tuple[pd.Series, pd.Series]:
        """Basic stochastic calculation."""
        rsi_low = rsi.rolling(window=self.stoch_length).min()
        rsi_high = rsi.rolling(window=self.stoch_length).max()
        
        stoch_k = ((rsi - rsi_low) / (rsi_high - rsi_low)) * 100
        stoch_d = stoch_k.rolling(window=3).mean()  # Simple smoothing
        
        return stoch_k, stoch_d
    
    def generate_signals(self, prices: pd.Series) -> Dict:
        """Generate basic signals without enhancements."""
        rsi = self.calculate_rsi(prices)
        stoch_k, stoch_d = self.calculate_stochastic(rsi)
        
        signals = pd.Series(0, index=prices.index)
        
        for i in range(1, len(stoch_k)):
            if (stoch_k.iloc[i-1] <= stoch_d.iloc[i-1] and 
                stoch_k.iloc[i] > stoch_d.iloc[i] and 
                stoch_k.iloc[i] < self.oversold_threshold):
                signals.iloc[i] = 1
            elif (stoch_k.iloc[i-1] >= stoch_d.iloc[i-1] and 
                  stoch_k.iloc[i] < stoch_d.iloc[i] and 
                  stoch_k.iloc[i] > self.overbought_threshold):
                signals.iloc[i] = -1
        
        return {
            'signals': signals,
            'stoch_k': stoch_k,
            'stoch_d': stoch_d,
            'rsi': rsi
        }


class EnhancedStochRSIIndicator(StochRSIIndicator):
    """Enhanced StochRSI with Epic 1 improvements."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dynamic_bands_enabled = True
        self.volume_confirmation_enabled = True
        self.multi_timeframe_enabled = True
    
    def calculate_enhanced_signals(self, data: pd.DataFrame) -> Dict:
        """Calculate signals with all Epic 1 enhancements."""
        # Basic StochRSI calculation
        basic_indicators = self.calculate_full_stoch_rsi(data['close'])
        
        # Dynamic band adjustment
        if self.dynamic_bands_enabled:
            oversold, overbought = self._calculate_dynamic_bands(data)
        else:
            oversold, overbought = self.oversold_threshold, self.overbought_threshold
        
        # Generate enhanced signals
        enhanced_signals = self._generate_enhanced_signals(
            basic_indicators['StochRSI_K'],
            basic_indicators['StochRSI_D'],
            data,
            oversold,
            overbought
        )
        
        return {
            **basic_indicators,
            'enhanced_signals': enhanced_signals,
            'dynamic_oversold': oversold,
            'dynamic_overbought': overbought
        }
    
    def _calculate_dynamic_bands(self, data: pd.DataFrame) -> Tuple[float, float]:
        """Calculate dynamic bands based on volatility and volume."""
        # Volatility adjustment
        returns = data['close'].pct_change()
        volatility = returns.rolling(window=20).std().iloc[-1]
        vol_adjustment = min(10, max(-10, (volatility - 0.02) * 500))
        
        # Volume adjustment
        avg_volume = data['volume'].rolling(window=20).mean().iloc[-1]
        current_volume = data['volume'].iloc[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
        vol_ratio_adjustment = min(5, max(-5, (volume_ratio - 1.5) * 3))
        
        # Apply adjustments
        oversold = max(5, self.oversold_threshold - vol_adjustment - vol_ratio_adjustment)
        overbought = min(95, self.overbought_threshold + vol_adjustment + vol_ratio_adjustment)
        
        return oversold, overbought
    
    def _generate_enhanced_signals(self, stoch_k: pd.Series, stoch_d: pd.Series, 
                                 data: pd.DataFrame, oversold: float, 
                                 overbought: float) -> Dict:
        """Generate enhanced signals with volume confirmation."""
        signals = pd.Series(0, index=stoch_k.index)
        signal_strength = pd.Series(0.0, index=stoch_k.index)
        volume_confirmed = pd.Series(False, index=stoch_k.index)
        
        # Calculate volume metrics for confirmation
        avg_volume = data['volume'].rolling(window=20).mean()
        volume_threshold = avg_volume * 1.5
        
        for i in range(1, len(stoch_k)):
            if pd.isna(stoch_k.iloc[i]) or pd.isna(stoch_d.iloc[i]):
                continue
            
            current_k = stoch_k.iloc[i]
            current_d = stoch_d.iloc[i]
            prev_k = stoch_k.iloc[i-1]
            prev_d = stoch_d.iloc[i-1]
            current_volume = data['volume'].iloc[i]
            
            # Volume confirmation
            vol_confirmed = current_volume >= volume_threshold.iloc[i] if not pd.isna(volume_threshold.iloc[i]) else False
            volume_confirmed.iloc[i] = vol_confirmed
            
            # Enhanced signal generation
            if (prev_k <= prev_d and current_k > current_d and current_k < oversold):
                signal_strength_val = (oversold - current_k) / oversold
                if self.volume_confirmation_enabled and vol_confirmed:
                    signals.iloc[i] = 1
                    signal_strength.iloc[i] = signal_strength_val * 1.2  # Volume boost
                elif not self.volume_confirmation_enabled:
                    signals.iloc[i] = 1
                    signal_strength.iloc[i] = signal_strength_val
                    
            elif (prev_k >= prev_d and current_k < current_d and current_k > overbought):
                signal_strength_val = (current_k - overbought) / (100 - overbought)
                if self.volume_confirmation_enabled and vol_confirmed:
                    signals.iloc[i] = -1
                    signal_strength.iloc[i] = signal_strength_val * 1.2  # Volume boost
                elif not self.volume_confirmation_enabled:
                    signals.iloc[i] = -1
                    signal_strength.iloc[i] = signal_strength_val
        
        return {
            'signals': signals,
            'signal_strength': signal_strength,
            'volume_confirmed': volume_confirmed
        }


class PerformanceProfiler:
    """Performance profiling utility for signal processing."""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset profiler state."""
        self.start_time = None
        self.end_time = None
        self.memory_start = None
        self.memory_end = None
        self.cpu_start = None
        self.cpu_end = None
    
    def start_profiling(self):
        """Start performance profiling."""
        gc.collect()  # Force garbage collection
        self.start_time = time.perf_counter()
        self.memory_start = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        self.cpu_start = psutil.cpu_percent()
    
    def stop_profiling(self):
        """Stop performance profiling."""
        self.end_time = time.perf_counter()
        self.memory_end = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        self.cpu_end = psutil.cpu_percent()
    
    def get_metrics(self) -> Dict:
        """Get performance metrics."""
        if self.start_time is None or self.end_time is None:
            return {}
        
        return {
            'execution_time': self.end_time - self.start_time,
            'memory_usage': self.memory_end - self.memory_start,
            'peak_memory': self.memory_end,
            'cpu_usage': self.cpu_end
        }


class TestPerformanceComparison:
    """Performance comparison test suite."""
    
    def test_basic_calculation_speed_comparison(self, performance_baseline_metrics):
        """Compare basic calculation speed between legacy and enhanced versions."""
        # Generate test data
        np.random.seed(42)
        periods = 1000
        test_data = pd.DataFrame({
            'close': [150 + np.random.normal(0, 5) for _ in range(periods)],
            'volume': [20000 + np.random.randint(-5000, 5000) for _ in range(periods)]
        })
        
        # Test legacy implementation
        legacy_indicator = LegacyStochRSIIndicator()
        profiler = PerformanceProfiler()
        
        profiler.start_profiling()
        iterations = 100
        for _ in range(iterations):
            legacy_result = legacy_indicator.generate_signals(test_data['close'])
        profiler.stop_profiling()
        
        legacy_metrics = profiler.get_metrics()
        legacy_avg_time = legacy_metrics['execution_time'] / iterations
        
        # Test enhanced implementation
        enhanced_indicator = EnhancedStochRSIIndicator()
        enhanced_indicator.dynamic_bands_enabled = False  # Fair comparison
        enhanced_indicator.volume_confirmation_enabled = False
        
        profiler.reset()
        profiler.start_profiling()
        for _ in range(iterations):
            enhanced_result = enhanced_indicator.calculate_full_stoch_rsi(test_data['close'])
        profiler.stop_profiling()
        
        enhanced_metrics = profiler.get_metrics()
        enhanced_avg_time = enhanced_metrics['execution_time'] / iterations
        
        # Performance should be comparable (within 20% difference)
        performance_ratio = enhanced_avg_time / legacy_avg_time
        assert performance_ratio < 1.2, f"Enhanced version too slow: {performance_ratio:.2f}x slower"
        
        # Verify results are valid
        assert len(legacy_result['signals']) == periods
        assert len(enhanced_result['StochRSI_K']) == periods
    
    def test_enhanced_features_performance_impact(self, volatile_market_data):
        """Test performance impact of Epic 1 enhanced features."""
        enhanced_indicator = EnhancedStochRSIIndicator()
        profiler = PerformanceProfiler()
        
        # Test without enhancements
        enhanced_indicator.dynamic_bands_enabled = False
        enhanced_indicator.volume_confirmation_enabled = False
        
        profiler.start_profiling()
        iterations = 50
        for _ in range(iterations):
            basic_result = enhanced_indicator.calculate_full_stoch_rsi(volatile_market_data['close'])
        profiler.stop_profiling()
        
        basic_metrics = profiler.get_metrics()
        basic_avg_time = basic_metrics['execution_time'] / iterations
        
        # Test with full enhancements
        enhanced_indicator.dynamic_bands_enabled = True
        enhanced_indicator.volume_confirmation_enabled = True
        
        profiler.reset()
        profiler.start_profiling()
        for _ in range(iterations):
            enhanced_result = enhanced_indicator.calculate_enhanced_signals(volatile_market_data)
        profiler.stop_profiling()
        
        enhanced_metrics = profiler.get_metrics()
        enhanced_avg_time = enhanced_metrics['execution_time'] / iterations
        
        # Enhanced features should have acceptable overhead (< 50% increase)
        overhead_ratio = enhanced_avg_time / basic_avg_time
        assert overhead_ratio < 1.5, f"Enhanced features too expensive: {overhead_ratio:.2f}x slower"
        
        # Memory usage should be reasonable
        memory_increase = enhanced_metrics['memory_usage']
        assert memory_increase < 100, f"Excessive memory usage: {memory_increase:.1f} MB increase"
    
    def test_memory_usage_comparison(self, performance_baseline_metrics):
        """Compare memory usage between implementations."""
        # Large dataset for memory testing
        large_dataset_size = 10000
        np.random.seed(42)
        
        large_data = pd.DataFrame({
            'close': [150 + np.random.normal(0, 5) for _ in range(large_dataset_size)],
            'volume': [20000 + np.random.randint(-5000, 5000) for _ in range(large_dataset_size)]
        })
        
        # Test legacy memory usage
        gc.collect()
        memory_before = psutil.Process().memory_info().rss / 1024 / 1024
        
        legacy_indicator = LegacyStochRSIIndicator()
        legacy_results = []
        for _ in range(10):  # Multiple calculations to accumulate memory
            result = legacy_indicator.generate_signals(large_data['close'])
            legacy_results.append(result)
        
        memory_after_legacy = psutil.Process().memory_info().rss / 1024 / 1024
        legacy_memory_usage = memory_after_legacy - memory_before
        
        # Clean up and test enhanced
        del legacy_results
        gc.collect()
        memory_before_enhanced = psutil.Process().memory_info().rss / 1024 / 1024
        
        enhanced_indicator = EnhancedStochRSIIndicator()
        enhanced_results = []
        for _ in range(10):
            result = enhanced_indicator.calculate_enhanced_signals(large_data)
            enhanced_results.append(result)
        
        memory_after_enhanced = psutil.Process().memory_info().rss / 1024 / 1024
        enhanced_memory_usage = memory_after_enhanced - memory_before_enhanced
        
        # Enhanced version should not use excessively more memory
        memory_ratio = enhanced_memory_usage / legacy_memory_usage
        assert memory_ratio < 2.0, f"Enhanced version uses too much memory: {memory_ratio:.2f}x more"
        
        # Verify baseline expectations
        baseline_max_memory = performance_baseline_metrics['enhanced_stochrsi']['max_memory_usage']
        assert enhanced_memory_usage < baseline_max_memory, f"Memory usage {enhanced_memory_usage:.1f}MB exceeds baseline {baseline_max_memory}MB"
    
    def test_signal_accuracy_improvement(self, performance_baseline_metrics):
        """Test signal accuracy improvements with Epic 1 enhancements."""
        # Generate test scenario with known signal patterns
        np.random.seed(42)
        periods = 500
        
        # Create market data with deliberate oversold/overbought conditions
        base_price = 150
        prices = [base_price]
        volumes = []
        
        for i in range(periods - 1):
            # Create oversold conditions every 50 periods
            if i % 50 == 25:  # Oversold setup
                change = -0.05  # 5% drop
                volume = 40000   # High volume
            elif i % 50 == 26:  # Recovery
                change = 0.03    # 3% recovery
                volume = 35000
            else:
                change = np.random.normal(0, 0.01)
                volume = np.random.randint(15000, 25000)
            
            prices.append(prices[-1] * (1 + change))
            volumes.append(volume)
        
        volumes.append(volumes[-1])
        
        test_data = pd.DataFrame({
            'close': prices,
            'volume': volumes
        })
        
        # Test legacy signals
        legacy_indicator = LegacyStochRSIIndicator()
        legacy_result = legacy_indicator.generate_signals(test_data['close'])
        legacy_signals = legacy_result['signals']
        legacy_signal_count = (legacy_signals != 0).sum()
        
        # Test enhanced signals
        enhanced_indicator = EnhancedStochRSIIndicator()
        enhanced_result = enhanced_indicator.calculate_enhanced_signals(test_data)
        enhanced_signals = enhanced_result['enhanced_signals']['signals']
        enhanced_signal_count = (enhanced_signals != 0).sum()
        
        # Enhanced version should generate fewer but higher quality signals
        signal_reduction_ratio = enhanced_signal_count / legacy_signal_count
        assert 0.5 <= signal_reduction_ratio <= 1.0, f"Unexpected signal count change: {signal_reduction_ratio:.2f}"
        
        # Check volume confirmation rates
        volume_confirmed_signals = enhanced_result['enhanced_signals']['volume_confirmed']
        volume_confirmation_rate = volume_confirmed_signals.sum() / len(volume_confirmed_signals)
        assert volume_confirmation_rate > 0.1, "Volume confirmation rate too low"
    
    def test_throughput_comparison(self, performance_baseline_metrics):
        """Test signal processing throughput comparison."""
        # Create multiple datasets for throughput testing
        dataset_sizes = [100, 500, 1000, 2000]
        throughput_results = {'legacy': {}, 'enhanced': {}}
        
        for size in dataset_sizes:
            # Generate test data
            test_data = pd.DataFrame({
                'close': [150 + np.random.normal(0, 5) for _ in range(size)],
                'volume': [20000 + np.random.randint(-5000, 5000) for _ in range(size)]
            })
            
            # Test legacy throughput
            legacy_indicator = LegacyStochRSIIndicator()
            start_time = time.perf_counter()
            iterations = 20
            
            for _ in range(iterations):
                legacy_indicator.generate_signals(test_data['close'])
            
            legacy_time = time.perf_counter() - start_time
            legacy_throughput = (size * iterations) / legacy_time  # data points per second
            throughput_results['legacy'][size] = legacy_throughput
            
            # Test enhanced throughput
            enhanced_indicator = EnhancedStochRSIIndicator()
            start_time = time.perf_counter()
            
            for _ in range(iterations):
                enhanced_indicator.calculate_enhanced_signals(test_data)
            
            enhanced_time = time.perf_counter() - start_time
            enhanced_throughput = (size * iterations) / enhanced_time
            throughput_results['enhanced'][size] = enhanced_throughput
        
        # Verify throughput scaling
        for size in dataset_sizes:
            legacy_throughput = throughput_results['legacy'][size]
            enhanced_throughput = throughput_results['enhanced'][size]
            
            throughput_ratio = enhanced_throughput / legacy_throughput
            
            # Enhanced version should maintain reasonable throughput
            assert throughput_ratio > 0.5, f"Enhanced throughput too low for size {size}: {throughput_ratio:.2f}"
    
    def test_latency_measurements(self, performance_baseline_metrics):
        """Test latency for real-time signal processing."""
        # Simulate real-time data updates
        enhanced_indicator = EnhancedStochRSIIndicator()
        
        # Start with base dataset
        base_size = 100
        base_data = pd.DataFrame({
            'close': [150 + np.random.normal(0, 5) for _ in range(base_size)],
            'volume': [20000 + np.random.randint(-5000, 5000) for _ in range(base_size)]
        })
        
        # Measure incremental update latencies
        latencies = []
        update_count = 50
        
        for i in range(update_count):
            # Add new data point
            new_price = base_data['close'].iloc[-1] * (1 + np.random.normal(0, 0.01))
            new_volume = 20000 + np.random.randint(-5000, 5000)
            
            new_row = pd.DataFrame({
                'close': [new_price],
                'volume': [new_volume]
            })
            
            updated_data = pd.concat([base_data, new_row], ignore_index=True)
            
            # Measure processing latency
            start_time = time.perf_counter()
            result = enhanced_indicator.calculate_enhanced_signals(updated_data)
            latency = time.perf_counter() - start_time
            
            latencies.append(latency)
            base_data = updated_data
        
        # Analyze latency statistics
        avg_latency = np.mean(latencies)
        max_latency = np.max(latencies)
        p95_latency = np.percentile(latencies, 95)
        
        # Verify latency requirements
        baseline_max_time = performance_baseline_metrics['enhanced_stochrsi']['max_processing_time']
        assert avg_latency < baseline_max_time, f"Average latency {avg_latency:.4f}s exceeds baseline {baseline_max_time}s"
        assert max_latency < baseline_max_time * 2, f"Max latency {max_latency:.4f}s too high"
        assert p95_latency < baseline_max_time * 1.5, f"P95 latency {p95_latency:.4f}s too high"
    
    def test_concurrent_processing_performance(self, performance_baseline_metrics):
        """Test performance under concurrent processing scenarios."""
        # Setup for concurrent testing
        enhanced_indicator = EnhancedStochRSIIndicator()
        num_threads = 4
        results_queue = queue.Queue()
        
        def process_data_thread(thread_id: int, data_size: int):
            """Thread function for concurrent processing."""
            # Generate thread-specific data
            np.random.seed(thread_id)
            test_data = pd.DataFrame({
                'close': [150 + np.random.normal(0, 5) for _ in range(data_size)],
                'volume': [20000 + np.random.randint(-5000, 5000) for _ in range(data_size)]
            })
            
            # Process data multiple times
            start_time = time.perf_counter()
            iterations = 10
            
            for _ in range(iterations):
                result = enhanced_indicator.calculate_enhanced_signals(test_data)
            
            processing_time = time.perf_counter() - start_time
            results_queue.put({
                'thread_id': thread_id,
                'processing_time': processing_time,
                'iterations': iterations,
                'data_size': data_size
            })
        
        # Run concurrent test
        threads = []
        data_size = 500
        start_time = time.perf_counter()
        
        for i in range(num_threads):
            thread = threading.Thread(target=process_data_thread, args=(i, data_size))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        total_time = time.perf_counter() - start_time
        
        # Collect results
        thread_results = []
        while not results_queue.empty():
            thread_results.append(results_queue.get())
        
        # Analyze concurrent performance
        assert len(thread_results) == num_threads, "Not all threads completed"
        
        avg_thread_time = np.mean([r['processing_time'] for r in thread_results])
        total_iterations = sum(r['iterations'] for r in thread_results)
        
        # Verify concurrent processing doesn't degrade performance significantly
        concurrent_throughput = (total_iterations * data_size) / total_time
        
        # Should maintain reasonable throughput under concurrency
        assert concurrent_throughput > 1000, f"Concurrent throughput too low: {concurrent_throughput:.0f} data points/sec"
    
    def test_memory_leak_detection(self, performance_baseline_metrics):
        """Test for memory leaks during extended processing."""
        enhanced_indicator = EnhancedStochRSIIndicator()
        
        # Monitor memory over extended processing
        memory_samples = []
        processing_cycles = 100
        
        for cycle in range(processing_cycles):
            # Generate fresh data each cycle
            test_data = pd.DataFrame({
                'close': [150 + np.random.normal(0, 5) for _ in range(200)],
                'volume': [20000 + np.random.randint(-5000, 5000) for _ in range(200)]
            })
            
            # Process data
            result = enhanced_indicator.calculate_enhanced_signals(test_data)
            
            # Sample memory usage every 10 cycles
            if cycle % 10 == 0:
                gc.collect()  # Force cleanup
                memory_usage = psutil.Process().memory_info().rss / 1024 / 1024
                memory_samples.append(memory_usage)
        
        # Analyze memory trend
        if len(memory_samples) >= 3:
            # Check for significant memory growth
            initial_memory = memory_samples[0]
            final_memory = memory_samples[-1]
            memory_growth = final_memory - initial_memory
            
            # Memory growth should be minimal (< 20% increase)
            growth_ratio = memory_growth / initial_memory
            assert growth_ratio < 0.2, f"Potential memory leak detected: {growth_ratio:.1%} growth"
            
            # Check for consistent upward trend
            memory_trend = np.polyfit(range(len(memory_samples)), memory_samples, 1)[0]
            assert memory_trend < 1.0, f"Memory trend too steep: {memory_trend:.2f} MB/cycle"
    
    @pytest.mark.parametrize("data_size", [100, 500, 1000, 5000])
    def test_scalability_performance(self, performance_baseline_metrics, data_size):
        """Test performance scalability with different data sizes."""
        enhanced_indicator = EnhancedStochRSIIndicator()
        
        # Generate test data
        test_data = pd.DataFrame({
            'close': [150 + np.random.normal(0, 5) for _ in range(data_size)],
            'volume': [20000 + np.random.randint(-5000, 5000) for _ in range(data_size)]
        })
        
        # Measure processing time
        start_time = time.perf_counter()
        iterations = max(1, 100 // (data_size // 100))  # Adjust iterations based on size
        
        for _ in range(iterations):
            result = enhanced_indicator.calculate_enhanced_signals(test_data)
        
        processing_time = time.perf_counter() - start_time
        avg_time_per_point = processing_time / (iterations * data_size)
        
        # Performance should scale reasonably (sublinear growth acceptable)
        baseline_time_per_point = performance_baseline_metrics['enhanced_stochrsi']['max_processing_time'] / 1000
        assert avg_time_per_point < baseline_time_per_point * 2, f"Processing too slow for size {data_size}: {avg_time_per_point:.6f}s per point"
        
        # Memory usage should also scale reasonably
        memory_before = psutil.Process().memory_info().rss / 1024 / 1024
        large_result = enhanced_indicator.calculate_enhanced_signals(test_data)
        memory_after = psutil.Process().memory_info().rss / 1024 / 1024
        memory_per_point = (memory_after - memory_before) / data_size
        
        assert memory_per_point < 0.01, f"Memory usage per point too high: {memory_per_point:.4f} MB/point"