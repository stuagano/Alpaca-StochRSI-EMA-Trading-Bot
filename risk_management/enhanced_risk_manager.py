import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Tuple, Optional, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import threading
from decimal import Decimal, ROUND_HALF_UP

from risk_management.risk_config import RiskConfig, get_risk_config
from risk_management.position_sizer import DynamicPositionSizer, PositionSizeRecommendation
from risk_management.trailing_stop_manager import TrailingStopManager, TrailingStopConfig, TrailingStopType
from risk_management.risk_models import PortfolioRiskAnalyzer, ValueAtRisk, VolatilityModel


class RiskViolationType(Enum):
    """Types of risk violations"""
    POSITION_SIZE = "position_size"
    PORTFOLIO_EXPOSURE = "portfolio_exposure"
    CORRELATION = "correlation"
    DRAWDOWN = "drawdown"
    DAILY_LOSS = "daily_loss"
    VOLATILITY = "volatility"
    CONCENTRATION = "concentration"
    LIQUIDITY = "liquidity"
    EMERGENCY_STOP = "emergency_stop"


@dataclass
class RiskValidationResult:
    """Result of risk validation"""
    approved: bool
    confidence_score: float
    risk_score: float
    violations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    risk_metrics: Dict[str, Any] = field(default_factory=dict)
    position_size_adjustment: Optional[float] = None
    stop_loss_adjustment: Optional[float] = None


@dataclass
class PortfolioRiskState:
    """Current portfolio risk state"""
    total_exposure: float = 0.0
    cash_available: float = 0.0
    daily_pnl: float = 0.0
    max_drawdown: float = 0.0
    positions_count: int = 0
    correlation_risk: float = 0.0
    volatility: float = 0.0
    var_95: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)


