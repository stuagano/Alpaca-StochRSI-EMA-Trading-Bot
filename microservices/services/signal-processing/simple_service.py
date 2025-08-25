#!/usr/bin/env python3
"""
Signal Processing Service
Trading signals and technical indicators
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import uvicorn
import math
import random
from typing import Dict, List

app = FastAPI(title="Signal Processing Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock technical indicators
def calculate_rsi(symbol: str) -> float:
    """Mock RSI calculation"""
    # Simulate RSI between 20-80 with some bias
    base_rsi = random.uniform(30, 70)
    if symbol in ["AAPL", "MSFT"]:  # Make these more oversold/overbought
        return random.uniform(20, 80)
    return base_rsi

def calculate_macd(symbol: str) -> Dict:
    """Mock MACD calculation"""
    macd_line = random.uniform(-2, 2)
    signal_line = macd_line + random.uniform(-0.5, 0.5)
    histogram = macd_line - signal_line
    
    return {
        "macd": round(macd_line, 4),
        "signal": round(signal_line, 4),
        "histogram": round(histogram, 4)
    }

def calculate_stoch_rsi(symbol: str) -> Dict:
    """Mock Stochastic RSI calculation"""
    k_value = random.uniform(20, 80)
    d_value = k_value + random.uniform(-5, 5)
    d_value = max(0, min(100, d_value))  # Clamp between 0-100
    
    return {
        "k": round(k_value, 2),
        "d": round(d_value, 2),
        "signal": "BUY" if k_value < 20 else "SELL" if k_value > 80 else "NEUTRAL"
    }

def calculate_ema(symbol: str, period: int) -> float:
    """Mock EMA calculation"""
    # Base price around current market levels
    base_prices = {
        "AAPL": 175, "MSFT": 420, "GOOGL": 140, "TSLA": 250,
        "NVDA": 880, "AMD": 145, "NFLX": 485, "META": 320
    }
    base_price = base_prices.get(symbol, 100)
    
    # Add some variation based on period
    variation = random.uniform(-0.02, 0.02) * (period / 10)
    return round(base_price * (1 + variation), 2)

def generate_trade_signal(symbol: str) -> Dict:
    """Generate comprehensive trade signal"""
    rsi = calculate_rsi(symbol)
    macd = calculate_macd(symbol)
    stoch_rsi = calculate_stoch_rsi(symbol)
    ema_20 = calculate_ema(symbol, 20)
    ema_50 = calculate_ema(symbol, 50)
    
    # Determine overall signal strength
    signals = []
    
    # RSI signals
    if rsi < 30:
        signals.append(("RSI", "BUY", 0.7))
    elif rsi > 70:
        signals.append(("RSI", "SELL", 0.7))
    else:
        signals.append(("RSI", "NEUTRAL", 0.3))
    
    # MACD signals
    if macd["macd"] > macd["signal"] and macd["histogram"] > 0:
        signals.append(("MACD", "BUY", 0.6))
    elif macd["macd"] < macd["signal"] and macd["histogram"] < 0:
        signals.append(("MACD", "SELL", 0.6))
    else:
        signals.append(("MACD", "NEUTRAL", 0.3))
    
    # Stochastic RSI
    signals.append(("StochRSI", stoch_rsi["signal"], 0.8))
    
    # EMA cross
    if ema_20 > ema_50:
        signals.append(("EMA", "BUY", 0.5))
    else:
        signals.append(("EMA", "SELL", 0.5))
    
    # Volume confirmation (mock)
    volume_signal = random.choice(["HIGH", "NORMAL", "LOW"])
    volume_weight = 0.7 if volume_signal == "HIGH" else 0.5
    signals.append(("Volume", "CONFIRM" if volume_signal == "HIGH" else "WEAK", volume_weight))
    
    # Calculate overall signal
    buy_score = sum(weight for _, signal, weight in signals if signal == "BUY")
    sell_score = sum(weight for _, signal, weight in signals if signal == "SELL")
    
    if buy_score > sell_score + 0.5:
        overall_signal = "STRONG_BUY" if buy_score > 2.5 else "BUY"
        confidence = min(95, int(buy_score / 3.5 * 100))
    elif sell_score > buy_score + 0.5:
        overall_signal = "STRONG_SELL" if sell_score > 2.5 else "SELL"
        confidence = min(95, int(sell_score / 3.5 * 100))
    else:
        overall_signal = "HOLD"
        confidence = random.randint(40, 60)
    
    return {
        "symbol": symbol,
        "signal": overall_signal,
        "confidence": confidence,
        "indicators": {
            "rsi": {
                "value": round(rsi, 2),
                "signal": "BUY" if rsi < 30 else "SELL" if rsi > 70 else "NEUTRAL"
            },
            "macd": macd,
            "stoch_rsi": stoch_rsi,
            "ema": {
                "ema_20": ema_20,
                "ema_50": ema_50,
                "cross": "BULLISH" if ema_20 > ema_50 else "BEARISH"
            },
            "volume": {
                "signal": volume_signal,
                "weight": volume_weight
            }
        },
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health")
async def health_check():
    return {
        "service": "signal-processing",
        "status": "healthy", 
        "timestamp": datetime.utcnow().isoformat(),
        "indicators_available": ["RSI", "MACD", "StochRSI", "EMA", "Volume"]
    }

@app.get("/signals/{symbol}")
async def get_signal(symbol: str):
    """Get trading signal for a specific symbol"""
    symbol = symbol.upper()
    return generate_trade_signal(symbol)

@app.get("/signals")
async def get_all_signals():
    """Get trading signals for all major symbols"""
    symbols = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA", "AMD", "NFLX", "META"]
    signals = {}
    
    for symbol in symbols:
        signals[symbol] = generate_trade_signal(symbol)
    
    return {
        "signals": signals,
        "count": len(signals),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/indicators/{symbol}")
async def get_indicators(symbol: str):
    """Get detailed technical indicators for a symbol"""
    symbol = symbol.upper()
    
    return {
        "symbol": symbol,
        "rsi": {
            "current": round(calculate_rsi(symbol), 2),
            "overbought": 70,
            "oversold": 30
        },
        "macd": calculate_macd(symbol),
        "stochastic_rsi": calculate_stoch_rsi(symbol),
        "moving_averages": {
            "ema_5": calculate_ema(symbol, 5),
            "ema_10": calculate_ema(symbol, 10),
            "ema_20": calculate_ema(symbol, 20),
            "ema_50": calculate_ema(symbol, 50),
            "ema_200": calculate_ema(symbol, 200)
        },
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/screener")
async def market_screener():
    """Market screener with filtered signals"""
    symbols = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA", "AMD", "NFLX", "META", 
               "AMZN", "CRM", "ORCL", "INTC", "QCOM", "ADBE", "PYPL", "SPOT"]
    
    strong_buys = []
    strong_sells = []
    oversold = []
    overbought = []
    
    for symbol in symbols:
        signal_data = generate_trade_signal(symbol)
        rsi = signal_data["indicators"]["rsi"]["value"]
        
        if signal_data["signal"] == "STRONG_BUY":
            strong_buys.append(signal_data)
        elif signal_data["signal"] == "STRONG_SELL":
            strong_sells.append(signal_data)
        
        if rsi < 30:
            oversold.append({
                "symbol": symbol,
                "rsi": rsi,
                "signal": signal_data["signal"]
            })
        elif rsi > 70:
            overbought.append({
                "symbol": symbol,
                "rsi": rsi,
                "signal": signal_data["signal"]
            })
    
    return {
        "strong_buys": strong_buys,
        "strong_sells": strong_sells,
        "oversold": oversold,
        "overbought": overbought,
        "scan_time": datetime.utcnow().isoformat()
    }

@app.get("/alerts")
async def get_alerts():
    """Get active trading alerts"""
    alerts = []
    symbols = ["AAPL", "MSFT", "GOOGL", "TSLA"]
    
    for symbol in symbols:
        rsi = calculate_rsi(symbol)
        if rsi < 25 or rsi > 75:
            alerts.append({
                "symbol": symbol,
                "type": "RSI_EXTREME",
                "message": f"{symbol} RSI at {rsi:.1f} - {'Oversold' if rsi < 25 else 'Overbought'}",
                "severity": "HIGH",
                "timestamp": datetime.utcnow().isoformat()
            })
    
    # Add some mock alerts
    if random.random() < 0.3:  # 30% chance
        alerts.append({
            "symbol": "AAPL",
            "type": "VOLUME_SPIKE",
            "message": "AAPL volume 150% above average",
            "severity": "MEDIUM",
            "timestamp": datetime.utcnow().isoformat()
        })
    
    return {
        "alerts": alerts,
        "count": len(alerts),
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    uvicorn.run("simple_service:app", host="127.0.0.1", port=9003, reload=True)