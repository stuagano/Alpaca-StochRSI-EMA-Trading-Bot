#!/usr/bin/env python3
"""
Risk Management Service
Position sizing, risk metrics, and portfolio protection
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import uvicorn
import math
from typing import Dict, List
from pydantic import BaseModel

app = FastAPI(title="Risk Management Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Risk models
class PositionSizeRequest(BaseModel):
    account_value: float
    entry_price: float
    stop_loss: float = None
    risk_percent: float = 2.0  # Default 2% risk per trade
    symbol: str

class RiskMetrics(BaseModel):
    total_risk_exposure: float
    position_risk: Dict[str, float]
    max_drawdown: float
    sharpe_ratio: float = None
    var_95: float = None  # Value at Risk 95%

# Mock portfolio data for calculations
PORTFOLIO_DATA = {
    "account_value": 117232.50,
    "cash": 75000.00,
    "positions": [
        {"symbol": "AAPL", "value": 17825.00, "qty": 100, "entry": 175.50, "current": 178.25},
        {"symbol": "MSFT", "value": 20837.50, "qty": 50, "entry": 420.00, "current": 416.75},
        {"symbol": "GOOGL", "value": 3570.00, "qty": 25, "entry": 140.00, "current": 142.80}
    ]
}

def calculate_position_size(account_value: float, entry_price: float, stop_loss: float = None, risk_percent: float = 2.0) -> Dict:
    """Calculate optimal position size based on risk parameters"""
    
    risk_amount = account_value * (risk_percent / 100)
    
    if stop_loss and stop_loss > 0:
        # Calculate position size based on stop loss
        risk_per_share = abs(entry_price - stop_loss)
        if risk_per_share > 0:
            position_size = int(risk_amount / risk_per_share)
        else:
            position_size = 0
    else:
        # Default to 2% risk with 10% stop loss
        default_stop_loss = entry_price * 0.90  # 10% stop loss
        risk_per_share = entry_price - default_stop_loss
        position_size = int(risk_amount / risk_per_share)
        stop_loss = default_stop_loss
    
    position_value = position_size * entry_price
    position_risk = position_size * abs(entry_price - stop_loss) if stop_loss else 0
    
    return {
        "position_size": position_size,
        "position_value": round(position_value, 2),
        "position_risk": round(position_risk, 2),
        "risk_percent": round((position_risk / account_value) * 100, 2),
        "stop_loss": round(stop_loss, 2) if stop_loss else None,
        "risk_reward_ratio": round((entry_price * 0.1) / abs(entry_price - stop_loss), 2) if stop_loss else None
    }

def calculate_portfolio_risk() -> Dict:
    """Calculate comprehensive portfolio risk metrics"""
    
    total_value = PORTFOLIO_DATA["account_value"]
    positions = PORTFOLIO_DATA["positions"]
    
    # Position concentration risk
    position_weights = {}
    total_position_value = sum(pos["value"] for pos in positions)
    
    for pos in positions:
        weight = (pos["value"] / total_value) * 100
        position_weights[pos["symbol"]] = round(weight, 2)
    
    # Calculate portfolio beta (mock)
    portfolio_beta = 1.15  # Mock beta relative to market
    
    # Calculate VaR (Value at Risk) - simplified
    portfolio_volatility = 0.18  # 18% annual volatility
    var_95 = total_value * portfolio_volatility * 1.645 * math.sqrt(1/252)  # Daily VaR
    
    # Risk exposure by sector (mock)
    sector_exposure = {
        "Technology": 85.4,
        "Consumer": 14.6,
        "Healthcare": 0.0,
        "Finance": 0.0,
        "Energy": 0.0
    }
    
    # Correlation risk (simplified)
    correlation_risk = "HIGH" if sector_exposure["Technology"] > 70 else "MEDIUM"
    
    return {
        "total_portfolio_value": total_value,
        "cash_percentage": round((PORTFOLIO_DATA["cash"] / total_value) * 100, 2),
        "invested_percentage": round((total_position_value / total_value) * 100, 2),
        "position_weights": position_weights,
        "largest_position": max(position_weights.items(), key=lambda x: x[1]),
        "portfolio_beta": portfolio_beta,
        "daily_var_95": round(var_95, 2),
        "sector_exposure": sector_exposure,
        "correlation_risk": correlation_risk,
        "risk_score": calculate_risk_score(position_weights, sector_exposure, portfolio_beta),
        "recommendations": generate_risk_recommendations(position_weights, sector_exposure)
    }

def calculate_risk_score(position_weights: Dict, sector_exposure: Dict, beta: float) -> int:
    """Calculate overall risk score (1-10, 10 being highest risk)"""
    score = 0
    
    # Concentration risk
    max_position = max(position_weights.values())
    if max_position > 40:
        score += 3
    elif max_position > 25:
        score += 2
    elif max_position > 15:
        score += 1
    
    # Sector concentration
    max_sector = max(sector_exposure.values())
    if max_sector > 80:
        score += 3
    elif max_sector > 60:
        score += 2
    elif max_sector > 40:
        score += 1
    
    # Beta risk
    if beta > 1.5:
        score += 2
    elif beta > 1.2:
        score += 1
    
    # Number of positions (diversification)
    num_positions = len(position_weights)
    if num_positions < 3:
        score += 2
    elif num_positions < 5:
        score += 1
    
    return min(10, max(1, score))

def generate_risk_recommendations(position_weights: Dict, sector_exposure: Dict) -> List[str]:
    """Generate risk management recommendations"""
    recommendations = []
    
    max_position_weight = max(position_weights.values())
    if max_position_weight > 30:
        symbol = max(position_weights.items(), key=lambda x: x[1])[0]
        recommendations.append(f"Consider reducing {symbol} position - currently {max_position_weight}% of portfolio")
    
    if sector_exposure.get("Technology", 0) > 70:
        recommendations.append("High technology sector concentration - consider diversification into other sectors")
    
    if len(position_weights) < 5:
        recommendations.append("Consider increasing diversification with additional positions")
    
    cash_pct = PORTFOLIO_DATA["cash"] / PORTFOLIO_DATA["account_value"] * 100
    if cash_pct < 10:
        recommendations.append("Consider maintaining higher cash reserves (10-20%) for opportunities")
    elif cash_pct > 30:
        recommendations.append("High cash allocation - consider deploying capital in market opportunities")
    
    return recommendations

@app.get("/health")
async def health_check():
    return {
        "service": "risk-management",
        "status": "healthy", 
        "timestamp": datetime.utcnow().isoformat(),
        "risk_models_active": ["position_sizing", "portfolio_risk", "var", "sector_analysis"]
    }

@app.post("/position-size")
async def calculate_position_sizing(request: PositionSizeRequest):
    """Calculate optimal position size for a trade"""
    try:
        result = calculate_position_size(
            account_value=request.account_value,
            entry_price=request.entry_price,
            stop_loss=request.stop_loss,
            risk_percent=request.risk_percent
        )
        
        result.update({
            "symbol": request.symbol,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error calculating position size: {str(e)}")

@app.get("/portfolio/risk")
async def get_portfolio_risk():
    """Get comprehensive portfolio risk analysis"""
    return calculate_portfolio_risk()

@app.get("/risk/alerts")
async def get_risk_alerts():
    """Get active risk alerts and warnings"""
    alerts = []
    
    portfolio_risk = calculate_portfolio_risk()
    risk_score = portfolio_risk["risk_score"]
    
    # Generate alerts based on risk metrics
    if risk_score >= 8:
        alerts.append({
            "type": "HIGH_RISK",
            "severity": "CRITICAL",
            "message": f"Portfolio risk score: {risk_score}/10 - Immediate attention required",
            "timestamp": datetime.utcnow().isoformat()
        })
    elif risk_score >= 6:
        alerts.append({
            "type": "MEDIUM_RISK", 
            "severity": "WARNING",
            "message": f"Portfolio risk score: {risk_score}/10 - Monitor closely",
            "timestamp": datetime.utcnow().isoformat()
        })
    
    # Check position concentration
    largest_position = portfolio_risk["largest_position"]
    if largest_position[1] > 30:
        alerts.append({
            "type": "CONCENTRATION_RISK",
            "severity": "WARNING",
            "message": f"{largest_position[0]} represents {largest_position[1]}% of portfolio",
            "timestamp": datetime.utcnow().isoformat()
        })
    
    # Check sector concentration
    max_sector = max(portfolio_risk["sector_exposure"].values())
    if max_sector > 75:
        alerts.append({
            "type": "SECTOR_CONCENTRATION",
            "severity": "WARNING",
            "message": f"Over-concentrated in single sector: {max_sector}%",
            "timestamp": datetime.utcnow().isoformat()
        })
    
    return {
        "alerts": alerts,
        "count": len(alerts),
        "risk_score": risk_score,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/risk/limits")
async def get_risk_limits():
    """Get current risk limits and parameters"""
    return {
        "max_position_size": 25.0,  # Max % of portfolio per position
        "max_sector_allocation": 60.0,  # Max % per sector
        "max_daily_risk": 5.0,  # Max daily portfolio risk %
        "min_cash_reserve": 10.0,  # Minimum cash %
        "max_portfolio_beta": 1.5,  # Maximum portfolio beta
        "var_limit": 2.0,  # Daily VaR limit %
        "correlation_threshold": 0.7,  # Max correlation between positions
        "stop_loss_required": True,
        "default_risk_per_trade": 2.0,  # Default risk per trade %
        "last_updated": datetime.utcnow().isoformat()
    }

@app.get("/stress-test")
async def run_stress_test():
    """Run portfolio stress test scenarios"""
    scenarios = {
        "market_crash_20": {
            "description": "20% market decline",
            "portfolio_impact": -21.5,  # With 1.15 beta
            "estimated_loss": PORTFOLIO_DATA["account_value"] * 0.215
        },
        "sector_rotation": {
            "description": "Technology sector decline -30%",
            "portfolio_impact": -25.6,  # High tech exposure
            "estimated_loss": PORTFOLIO_DATA["account_value"] * 0.256
        },
        "volatility_spike": {
            "description": "VIX spike to 40+",
            "portfolio_impact": -15.8,
            "estimated_loss": PORTFOLIO_DATA["account_value"] * 0.158
        },
        "interest_rate_shock": {
            "description": "Fed raises rates 200bp",
            "portfolio_impact": -12.3,
            "estimated_loss": PORTFOLIO_DATA["account_value"] * 0.123
        }
    }
    
    return {
        "stress_scenarios": scenarios,
        "overall_risk_rating": "MEDIUM-HIGH",
        "recommendations": [
            "Consider hedging technology exposure",
            "Maintain adequate cash reserves",
            "Review stop-loss levels"
        ],
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    uvicorn.run("simple_service:app", host="127.0.0.1", port=9004, reload=True)