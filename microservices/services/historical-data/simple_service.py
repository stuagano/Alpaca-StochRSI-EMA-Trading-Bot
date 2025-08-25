#!/usr/bin/env python3
"""
Historical Data Service
Provides historical price data, backtesting, and performance analysis
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import uvicorn
import random
import math
from typing import Dict, List, Optional
from pydantic import BaseModel

app = FastAPI(title="Historical Data Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data models
class HistoricalBar(BaseModel):
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: int

class BacktestRequest(BaseModel):
    symbol: str
    start_date: str
    end_date: str
    initial_capital: float = 100000.0
    strategy: str = "moving_average"  # simple, moving_average, momentum

class BacktestResult(BaseModel):
    symbol: str
    start_date: str
    end_date: str
    initial_capital: float
    final_capital: float
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    total_trades: int
    profitable_trades: int

# Mock symbols with realistic starting prices
SYMBOL_BASE_PRICES = {
    "AAPL": 178.25,
    "MSFT": 416.75,
    "GOOGL": 142.80,
    "TSLA": 245.67,
    "SPY": 551.23,
    "QQQ": 486.91,
    "AMZN": 172.84,
    "NVDA": 875.30,
    "META": 498.73,
    "NFLX": 487.12
}

def generate_historical_data(symbol: str, days: int = 252) -> List[Dict]:
    """Generate realistic historical price data"""
    base_price = SYMBOL_BASE_PRICES.get(symbol, 100.0)
    data = []
    current_price = base_price
    
    # Start from the specified number of days ago
    start_date = datetime.utcnow() - timedelta(days=days)
    
    for i in range(days):
        date = start_date + timedelta(days=i)
        
        # Random walk with slight upward bias
        daily_return = random.gauss(0.0008, 0.02)  # ~0.08% avg daily return, 2% volatility
        
        # Weekend effect - lower volatility on weekends
        if date.weekday() >= 5:  # Weekend
            daily_return *= 0.5
        
        current_price *= (1 + daily_return)
        
        # Generate OHLC data
        open_price = current_price
        high = open_price * (1 + abs(random.gauss(0, 0.005)))
        low = open_price * (1 - abs(random.gauss(0, 0.005)))
        close = open_price * (1 + random.gauss(0, 0.01))
        
        # Ensure high is highest and low is lowest
        high = max(high, open_price, close)
        low = min(low, open_price, close)
        
        volume = random.randint(1000000, 10000000)  # Random volume
        
        current_price = close
        
        data.append({
            "timestamp": date.isoformat(),
            "open": round(open_price, 2),
            "high": round(high, 2),
            "low": round(low, 2),
            "close": round(close, 2),
            "volume": volume
        })
    
    return data

def run_simple_backtest(symbol: str, historical_data: List[Dict], initial_capital: float, strategy: str) -> BacktestResult:
    """Run a simple backtest simulation"""
    
    trades = []
    capital = initial_capital
    position = 0  # 0 = no position, 1 = long, -1 = short
    entry_price = 0
    
    if strategy == "moving_average":
        # Simple moving average crossover
        ma_short = 10
        ma_long = 20
        
        prices = [bar["close"] for bar in historical_data]
        
        for i in range(ma_long, len(prices)):
            # Calculate moving averages
            short_ma = sum(prices[i-ma_short:i]) / ma_short
            long_ma = sum(prices[i-ma_long:i]) / ma_long
            
            current_price = prices[i]
            
            # Buy signal: short MA crosses above long MA
            if position == 0 and short_ma > long_ma and prices[i-1] <= sum(prices[i-ma_long-1:i-1]) / ma_long:
                position = 1
                entry_price = current_price
                shares = int(capital * 0.95 / current_price)  # Use 95% of capital
                capital -= shares * current_price
                
                trades.append({
                    "type": "BUY",
                    "price": current_price,
                    "shares": shares,
                    "date": historical_data[i]["timestamp"]
                })
            
            # Sell signal: short MA crosses below long MA
            elif position == 1 and short_ma < long_ma:
                position = 0
                shares = trades[-1]["shares"] if trades else 0
                capital += shares * current_price
                
                if trades:
                    profit = shares * (current_price - entry_price)
                    trades.append({
                        "type": "SELL",
                        "price": current_price,
                        "shares": shares,
                        "profit": profit,
                        "date": historical_data[i]["timestamp"]
                    })
    
    elif strategy == "momentum":
        # Simple momentum strategy
        lookback = 10
        prices = [bar["close"] for bar in historical_data]
        
        for i in range(lookback, len(prices)):
            momentum = (prices[i] - prices[i-lookback]) / prices[i-lookback]
            current_price = prices[i]
            
            # Buy on positive momentum
            if position == 0 and momentum > 0.05:  # 5% momentum
                position = 1
                entry_price = current_price
                shares = int(capital * 0.95 / current_price)
                capital -= shares * current_price
                
                trades.append({
                    "type": "BUY",
                    "price": current_price,
                    "shares": shares,
                    "date": historical_data[i]["timestamp"]
                })
            
            # Sell on negative momentum
            elif position == 1 and momentum < -0.03:  # -3% momentum
                position = 0
                shares = trades[-1]["shares"] if trades else 0
                capital += shares * current_price
                
                if trades:
                    profit = shares * (current_price - entry_price)
                    trades.append({
                        "type": "SELL",
                        "price": current_price,
                        "shares": shares,
                        "profit": profit,
                        "date": historical_data[i]["timestamp"]
                    })
    
    # Calculate performance metrics
    if position == 1 and trades:  # Close any open position
        shares = trades[-1]["shares"]
        final_price = historical_data[-1]["close"]
        capital += shares * final_price
        profit = shares * (final_price - entry_price)
        trades.append({
            "type": "SELL",
            "price": final_price,
            "shares": shares,
            "profit": profit,
            "date": historical_data[-1]["timestamp"]
        })
    
    final_capital = capital
    total_return = (final_capital - initial_capital) / initial_capital * 100
    
    # Calculate additional metrics
    profitable_trades = len([t for t in trades if t.get("profit", 0) > 0])
    total_trades = len([t for t in trades if t["type"] == "SELL"])
    win_rate = (profitable_trades / total_trades * 100) if total_trades > 0 else 0
    
    # Simple Sharpe ratio approximation
    if total_trades > 2:
        returns = [t.get("profit", 0) / initial_capital for t in trades if "profit" in t]
        avg_return = sum(returns) / len(returns) if returns else 0
        return_std = math.sqrt(sum((r - avg_return) ** 2 for r in returns) / len(returns)) if returns else 1
        sharpe_ratio = (avg_return / return_std * math.sqrt(252)) if return_std > 0 else 0
    else:
        sharpe_ratio = 0
    
    # Simple max drawdown calculation
    peak = initial_capital
    max_drawdown = 0
    running_capital = initial_capital
    
    for trade in trades:
        if trade["type"] == "SELL" and "profit" in trade:
            running_capital += trade["profit"]
            if running_capital > peak:
                peak = running_capital
            else:
                drawdown = (peak - running_capital) / peak * 100
                max_drawdown = max(max_drawdown, drawdown)
    
    return BacktestResult(
        symbol=symbol,
        start_date=historical_data[0]["timestamp"],
        end_date=historical_data[-1]["timestamp"],
        initial_capital=initial_capital,
        final_capital=round(final_capital, 2),
        total_return=round(total_return, 2),
        sharpe_ratio=round(sharpe_ratio, 2),
        max_drawdown=round(max_drawdown, 2),
        win_rate=round(win_rate, 2),
        total_trades=total_trades,
        profitable_trades=profitable_trades
    )

@app.get("/health")
async def health_check():
    return {
        "service": "historical-data",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "data_sources": ["market_data", "price_history", "backtesting_engine"],
        "available_symbols": list(SYMBOL_BASE_PRICES.keys())
    }

@app.get("/historical/{symbol}")
async def get_historical_data(
    symbol: str,
    days: int = Query(default=30, ge=1, le=1000, description="Number of days of historical data")
):
    """Get historical price data for a symbol"""
    if symbol.upper() not in SYMBOL_BASE_PRICES:
        raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")
    
    try:
        data = generate_historical_data(symbol.upper(), days)
        
        return {
            "symbol": symbol.upper(),
            "days_requested": days,
            "bars_returned": len(data),
            "data": data[-days:],  # Return most recent data
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching historical data: {str(e)}")

@app.get("/ohlc/{symbol}")
async def get_ohlc_data(
    symbol: str,
    timeframe: str = Query(default="1D", description="Timeframe: 1D, 4H, 1H, 15M"),
    limit: int = Query(default=100, ge=1, le=1000)
):
    """Get OHLC data for charting"""
    if symbol.upper() not in SYMBOL_BASE_PRICES:
        raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")
    
    # Generate data based on timeframe
    if timeframe == "1D":
        days = limit
    elif timeframe == "4H":
        days = limit // 6  # 6 bars per day
    elif timeframe == "1H":
        days = limit // 24  # 24 bars per day
    else:  # 15M
        days = limit // 96  # 96 bars per day
    
    days = max(1, days)
    data = generate_historical_data(symbol.upper(), days)
    
    return {
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        "bars": data[-limit:],
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/backtest")
async def run_backtest(request: BacktestRequest):
    """Run a backtest simulation"""
    if request.symbol.upper() not in SYMBOL_BASE_PRICES:
        raise HTTPException(status_code=404, detail=f"Symbol {request.symbol} not found")
    
    try:
        # Parse dates and calculate days
        start_date = datetime.fromisoformat(request.start_date.replace('Z', '+00:00'))
        end_date = datetime.fromisoformat(request.end_date.replace('Z', '+00:00'))
        days = (end_date - start_date).days
        
        if days <= 0:
            raise HTTPException(status_code=400, detail="End date must be after start date")
        
        # Generate historical data for the period
        historical_data = generate_historical_data(request.symbol.upper(), days)
        
        # Run backtest
        result = run_simple_backtest(
            request.symbol.upper(), 
            historical_data, 
            request.initial_capital, 
            request.strategy
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backtest error: {str(e)}")

@app.get("/performance/{symbol}")
async def get_performance_metrics(
    symbol: str,
    days: int = Query(default=252, description="Period for performance calculation")
):
    """Get performance metrics for a symbol"""
    if symbol.upper() not in SYMBOL_BASE_PRICES:
        raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")
    
    try:
        data = generate_historical_data(symbol.upper(), days)
        prices = [bar["close"] for bar in data]
        
        # Calculate returns
        returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
        
        # Performance metrics
        total_return = (prices[-1] - prices[0]) / prices[0] * 100
        volatility = math.sqrt(sum(r**2 for r in returns) / len(returns)) * math.sqrt(252) * 100
        
        # Sharpe ratio (assuming 2% risk-free rate)
        avg_return = sum(returns) / len(returns) * 252
        excess_return = avg_return - 0.02
        return_std = math.sqrt(sum((r - sum(returns)/len(returns))**2 for r in returns) / len(returns)) * math.sqrt(252)
        sharpe = excess_return / return_std if return_std > 0 else 0
        
        # Max drawdown
        peak = prices[0]
        max_drawdown = 0
        for price in prices:
            if price > peak:
                peak = price
            else:
                drawdown = (peak - price) / peak * 100
                max_drawdown = max(max_drawdown, drawdown)
        
        return {
            "symbol": symbol.upper(),
            "period_days": days,
            "total_return_pct": round(total_return, 2),
            "annualized_volatility_pct": round(volatility, 2),
            "sharpe_ratio": round(sharpe, 2),
            "max_drawdown_pct": round(max_drawdown, 2),
            "current_price": round(prices[-1], 2),
            "period_high": round(max(prices), 2),
            "period_low": round(min(prices), 2),
            "average_volume": sum(bar["volume"] for bar in data) // len(data),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating performance: {str(e)}")

@app.get("/correlation")
async def get_correlation_matrix(
    symbols: str = Query(description="Comma-separated symbols", default="AAPL,MSFT,GOOGL"),
    days: int = Query(default=252, description="Period for correlation calculation")
):
    """Calculate correlation matrix between symbols"""
    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    
    # Validate symbols
    invalid_symbols = [s for s in symbol_list if s not in SYMBOL_BASE_PRICES]
    if invalid_symbols:
        raise HTTPException(status_code=400, detail=f"Invalid symbols: {invalid_symbols}")
    
    try:
        # Get historical data for all symbols
        symbol_data = {}
        for symbol in symbol_list:
            data = generate_historical_data(symbol, days)
            symbol_data[symbol] = [bar["close"] for bar in data]
        
        # Calculate correlations
        correlations = {}
        for i, symbol1 in enumerate(symbol_list):
            correlations[symbol1] = {}
            for symbol2 in symbol_list:
                if symbol1 == symbol2:
                    correlation = 1.0
                else:
                    # Calculate correlation coefficient
                    prices1 = symbol_data[symbol1]
                    prices2 = symbol_data[symbol2]
                    
                    returns1 = [(prices1[j] - prices1[j-1]) / prices1[j-1] for j in range(1, len(prices1))]
                    returns2 = [(prices2[j] - prices2[j-1]) / prices2[j-1] for j in range(1, len(prices2))]
                    
                    mean1 = sum(returns1) / len(returns1)
                    mean2 = sum(returns2) / len(returns2)
                    
                    numerator = sum((returns1[k] - mean1) * (returns2[k] - mean2) for k in range(len(returns1)))
                    denom1 = math.sqrt(sum((r - mean1)**2 for r in returns1))
                    denom2 = math.sqrt(sum((r - mean2)**2 for r in returns2))
                    
                    correlation = numerator / (denom1 * denom2) if denom1 > 0 and denom2 > 0 else 0
                
                correlations[symbol1][symbol2] = round(correlation, 3)
        
        return {
            "symbols": symbol_list,
            "period_days": days,
            "correlation_matrix": correlations,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating correlations: {str(e)}")

@app.get("/market-summary")
async def get_market_summary():
    """Get overall market summary and statistics"""
    try:
        market_data = {}
        
        # Generate data for major indices/symbols
        major_symbols = ["SPY", "QQQ", "AAPL", "MSFT", "GOOGL"]
        
        for symbol in major_symbols:
            data = generate_historical_data(symbol, 5)  # Last 5 days
            current = data[-1]["close"]
            previous = data[-2]["close"]
            change = ((current - previous) / previous) * 100
            
            market_data[symbol] = {
                "price": current,
                "change_pct": round(change, 2),
                "volume": data[-1]["volume"]
            }
        
        # Overall market sentiment
        avg_change = sum(data["change_pct"] for data in market_data.values()) / len(market_data)
        
        if avg_change > 1:
            sentiment = "BULLISH"
        elif avg_change < -1:
            sentiment = "BEARISH" 
        else:
            sentiment = "NEUTRAL"
        
        return {
            "market_data": market_data,
            "market_sentiment": sentiment,
            "average_change_pct": round(avg_change, 2),
            "trading_day": datetime.utcnow().strftime("%Y-%m-%d"),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting market summary: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("simple_service:app", host="127.0.0.1", port=9006, reload=True)