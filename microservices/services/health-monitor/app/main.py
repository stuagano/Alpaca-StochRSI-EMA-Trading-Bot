#!/usr/bin/env python3
"""
Health Monitor Service

Monitors the health and performance of all microservices in the trading system.
Provides centralized health checking, alerting, and performance metrics.

Features:
- Service health monitoring
- Performance metrics collection
- Alert generation
- Dashboard data aggregation
- Service dependency tracking
- Health trend analysis
"""

import os
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, HTTPException, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import redis.asyncio as redis
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
import json

# Import shared database components
import sys
sys.path.append('/app')
from shared.database import get_db_session, init_database

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://trading_user:trading_pass@postgres:5432/trading_db")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
SERVICES_TO_MONITOR = os.getenv("SERVICES_TO_MONITOR", "").split(",")

# Parse services configuration
MONITORED_SERVICES = {}
for service_config in SERVICES_TO_MONITOR:
    if ":" in service_config:
        name, port = service_config.strip().split(":")
        MONITORED_SERVICES[name] = f"http://{name}:{port}"

# Redis client
redis_client = None

# Data Models
class ServiceHealth(BaseModel):
    service_name: str
    status: str  # healthy, unhealthy, unknown
    response_time_ms: Optional[float] = None
    last_check: str
    error_message: Optional[str] = None
    consecutive_failures: int = 0

class SystemHealth(BaseModel):
    overall_status: str
    healthy_services: int
    total_services: int
    timestamp: str
    services: Dict[str, ServiceHealth]

class HealthMetrics(BaseModel):
    service_name: str
    timestamp: str
    response_time_ms: float
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None
    error_rate: Optional[float] = None

class AlertRule(BaseModel):
    service_name: str
    metric_type: str  # response_time, error_rate, consecutive_failures
    threshold: float
    severity: str  # low, medium, high, critical
    enabled: bool = True

class Alert(BaseModel):
    id: str
    service_name: str
    alert_type: str
    severity: str
    message: str
    timestamp: str
    acknowledged: bool = False

