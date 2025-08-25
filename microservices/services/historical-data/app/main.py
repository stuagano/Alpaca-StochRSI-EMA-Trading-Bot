#!/usr/bin/env python3
"""
Historical Data Service

Provides historical market data storage, retrieval, and analysis.
Manages historical data caching and provides advanced data queries.

Features:
- Historical data storage and retrieval
- Data aggregation and resampling
- Indicator calculations
- Data export functionality
- Efficient querying with caching
"""

import os
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Union
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, HTTPException, Depends, status, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import httpx
from pydantic import BaseModel, Field
import redis.asyncio as redis
import pandas as pd
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
import asyncpg

# Import shared database components
import sys
sys.path.append('/app')
from shared.database import get_db_session, MarketData, init_database

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
MARKET_DATA_SERVICE_URL = os.getenv("MARKET_DATA_SERVICE_URL", "http://market-data:8005")

# Redis client
redis_client = None

# Data Models
class HistoricalDataRequest(BaseModel):
    symbols: List[str] = Field(..., description="List of symbols")
    timeframe: str = Field(default="1d", description="Timeframe (1m, 5m, 15m, 30m, 1h, 1d, 1w)")
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="End date (YYYY-MM-DD)")
    indicators: Optional[List[str]] = Field(None, description="Technical indicators to calculate")

class HistoricalDataResponse(BaseModel):
    symbol: str
    timeframe: str
    start_date: str
    end_date: str
    data: List[Dict[str, Any]]
    indicators: Optional[Dict[str, List[float]]] = None
    total_records: int

class DataAggregationRequest(BaseModel):
    symbols: List[str]
    source_timeframe: str = Field(..., description="Source timeframe")
    target_timeframe: str = Field(..., description="Target timeframe")
    start_date: str
    end_date: str

class IndicatorRequest(BaseModel):
    symbol: str
    timeframe: str = "1d"
    period: int = 14
    indicator_type: str = Field(..., description="sma, ema, rsi, macd, bollinger")
    start_date: Optional[str] = None
    end_date: Optional[str] = None

class DataExportRequest(BaseModel):
    symbols: List[str]
    timeframe: str = "1d"
    start_date: str
    end_date: str
    format: str = Field(default="csv", description="Export format: csv, json, parquet")
    include_indicators: bool = False

