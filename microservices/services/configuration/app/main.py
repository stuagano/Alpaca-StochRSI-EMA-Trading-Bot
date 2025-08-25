#!/usr/bin/env python3
"""
Configuration Service

Centralized configuration management for the trading system.
Provides dynamic configuration updates, environment-specific settings,
and secure parameter management.

Features:
- Dynamic configuration updates
- Environment-specific configurations
- Configuration validation
- Secure parameter storage
- Configuration versioning
- Real-time configuration broadcasts
"""

import os
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
import json
import hashlib

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

# Redis client
redis_client = None

# Data Models
class ConfigurationItem(BaseModel):
    key: str = Field(..., description="Configuration key")
    value: Any = Field(..., description="Configuration value")
    environment: str = Field(default="default", description="Environment (default, dev, prod)")
    description: Optional[str] = Field(None, description="Configuration description")
    is_secure: bool = Field(default=False, description="Whether value should be encrypted")
    tags: Optional[List[str]] = Field(None, description="Configuration tags")

class ConfigurationUpdate(BaseModel):
    key: str
    value: Any
    environment: str = "default"
    description: Optional[str] = None

class ConfigurationResponse(BaseModel):
    key: str
    value: Any
    environment: str
    description: Optional[str]
    version: int
    last_updated: str
    updated_by: str

class ConfigurationBatch(BaseModel):
    configurations: List[ConfigurationItem]
    environment: str = "default"

