#!/usr/bin/env python3
"""
Simplified Configuration Service for localhost testing
"""

import os
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(
    title="Configuration Service (Simple)",
    description="Simplified configuration management",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory configuration store
CONFIG_STORE = {
    "trading.enabled": {
        "value": True,
        "description": "Enable/disable trading functionality",
        "version": 1
    },
    "trading.max_position_size": {
        "value": 10000.0,
        "description": "Maximum position size in USD",
        "version": 1
    },
    "trading.risk_per_trade": {
        "value": 0.02,
        "description": "Risk percentage per trade (2%)",
        "version": 1
    },
    "signals.rsi_oversold": {
        "value": 30,
        "description": "RSI oversold threshold",
        "version": 1
    },
    "signals.rsi_overbought": {
        "value": 70,
        "description": "RSI overbought threshold",
        "version": 1
    },
    "market_data.update_interval": {
        "value": 60,
        "description": "Market data update interval in seconds",
        "version": 1
    }
}

class ConfigurationUpdate(BaseModel):
    value: Any
    environment: str = "default"
    description: Optional[str] = None

@app.get("/health")
async def health_check():
    """Configuration service health check."""
    return {
        "service": "configuration",
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "configs_loaded": len(CONFIG_STORE)
    }

@app.get("/config")
async def get_all_configurations():
    """Get all configurations."""
    result = {}
    for key, data in CONFIG_STORE.items():
        result[key] = {
            "value": data["value"],
            "description": data.get("description"),
            "version": data.get("version", 1),
            "last_updated": datetime.utcnow().isoformat()
        }
    return result

@app.get("/config/{key}")
async def get_configuration(key: str):
    """Get a specific configuration."""
    if key not in CONFIG_STORE:
        raise HTTPException(status_code=404, detail=f"Configuration {key} not found")
    
    config = CONFIG_STORE[key]
    return {
        "key": key,
        "value": config["value"],
        "description": config.get("description"),
        "version": config.get("version", 1),
        "last_updated": datetime.utcnow().isoformat()
    }

@app.post("/config/{key}")
async def update_configuration(key: str, update: ConfigurationUpdate):
    """Update a configuration value."""
    if key not in CONFIG_STORE:
        CONFIG_STORE[key] = {}
    
    CONFIG_STORE[key]["value"] = update.value
    CONFIG_STORE[key]["description"] = update.description
    CONFIG_STORE[key]["version"] = CONFIG_STORE[key].get("version", 0) + 1
    
    return {
        "key": key,
        "value": update.value,
        "description": update.description,
        "version": CONFIG_STORE[key]["version"],
        "last_updated": datetime.utcnow().isoformat(),
        "updated_by": "api"
    }

@app.get("/validate")
async def validate_configurations():
    """Validate all configurations."""
    return {
        "valid": True,
        "errors": [],
        "warnings": [],
        "total_configs": len(CONFIG_STORE),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/environments")
async def get_environments():
    """Get available environments."""
    return {
        "environments": ["default", "dev", "prod"],
        "current": "default"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main_simple:app", host="127.0.0.1", port=9009, reload=True)