# Historical Data Service
class HistoricalDataService:
    """Core historical data management service."""
    
    def __init__(self):
        self.cache_ttl = 3600  # 1 hour cache
        
    async def get_historical_data(self, 
                                symbols: List[str],
                                timeframe: str = "1d",
                                start_date: Optional[str] = None,
                                end_date: Optional[str] = None,
                                include_indicators: bool = False) -> List[HistoricalDataResponse]:
        """Get historical data for multiple symbols."""
        try:
            responses = []
            
            for symbol in symbols:
                # Check database first
                db_data = await self._get_data_from_db(symbol, timeframe, start_date, end_date)
                
                if not db_data:
                    # Fetch from market data service
                    market_data = await self._fetch_from_market_service(symbol, timeframe, start_date, end_date)
                    
                    if market_data:
                        # Store in database
                        await self._store_market_data(symbol, timeframe, market_data)
                        db_data = market_data
                
                if db_data:
                    # Calculate indicators if requested
                    indicators = None
                    if include_indicators:
                        indicators = await self._calculate_indicators(db_data)
                    
                    response = HistoricalDataResponse(
                        symbol=symbol,
                        timeframe=timeframe,
                        start_date=start_date or (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d"),
                        end_date=end_date or datetime.utcnow().strftime("%Y-%m-%d"),
                        data=db_data,
                        indicators=indicators,
                        total_records=len(db_data)
                    )
                    responses.append(response)
                else:
                    logger.warning("No data found for symbol", symbol=symbol)
            
            return responses
            
        except Exception as e:
            logger.error("Error getting historical data", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get historical data: {str(e)}"
            )
    
    async def aggregate_data(self, 
                           symbols: List[str],
                           source_timeframe: str,
                           target_timeframe: str,
                           start_date: str,
                           end_date: str) -> List[HistoricalDataResponse]:
        """Aggregate data from one timeframe to another."""
        try:
            responses = []
            
            for symbol in symbols:
                # Get source data
                source_data = await self._get_data_from_db(symbol, source_timeframe, start_date, end_date)
                
                if not source_data:
                    continue
                
                # Convert to DataFrame for aggregation
                df = pd.DataFrame(source_data)
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)
                
                # Define aggregation rules
                agg_rules = {
                    'open': 'first',
                    'high': 'max',
                    'low': 'min',
                    'close': 'last',
                    'volume': 'sum'
                }
                
                # Map target timeframe to pandas frequency
                freq_map = {
                    '5m': '5T', '15m': '15T', '30m': '30T', 
                    '1h': '1H', '4h': '4H', '1d': '1D', '1w': '1W'
                }
                
                freq = freq_map.get(target_timeframe, '1D')
                
                # Perform aggregation
                aggregated = df.resample(freq).agg(agg_rules).dropna()
                
                # Convert back to list of dictionaries
                aggregated_data = []
                for index, row in aggregated.iterrows():
                    aggregated_data.append({
                        'timestamp': index.isoformat(),
                        'open': float(row['open']),
                        'high': float(row['high']),
                        'low': float(row['low']),
                        'close': float(row['close']),
                        'volume': int(row['volume'])
                    })
                
                # Store aggregated data
                await self._store_market_data(symbol, target_timeframe, aggregated_data)
                
                response = HistoricalDataResponse(
                    symbol=symbol,
                    timeframe=target_timeframe,
                    start_date=start_date,
                    end_date=end_date,
                    data=aggregated_data,
                    total_records=len(aggregated_data)
                )
                responses.append(response)
            
            return responses
            
        except Exception as e:
            logger.error("Error aggregating data", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to aggregate data: {str(e)}"
            )
    
    async def calculate_technical_indicators(self, 
                                           symbol: str,
                                           timeframe: str,
                                           indicator_type: str,
                                           period: int = 14,
                                           start_date: Optional[str] = None,
                                           end_date: Optional[str] = None) -> Dict[str, Any]:
        """Calculate technical indicators for historical data."""
        try:
            # Get historical data
            data = await self._get_data_from_db(symbol, timeframe, start_date, end_date)
            
            if not data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No data found for {symbol}"
                )
            
            # Convert to DataFrame
            df = pd.DataFrame(data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Calculate indicator
            if indicator_type.lower() == 'sma':
                df['sma'] = df['close'].rolling(window=period).mean()
                indicator_values = df['sma'].dropna().tolist()
            
            elif indicator_type.lower() == 'ema':
                df['ema'] = df['close'].ewm(span=period).mean()
                indicator_values = df['ema'].dropna().tolist()
            
            elif indicator_type.lower() == 'rsi':
                delta = df['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
                rs = gain / loss
                df['rsi'] = 100 - (100 / (1 + rs))
                indicator_values = df['rsi'].dropna().tolist()
            
            elif indicator_type.lower() == 'macd':
                ema12 = df['close'].ewm(span=12).mean()
                ema26 = df['close'].ewm(span=26).mean()
                df['macd'] = ema12 - ema26
                df['signal'] = df['macd'].ewm(span=9).mean()
                df['histogram'] = df['macd'] - df['signal']
                
                indicator_values = {
                    'macd': df['macd'].dropna().tolist(),
                    'signal': df['signal'].dropna().tolist(),
                    'histogram': df['histogram'].dropna().tolist()
                }
            
            elif indicator_type.lower() == 'bollinger':
                df['sma'] = df['close'].rolling(window=period).mean()
                df['std'] = df['close'].rolling(window=period).std()
                df['upper_band'] = df['sma'] + (df['std'] * 2)
                df['lower_band'] = df['sma'] - (df['std'] * 2)
                
                indicator_values = {
                    'upper_band': df['upper_band'].dropna().tolist(),
                    'middle_band': df['sma'].dropna().tolist(),
                    'lower_band': df['lower_band'].dropna().tolist()
                }
            
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported indicator type: {indicator_type}"
                )
            
            return {
                'symbol': symbol,
                'indicator_type': indicator_type,
                'period': period,
                'values': indicator_values,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Error calculating indicators", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to calculate indicators: {str(e)}"
            )
    
    async def export_data(self, request: DataExportRequest) -> str:
        """Export historical data in specified format."""
        try:
            # Get data for all symbols
            all_data = []
            for symbol in request.symbols:
                data = await self._get_data_from_db(
                    symbol, request.timeframe, request.start_date, request.end_date
                )
                
                for record in data:
                    record['symbol'] = symbol
                    all_data.append(record)
            
            if not all_data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No data found for export"
                )
            
            # Convert to DataFrame
            df = pd.DataFrame(all_data)
            
            # Add indicators if requested
            if request.include_indicators:
                # Add basic indicators for each symbol
                for symbol in request.symbols:
                    symbol_data = df[df['symbol'] == symbol].copy()
                    symbol_data['sma_20'] = symbol_data['close'].rolling(20).mean()
                    symbol_data['rsi_14'] = self._calculate_rsi(symbol_data['close'], 14)
                    df[df['symbol'] == symbol] = symbol_data
            
            # Generate export filename
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"historical_data_{timestamp}.{request.format}"
            
            # Export based on format
            if request.format == 'csv':
                export_path = f"/tmp/{filename}"
                df.to_csv(export_path, index=False)
            elif request.format == 'json':
                export_path = f"/tmp/{filename}"
                df.to_json(export_path, orient='records', date_format='iso')
            elif request.format == 'parquet':
                export_path = f"/tmp/{filename}"
                df.to_parquet(export_path, index=False)
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported export format: {request.format}"
                )
            
            return export_path
            
        except Exception as e:
            logger.error("Error exporting data", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to export data: {str(e)}"
            )
    
    # Helper methods
    async def _get_data_from_db(self, 
                              symbol: str, 
                              timeframe: str, 
                              start_date: Optional[str] = None, 
                              end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get historical data from database."""
        try:
            async with get_db_session() as session:
                query = select(MarketData).where(
                    and_(
                        MarketData.symbol == symbol,
                        MarketData.timeframe == timeframe
                    )
                )
                
                if start_date:
                    start_dt = datetime.fromisoformat(start_date)
                    query = query.where(MarketData.timestamp >= start_dt)
                
                if end_date:
                    end_dt = datetime.fromisoformat(end_date)
                    query = query.where(MarketData.timestamp <= end_dt)
                
                query = query.order_by(MarketData.timestamp)
                
                result = await session.execute(query)
                records = result.scalars().all()
                
                return [record.to_dict() for record in records]
                
        except Exception as e:
            logger.error("Database query error", error=str(e))
            return []
    
    async def _fetch_from_market_service(self, 
                                       symbol: str, 
                                       timeframe: str, 
                                       start_date: Optional[str] = None, 
                                       end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch data from market data service."""
        try:
            async with httpx.AsyncClient() as client:
                params = {
                    'timeframe': timeframe,
                    'limit': 1000
                }
                
                if start_date:
                    params['start_date'] = start_date
                if end_date:
                    params['end_date'] = end_date
                
                response = await client.get(
                    f"{MARKET_DATA_SERVICE_URL}/historical/{symbol}",
                    params=params,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get('data', [])
                else:
                    logger.warning("Market service request failed", 
                                 status=response.status_code, symbol=symbol)
                    return []
                    
        except Exception as e:
            logger.error("Market service fetch error", error=str(e))
            return []
    
    async def _store_market_data(self, symbol: str, timeframe: str, data: List[Dict[str, Any]]):
        """Store market data in database."""
        try:
            async with get_db_session() as session:
                for record in data:
                    # Check if record already exists
                    existing = await session.execute(
                        select(MarketData).where(
                            and_(
                                MarketData.symbol == symbol,
                                MarketData.timeframe == timeframe,
                                MarketData.timestamp == datetime.fromisoformat(record['timestamp'].replace('Z', '+00:00'))
                            )
                        )
                    )
                    
                    if not existing.scalar():
                        market_data = MarketData(
                            symbol=symbol,
                            timeframe=timeframe,
                            timestamp=datetime.fromisoformat(record['timestamp'].replace('Z', '+00:00')),
                            open_price=record.get('open'),
                            high_price=record.get('high'),
                            low_price=record.get('low'),
                            close_price=record.get('close'),
                            volume=record.get('volume'),
                            data_type='bar'
                        )
                        session.add(market_data)
                
                await session.commit()
                
        except Exception as e:
            logger.error("Error storing market data", error=str(e))
    
    async def _calculate_indicators(self, data: List[Dict[str, Any]]) -> Dict[str, List[float]]:
        """Calculate basic technical indicators."""
        try:
            df = pd.DataFrame(data)
            df['close'] = df['close'].astype(float)
            
            indicators = {}
            
            # Simple Moving Average (20 period)
            indicators['sma_20'] = df['close'].rolling(20).mean().dropna().tolist()
            
            # RSI (14 period)
            indicators['rsi_14'] = self._calculate_rsi(df['close'], 14).dropna().tolist()
            
            return indicators
            
        except Exception as e:
            logger.error("Error calculating indicators", error=str(e))
            return {}
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI indicator."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

# Global service instance
historical_service = HistoricalDataService()

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
        
        logger.info("✅ Historical Data Service started successfully")
        yield
    except Exception as e:
        logger.error("❌ Failed to start Historical Data Service", error=str(e))
        yield
    finally:
        if redis_client:
            await redis_client.close()
        logger.info("🔌 Historical Data Service shutdown complete")

# FastAPI application
app = FastAPI(
    title="Historical Data Service",
    description="Historical market data storage and analysis",
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
        "service": "historical-data",
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "redis_connected": redis_connected
    }

@app.post("/data", response_model=List[HistoricalDataResponse])
async def get_historical_data(request: HistoricalDataRequest):
    """Get historical data for multiple symbols."""
    include_indicators = bool(request.indicators)
    
    return await historical_service.get_historical_data(
        symbols=request.symbols,
        timeframe=request.timeframe,
        start_date=request.start_date,
        end_date=request.end_date,
        include_indicators=include_indicators
    )

@app.get("/data/{symbol}", response_model=HistoricalDataResponse)
async def get_symbol_data(
    symbol: str,
    timeframe: str = Query(default="1d"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    include_indicators: bool = Query(default=False)
):
    """Get historical data for a single symbol."""
    results = await historical_service.get_historical_data(
        symbols=[symbol.upper()],
        timeframe=timeframe,
        start_date=start_date,
        end_date=end_date,
        include_indicators=include_indicators
    )
    
    if not results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No data found for symbol {symbol}"
        )
    
    return results[0]

@app.post("/aggregate", response_model=List[HistoricalDataResponse])
async def aggregate_data(request: DataAggregationRequest):
    """Aggregate data from one timeframe to another."""
    return await historical_service.aggregate_data(
        symbols=request.symbols,
        source_timeframe=request.source_timeframe,
        target_timeframe=request.target_timeframe,
        start_date=request.start_date,
        end_date=request.end_date
    )

@app.post("/indicators")
async def calculate_indicators(request: IndicatorRequest):
    """Calculate technical indicators."""
    return await historical_service.calculate_technical_indicators(
        symbol=request.symbol,
        timeframe=request.timeframe,
        indicator_type=request.indicator_type,
        period=request.period,
        start_date=request.start_date,
        end_date=request.end_date
    )

@app.post("/export")
async def export_data(request: DataExportRequest, background_tasks: BackgroundTasks):
    """Export historical data."""
    export_path = await historical_service.export_data(request)
    
    # Schedule file cleanup after 1 hour
    background_tasks.add_task(lambda: os.remove(export_path) if os.path.exists(export_path) else None)
    
    return {
        "message": "Data exported successfully",
        "file_path": export_path,
        "download_url": f"/download/{os.path.basename(export_path)}"
    }

@app.get("/stats/{symbol}")
async def get_data_stats(symbol: str, timeframe: str = Query(default="1d")):
    """Get statistics about available data for a symbol."""
    try:
        async with get_db_session() as session:
            # Get data range and count
            result = await session.execute(
                select(
                    func.min(MarketData.timestamp).label('earliest'),
                    func.max(MarketData.timestamp).label('latest'),
                    func.count(MarketData.id).label('total_records')
                ).where(
                    and_(
                        MarketData.symbol == symbol.upper(),
                        MarketData.timeframe == timeframe
                    )
                )
            )
            
            stats = result.first()
            
            return {
                "symbol": symbol.upper(),
                "timeframe": timeframe,
                "earliest_date": stats.earliest.isoformat() if stats.earliest else None,
                "latest_date": stats.latest.isoformat() if stats.latest else None,
                "total_records": stats.total_records or 0
            }
            
    except Exception as e:
        logger.error("Error getting data stats", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get data statistics"
        )

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8006,
        reload=True
    )