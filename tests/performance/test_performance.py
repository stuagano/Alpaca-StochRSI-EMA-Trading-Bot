"""
Performance and load testing suite for the trading bot.
Tests system performance under various loads and stress conditions.
"""

import pytest
import time
import threading
import multiprocessing
import psutil
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
import gc
import sys
import tracemalloc

from trading_bot import TradingBot
from strategies.stoch_rsi_strategy import StochRSIStrategy
from services.data_service import TradingDataService
from tests.mocks.alpaca_api_mock import create_mock_alpaca_api
from tests.fixtures.market_data_fixtures import MarketDataGenerator
from tests.fixtures.order_fixtures import OrderGenerator


@pytest.mark.performance
class TestTradingBotPerformance:
    """Performance tests for trading bot operations."""
    
    def test_strategy_execution_speed(self, benchmark, test_config):
        """Benchmark strategy execution speed."""
        strategy = StochRSIStrategy(test_config)
        
        # Generate large dataset
        generator = MarketDataGenerator()
        large_dataset = generator.generate_intraday_data(
            symbol="AAPL",
            date=datetime.now().strftime('%Y-%m-%d'),
            periods=1000  # 1000 data points
        )
        
        # Mock strategy dependencies
        with patch('strategies.stoch_rsi_strategy.rsi') as mock_rsi, \
             patch('strategies.stoch_rsi_strategy.stochastic') as mock_stoch:
            
            df_with_signals = large_dataset.copy()
            df_with_signals['StochRSI Signal'] = np.random.choice([0, 1], size=len(large_dataset))
            
            mock_rsi.return_value = df_with_signals
            mock_stoch.return_value = df_with_signals
            
            # Benchmark strategy execution
            result = benchmark(strategy.generate_signal, large_dataset)
            assert result in [0, 1]
    
    def test_data_processing_throughput(self, benchmark, temp_db):
        """Benchmark data processing throughput."""
        service = TradingDataService()
        service.db_manager.db_path = temp_db
        
        def process_large_batch():
            """Process a large batch of orders."""
            order_gen = OrderGenerator()
            orders = []
            
            for i in range(100):
                order_data = {
                    'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'ticker': f'STOCK{i%10}',
                    'type': 'buy',
                    'buy_price': 100.0 + i,
                    'quantity': 10,
                    'total': (100.0 + i) * 10,
                    'acc_balance': 50000.0
                }
                order_id = service.add_completed_order(order_data)
                orders.append(order_id)
            
            return orders
        
        # Benchmark batch processing
        order_ids = benchmark(process_large_batch)
        assert len(order_ids) == 100
    
    def test_position_monitoring_scale(self, benchmark, integration_test_setup):
        """Benchmark position monitoring with many positions."""
        setup = integration_test_setup
        bot = setup['bot']
        
        # Create many mock positions
        positions = []
        for i in range(100):
            position = Mock()
            position.symbol = f'STOCK{i}'
            position.qty = 10
            position.avg_entry_price = 100.0 + i
            position.client_order_id = f'order_{i}'
            positions.append(position)
        
        bot.api.list_positions.return_value = positions
        bot.data_manager.get_latest_price.return_value = 150.0
        bot.enable_enhanced_risk_management = False
        
        # Mock order lookup
        mock_order = Mock()
        mock_order.client_order_id = 'sl_142.50_tp_165.00'
        bot.api.get_order_by_client_order_id.return_value = mock_order
        
        # Benchmark position monitoring
        benchmark(bot.check_open_positions)
    
    def test_memory_usage_large_dataset(self, test_config):
        """Test memory usage with large datasets."""
        tracemalloc.start()
        
        strategy = StochRSIStrategy(test_config)
        generator = MarketDataGenerator()
        
        # Generate very large dataset
        large_dataset = generator.generate_intraday_data(
            symbol="AAPL",
            date=datetime.now().strftime('%Y-%m-%d'),
            periods=10000  # 10k data points
        )
        
        # Monitor memory before processing
        snapshot1 = tracemalloc.take_snapshot()
        
        # Process data
        with patch('strategies.stoch_rsi_strategy.rsi') as mock_rsi, \
             patch('strategies.stoch_rsi_strategy.stochastic') as mock_stoch:
            
            df_with_signals = large_dataset.copy()
            df_with_signals['StochRSI Signal'] = 0
            
            mock_rsi.return_value = df_with_signals
            mock_stoch.return_value = df_with_signals
            
            result = strategy.generate_signal(large_dataset)
        
        # Monitor memory after processing
        snapshot2 = tracemalloc.take_snapshot()
        
        # Calculate memory difference
        top_stats = snapshot2.compare_to(snapshot1, 'lineno')
        total_size = sum(stat.size_diff for stat in top_stats)
        
        # Memory increase should be reasonable (less than 50MB)
        assert total_size < 50 * 1024 * 1024, f"Memory increase too large: {total_size / 1024 / 1024:.2f}MB"
        
        tracemalloc.stop()
    
    @pytest.mark.slow
    def test_sustained_operation_performance(self, integration_test_setup):
        """Test performance during sustained operations."""
        setup = integration_test_setup
        bot = setup['bot']
        
        # Setup for sustained operation
        bot.tickers = ['AAPL', 'TSLA', 'GOOGL']
        bot.api.list_positions.return_value = []
        
        # Generate market data
        generator = MarketDataGenerator()
        market_data = generator.generate_intraday_data('AAPL', datetime.now().strftime('%Y-%m-%d'))
        bot.data_manager.get_historical_data.return_value = market_data
        bot.data_manager.get_latest_price.return_value = 150.0
        bot.strategy.generate_signal.return_value = 0  # No trades to avoid order placement
        
        # Run sustained operations
        start_time = time.time()
        operation_times = []
        
        for i in range(50):  # 50 iterations
            iter_start = time.time()
            bot.run_strategy()
            iter_end = time.time()
            
            operation_times.append(iter_end - iter_start)
            
            # Brief pause to simulate real trading intervals
            time.sleep(0.01)
        
        total_time = time.time() - start_time
        
        # Performance assertions
        avg_time = np.mean(operation_times)
        max_time = np.max(operation_times)
        
        assert avg_time < 0.1, f"Average operation time too slow: {avg_time:.3f}s"
        assert max_time < 0.5, f"Maximum operation time too slow: {max_time:.3f}s"
        assert total_time < 10, f"Total time too long: {total_time:.3f}s"