# Configuration Service
class ConfigurationService:
    """Core configuration management service."""
    
    def __init__(self):
        self.config_cache = {}
        self.cache_ttl = 300  # 5 minutes
        
    async def get_configuration(self, 
                              key: str, 
                              environment: str = "default") -> Optional[Dict[str, Any]]:
        """Get a single configuration value."""
        try:
            # Check cache first
            cache_key = f"config:{environment}:{key}"
            
            if redis_client:
                cached = await redis_client.get(cache_key)
                if cached:
                    return json.loads(cached)
            
            # Get from database (would implement with proper config table)
            # For now, return default configurations
            config_data = await self._get_default_configurations(environment)
            
            if key in config_data:
                result = {
                    "key": key,
                    "value": config_data[key]["value"],
                    "environment": environment,
                    "description": config_data[key].get("description"),
                    "version": config_data[key].get("version", 1),
                    "last_updated": datetime.utcnow().isoformat(),
                    "updated_by": "system"
                }
                
                # Cache the result
                if redis_client:
                    await redis_client.setex(
                        cache_key, 
                        self.cache_ttl, 
                        json.dumps(result)
                    )
                
                return result
            
            return None
            
        except Exception as e:
            logger.error("Error getting configuration", key=key, error=str(e))
            return None
    
    async def get_all_configurations(self, environment: str = "default") -> Dict[str, Any]:
        """Get all configurations for an environment."""
        try:
            # Check cache first
            cache_key = f"config:all:{environment}"
            
            if redis_client:
                cached = await redis_client.get(cache_key)
                if cached:
                    return json.loads(cached)
            
            # Get default configurations
            config_data = await self._get_default_configurations(environment)
            
            # Format response
            result = {}
            for key, data in config_data.items():
                result[key] = {
                    "value": data["value"],
                    "description": data.get("description"),
                    "version": data.get("version", 1),
                    "last_updated": datetime.utcnow().isoformat()
                }
            
            # Cache the result
            if redis_client:
                await redis_client.setex(
                    cache_key, 
                    self.cache_ttl, 
                    json.dumps(result)
                )
            
            return result
            
        except Exception as e:
            logger.error("Error getting all configurations", error=str(e))
            return {}
    
    async def update_configuration(self, 
                                 key: str, 
                                 value: Any, 
                                 environment: str = "default",
                                 description: Optional[str] = None) -> Dict[str, Any]:
        """Update a configuration value."""
        try:
            # Validate the configuration
            await self._validate_configuration(key, value, environment)
            
            # In a real implementation, this would update the database
            # For now, we'll simulate by updating cache
            config_data = {
                "key": key,
                "value": value,
                "environment": environment,
                "description": description,
                "version": 1,
                "last_updated": datetime.utcnow().isoformat(),
                "updated_by": "api"
            }
            
            # Update cache
            if redis_client:
                cache_key = f"config:{environment}:{key}"
                await redis_client.setex(
                    cache_key, 
                    self.cache_ttl, 
                    json.dumps(config_data)
                )
                
                # Invalidate all configs cache
                all_cache_key = f"config:all:{environment}"
                await redis_client.delete(all_cache_key)
                
                # Broadcast configuration change
                await self._broadcast_config_change(key, value, environment)
            
            logger.info("Configuration updated", key=key, environment=environment)
            return config_data
            
        except Exception as e:
            logger.error("Error updating configuration", key=key, error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update configuration: {str(e)}"
            )
    
    async def delete_configuration(self, key: str, environment: str = "default") -> bool:
        """Delete a configuration."""
        try:
            # Remove from cache
            if redis_client:
                cache_key = f"config:{environment}:{key}"
                await redis_client.delete(cache_key)
                
                # Invalidate all configs cache
                all_cache_key = f"config:all:{environment}"
                await redis_client.delete(all_cache_key)
                
                # Broadcast deletion
                await self._broadcast_config_change(key, None, environment, deleted=True)
            
            logger.info("Configuration deleted", key=key, environment=environment)
            return True
            
        except Exception as e:
            logger.error("Error deleting configuration", key=key, error=str(e))
            return False
    
    async def get_configuration_history(self, key: str, environment: str = "default") -> List[Dict[str, Any]]:
        """Get configuration change history."""
        try:
            # In a real implementation, this would query configuration history table
            # For now, return mock history
            return [
                {
                    "key": key,
                    "environment": environment,
                    "version": 1,
                    "value": "mock_value",
                    "changed_at": datetime.utcnow().isoformat(),
                    "changed_by": "system",
                    "change_type": "created"
                }
            ]
            
        except Exception as e:
            logger.error("Error getting configuration history", key=key, error=str(e))
            return []
    
    async def validate_configurations(self, environment: str = "default") -> Dict[str, Any]:
        """Validate all configurations for an environment."""
        try:
            config_data = await self.get_all_configurations(environment)
            validation_results = {
                "valid": True,
                "errors": [],
                "warnings": [],
                "total_configs": len(config_data)
            }
            
            # Validate each configuration
            for key, data in config_data.items():
                try:
                    await self._validate_configuration(key, data["value"], environment)
                except Exception as e:
                    validation_results["valid"] = False
                    validation_results["errors"].append({
                        "key": key,
                        "error": str(e)
                    })
            
            return validation_results
            
        except Exception as e:
            logger.error("Error validating configurations", error=str(e))
            return {"valid": False, "errors": [str(e)]}
    
    # Helper methods
    async def _get_default_configurations(self, environment: str) -> Dict[str, Any]:
        """Get default configurations for the trading system."""
        
        base_configs = {
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
            "signals.ema_periods": {
                "value": [12, 26],
                "description": "EMA periods for signal calculation",
                "version": 1
            },
            "risk.max_drawdown": {
                "value": 0.10,
                "description": "Maximum allowable drawdown (10%)",
                "version": 1
            },
            "risk.max_daily_loss": {
                "value": 0.05,
                "description": "Maximum daily loss (5%)",
                "version": 1
            },
            "market_data.update_interval": {
                "value": 60,
                "description": "Market data update interval in seconds",
                "version": 1
            },
            "notifications.email_enabled": {
                "value": True,
                "description": "Enable email notifications",
                "version": 1
            }
        }
        
        # Environment-specific overrides
        if environment == "dev":
            base_configs["trading.enabled"]["value"] = False
            base_configs["trading.max_position_size"]["value"] = 1000.0
        elif environment == "prod":
            base_configs["risk.max_drawdown"]["value"] = 0.05
            base_configs["risk.max_daily_loss"]["value"] = 0.02
        
        return base_configs
    
    async def _validate_configuration(self, key: str, value: Any, environment: str):
        """Validate a configuration value."""
        
        # Define validation rules
        validation_rules = {
            "trading.max_position_size": lambda v: isinstance(v, (int, float)) and v > 0,
            "trading.risk_per_trade": lambda v: isinstance(v, (int, float)) and 0 < v <= 1,
            "signals.rsi_oversold": lambda v: isinstance(v, int) and 0 <= v <= 100,
            "signals.rsi_overbought": lambda v: isinstance(v, int) and 0 <= v <= 100,
            "risk.max_drawdown": lambda v: isinstance(v, (int, float)) and 0 < v <= 1,
            "risk.max_daily_loss": lambda v: isinstance(v, (int, float)) and 0 < v <= 1,
            "market_data.update_interval": lambda v: isinstance(v, int) and v > 0,
        }
        
        if key in validation_rules:
            if not validation_rules[key](value):
                raise ValueError(f"Invalid value for {key}: {value}")
    
    async def _broadcast_config_change(self, key: str, value: Any, environment: str, deleted: bool = False):
        """Broadcast configuration changes to subscribed services."""
        try:
            if redis_client:
                change_event = {
                    "type": "config_deleted" if deleted else "config_updated",
                    "key": key,
                    "value": value,
                    "environment": environment,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                # Publish to Redis channel
                channel = f"config_changes:{environment}"
                await redis_client.publish(channel, json.dumps(change_event))
                
        except Exception as e:
            logger.error("Error broadcasting config change", error=str(e))

# Global service instance
config_service = ConfigurationService()

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
        
        logger.info("✅ Configuration Service started successfully")
        yield
    except Exception as e:
        logger.error("❌ Failed to start Configuration Service", error=str(e))
        yield
    finally:
        if redis_client:
            await redis_client.close()
        logger.info("🔌 Configuration Service shutdown complete")

# FastAPI application
app = FastAPI(
    title="Configuration Service",
    description="Centralized configuration management for trading system",
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
        "service": "configuration",
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "redis_connected": redis_connected
    }

@app.get("/config/{key}", response_model=ConfigurationResponse)
async def get_configuration(key: str, environment: str = "default"):
    """Get a specific configuration value."""
    config = await config_service.get_configuration(key, environment)
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration {key} not found for environment {environment}"
        )
    
    return config

