#!/usr/bin/env python3
"""
Risk Calculator Service
Handles portfolio risk assessment, position risk analysis, and risk metrics calculation
"""

import logging
import math
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
import numpy as np

from ..models import (
    PositionRisk, PortfolioRisk, RiskEvent, RiskEventCreate, RiskMetrics,
    RiskLevel, AlertType, RiskLimits, StressTestResult, StressTestScenario
)

logger = logging.getLogger(__name__)

class RiskCalculator:
    """Advanced risk calculation engine"""
    
    def __init__(self):
        self.default_limits = RiskLimits()
        
    async def assess_position_risk(
        self, 
        position: Dict[str, Any], 
        portfolio_value: float,
        limits: Optional[RiskLimits] = None
    ) -> PositionRisk:
        """Assess risk for a single position"""
        try:
            if not limits:
                limits = self.default_limits
            
            # Basic position metrics
            position_value = abs(position.get("market_value", 0.0))
            position_size_pct = (position_value / portfolio_value * 100) if portfolio_value > 0 else 0
            
            # Price risk calculations
            entry_price = position.get("entry_price", 0.0)
            current_price = position.get("current_price", entry_price)
            stop_loss = position.get("stop_loss")
            take_profit = position.get("take_profit")
            
            distance_to_stop_loss = None
            distance_to_take_profit = None
            potential_loss = 0.0
            
            if stop_loss and current_price > 0:
                distance_to_stop_loss = abs(current_price - stop_loss) / current_price * 100
                potential_loss = abs(position_value * (current_price - stop_loss) / current_price)
            
            if take_profit and current_price > 0:
                distance_to_take_profit = abs(take_profit - current_price) / current_price * 100
            
            # Risk scoring
            liquidity_risk = self._calculate_liquidity_risk(position)
            price_risk = self._calculate_price_risk(position, distance_to_stop_loss)
            size_risk = min(position_size_pct / limits.max_position_size_pct * 100, 100)
            
            # Overall risk score (weighted average)
            overall_risk = (
                size_risk * 0.4 +
                price_risk * 0.3 +
                liquidity_risk * 0.3
            )
            
            # Risk level determination
            risk_level = self._determine_risk_level(overall_risk)
            
            # Generate recommendations and warnings
            recommendations = []
            warnings = []
            
            if position_size_pct > limits.max_position_size_pct:
                warnings.append(f"Position size ({position_size_pct:.1f}%) exceeds limit ({limits.max_position_size_pct:.1f}%)")
                recommendations.append("Consider reducing position size")
            
            if not stop_loss:
                warnings.append("No stop loss set")
                recommendations.append("Set a stop loss to limit downside risk")
            
            if distance_to_stop_loss and distance_to_stop_loss > 10:
                warnings.append(f"Stop loss is far from current price ({distance_to_stop_loss:.1f}%)")
                recommendations.append("Consider tightening stop loss")
            
            if overall_risk > 75:
                recommendations.append("Consider reducing position size or setting tighter risk controls")
            
            return PositionRisk(
                position_id=position.get("id", str(uuid.uuid4())),
                symbol=position.get("symbol", "UNKNOWN"),
                current_value=position_value,
                position_size_pct=position_size_pct,
                is_oversized=position_size_pct > limits.max_position_size_pct,
                distance_to_stop_loss=distance_to_stop_loss,
                distance_to_take_profit=distance_to_take_profit,
                potential_loss=potential_loss,
                volatility=self._estimate_volatility(position),
                beta=position.get("beta"),
                liquidity_risk=liquidity_risk,
                price_risk=price_risk,
                overall_risk=overall_risk,
                risk_level=risk_level,
                recommendations=recommendations,
                warnings=warnings
            )
            
        except Exception as e:
            logger.error(f"Error assessing position risk: {e}")
            raise
    
    async def assess_portfolio_risk(
        self, 
        positions: List[Dict[str, Any]], 
        limits: Optional[RiskLimits] = None
    ) -> PortfolioRisk:
        """Assess risk for entire portfolio"""
        try:
            if not limits:
                limits = self.default_limits
            
            if not positions:
                return self._empty_portfolio_risk()
            
            # Calculate portfolio totals
            total_value = sum(abs(pos.get("market_value", 0.0)) for pos in positions)
            cash_value = 0.0  # Assume for now, should come from portfolio data
            total_exposure = total_value
            
            # Basic portfolio metrics
            total_exposure_pct = (total_exposure / (total_value + cash_value) * 100) if (total_value + cash_value) > 0 else 0
            cash_pct = (cash_value / (total_value + cash_value) * 100) if (total_value + cash_value) > 0 else 0
            leverage_ratio = total_exposure / (total_value + cash_value) if (total_value + cash_value) > 0 else 0
            
            # Concentration analysis
            position_values = [abs(pos.get("market_value", 0.0)) for pos in positions]
            position_values.sort(reverse=True)
            
            largest_position_pct = (position_values[0] / total_value * 100) if position_values and total_value > 0 else 0
            top_5_positions_pct = sum(position_values[:5]) / total_value * 100 if len(position_values) >= 5 and total_value > 0 else 0
            
            # Sector analysis (simplified)
            sector_exposures = self._calculate_sector_exposures(positions, total_value)
            
            # Risk scores
            concentration_risk_score = self._calculate_concentration_risk(largest_position_pct, top_5_positions_pct, limits)
            sector_concentration_risk = self._calculate_sector_concentration_risk(sector_exposures, limits)
            correlation_risk = self._estimate_correlation_risk(positions)
            
            # Portfolio volatility estimation
            portfolio_volatility = self._estimate_portfolio_volatility(positions)
            
            # VaR calculations (simplified)
            var_95, var_99 = self._calculate_var(total_value, portfolio_volatility)
            max_drawdown = self._estimate_max_drawdown(positions)
            
            # Performance metrics
            beta = self._calculate_portfolio_beta(positions)
            sharpe_ratio = self._estimate_sharpe_ratio(positions)
            
            # Overall risk assessment
            exposure_risk = min(total_exposure_pct / limits.max_portfolio_exposure_pct * 100, 100)
            leverage_risk = min(leverage_ratio / limits.max_leverage * 100, 100)
            
            overall_risk_score = (
                concentration_risk_score * 0.3 +
                exposure_risk * 0.25 +
                sector_concentration_risk * 0.2 +
                correlation_risk * 0.15 +
                leverage_risk * 0.1
            )
            
            risk_level = self._determine_risk_level(overall_risk_score)
            
            # Generate recommendations and warnings
            recommendations = []
            warnings = []
            
            if total_exposure_pct > limits.max_portfolio_exposure_pct:
                warnings.append(f"Portfolio exposure ({total_exposure_pct:.1f}%) exceeds limit")
                recommendations.append("Reduce overall portfolio exposure")
            
            if largest_position_pct > limits.max_position_size_pct:
                warnings.append(f"Largest position ({largest_position_pct:.1f}%) exceeds size limit")
                recommendations.append("Reduce size of largest position")
            
            if cash_pct < limits.min_cash_pct:
                warnings.append(f"Cash level ({cash_pct:.1f}%) below minimum")
                recommendations.append("Increase cash reserves")
            
            return PortfolioRisk(
                portfolio_id="default",
                total_value=total_value,
                total_exposure_pct=total_exposure_pct,
                cash_pct=cash_pct,
                leverage_ratio=leverage_ratio,
                largest_position_pct=largest_position_pct,
                top_5_positions_pct=top_5_positions_pct,
                concentration_risk_score=concentration_risk_score,
                sector_exposures=sector_exposures,
                sector_concentration_risk=sector_concentration_risk,
                correlation_risk=correlation_risk,
                portfolio_volatility=portfolio_volatility,
                var_95=var_95,
                var_99=var_99,
                max_drawdown=max_drawdown,
                beta=beta,
                sharpe_ratio=sharpe_ratio,
                overall_risk_score=overall_risk_score,
                risk_level=risk_level,
                recommendations=recommendations,
                warnings=warnings
            )
            
        except Exception as e:
            logger.error(f"Error assessing portfolio risk: {e}")
            raise
    
    async def create_risk_event(
        self,
        db: AsyncSession,
        event_data: RiskEventCreate
    ) -> RiskEvent:
        """Create a new risk event"""
        try:
            from ..models import RiskEventDB
            
            event_id = str(uuid.uuid4())
            
            # Create database record
            event_db = RiskEventDB(
                id=event_id,
                event_type=event_data.event_type.value,
                risk_level=event_data.risk_level.value,
                entity_type=event_data.entity_type,
                entity_id=event_data.entity_id,
                title=event_data.title,
                description=event_data.description,
                risk_score=event_data.risk_score,
                threshold_breached=event_data.threshold_breached,
                current_value=event_data.current_value,
                metadata=event_data.metadata,
                recommendations=event_data.recommendations
            )
            
            db.add(event_db)
            await db.commit()
            await db.refresh(event_db)
            
            # Return Pydantic model
            event = RiskEvent(
                id=event_db.id,
                event_type=AlertType(event_db.event_type),
                risk_level=RiskLevel(event_db.risk_level),
                entity_type=event_db.entity_type,
                entity_id=event_db.entity_id,
                title=event_db.title,
                description=event_db.description,
                risk_score=event_db.risk_score,
                threshold_breached=event_db.threshold_breached,
                current_value=event_db.current_value,
                metadata=event_db.metadata or {},
                recommendations=event_db.recommendations or [],
                is_active=event_db.is_active,
                acknowledged=event_db.acknowledged,
                resolved=event_db.resolved,
                created_at=event_db.created_at
            )
            
            logger.info(f"🚨 Created {event_data.risk_level} risk event: {event_data.title}")
            return event
            
        except Exception as e:
            logger.error(f"Error creating risk event: {e}")
            await db.rollback()
            raise
    
    def _calculate_liquidity_risk(self, position: Dict[str, Any]) -> float:
        """Calculate liquidity risk score (0-100)"""
        # Simplified liquidity risk based on volume
        volume = position.get("volume", 0)
        avg_volume = position.get("avg_volume", volume)
        
        if avg_volume == 0:
            return 80.0  # High liquidity risk
        
        volume_ratio = volume / avg_volume
        
        if volume_ratio > 2.0:
            return 20.0  # Low liquidity risk
        elif volume_ratio > 1.0:
            return 40.0  # Medium liquidity risk
        elif volume_ratio > 0.5:
            return 60.0  # Medium-high liquidity risk
        else:
            return 80.0  # High liquidity risk
    
    def _calculate_price_risk(self, position: Dict[str, Any], distance_to_stop_loss: Optional[float]) -> float:
        """Calculate price risk score (0-100)"""
        if not distance_to_stop_loss:
            return 70.0  # High risk if no stop loss
        
        if distance_to_stop_loss > 15:
            return 80.0  # Very high risk
        elif distance_to_stop_loss > 10:
            return 60.0  # High risk
        elif distance_to_stop_loss > 5:
            return 40.0  # Medium risk
        else:
            return 20.0  # Low risk
    
    def _calculate_concentration_risk(
        self, 
        largest_position_pct: float, 
        top_5_positions_pct: float,
        limits: RiskLimits
    ) -> float:
        """Calculate concentration risk score"""
        largest_risk = min(largest_position_pct / limits.max_position_size_pct * 100, 100)
        concentration_risk = min(top_5_positions_pct / 50.0 * 100, 100)  # Assume 50% as high concentration
        
        return (largest_risk * 0.6 + concentration_risk * 0.4)
    
    def _calculate_sector_exposures(self, positions: List[Dict[str, Any]], total_value: float) -> Dict[str, float]:
        """Calculate sector exposure percentages"""
        sector_values = {}
        
        for position in positions:
            sector = position.get("sector", "Unknown")
            value = abs(position.get("market_value", 0.0))
            sector_values[sector] = sector_values.get(sector, 0.0) + value
        
        return {
            sector: (value / total_value * 100) if total_value > 0 else 0
            for sector, value in sector_values.items()
        }
    
    def _calculate_sector_concentration_risk(self, sector_exposures: Dict[str, float], limits: RiskLimits) -> float:
        """Calculate sector concentration risk"""
        max_sector_exposure = max(sector_exposures.values()) if sector_exposures else 0
        return min(max_sector_exposure / limits.max_sector_exposure_pct * 100, 100)
    
    def _estimate_correlation_risk(self, positions: List[Dict[str, Any]]) -> float:
        """Estimate correlation risk (simplified)"""
        # Simplified: assume higher correlation in larger portfolios
        num_positions = len(positions)
        
        if num_positions <= 5:
            return 80.0  # High correlation risk
        elif num_positions <= 10:
            return 60.0  # Medium-high correlation risk
        elif num_positions <= 20:
            return 40.0  # Medium correlation risk
        else:
            return 20.0  # Low correlation risk
    
    def _estimate_volatility(self, position: Dict[str, Any]) -> Optional[float]:
        """Estimate position volatility"""
        # Simplified: return stored volatility or estimate based on price movements
        return position.get("volatility")
    
    def _estimate_portfolio_volatility(self, positions: List[Dict[str, Any]]) -> Optional[float]:
        """Estimate portfolio volatility"""
        # Simplified: average of position volatilities weighted by size
        total_value = sum(abs(pos.get("market_value", 0.0)) for pos in positions)
        if total_value == 0:
            return None
        
        weighted_vol = 0.0
        total_weight = 0.0
        
        for position in positions:
            vol = position.get("volatility")
            if vol is not None:
                weight = abs(position.get("market_value", 0.0)) / total_value
                weighted_vol += vol * weight
                total_weight += weight
        
        return weighted_vol / total_weight if total_weight > 0 else None
    
    def _calculate_var(self, portfolio_value: float, volatility: Optional[float]) -> tuple:
        """Calculate Value at Risk (95% and 99%)"""
        if not volatility or portfolio_value <= 0:
            return None, None
        
        # Simplified VaR calculation (assuming normal distribution)
        daily_vol = volatility / math.sqrt(252)  # Convert to daily
        var_95 = portfolio_value * daily_vol * 1.645  # 95% confidence
        var_99 = portfolio_value * daily_vol * 2.326  # 99% confidence
        
        return var_95, var_99
    
    def _estimate_max_drawdown(self, positions: List[Dict[str, Any]]) -> Optional[float]:
        """Estimate maximum drawdown"""
        # Simplified: assume based on current unrealized P&L
        total_unrealized_pnl = sum(pos.get("unrealized_pnl", 0.0) for pos in positions)
        total_value = sum(abs(pos.get("market_value", 0.0)) for pos in positions)
        
        if total_value > 0:
            return abs(min(0, total_unrealized_pnl)) / total_value * 100
        
        return None
    
    def _calculate_portfolio_beta(self, positions: List[Dict[str, Any]]) -> Optional[float]:
        """Calculate portfolio beta"""
        total_value = sum(abs(pos.get("market_value", 0.0)) for pos in positions)
        if total_value == 0:
            return None
        
        weighted_beta = 0.0
        total_weight = 0.0
        
        for position in positions:
            beta = position.get("beta")
            if beta is not None:
                weight = abs(position.get("market_value", 0.0)) / total_value
                weighted_beta += beta * weight
                total_weight += weight
        
        return weighted_beta / total_weight if total_weight > 0 else None
    
    def _estimate_sharpe_ratio(self, positions: List[Dict[str, Any]]) -> Optional[float]:
        """Estimate Sharpe ratio"""
        # Simplified: would need returns data for proper calculation
        return None
    
    def _determine_risk_level(self, risk_score: float) -> RiskLevel:
        """Determine risk level from score"""
        if risk_score >= 80:
            return RiskLevel.CRITICAL
        elif risk_score >= 60:
            return RiskLevel.HIGH
        elif risk_score >= 40:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _empty_portfolio_risk(self) -> PortfolioRisk:
        """Return empty portfolio risk assessment"""
        return PortfolioRisk(
            portfolio_id="default",
            total_value=0.0,
            total_exposure_pct=0.0,
            cash_pct=100.0,
            leverage_ratio=0.0,
            largest_position_pct=0.0,
            top_5_positions_pct=0.0,
            concentration_risk_score=0.0,
            sector_exposures={},
            sector_concentration_risk=0.0,
            correlation_risk=0.0,
            overall_risk_score=0.0,
            risk_level=RiskLevel.LOW
        )