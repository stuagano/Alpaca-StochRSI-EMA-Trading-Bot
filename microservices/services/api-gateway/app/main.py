#!/usr/bin/env python3
"""
API Gateway Service

Central entry point for the microservices architecture. Provides:
- Request routing to appropriate services
- Authentication and authorization
- Rate limiting and circuit breaker patterns
- Request/response logging
- Service discovery integration
"""

import os
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
from pydantic import BaseModel

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

# Service configuration - Updated for localhost services
SERVICES = {
    "position-management": os.getenv("POSITION_SERVICE_URL", "http://localhost:9001"),
    "trading-execution": os.getenv("TRADING_SERVICE_URL", "http://localhost:9002"),
    "signal-processing": os.getenv("SIGNAL_SERVICE_URL", "http://localhost:9003"),
    "risk-management": os.getenv("RISK_SERVICE_URL", "http://localhost:9004"),
    "market-data": os.getenv("MARKET_DATA_SERVICE_URL", "http://localhost:9005"),
    "historical-data": os.getenv("HISTORICAL_DATA_SERVICE_URL", "http://localhost:9006"),
    "analytics": os.getenv("ANALYTICS_SERVICE_URL", "http://localhost:9007"),
    "training": os.getenv("TRAINING_SERVICE_URL", "http://localhost:9011"),
    "notification": os.getenv("NOTIFICATION_SERVICE_URL", "http://notification:9008"),
    "configuration": os.getenv("CONFIGURATION_SERVICE_URL", "http://configuration:9009"),
    "health-monitor": os.getenv("HEALTH_MONITOR_SERVICE_URL", "http://health-monitor:9010"),
}

# Circuit breaker configuration
class CircuitBreakerStatus:
    def __init__(self):
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
        self.failure_threshold = 5
        self.timeout = 60  # seconds

# Circuit breakers for each service
circuit_breakers = {service: CircuitBreakerStatus() for service in SERVICES}

# Rate limiting
class RateLimiter:
    def __init__(self):
        self.requests = {}
        self.window_size = 60  # 1 minute
        self.max_requests = 100  # requests per minute

    def is_allowed(self, client_ip: str) -> bool:
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=self.window_size)
        
        if client_ip not in self.requests:
            self.requests[client_ip] = []
        
        # Clean old requests
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip]
            if req_time > window_start
        ]
        
        # Check if under limit
        if len(self.requests[client_ip]) >= self.max_requests:
            return False
        
        # Add current request
        self.requests[client_ip].append(now)
        return True

rate_limiter = RateLimiter()

# Request/Response models
class ServiceHealth(BaseModel):
    service: str
    status: str
    response_time_ms: Optional[float] = None
    last_check: str

class GatewayStatus(BaseModel):
    gateway: str
    status: str
    timestamp: str
    services: Dict[str, ServiceHealth]
    total_services: int
    healthy_services: int

