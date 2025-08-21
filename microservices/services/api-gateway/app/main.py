
import httpx
from fastapi import FastAPI, Request
from datetime import datetime

app = FastAPI(title="API Gateway")

SERVICES = {
    "position-management": "http://localhost:6001",
    "trading-execution": "http://localhost:6002", 
    "signal-processing": "http://localhost:6003",
    "risk-management": "http://localhost:6004"
}

@app.get("/health")
async def health():
    return {
        "service": "api-gateway",
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/dashboard/overview")
async def dashboard_overview():
    data = {}
    async with httpx.AsyncClient(timeout=5.0) as client:
        for service, url in SERVICES.items():
            try:
                response = await client.get(f"{url}/health")
                data[service] = {"status": "healthy" if response.status_code == 200 else "unhealthy"}
            except:
                data[service] = {"status": "error"}
    
    return {
        "timestamp": datetime.now().isoformat(),
        "services": data,
        "status": "success"
    }

@app.api_route("/api/positions/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def route_positions(request: Request, path: str):
    async with httpx.AsyncClient() as client:
        response = await client.request(
            request.method,
            f"http://localhost:6001/positions/{path}",
            params=request.query_params
        )
        return response.json()

@app.api_route("/api/orders/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def route_orders(request: Request, path: str):
    async with httpx.AsyncClient() as client:
        response = await client.request(
            request.method,
            f"http://localhost:6002/orders/{path}",
            params=request.query_params
        )
        return response.json()