class EnhancedRiskManager:
    """
    Comprehensive risk management system with advanced validation and controls
    """
    
    def __init__(self, config: Optional[RiskConfig] = None):
        self.logger = logging.getLogger('risk.enhanced_manager')
        
        # Load configuration
        self.config = config or get_risk_config()
        
        # Initialize components
        self.position_sizer = DynamicPositionSizer()
        self.trailing_stop_manager = TrailingStopManager()
        self.portfolio_analyzer = PortfolioRiskAnalyzer()
        self.var_model = ValueAtRisk()
        self.volatility_model = VolatilityModel()
        
        # Risk state tracking
        self.portfolio_state = PortfolioRiskState()
        self.active_positions: Dict[str, Dict[str, Any]] = {}
        self.risk_breaches: Dict[str, List[Dict[str, Any]]] = {}
        self.validation_stats = {
            'total_validations': 0,
            'approvals': 0,
            'rejections': 0,
            'warnings_issued': 0,
            'last_reset': datetime.now()
        }
        
        # Thread safety
        self.lock = threading.Lock()
        
        # Emergency controls
        self.emergency_stop_active = False
        self.emergency_stop_reason = None
        self.emergency_stop_time = None
        
        # Override controls (for emergency situations)
        self.override_active = False
        self.override_reason = None
        self.override_expiry = None
        
        self.logger.info("Enhanced Risk Manager initialized with comprehensive controls")
    
    def validate_position_size(self, symbol: str, proposed_size: float, 
                             entry_price: float, stop_loss_price: Optional[float] = None) -> RiskValidationResult:
        """
        Comprehensive position size validation with safety checks
        
        Args:
            symbol: Trading symbol
            proposed_size: Proposed position size (shares/units)
            entry_price: Entry price
            stop_loss_price: Stop loss price
            
        Returns:
            RiskValidationResult with validation outcome
        """
        
        self.logger.info(f"Validating position size for {symbol}: size={proposed_size}, entry=${entry_price:.4f}")
        
        with self.lock:
            self.validation_stats['total_validations'] += 1
            
            try:
                # Input validation
                validation_errors = self._validate_inputs(symbol, proposed_size, entry_price, stop_loss_price)
                if validation_errors:
                    result = RiskValidationResult(
                        approved=False,
                        confidence_score=0.0,
                        risk_score=100.0,
                        violations=validation_errors
                    )
                    self.validation_stats['rejections'] += 1
                    return result
                
                # Emergency stop check
                if self.emergency_stop_active and not self.override_active:
                    return RiskValidationResult(
                        approved=False,
                        confidence_score=0.0,
                        risk_score=100.0,
                        violations=[f"Emergency stop active: {self.emergency_stop_reason}"]
                    )
                
                # Calculate position value and percentage
                position_value = abs(proposed_size) * entry_price
                portfolio_value = self._get_portfolio_value()
                position_pct = position_value / portfolio_value if portfolio_value > 0 else 0
                
                # Initialize result
                result = RiskValidationResult(
                    approved=True,
                    confidence_score=1.0,
                    risk_score=0.0,
                    risk_metrics={
                        'position_value': position_value,
                        'position_percentage': position_pct * 100,
                        'portfolio_value': portfolio_value
                    }
                )
                
                # Prevent negative position sizes
                if proposed_size <= 0:
                    result.approved = False
                    result.violations.append("Position size must be positive")
                    result.risk_score = 100.0
                
                # Maximum position size check
                if position_pct > self.config.max_position_size:
                    if position_pct > self.config.max_position_size * 1.1:  # 10% buffer for hard rejection
                        result.approved = False
                        result.violations.append(
                            f"Position size ({position_pct:.2%}) exceeds maximum limit ({self.config.max_position_size:.2%})"
                        )
                    else:
                        # Suggest adjustment
                        max_allowed_size = (portfolio_value * self.config.max_position_size) / entry_price
                        result.position_size_adjustment = max_allowed_size
                        result.warnings.append(f"Position size reduced to comply with limits")
                        result.risk_score += 20
                
                # Portfolio exposure check
                current_exposure = self._calculate_current_exposure()
                new_total_exposure = current_exposure + position_value
                exposure_pct = new_total_exposure / portfolio_value if portfolio_value > 0 else 0
                
                if exposure_pct > self.config.max_portfolio_exposure:
                    result.approved = False
                    result.violations.append(
                        f"New position would exceed portfolio exposure limit "
                        f"({exposure_pct:.2%} > {self.config.max_portfolio_exposure:.2%})"
                    )
                    result.risk_score += 30
                
                # Maximum positions check
                if len(self.active_positions) >= self.config.max_positions:
                    result.approved = False
                    result.violations.append(f"Maximum positions limit reached ({self.config.max_positions})")
                    result.risk_score += 25
                
                # Stop loss validation
                if stop_loss_price:
                    stop_distance = abs(entry_price - stop_loss_price) / entry_price
                    
                    if stop_distance < self.config.min_stop_loss_distance:
                        result.warnings.append(f"Stop loss very tight ({stop_distance:.2%})")
                        result.risk_score += 15
                    elif stop_distance > self.config.max_stop_loss_distance:
                        result.warnings.append(f"Stop loss very wide ({stop_distance:.2%})")
                        result.risk_score += 10
                    
                    result.risk_metrics['stop_loss_distance'] = stop_distance * 100
                
                # ATR-based position sizing validation
                if self.config.use_atr_position_sizing:
                    atr_recommendation = self._validate_atr_position_sizing(
                        symbol, proposed_size, entry_price, stop_loss_price
                    )
                    if atr_recommendation:
                        result.warnings.extend(atr_recommendation.get('warnings', []))
                        if atr_recommendation.get('suggested_size'):
                            result.position_size_adjustment = atr_recommendation['suggested_size']
                
                # Correlation risk check
                correlation_risk = self._assess_correlation_risk(symbol)
                if correlation_risk > self.config.max_correlation_exposure:
                    result.warnings.append(f"High correlation risk detected ({correlation_risk:.2%})")
                    result.risk_score += 15
                    
                    if correlation_risk > 0.8:  # Very high correlation
                        result.approved = False
                        result.violations.append("Excessive correlation risk")
                
                # Daily loss limit check
                daily_loss_pct = self._get_daily_loss_percentage()
                if daily_loss_pct > self.config.max_daily_loss * 0.8:  # 80% of limit
                    result.warnings.append(f"Approaching daily loss limit ({daily_loss_pct:.2%})")
                    result.risk_score += 20
                    
                    if daily_loss_pct > self.config.max_daily_loss:
                        result.approved = False
                        result.violations.append("Daily loss limit exceeded")
                
                # Final risk score and confidence calculation
                result.confidence_score = max(0.1, 1.0 - (result.risk_score / 100))
                
                # Generate recommendations
                result.recommendations = self._generate_position_recommendations(result, symbol, proposed_size)
                
                # Record validation outcome
                if result.approved:
                    self.validation_stats['approvals'] += 1
                else:
                    self.validation_stats['rejections'] += 1
                
                if result.warnings:
                    self.validation_stats['warnings_issued'] += len(result.warnings)
                
                self.logger.info(f"Position validation for {symbol}: "
                               f"{'APPROVED' if result.approved else 'REJECTED'} "
                               f"(risk_score: {result.risk_score:.1f})")
                
                return result
                
            except Exception as e:
                self.logger.error(f"Position size validation failed for {symbol}: {e}")
                result = RiskValidationResult(
                    approved=False,
                    confidence_score=0.0,
                    risk_score=100.0,
                    violations=[f"Validation error: {str(e)}"]
                )
                self.validation_stats['rejections'] += 1
                return result
    
    def calculate_optimal_position_size(self, symbol: str, entry_price: float,
                                      stop_loss_price: Optional[float] = None,
                                      target_risk: Optional[float] = None) -> PositionSizeRecommendation:
        """
        Calculate optimal position size using advanced sizing algorithms
        
        Args:
            symbol: Trading symbol
            entry_price: Entry price
            stop_loss_price: Stop loss price
            target_risk: Target risk percentage (optional)
            
        Returns:
            PositionSizeRecommendation
        """
        
        try:
            # Get portfolio value
            portfolio_value = self._get_portfolio_value()
            
            # Use target risk or default
            if target_risk is None:
                target_risk = self.config.default_risk_per_trade
            
            # Auto-calculate stop loss if not provided
            if stop_loss_price is None:
                stop_loss_price = self._calculate_dynamic_stop_loss(symbol, entry_price)
            
            # Get historical data for advanced calculations
            historical_data = self._get_historical_data(symbol)
            
            # Calculate using position sizer
            recommendation = self.position_sizer.calculate_position_size(
                symbol=symbol,
                entry_price=entry_price,
                stop_loss_price=stop_loss_price,
                portfolio_value=portfolio_value,
                historical_data=historical_data,
                target_risk=target_risk
            )
            
            # Apply additional risk controls
            recommendation = self._apply_risk_controls(recommendation, symbol, entry_price)
            
            return recommendation
            
        except Exception as e:
            self.logger.error(f"Optimal position size calculation failed for {symbol}: {e}")
            # Return conservative fallback
            return PositionSizeRecommendation(
                symbol=symbol,
                recommended_size=self.config.min_position_size,
                max_safe_size=self.config.min_position_size,
                risk_adjusted_size=self.config.min_position_size,
                method_used="fallback",
                risk_per_trade=0.01,
                stop_loss_distance=0.05,
                confidence_score=0.1,
                warnings=["Calculation failed - using conservative fallback"]
            )
    
    def create_trailing_stop(self, symbol: str, entry_price: float, 
                           position_size: float, config_override: Optional[Dict] = None) -> bool:
        """
        Create a trailing stop with comprehensive validation
        
        Args:
            symbol: Trading symbol
            entry_price: Entry price
            position_size: Position size
            config_override: Optional configuration overrides
            
        Returns:
            Success flag
        """
        
        try:
            # Create trailing stop configuration
            if config_override:
                trailing_config = TrailingStopConfig(
                    stop_type=TrailingStopType(config_override.get('type', 'percentage')),
                    initial_distance=config_override.get('initial_distance', self.config.trailing_stop_distance),
                    trail_distance=config_override.get('trail_distance', self.config.trailing_stop_distance * 0.5),
                    activation_threshold=config_override.get('activation_threshold', self.config.trailing_activation_threshold)
                )
            else:
                trailing_config = TrailingStopConfig(
                    stop_type=TrailingStopType.PERCENTAGE,
                    initial_distance=self.config.trailing_stop_distance,
                    trail_distance=self.config.trailing_stop_distance * 0.5,
                    activation_threshold=self.config.trailing_activation_threshold
                )
            
            # Add trailing stop
            success = self.trailing_stop_manager.add_trailing_stop(
                symbol=symbol,
                entry_price=entry_price,
                position_size=position_size,
                config=trailing_config
            )
            
            if success:
                self.logger.info(f"Trailing stop created for {symbol} at entry ${entry_price:.4f}")
            else:
                self.logger.error(f"Failed to create trailing stop for {symbol}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Trailing stop creation failed for {symbol}: {e}")
            return False
    
    def update_position_price(self, symbol: str, current_price: float) -> Optional[Dict[str, Any]]:
        """
        Update position price and check for trailing stop triggers
        
        Args:
            symbol: Trading symbol
            current_price: Current market price
            
        Returns:
            Stop trigger information if triggered
        """
        
        try:
            # Update trailing stop
            trigger_info = self.trailing_stop_manager.update_price(symbol, current_price)
            
            # Update portfolio state
            self._update_portfolio_state()
            
            # Check for risk breaches
            self._check_portfolio_risk_limits()
            
            return trigger_info
            
        except Exception as e:
            self.logger.error(f"Price update failed for {symbol}: {e}")
            return None
    
    def add_position(self, symbol: str, entry_price: float, position_size: float, 
                    stop_loss_price: float) -> bool:
        """
        Add a new position to risk tracking
        
        Args:
            symbol: Trading symbol
            entry_price: Entry price
            position_size: Position size
            stop_loss_price: Stop loss price
            
        Returns:
            Success flag
        """
        
        try:
            with self.lock:
                position_info = {
                    'symbol': symbol,
                    'entry_price': entry_price,
                    'current_price': entry_price,
                    'position_size': position_size,
                    'stop_loss_price': stop_loss_price,
                    'entry_time': datetime.now(),
                    'market_value': abs(position_size) * entry_price,
                    'unrealized_pnl': 0.0,
                    'max_favorable_excursion': 0.0,
                    'max_adverse_excursion': 0.0
                }
                
                self.active_positions[symbol] = position_info
                
                # Update portfolio state
                self._update_portfolio_state()
                
                self.logger.info(f"Position added to risk tracking: {symbol} at ${entry_price:.4f}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to add position {symbol}: {e}")
            return False
    
    def remove_position(self, symbol: str) -> bool:
        """
        Remove position from risk tracking
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Success flag
        """
        
        try:
            with self.lock:
                if symbol in self.active_positions:
                    del self.active_positions[symbol]
                    
                    # Remove trailing stop
                    self.trailing_stop_manager.remove_trailing_stop(symbol)
                    
                    # Update portfolio state
                    self._update_portfolio_state()
                    
                    self.logger.info(f"Position removed from risk tracking: {symbol}")
                    return True
                else:
                    self.logger.warning(f"Position not found for removal: {symbol}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Failed to remove position {symbol}: {e}")
            return False
    
    def get_portfolio_risk_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive portfolio risk summary
        
        Returns:
            Portfolio risk summary
        """
        
        try:
            with self.lock:
                # Update portfolio state
                self._update_portfolio_state()
                
                # Calculate additional metrics
                total_positions = len(self.active_positions)
                largest_position_pct = 0.0
                if self.active_positions and self.portfolio_state.total_exposure > 0:
                    largest_position = max(
                        self.active_positions.values(),
                        key=lambda x: x['market_value']
                    )
                    largest_position_pct = largest_position['market_value'] / self._get_portfolio_value() * 100
                
                # Risk level classification
                risk_level = self._classify_portfolio_risk_level()
                
                summary = {
                    'timestamp': datetime.now().isoformat(),
                    'risk_level': risk_level,
                    'portfolio_metrics': {
                        'total_exposure_pct': (self.portfolio_state.total_exposure / self._get_portfolio_value() * 100) if self._get_portfolio_value() > 0 else 0,
                        'cash_available': self.portfolio_state.cash_available,
                        'daily_pnl': self.portfolio_state.daily_pnl,
                        'max_drawdown': self.portfolio_state.max_drawdown,
                        'volatility': self.portfolio_state.volatility,
                        'var_95': self.portfolio_state.var_95,
                        'correlation_risk': self.portfolio_state.correlation_risk
                    },
                    'position_metrics': {
                        'total_positions': total_positions,
                        'max_positions_allowed': self.config.max_positions,
                        'largest_position_pct': largest_position_pct,
                        'positions_near_stop': self._count_positions_near_stop()
                    },
                    'risk_limits': {
                        'daily_loss_limit': self.config.max_daily_loss * 100,
                        'portfolio_exposure_limit': self.config.max_portfolio_exposure * 100,
                        'max_position_size': self.config.max_position_size * 100,
                        'correlation_limit': self.config.max_correlation_exposure * 100
                    },
                    'current_breaches': len(self.risk_breaches),
                    'validation_stats': self.validation_stats.copy(),
                    'emergency_stop_active': self.emergency_stop_active,
                    'override_active': self.override_active
                }
                
                return summary
                
        except Exception as e:
            self.logger.error(f"Portfolio risk summary generation failed: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'risk_level': 'UNKNOWN',
                'error': str(e)
            }
    
    def enable_emergency_override(self, reason: str, duration_minutes: int = 60) -> bool:
        """
        Enable emergency risk override
        
        Args:
            reason: Reason for override
            duration_minutes: Override duration in minutes
            
        Returns:
            Success flag
        """
        
        try:
            with self.lock:
                self.override_active = True
                self.override_reason = reason
                self.override_expiry = datetime.now() + timedelta(minutes=duration_minutes)
                
                self.logger.warning(f"Emergency override enabled: {reason} (expires in {duration_minutes} minutes)")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to enable emergency override: {e}")
            return False
    
    def disable_emergency_override(self) -> bool:
        """
        Disable emergency risk override
        
        Returns:
            Success flag
        """
        
        try:
            with self.lock:
                self.override_active = False
                self.override_reason = None
                self.override_expiry = None
                
                self.logger.info("Emergency override disabled")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to disable emergency override: {e}")
            return False
    
    def get_validation_statistics(self) -> Dict[str, Any]:
        """
        Get risk validation statistics
        
        Returns:
            Validation statistics
        """
        
        with self.lock:
            stats = self.validation_stats.copy()
            
            # Calculate additional metrics
            if stats['total_validations'] > 0:
                stats['approval_rate'] = stats['approvals'] / stats['total_validations'] * 100
                stats['rejection_rate'] = stats['rejections'] / stats['total_validations'] * 100
                stats['avg_warnings_per_validation'] = stats['warnings_issued'] / stats['total_validations']
            else:
                stats['approval_rate'] = 0
                stats['rejection_rate'] = 0
                stats['avg_warnings_per_validation'] = 0
            
            # Time since last reset
            stats['hours_since_reset'] = (datetime.now() - stats['last_reset']).total_seconds() / 3600
            
            return stats
    
    def reset_validation_statistics(self) -> bool:
        """
        Reset validation statistics
        
        Returns:
            Success flag
        """
        
        try:
            with self.lock:
                self.validation_stats = {
                    'total_validations': 0,
                    'approvals': 0,
                    'rejections': 0,
                    'warnings_issued': 0,
                    'last_reset': datetime.now()
                }
                
                self.logger.info("Validation statistics reset")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to reset validation statistics: {e}")
            return False
    
    # Private helper methods
    
    def _validate_inputs(self, symbol: str, proposed_size: float, 
                        entry_price: float, stop_loss_price: Optional[float]) -> List[str]:
        """Validate input parameters"""
        
        errors = []
        
        if not symbol or not isinstance(symbol, str):
            errors.append("Invalid symbol")
        
        if not isinstance(proposed_size, (int, float)) or proposed_size <= 0:
            errors.append("Position size must be positive number")
        
        if not isinstance(entry_price, (int, float)) or entry_price <= 0:
            errors.append("Entry price must be positive number")
        
        if stop_loss_price is not None:
            if not isinstance(stop_loss_price, (int, float)) or stop_loss_price <= 0:
                errors.append("Stop loss price must be positive number")
            elif stop_loss_price >= entry_price:
                errors.append("Stop loss price must be below entry price for long positions")
        
        return errors
    
    def _get_portfolio_value(self) -> float:
        """Get current portfolio value"""
        
        try:
            # This would integrate with actual broker API
            # For now, return a calculated value based on positions and cash
            total_position_value = sum(pos['market_value'] for pos in self.active_positions.values())
            return total_position_value + self.portfolio_state.cash_available
        except Exception as e:
            self.logger.error(f"Failed to get portfolio value: {e}")
            return 100000.0  # Default fallback
    
    def _calculate_current_exposure(self) -> float:
        """Calculate current portfolio exposure"""
        
        try:
            return sum(pos['market_value'] for pos in self.active_positions.values())
        except Exception as e:
            self.logger.error(f"Failed to calculate exposure: {e}")
            return 0.0
    
    def _assess_correlation_risk(self, symbol: str) -> float:
        """Assess correlation risk for new symbol"""
        
        try:
            # Simplified correlation assessment
            # In production, this would calculate actual correlations
            
            # Check for similar symbols/sectors
            similar_count = 0
            for existing_symbol in self.active_positions.keys():
                if self._symbols_are_correlated(symbol, existing_symbol):
                    similar_count += 1
            
            # Return correlation risk as percentage
            total_positions = len(self.active_positions)
            if total_positions == 0:
                return 0.0
            
            return min(similar_count / total_positions * 100, 100.0)
            
        except Exception as e:
            self.logger.error(f"Correlation risk assessment failed: {e}")
            return 50.0  # Conservative default
    
    def _symbols_are_correlated(self, symbol1: str, symbol2: str) -> bool:
        """Check if two symbols are likely correlated"""
        
        # Simplified correlation check
        # In production, use actual correlation calculations
        
        # Check for same sector ETFs
        tech_etfs = ['QQQ', 'XLK', 'VGT', 'FTEC']
        financial_etfs = ['XLF', 'VFH', 'KBE']
        energy_etfs = ['XLE', 'VDE', 'OIH']
        
        for sector_group in [tech_etfs, financial_etfs, energy_etfs]:
            if symbol1 in sector_group and symbol2 in sector_group:
                return True
        
        # Check for similar company names/tickers
        if symbol1[:2] == symbol2[:2] and len(symbol1) > 2 and len(symbol2) > 2:
            return True
        
        return False
    
    def _get_daily_loss_percentage(self) -> float:
        """Get current daily loss percentage"""
        
        try:
            daily_pnl = self.portfolio_state.daily_pnl
            portfolio_value = self._get_portfolio_value()
            
            if portfolio_value > 0 and daily_pnl < 0:
                return abs(daily_pnl) / portfolio_value * 100
            else:
                return 0.0
                
        except Exception as e:
            self.logger.error(f"Failed to get daily loss percentage: {e}")
            return 0.0
    
    def _validate_atr_position_sizing(self, symbol: str, proposed_size: float,
                                    entry_price: float, stop_loss_price: Optional[float]) -> Optional[Dict]:
        """Validate ATR-based position sizing"""
        
        try:
            if not self.config.use_atr_position_sizing:
                return None
            
            historical_data = self._get_historical_data(symbol)
            if historical_data is None or len(historical_data) < 20:
                return {'warnings': ['Insufficient data for ATR validation']}
            
            # Calculate ATR
            atr = self._calculate_atr(historical_data)
            if atr <= 0:
                return {'warnings': ['Invalid ATR calculation']}
            
            # Calculate suggested position size based on ATR
            risk_amount = self._get_portfolio_value() * self.config.default_risk_per_trade
            atr_stop_distance = atr * self.config.atr_multiplier
            suggested_size = risk_amount / atr_stop_distance
            
            # Compare with proposed size
            size_diff_pct = abs(suggested_size - proposed_size) / suggested_size * 100
            
            if size_diff_pct > 25:  # More than 25% difference
                return {
                    'warnings': [f'Position size differs significantly from ATR recommendation ({size_diff_pct:.1f}%)'],
                    'suggested_size': suggested_size
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"ATR position sizing validation failed: {e}")
            return {'warnings': ['ATR validation failed']}
    
    def _calculate_dynamic_stop_loss(self, symbol: str, entry_price: float) -> float:
        """Calculate dynamic stop loss"""
        
        try:
            if self.config.use_atr_stop_loss:
                historical_data = self._get_historical_data(symbol)
                if historical_data is not None and len(historical_data) >= 20:
                    atr = self._calculate_atr(historical_data)
                    if atr > 0:
                        return entry_price - (atr * self.config.atr_multiplier)
            
            # Fallback to percentage-based stop
            return entry_price * (1 - self.config.default_stop_loss_distance)
            
        except Exception as e:
            self.logger.error(f"Dynamic stop loss calculation failed: {e}")
            return entry_price * 0.95  # 5% fallback
    
    def _calculate_atr(self, data: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average True Range"""
        
        try:
            if len(data) < period:
                return 0.0
            
            high = data['high']
            low = data['low']
            close = data['close']
            
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            
            true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = true_range.rolling(window=period).mean().iloc[-1]
            
            return atr if not pd.isna(atr) else 0.0
            
        except Exception as e:
            self.logger.error(f"ATR calculation failed: {e}")
            return 0.0
    
    def _get_historical_data(self, symbol: str, days: int = 60) -> Optional[pd.DataFrame]:
        """Get historical data for symbol"""
        
        try:
            # This would integrate with actual data provider
            # For now, return simulated data
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            date_range = pd.date_range(start=start_date, end=end_date, freq='D')
            
            # Simple random walk
            np.random.seed(hash(symbol) % 1000)
            returns = np.random.normal(0.001, 0.02, len(date_range))
            prices = 100 * (1 + returns).cumprod()
            
            data = pd.DataFrame({
                'open': prices * (1 + np.random.normal(0, 0.005, len(prices))),
                'high': prices * (1 + np.abs(np.random.normal(0, 0.01, len(prices)))),
                'low': prices * (1 - np.abs(np.random.normal(0, 0.01, len(prices)))),
                'close': prices,
                'volume': np.random.randint(100000, 1000000, len(prices))
            }, index=date_range)
            
            # Ensure OHLC consistency
            data['high'] = data[['open', 'high', 'close']].max(axis=1)
            data['low'] = data[['open', 'low', 'close']].min(axis=1)
            
            return data
            
        except Exception as e:
            self.logger.error(f"Failed to get historical data for {symbol}: {e}")
            return None
    
    def _apply_risk_controls(self, recommendation: PositionSizeRecommendation, 
                           symbol: str, entry_price: float) -> PositionSizeRecommendation:
        """Apply additional risk controls to position size recommendation"""
        
        try:
            # Check against maximum position size
            portfolio_value = self._get_portfolio_value()
            max_position_value = portfolio_value * self.config.max_position_size
            max_position_size = max_position_value / entry_price
            
            if recommendation.risk_adjusted_size > max_position_size:
                recommendation.risk_adjusted_size = max_position_size
                recommendation.warnings.append("Position size capped by portfolio limit")
            
            # Check against minimum position size
            min_position_value = portfolio_value * self.config.min_position_size
            min_position_size = min_position_value / entry_price
            
            if recommendation.risk_adjusted_size < min_position_size:
                recommendation.risk_adjusted_size = min_position_size
                recommendation.warnings.append("Position size increased to minimum threshold")
            
            return recommendation
            
        except Exception as e:
            self.logger.error(f"Risk control application failed: {e}")
            return recommendation
    
    def _generate_position_recommendations(self, result: RiskValidationResult, 
                                         symbol: str, proposed_size: float) -> List[str]:
        """Generate recommendations based on validation result"""
        
        recommendations = []
        
        if not result.approved:
            recommendations.append("Position rejected - address violations before proceeding")
        elif result.warnings:
            recommendations.append("Position approved with warnings - monitor closely")
        else:
            recommendations.append("Position approved - low risk")
        
        if result.position_size_adjustment:
            recommendations.append(f"Consider adjusting position size to {result.position_size_adjustment:.0f} shares")
        
        if result.risk_score > 50:
            recommendations.append("High risk detected - consider smaller position or tighter stop loss")
        
        return recommendations
    
    def _update_portfolio_state(self):
        """Update portfolio risk state"""
        
        try:
            # Calculate total exposure
            self.portfolio_state.total_exposure = self._calculate_current_exposure()
            
            # Update position count
            self.portfolio_state.positions_count = len(self.active_positions)
            
            # Calculate unrealized P&L
            total_unrealized_pnl = 0.0
            for position in self.active_positions.values():
                if 'current_price' in position and 'entry_price' in position:
                    pnl = (position['current_price'] - position['entry_price']) * position['position_size']
                    position['unrealized_pnl'] = pnl
                    total_unrealized_pnl += pnl
            
            self.portfolio_state.daily_pnl = total_unrealized_pnl
            
            # Update timestamp
            self.portfolio_state.last_updated = datetime.now()
            
        except Exception as e:
            self.logger.error(f"Portfolio state update failed: {e}")
    
    def _check_portfolio_risk_limits(self):
        """Check for portfolio-level risk limit breaches"""
        
        try:
            # Check daily loss limit
            daily_loss_pct = self._get_daily_loss_percentage()
            if daily_loss_pct > self.config.max_daily_loss * 100:
                self._record_risk_breach(
                    RiskViolationType.DAILY_LOSS,
                    f"Daily loss {daily_loss_pct:.2f}% exceeds limit {self.config.max_daily_loss * 100:.2f}%"
                )
            
            # Check portfolio exposure
            portfolio_value = self._get_portfolio_value()
            if portfolio_value > 0:
                exposure_pct = self.portfolio_state.total_exposure / portfolio_value
                if exposure_pct > self.config.max_portfolio_exposure:
                    self._record_risk_breach(
                        RiskViolationType.PORTFOLIO_EXPOSURE,
                        f"Portfolio exposure {exposure_pct:.2%} exceeds limit {self.config.max_portfolio_exposure:.2%}"
                    )
            
            # Check position count
            if self.portfolio_state.positions_count > self.config.max_positions:
                self._record_risk_breach(
                    RiskViolationType.POSITION_SIZE,
                    f"Position count {self.portfolio_state.positions_count} exceeds limit {self.config.max_positions}"
                )
                
        except Exception as e:
            self.logger.error(f"Risk limit check failed: {e}")
    
    def _record_risk_breach(self, violation_type: RiskViolationType, description: str):
        """Record a risk limit breach"""
        
        try:
            breach_info = {
                'timestamp': datetime.now().isoformat(),
                'type': violation_type.value,
                'description': description
            }
            
            if violation_type.value not in self.risk_breaches:
                self.risk_breaches[violation_type.value] = []
            
            self.risk_breaches[violation_type.value].append(breach_info)
            
            # Keep only recent breaches (last 100)
            if len(self.risk_breaches[violation_type.value]) > 100:
                self.risk_breaches[violation_type.value] = self.risk_breaches[violation_type.value][-100:]
            
            self.logger.warning(f"Risk breach recorded: {violation_type.value} - {description}")
            
        except Exception as e:
            self.logger.error(f"Failed to record risk breach: {e}")
    
    def _classify_portfolio_risk_level(self) -> str:
        """Classify current portfolio risk level"""
        
        try:
            risk_factors = 0
            
            # Check various risk factors
            if self._get_daily_loss_percentage() > self.config.max_daily_loss * 50:  # 50% of limit
                risk_factors += 1
            
            portfolio_value = self._get_portfolio_value()
            if portfolio_value > 0:
                exposure_pct = self.portfolio_state.total_exposure / portfolio_value
                if exposure_pct > self.config.max_portfolio_exposure * 0.8:  # 80% of limit
                    risk_factors += 1
            
            if self.portfolio_state.positions_count > self.config.max_positions * 0.8:  # 80% of limit
                risk_factors += 1
            
            if len(self.risk_breaches) > 0:
                risk_factors += 1
            
            # Classify based on risk factors
            if risk_factors == 0:
                return "LOW"
            elif risk_factors <= 2:
                return "MODERATE"
            elif risk_factors <= 3:
                return "HIGH"
            else:
                return "CRITICAL"
                
        except Exception as e:
            self.logger.error(f"Risk level classification failed: {e}")
            return "UNKNOWN"
    
    def _count_positions_near_stop(self) -> int:
        """Count positions near their stop loss"""
        
        try:
            count = 0
            for position in self.active_positions.values():
                if 'current_price' in position and 'stop_loss_price' in position:
                    current_price = position['current_price']
                    stop_price = position['stop_loss_price']
                    
                    # Check if within 10% of stop loss
                    if abs(current_price - stop_price) / current_price <= 0.10:
                        count += 1
            
            return count
            
        except Exception as e:
            self.logger.error(f"Failed to count positions near stop: {e}")
            return 0


# Global enhanced risk manager instance
_enhanced_risk_manager = None

def get_enhanced_risk_manager() -> EnhancedRiskManager:
    """Get singleton enhanced risk manager instance"""
    global _enhanced_risk_manager
    if _enhanced_risk_manager is None:
        _enhanced_risk_manager = EnhancedRiskManager()
    return _enhanced_risk_manager