# Proxy service
class ProxyService:
    """Handles service routing and communication."""
    
    def __init__(self):
        self.client = None
    
    async def initialize(self):
        """Initialize HTTP client."""
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        """Close HTTP client."""
        if self.client:
            await self.client.aclose()
    
    async def forward_request(self, 
                            service_name: str, 
                            path: str, 
                            method: str,
                            params: Dict = None,
                            json_data: Dict = None,
                            headers: Dict = None) -> httpx.Response:
        """Forward request to target service with circuit breaker."""
        
        if service_name not in SERVICES:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Service {service_name} not found"
            )
        
        circuit_breaker = circuit_breakers[service_name]
        
        # Check circuit breaker
        if not self._is_circuit_closed(circuit_breaker):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Service {service_name} is currently unavailable"
            )
        
        service_url = SERVICES[service_name]
        full_url = f"{service_url}{path}"
        
        try:
            logger.info("Forwarding request", 
                       service=service_name, url=full_url, method=method)
            
            start_time = datetime.utcnow()
            
            response = await self.client.request(
                method=method,
                url=full_url,
                params=params,
                json=json_data,
                headers=headers
            )
            
            end_time = datetime.utcnow()
            response_time = (end_time - start_time).total_seconds() * 1000
            
            logger.info("Request completed", 
                       service=service_name, 
                       status_code=response.status_code,
                       response_time_ms=response_time)
            
            # Reset circuit breaker on success
            if response.status_code < 500:
                self._reset_circuit_breaker(circuit_breaker)
            else:
                self._record_failure(circuit_breaker)
            
            return response
            
        except Exception as e:
            logger.error("Request failed", 
                        service=service_name, error=str(e))
            self._record_failure(circuit_breaker)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Service {service_name} request failed: {str(e)}"
            )
    
    def _is_circuit_closed(self, circuit_breaker: CircuitBreakerStatus) -> bool:
        """Check if circuit breaker allows requests."""
        if circuit_breaker.state == "closed":
            return True
        
        if circuit_breaker.state == "open":
            # Check if timeout has passed
            if (circuit_breaker.last_failure_time and 
                datetime.utcnow() - circuit_breaker.last_failure_time > timedelta(seconds=circuit_breaker.timeout)):
                circuit_breaker.state = "half-open"
                return True
            return False
        
        # half-open state - allow one request
        return True
    
    def _record_failure(self, circuit_breaker: CircuitBreakerStatus):
        """Record a failure and potentially open circuit."""
        circuit_breaker.failure_count += 1
        circuit_breaker.last_failure_time = datetime.utcnow()
        
        if circuit_breaker.failure_count >= circuit_breaker.failure_threshold:
            circuit_breaker.state = "open"
            logger.warning("Circuit breaker opened", 
                          failure_count=circuit_breaker.failure_count)
    
    def _reset_circuit_breaker(self, circuit_breaker: CircuitBreakerStatus):
        """Reset circuit breaker on successful request."""
        circuit_breaker.failure_count = 0
        circuit_breaker.state = "closed"
        circuit_breaker.last_failure_time = None
    
    async def check_service_health(self, service_name: str) -> ServiceHealth:
        """Check health of a specific service."""
        if service_name not in SERVICES:
            return ServiceHealth(
                service=service_name,
                status="unknown",
                last_check=datetime.utcnow().isoformat()
            )
        
        try:
            start_time = datetime.utcnow()
            
            response = await self.client.get(
                f"{SERVICES[service_name]}/health",
                timeout=5.0
            )
            
            end_time = datetime.utcnow()
            response_time = (end_time - start_time).total_seconds() * 1000
            
            status_text = "healthy" if response.status_code == 200 else "unhealthy"
            
            return ServiceHealth(
                service=service_name,
                status=status_text,
                response_time_ms=response_time,
                last_check=datetime.utcnow().isoformat()
            )
            
        except Exception as e:
            logger.error("Health check failed", service=service_name, error=str(e))
            return ServiceHealth(
                service=service_name,
                status="error",
                last_check=datetime.utcnow().isoformat()
            )

# Global proxy service
proxy_service = ProxyService()

# Rate limiting dependency
async def check_rate_limit(request: Request):
    """Check rate limiting for requests."""
    client_ip = request.client.host
    
    if not rate_limiter.is_allowed(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded"
        )

# Application lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    try:
        # Initialize proxy service
        await proxy_service.initialize()
        logger.info("✅ API Gateway started successfully")
        
        yield
        
    except Exception as e:
        logger.error("❌ Failed to start API Gateway", error=str(e))
        yield
    finally:
        # Cleanup
        await proxy_service.close()
        logger.info("🔌 API Gateway shutdown complete")

