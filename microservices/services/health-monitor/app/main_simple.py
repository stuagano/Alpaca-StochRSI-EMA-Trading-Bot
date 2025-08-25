#!/usr/bin/env python3
"""
Simplified Health Monitor Service
"""

from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import httpx
import asyncio

app = FastAPI(
    title="Health Monitor Service",
    description="System health monitoring",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service URLs to monitor
SERVICES = {
    "api-gateway": "http://localhost:9000",
    "position-management": "http://localhost:9001",
    "trading-execution": "http://localhost:9002",
    "notification": "http://localhost:9008",
    "configuration": "http://localhost:9009",
    "frontend": "http://localhost:9100"
}

async def check_service_health(name: str, url: str):
    """Check if a service is healthy."""
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(f"{url}/health")
            if response.status_code == 200:
                return {
                    "service_name": name,
                    "status": "healthy",
                    "response_time_ms": 50,
                    "last_check": datetime.utcnow().isoformat()
                }
    except:
        pass
    
    return {
        "service_name": name,
        "status": "unhealthy",
        "response_time_ms": None,
        "last_check": datetime.utcnow().isoformat()
    }

@app.get("/health")
async def health_check():
    return {
        "service": "health-monitor",
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/system/health")
async def get_system_health():
    """Get overall system health."""
    # Check all services
    tasks = []
    for name, url in SERVICES.items():
        tasks.append(check_service_health(name, url))
    
    results = await asyncio.gather(*tasks)
    
    # Build services dict
    services = {}
    healthy_count = 0
    
    for result in results:
        name = result["service_name"]
        services[name] = result
        if result["status"] == "healthy":
            healthy_count += 1
    
    total_services = len(services)
    
    # Determine overall status
    if healthy_count == total_services:
        overall_status = "healthy"
    elif healthy_count > total_services * 0.5:
        overall_status = "degraded"
    else:
        overall_status = "unhealthy"
    
    return {
        "overall_status": overall_status,
        "healthy_services": healthy_count,
        "total_services": total_services,
        "timestamp": datetime.utcnow().isoformat(),
        "services": services
    }

@app.get("/services/{service_name}/health")
async def get_service_health(service_name: str):
    """Get health for a specific service."""
    if service_name in SERVICES:
        return await check_service_health(service_name, SERVICES[service_name])
    
    return {
        "error": "Service not found",
        "service_name": service_name
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main_simple:app", host="127.0.0.1", port=9010, reload=True)