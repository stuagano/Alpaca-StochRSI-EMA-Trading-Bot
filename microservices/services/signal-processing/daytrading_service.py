#!/usr/bin/env python3
"""
High-Frequency Day Trading Signal Processing Service
Fast-moving patterns, scalping strategies, momentum trading
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import uvicorn
import math
import random
import asyncio
import json
from typing import Dict, List
from pydantic import BaseModel

app = FastAPI(title="Day Trading Signal Processing", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Day trading symbols - high volume, volatile stocks + crypto
DAYTRADING_SYMBOLS = [
    # High volume tech stocks
    "TSLA", "NVDA", "AMD", "PLTR", "SOFI", "RIVN", "LCID",
    # Volatile growth stocks  
    "COIN", "ROKU", "SNAP", "TWTR", "SQ", "PYPL", "SHOP",
    # Meme stocks with high movement
    "GME", "AMC", "BB", "NOK", "CLOV", "WISH", "SPCE",
    # High beta ETFs
    "SQQQ", "TQQQ", "SPXL", "SPXS", "TNA", "TZA", "UVXY",
    # Penny stocks (mock)
    "SNDL", "GGPI", "MULN", "PROG", "BBIG", "XELA"
]

# Crypto trading pairs - 24/7 market
CRYPTO_SYMBOLS = [
    # Major cryptocurrencies
    "BTC/USD", "ETH/USD", "BNB/USD", "XRP/USD", "ADA/USD",
    # High volatility altcoins
    "DOGE/USD", "SHIB/USD", "MATIC/USD", "DOT/USD", "LINK/USD",
    # DeFi tokens
    "UNI/USD", "AAVE/USD", "COMP/USD", "MKR/USD", "CRV/USD",
    # Layer 1 blockchains
    "SOL/USD", "AVAX/USD", "ATOM/USD", "NEAR/USD", "FTM/USD",
    # Meme coins and high volatility
    "PEPE/USD", "FLOKI/USD", "BONK/USD", "WIF/USD", "POPCAT/USD"
]

# Combined symbols for 24/7 trading
ALL_TRADING_SYMBOLS = DAYTRADING_SYMBOLS + CRYPTO_SYMBOLS

# Base prices for day trading symbols (more volatile ranges)
SYMBOL_PRICES = {
    # Stock prices
    "TSLA": random.uniform(180, 220), "NVDA": random.uniform(400, 500),
    "AMD": random.uniform(90, 120), "PLTR": random.uniform(8, 15),
    "SOFI": random.uniform(5, 8), "RIVN": random.uniform(15, 25),
    "LCID": random.uniform(3, 6), "COIN": random.uniform(45, 70),
    "ROKU": random.uniform(40, 60), "SNAP": random.uniform(8, 12),
    "SQ": random.uniform(60, 85), "PYPL": random.uniform(50, 65),
    "GME": random.uniform(15, 25), "AMC": random.uniform(3, 8),
    "SQQQ": random.uniform(25, 35), "TQQQ": random.uniform(30, 45),
    "SPXL": random.uniform(80, 120), "UVXY": random.uniform(8, 15),
    "SNDL": random.uniform(0.20, 0.50), "MULN": random.uniform(0.15, 0.40)
}

# Crypto base prices (24/7 markets)
CRYPTO_PRICES = {
    # Major crypto
    "BTC/USD": random.uniform(40000, 50000), "ETH/USD": random.uniform(2500, 3500),
    "BNB/USD": random.uniform(400, 600), "XRP/USD": random.uniform(0.45, 0.65),
    "ADA/USD": random.uniform(0.35, 0.55), "SOL/USD": random.uniform(80, 140),
    # Altcoins
    "DOGE/USD": random.uniform(0.07, 0.12), "SHIB/USD": random.uniform(0.000015, 0.000025),
    "MATIC/USD": random.uniform(0.85, 1.25), "DOT/USD": random.uniform(6, 9),
    "LINK/USD": random.uniform(12, 18), "UNI/USD": random.uniform(6, 10),
    # DeFi tokens
    "AAVE/USD": random.uniform(80, 120), "COMP/USD": random.uniform(45, 75),
    "MKR/USD": random.uniform(1200, 1800), "CRV/USD": random.uniform(0.4, 0.7),
    # Layer 1s
    "AVAX/USD": random.uniform(25, 40), "ATOM/USD": random.uniform(8, 12),
    "NEAR/USD": random.uniform(4, 7), "FTM/USD": random.uniform(0.5, 0.8),
    # Meme coins
    "PEPE/USD": random.uniform(0.00000150, 0.00000250), "FLOKI/USD": random.uniform(0.000150, 0.000250),
    "BONK/USD": random.uniform(0.000025, 0.000045), "WIF/USD": random.uniform(1.8, 2.8),
    "POPCAT/USD": random.uniform(0.85, 1.35)
}

# Combined prices
ALL_SYMBOL_PRICES = {**SYMBOL_PRICES, **CRYPTO_PRICES}

class TradeSignal(BaseModel):
    symbol: str
    signal: str  # BUY, SELL, STRONG_BUY, STRONG_SELL
    confidence: float
    timeframe: str  # 1m, 5m, 15m
    entry_price: float
    stop_loss: float
    take_profit: float
    reason: str
    urgency: str  # LOW, MEDIUM, HIGH, CRITICAL
    expected_move: float  # Expected % move

def calculate_fast_rsi(symbol: str, timeframe: str = "5m") -> float:
    """Fast RSI for day trading - more sensitive"""
    base_rsi = random.uniform(25, 75)
    
    # Add volatility based on symbol type
    if symbol in ["TSLA", "NVDA", "GME", "AMC"]:
        # High volatility stocks - more extreme RSI
        return random.choice([
            random.uniform(10, 25),  # Oversold
            random.uniform(75, 90),  # Overbought
            random.uniform(45, 55)   # Neutral
        ])
    elif symbol.startswith("SQ") or "X" in symbol:  # Leveraged ETFs
        return random.uniform(15, 85)
    else:
        return base_rsi

def calculate_momentum(symbol: str) -> Dict:
    """Calculate momentum indicators for day trading"""
    # Price change over last periods
    price_1m = random.uniform(-0.02, 0.02)  # 1 min change
    price_5m = random.uniform(-0.05, 0.05)  # 5 min change
    price_15m = random.uniform(-0.08, 0.08) # 15 min change
    
    # Volume surge detection
    volume_ratio = random.uniform(0.5, 3.0)  # Volume vs average
    
    # Volatility spike
    volatility = random.uniform(0.01, 0.15)
    
    return {
        "price_momentum_1m": round(price_1m * 100, 2),
        "price_momentum_5m": round(price_5m * 100, 2),
        "price_momentum_15m": round(price_15m * 100, 2),
        "volume_ratio": round(volume_ratio, 2),
        "volatility": round(volatility, 4),
        "momentum_score": round((abs(price_5m) + volume_ratio + volatility) * 10, 1)
    }

def calculate_scalping_signals(symbol: str) -> Dict:
    """High-frequency scalping signals"""
    current_price = SYMBOL_PRICES.get(symbol, random.uniform(10, 100))
    
    # Bollinger Band scalping
    bb_upper = current_price * 1.005  # 0.5% above
    bb_lower = current_price * 0.995  # 0.5% below
    
    # VWAP deviation
    vwap = current_price * random.uniform(0.998, 1.002)
    vwap_deviation = (current_price - vwap) / vwap
    
    # Order flow imbalance (mock)
    bid_ask_pressure = random.uniform(-1, 1)
    
    return {
        "bb_position": "UPPER" if current_price > bb_upper else "LOWER" if current_price < bb_lower else "MIDDLE",
        "vwap_deviation": round(vwap_deviation * 100, 3),
        "bid_ask_pressure": round(bid_ask_pressure, 2),
        "scalping_opportunity": abs(vwap_deviation) > 0.001 or abs(bid_ask_pressure) > 0.5
    }

def calculate_breakout_signals(symbol: str) -> Dict:
    """Breakout and breakdown signals"""
    current_price = SYMBOL_PRICES.get(symbol, random.uniform(10, 100))
    
    # Support/resistance levels
    resistance = current_price * random.uniform(1.01, 1.03)
    support = current_price * random.uniform(0.97, 0.99)
    
    # Distance to levels
    resistance_distance = (resistance - current_price) / current_price
    support_distance = (current_price - support) / current_price
    
    # Breakout probability
    breakout_probability = random.uniform(0, 1)
    
    return {
        "resistance_level": round(resistance, 2),
        "support_level": round(support, 2),
        "resistance_distance_pct": round(resistance_distance * 100, 2),
        "support_distance_pct": round(support_distance * 100, 2),
        "breakout_probability": round(breakout_probability, 2),
        "near_breakout": resistance_distance < 0.01 or support_distance < 0.01
    }

def generate_daytrading_signal(symbol: str) -> TradeSignal:
    """Generate high-frequency day trading signal"""
    current_price = SYMBOL_PRICES.get(symbol, random.uniform(10, 100))
    
    rsi = calculate_fast_rsi(symbol)
    momentum = calculate_momentum(symbol)
    scalping = calculate_scalping_signals(symbol)
    breakout = calculate_breakout_signals(symbol)
    
    # Determine signal based on multiple factors
    signal_strength = 0
    signal_reasons = []
    
    # RSI analysis
    if rsi < 20:
        signal_strength += 3
        signal_reasons.append("RSI Oversold")
    elif rsi > 80:
        signal_strength -= 3
        signal_reasons.append("RSI Overbought")
    
    # Momentum analysis
    if momentum["momentum_score"] > 20:
        if momentum["price_momentum_5m"] > 2:
            signal_strength += 2
            signal_reasons.append("Strong Upward Momentum")
        elif momentum["price_momentum_5m"] < -2:
            signal_strength -= 2
            signal_reasons.append("Strong Downward Momentum")
    
    # Volume surge
    if momentum["volume_ratio"] > 2:
        signal_strength += 1
        signal_reasons.append("Volume Surge")
    
    # Scalping opportunities
    if scalping["scalping_opportunity"]:
        if scalping["vwap_deviation"] > 0.1:
            signal_strength -= 1
            signal_reasons.append("Above VWAP")
        elif scalping["vwap_deviation"] < -0.1:
            signal_strength += 1
            signal_reasons.append("Below VWAP")
    
    # Breakout signals
    if breakout["near_breakout"] and breakout["breakout_probability"] > 0.7:
        if breakout["resistance_distance_pct"] < 1:
            signal_strength += 2
            signal_reasons.append("Breakout Imminent")
        elif breakout["support_distance_pct"] < 1:
            signal_strength -= 2
            signal_reasons.append("Breakdown Risk")
    
    # Determine final signal
    if signal_strength >= 4:
        signal_type = "STRONG_BUY"
        confidence = min(95, 70 + signal_strength * 2)
        urgency = "CRITICAL"
    elif signal_strength >= 2:
        signal_type = "BUY"
        confidence = min(85, 60 + signal_strength * 3)
        urgency = "HIGH"
    elif signal_strength <= -4:
        signal_type = "STRONG_SELL"
        confidence = min(95, 70 + abs(signal_strength) * 2)
        urgency = "CRITICAL"
    elif signal_strength <= -2:
        signal_type = "SELL"
        confidence = min(85, 60 + abs(signal_strength) * 3)
        urgency = "HIGH"
    else:
        signal_type = "HOLD"
        confidence = random.uniform(30, 50)
        urgency = "LOW"
    
    # Calculate targets for day trading
    if signal_type in ["BUY", "STRONG_BUY"]:
        stop_loss = current_price * 0.995  # 0.5% stop loss
        take_profit = current_price * 1.01  # 1% take profit
        expected_move = random.uniform(0.5, 2.0)
    elif signal_type in ["SELL", "STRONG_SELL"]:
        stop_loss = current_price * 1.005  # 0.5% stop loss
        take_profit = current_price * 0.99   # 1% take profit  
        expected_move = random.uniform(-2.0, -0.5)
    else:
        stop_loss = current_price * 0.99
        take_profit = current_price * 1.01
        expected_move = random.uniform(-0.5, 0.5)
    
    return TradeSignal(
        symbol=symbol,
        signal=signal_type,
        confidence=round(confidence, 1),
        timeframe="5m",
        entry_price=round(current_price, 2),
        stop_loss=round(stop_loss, 2),
        take_profit=round(take_profit, 2),
        reason=" | ".join(signal_reasons[:3]) or "Technical Analysis",
        urgency=urgency,
        expected_move=round(expected_move, 2)
    )

# WebSocket connections for real-time signals
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass

manager = ConnectionManager()

@app.get("/health")
async def health_check():
    return {
        "service": "daytrading-signals",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "trading_mode": "HIGH_FREQUENCY",
        "symbols_tracked": len(DAYTRADING_SYMBOLS),
        "signal_types": ["SCALPING", "MOMENTUM", "BREAKOUT", "MEAN_REVERSION"]
    }

@app.get("/signals")
async def get_all_signals():
    """Get signals for all day trading symbols"""
    signals = {}
    strong_signals = []
    
    for symbol in DAYTRADING_SYMBOLS[:15]:  # Top 15 for performance
        signal = generate_daytrading_signal(symbol)
        signals[symbol] = signal.dict()
        
        # Collect high-urgency signals
        if signal.urgency in ["HIGH", "CRITICAL"]:
            strong_signals.append(signal.dict())
    
    return {
        "signals": signals,
        "strong_signals": strong_signals,
        "count": len(signals),
        "high_priority_count": len(strong_signals),
        "timestamp": datetime.utcnow().isoformat(),
        "next_update": (datetime.utcnow() + timedelta(minutes=1)).isoformat()
    }

@app.get("/signals/{symbol}")
async def get_symbol_signal(symbol: str):
    """Get detailed signal for specific symbol"""
    if symbol.upper() not in DAYTRADING_SYMBOLS:
        # Add to tracking if not present
        DAYTRADING_SYMBOLS.append(symbol.upper())
        SYMBOL_PRICES[symbol.upper()] = random.uniform(5, 200)
    
    signal = generate_daytrading_signal(symbol.upper())
    momentum = calculate_momentum(symbol.upper())
    scalping = calculate_scalping_signals(symbol.upper())
    breakout = calculate_breakout_signals(symbol.upper())
    
    return {
        "signal": signal.dict(),
        "technical_analysis": {
            "rsi": calculate_fast_rsi(symbol.upper()),
            "momentum": momentum,
            "scalping": scalping,
            "breakout": breakout
        },
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/hot-signals")
async def get_hot_signals():
    """Get only the hottest, most urgent signals"""
    hot_signals = []
    
    for symbol in DAYTRADING_SYMBOLS:
        signal = generate_daytrading_signal(symbol)
        
        if (signal.urgency == "CRITICAL" or 
            (signal.urgency == "HIGH" and signal.confidence > 80)):
            hot_signals.append(signal.dict())
    
    # Sort by confidence and urgency
    hot_signals.sort(key=lambda x: (
        2 if x["urgency"] == "CRITICAL" else 1,
        x["confidence"]
    ), reverse=True)
    
    return {
        "hot_signals": hot_signals[:10],  # Top 10 hottest
        "total_opportunities": len(hot_signals),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/scalping-opportunities")
async def get_scalping_opportunities():
    """Get immediate scalping opportunities"""
    opportunities = []
    
    for symbol in DAYTRADING_SYMBOLS:
        scalping = calculate_scalping_signals(symbol)
        
        if scalping["scalping_opportunity"]:
            current_price = SYMBOL_PRICES.get(symbol, 100)
            
            opportunities.append({
                "symbol": symbol,
                "current_price": round(current_price, 2),
                "vwap_deviation": scalping["vwap_deviation"],
                "bid_ask_pressure": scalping["bid_ask_pressure"],
                "bb_position": scalping["bb_position"],
                "expected_profit": round(abs(scalping["vwap_deviation"]) * 100, 2),
                "time_horizon": "1-5 minutes"
            })
    
    # Sort by profit potential
    opportunities.sort(key=lambda x: x["expected_profit"], reverse=True)
    
    return {
        "scalping_opportunities": opportunities[:8],
        "total_count": len(opportunities),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.websocket("/ws/live-signals")
async def websocket_live_signals(websocket: WebSocket):
    """Real-time signal streaming"""
    await manager.connect(websocket)
    
    try:
        while True:
            # Generate signals for top symbols
            signals_update = []
            
            for symbol in DAYTRADING_SYMBOLS[:8]:  # Top 8 for real-time
                signal = generate_daytrading_signal(symbol)
                if signal.urgency in ["HIGH", "CRITICAL"]:
                    signals_update.append({
                        "type": "signal_update",
                        "symbol": symbol,
                        "signal": signal.signal,
                        "confidence": signal.confidence,
                        "urgency": signal.urgency,
                        "entry_price": signal.entry_price,
                        "expected_move": signal.expected_move,
                        "timestamp": datetime.utcnow().isoformat()
                    })
            
            if signals_update:
                await websocket.send_text(json.dumps({
                    "type": "signals_batch",
                    "signals": signals_update,
                    "count": len(signals_update)
                }))
            
            # Wait before next update (high frequency)
            await asyncio.sleep(5)  # 5-second updates
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Update prices periodically for realism
@app.on_event("startup")
async def startup_event():
    async def update_prices():
        while True:
            for symbol in DAYTRADING_SYMBOLS:
                current_price = SYMBOL_PRICES.get(symbol, 100)
                # Add realistic price movement
                change_pct = random.gauss(0, 0.01)  # 1% std dev
                new_price = current_price * (1 + change_pct)
                SYMBOL_PRICES[symbol] = max(0.01, new_price)  # Prevent negative prices
            
            await asyncio.sleep(10)  # Update every 10 seconds
    
    # Start background price updates
    asyncio.create_task(update_prices())

if __name__ == "__main__":
    uvicorn.run("daytrading_service:app", host="127.0.0.1", port=9003, reload=True)