# Health Monitor Service
class HealthMonitorService:
    """Core health monitoring service."""
    
    def __init__(self):
        self.health_cache = {}
        self.metrics_history = {}
        self.alert_rules = self._get_default_alert_rules()
        self.active_alerts = {}
        self.check_interval = 30  # seconds
        
    async def start_monitoring(self):
        """Start the health monitoring background task."""
        asyncio.create_task(self._monitoring_loop())
        logger.info("Health monitoring started", interval=self.check_interval)
    
    async def check_service_health(self, service_name: str, service_url: str) -> ServiceHealth:
        """Check health of a specific service."""
        start_time = datetime.utcnow()
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{service_url}/health")
                
                end_time = datetime.utcnow()
                response_time = (end_time - start_time).total_seconds() * 1000
                
                if response.status_code == 200:
                    status_text = "healthy"
                    error_message = None
                    
                    # Reset consecutive failures
                    if service_name in self.health_cache:
                        self.health_cache[service_name]["consecutive_failures"] = 0
                else:
                    status_text = "unhealthy"
                    error_message = f"HTTP {response.status_code}"
                    
                    # Increment consecutive failures
                    if service_name in self.health_cache:
                        self.health_cache[service_name]["consecutive_failures"] += 1
                    else:
                        self.health_cache[service_name] = {"consecutive_failures": 1}
                
                health = ServiceHealth(
                    service_name=service_name,
                    status=status_text,
                    response_time_ms=response_time,
                    last_check=datetime.utcnow().isoformat(),
                    error_message=error_message,
                    consecutive_failures=self.health_cache.get(service_name, {}).get("consecutive_failures", 0)
                )
                
                # Store health data
                self.health_cache[service_name] = health.dict()
                
                # Store metrics
                await self._store_metrics(service_name, response_time)
                
                # Check alerts
                await self._check_alerts(health)
                
                return health
                
        except Exception as e:
            error_message = str(e)
            
            # Increment consecutive failures
            if service_name in self.health_cache:
                self.health_cache[service_name]["consecutive_failures"] += 1
            else:
                self.health_cache[service_name] = {"consecutive_failures": 1}
            
            health = ServiceHealth(
                service_name=service_name,
                status="unhealthy",
                response_time_ms=None,
                last_check=datetime.utcnow().isoformat(),
                error_message=error_message,
                consecutive_failures=self.health_cache.get(service_name, {}).get("consecutive_failures", 0)
            )
            
            self.health_cache[service_name] = health.dict()
            
            # Check alerts
            await self._check_alerts(health)
            
            return health
    
    async def get_system_health(self) -> SystemHealth:
        """Get overall system health status."""
        try:
            services = {}
            healthy_count = 0
            
            for service_name in MONITORED_SERVICES:
                if service_name in self.health_cache:
                    health_data = self.health_cache[service_name]
                    services[service_name] = ServiceHealth(**health_data)
                    
                    if health_data["status"] == "healthy":
                        healthy_count += 1
                else:
                    # Service not checked yet
                    services[service_name] = ServiceHealth(
                        service_name=service_name,
                        status="unknown",
                        last_check=datetime.utcnow().isoformat()
                    )
            
            total_services = len(MONITORED_SERVICES)
            
            # Determine overall status
            if healthy_count == total_services:
                overall_status = "healthy"
            elif healthy_count > total_services * 0.5:
                overall_status = "degraded"
            else:
                overall_status = "unhealthy"
            
            return SystemHealth(
                overall_status=overall_status,
                healthy_services=healthy_count,
                total_services=total_services,
                timestamp=datetime.utcnow().isoformat(),
                services=services
            )
            
        except Exception as e:
            logger.error("Error getting system health", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get system health"
            )
    
    async def get_service_metrics(self, 
                                service_name: str, 
                                hours: int = 24) -> List[HealthMetrics]:
        """Get metrics history for a service."""
        try:
            if redis_client:
                # Get metrics from Redis
                start_time = datetime.utcnow() - timedelta(hours=hours)
                metrics_key = f"metrics:{service_name}"
                
                # In a real implementation, we'd query time-series data
                # For now, return sample data
                metrics = []
                current_time = start_time
                
                while current_time <= datetime.utcnow():
                    metrics.append(HealthMetrics(
                        service_name=service_name,
                        timestamp=current_time.isoformat(),
                        response_time_ms=50.0 + (hash(str(current_time)) % 100),
                        cpu_usage=20.0 + (hash(str(current_time)) % 30),
                        memory_usage=40.0 + (hash(str(current_time)) % 20),
                        error_rate=0.0
                    ))
                    current_time += timedelta(minutes=5)
                
                return metrics[-288:]  # Last 24 hours in 5-minute intervals
            
            return []
            
        except Exception as e:
            logger.error("Error getting service metrics", service=service_name, error=str(e))
            return []
    
    async def get_active_alerts(self, severity: Optional[str] = None) -> List[Alert]:
        """Get active alerts."""
        try:
            alerts = list(self.active_alerts.values())
            
            if severity:
                alerts = [alert for alert in alerts if alert.severity == severity]
            
            # Sort by timestamp (newest first)
            alerts.sort(key=lambda x: x.timestamp, reverse=True)
            
            return alerts
            
        except Exception as e:
            logger.error("Error getting active alerts", error=str(e))
            return []
    
    async def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert."""
        try:
            if alert_id in self.active_alerts:
                self.active_alerts[alert_id].acknowledged = True
                
                # Store acknowledgment in Redis
                if redis_client:
                    alert_key = f"alert:ack:{alert_id}"
                    await redis_client.setex(alert_key, 86400, "true")  # 24 hours
                
                logger.info("Alert acknowledged", alert_id=alert_id)
                return True
            
            return False
            
        except Exception as e:
            logger.error("Error acknowledging alert", alert_id=alert_id, error=str(e))
            return False
    
    # Background monitoring
    async def _monitoring_loop(self):
        """Continuous monitoring loop."""
        while True:
            try:
                logger.debug("Running health checks", services=len(MONITORED_SERVICES))
                
                # Check all services concurrently
                tasks = []
                for service_name, service_url in MONITORED_SERVICES.items():
                    task = self.check_service_health(service_name, service_url)
                    tasks.append(task)
                
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
                
                # Clean up old alerts
                await self._cleanup_old_alerts()
                
                # Wait for next check
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error("Error in monitoring loop", error=str(e))
                await asyncio.sleep(30)  # Wait longer on error
    
    async def _store_metrics(self, service_name: str, response_time: float):
        """Store service metrics."""
        try:
            if redis_client:
                metrics_data = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "response_time_ms": response_time,
                    "service_name": service_name
                }
                
                # Store in Redis with expiration
                metrics_key = f"metrics:{service_name}:{int(datetime.utcnow().timestamp())}"
                await redis_client.setex(
                    metrics_key, 
                    86400 * 7,  # 7 days
                    json.dumps(metrics_data)
                )
                
        except Exception as e:
            logger.error("Error storing metrics", error=str(e))
    
    async def _check_alerts(self, health: ServiceHealth):
        """Check if any alert rules are triggered."""
        try:
            service_rules = [rule for rule in self.alert_rules if rule.service_name == health.service_name]
            
            for rule in service_rules:
                if not rule.enabled:
                    continue
                
                triggered = False
                alert_message = ""
                
                if rule.metric_type == "response_time" and health.response_time_ms:
                    if health.response_time_ms > rule.threshold:
                        triggered = True
                        alert_message = f"High response time: {health.response_time_ms:.1f}ms (threshold: {rule.threshold}ms)"
                
                elif rule.metric_type == "consecutive_failures":
                    if health.consecutive_failures >= rule.threshold:
                        triggered = True
                        alert_message = f"Service has failed {health.consecutive_failures} consecutive times"
                
                elif rule.metric_type == "service_down":
                    if health.status == "unhealthy":
                        triggered = True
                        alert_message = f"Service is unhealthy: {health.error_message}"
                
                if triggered:
                    await self._create_alert(
                        service_name=health.service_name,
                        alert_type=rule.metric_type,
                        severity=rule.severity,
                        message=alert_message
                    )
            
        except Exception as e:
            logger.error("Error checking alerts", error=str(e))
    
    async def _create_alert(self, 
                          service_name: str, 
                          alert_type: str, 
                          severity: str, 
                          message: str):
        """Create a new alert."""
        try:
            alert_id = f"{service_name}_{alert_type}_{int(datetime.utcnow().timestamp())}"
            
            # Check if similar alert already exists
            existing_key = f"{service_name}_{alert_type}"
            if existing_key in self.active_alerts:
                return  # Don't create duplicate alerts
            
            alert = Alert(
                id=alert_id,
                service_name=service_name,
                alert_type=alert_type,
                severity=severity,
                message=message,
                timestamp=datetime.utcnow().isoformat()
            )
            
            self.active_alerts[existing_key] = alert
            
            # Store in Redis
            if redis_client:
                alert_key = f"alert:{alert_id}"
                await redis_client.setex(
                    alert_key, 
                    86400,  # 24 hours
                    json.dumps(alert.dict())
                )
            
            logger.warning("Alert created", 
                         service=service_name, 
                         type=alert_type, 
                         severity=severity,
                         message=message)
            
        except Exception as e:
            logger.error("Error creating alert", error=str(e))
    
    async def _cleanup_old_alerts(self):
        """Clean up old alerts."""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            
            alerts_to_remove = []
            for key, alert in self.active_alerts.items():
                alert_time = datetime.fromisoformat(alert.timestamp.replace('Z', '+00:00'))
                if alert_time < cutoff_time:
                    alerts_to_remove.append(key)
            
            for key in alerts_to_remove:
                del self.active_alerts[key]
            
            if alerts_to_remove:
                logger.info("Cleaned up old alerts", count=len(alerts_to_remove))
            
        except Exception as e:
            logger.error("Error cleaning up alerts", error=str(e))
    
    def _get_default_alert_rules(self) -> List[AlertRule]:
        """Get default alert rules."""
        return [
            AlertRule(
                service_name="*",  # All services
                metric_type="response_time",
                threshold=5000.0,  # 5 seconds
                severity="high"
            ),
            AlertRule(
                service_name="*",
                metric_type="consecutive_failures", 
                threshold=3.0,
                severity="critical"
            ),
            AlertRule(
                service_name="*",
                metric_type="service_down",
                threshold=1.0,
                severity="critical"
            )
        ]

# Global service instance
health_monitor = HealthMonitorService()

# Application lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global redis_client
    
    try:
        # Initialize Redis connection
        redis_client = redis.from_url(REDIS_URL)
        await redis_client.ping()
        
        # Initialize database tables
        await init_database()
        
        # Start health monitoring
        await health_monitor.start_monitoring()
        
        logger.info("✅ Health Monitor Service started successfully", 
                   monitored_services=list(MONITORED_SERVICES.keys()))
        yield
    except Exception as e:
        logger.error("❌ Failed to start Health Monitor Service", error=str(e))
        yield
    finally:
        if redis_client:
            await redis_client.close()
        logger.info("🔌 Health Monitor Service shutdown complete")

# FastAPI application
app = FastAPI(
    title="Health Monitor Service",
    description="System health monitoring and alerting",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routes

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    redis_connected = False
    if redis_client:
        try:
            await redis_client.ping()
            redis_connected = True
        except:
            pass
    
    return {
        "service": "health-monitor",
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "redis_connected": redis_connected,
        "monitored_services": list(MONITORED_SERVICES.keys())
    }

@app.get("/system/health", response_model=SystemHealth)
async def get_system_health():
    """Get overall system health."""
    return await health_monitor.get_system_health()

@app.get("/services/{service_name}/health", response_model=ServiceHealth)
async def get_service_health(service_name: str):
    """Get health status for a specific service."""
    if service_name not in MONITORED_SERVICES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service {service_name} is not monitored"
        )
    
    service_url = MONITORED_SERVICES[service_name]
    return await health_monitor.check_service_health(service_name, service_url)

@app.get("/services/{service_name}/metrics", response_model=List[HealthMetrics])
async def get_service_metrics(service_name: str, hours: int = 24):
    """Get metrics history for a service."""
    return await health_monitor.get_service_metrics(service_name, hours)

@app.get("/alerts", response_model=List[Alert])
async def get_alerts(severity: Optional[str] = None):
    """Get active alerts."""
    return await health_monitor.get_active_alerts(severity)

@app.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str):
    """Acknowledge an alert."""
    success = await health_monitor.acknowledge_alert(alert_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    return {"message": "Alert acknowledged successfully"}

@app.get("/services")
async def get_monitored_services():
    """Get list of monitored services."""
    return {
        "services": list(MONITORED_SERVICES.keys()),
        "total": len(MONITORED_SERVICES)
    }

@app.post("/services/{service_name}/check")
async def manual_health_check(service_name: str):
    """Manually trigger health check for a service."""
    if service_name not in MONITORED_SERVICES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service {service_name} is not monitored"
        )
    
    service_url = MONITORED_SERVICES[service_name]
    health = await health_monitor.check_service_health(service_name, service_url)
    
    return {
        "message": "Health check completed",
        "health": health
    }

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8010,
        reload=True
    )