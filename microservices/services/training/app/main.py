"""
Training Service - Collaborative Human-AI Trading Strategy Development
Port: 9011
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import pandas as pd
import numpy as np
import yfinance as yf
try:
    import redis
except ImportError:
    redis = None
import sqlite3
from pathlib import Path

# Add training module to path
sys.path.append('/app')
try:
    from training_engine import TrainingDatabase, BacktestEngine, StrategyEngine, CollaborativeLearning as CollaborativeEngine
except ImportError:
    from app.training_engine import TrainingDatabase, BacktestEngine, StrategyEngine, CollaborativeLearning as CollaborativeEngine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Redis connection
redis_client = None

# Database and engines
training_db = None
backtest_engine = None
strategy_engine = None
collaborative_engine = None

# WebSocket connections manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

# Pydantic models
class BacktestRequest(BaseModel):
    strategy: str = Field(default="stoch_rsi_ema")
    symbol: str = Field(default="AAPL")
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    initial_capital: float = Field(default=10000.0)
    parameters: Optional[Dict] = None

class CollaborativeDecisionRequest(BaseModel):
    symbol: str
    human_decision: str
    human_reasoning: str
    confidence: float = Field(ge=0, le=100)

class TrainingScenarioRequest(BaseModel):
    scenario: str
    symbol: str
    difficulty: str = Field(default="intermediate")

class StrategyComparisonRequest(BaseModel):
    symbol: str
    strategies: List[str] = Field(default=["stoch_rsi_ema", "bollinger_mean_reversion", "momentum_breakout"])
    days: int = Field(default=180)

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global redis_client, training_db, backtest_engine, strategy_engine, collaborative_engine
    
    # Initialize Redis (optional)
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    try:
        if redis:
            redis_client = redis.Redis.from_url(redis_url, decode_responses=True)
            redis_client.ping()
            logger.info("Connected to Redis")
        else:
            logger.warning("Redis not available. Continuing without cache.")
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}. Continuing without cache.")
        redis_client = None
    
    # Initialize training database and engines
    db_path = os.getenv("DATABASE_PATH", "data/training.db")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    training_db = TrainingDatabase(db_path)
    backtest_engine = BacktestEngine(training_db)
    strategy_engine = StrategyEngine()
    collaborative_engine = CollaborativeEngine(training_db)
    
    logger.info(f"Training service initialized with database at {db_path}")
    
    # Download initial market data for popular symbols
    await download_initial_data()
    
    yield
    
    # Shutdown
    if redis_client:
        await redis_client.close()
    logger.info("Training service shutdown complete")

# Initialize FastAPI app
app = FastAPI(
    title="Trading Training Service",
    description="Collaborative Human-AI Trading Strategy Development",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def download_initial_data():
    """Download initial market data for common symbols"""
    symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'SPY']
    end_date = datetime.now()
    start_date = end_date - timedelta(days=730)  # 2 years
    
    for symbol in symbols:
        try:
            # Check if data already exists
            existing_data = training_db.get_historical_data(
                symbol, 
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d')
            )
            
            if existing_data.empty:
                logger.info(f"Downloading historical data for {symbol}")
                data = yf.download(
                    symbol, 
                    start=start_date.strftime('%Y-%m-%d'),
                    end=end_date.strftime('%Y-%m-%d'),
                    progress=False
                )
                if not data.empty:
                    training_db.store_historical_data(symbol, data, '1d')
                    logger.info(f"Stored {len(data)} days of data for {symbol}")
        except Exception as e:
            logger.error(f"Error downloading data for {symbol}: {e}")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "training",
        "timestamp": datetime.now().isoformat(),
        "database": "connected" if training_db else "disconnected",
        "redis": "connected" if redis_client else "disconnected"
    }

# Backtest endpoints
@app.post("/api/backtest")
async def run_backtest(request: BacktestRequest):
    """Run a strategy backtest"""
    try:
        # Set default dates if not provided
        if not request.end_date:
            request.end_date = datetime.now().strftime('%Y-%m-%d')
        if not request.start_date:
            start = datetime.now() - timedelta(days=180)
            request.start_date = start.strftime('%Y-%m-%d')
        
        # Run backtest
        performance = backtest_engine.run_backtest(
            strategy_name=request.strategy,
            symbol=request.symbol,
            start_date=request.start_date,
            end_date=request.end_date,
            strategy_params=request.parameters or {},
            initial_capital=request.initial_capital
        )
        
        # Cache result in Redis if available
        if redis_client:
            try:
                cache_key = f"backtest:{request.symbol}:{request.strategy}:{request.start_date}:{request.end_date}"
                redis_client.setex(
                    cache_key,
                    3600,  # 1 hour TTL
                    json.dumps(performance, default=str)
                )
            except Exception as e:
                logger.warning(f"Redis caching failed: {e}")
        
        return {
            "status": "success",
            "data": performance
        }
    
    except Exception as e:
        logger.error(f"Backtest error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/backtest/history")
async def get_backtest_history(limit: int = 10):
    """Get recent backtest history"""
    try:
        conn = sqlite3.connect(training_db.db_path)
        cursor = conn.execute("""
            SELECT b.*, s.name as strategy_name
            FROM backtests b
            JOIN strategies s ON b.strategy_id = s.id
            ORDER BY b.created_at DESC
            LIMIT ?
        """, (limit,))
        
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
        
        return {
            "status": "success",
            "data": results
        }
    
    except Exception as e:
        logger.error(f"Error fetching backtest history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Collaborative decision endpoints
@app.post("/api/collaborate/decision")
async def make_collaborative_decision(request: CollaborativeDecisionRequest):
    """Make a collaborative trading decision"""
    try:
        # Get current market data
        data = yf.download(
            request.symbol,
            start=(datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d'),
            end=datetime.now().strftime('%Y-%m-%d'),
            progress=False
        )
        
        if data.empty:
            raise HTTPException(status_code=404, detail="No market data available")
        
        # Get AI analysis
        ai_analysis = collaborative_engine.analyze_market(request.symbol, data)
        
        # Store collaborative decision
        decision_id = training_db.store_decision(
            session_name=f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            symbol=request.symbol,
            timestamp=datetime.now(),
            current_price=float(data['Close'].iloc[-1]),
            market_data=ai_analysis['indicators'],
            human_decision=request.human_decision,
            human_reasoning=request.human_reasoning,
            human_confidence=request.confidence,
            ai_decision=ai_analysis['recommendation'],
            ai_reasoning=ai_analysis['reasoning'],
            ai_confidence=ai_analysis['confidence'],
            final_decision=collaborative_engine.synthesize_decision(
                request.human_decision,
                ai_analysis['recommendation'],
                request.confidence,
                ai_analysis['confidence']
            )['action'],
            synthesis_reasoning=collaborative_engine.synthesize_decision(
                request.human_decision,
                ai_analysis['recommendation'],
                request.confidence,
                ai_analysis['confidence']
            )['reasoning']
        )
        
        return {
            "status": "success",
            "data": {
                "decision_id": decision_id,
                "human_decision": request.human_decision,
                "ai_analysis": ai_analysis,
                "final_decision": collaborative_engine.synthesize_decision(
                    request.human_decision,
                    ai_analysis['recommendation'],
                    request.confidence,
                    ai_analysis['confidence']
                )
            }
        }
    
    except Exception as e:
        logger.error(f"Collaborative decision error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/collaborate/current/{symbol}")
async def get_current_market_analysis(symbol: str):
    """Get current market analysis for a symbol"""
    try:
        # Get recent market data
        data = yf.download(
            symbol,
            start=(datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d'),
            end=datetime.now().strftime('%Y-%m-%d'),
            progress=False
        )
        
        if data.empty:
            raise HTTPException(status_code=404, detail="No market data available")
        
        # Get AI analysis
        analysis = collaborative_engine.analyze_market(symbol, data)
        
        # Add current price and basic stats
        current_price = float(data['Close'].iloc[-1])
        analysis['current_price'] = current_price
        analysis['day_change'] = float((data['Close'].iloc[-1] - data['Close'].iloc[-2]) / data['Close'].iloc[-2] * 100)
        analysis['volume'] = int(data['Volume'].iloc[-1])
        
        return {
            "status": "success",
            "data": analysis
        }
    
    except Exception as e:
        logger.error(f"Market analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Strategy comparison endpoints
@app.post("/api/strategies/compare")
async def compare_strategies(request: StrategyComparisonRequest):
    """Compare multiple strategies on the same data"""
    try:
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=request.days)).strftime('%Y-%m-%d')
        
        comparison_results = []
        
        for strategy in request.strategies:
            try:
                performance = backtest_engine.run_backtest(
                    strategy_name=strategy,
                    symbol=request.symbol,
                    start_date=start_date,
                    end_date=end_date,
                    initial_capital=10000
                )
                
                comparison_results.append({
                    "strategy": strategy,
                    "performance": performance
                })
            except Exception as e:
                logger.error(f"Error backtesting {strategy}: {e}")
                comparison_results.append({
                    "strategy": strategy,
                    "error": str(e)
                })
        
        # Sort by total return
        comparison_results.sort(
            key=lambda x: x.get('performance', {}).get('total_return', -999),
            reverse=True
        )
        
        return {
            "status": "success",
            "data": {
                "symbol": request.symbol,
                "period": f"{start_date} to {end_date}",
                "results": comparison_results
            }
        }
    
    except Exception as e:
        logger.error(f"Strategy comparison error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/strategies")
async def get_available_strategies():
    """Get list of available trading strategies"""
    strategies = [
        {
            "name": "stoch_rsi_ema",
            "display_name": "StochRSI + EMA Crossover",
            "description": "Combines StochRSI oversold/overbought with EMA trend confirmation",
            "complexity": "intermediate",
            "parameters": {
                "rsi_oversold": 20,
                "rsi_overbought": 80,
                "ema_fast": 9,
                "ema_slow": 21
            }
        },
        {
            "name": "bollinger_mean_reversion",
            "display_name": "Bollinger Bands Mean Reversion",
            "description": "Trades bounces off Bollinger Band extremes",
            "complexity": "beginner",
            "parameters": {
                "period": 20,
                "std_dev": 2,
                "rsi_threshold": 30
            }
        },
        {
            "name": "momentum_breakout",
            "display_name": "Momentum Breakout",
            "description": "Trades breakouts with volume confirmation",
            "complexity": "advanced",
            "parameters": {
                "breakout_pct": 2,
                "volume_threshold": 1.5,
                "confirmation_candles": 2
            }
        },
        {
            "name": "multi_timeframe_trend",
            "display_name": "Multi-Timeframe Trend",
            "description": "Confirms trend across multiple timeframes",
            "complexity": "expert",
            "parameters": {
                "timeframes": ["1d", "1h", "15m"],
                "ema_periods": [50, 20, 9]
            }
        }
    ]
    
    return {
        "status": "success",
        "data": strategies
    }

# Training scenarios endpoints
@app.get("/api/scenarios")
async def get_training_scenarios():
    """Get available training scenarios"""
    scenarios = [
        {
            "id": "bull_market_basics",
            "name": "Bull Market Basics",
            "description": "Learn trend-following in strong uptrends",
            "difficulty": "beginner",
            "period": "2023-01 to 2023-06",
            "objectives": [
                "Identify trend direction",
                "Time entries and exits",
                "Manage position sizing"
            ],
            "success_criteria": {
                "min_return": 15,
                "max_drawdown": 10
            }
        },
        {
            "id": "volatile_market_mastery",
            "name": "Volatile Market Mastery",
            "description": "Navigate high-volatility conditions",
            "difficulty": "intermediate",
            "period": "2022-01 to 2022-12",
            "objectives": [
                "Risk management",
                "Position sizing",
                "Stop-loss placement"
            ],
            "success_criteria": {
                "sharpe_ratio": 1.2,
                "max_drawdown": 15
            }
        },
        {
            "id": "bear_market_survival",
            "name": "Bear Market Survival",
            "description": "Capital preservation in downtrends",
            "difficulty": "expert",
            "period": "2008-09 to 2009-03",
            "objectives": [
                "Defensive positioning",
                "Short opportunities",
                "Capital preservation"
            ],
            "success_criteria": {
                "outperform_spy": 10,
                "max_drawdown": 20
            }
        }
    ]
    
    return {
        "status": "success",
        "data": scenarios
    }

@app.post("/api/scenarios/start")
async def start_training_scenario(request: TrainingScenarioRequest):
    """Start a training scenario session"""
    try:
        # This would initialize a guided training session
        # For now, return scenario details
        return {
            "status": "success",
            "data": {
                "scenario": request.scenario,
                "symbol": request.symbol,
                "session_id": f"training_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "message": "Training scenario initialized"
            }
        }
    
    except Exception as e:
        logger.error(f"Training scenario error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Learning insights endpoints
@app.get("/api/insights/recent")
async def get_recent_insights(limit: int = 10):
    """Get recent learning insights"""
    try:
        conn = sqlite3.connect(training_db.db_path)
        cursor = conn.execute("""
            SELECT * FROM learning_insights
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
        
        return {
            "status": "success",
            "data": results
        }
    
    except Exception as e:
        logger.error(f"Error fetching insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket endpoint for real-time collaboration
@app.websocket("/ws/collaborate/{symbol}")
async def websocket_collaborate(websocket: WebSocket, symbol: str):
    """WebSocket endpoint for real-time collaborative trading"""
    await manager.connect(websocket)
    
    try:
        # Send initial market data
        data = yf.download(
            symbol,
            start=(datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d'),
            end=datetime.now().strftime('%Y-%m-%d'),
            progress=False
        )
        
        if not data.empty:
            analysis = collaborative_engine.analyze_market(symbol, data)
            await websocket.send_json({
                "type": "market_analysis",
                "data": analysis
            })
        
        # Listen for messages
        while True:
            message = await websocket.receive_text()
            data = json.loads(message)
            
            if data.get("type") == "decision":
                # Process collaborative decision
                response = await make_collaborative_decision(
                    CollaborativeDecisionRequest(
                        symbol=symbol,
                        human_decision=data.get("decision"),
                        human_reasoning=data.get("reasoning"),
                        confidence=data.get("confidence", 50)
                    )
                )
                
                await websocket.send_json({
                    "type": "decision_result",
                    "data": response["data"]
                })
                
                # Broadcast to other connected clients
                await manager.broadcast(json.dumps({
                    "type": "new_decision",
                    "symbol": symbol,
                    "decision": response["data"]["final_decision"]
                }))
            
            elif data.get("type") == "refresh":
                # Send updated market data
                fresh_data = yf.download(
                    symbol,
                    start=(datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d'),
                    end=datetime.now().strftime('%Y-%m-%d'),
                    progress=False
                )
                
                if not fresh_data.empty:
                    analysis = collaborative_engine.analyze_market(symbol, fresh_data)
                    await websocket.send_json({
                        "type": "market_analysis",
                        "data": analysis
                    })
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info(f"WebSocket disconnected for {symbol}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

# Performance metrics endpoint
@app.get("/api/metrics/performance")
async def get_performance_metrics(days: int = 30):
    """Get overall performance metrics"""
    try:
        conn = sqlite3.connect(training_db.db_path)
        
        # Get backtest performance
        cursor = conn.execute("""
            SELECT 
                COUNT(*) as total_backtests,
                AVG(total_return) as avg_return,
                MAX(total_return) as best_return,
                MIN(total_return) as worst_return,
                AVG(sharpe_ratio) as avg_sharpe,
                AVG(win_rate) as avg_win_rate
            FROM backtests
            WHERE created_at >= datetime('now', '-{} days')
        """.format(days))
        
        backtest_metrics = dict(zip([desc[0] for desc in cursor.description], cursor.fetchone()))
        
        # Get collaborative decision performance
        cursor = conn.execute("""
            SELECT 
                COUNT(*) as total_decisions,
                AVG(human_confidence) as avg_human_confidence,
                AVG(ai_confidence) as avg_ai_confidence
            FROM collaborative_decisions
            WHERE timestamp >= datetime('now', '-{} days')
        """.format(days))
        
        decision_metrics = dict(zip([desc[0] for desc in cursor.description], cursor.fetchone()))
        
        conn.close()
        
        return {
            "status": "success",
            "data": {
                "period_days": days,
                "backtests": backtest_metrics,
                "decisions": decision_metrics
            }
        }
    
    except Exception as e:
        logger.error(f"Error fetching performance metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 9011))
    uvicorn.run(app, host="0.0.0.0", port=port)