@pytest.mark.performance
class TestConcurrencyPerformance:
    """Test performance under concurrent operations."""
    
    def test_concurrent_strategy_execution(self, test_config):
        """Test strategy execution under concurrent load."""
        strategy = StochRSIStrategy(test_config)
        generator = MarketDataGenerator()
        
        # Generate test data
        test_data = generator.generate_intraday_data('AAPL', datetime.now().strftime('%Y-%m-%d'))
        
        def execute_strategy():
            """Execute strategy with mocked dependencies."""
            with patch('strategies.stoch_rsi_strategy.rsi') as mock_rsi, \
                 patch('strategies.stoch_rsi_strategy.stochastic') as mock_stoch:
                
                df_with_signals = test_data.copy()
                df_with_signals['StochRSI Signal'] = 0
                
                mock_rsi.return_value = df_with_signals
                mock_stoch.return_value = df_with_signals
                
                return strategy.generate_signal(test_data)
        
        # Test concurrent execution
        with ThreadPoolExecutor(max_workers=10) as executor:
            start_time = time.time()
            futures = [executor.submit(execute_strategy) for _ in range(20)]
            results = [future.result() for future in futures]
            end_time = time.time()
        
        # Verify results
        assert len(results) == 20
        assert all(result in [0, 1] for result in results)
        
        # Performance check
        total_time = end_time - start_time
        assert total_time < 5.0, f"Concurrent execution too slow: {total_time:.3f}s"
    
    def test_concurrent_database_operations(self, temp_db):
        """Test concurrent database operations."""
        def database_worker(worker_id):
            """Worker function for database operations."""
            service = TradingDataService()
            service.db_manager.db_path = temp_db
            
            orders_created = 0
            for i in range(10):
                order_data = {
                    'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'ticker': f'STOCK{worker_id}_{i}',
                    'type': 'buy',
                    'buy_price': 100.0 + i,
                    'quantity': 10,
                    'total': (100.0 + i) * 10,
                    'acc_balance': 50000.0
                }
                
                try:
                    order_id = service.add_completed_order(order_data)
                    if order_id:
                        orders_created += 1
                except Exception:
                    pass  # Some contention expected
            
            return orders_created
        
        # Run concurrent database operations
        with ThreadPoolExecutor(max_workers=5) as executor:
            start_time = time.time()
            futures = [executor.submit(database_worker, i) for i in range(5)]
            results = [future.result() for future in futures]
            end_time = time.time()
        
        # Verify operations completed
        total_orders = sum(results)
        assert total_orders >= 40, f"Too few orders created: {total_orders}"
        
        # Performance check
        total_time = end_time - start_time
        assert total_time < 10.0, f"Concurrent database operations too slow: {total_time:.3f}s"
    
    def test_multiprocess_performance(self, test_config):
        """Test performance with multiprocessing."""
        def worker_process(worker_id):
            """Worker process for testing."""
            np.random.seed(worker_id)  # Different seed per process
            
            strategy = StochRSIStrategy(test_config)
            generator = MarketDataGenerator(seed=worker_id)
            
            # Generate unique data per process
            test_data = generator.generate_intraday_data(
                f'STOCK{worker_id}', 
                datetime.now().strftime('%Y-%m-%d'),
                periods=100
            )
            
            # Simulate strategy execution
            execution_times = []
            for _ in range(10):
                start = time.time()
                
                # Mock strategy execution
                with patch('strategies.stoch_rsi_strategy.rsi') as mock_rsi, \
                     patch('strategies.stoch_rsi_strategy.stochastic') as mock_stoch:
                    
                    df_with_signals = test_data.copy()
                    df_with_signals['StochRSI Signal'] = 0
                    
                    mock_rsi.return_value = df_with_signals
                    mock_stoch.return_value = df_with_signals
                    
                    result = strategy.generate_signal(test_data)
                
                execution_times.append(time.time() - start)
            
            return {
                'worker_id': worker_id,
                'avg_time': np.mean(execution_times),
                'max_time': np.max(execution_times),
                'executions': len(execution_times)
            }
        
        # Run multiprocess test
        with ProcessPoolExecutor(max_workers=4) as executor:
            start_time = time.time()
            futures = [executor.submit(worker_process, i) for i in range(4)]
            results = [future.result() for future in futures]
            end_time = time.time()
        
        # Verify results
        assert len(results) == 4
        total_executions = sum(r['executions'] for r in results)
        assert total_executions == 40
        
        # Performance checks
        avg_times = [r['avg_time'] for r in results]
        max_avg_time = max(avg_times)
        
        total_time = end_time - start_time
        assert total_time < 15.0, f"Multiprocess execution too slow: {total_time:.3f}s"
        assert max_avg_time < 0.1, f"Individual process too slow: {max_avg_time:.3f}s"