# FastAPI application
app = FastAPI(
    title="API Gateway",
    description="Central entry point for trading system microservices",
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

# Health check endpoint
@app.get("/health", response_model=GatewayStatus)
async def health_check():
    """Gateway health check with service status."""
    
    # Check all services
    service_checks = []
    for service_name in SERVICES:
        health = await proxy_service.check_service_health(service_name)
        service_checks.append(health)
    
    # Calculate overall health
    healthy_count = sum(1 for health in service_checks if health.status == "healthy")
    total_count = len(service_checks)
    
    # Build service status dict
    services = {health.service: health for health in service_checks}
    
    return GatewayStatus(
        gateway="api-gateway",
        status="healthy" if healthy_count > total_count / 2 else "degraded",
        timestamp=datetime.utcnow().isoformat(),
        services=services,
        total_services=total_count,
        healthy_services=healthy_count
    )

# Service routing endpoints

# Position Management routes
@app.api_route("/api/positions/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def route_positions(request: Request, path: str, _: None = Depends(check_rate_limit)):
    """Route position management requests."""
    body = None
    if request.method in ["POST", "PUT", "PATCH"]:
        body = await request.json() if await request.body() else None
    
    response = await proxy_service.forward_request(
        service_name="position-management",
        path=f"/{path}",
        method=request.method,
        params=dict(request.query_params),
        json_data=body,
        headers=dict(request.headers)
    )
    
    return JSONResponse(content=response.json(), status_code=response.status_code)

@app.api_route("/api/portfolio/{path:path}", methods=["GET"])
async def route_portfolio(request: Request, path: str, _: None = Depends(check_rate_limit)):
    """Route portfolio requests."""
    response = await proxy_service.forward_request(
        service_name="position-management",
        path=f"/portfolio/{path}",
        method=request.method,
        params=dict(request.query_params)
    )
    
    return JSONResponse(content=response.json(), status_code=response.status_code)

# Trading Execution routes
@app.api_route("/api/orders/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def route_orders(request: Request, path: str, _: None = Depends(check_rate_limit)):
    """Route trading execution requests."""
    body = None
    if request.method in ["POST", "PUT", "PATCH"]:
        body = await request.json() if await request.body() else None
    
    response = await proxy_service.forward_request(
        service_name="trading-execution",
        path=f"/orders/{path}" if path else "/orders",
        method=request.method,
        params=dict(request.query_params),
        json_data=body
    )
    
    return JSONResponse(content=response.json(), status_code=response.status_code)

@app.post("/api/execute/signal")
async def route_execute_signal(request: Request, _: None = Depends(check_rate_limit)):
    """Route signal execution requests."""
    body = await request.json()
    
    response = await proxy_service.forward_request(
        service_name="trading-execution",
        path="/execute/signal",
        method="POST",
        json_data=body
    )
    
    return JSONResponse(content=response.json(), status_code=response.status_code)

@app.get("/api/account")
async def route_account(request: Request, _: None = Depends(check_rate_limit)):
    """Route account information requests."""
    response = await proxy_service.forward_request(
        service_name="trading-execution",
        path="/account",
        method="GET"
    )
    
    return JSONResponse(content=response.json(), status_code=response.status_code)

# Market Data routes
@app.api_route("/api/market/{path:path}", methods=["GET", "POST"])
async def route_market_data(request: Request, path: str, _: None = Depends(check_rate_limit)):
    """Route market data requests."""
    body = None
    if request.method in ["POST"]:
        body = await request.json() if await request.body() else None
    
    response = await proxy_service.forward_request(
        service_name="market-data",
        path=f"/{path}",
        method=request.method,
        params=dict(request.query_params),
        json_data=body
    )
    
    return JSONResponse(content=response.json(), status_code=response.status_code)

# Risk Management routes
@app.api_route("/api/risk/{path:path}", methods=["GET", "POST"])
async def route_risk_management(request: Request, path: str, _: None = Depends(check_rate_limit)):
    """Route risk management requests."""
    body = None
    if request.method in ["POST"]:
        body = await request.json() if await request.body() else None
    
    response = await proxy_service.forward_request(
        service_name="risk-management",
        path=f"/{path}",
        method=request.method,
        params=dict(request.query_params),
        json_data=body
    )
    
    return JSONResponse(content=response.json(), status_code=response.status_code)

# Signal Processing routes
@app.api_route("/api/signals/{path:path}", methods=["GET", "POST"])
async def route_signals(request: Request, path: str, _: None = Depends(check_rate_limit)):
    """Route signal processing requests."""
    body = None
    if request.method in ["POST"]:
        body = await request.json() if await request.body() else None
    
    response = await proxy_service.forward_request(
        service_name="signal-processing",
        path=f"/{path}",
        method=request.method,
        params=dict(request.query_params),
        json_data=body
    )
    
    return JSONResponse(content=response.json(), status_code=response.status_code)

# Analytics routes
@app.api_route("/api/analytics/{path:path}", methods=["GET", "POST"])
async def route_analytics(request: Request, path: str, _: None = Depends(check_rate_limit)):
    """Route analytics requests."""
    body = None
    if request.method in ["POST"]:
        body = await request.json() if await request.body() else None
    
    response = await proxy_service.forward_request(
        service_name="analytics",
        path=f"/analytics/{path}",
        method=request.method,
        params=dict(request.query_params),
        json_data=body
    )
    
    return JSONResponse(content=response.json(), status_code=response.status_code)

# Historical Data routes
@app.api_route("/api/historical/{path:path}", methods=["GET", "POST"])
async def route_historical_data(request: Request, path: str, _: None = Depends(check_rate_limit)):
    """Route historical data requests."""
    body = None
    if request.method in ["POST"]:
        body = await request.json() if await request.body() else None
    
    response = await proxy_service.forward_request(
        service_name="historical-data",
        path=f"/{path}",
        method=request.method,
        params=dict(request.query_params),
        json_data=body
    )
    
    return JSONResponse(content=response.json(), status_code=response.status_code)

# Notification routes
@app.api_route("/api/notifications/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def route_notifications(request: Request, path: str, _: None = Depends(check_rate_limit)):
    """Route notification requests."""
    body = None
    if request.method in ["POST", "PUT", "PATCH"]:
        body = await request.json() if await request.body() else None
    
    response = await proxy_service.forward_request(
        service_name="notification",
        path=f"/{path}",
        method=request.method,
        params=dict(request.query_params),
        json_data=body
    )
    
    return JSONResponse(content=response.json(), status_code=response.status_code)

# Configuration routes
@app.api_route("/api/config/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def route_configuration(request: Request, path: str, _: None = Depends(check_rate_limit)):
    """Route configuration requests."""
    body = None
    if request.method in ["POST", "PUT", "PATCH"]:
        body = await request.json() if await request.body() else None
    
    response = await proxy_service.forward_request(
        service_name="configuration",
        path=f"/{path}",
        method=request.method,
        params=dict(request.query_params),
        json_data=body
    )
    
    return JSONResponse(content=response.json(), status_code=response.status_code)

# Health Monitor routes
@app.api_route("/api/monitoring/{path:path}", methods=["GET", "POST"])
async def route_health_monitor(request: Request, path: str, _: None = Depends(check_rate_limit)):
    """Route health monitoring requests."""
    body = None
    if request.method in ["POST"]:
        body = await request.json() if await request.body() else None
    
    response = await proxy_service.forward_request(
        service_name="health-monitor",
        path=f"/{path}",
        method=request.method,
        params=dict(request.query_params),
        json_data=body
    )
    
    return JSONResponse(content=response.json(), status_code=response.status_code)

# Dashboard overview endpoint
@app.get("/api/dashboard/overview")
async def dashboard_overview(_: None = Depends(check_rate_limit)):
    """Get comprehensive dashboard overview."""
    try:
        # Get service health
        health_data = await health_check()
        
        # Try to get additional data from services
        overview_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "services": health_data.services,
            "service_count": {
                "total": health_data.total_services,
                "healthy": health_data.healthy_services,
                "unhealthy": health_data.total_services - health_data.healthy_services
            }
        }
        
        # Try to get portfolio summary if position service is healthy
        try:
            portfolio_response = await proxy_service.forward_request(
                service_name="position-management",
                path="/portfolio/summary",
                method="GET"
            )
            if portfolio_response.status_code == 200:
                overview_data["portfolio"] = portfolio_response.json()
        except:
            overview_data["portfolio"] = {"status": "unavailable"}
        
        # Try to get account info if trading service is healthy
        try:
            account_response = await proxy_service.forward_request(
                service_name="trading-execution",
                path="/account",
                method="GET"
            )
            if account_response.status_code == 200:
                overview_data["account"] = account_response.json()
        except:
            overview_data["account"] = {"status": "unavailable"}
        
        return overview_data
        
    except Exception as e:
        logger.error("Error getting dashboard overview", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get dashboard overview"
        )

# Circuit breaker status endpoint
@app.get("/api/gateway/circuits")
async def get_circuit_breaker_status():
    """Get circuit breaker status for all services."""
    status_data = {}
    
    for service_name, circuit_breaker in circuit_breakers.items():
        status_data[service_name] = {
            "state": circuit_breaker.state,
            "failure_count": circuit_breaker.failure_count,
            "last_failure": circuit_breaker.last_failure_time.isoformat() if circuit_breaker.last_failure_time else None,
            "threshold": circuit_breaker.failure_threshold
        }
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "circuit_breakers": status_data
    }

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=9000,
        reload=True
    )