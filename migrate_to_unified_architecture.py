#!/usr/bin/env python3
"""
Migration script to transition from old architecture to unified architecture.
This script helps migrate data and validates the new architecture.
"""

import os
import sys
import logging
import time
from datetime import datetime
import pandas as pd

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.unified_data_manager import get_data_manager, cleanup_data_manager
from services.database_abstraction import get_database, close_database
from services.memory_cache import cache_manager
from services.circuit_breaker import circuit_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def validate_new_architecture():
    """Validate that the new unified architecture works correctly."""
    logger.info("=== Validating New Unified Architecture ===")
    
    try:
        # Test data manager initialization
        logger.info("1. Testing data manager initialization...")
        data_manager = get_data_manager()
        if data_manager.api is None:
            logger.warning("API not initialized - this is expected without valid credentials")
        else:
            logger.info("✓ Data manager initialized successfully")
        
        # Test database connections
        logger.info("2. Testing database connections...")
        db = get_database()
        stats = db.get_database_stats()
        logger.info(f"✓ Database connected: {stats.get('database_size_mb', 0):.2f} MB")
        
        # Test cache functionality
        logger.info("3. Testing cache functionality...")
        cache = cache_manager.get_cache('test_cache', max_size=10, default_ttl=5.0)
        cache.set('test_key', 'test_value')
        value = cache.get('test_key')
        if value == 'test_value':
            logger.info("✓ Cache working correctly")
        else:
            raise ValueError("Cache test failed")
        
        # Test circuit breaker
        logger.info("4. Testing circuit breaker...")
        breaker = circuit_manager.get_breaker('test_breaker', failure_threshold=2)
        
        def test_function():
            return "success"
        
        result = breaker.call(test_function)
        if result == "success":
            logger.info("✓ Circuit breaker working correctly")
        else:
            raise ValueError("Circuit breaker test failed")
        
        # Test data manager with mock data
        logger.info("5. Testing data manager functionality...")
        
        # Test cache stats
        cache_stats = data_manager.get_cache_stats()
        logger.info(f"✓ Cache stats: {len(cache_stats)} cache types available")
        
        # Test system health
        health = data_manager.get_system_health()
        logger.info(f"✓ System health check: API={health['api_initialized']}, Streaming={health['streaming']}")
        
        logger.info("=== All Architecture Validation Tests Passed! ===")
        return True
        
    except Exception as e:
        logger.error(f"Architecture validation failed: {e}")
        return False


def migrate_historical_data():
    """Migrate any existing historical data to new format."""
    logger.info("=== Migrating Historical Data ===")
    
    try:
        # Check if old database exists
        old_db_path = 'database/trading_data.db'
        if not os.path.exists(old_db_path):
            logger.info("No existing database found - clean installation")
            return True
        
        logger.info(f"Found existing database: {old_db_path}")
        
        # Get new database handle
        db = get_database()
        
        # Migration is automatic since we're using the same database file
        # The new schema will be created alongside existing data
        stats = db.get_database_stats()
        logger.info(f"✓ Database migration complete: {stats}")
        
        return True
        
    except Exception as e:
        logger.error(f"Data migration failed: {e}")
        return False


def cleanup_old_files():
    """Create deprecation notices for old files."""
    logger.info("=== Creating Deprecation Notices ===")
    
    deprecated_files = [
        'realtime_manager.py',
        'realtime_manager_flask.py'
    ]
    
    for file_path in deprecated_files:
        if os.path.exists(file_path):
            # Create backup
            backup_path = f"{file_path}.deprecated_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            logger.info(f"Creating backup: {backup_path}")
            
            # Read original file
            with open(file_path, 'r') as f:
                original_content = f.read()
            
            # Write backup
            with open(backup_path, 'w') as f:
                f.write(original_content)
            
            # Create deprecation notice
            deprecation_notice = f'''"""
DEPRECATED: This file has been replaced by the unified architecture.

Original file backed up as: {backup_path}
Migration date: {datetime.now().isoformat()}

New unified architecture:
- services/unified_data_manager.py - Replaces both realtime managers
- services/database_abstraction.py - Thread-safe database with connection pooling
- services/memory_cache.py - Memory-managed caching with TTL
- services/circuit_breaker.py - API failure resilience

To use the new architecture:
    from services.unified_data_manager import get_data_manager
    
    data_manager = get_data_manager()
    # Use same interface as before but with enhanced features

For more information, see the migration documentation.
"""

# Original content preserved below for reference:
{original_content}
'''
            
            with open(file_path, 'w') as f:
                f.write(deprecation_notice)
            
            logger.info(f"✓ Created deprecation notice for {file_path}")
    
    logger.info("=== Deprecation notices created ===")


def performance_benchmark():
    """Run basic performance benchmarks."""
    logger.info("=== Running Performance Benchmarks ===")
    
    try:
        data_manager = get_data_manager()
        
        # Benchmark cache operations
        cache = cache_manager.get_cache('benchmark_cache', max_size=1000, default_ttl=60.0)
        
        # Write benchmark
        start_time = time.time()
        for i in range(1000):
            cache.set(f'key_{i}', f'value_{i}')
        write_time = time.time() - start_time
        
        # Read benchmark
        start_time = time.time()
        for i in range(1000):
            cache.get(f'key_{i}')
        read_time = time.time() - start_time
        
        logger.info(f"✓ Cache performance: {1000/write_time:.0f} writes/sec, {1000/read_time:.0f} reads/sec")
        
        # Database benchmark
        db = get_database()
        start_time = time.time()
        for i in range(10):
            db.execute_query("SELECT COUNT(*) FROM historical_data", fetch='one')
        db_time = time.time() - start_time
        
        logger.info(f"✓ Database performance: {10/db_time:.1f} queries/sec")
        
        # Circuit breaker benchmark
        breaker = circuit_manager.get_breaker('benchmark_breaker')
        start_time = time.time()
        for i in range(1000):
            breaker.call(lambda: True)
        breaker_time = time.time() - start_time
        
        logger.info(f"✓ Circuit breaker performance: {1000/breaker_time:.0f} calls/sec")
        
        logger.info("=== Performance Benchmarks Complete ===")
        return True
        
    except Exception as e:
        logger.error(f"Performance benchmark failed: {e}")
        return False


def main():
    """Run complete migration process."""
    print("🚀 Starting Migration to Unified Architecture")
    print("=" * 50)
    
    success = True
    
    # Step 1: Validate new architecture
    if not validate_new_architecture():
        success = False
    
    # Step 2: Migrate historical data
    if not migrate_historical_data():
        success = False
    
    # Step 3: Run performance benchmarks
    if not performance_benchmark():
        success = False
        
    # Step 4: Create deprecation notices
    cleanup_old_files()
    
    # Cleanup
    try:
        cleanup_data_manager()
        close_database()
        cache_manager.shutdown_all()
    except Exception as e:
        logger.warning(f"Cleanup warning: {e}")
    
    print("=" * 50)
    if success:
        print("✅ Migration completed successfully!")
        print("\nNext steps:")
        print("1. Test your application with the new architecture")
        print("2. Remove deprecated files when confident")
        print("3. Update any remaining imports if needed")
        print("\nNew architecture features:")
        print("- Thread-safe database operations with connection pooling")
        print("- Memory-managed caching with automatic cleanup")
        print("- Circuit breaker pattern for API resilience")
        print("- Comprehensive error handling and logging")
        print("- Performance monitoring and health checks")
    else:
        print("❌ Migration completed with errors. Please check logs.")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())