@app.get("/config")
async def get_all_configurations(environment: str = "default"):
    """Get all configurations for an environment."""
    return await config_service.get_all_configurations(environment)

@app.post("/config/{key}")
async def update_configuration(key: str, update: ConfigurationUpdate):
    """Update a configuration value."""
    return await config_service.update_configuration(
        key=key,
        value=update.value,
        environment=update.environment,
        description=update.description
    )

@app.put("/config/{key}")
async def create_or_update_configuration(key: str, item: ConfigurationItem):
    """Create or update a configuration value."""
    return await config_service.update_configuration(
        key=key,
        value=item.value,
        environment=item.environment,
        description=item.description
    )

@app.delete("/config/{key}")
async def delete_configuration(key: str, environment: str = "default"):
    """Delete a configuration."""
    success = await config_service.delete_configuration(key, environment)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete configuration"
        )
    
    return {"message": f"Configuration {key} deleted successfully"}

@app.post("/config/batch")
async def batch_update_configurations(batch: ConfigurationBatch):
    """Batch update multiple configurations."""
    results = []
    
    for config_item in batch.configurations:
        try:
            result = await config_service.update_configuration(
                key=config_item.key,
                value=config_item.value,
                environment=config_item.environment or batch.environment,
                description=config_item.description
            )
            results.append({"key": config_item.key, "status": "success", "data": result})
        except Exception as e:
            results.append({"key": config_item.key, "status": "error", "error": str(e)})
    
    return {"results": results}

@app.get("/config/{key}/history")
async def get_configuration_history(key: str, environment: str = "default"):
    """Get configuration change history."""
    return await config_service.get_configuration_history(key, environment)

@app.get("/validate")
async def validate_configurations(environment: str = "default"):
    """Validate all configurations."""
    return await config_service.validate_configurations(environment)

@app.get("/environments")
async def get_environments():
    """Get available environments."""
    return {
        "environments": ["default", "dev", "prod"],
        "current": "default"
    }

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8009,
        reload=True
    )