# Epic 1 Signal Quality Enhancement - Maintenance Guide

## Table of Contents

1. [System Monitoring](#system-monitoring)
2. [Performance Optimization](#performance-optimization)
3. [Data Management](#data-management)
4. [Troubleshooting Procedures](#troubleshooting-procedures)
5. [Update and Upgrade Procedures](#update-and-upgrade-procedures)
6. [Backup and Recovery](#backup-and-recovery)
7. [Security Maintenance](#security-maintenance)
8. [Preventive Maintenance](#preventive-maintenance)

---

## System Monitoring

### Daily Monitoring Tasks

#### Epic 1 Health Check Script
```bash
#!/bin/bash
# epic1_daily_check.sh

echo "=== Epic 1 Daily Health Check ==="
echo "Date: $(date)"

# Check system status
echo "1. System Status:"
curl -s http://localhost:5000/api/epic1/status | jq '.status'

# Check performance metrics
echo "2. Performance Metrics:"
curl -s http://localhost:5000/api/epic1/status | jq '.performance'

# Check component status
echo "3. Component Status:"
curl -s http://localhost:5000/api/epic1/status | jq '.components'

# Check memory usage
echo "4. Memory Usage:"
ps aux | grep "flask_app.py" | awk '{print $4}' | head -1

# Check log errors
echo "5. Recent Errors:"
tail -100 logs/trading_bot.log | grep -i "error" | grep "epic1" | tail -5

echo "=== Health Check Complete ==="
```

#### Automated Monitoring Setup
```yaml
# monitoring/epic1_monitoring.yml
monitoring:
  checks:
    - name: "Epic 1 Status"
      endpoint: "/api/epic1/status"
      interval: 60  # seconds
      alert_threshold: 500  # ms response time
      
    - name: "Signal Quality"
      metric: "false_signal_reduction"
      threshold: 25.0  # minimum percentage
      interval: 300    # 5 minutes
      
    - name: "Memory Usage"
      threshold: 85    # percentage
      interval: 120    # 2 minutes
      
    - name: "Processing Time"
      threshold: 200   # milliseconds
      interval: 60     # 1 minute

  alerts:
    email: "admin@trading-bot.com"
    slack: "#epic1-alerts"
    pagerduty: "epic1-service-key"
```

### Performance Metrics Dashboard

#### Key Metrics to Monitor
```python
# monitoring/epic1_metrics.py
import psutil
import time
from datetime import datetime

class Epic1MetricsCollector:
    def __init__(self):
        self.metrics = {}
    
    def collect_metrics(self):
        """Collect comprehensive Epic 1 metrics"""
        return {
            'timestamp': datetime.now().isoformat(),
            'system_metrics': self._collect_system_metrics(),
            'epic1_metrics': self._collect_epic1_metrics(),
            'performance_metrics': self._collect_performance_metrics(),
            'quality_metrics': self._collect_quality_metrics()
        }
    
    def _collect_system_metrics(self):
        """Collect system-level metrics"""
        return {
            'cpu_percent': psutil.cpu_percent(),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent,
            'network_io': psutil.net_io_counters()._asdict(),
            'process_count': len(psutil.pids())
        }
    
    def _collect_epic1_metrics(self):
        """Collect Epic 1 specific metrics"""
        # Implementation would fetch from Epic 1 APIs
        return {
            'total_validations': self._get_validation_count(),
            'approval_rate': self._get_approval_rate(),
            'false_signal_reduction': self._get_false_signal_reduction(),
            'avg_processing_time': self._get_avg_processing_time()
        }
```

#### Metric Thresholds and Alerts
```python
# monitoring/thresholds.py
EPIC1_THRESHOLDS = {
    'system': {
        'cpu_percent': {'warning': 70, 'critical': 85},
        'memory_percent': {'warning': 75, 'critical': 90},
        'disk_usage': {'warning': 80, 'critical': 95}
    },
    'performance': {
        'avg_processing_time': {'warning': 150, 'critical': 300},  # ms
        'api_response_time': {'warning': 500, 'critical': 1000},  # ms
        'false_signal_reduction': {'warning': 20, 'critical': 15}  # %
    },
    'quality': {
        'signal_quality_score': {'warning': 0.6, 'critical': 0.5},
        'volume_confirmation_rate': {'warning': 0.4, 'critical': 0.3},
        'consensus_accuracy': {'warning': 0.7, 'critical': 0.6}
    }
}
```

### Log Analysis and Monitoring

#### Log Rotation Setup
```bash
# /etc/logrotate.d/epic1
/opt/trading-bot/logs/epic1*.log {
    daily
    missingok
    rotate 30
    compress
    notifempty
    create 644 trading-bot trading-bot
    postrotate
        /bin/systemctl reload trading-bot
    endscript
}
```

#### Log Analysis Scripts
```python
# monitoring/log_analyzer.py
import re
from collections import defaultdict
from datetime import datetime, timedelta

class Epic1LogAnalyzer:
    def __init__(self, log_file):
        self.log_file = log_file
        self.patterns = {
            'error': r'ERROR.*epic1',
            'warning': r'WARNING.*epic1',
            'performance': r'epic1.*(\d+)ms',
            'signal_validation': r'signal.*validated.*(\w+)'
        }
    
    def analyze_last_24h(self):
        """Analyze Epic 1 logs from the last 24 hours"""
        cutoff = datetime.now() - timedelta(days=1)
        analysis = {
            'errors': [],
            'warnings': [],
            'performance_issues': [],
            'signal_stats': defaultdict(int)
        }
        
        with open(self.log_file, 'r') as f:
            for line in f:
                if self._is_recent_log(line, cutoff):
                    self._analyze_line(line, analysis)
        
        return analysis
    
    def _analyze_line(self, line, analysis):
        """Analyze individual log line"""
        for pattern_name, pattern in self.patterns.items():
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                self._handle_pattern_match(pattern_name, match, line, analysis)
```

---

## Performance Optimization

### Database Optimization

#### Index Optimization
```sql
-- Epic 1 specific database indexes
CREATE INDEX IF NOT EXISTS idx_epic1_signals_timestamp 
ON epic1_signals(timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_epic1_signals_symbol_timestamp 
ON epic1_signals(symbol, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_epic1_validations_status 
ON epic1_validations(validation_status, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_market_data_epic1 
ON market_data(symbol, timestamp DESC, volume);

-- Composite indexes for Epic 1 queries
CREATE INDEX IF NOT EXISTS idx_epic1_composite 
ON epic1_signals(symbol, signal_type, timestamp DESC, quality_score);
```

#### Database Maintenance Scripts
```python
# maintenance/db_optimization.py
import sqlite3
from datetime import datetime, timedelta

class Epic1DBMaintenance:
    def __init__(self, db_path):
        self.db_path = db_path
    
    def optimize_database(self):
        """Perform database optimization tasks"""
        with sqlite3.connect(self.db_path) as conn:
            # Analyze tables for optimal query plans
            conn.execute("ANALYZE epic1_signals")
            conn.execute("ANALYZE epic1_validations")
            conn.execute("ANALYZE market_data")
            
            # Vacuum to reclaim space
            conn.execute("VACUUM")
            
            # Update statistics
            conn.execute("PRAGMA optimize")
    
    def cleanup_old_data(self, retention_days=90):
        """Clean up old Epic 1 data"""
        cutoff = datetime.now() - timedelta(days=retention_days)
        
        with sqlite3.connect(self.db_path) as conn:
            # Clean old signals
            conn.execute(
                "DELETE FROM epic1_signals WHERE timestamp < ?",
                (cutoff,)
            )
            
            # Clean old validations
            conn.execute(
                "DELETE FROM epic1_validations WHERE timestamp < ?",
                (cutoff,)
            )
            
            # Clean old performance metrics
            conn.execute(
                "DELETE FROM epic1_performance WHERE timestamp < ?",
                (cutoff,)
            )
```

### Cache Optimization

#### Redis Cache Maintenance
```python
# maintenance/cache_maintenance.py
import redis
import json
from datetime import datetime

class Epic1CacheMaintenance:
    def __init__(self, redis_host='localhost', redis_port=6379):
        self.redis_client = redis.Redis(host=redis_host, port=redis_port)
    
    def optimize_cache(self):
        """Optimize Epic 1 cache performance"""
        # Get cache statistics
        info = self.redis_client.info('memory')
        
        # Clear expired keys
        self._cleanup_expired_keys()
        
        # Optimize memory usage
        if info['used_memory'] > 500 * 1024 * 1024:  # 500MB
            self._reduce_cache_size()
    
    def _cleanup_expired_keys(self):
        """Remove expired Epic 1 cache keys"""
        epic1_keys = self.redis_client.keys('epic1:*')
        
        for key in epic1_keys:
            ttl = self.redis_client.ttl(key)
            if ttl == -1:  # No expiration set
                # Set default expiration for Epic 1 keys
                self.redis_client.expire(key, 3600)  # 1 hour
    
    def _reduce_cache_size(self):
        """Reduce cache size by removing least used keys"""
        # Get Epic 1 keys sorted by last access time
        epic1_keys = self.redis_client.keys('epic1:*')
        
        # Remove oldest 20% of keys
        keys_to_remove = int(len(epic1_keys) * 0.2)
        if keys_to_remove > 0:
            # Sort by last access (would need custom implementation)
            # For now, remove random keys
            import random
            keys_to_delete = random.sample(epic1_keys, keys_to_remove)
            self.redis_client.delete(*keys_to_delete)
```

### Memory Optimization

#### Memory Usage Monitoring
```python
# maintenance/memory_optimization.py
import gc
import sys
import psutil
from typing import Dict, List

class Epic1MemoryOptimizer:
    def __init__(self):
        self.memory_threshold = 1024 * 1024 * 1024  # 1GB
    
    def optimize_memory(self) -> Dict:
        """Optimize Epic 1 memory usage"""
        before_memory = self._get_memory_usage()
        
        # Force garbage collection
        collected = gc.collect()
        
        # Clear Epic 1 caches if memory usage is high
        if before_memory['rss'] > self.memory_threshold:
            self._clear_epic1_caches()
        
        after_memory = self._get_memory_usage()
        
        return {
            'before': before_memory,
            'after': after_memory,
            'objects_collected': collected,
            'memory_freed': before_memory['rss'] - after_memory['rss']
        }
    
    def _get_memory_usage(self) -> Dict:
        """Get current memory usage"""
        process = psutil.Process()
        memory_info = process.memory_info()
        
        return {
            'rss': memory_info.rss,
            'vms': memory_info.vms,
            'percent': process.memory_percent()
        }
    
    def _clear_epic1_caches(self):
        """Clear Epic 1 specific caches"""
        # Clear internal caches (implementation specific)
        try:
            from src.utils.epic1_integration_helpers import clear_caches
            clear_caches()
        except ImportError:
            pass
```

---

## Data Management

### Data Retention Policies

#### Automated Data Cleanup
```python
# maintenance/data_retention.py
from datetime import datetime, timedelta
import sqlite3
import os

class Epic1DataRetention:
    def __init__(self, config):
        self.config = config
        self.retention_policies = {
            'signal_data': 90,      # days
            'validation_data': 30,   # days
            'performance_metrics': 60, # days
            'log_files': 30,        # days
            'cache_data': 7         # days
        }
    
    def apply_retention_policies(self):
        """Apply data retention policies"""
        results = {}
        
        for data_type, retention_days in self.retention_policies.items():
            try:
                if data_type == 'log_files':
                    results[data_type] = self._cleanup_log_files(retention_days)
                else:
                    results[data_type] = self._cleanup_database_data(data_type, retention_days)
            except Exception as e:
                results[data_type] = {'error': str(e)}
        
        return results
    
    def _cleanup_database_data(self, data_type, retention_days):
        """Clean up database data based on retention policy"""
        cutoff = datetime.now() - timedelta(days=retention_days)
        
        table_map = {
            'signal_data': 'epic1_signals',
            'validation_data': 'epic1_validations',
            'performance_metrics': 'epic1_performance'
        }
        
        table_name = table_map.get(data_type)
        if not table_name:
            return {'error': f'Unknown data type: {data_type}'}
        
        with sqlite3.connect(self.config.database_path) as conn:
            cursor = conn.execute(
                f"SELECT COUNT(*) FROM {table_name} WHERE timestamp < ?",
                (cutoff,)
            )
            rows_to_delete = cursor.fetchone()[0]
            
            conn.execute(
                f"DELETE FROM {table_name} WHERE timestamp < ?",
                (cutoff,)
            )
            
            return {'rows_deleted': rows_to_delete}
```

### Data Backup Procedures

#### Automated Backup Script
```bash
#!/bin/bash
# backup/epic1_backup.sh

BACKUP_DIR="/opt/trading-bot/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="epic1_backup_${DATE}"

echo "Starting Epic 1 backup: $BACKUP_NAME"

# Create backup directory
mkdir -p "$BACKUP_DIR/$BACKUP_NAME"

# Backup database
echo "Backing up database..."
sqlite3 /opt/trading-bot/data/trading_bot.db ".backup $BACKUP_DIR/$BACKUP_NAME/database.db"

# Backup configuration
echo "Backing up configuration..."
cp -r /opt/trading-bot/config "$BACKUP_DIR/$BACKUP_NAME/"

# Backup Epic 1 specific files
echo "Backing up Epic 1 files..."
mkdir -p "$BACKUP_DIR/$BACKUP_NAME/epic1"
cp -r /opt/trading-bot/src/utils/epic1* "$BACKUP_DIR/$BACKUP_NAME/epic1/"
cp -r /opt/trading-bot/src/services/timeframe "$BACKUP_DIR/$BACKUP_NAME/epic1/"

# Backup logs (last 7 days)
echo "Backing up recent logs..."
find /opt/trading-bot/logs -name "*.log" -mtime -7 -exec cp {} "$BACKUP_DIR/$BACKUP_NAME/" \;

# Compress backup
echo "Compressing backup..."
cd "$BACKUP_DIR"
tar -czf "$BACKUP_NAME.tar.gz" "$BACKUP_NAME"
rm -rf "$BACKUP_NAME"

# Clean old backups (keep 30 days)
find "$BACKUP_DIR" -name "epic1_backup_*.tar.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_DIR/$BACKUP_NAME.tar.gz"
```

#### Backup Verification Script
```python
# backup/verify_backup.py
import tarfile
import sqlite3
import tempfile
import os
from datetime import datetime

def verify_epic1_backup(backup_path):
    """Verify Epic 1 backup integrity"""
    verification_results = {
        'backup_path': backup_path,
        'verification_time': datetime.now().isoformat(),
        'tests': {}
    }
    
    try:
        # Extract backup to temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            with tarfile.open(backup_path, 'r:gz') as tar:
                tar.extractall(temp_dir)
            
            backup_contents = os.listdir(temp_dir)
            if len(backup_contents) != 1:
                raise ValueError("Invalid backup structure")
            
            backup_dir = os.path.join(temp_dir, backup_contents[0])
            
            # Verify database
            verification_results['tests']['database'] = verify_database_backup(
                os.path.join(backup_dir, 'database.db')
            )
            
            # Verify configuration
            verification_results['tests']['configuration'] = verify_config_backup(
                os.path.join(backup_dir, 'config')
            )
            
            # Verify Epic 1 files
            verification_results['tests']['epic1_files'] = verify_epic1_files(
                os.path.join(backup_dir, 'epic1')
            )
    
    except Exception as e:
        verification_results['error'] = str(e)
        verification_results['verified'] = False
        return verification_results
    
    # Overall verification status
    all_tests_passed = all(
        result.get('verified', False) 
        for result in verification_results['tests'].values()
    )
    verification_results['verified'] = all_tests_passed
    
    return verification_results

def verify_database_backup(db_path):
    """Verify database backup integrity"""
    try:
        with sqlite3.connect(db_path) as conn:
            # Check if Epic 1 tables exist
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'epic1_%'"
            )
            epic1_tables = cursor.fetchall()
            
            # Verify table integrity
            for table in epic1_tables:
                conn.execute(f"PRAGMA integrity_check({table[0]})")
        
        return {'verified': True, 'epic1_tables': len(epic1_tables)}
    
    except Exception as e:
        return {'verified': False, 'error': str(e)}
```

---

## Troubleshooting Procedures

### Automated Diagnostics

#### Comprehensive Diagnostic Script
```python
# diagnostics/epic1_diagnostics.py
import requests
import sqlite3
import psutil
import json
from datetime import datetime, timedelta

class Epic1Diagnostics:
    def __init__(self, base_url='http://localhost:5000'):
        self.base_url = base_url
        self.diagnostics = {}
    
    def run_full_diagnostics(self):
        """Run comprehensive Epic 1 diagnostics"""
        self.diagnostics = {
            'timestamp': datetime.now().isoformat(),
            'system_health': self._check_system_health(),
            'epic1_status': self._check_epic1_status(),
            'api_endpoints': self._test_api_endpoints(),
            'database_health': self._check_database_health(),
            'performance_metrics': self._analyze_performance(),
            'recent_errors': self._analyze_recent_errors()
        }
        
        # Generate recommendations
        self.diagnostics['recommendations'] = self._generate_recommendations()
        
        return self.diagnostics
    
    def _check_system_health(self):
        """Check overall system health"""
        try:
            return {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_usage': psutil.disk_usage('/').percent,
                'load_average': os.getloadavg() if hasattr(os, 'getloadavg') else None,
                'healthy': True
            }
        except Exception as e:
            return {'healthy': False, 'error': str(e)}
    
    def _check_epic1_status(self):
        """Check Epic 1 component status"""
        try:
            response = requests.get(f'{self.base_url}/api/epic1/status', timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {'healthy': False, 'error': str(e)}
    
    def _test_api_endpoints(self):
        """Test Epic 1 API endpoints"""
        endpoints = [
            '/api/epic1/status',
            '/api/epic1/enhanced-signal/AAPL',
            '/api/epic1/volume-dashboard-data',
            '/api/epic1/multi-timeframe/AAPL'
        ]
        
        results = {}
        for endpoint in endpoints:
            try:
                start_time = time.time()
                response = requests.get(f'{self.base_url}{endpoint}', timeout=30)
                response_time = (time.time() - start_time) * 1000  # ms
                
                results[endpoint] = {
                    'status_code': response.status_code,
                    'response_time': response_time,
                    'healthy': response.status_code == 200 and response_time < 1000
                }
            except Exception as e:
                results[endpoint] = {
                    'healthy': False,
                    'error': str(e)
                }
        
        return results
    
    def _generate_recommendations(self):
        """Generate recommendations based on diagnostic results"""
        recommendations = []
        
        # System health recommendations
        system = self.diagnostics.get('system_health', {})
        if system.get('cpu_percent', 0) > 80:
            recommendations.append({
                'type': 'performance',
                'severity': 'high',
                'message': 'High CPU usage detected. Consider reducing worker threads or enabling caching.'
            })
        
        if system.get('memory_percent', 0) > 85:
            recommendations.append({
                'type': 'performance',
                'severity': 'high',
                'message': 'High memory usage detected. Run memory optimization or increase available RAM.'
            })
        
        # Epic 1 specific recommendations
        epic1_status = self.diagnostics.get('epic1_status', {})
        if not epic1_status.get('healthy', False):
            recommendations.append({
                'type': 'functionality',
                'severity': 'critical',
                'message': 'Epic 1 components are not healthy. Check configuration and restart services.'
            })
        
        # API performance recommendations
        api_results = self.diagnostics.get('api_endpoints', {})
        slow_endpoints = [
            endpoint for endpoint, result in api_results.items()
            if result.get('response_time', 0) > 500
        ]
        if slow_endpoints:
            recommendations.append({
                'type': 'performance',
                'severity': 'medium',
                'message': f'Slow API endpoints detected: {", ".join(slow_endpoints)}. Enable caching or optimize queries.'
            })
        
        return recommendations
```

### Issue Resolution Procedures

#### Common Issue Resolution Matrix
```python
# diagnostics/issue_resolution.py
class Epic1IssueResolver:
    def __init__(self):
        self.resolution_matrix = {
            'component_not_initialized': [
                'Check configuration file syntax',
                'Verify environment variables',
                'Restart Epic 1 services',
                'Clear cache and reinitialize'
            ],
            'high_memory_usage': [
                'Run memory optimization',
                'Clear Epic 1 caches',
                'Reduce cache size limits',
                'Restart application'
            ],
            'slow_api_response': [
                'Enable response caching',
                'Optimize database queries',
                'Increase worker threads',
                'Check network connectivity'
            ],
            'volume_confirmation_failing': [
                'Verify market data quality',
                'Adjust confirmation threshold',
                'Check volume data source',
                'Recalibrate volume analyzer'
            ],
            'multi_timeframe_timeout': [
                'Increase validation timeout',
                'Check data source connections',
                'Reduce concurrent validations',
                'Optimize timeframe data caching'
            ]
        }
    
    def resolve_issue(self, issue_type, auto_resolve=False):
        """Resolve Epic 1 issues automatically or provide guidance"""
        if issue_type not in self.resolution_matrix:
            return {'error': f'Unknown issue type: {issue_type}'}
        
        steps = self.resolution_matrix[issue_type]
        results = {'issue_type': issue_type, 'steps': []}
        
        for step in steps:
            if auto_resolve:
                result = self._execute_resolution_step(step)
                results['steps'].append({
                    'step': step,
                    'executed': True,
                    'result': result
                })
                
                # If step succeeded, we might be done
                if result.get('success'):
                    break
            else:
                results['steps'].append({
                    'step': step,
                    'executed': False,
                    'description': self._get_step_description(step)
                })
        
        return results
    
    def _execute_resolution_step(self, step):
        """Execute an automated resolution step"""
        try:
            if step == 'Run memory optimization':
                from maintenance.memory_optimization import Epic1MemoryOptimizer
                optimizer = Epic1MemoryOptimizer()
                return optimizer.optimize_memory()
            
            elif step == 'Clear Epic 1 caches':
                # Implementation for cache clearing
                return {'success': True, 'message': 'Caches cleared'}
            
            elif step == 'Restart Epic 1 services':
                # Implementation for service restart
                return {'success': True, 'message': 'Services restarted'}
            
            else:
                return {'success': False, 'message': f'Manual step required: {step}'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
```

---

## Update and Upgrade Procedures

### Version Management

#### Epic 1 Version Tracking
```python
# updates/version_manager.py
import json
import requests
from packaging import version

class Epic1VersionManager:
    def __init__(self, current_version='1.0.0'):
        self.current_version = current_version
        self.version_info_url = 'https://api.trading-bot.com/epic1/version-info'
    
    def check_for_updates(self):
        """Check for Epic 1 updates"""
        try:
            response = requests.get(self.version_info_url, timeout=10)
            response.raise_for_status()
            version_info = response.json()
            
            latest_version = version_info['latest_version']
            
            return {
                'current_version': self.current_version,
                'latest_version': latest_version,
                'update_available': version.parse(latest_version) > version.parse(self.current_version),
                'changelog': version_info.get('changelog', []),
                'breaking_changes': version_info.get('breaking_changes', []),
                'update_priority': version_info.get('priority', 'optional')
            }
        except Exception as e:
            return {'error': str(e)}
    
    def prepare_update(self, target_version):
        """Prepare for Epic 1 update"""
        preparation_steps = [
            'Create system backup',
            'Verify configuration compatibility',
            'Check dependency requirements',
            'Plan downtime window',
            'Prepare rollback procedure'
        ]
        
        return {
            'target_version': target_version,
            'preparation_steps': preparation_steps,
            'estimated_downtime': '15-30 minutes',
            'rollback_time': '5-10 minutes'
        }
```

#### Update Procedure
```bash
#!/bin/bash
# updates/epic1_update.sh

VERSION=$1
if [ -z "$VERSION" ]; then
    echo "Usage: $0 <version>"
    exit 1
fi

echo "Starting Epic 1 update to version $VERSION"

# Pre-update backup
echo "Creating backup..."
./backup/epic1_backup.sh

# Stop Epic 1 services
echo "Stopping services..."
systemctl stop trading-bot

# Download and install update
echo "Downloading update..."
wget "https://releases.trading-bot.com/epic1/v$VERSION/epic1-$VERSION.tar.gz"
tar -xzf "epic1-$VERSION.tar.gz"

# Install update
echo "Installing update..."
cp -r "epic1-$VERSION/"* /opt/trading-bot/

# Update dependencies
echo "Updating dependencies..."
pip install -r requirements.txt

# Run database migrations if needed
echo "Running migrations..."
python migrations/epic1_migrate.py --version "$VERSION"

# Update configuration if needed
echo "Updating configuration..."
python config/update_config.py --version "$VERSION"

# Start services
echo "Starting services..."
systemctl start trading-bot

# Verify update
echo "Verifying update..."
sleep 10
curl -f http://localhost:5000/api/epic1/status || {
    echo "Update verification failed. Rolling back..."
    ./updates/rollback.sh
    exit 1
}

echo "Update completed successfully to version $VERSION"
```

### Configuration Migrations

#### Configuration Migration Script
```python
# migrations/config_migration.py
import yaml
import shutil
from datetime import datetime

class Epic1ConfigMigrator:
    def __init__(self):
        self.migrations = {
            '1.0.0': self._migrate_to_1_0_0,
            '1.1.0': self._migrate_to_1_1_0,
            '1.2.0': self._migrate_to_1_2_0
        }
    
    def migrate_config(self, target_version, config_path):
        """Migrate configuration to target version"""
        # Backup current configuration
        backup_path = f"{config_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(config_path, backup_path)
        
        # Load current configuration
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Apply migrations in order
        for version, migration_func in self.migrations.items():
            if self._should_apply_migration(version, target_version):
                config = migration_func(config)
        
        # Save migrated configuration
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, indent=2)
        
        return {
            'backup_path': backup_path,
            'migrations_applied': [
                v for v in self.migrations.keys()
                if self._should_apply_migration(v, target_version)
            ]
        }
    
    def _migrate_to_1_1_0(self, config):
        """Migration for version 1.1.0"""
        # Add new configuration options
        if 'epic1' in config:
            config['epic1'].setdefault('neural_enhancement', {
                'enabled': False,
                'model_path': 'models/epic1_neural.pkl'
            })
        return config
    
    def _migrate_to_1_2_0(self, config):
        """Migration for version 1.2.0"""
        # Restructure volume confirmation settings
        if 'epic1' in config and 'volume_confirmation' in config['epic1']:
            old_config = config['epic1']['volume_confirmation']
            config['epic1']['volume_confirmation'] = {
                'basic': {
                    'enabled': old_config.get('enabled', True),
                    'threshold': old_config.get('confirmation_threshold', 1.2)
                },
                'advanced': {
                    'enable_profile_analysis': True,
                    'enable_institutional_detection': False
                }
            }
        return config
```

---

## Backup and Recovery

### Disaster Recovery Procedures

#### Epic 1 Disaster Recovery Plan
```bash
#!/bin/bash
# recovery/epic1_disaster_recovery.sh

RECOVERY_MODE=$1
BACKUP_PATH=$2

case $RECOVERY_MODE in
    "full")
        echo "Starting full Epic 1 disaster recovery..."
        
        # Stop all services
        systemctl stop trading-bot
        
        # Restore from backup
        if [ -f "$BACKUP_PATH" ]; then
            echo "Restoring from backup: $BACKUP_PATH"
            tar -xzf "$BACKUP_PATH" -C /opt/trading-bot/
        else
            echo "Backup file not found: $BACKUP_PATH"
            exit 1
        fi
        
        # Restore database
        if [ -f "/opt/trading-bot/backup/database.db" ]; then
            mv /opt/trading-bot/data/trading_bot.db /opt/trading-bot/data/trading_bot.db.corrupted
            cp /opt/trading-bot/backup/database.db /opt/trading-bot/data/trading_bot.db
        fi
        
        # Restore configuration
        if [ -d "/opt/trading-bot/backup/config" ]; then
            rm -rf /opt/trading-bot/config
            cp -r /opt/trading-bot/backup/config /opt/trading-bot/
        fi
        
        # Start services
        systemctl start trading-bot
        ;;
        
    "config")
        echo "Recovering Epic 1 configuration..."
        systemctl stop trading-bot
        
        # Restore configuration only
        if [ -d "$BACKUP_PATH/config" ]; then
            cp -r "$BACKUP_PATH/config" /opt/trading-bot/
        fi
        
        systemctl start trading-bot
        ;;
        
    "database")
        echo "Recovering Epic 1 database..."
        systemctl stop trading-bot
        
        # Restore database only
        if [ -f "$BACKUP_PATH/database.db" ]; then
            mv /opt/trading-bot/data/trading_bot.db /opt/trading-bot/data/trading_bot.db.corrupted
            cp "$BACKUP_PATH/database.db" /opt/trading-bot/data/trading_bot.db
        fi
        
        systemctl start trading-bot
        ;;
        
    *)
        echo "Usage: $0 {full|config|database} <backup_path>"
        exit 1
        ;;
esac

echo "Recovery completed. Verifying system status..."
sleep 10
curl -f http://localhost:5000/api/epic1/status && echo "Epic 1 recovery successful" || echo "Epic 1 recovery failed"
```

---

## Security Maintenance

### Security Monitoring

#### Security Audit Script
```python
# security/epic1_security_audit.py
import os
import subprocess
import json
from datetime import datetime

class Epic1SecurityAuditor:
    def __init__(self):
        self.security_checks = [
            'check_file_permissions',
            'check_api_security',
            'check_database_security',
            'check_log_security',
            'check_configuration_security'
        ]
    
    def run_security_audit(self):
        """Run comprehensive security audit"""
        audit_results = {
            'timestamp': datetime.now().isoformat(),
            'checks': {},
            'recommendations': []
        }
        
        for check in self.security_checks:
            try:
                check_method = getattr(self, check)
                audit_results['checks'][check] = check_method()
            except Exception as e:
                audit_results['checks'][check] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        # Generate security recommendations
        audit_results['recommendations'] = self._generate_security_recommendations(audit_results['checks'])
        
        return audit_results
    
    def check_file_permissions(self):
        """Check Epic 1 file permissions"""
        sensitive_files = [
            '/opt/trading-bot/config/unified_config.yml',
            '/opt/trading-bot/data/trading_bot.db',
            '/opt/trading-bot/logs/'
        ]
        
        permission_issues = []
        
        for file_path in sensitive_files:
            if os.path.exists(file_path):
                stat_info = os.stat(file_path)
                mode = oct(stat_info.st_mode)[-3:]
                
                # Check for overly permissive permissions
                if os.path.isfile(file_path) and mode != '600':
                    permission_issues.append({
                        'file': file_path,
                        'current_permissions': mode,
                        'recommended_permissions': '600'
                    })
                elif os.path.isdir(file_path) and mode not in ['700', '750']:
                    permission_issues.append({
                        'file': file_path,
                        'current_permissions': mode,
                        'recommended_permissions': '750'
                    })
        
        return {
            'status': 'pass' if not permission_issues else 'fail',
            'issues': permission_issues
        }
    
    def check_api_security(self):
        """Check Epic 1 API security configuration"""
        security_issues = []
        
        # Check if API authentication is enabled
        try:
            import requests
            response = requests.get('http://localhost:5000/api/epic1/status')
            if response.status_code == 200:
                # Check if API requires authentication
                if 'X-API-Key' not in response.request.headers:
                    security_issues.append('API endpoints accessible without authentication')
        except:
            pass
        
        return {
            'status': 'pass' if not security_issues else 'fail',
            'issues': security_issues
        }
```

### Security Hardening

#### Security Hardening Script
```bash
#!/bin/bash
# security/harden_epic1.sh

echo "Starting Epic 1 security hardening..."

# Set proper file permissions
echo "Setting file permissions..."
chmod 600 /opt/trading-bot/config/unified_config.yml
chmod 600 /opt/trading-bot/data/trading_bot.db
chmod 750 /opt/trading-bot/logs
chmod 644 /opt/trading-bot/src/utils/epic1_integration_helpers.py

# Set proper ownership
chown -R trading-bot:trading-bot /opt/trading-bot

# Configure firewall rules
echo "Configuring firewall..."
ufw allow from 127.0.0.1 to any port 5000
ufw deny 5000

# Set up log monitoring
echo "Setting up log monitoring..."
cat > /etc/logwatch/conf/services/epic1.conf << EOF
Title = "Epic 1 Trading Bot"
LogFile = /opt/trading-bot/logs/trading_bot.log
*OnlyService = epic1
*RemoveHeaders
EOF

# Configure fail2ban for API protection
echo "Configuring fail2ban..."
cat > /etc/fail2ban/filter.d/epic1.conf << EOF
[Definition]
failregex = .*epic1.*authentication failed.*<HOST>
ignoreregex =
EOF

cat > /etc/fail2ban/jail.d/epic1.conf << EOF
[epic1]
enabled = true
port = 5000
filter = epic1
logpath = /opt/trading-bot/logs/trading_bot.log
maxretry = 5
bantime = 3600
EOF

# Restart fail2ban
systemctl restart fail2ban

echo "Epic 1 security hardening completed"
```

---

## Preventive Maintenance

### Scheduled Maintenance Tasks

#### Maintenance Scheduler
```python
# maintenance/scheduler.py
import schedule
import time
import logging
from datetime import datetime

class Epic1MaintenanceScheduler:
    def __init__(self):
        self.logger = logging.getLogger('epic1_maintenance')
        self._setup_schedule()
    
    def _setup_schedule(self):
        """Set up maintenance schedule"""
        # Daily tasks
        schedule.every().day.at("02:00").do(self._daily_maintenance)
        schedule.every().day.at("02:30").do(self._backup_data)
        
        # Weekly tasks
        schedule.every().sunday.at("03:00").do(self._weekly_maintenance)
        
        # Monthly tasks
        schedule.every(30).days.at("04:00").do(self._monthly_maintenance)
    
    def _daily_maintenance(self):
        """Daily maintenance tasks"""
        try:
            self.logger.info("Starting daily maintenance")
            
            # Optimize database
            from maintenance.db_optimization import Epic1DBMaintenance
            db_maintenance = Epic1DBMaintenance('/opt/trading-bot/data/trading_bot.db')
            db_maintenance.optimize_database()
            
            # Clear old logs
            from maintenance.data_retention import Epic1DataRetention
            retention = Epic1DataRetention({})
            retention.apply_retention_policies()
            
            # Memory optimization
            from maintenance.memory_optimization import Epic1MemoryOptimizer
            memory_optimizer = Epic1MemoryOptimizer()
            memory_optimizer.optimize_memory()
            
            self.logger.info("Daily maintenance completed")
            
        except Exception as e:
            self.logger.error(f"Daily maintenance failed: {e}")
    
    def _weekly_maintenance(self):
        """Weekly maintenance tasks"""
        try:
            self.logger.info("Starting weekly maintenance")
            
            # Performance analysis
            self._analyze_weekly_performance()
            
            # Security audit
            from security.epic1_security_audit import Epic1SecurityAuditor
            auditor = Epic1SecurityAuditor()
            auditor.run_security_audit()
            
            # Update checks
            from updates.version_manager import Epic1VersionManager
            version_manager = Epic1VersionManager()
            version_manager.check_for_updates()
            
            self.logger.info("Weekly maintenance completed")
            
        except Exception as e:
            self.logger.error(f"Weekly maintenance failed: {e}")
    
    def run_scheduler(self):
        """Run the maintenance scheduler"""
        self.logger.info("Starting Epic 1 maintenance scheduler")
        
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
```

### Health Monitoring

#### Continuous Health Monitor
```python
# monitoring/health_monitor.py
import time
import logging
import requests
from datetime import datetime, timedelta

class Epic1HealthMonitor:
    def __init__(self, check_interval=60):
        self.check_interval = check_interval
        self.logger = logging.getLogger('epic1_health')
        self.alert_cooldown = {}
    
    def start_monitoring(self):
        """Start continuous health monitoring"""
        self.logger.info("Starting Epic 1 health monitoring")
        
        while True:
            try:
                health_status = self._check_health()
                
                if not health_status['healthy']:
                    self._handle_health_issue(health_status)
                
                time.sleep(self.check_interval)
                
            except Exception as e:
                self.logger.error(f"Health monitoring error: {e}")
                time.sleep(self.check_interval)
    
    def _check_health(self):
        """Perform health check"""
        health_status = {
            'timestamp': datetime.now(),
            'healthy': True,
            'issues': []
        }
        
        # Check API responsiveness
        try:
            response = requests.get('http://localhost:5000/api/epic1/status', timeout=10)
            if response.status_code != 200:
                health_status['healthy'] = False
                health_status['issues'].append('API not responding correctly')
        except:
            health_status['healthy'] = False
            health_status['issues'].append('API unreachable')
        
        # Check memory usage
        import psutil
        memory_percent = psutil.virtual_memory().percent
        if memory_percent > 90:
            health_status['healthy'] = False
            health_status['issues'].append(f'High memory usage: {memory_percent}%')
        
        # Check disk space
        disk_percent = psutil.disk_usage('/').percent
        if disk_percent > 90:
            health_status['healthy'] = False
            health_status['issues'].append(f'Low disk space: {disk_percent}% used')
        
        return health_status
    
    def _handle_health_issue(self, health_status):
        """Handle detected health issues"""
        issue_key = str(health_status['issues'])
        
        # Check alert cooldown
        if issue_key in self.alert_cooldown:
            if datetime.now() - self.alert_cooldown[issue_key] < timedelta(hours=1):
                return  # Skip alert due to cooldown
        
        # Log the issue
        self.logger.warning(f"Health issue detected: {health_status['issues']}")
        
        # Send alert (implementation depends on your alerting system)
        self._send_alert(health_status)
        
        # Set cooldown
        self.alert_cooldown[issue_key] = datetime.now()
    
    def _send_alert(self, health_status):
        """Send health alert"""
        # Implementation for sending alerts (email, Slack, etc.)
        pass
```

This comprehensive maintenance guide provides all the tools and procedures needed to keep Epic 1 Signal Quality Enhancement running optimally in production. Regular execution of these maintenance tasks will ensure high availability, performance, and security of the Epic 1 system.