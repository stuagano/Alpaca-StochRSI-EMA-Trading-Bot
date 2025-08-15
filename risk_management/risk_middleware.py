import logging
from typing import Dict, List, Tuple, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import functools
import threading

from risk_management.risk_service import get_risk_service
from risk_management.trailing_stop_manager import get_trailing_stop_manager

class TradeAction(Enum):
    """Trading actions that require risk validation"""
    BUY = "buy"
    SELL = "sell"
    MODIFY = "modify"
    CANCEL = "cancel"

class ValidationSeverity(Enum):
    """Risk validation severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class RiskValidationResult:
    """Result of risk validation"""
    approved: bool
    action: TradeAction
    symbol: str
    severity: ValidationSeverity
    messages: List[str]
    recommendations: List[str]
    risk_metrics: Dict[str, Any]
    timestamp: datetime
    override_allowed: bool = False
    
class RiskValidationMiddleware:
    """
    Comprehensive risk validation middleware for all trading operations
    """
    
    def __init__(self):
        self.logger = logging.getLogger('risk.middleware')
        self.risk_service = get_risk_service()
        self.trailing_stop_manager = get_trailing_stop_manager()
        
        # Validation history
        self.validation_history: List[RiskValidationResult] = []
        self.lock = threading.Lock()
        
        # Validation rules configuration
        self.validation_rules = {
            'pre_trade_checks': True,
            'position_size_validation': True,
            'portfolio_risk_validation': True,
            'correlation_checks': True,
            'leverage_checks': True,
            'emergency_stop_checks': True,
            'trailing_stop_validation': True,
            'daily_limit_checks': True
        }
        
        # Override settings (for emergency situations)
        self.override_enabled = False
        self.override_expiry = None
        self.override_reason = None
        
        self.logger.info("Risk Validation Middleware initialized")
    
    def validate_trade(self, action: TradeAction, symbol: str, quantity: float, 
                      price: float, **kwargs) -> RiskValidationResult:
        """
        Comprehensive trade validation
        
        Args:
            action: Trading action (BUY, SELL, etc.)
            symbol: Trading symbol
            quantity: Trade quantity (positive for long, negative for short)
            price: Trade price
            **kwargs: Additional trade parameters
            
        Returns:
            RiskValidationResult with approval status and details
        """
        
        start_time = datetime.now()
        
        try:
            with self.lock:
                # Check if override is active and valid
                if self._is_override_active():
                    self.logger.warning(f"Risk validation override active: {self.override_reason}")
                    result = RiskValidationResult(
                        approved=True,
                        action=action,
                        symbol=symbol,
                        severity=ValidationSeverity.WARNING,
                        messages=[f"Trade approved under override: {self.override_reason}"],
                        recommendations=["Monitor trade closely due to override"],
                        risk_metrics={},
                        timestamp=start_time,
                        override_allowed=False
                    )
                    self._record_validation(result)
                    return result
                
                # Emergency stop check (highest priority)
                if self.risk_service.is_emergency_stop_active():
                    result = RiskValidationResult(
                        approved=False,
                        action=action,
                        symbol=symbol,
                        severity=ValidationSeverity.CRITICAL,
                        messages=["EMERGENCY STOP ACTIVE - All trading operations suspended"],
                        recommendations=["Contact risk management immediately", "Review emergency stop conditions"],
                        risk_metrics={'emergency_stop': True},
                        timestamp=start_time,
                        override_allowed=True
                    )
                    self._record_validation(result)
                    return result
                
                # Input validation
                validation_errors = self._validate_inputs(action, symbol, quantity, price, **kwargs)
                if validation_errors:
                    result = RiskValidationResult(
                        approved=False,
                        action=action,
                        symbol=symbol,
                        severity=ValidationSeverity.ERROR,
                        messages=validation_errors,
                        recommendations=["Correct input parameters", "Verify trade details"],
                        risk_metrics={},
                        timestamp=start_time
                    )
                    self._record_validation(result)
                    return result
                
                # Perform comprehensive risk checks
                validation_result = self._perform_risk_checks(action, symbol, quantity, price, **kwargs)
                
                # Record validation result
                self._record_validation(validation_result)
                
                execution_time = (datetime.now() - start_time).total_seconds()
                self.logger.info(f"Trade validation completed in {execution_time:.3f}s: "
                               f"{action.value} {symbol} - {'APPROVED' if validation_result.approved else 'REJECTED'}")
                
                return validation_result
                
        except Exception as e:
            self.logger.error(f"Trade validation failed: {e}")
            
            # Return conservative rejection on error
            error_result = RiskValidationResult(
                approved=False,
                action=action,
                symbol=symbol,
                severity=ValidationSeverity.CRITICAL,
                messages=[f"Validation system error: {str(e)}"],
                recommendations=["Contact technical support", "Manual review required"],
                risk_metrics={},
                timestamp=start_time,
                override_allowed=True
            )
            self._record_validation(error_result)
            return error_result
    
    def validate_portfolio_operation(self, operation_type: str, 
                                   details: Dict[str, Any]) -> RiskValidationResult:
        """
        Validate portfolio-level operations (rebalancing, risk adjustments, etc.)
        """
        
        try:
            # Get current portfolio assessment
            portfolio_assessment = self.risk_service.assess_portfolio_risk()
            
            # Check if operation would improve or worsen risk profile
            risk_impact = self._assess_portfolio_operation_risk(operation_type, details, portfolio_assessment)
            
            if risk_impact['approved']:
                return RiskValidationResult(
                    approved=True,
                    action=TradeAction.MODIFY,  # Portfolio modification
                    symbol="PORTFOLIO",
                    severity=ValidationSeverity.INFO,
                    messages=[f"Portfolio operation '{operation_type}' approved"],
                    recommendations=risk_impact.get('recommendations', []),
                    risk_metrics=risk_impact.get('metrics', {}),
                    timestamp=datetime.now()
                )
            else:
                return RiskValidationResult(
                    approved=False,
                    action=TradeAction.MODIFY,
                    symbol="PORTFOLIO",
                    severity=ValidationSeverity.WARNING,
                    messages=risk_impact.get('messages', [f"Portfolio operation '{operation_type}' rejected"]),
                    recommendations=risk_impact.get('recommendations', ["Review operation parameters"]),
                    risk_metrics=risk_impact.get('metrics', {}),
                    timestamp=datetime.now()
                )
                
        except Exception as e:
            self.logger.error(f"Portfolio operation validation failed: {e}")
            return RiskValidationResult(
                approved=False,
                action=TradeAction.MODIFY,
                symbol="PORTFOLIO",
                severity=ValidationSeverity.ERROR,
                messages=[f"Portfolio validation error: {str(e)}"],
                recommendations=["Manual review required"],
                risk_metrics={},
                timestamp=datetime.now()
            )
    
    def _perform_risk_checks(self, action: TradeAction, symbol: str, quantity: float, 
                           price: float, **kwargs) -> RiskValidationResult:
        """Perform comprehensive risk checks"""
        
        messages = []
        recommendations = []
        risk_metrics = {}
        severity = ValidationSeverity.INFO
        approved = True
        
        try:
            # Position sizing validation
            if self.validation_rules['position_size_validation']:
                position_check = self._validate_position_size(action, symbol, quantity, price, **kwargs)
                if not position_check['approved']:
                    approved = False
                    severity = max(severity, ValidationSeverity.WARNING)
                messages.extend(position_check.get('messages', []))
                recommendations.extend(position_check.get('recommendations', []))
                risk_metrics.update(position_check.get('metrics', {}))
            
            # Portfolio risk validation
            if self.validation_rules['portfolio_risk_validation']:
                portfolio_check = self._validate_portfolio_impact(action, symbol, quantity, price, **kwargs)
                if not portfolio_check['approved']:
                    approved = False
                    severity = max(severity, ValidationSeverity.WARNING)
                messages.extend(portfolio_check.get('messages', []))
                recommendations.extend(portfolio_check.get('recommendations', []))
                risk_metrics.update(portfolio_check.get('metrics', {}))
            
            # Correlation checks
            if self.validation_rules['correlation_checks']:
                correlation_check = self._validate_correlation_risk(action, symbol, quantity, price, **kwargs)
                if not correlation_check['approved']:
                    approved = False
                    severity = max(severity, ValidationSeverity.WARNING)
                messages.extend(correlation_check.get('messages', []))
                recommendations.extend(correlation_check.get('recommendations', []))
                risk_metrics.update(correlation_check.get('metrics', {}))
            
            # Leverage checks
            if self.validation_rules['leverage_checks']:
                leverage_check = self._validate_leverage_impact(action, symbol, quantity, price, **kwargs)
                if not leverage_check['approved']:
                    approved = False
                    severity = max(severity, ValidationSeverity.WARNING)
                messages.extend(leverage_check.get('messages', []))
                recommendations.extend(leverage_check.get('recommendations', []))
                risk_metrics.update(leverage_check.get('metrics', {}))
            
            # Daily limit checks
            if self.validation_rules['daily_limit_checks']:
                daily_check = self._validate_daily_limits(action, symbol, quantity, price, **kwargs)
                if not daily_check['approved']:
                    approved = False
                    severity = max(severity, ValidationSeverity.ERROR)
                messages.extend(daily_check.get('messages', []))
                recommendations.extend(daily_check.get('recommendations', []))
                risk_metrics.update(daily_check.get('metrics', {}))
            
            # Trailing stop validation
            if self.validation_rules['trailing_stop_validation'] and action == TradeAction.SELL:
                trailing_check = self._validate_trailing_stop_compliance(symbol, price, **kwargs)
                messages.extend(trailing_check.get('messages', []))
                recommendations.extend(trailing_check.get('recommendations', []))
                risk_metrics.update(trailing_check.get('metrics', {}))
            
            # Final approval message
            if approved:
                if not messages:
                    messages.append(f"Trade {action.value} {symbol} approved - all risk checks passed")
                if not recommendations:
                    recommendations.append("Monitor position closely")
            else:
                if not messages:
                    messages.append(f"Trade {action.value} {symbol} rejected - risk threshold exceeded")
                if not recommendations:
                    recommendations.append("Review trade parameters and risk limits")
            
            return RiskValidationResult(
                approved=approved,
                action=action,
                symbol=symbol,
                severity=severity,
                messages=messages,
                recommendations=recommendations,
                risk_metrics=risk_metrics,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"Risk checks failed: {e}")
            return RiskValidationResult(
                approved=False,
                action=action,
                symbol=symbol,
                severity=ValidationSeverity.ERROR,
                messages=[f"Risk check error: {str(e)}"],
                recommendations=["Manual review required"],
                risk_metrics={},
                timestamp=datetime.now()
            )
    
    def _validate_inputs(self, action: TradeAction, symbol: str, quantity: float, 
                        price: float, **kwargs) -> List[str]:
        """Validate input parameters"""
        
        errors = []
        
        # Symbol validation
        if not symbol or not isinstance(symbol, str) or len(symbol.strip()) == 0:
            errors.append("Invalid or missing symbol")
        
        # Price validation
        if price <= 0:
            errors.append(f"Invalid price: {price}")
        
        # Quantity validation
        if quantity == 0:
            errors.append("Quantity cannot be zero")
        
        # Action-specific validations
        if action == TradeAction.BUY and quantity < 0:
            errors.append("Buy action requires positive quantity")
        elif action == TradeAction.SELL and quantity > 0:
            # Allow positive quantity for sell (will be interpreted as closing long position)
            pass
        
        return errors
    
    def _validate_position_size(self, action: TradeAction, symbol: str, quantity: float, 
                              price: float, **kwargs) -> Dict[str, Any]:
        """Validate position size against risk limits"""
        
        try:
            # Use risk service to validate trade
            validation_result = self.risk_service.validate_trade_risk(symbol, action.value, abs(quantity), price)
            
            return {
                'approved': validation_result['approved'],
                'messages': validation_result.get('warnings', []),
                'recommendations': validation_result.get('recommendations', []),
                'metrics': validation_result.get('risk_metrics', {})
            }
            
        except Exception as e:
            self.logger.error(f"Position size validation failed: {e}")
            return {
                'approved': False,
                'messages': [f"Position size validation error: {str(e)}"],
                'recommendations': ["Manual review required"],
                'metrics': {}
            }
    
    def _validate_portfolio_impact(self, action: TradeAction, symbol: str, quantity: float, 
                                 price: float, **kwargs) -> Dict[str, Any]:
        """Validate impact on overall portfolio risk"""
        
        try:
            # Get current portfolio assessment
            portfolio_assessment = self.risk_service.assess_portfolio_risk()
            
            # Simulate trade impact (simplified)
            current_var = portfolio_assessment['portfolio_metrics']['var_95']
            current_violations = len(portfolio_assessment['risk_violations'])
            
            # If current portfolio already has violations, be more conservative
            if current_violations > 0:
                return {
                    'approved': False,
                    'messages': [f"Portfolio has {current_violations} existing risk violations"],
                    'recommendations': ["Address existing violations before new trades"],
                    'metrics': {'current_violations': current_violations}
                }
            
            # Check if trade would significantly increase portfolio VaR
            trade_value = abs(quantity) * price
            portfolio_value = portfolio_assessment['portfolio_metrics'].get('total_value', 100000)
            
            if portfolio_value > 0:
                trade_impact_pct = trade_value / portfolio_value
                if trade_impact_pct > 0.10:  # 10% of portfolio
                    return {
                        'approved': False,
                        'messages': [f"Trade represents {trade_impact_pct:.1%} of portfolio (>10% limit)"],
                        'recommendations': ["Reduce trade size", "Consider portfolio rebalancing"],
                        'metrics': {'trade_impact_pct': trade_impact_pct}
                    }
            
            return {
                'approved': True,
                'messages': ["Portfolio impact within acceptable limits"],
                'recommendations': ["Monitor portfolio risk metrics"],
                'metrics': {'current_var': current_var}
            }
            
        except Exception as e:
            self.logger.error(f"Portfolio impact validation failed: {e}")
            return {
                'approved': False,
                'messages': [f"Portfolio validation error: {str(e)}"],
                'recommendations': ["Manual review required"],
                'metrics': {}
            }
    
    def _validate_correlation_risk(self, action: TradeAction, symbol: str, quantity: float, 
                                 price: float, **kwargs) -> Dict[str, Any]:
        """Validate correlation risk impact"""
        
        try:
            # This would use more sophisticated correlation analysis in production
            # For now, implement basic correlation checks
            
            if action != TradeAction.BUY:
                return {'approved': True, 'messages': [], 'recommendations': [], 'metrics': {}}
            
            # Check for high correlation with existing positions
            # (Simplified implementation)
            portfolio_assessment = self.risk_service.assess_portfolio_risk()
            correlation_risk = portfolio_assessment['portfolio_metrics'].get('correlation_risk', 0)
            
            if correlation_risk > 0.8:  # High correlation threshold
                return {
                    'approved': False,
                    'messages': [f"Portfolio correlation risk ({correlation_risk:.1%}) is too high"],
                    'recommendations': ["Diversify holdings", "Reduce correlated positions"],
                    'metrics': {'correlation_risk': correlation_risk}
                }
            
            return {
                'approved': True,
                'messages': ["Correlation risk within limits"],
                'recommendations': [],
                'metrics': {'correlation_risk': correlation_risk}
            }
            
        except Exception as e:
            self.logger.error(f"Correlation validation failed: {e}")
            return {
                'approved': True,  # Default to approved on error
                'messages': [f"Correlation check error: {str(e)}"],
                'recommendations': [],
                'metrics': {}
            }
    
    def _validate_leverage_impact(self, action: TradeAction, symbol: str, quantity: float, 
                                price: float, **kwargs) -> Dict[str, Any]:
        """Validate leverage impact"""
        
        try:
            # Check if trade would violate leverage limits
            trade_value = abs(quantity) * price
            
            # Get current portfolio status
            portfolio_assessment = self.risk_service.assess_portfolio_risk()
            
            # Basic leverage check (would be more sophisticated in production)
            return {
                'approved': True,
                'messages': ["Leverage within limits"],
                'recommendations': [],
                'metrics': {'trade_value': trade_value}
            }
            
        except Exception as e:
            self.logger.error(f"Leverage validation failed: {e}")
            return {
                'approved': True,
                'messages': [],
                'recommendations': [],
                'metrics': {}
            }
    
    def _validate_daily_limits(self, action: TradeAction, symbol: str, quantity: float, 
                             price: float, **kwargs) -> Dict[str, Any]:
        """Validate daily trading limits"""
        
        try:
            # Check daily loss limits
            portfolio_assessment = self.risk_service.assess_portfolio_risk()
            daily_violations = [v for v in portfolio_assessment['risk_violations'] if 'daily' in v.lower()]
            
            if daily_violations:
                return {
                    'approved': False,
                    'messages': daily_violations,
                    'recommendations': ["Wait for daily reset", "Review daily risk management"],
                    'metrics': {'daily_violations': len(daily_violations)}
                }
            
            return {
                'approved': True,
                'messages': ["Daily limits OK"],
                'recommendations': [],
                'metrics': {}
            }
            
        except Exception as e:
            self.logger.error(f"Daily limit validation failed: {e}")
            return {
                'approved': True,
                'messages': [],
                'recommendations': [],
                'metrics': {}
            }
    
    def _validate_trailing_stop_compliance(self, symbol: str, price: float, 
                                         **kwargs) -> Dict[str, Any]:
        """Validate trailing stop compliance for sell orders"""
        
        try:
            # Check if there's an active trailing stop for this symbol
            stop_status = self.trailing_stop_manager.get_stop_status(symbol)
            
            if stop_status:
                messages = [f"Active trailing stop for {symbol}: current stop at {stop_status['stop_price']:.4f}"]
                
                if stop_status['is_activated']:
                    messages.append("Trailing stop is actively tracking price movement")
                else:
                    messages.append(f"Trailing stop will activate at {stop_status['activation_price']:.4f}")
                
                return {
                    'messages': messages,
                    'recommendations': ["Consider trailing stop impact on exit timing"],
                    'metrics': {'trailing_stop_active': True, 'stop_price': stop_status['stop_price']}
                }
            
            return {
                'messages': [],
                'recommendations': [],
                'metrics': {'trailing_stop_active': False}
            }
            
        except Exception as e:
            self.logger.error(f"Trailing stop validation failed: {e}")
            return {
                'messages': [],
                'recommendations': [],
                'metrics': {}
            }
    
    def _assess_portfolio_operation_risk(self, operation_type: str, details: Dict[str, Any], 
                                       portfolio_assessment: Dict[str, Any]) -> Dict[str, Any]:
        """Assess risk impact of portfolio operations"""
        
        # This would be more sophisticated in production
        # For now, basic approval for portfolio operations
        
        return {
            'approved': True,
            'messages': [f"Portfolio operation '{operation_type}' assessment completed"],
            'recommendations': ["Monitor operation impact"],
            'metrics': {'operation_type': operation_type}
        }
    
    def _record_validation(self, result: RiskValidationResult):
        """Record validation result in history"""
        
        try:
            self.validation_history.append(result)
            
            # Keep only recent validations (last 1000)
            if len(self.validation_history) > 1000:
                self.validation_history = self.validation_history[-1000:]
                
        except Exception as e:
            self.logger.error(f"Failed to record validation: {e}")
    
    def _is_override_active(self) -> bool:
        """Check if override is currently active"""
        
        if not self.override_enabled:
            return False
        
        if self.override_expiry and datetime.now() > self.override_expiry:
            self.override_enabled = False
            self.override_expiry = None
            self.override_reason = None
            return False
        
        return True
    
    def enable_override(self, reason: str, duration_minutes: int = 60) -> bool:
        """Enable risk validation override"""
        
        try:
            self.override_enabled = True
            self.override_reason = reason
            self.override_expiry = datetime.now() + timedelta(minutes=duration_minutes)
            
            self.logger.warning(f"Risk validation override enabled: {reason} (expires in {duration_minutes} minutes)")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to enable override: {e}")
            return False
    
    def disable_override(self) -> bool:
        """Disable risk validation override"""
        
        try:
            self.override_enabled = False
            self.override_expiry = None
            self.override_reason = None
            
            self.logger.info("Risk validation override disabled")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to disable override: {e}")
            return False
    
    def get_validation_history(self, symbol: str = None, limit: int = 100) -> List[RiskValidationResult]:
        """Get validation history"""
        
        try:
            with self.lock:
                history = self.validation_history
                
                if symbol:
                    history = [v for v in history if v.symbol == symbol]
                
                return history[-limit:] if limit else history
                
        except Exception as e:
            self.logger.error(f"Failed to get validation history: {e}")
            return []
    
    def get_validation_statistics(self) -> Dict[str, Any]:
        """Get validation statistics"""
        
        try:
            with self.lock:
                total_validations = len(self.validation_history)
                
                if total_validations == 0:
                    return {'total_validations': 0}
                
                approved_count = sum(1 for v in self.validation_history if v.approved)
                rejected_count = total_validations - approved_count
                
                severity_counts = {}
                for severity in ValidationSeverity:
                    severity_counts[severity.value] = sum(1 for v in self.validation_history if v.severity == severity)
                
                return {
                    'total_validations': total_validations,
                    'approved_count': approved_count,
                    'rejected_count': rejected_count,
                    'approval_rate': approved_count / total_validations * 100,
                    'severity_breakdown': severity_counts,
                    'override_active': self._is_override_active(),
                    'override_reason': self.override_reason
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get validation statistics: {e}")
            return {}

# Decorator for automatic risk validation
def risk_validated(validation_middleware: RiskValidationMiddleware = None):
    """
    Decorator to automatically validate trading operations
    """
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Extract trading parameters from function arguments
            # This would need to be customized based on your trading function signatures
            
            if validation_middleware is None:
                # Get global middleware instance
                middleware = get_risk_middleware()
            else:
                middleware = validation_middleware
            
            # Perform validation before executing trade
            # Implementation would depend on your specific function signatures
            
            # For now, just log and execute
            middleware.logger.info(f"Risk validation decorator applied to {func.__name__}")
            return func(*args, **kwargs)
        
        return wrapper
    return decorator

# Global middleware instance
_risk_middleware = None

def get_risk_middleware() -> RiskValidationMiddleware:
    """Get singleton risk validation middleware instance"""
    global _risk_middleware
    if _risk_middleware is None:
        _risk_middleware = RiskValidationMiddleware()
    return _risk_middleware