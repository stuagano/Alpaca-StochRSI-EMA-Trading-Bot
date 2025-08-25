#!/usr/bin/env python3
"""
Analytics Service

Provides portfolio analytics, performance metrics, and risk analysis.
Analyzes trading performance and generates insights for optimization.

Features:
- Portfolio performance analysis
- Risk metrics calculation
- Trading strategy performance
- Historical analysis and reporting
- Real-time analytics dashboard data
"""

import os
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager
import pandas as pd
import numpy as np

import structlog
from fastapi import FastAPI, HTTPException, Depends, status, Query
from fastapi.middleware.cors import CORSMiddleware
import httpx
from pydantic import BaseModel, Field
import redis.asyncio as redis

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
POSITION_SERVICE_URL = os.getenv("POSITION_SERVICE_URL", "http://position-management:8001")
MARKET_DATA_SERVICE_URL = os.getenv("MARKET_DATA_SERVICE_URL", "http://market-data:8005")

# Redis client
redis_client = None

# Data Models
class PerformanceMetrics(BaseModel):
    total_return: float = Field(..., description="Total portfolio return")
    annualized_return: float = Field(..., description="Annualized return")
    volatility: float = Field(..., description="Portfolio volatility")
    sharpe_ratio: float = Field(..., description="Sharpe ratio")
    max_drawdown: float = Field(..., description="Maximum drawdown")
    win_rate: float = Field(..., description="Win rate percentage")
    profit_factor: float = Field(..., description="Profit factor")
    avg_win: float = Field(..., description="Average winning trade")
    avg_loss: float = Field(..., description="Average losing trade")
    total_trades: int = Field(..., description="Total number of trades")

class RiskMetrics(BaseModel):
    var_daily: float = Field(..., description="Daily Value at Risk (95%)")
    var_weekly: float = Field(..., description="Weekly Value at Risk (95%)")
    expected_shortfall: float = Field(..., description="Expected shortfall")
    beta: float = Field(..., description="Portfolio beta")
    tracking_error: float = Field(..., description="Tracking error")
    information_ratio: float = Field(..., description="Information ratio")
    risk_score: float = Field(..., description="Overall risk score (0-100)")

class PortfolioSnapshot(BaseModel):
    timestamp: datetime
    total_value: float
    cash: float
    equity: float
    day_pnl: float
    total_pnl: float
    positions_count: int
    leverage: float

class TradeAnalysis(BaseModel):
    symbol: str
    entry_date: datetime
    exit_date: Optional[datetime]
    entry_price: float
    exit_price: Optional[float]
    quantity: int
    pnl: float
    pnl_percent: float
    duration_hours: Optional[float]
    trade_type: str  # "win", "loss", "open"

class StrategyPerformance(BaseModel):
    strategy_name: str
    total_trades: int
    win_rate: float
    avg_return: float
    sharpe_ratio: float
    max_drawdown: float
    total_pnl: float