@pytest.mark.performance
class TestMemoryPerformance:
    """Test memory usage and leak detection."""
    
    def test_memory_leak_detection(self, integration_test_setup):
        """Test for memory leaks during repeated operations."""
        setup = integration_test_setup
        bot = setup['bot']
        
        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # Setup test data
        generator = MarketDataGenerator()
        test_data = generator.generate_intraday_data('AAPL', datetime.now().strftime('%Y-%m-%d'))
        
        bot.data_manager.get_historical_data.return_value = test_data
        bot.data_manager.get_latest_price.return_value = 150.0
        bot.strategy.generate_signal.return_value = 0
        bot.api.list_positions.return_value = []
        
        # Run repeated operations
        memory_samples = []
        for i in range(100):
            bot.run_strategy()
            
            # Sample memory every 10 iterations
            if i % 10 == 0:
                current_memory = process.memory_info().rss
                memory_samples.append(current_memory)
                
                # Force garbage collection
                gc.collect()
        
        final_memory = process.memory_info().rss
        
        # Check for memory leaks
        memory_increase = final_memory - initial_memory
        memory_increase_mb = memory_increase / (1024 * 1024)
        
        # Memory increase should be minimal (<10MB)
        assert memory_increase_mb < 10, f"Potential memory leak: {memory_increase_mb:.2f}MB increase"
        
        # Check memory trend
        if len(memory_samples) > 2:
            # Simple linear regression to check for upward trend
            x = np.arange(len(memory_samples))
            y = np.array(memory_samples)
            slope = np.polyfit(x, y, 1)[0]
            
            # Slope should be minimal (< 1MB per sample)
            slope_mb_per_sample = slope / (1024 * 1024)
            assert slope_mb_per_sample < 1, f"Memory trending upward: {slope_mb_per_sample:.3f}MB per sample"
    
    def test_large_dataset_memory_efficiency(self, test_config):
        """Test memory efficiency with large datasets."""
        tracemalloc.start()
        
        strategy = StochRSIStrategy(test_config)
        generator = MarketDataGenerator()
        
        # Test with increasingly large datasets
        dataset_sizes = [1000, 5000, 10000]
        memory_usage = []
        
        for size in dataset_sizes:
            # Clear memory
            gc.collect()
            snapshot_start = tracemalloc.take_snapshot()
            
            # Generate large dataset
            large_data = generator.generate_intraday_data(
                'AAPL', 
                datetime.now().strftime('%Y-%m-%d'),
                periods=size
            )
            
            # Process dataset
            with patch('strategies.stoch_rsi_strategy.rsi') as mock_rsi, \
                 patch('strategies.stoch_rsi_strategy.stochastic') as mock_stoch:
                
                df_with_signals = large_data.copy()
                df_with_signals['StochRSI Signal'] = 0
                
                mock_rsi.return_value = df_with_signals
                mock_stoch.return_value = df_with_signals
                
                result = strategy.generate_signal(large_data)
            
            snapshot_end = tracemalloc.take_snapshot()
            
            # Calculate memory usage
            top_stats = snapshot_end.compare_to(snapshot_start, 'lineno')
            total_memory = sum(stat.size for stat in top_stats if stat.size > 0)
            memory_usage.append((size, total_memory))
            
            # Clean up
            del large_data
            gc.collect()
        
        tracemalloc.stop()
        
        # Check memory scaling
        for i, (size, memory) in enumerate(memory_usage):
            memory_mb = memory / (1024 * 1024)
            memory_per_record = memory / size
            
            # Memory per record should be reasonable
            assert memory_per_record < 1000, f"Memory per record too high: {memory_per_record} bytes"
            assert memory_mb < 100, f"Total memory usage too high: {memory_mb:.2f}MB for {size} records"
    
    def test_garbage_collection_effectiveness(self, integration_test_setup):
        """Test garbage collection effectiveness."""
        setup = integration_test_setup
        bot = setup['bot']
        
        # Get initial object count
        gc.collect()
        initial_objects = len(gc.get_objects())
        
        # Create many temporary objects
        temp_objects = []
        for i in range(1000):
            # Create various objects that should be garbage collected
            temp_data = pd.DataFrame({
                'timestamp': pd.date_range(start='2024-01-01', periods=100, freq='1min'),
                'price': np.random.random(100) * 100
            })
            temp_objects.append(temp_data)
        
        objects_after_creation = len(gc.get_objects())
        
        # Clear references
        temp_objects.clear()
        del temp_objects
        
        # Force garbage collection
        collected = gc.collect()
        final_objects = len(gc.get_objects())
        
        # Check garbage collection effectiveness
        objects_cleaned = objects_after_creation - final_objects
        cleanup_rate = objects_cleaned / (objects_after_creation - initial_objects)
        
        assert collected > 0, "No objects were garbage collected"
        assert cleanup_rate > 0.8, f"Garbage collection not effective: {cleanup_rate:.2%} cleanup rate"


