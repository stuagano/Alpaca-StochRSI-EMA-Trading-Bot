# ADR-001: Database Connection Pooling Implementation

## Status
Proposed

## Context

The current trading bot uses a single database connection per service through psycopg2, leading to several critical issues:

1. **Connection Exhaustion:** Under load, services fail to acquire database connections
2. **Performance Bottlenecks:** Single connection becomes a serialization point
3. **Resource Inefficiency:** Connections are held longer than necessary
4. **Scaling Limitations:** Cannot handle concurrent users effectively

### Current Implementation
```python
class DatabaseManager:
    def __init__(self, db_url='postgresql://...'):
        self.conn = psycopg2.connect(self.db_url)  # Single connection
```

### Observed Issues
- Connection timeouts during market volatility (high trading volume)
- Database lock contention
- Poor performance with multiple concurrent API requests

## Decision

We will implement database connection pooling using SQLAlchemy with the following configuration:

### Technical Approach
1. Replace psycopg2 direct connections with SQLAlchemy Engine
2. Configure connection pool with appropriate sizing
3. Implement context managers for proper connection lifecycle
4. Add connection monitoring and health checks

### Configuration Parameters
```python
@dataclass
class DatabaseConfig:
    url: str = "sqlite:///database/trading_data.db"
    pool_size: int = 20          # Base pool size
    max_overflow: int = 50       # Additional connections when needed
    pool_timeout: int = 30       # Timeout waiting for connection
    pool_recycle: int = 3600     # Recycle connections hourly
    pool_pre_ping: bool = True   # Verify connections before use
    echo: bool = False           # SQL logging for debugging
```

### Implementation Strategy
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager

class DatabaseManager:
    def __init__(self, config: DatabaseConfig):
        self.engine = create_engine(
            config.url,
            pool_size=config.pool_size,
            max_overflow=config.max_overflow,
            pool_timeout=config.pool_timeout,
            pool_recycle=config.pool_recycle,
            pool_pre_ping=config.pool_pre_ping,
            echo=config.echo
        )
        self.session_factory = sessionmaker(bind=self.engine)
    
    @contextmanager
    def get_session(self):
        """Context manager for database sessions"""
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def health_check(self) -> bool:
        """Check database connectivity and pool status"""
        try:
            with self.get_session() as session:
                session.execute("SELECT 1")
            return True
        except Exception:
            return False
    
    def get_pool_status(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        pool = self.engine.pool
        return {
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "invalid": pool.invalid()
        }
```

## Consequences

### Positive
1. **Improved Concurrency:** Support for 20-70 concurrent database operations
2. **Better Resource Management:** Automatic connection lifecycle management
3. **Enhanced Reliability:** Connection health monitoring and automatic recovery
4. **Performance Optimization:** Connection reuse reduces overhead
5. **Monitoring Capability:** Pool statistics for operational visibility

### Negative
1. **Increased Memory Usage:** Connection pool consumes more memory
2. **Configuration Complexity:** More parameters to tune and monitor
3. **Migration Effort:** All database access code needs updating
4. **Debugging Complexity:** Additional layer between application and database

### Migration Impact
- **Breaking Changes:** All direct database access must be updated
- **Testing Requirements:** Extensive testing of concurrent scenarios
- **Rollback Strategy:** Ability to revert to single connection if issues arise

## Implementation Plan

### Phase 1: Foundation (1-2 days)
1. Update DatabaseConfig dataclass
2. Implement new DatabaseManager class
3. Add connection pool monitoring

### Phase 2: Migration (2-3 days)
1. Update UnifiedDataManager to use connection pool
2. Update all service classes using database
3. Update API endpoints for proper session management

### Phase 3: Testing & Monitoring (1 day)
1. Load testing with concurrent requests
2. Monitor pool utilization patterns
3. Tune pool parameters based on usage

### Files to Modify
- `database/database_manager.py` (complete rewrite)
- `services/unified_data_manager.py` (update database calls)
- `config/unified_config.py` (add pool configuration)
- `core/service_registry.py` (update database service registration)

## Alternatives Considered

### Alternative 1: Keep psycopg2 with manual pooling
- **Pros:** Minimal code changes, familiar technology
- **Cons:** More complex to implement correctly, error-prone

### Alternative 2: Use asyncpg for async operations
- **Pros:** Better performance for I/O bound operations
- **Cons:** Requires converting entire application to async

### Alternative 3: Implement custom connection pool
- **Pros:** Full control over behavior
- **Cons:** Significant development time, potential bugs

## Monitoring & Success Criteria

### Key Metrics
1. **Connection Pool Utilization:** Target 60-80% under normal load
2. **Query Response Time:** Improvement of 30-50% for concurrent operations
3. **Connection Errors:** Reduction to < 0.1% of requests
4. **System Stability:** Zero connection exhaustion events

### Monitoring Implementation
```python
from prometheus_client import Gauge, Histogram

# Connection pool metrics
pool_connections_total = Gauge('db_pool_connections_total', 'Total pool connections')
pool_connections_active = Gauge('db_pool_connections_active', 'Active pool connections')
db_query_duration = Histogram('db_query_duration_seconds', 'Database query duration')

def update_pool_metrics(self):
    status = self.get_pool_status()
    pool_connections_total.set(status['size'] + status['overflow'])
    pool_connections_active.set(status['checked_out'])
```

### Testing Strategy
1. **Unit Tests:** Connection acquisition/release cycles
2. **Integration Tests:** Concurrent database operations
3. **Load Tests:** Simulate high-traffic scenarios
4. **Chaos Tests:** Database connection failures and recovery

## Risks & Mitigation

### Risk 1: Connection Pool Exhaustion
- **Mitigation:** Monitoring and alerting on pool utilization
- **Fallback:** Automatic pool size adjustment

### Risk 2: Memory Usage Growth
- **Mitigation:** Connection recycling and monitoring
- **Fallback:** Pool size reduction if memory constraints

### Risk 3: Migration Bugs
- **Mitigation:** Extensive testing and gradual rollout
- **Fallback:** Ability to revert to single connection

## References

- [SQLAlchemy Connection Pooling Documentation](https://docs.sqlalchemy.org/en/14/core/pooling.html)
- [PostgreSQL Connection Best Practices](https://wiki.postgresql.org/wiki/Number_Of_Database_Connections)
- [Database Connection Pool Sizing](https://github.com/brettwooldridge/HikariCP/wiki/About-Pool-Sizing)

---

**Decision Date:** 2025-08-21  
**Status:** Proposed  
**Stakeholders:** Development Team, Operations Team  
**Next Review:** After implementation completion