# Analytics Service
class AnalyticsService:
    """Core analytics service for portfolio performance analysis."""
    
    def __init__(self):
        self.cache_ttl = 300  # 5 minutes
        
    async def get_portfolio_performance(self, 
                                      start_date: Optional[datetime] = None,
                                      end_date: Optional[datetime] = None) -> PerformanceMetrics:
        """Calculate comprehensive portfolio performance metrics."""
        try:
            # Default to last 30 days if no dates provided
            if not end_date:
                end_date = datetime.utcnow()
            if not start_date:
                start_date = end_date - timedelta(days=30)
            
            # Get portfolio history
            portfolio_history = await self._get_portfolio_history(start_date, end_date)
            
            if not portfolio_history:
                raise ValueError("No portfolio data available for the specified period")
            
            # Convert to pandas DataFrame for analysis
            df = pd.DataFrame(portfolio_history)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp')
            
            # Calculate returns
            df['returns'] = df['total_value'].pct_change().fillna(0)
            
            # Performance calculations
            total_return = (df['total_value'].iloc[-1] / df['total_value'].iloc[0] - 1) * 100
            
            # Annualized return
            days = (end_date - start_date).days
            annualized_return = ((df['total_value'].iloc[-1] / df['total_value'].iloc[0]) ** (365.0 / max(days, 1)) - 1) * 100
            
            # Volatility (annualized)
            volatility = df['returns'].std() * np.sqrt(252) * 100
            
            # Sharpe ratio (assuming 2% risk-free rate)
            risk_free_rate = 0.02
            excess_returns = df['returns'].mean() * 252 - risk_free_rate
            sharpe_ratio = excess_returns / (volatility / 100) if volatility > 0 else 0
            
            # Maximum drawdown
            df['cumulative'] = (1 + df['returns']).cumprod()
            df['running_max'] = df['cumulative'].expanding().max()
            df['drawdown'] = (df['cumulative'] / df['running_max'] - 1) * 100
            max_drawdown = df['drawdown'].min()
            
            # Get trade statistics
            trade_stats = await self._get_trade_statistics(start_date, end_date)
            
            return PerformanceMetrics(
                total_return=total_return,
                annualized_return=annualized_return,
                volatility=volatility,
                sharpe_ratio=sharpe_ratio,
                max_drawdown=abs(max_drawdown),
                win_rate=trade_stats.get('win_rate', 0),
                profit_factor=trade_stats.get('profit_factor', 0),
                avg_win=trade_stats.get('avg_win', 0),
                avg_loss=trade_stats.get('avg_loss', 0),
                total_trades=trade_stats.get('total_trades', 0)
            )
            
        except Exception as e:
            logger.error("Error calculating portfolio performance", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to calculate performance metrics: {str(e)}"
            )
    
    async def get_risk_metrics(self) -> RiskMetrics:
        """Calculate risk metrics for the portfolio."""
        try:
            # Get current positions
            positions = await self._get_current_positions()
            
            # Get historical data for risk calculations
            portfolio_history = await self._get_portfolio_history(
                datetime.utcnow() - timedelta(days=90),
                datetime.utcnow()
            )
            
            if not portfolio_history:
                raise ValueError("Insufficient data for risk calculations")
            
            df = pd.DataFrame(portfolio_history)
            df['returns'] = df['total_value'].pct_change().fillna(0)
            
            # Value at Risk calculations (95% confidence)
            var_daily = np.percentile(df['returns'], 5) * 100
            var_weekly = var_daily * np.sqrt(5)
            
            # Expected Shortfall (Conditional VaR)
            var_threshold = np.percentile(df['returns'], 5)
            tail_returns = df['returns'][df['returns'] <= var_threshold]
            expected_shortfall = tail_returns.mean() * 100 if len(tail_returns) > 0 else 0
            
            # Beta calculation (vs SPY benchmark)
            beta = await self._calculate_beta(df['returns'])
            
            # Tracking error and information ratio
            benchmark_returns = await self._get_benchmark_returns()
            if benchmark_returns is not None:
                excess_returns = df['returns'] - benchmark_returns
                tracking_error = excess_returns.std() * np.sqrt(252) * 100
                information_ratio = (excess_returns.mean() * 252) / (tracking_error / 100) if tracking_error > 0 else 0
            else:
                tracking_error = 0
                information_ratio = 0
            
            # Overall risk score (0-100)
            risk_score = self._calculate_risk_score(var_daily, df['returns'].std(), len(positions))
            
            return RiskMetrics(
                var_daily=abs(var_daily),
                var_weekly=abs(var_weekly),
                expected_shortfall=abs(expected_shortfall),
                beta=beta,
                tracking_error=tracking_error,
                information_ratio=information_ratio,
                risk_score=risk_score
            )
            
        except Exception as e:
            logger.error("Error calculating risk metrics", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to calculate risk metrics: {str(e)}"
            )
    
    async def get_trade_analysis(self, 
                               start_date: Optional[datetime] = None,
                               end_date: Optional[datetime] = None,
                               symbol: Optional[str] = None) -> List[TradeAnalysis]:
        """Get detailed trade analysis."""
        try:
            # Get trade history from position service
            async with httpx.AsyncClient() as client:
                params = {}
                if start_date:
                    params['start_date'] = start_date.isoformat()
                if end_date:
                    params['end_date'] = end_date.isoformat()
                if symbol:
                    params['symbol'] = symbol
                
                response = await client.get(
                    f"{POSITION_SERVICE_URL}/trades/history",
                    params=params,
                    timeout=10.0
                )
                
                if response.status_code != 200:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail="Failed to fetch trade history"
                    )
                
                trades_data = response.json()
                
                trade_analyses = []
                for trade in trades_data.get('trades', []):
                    analysis = TradeAnalysis(
                        symbol=trade['symbol'],
                        entry_date=datetime.fromisoformat(trade['entry_date'].replace('Z', '+00:00')),
                        exit_date=datetime.fromisoformat(trade['exit_date'].replace('Z', '+00:00')) if trade.get('exit_date') else None,
                        entry_price=trade['entry_price'],
                        exit_price=trade.get('exit_price'),
                        quantity=trade['quantity'],
                        pnl=trade['pnl'],
                        pnl_percent=trade['pnl_percent'],
                        duration_hours=trade.get('duration_hours'),
                        trade_type=trade['trade_type']
                    )
                    trade_analyses.append(analysis)
                
                return trade_analyses
                
        except Exception as e:
            logger.error("Error getting trade analysis", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get trade analysis: {str(e)}"
            )
    
    async def get_strategy_performance(self) -> List[StrategyPerformance]:
        """Get performance metrics by trading strategy."""
        try:
            # This would integrate with strategy tracking
            # For now, return mock data for the main strategy
            return [
                StrategyPerformance(
                    strategy_name="StochRSI_EMA",
                    total_trades=50,
                    win_rate=65.0,
                    avg_return=2.3,
                    sharpe_ratio=1.45,
                    max_drawdown=8.2,
                    total_pnl=1250.75
                )
            ]
            
        except Exception as e:
            logger.error("Error getting strategy performance", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get strategy performance: {str(e)}"
            )
    
    # Helper methods
    async def _get_portfolio_history(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Get portfolio value history from position service."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{POSITION_SERVICE_URL}/portfolio/history",
                    params={
                        'start_date': start_date.isoformat(),
                        'end_date': end_date.isoformat()
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    return response.json().get('history', [])
                else:
                    logger.warning("Portfolio history not available, using mock data")
                    # Generate mock data for demonstration
                    return self._generate_mock_portfolio_history(start_date, end_date)
        except:
            logger.warning("Portfolio service unavailable, using mock data")
            return self._generate_mock_portfolio_history(start_date, end_date)
    
    async def _get_current_positions(self) -> List[Dict]:
        """Get current positions from position service."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{POSITION_SERVICE_URL}/positions", timeout=5.0)
                if response.status_code == 200:
                    return response.json().get('positions', [])
                return []
        except:
            return []
    
    async def _get_trade_statistics(self, start_date: datetime, end_date: datetime) -> Dict:
        """Get trade statistics for performance calculations."""
        try:
            trade_analyses = await self.get_trade_analysis(start_date, end_date)
            
            if not trade_analyses:
                return {
                    'win_rate': 0, 'profit_factor': 0, 'avg_win': 0, 
                    'avg_loss': 0, 'total_trades': 0
                }
            
            wins = [t for t in trade_analyses if t.pnl > 0]
            losses = [t for t in trade_analyses if t.pnl < 0]
            
            win_rate = (len(wins) / len(trade_analyses)) * 100 if trade_analyses else 0
            avg_win = sum(t.pnl for t in wins) / len(wins) if wins else 0
            avg_loss = abs(sum(t.pnl for t in losses) / len(losses)) if losses else 0
            profit_factor = avg_win / avg_loss if avg_loss > 0 else 0
            
            return {
                'win_rate': win_rate,
                'profit_factor': profit_factor,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'total_trades': len(trade_analyses)
            }
        except:
            return {'win_rate': 0, 'profit_factor': 0, 'avg_win': 0, 'avg_loss': 0, 'total_trades': 0}
    
    async def _calculate_beta(self, returns: pd.Series) -> float:
        """Calculate portfolio beta vs market."""
        try:
            # This would typically use SPY returns as benchmark
            # For now, return a default beta
            return 1.0
        except:
            return 1.0
    
    async def _get_benchmark_returns(self) -> Optional[pd.Series]:
        """Get benchmark returns for comparison."""
        # This would fetch benchmark data (e.g., SPY)
        return None
    
    def _calculate_risk_score(self, var_daily: float, volatility: float, position_count: int) -> float:
        """Calculate overall risk score (0-100)."""
        # Simple risk scoring based on VaR, volatility, and diversification
        var_score = min(abs(var_daily) * 100, 50)  # Cap at 50
        vol_score = min(volatility * 100, 30)      # Cap at 30
        diversification_score = max(20 - position_count, 0)  # Less diversification = higher risk
        
        risk_score = var_score + vol_score + diversification_score
        return min(risk_score, 100)
    
    def _generate_mock_portfolio_history(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Generate mock portfolio history for demonstration."""
        history = []
        current_date = start_date
        current_value = 10000.0
        
        while current_date <= end_date:
            # Simulate portfolio growth with some volatility
            daily_return = np.random.normal(0.0005, 0.02)  # 0.05% daily return with 2% volatility
            current_value *= (1 + daily_return)
            
            history.append({
                'timestamp': current_date.isoformat(),
                'total_value': current_value,
                'cash': current_value * 0.1,  # 10% cash
                'equity': current_value * 0.9,  # 90% equity
                'day_pnl': current_value * daily_return,
                'total_pnl': current_value - 10000.0
            })
            
            current_date += timedelta(days=1)
        
        return history

# Global service instance
analytics_service = AnalyticsService()

# Application lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global redis_client
    
    try:
        # Initialize Redis connection
        redis_client = redis.from_url(REDIS_URL)
        await redis_client.ping()
        logger.info("✅ Analytics Service started successfully")
        yield
    except Exception as e:
        logger.error("❌ Failed to start Analytics Service", error=str(e))
        yield
    finally:
        if redis_client:
            await redis_client.close()
        logger.info("🔌 Analytics Service shutdown complete")

# FastAPI application
app = FastAPI(
    title="Analytics Service",
    description="Portfolio analytics and performance metrics",
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
        "service": "analytics",
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "redis_connected": redis_connected
    }

@app.get("/performance", response_model=PerformanceMetrics)
async def get_performance_metrics(
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)")
):
    """Get comprehensive portfolio performance metrics."""
    start_dt = None
    end_dt = None
    
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        except:
            raise HTTPException(status_code=400, detail="Invalid start_date format")
    
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        except:
            raise HTTPException(status_code=400, detail="Invalid end_date format")
    
    return await analytics_service.get_portfolio_performance(start_dt, end_dt)

@app.get("/risk", response_model=RiskMetrics)
async def get_risk_metrics():
    """Get portfolio risk metrics."""
    return await analytics_service.get_risk_metrics()

@app.get("/trades", response_model=List[TradeAnalysis])
async def get_trade_analysis(
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    symbol: Optional[str] = Query(None, description="Filter by symbol")
):
    """Get detailed trade analysis."""
    start_dt = None
    end_dt = None
    
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        except:
            raise HTTPException(status_code=400, detail="Invalid start_date format")
    
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        except:
            raise HTTPException(status_code=400, detail="Invalid end_date format")
    
    return await analytics_service.get_trade_analysis(start_dt, end_dt, symbol)

@app.get("/strategies", response_model=List[StrategyPerformance])
async def get_strategy_performance():
    """Get performance metrics by trading strategy."""
    return await analytics_service.get_strategy_performance()

@app.get("/dashboard")
async def get_dashboard_data():
    """Get combined data for analytics dashboard."""
    try:
        # Get all metrics in parallel
        performance_task = analytics_service.get_portfolio_performance()
        risk_task = analytics_service.get_risk_metrics()
        trades_task = analytics_service.get_trade_analysis()
        
        performance, risk, trades = await asyncio.gather(
            performance_task, risk_task, trades_task,
            return_exceptions=True
        )
        
        return {
            "performance": performance if not isinstance(performance, Exception) else None,
            "risk": risk if not isinstance(risk, Exception) else None,
            "recent_trades": trades[:10] if not isinstance(trades, Exception) else [],
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error("Error getting dashboard data", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get dashboard data"
        )

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=9007,
        reload=True
    )