@pytest.mark.performance
@pytest.mark.slow
class TestStressTests:
    """Stress tests for extreme conditions."""
    
    def test_high_frequency_operations(self, integration_test_setup):
        """Test high-frequency trading operations."""
        setup = integration_test_setup
        bot = setup['bot']
        
        # Setup for high-frequency testing
        bot.tickers = ['AAPL']
        bot.api.list_positions.return_value = []
        
        generator = MarketDataGenerator()
        test_data = generator.generate_intraday_data('AAPL', datetime.now().strftime('%Y-%m-%d'))
        
        bot.data_manager.get_historical_data.return_value = test_data
        bot.data_manager.get_latest_price.return_value = 150.0
        bot.strategy.generate_signal.return_value = 0
        
        # Rapid-fire operations
        start_time = time.time()
        operations_completed = 0
        
        target_duration = 5.0  # 5 seconds
        while time.time() - start_time < target_duration:
            try:
                bot.run_strategy()
                operations_completed += 1
            except Exception:
                break
        
        actual_duration = time.time() - start_time
        operations_per_second = operations_completed / actual_duration
        
        # Should handle at least 10 operations per second
        assert operations_per_second >= 10, f"Low throughput: {operations_per_second:.2f} ops/sec"
        assert operations_completed >= 50, f"Too few operations completed: {operations_completed}"
    
    def test_extreme_market_volatility(self, test_config):
        """Test performance under extreme market conditions."""
        strategy = StochRSIStrategy(test_config)
        generator = MarketDataGenerator()
        
        # Generate extremely volatile data
        volatile_data = generator.generate_intraday_data(
            'AAPL',
            datetime.now().strftime('%Y-%m-%d'),
            volatility=0.20,  # 20% volatility
            periods=1000
        )
        
        # Add extreme price movements
        volatile_data.loc[500:510, 'close'] *= 1.15  # 15% spike
        volatile_data.loc[700:710, 'close'] *= 0.85  # 15% drop
        
        execution_times = []
        
        # Test strategy performance with volatile data
        for _ in range(10):
            with patch('strategies.stoch_rsi_strategy.rsi') as mock_rsi, \
                 patch('strategies.stoch_rsi_strategy.stochastic') as mock_stoch:
                
                df_with_signals = volatile_data.copy()
                df_with_signals['StochRSI Signal'] = np.random.choice([0, 1], size=len(volatile_data))
                
                mock_rsi.return_value = df_with_signals
                mock_stoch.return_value = df_with_signals
                
                start = time.time()
                result = strategy.generate_signal(volatile_data)
                execution_times.append(time.time() - start)
        
        # Performance should remain stable despite volatility
        avg_time = np.mean(execution_times)
        max_time = np.max(execution_times)
        
        assert avg_time < 0.1, f"Strategy too slow with volatile data: {avg_time:.3f}s"
        assert max_time < 0.2, f"Strategy inconsistent with volatile data: {max_time:.3f}s"
    
    def test_system_resource_limits(self, integration_test_setup):
        """Test behavior at system resource limits."""
        setup = integration_test_setup
        bot = setup['bot']
        
        # Monitor system resources
        process = psutil.Process()
        
        # Test with maximum reasonable load
        bot.tickers = [f'STOCK{i}' for i in range(20)]  # 20 symbols
        
        # Create complex market data for each symbol
        generator = MarketDataGenerator()
        
        def get_complex_data(symbol):
            return generator.generate_intraday_data(symbol, datetime.now().strftime('%Y-%m-%d'), periods=500)
        
        bot.data_manager.get_historical_data.side_effect = get_complex_data
        bot.data_manager.get_latest_price.return_value = 150.0
        bot.strategy.generate_signal.return_value = 0
        bot.api.list_positions.return_value = []
        
        # Monitor resource usage during execution
        start_time = time.time()
        max_memory = 0
        max_cpu = 0
        
        for i in range(5):  # 5 iterations
            iter_start = time.time()
            
            bot.run_strategy()
            
            # Monitor resources
            memory_percent = process.memory_percent()
            cpu_percent = process.cpu_percent()
            
            max_memory = max(max_memory, memory_percent)
            max_cpu = max(max_cpu, cpu_percent)
            
            iter_time = time.time() - iter_start
            
            # Each iteration should complete reasonably quickly
            assert iter_time < 5.0, f"Iteration {i} too slow: {iter_time:.3f}s"
        
        total_time = time.time() - start_time
        
        # Resource usage checks
        assert max_memory < 80, f"Memory usage too high: {max_memory:.1f}%"
        assert total_time < 30, f"Total execution too slow: {total_time:.3f}s"


@pytest.mark.performance
class TestBenchmarkBaselines:
    """Establish performance baselines for monitoring."""
    
    def test_strategy_execution_baseline(self, benchmark, test_config):
        """Establish baseline for strategy execution time."""
        strategy = StochRSIStrategy(test_config)
        generator = MarketDataGenerator()
        
        # Standard test data
        test_data = generator.generate_intraday_data(
            'AAPL', 
            datetime.now().strftime('%Y-%m-%d'),
            periods=390  # Full trading day
        )
        
        def execute_strategy():
            with patch('strategies.stoch_rsi_strategy.rsi') as mock_rsi, \
                 patch('strategies.stoch_rsi_strategy.stochastic') as mock_stoch:
                
                df_with_signals = test_data.copy()
                df_with_signals['StochRSI Signal'] = 0
                
                mock_rsi.return_value = df_with_signals
                mock_stoch.return_value = df_with_signals
                
                return strategy.generate_signal(test_data)
        
        # Benchmark with baseline expectations
        result = benchmark.pedantic(execute_strategy, rounds=10, iterations=3)
        
        # Store baseline for comparison
        baseline_time = benchmark.stats['mean']
        
        # Baseline should be under 50ms for standard dataset
        assert baseline_time < 0.05, f"Baseline too slow: {baseline_time:.4f}s"
        
        return baseline_time
    
    def test_database_operations_baseline(self, benchmark, temp_db):
        """Establish baseline for database operations."""
        service = TradingDataService()
        service.db_manager.db_path = temp_db
        
        def database_operations():
            # Standard database operation set
            order_data = {
                'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'ticker': 'AAPL',
                'type': 'buy',
                'buy_price': 150.0,
                'quantity': 10,
                'total': 1500.0,
                'acc_balance': 50000.0
            }
            
            # Create order
            order_id = service.add_completed_order(order_data)
            
            # Query orders
            orders = service.get_completed_orders('AAPL')
            
            # Get portfolio summary
            summary = service.get_portfolio_summary()
            
            return order_id, len(orders), summary
        
        # Benchmark database operations
        result = benchmark.pedantic(database_operations, rounds=5, iterations=2)
        
        baseline_time = benchmark.stats['mean']
        
        # Database operations should be under 10ms
        assert baseline_time < 0.01, f"Database baseline too slow: {baseline_time:.4f}s"
        
        return baseline_time
    
    def test_api_response_baseline(self, benchmark):
        """Establish baseline for API response times."""
        mock_api = create_mock_alpaca_api()
        
        def api_operations():
            # Standard API operation set
            account = mock_api.get_account()
            positions = mock_api.list_positions()
            clock = mock_api.get_clock()
            bars = mock_api.get_bars('AAPL', '1Min', limit=100)
            
            return account, positions, clock, len(bars)
        
        # Benchmark API operations
        result = benchmark.pedantic(api_operations, rounds=10, iterations=5)
        
        baseline_time = benchmark.stats['mean']
        
        # API operations should be very fast (under 1ms for mocked)
        assert baseline_time < 0.001, f"API baseline too slow: {baseline_time:.4f}s"
        
        return baseline_time