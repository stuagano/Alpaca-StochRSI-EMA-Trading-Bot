import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
from dataclasses import asdict

from risk_management.risk_models import (
    PortfolioRiskAnalyzer, RiskMetrics, PositionRisk, 
    ValueAtRisk, VolatilityModel
)
from risk_management.position_sizer import (
    DynamicPositionSizer, PositionSizingMethod, 
    PositionSizeRecommendation, RiskAdjustedRebalancer
)
from services.data_service import get_data_service
from config.config_manager import get_trading_config
from utils.logging_config import PerformanceLogger

class RiskManagementService:
    """
    Comprehensive risk management service integrating all risk components
    """
    
    def __init__(self):
        self.logger = logging.getLogger('risk.service')
        self.perf_logger = PerformanceLogger(self.logger)
        
        # Initialize components
        self.portfolio_analyzer = PortfolioRiskAnalyzer()
        self.position_sizer = DynamicPositionSizer()
        self.rebalancer = RiskAdjustedRebalancer()
        self.var_model = ValueAtRisk()
        self.volatility_model = VolatilityModel()
        
        # Get configuration
        self.trading_config = get_trading_config()
        self.data_service = get_data_service()
        
        # Enhanced portfolio-level risk limits
        self.max_daily_loss = getattr(self.trading_config, 'max_daily_loss_percentage', 5.0) / 100
        self.max_drawdown = getattr(self.trading_config, 'max_drawdown_percentage', 15.0) / 100
        self.max_positions = getattr(self.trading_config, 'max_positions', 10)
        self.correlation_threshold = getattr(self.trading_config, 'correlation_threshold', 0.7)
        
        # Additional portfolio risk limits
        self.max_portfolio_var_95 = 0.10  # 10% maximum VaR
        self.max_portfolio_volatility = 0.30  # 30% maximum annualized volatility
        self.max_sector_concentration = 0.40  # 40% maximum in any sector
        self.max_single_position = 0.20  # 20% maximum single position
        self.max_leverage = 1.0  # No leverage by default
        self.min_cash_reserve = 0.05  # 5% minimum cash reserve
        self.max_correlation_exposure = 0.60  # 60% maximum in highly correlated assets
        
        # Risk monitoring flags
        self.portfolio_risk_alerts = []
        self.risk_breaches = {}
        self.last_risk_check = datetime.now()
        
        # Emergency stop triggers
        self.emergency_stop_triggered = False
        self.emergency_stop_reason = None
        
        self.logger.info("Enhanced Risk Management Service initialized with portfolio-level controls")
    
    def assess_portfolio_risk(self, positions: Dict[str, Dict[str, Any]] = None,
                            market_data: Dict[str, pd.DataFrame] = None) -> Dict[str, Any]:
        """
        Comprehensive portfolio risk assessment
        
        Returns:
            Dictionary containing all risk metrics and analysis
        """
        
        start_time = datetime.now()
        
        try:
            # Get current positions if not provided
            if positions is None:
                positions = self._get_current_positions()
            
            # Get market data if not provided
            if market_data is None:
                market_data = self._get_market_data(list(positions.keys()))
            
            # Calculate portfolio risk metrics
            portfolio_risk = self.portfolio_analyzer.calculate_portfolio_risk(
                positions, market_data
            )
            
            # Analyze individual position risks
            position_risks = self.portfolio_analyzer.analyze_position_risk(
                positions, market_data
            )
            
            # Calculate risk budget
            risk_budget = self.portfolio_analyzer.calculate_risk_budget(positions)
            
            # Enhanced risk limit checks
            risk_violations = self._check_comprehensive_risk_limits(portfolio_risk, positions, market_data)
            
            # Generate risk summary
            risk_summary = self._generate_risk_summary(
                portfolio_risk, position_risks, risk_violations
            )
            
            # Compile comprehensive risk report
            risk_assessment = {
                'timestamp': datetime.now().isoformat(),
                'portfolio_metrics': asdict(portfolio_risk),
                'position_risks': [asdict(pr) for pr in position_risks],
                'risk_budget': risk_budget,
                'risk_violations': risk_violations,
                'risk_summary': risk_summary,
                'recommendations': self._generate_risk_recommendations(
                    portfolio_risk, position_risks, risk_violations
                )
            }
            
            # Log performance
            execution_time = (datetime.now() - start_time).total_seconds()
            self.perf_logger.log_risk_assessment(
                ticker="PORTFOLIO",
                risk_score=portfolio_risk.var_95,
                risk_factors={
                    'volatility': portfolio_risk.volatility,
                    'max_drawdown': portfolio_risk.max_drawdown,
                    'correlation_risk': portfolio_risk.correlation_risk
                },
                decision="ASSESSED"
            )
            
            self.logger.info(f"Portfolio risk assessment completed in {execution_time:.3f}s")
            
            return risk_assessment
            
        except Exception as e:
            self.logger.error(f"Portfolio risk assessment failed: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'portfolio_metrics': asdict(RiskMetrics()),
                'position_risks': [],
                'risk_violations': ['Assessment failed'],
                'recommendations': ['Review system configuration and data availability']
            }
    
    def calculate_position_size(self, symbol: str, entry_price: float,
                              stop_loss_price: float = None,
                              method: str = "volatility_adjusted",
                              **kwargs) -> PositionSizeRecommendation:
        """
        Calculate optimal position size for a new trade
        
        Args:
            symbol: Trading symbol
            entry_price: Intended entry price
            stop_loss_price: Stop loss price (auto-calculated if not provided)
            method: Position sizing method
            **kwargs: Additional parameters
            
        Returns:
            PositionSizeRecommendation object
        """
        
        try:
            # Auto-calculate stop loss if not provided
            if stop_loss_price is None:
                stop_loss_price = self._calculate_auto_stop_loss(symbol, entry_price)
            
            # Get current portfolio value
            portfolio_summary = self.data_service.get_portfolio_summary()
            portfolio_value = portfolio_summary.get('total_open_value', 100000)  # Default 100k
            
            # Get historical data for the symbol
            historical_data = self._get_symbol_data(symbol)
            
            # Convert method string to enum
            try:
                sizing_method = PositionSizingMethod(method)
            except ValueError:
                sizing_method = PositionSizingMethod.VOLATILITY_ADJUSTED
                self.logger.warning(f"Unknown sizing method {method}, using volatility_adjusted")
            
            # Calculate position size
            recommendation = self.position_sizer.calculate_position_size(
                symbol=symbol,
                entry_price=entry_price,
                stop_loss_price=stop_loss_price,
                portfolio_value=portfolio_value,
                method=sizing_method,
                historical_data=historical_data,
                **kwargs
            )
            
            # Additional risk checks
            self._validate_position_recommendation(recommendation)
            
            return recommendation
            
        except Exception as e:
            self.logger.error(f"Position sizing failed for {symbol}: {e}")
            
            # Return conservative fallback
            return PositionSizeRecommendation(
                symbol=symbol,
                recommended_size=0.05,
                max_safe_size=0.05,
                risk_adjusted_size=0.05,
                method_used="fallback",
                risk_per_trade=0.01,
                stop_loss_distance=0.05,
                confidence_score=0.1,
                warnings=[f"Calculation failed: {str(e)}"]
            )
    
    def validate_trade_risk(self, symbol: str, action: str, quantity: float,
                          price: float) -> Dict[str, Any]:
        """
        Validate if a proposed trade meets risk requirements
        
        Args:
            symbol: Trading symbol
            action: 'BUY' or 'SELL'
            quantity: Trade quantity
            price: Trade price
            
        Returns:
            Validation result with approval status and warnings
        """
        
        try:
            validation_result = {
                'approved': True,
                'warnings': [],
                'risk_metrics': {},
                'recommendations': []
            }
            
            # Get current portfolio state
            portfolio_summary = self.data_service.get_portfolio_summary()
            current_positions = self.data_service.get_open_orders()
            
            portfolio_value = portfolio_summary.get('total_open_value', 100000)
            trade_value = quantity * price
            
            # Position size validation
            position_size_pct = trade_value / portfolio_value
            
            if position_size_pct > self.position_sizer.max_position_size:
                validation_result['warnings'].append(
                    f"Trade size ({position_size_pct:.2%}) exceeds maximum position size limit "
                    f"({self.position_sizer.max_position_size:.2%})"
                )
            
            # Portfolio concentration check
            if action == 'BUY':
                current_positions_count = len(current_positions) if not current_positions.empty else 0
                if current_positions_count >= self.max_positions:
                    validation_result['approved'] = False
                    validation_result['warnings'].append(
                        f"Maximum positions ({self.max_positions}) already reached"
                    )
            
            # Daily risk limit check
            daily_pnl = portfolio_summary.get('unrealized_pnl', 0)
            daily_risk_pct = abs(daily_pnl) / portfolio_value
            
            if daily_risk_pct > self.max_daily_loss * 0.8:  # 80% of limit
                validation_result['warnings'].append(
                    f"Approaching daily loss limit: {daily_risk_pct:.2%} of {self.max_daily_loss:.2%}"
                )
                
                if daily_risk_pct > self.max_daily_loss:
                    validation_result['approved'] = False
                    validation_result['warnings'].append("Daily loss limit exceeded")
            
            # Correlation check for new positions
            if action == 'BUY' and not current_positions.empty:
                correlation_risk = self._check_correlation_risk(symbol, current_positions)
                
                if correlation_risk > self.correlation_threshold:
                    validation_result['warnings'].append(
                        f"High correlation risk detected ({correlation_risk:.2f})"
                    )
                    
                    if correlation_risk > 0.85:  # Very high correlation
                        validation_result['approved'] = False
                        validation_result['warnings'].append(
                            "Trade rejected due to excessive correlation risk"
                        )
            
            # Add risk metrics
            validation_result['risk_metrics'] = {
                'position_size_pct': position_size_pct,
                'portfolio_value': portfolio_value,
                'trade_value': trade_value,
                'daily_risk_pct': daily_risk_pct,
                'positions_count': len(current_positions) if not current_positions.empty else 0
            }
            
            # Generate recommendations
            if not validation_result['approved']:
                validation_result['recommendations'].append("Trade rejected - address risk violations")
            elif validation_result['warnings']:
                validation_result['recommendations'].append("Trade approved with warnings - monitor closely")
            else:
                validation_result['recommendations'].append("Trade approved - low risk")
            
            self.logger.info(f"Trade validation for {symbol}: {'APPROVED' if validation_result['approved'] else 'REJECTED'}")
            
            return validation_result
            
        except Exception as e:
            self.logger.error(f"Trade validation failed for {symbol}: {e}")
            return {
                'approved': False,
                'warnings': [f"Validation failed: {str(e)}"],
                'risk_metrics': {},
                'recommendations': ["Review trade manually due to validation error"]
            }
    
    def calculate_dynamic_stop_loss(self, symbol: str, entry_price: float,
                                  method: str = "atr", multiplier: float = 2.0,
                                  min_stop_pct: float = 0.005, max_stop_pct: float = 0.20) -> float:
        """
        Calculate dynamic stop loss based on market conditions with comprehensive validation
        
        Args:
            symbol: Trading symbol
            entry_price: Entry price
            method: Stop loss calculation method ('atr', 'volatility', 'support_resistance', 'adaptive')
            multiplier: ATR multiplier for ATR-based stops
            min_stop_pct: Minimum stop loss percentage (e.g., 0.005 = 0.5%)
            max_stop_pct: Maximum stop loss percentage (e.g., 0.20 = 20%)
            
        Returns:
            Recommended stop loss price
        """
        
        try:
            # Input validation
            if not symbol or entry_price <= 0:
                self.logger.error(f"Invalid inputs: symbol='{symbol}', entry_price={entry_price}")
                return entry_price * 0.95
            
            # Validate stop loss bounds
            min_stop_pct = max(min_stop_pct, 0.001)  # Minimum 0.1%
            max_stop_pct = min(max_stop_pct, 0.50)   # Maximum 50%
            
            if min_stop_pct >= max_stop_pct:
                self.logger.warning(f"Invalid stop percentage bounds: min={min_stop_pct}, max={max_stop_pct}")
                min_stop_pct = 0.005
                max_stop_pct = 0.20
            
            historical_data = self._get_symbol_data(symbol)
            
            if historical_data is None or len(historical_data) < 20:
                self.logger.warning(f"Insufficient data for dynamic stop loss calculation for {symbol}")
                # Fallback to conservative fixed percentage
                return entry_price * (1 - min_stop_pct * 2)  # 2x minimum stop
            
            stop_loss = None
            
            # Calculate stop loss based on method
            if method == "atr":
                stop_loss = self._calculate_atr_stop_loss(historical_data, entry_price, multiplier)
            elif method == "volatility":
                stop_loss = self._calculate_volatility_stop_loss(historical_data, entry_price)
            elif method == "support_resistance":
                stop_loss = self._calculate_support_resistance_stop_loss(historical_data, entry_price)
            elif method == "adaptive":
                # Try ATR first, fallback to volatility if ATR fails
                stop_loss = self._calculate_atr_stop_loss(historical_data, entry_price, multiplier)
                if stop_loss == entry_price * 0.95:  # ATR failed, try volatility
                    stop_loss = self._calculate_volatility_stop_loss(historical_data, entry_price)
            else:
                self.logger.warning(f"Unknown stop loss method '{method}', using ATR")
                stop_loss = self._calculate_atr_stop_loss(historical_data, entry_price, multiplier)
            
            # Apply final safety bounds
            if stop_loss is None or stop_loss <= 0:
                self.logger.error(f"Invalid stop loss calculated: {stop_loss}")
                stop_loss = entry_price * (1 - min_stop_pct * 2)
            
            # Ensure stop loss is within acceptable range
            min_stop_loss = entry_price * (1 - max_stop_pct)
            max_stop_loss = entry_price * (1 - min_stop_pct)
            
            stop_loss = max(stop_loss, min_stop_loss)  # Not too wide
            stop_loss = min(stop_loss, max_stop_loss)  # Not too tight
            
            # Final validation
            if stop_loss >= entry_price:
                self.logger.error(f"Stop loss ({stop_loss}) >= entry price ({entry_price})")
                stop_loss = entry_price * (1 - min_stop_pct * 2)
            
            stop_distance_pct = (entry_price - stop_loss) / entry_price * 100
            self.logger.info(f"Dynamic stop loss for {symbol}: {stop_loss:.4f} ({stop_distance_pct:.2f}% from entry) using {method} method")
            
            return stop_loss
                
        except Exception as e:
            self.logger.error(f"Dynamic stop loss calculation failed for {symbol}: {e}")
            return entry_price * 0.95  # 5% fallback
    
    def get_portfolio_risk_dashboard(self) -> Dict[str, Any]:
        """
        Generate comprehensive risk dashboard data
        """
        
        try:
            # Get full risk assessment
            risk_assessment = self.assess_portfolio_risk()
            
            # Calculate additional dashboard metrics
            dashboard_data = {
                'overview': {
                    'risk_level': self._categorize_risk_level(risk_assessment),
                    'var_95': risk_assessment['portfolio_metrics']['var_95'],
                    'max_drawdown': risk_assessment['portfolio_metrics']['max_drawdown'],
                    'volatility': risk_assessment['portfolio_metrics']['volatility'],
                    'sharpe_ratio': risk_assessment['portfolio_metrics']['sharpe_ratio']
                },
                'alerts': self._generate_risk_alerts(risk_assessment),
                'top_risks': self._identify_top_risks(risk_assessment),
                'recommendations': risk_assessment.get('recommendations', []),
                'risk_attribution': self._calculate_risk_attribution(risk_assessment),
                'limits_status': self._get_limits_status(risk_assessment),
                'timestamp': datetime.now().isoformat()
            }
            
            return dashboard_data
            
        except Exception as e:
            self.logger.error(f"Risk dashboard generation failed: {e}")
            return {
                'overview': {'risk_level': 'UNKNOWN'},
                'alerts': [f"Dashboard generation failed: {str(e)}"],
                'top_risks': [],
                'recommendations': ['Review system configuration'],
                'timestamp': datetime.now().isoformat()
            }
    
    def _get_current_positions(self) -> Dict[str, Dict[str, Any]]:
        """Get current portfolio positions"""
        
        try:
            open_orders = self.data_service.get_open_orders()
            
            positions = {}
            for _, order in open_orders.iterrows():
                positions[order['ticker']] = {
                    'quantity': order.get('quantity', 0),
                    'market_value': order.get('total', 0),
                    'entry_price': order.get('buy_price', 0),
                    'current_price': order.get('current_price', order.get('buy_price', 0))
                }
            
            return positions
            
        except Exception as e:
            self.logger.error(f"Failed to get current positions: {e}")
            return {}
    
    def _get_market_data(self, symbols: List[str]) -> Dict[str, pd.DataFrame]:
        """Get market data for symbols"""
        
        market_data = {}
        
        for symbol in symbols:
            try:
                data = self._get_symbol_data(symbol)
                if data is not None and not data.empty:
                    market_data[symbol] = data
            except Exception as e:
                self.logger.warning(f"Failed to get market data for {symbol}: {e}")
        
        return market_data
    
    def _get_symbol_data(self, symbol: str, days: int = 90) -> pd.DataFrame:
        """Get historical data for a symbol"""
        
        try:
            # Try to get from data service first
            historical_data = self.data_service.get_historical_data(symbol, days)
            
            if not historical_data.empty:
                return historical_data
            
            # Generate synthetic data for demonstration
            # In production, this would fetch real market data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            date_range = pd.date_range(start=start_date, end=end_date, freq='D')
            
            # Simple random walk
            np.random.seed(hash(symbol) % 1000)  # Consistent seed per symbol
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
            self.logger.error(f"Failed to get data for {symbol}: {e}")
            return pd.DataFrame()
    
    def _calculate_auto_stop_loss(self, symbol: str, entry_price: float) -> float:
        """Calculate automatic stop loss based on volatility"""
        
        try:
            historical_data = self._get_symbol_data(symbol)
            
            if historical_data is not None and len(historical_data) > 20:
                # Use 2x ATR for stop loss
                return self._calculate_atr_stop_loss(historical_data, entry_price, multiplier=2.0)
            else:
                # Fallback to 5% stop loss
                return entry_price * 0.95
                
        except Exception as e:
            self.logger.error(f"Auto stop loss calculation failed: {e}")
            return entry_price * 0.95
    
    def _calculate_atr_stop_loss(self, data: pd.DataFrame, entry_price: float,
                               multiplier: float = 2.0) -> float:
        """Calculate ATR-based stop loss"""
        
        try:
            # Calculate True Range
            high = data['high']
            low = data['low']
            close = data['close']
            
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            
            true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = true_range.rolling(window=14).mean().iloc[-1]
            
            if pd.isna(atr) or atr <= 0:
                return entry_price * 0.95
            
            stop_loss = entry_price - (multiplier * atr)
            return max(stop_loss, entry_price * 0.90)  # Minimum 10% stop
            
        except Exception as e:
            self.logger.error(f"ATR stop loss calculation failed: {e}")
            return entry_price * 0.95
    
    def _calculate_volatility_stop_loss(self, data: pd.DataFrame, entry_price: float) -> float:
        """Calculate volatility-based stop loss"""
        
        try:
            returns = data['close'].pct_change().dropna()
            volatility = returns.std()
            
            if volatility <= 0:
                return entry_price * 0.95
            
            # 2 standard deviation stop
            stop_distance = 2 * volatility
            stop_loss = entry_price * (1 - stop_distance)
            
            return max(stop_loss, entry_price * 0.90)  # Minimum 10% stop
            
        except Exception as e:
            self.logger.error(f"Volatility stop loss calculation failed: {e}")
            return entry_price * 0.95
    
    def _calculate_support_resistance_stop_loss(self, data: pd.DataFrame, entry_price: float) -> float:
        """Calculate support/resistance based stop loss"""
        
        try:
            # Simple support level calculation
            recent_lows = data['low'].tail(20)
            support_level = recent_lows.min()
            
            # Stop loss slightly below support
            stop_loss = support_level * 0.98
            
            # Ensure reasonable distance
            if (entry_price - stop_loss) / entry_price > 0.15:  # More than 15%
                stop_loss = entry_price * 0.90  # Cap at 10%
            elif (entry_price - stop_loss) / entry_price < 0.02:  # Less than 2%
                stop_loss = entry_price * 0.98  # Minimum 2%
            
            return stop_loss
            
        except Exception as e:
            self.logger.error(f"Support/resistance stop loss calculation failed: {e}")
            return entry_price * 0.95
    
    def _check_comprehensive_risk_limits(self, portfolio_risk: RiskMetrics,
                                        positions: Dict[str, Dict[str, Any]],
                                        market_data: Dict[str, pd.DataFrame]) -> List[str]:
        """Comprehensive portfolio-level risk limit checks with enhanced validation"""
        
        violations = []
        
        try:
            # Portfolio Value at Risk checks
            if portfolio_risk.var_95 > self.max_portfolio_var_95 * 100:
                violations.append(
                    f"Portfolio VaR 95% ({portfolio_risk.var_95:.2f}%) exceeds limit ({self.max_portfolio_var_95*100:.1f}%)"
                )
                self._record_risk_breach('var_95', portfolio_risk.var_95, self.max_portfolio_var_95 * 100)
            
            # Portfolio volatility checks
            if portfolio_risk.volatility > self.max_portfolio_volatility * 100:
                violations.append(
                    f"Portfolio volatility ({portfolio_risk.volatility:.2f}%) exceeds limit ({self.max_portfolio_volatility*100:.1f}%)"
                )
                self._record_risk_breach('volatility', portfolio_risk.volatility, self.max_portfolio_volatility * 100)
            
            # Concentration risk checks
            concentration_violations = self._check_concentration_limits(positions)
            violations.extend(concentration_violations)
            
            # Position count and size checks
            position_violations = self._check_position_limits(positions)
            violations.extend(position_violations)
            
            # Drawdown checks
            if portfolio_risk.max_drawdown > self.max_drawdown * 100:
                violations.append(
                    f"Maximum drawdown ({portfolio_risk.max_drawdown:.2f}%) exceeds limit ({self.max_drawdown*100:.1f}%)"
                )
                self._record_risk_breach('max_drawdown', portfolio_risk.max_drawdown, self.max_drawdown * 100)
            
            # Correlation risk checks
            if portfolio_risk.correlation_risk > self.correlation_threshold:
                violations.append(
                    f"Portfolio correlation risk ({portfolio_risk.correlation_risk:.2f}) exceeds limit ({self.correlation_threshold:.2f})"
                )
                self._record_risk_breach('correlation_risk', portfolio_risk.correlation_risk, self.correlation_threshold)
            
            # Liquidity risk checks
            if portfolio_risk.liquidity_risk > 0.8:  # 80% liquidity risk threshold
                violations.append(
                    f"Portfolio liquidity risk ({portfolio_risk.liquidity_risk:.2f}) is critically high (>0.8)"
                )
                self._record_risk_breach('liquidity_risk', portfolio_risk.liquidity_risk, 0.8)
            
            # Portfolio leverage checks
            leverage_violations = self._check_leverage_limits(positions)
            violations.extend(leverage_violations)
            
            # Cash reserve checks
            cash_violations = self._check_cash_reserve_limits()
            violations.extend(cash_violations)
            
            # Daily loss checks
            daily_loss_violations = self._check_daily_loss_limits()
            violations.extend(daily_loss_violations)
            
            # Emergency stop conditions
            emergency_violations = self._check_emergency_stop_conditions(portfolio_risk, positions)
            violations.extend(emergency_violations)
            
            # Update last risk check timestamp
            self.last_risk_check = datetime.now()
            
            # Log critical violations
            if violations:
                self.logger.warning(f"Risk limit violations detected: {len(violations)} issues")
                for violation in violations:
                    self.logger.warning(f"  - {violation}")
            
            return violations
            
        except Exception as e:
            self.logger.error(f"Comprehensive risk limit check failed: {e}")
            return [f"Risk limit check failed: {str(e)}"]
    
    def _check_correlation_risk(self, symbol: str, current_positions: pd.DataFrame) -> float:
        """Check correlation risk for new symbol"""
        
        try:
            # Simplified correlation check
            # In production, this would calculate actual correlations
            
            # If positions include similar symbols, return high correlation
            similar_patterns = ['SPY', 'QQQ', 'IWM']  # ETFs
            
            symbol_type = None
            for pattern in similar_patterns:
                if pattern in symbol:
                    symbol_type = pattern
                    break
            
            if symbol_type:
                similar_count = sum(1 for _, pos in current_positions.iterrows() 
                                  if symbol_type in pos.get('ticker', ''))
                return min(similar_count * 0.3, 0.9)  # Max 90% correlation
            
            return 0.3  # Default moderate correlation
            
        except Exception as e:
            self.logger.error(f"Correlation check failed: {e}")
            return 0.5
    
    def _validate_position_recommendation(self, recommendation: PositionSizeRecommendation):
        """Add additional validation to position recommendation"""
        
        # Check if position size is reasonable
        if recommendation.risk_adjusted_size > 0.25:  # 25% of portfolio
            recommendation.warnings.append("Very large position size - consider reducing")
        
        # Check risk per trade
        if recommendation.risk_per_trade > self.position_sizer.max_risk_per_trade:
            recommendation.warnings.append(
                f"Risk per trade ({recommendation.risk_per_trade:.2%}) exceeds limit "
                f"({self.position_sizer.max_risk_per_trade:.2%})"
            )
    
    def _generate_risk_summary(self, portfolio_risk: RiskMetrics,
                             position_risks: List[PositionRisk],
                             violations: List[str]) -> str:
        """Generate human-readable risk summary"""
        
        risk_level = "LOW"
        if portfolio_risk.var_95 > 7.5 or len(violations) > 2:
            risk_level = "HIGH"
        elif portfolio_risk.var_95 > 5.0 or len(violations) > 0:
            risk_level = "MODERATE"
        
        summary = f"Portfolio Risk Level: {risk_level}\n"
        summary += f"Value at Risk (95%): {portfolio_risk.var_95:.2f}%\n"
        summary += f"Portfolio Volatility: {portfolio_risk.volatility:.2f}%\n"
        summary += f"Maximum Drawdown: {portfolio_risk.max_drawdown:.2f}%\n"
        
        if violations:
            summary += f"\nRisk Violations: {len(violations)}\n"
        
        if position_risks:
            highest_risk = max(position_risks, key=lambda x: x.risk_score)
            summary += f"Highest Risk Position: {highest_risk.symbol} ({highest_risk.risk_score:.1f}%)\n"
        
        return summary
    
    def _generate_risk_recommendations(self, portfolio_risk: RiskMetrics,
                                     position_risks: List[PositionRisk],
                                     violations: List[str]) -> List[str]:
        """Generate risk management recommendations"""
        
        recommendations = []
        
        if violations:
            recommendations.append("Address risk limit violations immediately")
        
        if portfolio_risk.var_95 > 7.5:
            recommendations.append("Consider reducing position sizes to lower portfolio VaR")
        
        if portfolio_risk.concentration_risk > 0.6:
            recommendations.append("Diversify portfolio to reduce concentration risk")
        
        if portfolio_risk.correlation_risk > 0.7:
            recommendations.append("Reduce correlation risk by diversifying across sectors")
        
        # Position-specific recommendations
        high_risk_positions = [pr for pr in position_risks if pr.risk_score > 70]
        if high_risk_positions:
            recommendations.append(f"Review high-risk positions: {', '.join([pr.symbol for pr in high_risk_positions])}")
        
        if not recommendations:
            recommendations.append("Portfolio risk levels are acceptable")
        
        return recommendations
    
    def _categorize_risk_level(self, risk_assessment: Dict[str, Any]) -> str:
        """Categorize overall portfolio risk level"""
        
        var_95 = risk_assessment['portfolio_metrics']['var_95']
        violations = len(risk_assessment['risk_violations'])
        
        if var_95 > 10 or violations > 3:
            return "CRITICAL"
        elif var_95 > 7.5 or violations > 1:
            return "HIGH"
        elif var_95 > 5.0 or violations > 0:
            return "MODERATE"
        else:
            return "LOW"
    
    def _generate_risk_alerts(self, risk_assessment: Dict[str, Any]) -> List[str]:
        """Generate immediate risk alerts"""
        
        alerts = []
        
        # High priority alerts from violations
        for violation in risk_assessment['risk_violations']:
            alerts.append(f"⚠️ {violation}")
        
        # Portfolio-level alerts
        var_95 = risk_assessment['portfolio_metrics']['var_95']
        if var_95 > 8.0:
            alerts.append(f"🔴 High VaR: {var_95:.2f}% - Consider reducing exposure")
        
        volatility = risk_assessment['portfolio_metrics']['volatility']
        if volatility > 25.0:
            alerts.append(f"📈 High Volatility: {volatility:.2f}% - Monitor positions closely")
        
        return alerts[:5]  # Limit to top 5 alerts
    
    def _identify_top_risks(self, risk_assessment: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify top portfolio risks"""
        
        top_risks = []
        
        # Sort position risks by risk score
        position_risks = risk_assessment.get('position_risks', [])
        sorted_risks = sorted(position_risks, key=lambda x: x['risk_score'], reverse=True)
        
        for risk in sorted_risks[:3]:  # Top 3 risky positions
            top_risks.append({
                'type': 'Position Risk',
                'symbol': risk['symbol'],
                'risk_score': risk['risk_score'],
                'description': f"High risk position ({risk['risk_score']:.1f}% risk score)"
            })
        
        # Add portfolio-level risks
        portfolio_metrics = risk_assessment['portfolio_metrics']
        
        if portfolio_metrics['concentration_risk'] > 60:
            top_risks.append({
                'type': 'Concentration Risk',
                'symbol': 'PORTFOLIO',
                'risk_score': portfolio_metrics['concentration_risk'],
                'description': f"Portfolio concentration risk ({portfolio_metrics['concentration_risk']:.1f}%)"
            })
        
        return top_risks
    
    def _calculate_risk_attribution(self, risk_assessment: Dict[str, Any]) -> Dict[str, float]:
        """Calculate risk attribution by source"""
        
        total_var = risk_assessment['portfolio_metrics']['var_95']
        position_risks = risk_assessment.get('position_risks', [])
        
        attribution = {}
        
        for position in position_risks:
            contribution = abs(position['var_contribution'])
            if total_var > 0:
                attribution[position['symbol']] = (contribution / total_var) * 100
            else:
                attribution[position['symbol']] = 0
        
        return attribution
    
    def _get_limits_status(self, risk_assessment: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Get comprehensive status of all portfolio risk limits"""
        
        portfolio_metrics = risk_assessment['portfolio_metrics']
        
        limits_status = {
            'var_95': {
                'current': portfolio_metrics['var_95'],
                'limit': self.max_portfolio_var_95 * 100,
                'utilization': portfolio_metrics['var_95'] / (self.max_portfolio_var_95 * 100) * 100,
                'status': 'OK' if portfolio_metrics['var_95'] <= self.max_portfolio_var_95 * 100 else 'BREACH',
                'severity': self._get_breach_severity(portfolio_metrics['var_95'], self.max_portfolio_var_95 * 100)
            },
            'volatility': {
                'current': portfolio_metrics['volatility'],
                'limit': self.max_portfolio_volatility * 100,
                'utilization': portfolio_metrics['volatility'] / (self.max_portfolio_volatility * 100) * 100,
                'status': 'OK' if portfolio_metrics['volatility'] <= self.max_portfolio_volatility * 100 else 'BREACH',
                'severity': self._get_breach_severity(portfolio_metrics['volatility'], self.max_portfolio_volatility * 100)
            },
            'max_drawdown': {
                'current': portfolio_metrics['max_drawdown'],
                'limit': self.max_drawdown * 100,
                'utilization': portfolio_metrics['max_drawdown'] / (self.max_drawdown * 100) * 100,
                'status': 'OK' if portfolio_metrics['max_drawdown'] <= self.max_drawdown * 100 else 'BREACH',
                'severity': self._get_breach_severity(portfolio_metrics['max_drawdown'], self.max_drawdown * 100)
            },
            'concentration_risk': {
                'current': portfolio_metrics['concentration_risk'] * 100,
                'limit': self.max_sector_concentration * 100,
                'utilization': portfolio_metrics['concentration_risk'] / self.max_sector_concentration * 100,
                'status': 'OK' if portfolio_metrics['concentration_risk'] <= self.max_sector_concentration else 'BREACH',
                'severity': self._get_breach_severity(portfolio_metrics['concentration_risk'], self.max_sector_concentration)
            },
            'correlation_risk': {
                'current': portfolio_metrics['correlation_risk'] * 100,
                'limit': self.correlation_threshold * 100,
                'utilization': portfolio_metrics['correlation_risk'] / self.correlation_threshold * 100,
                'status': 'OK' if portfolio_metrics['correlation_risk'] <= self.correlation_threshold else 'BREACH',
                'severity': self._get_breach_severity(portfolio_metrics['correlation_risk'], self.correlation_threshold)
            },
            'liquidity_risk': {
                'current': portfolio_metrics['liquidity_risk'] * 100,
                'limit': 80.0,  # 80% liquidity risk threshold
                'utilization': portfolio_metrics['liquidity_risk'] / 0.8 * 100,
                'status': 'OK' if portfolio_metrics['liquidity_risk'] <= 0.8 else 'BREACH',
                'severity': self._get_breach_severity(portfolio_metrics['liquidity_risk'], 0.8)
            },
            'daily_loss': {
                'current': self._get_daily_loss_percentage(),
                'limit': self.max_daily_loss * 100,
                'utilization': self._get_daily_loss_percentage() / (self.max_daily_loss * 100) * 100,
                'status': 'OK' if self._get_daily_loss_percentage() <= self.max_daily_loss * 100 else 'BREACH',
                'severity': self._get_breach_severity(self._get_daily_loss_percentage(), self.max_daily_loss * 100)
            }
        }
        
        return limits_status
    
    def _check_concentration_limits(self, positions: Dict[str, Dict[str, Any]]) -> List[str]:
        """Check portfolio concentration limits"""
        
        violations = []
        
        try:
            if not positions:
                return violations
            
            total_value = sum(pos['market_value'] for pos in positions.values())
            if total_value <= 0:
                return violations
            
            # Check individual position concentration
            for symbol, position in positions.items():
                weight = position['market_value'] / total_value
                if weight > self.max_single_position:
                    violations.append(
                        f"Position {symbol} ({weight:.2%}) exceeds maximum single position limit ({self.max_single_position:.2%})"
                    )
                    self._record_risk_breach('single_position', weight * 100, self.max_single_position * 100)
            
            # Check sector concentration (simplified - would need sector mapping in production)
            # For now, check if too many positions in similar symbols (e.g., tech stocks)
            symbol_groups = self._group_symbols_by_sector(positions.keys())
            for sector, symbols in symbol_groups.items():
                sector_weight = sum(positions[sym]['market_value'] for sym in symbols) / total_value
                if sector_weight > self.max_sector_concentration:
                    violations.append(
                        f"Sector {sector} concentration ({sector_weight:.2%}) exceeds limit ({self.max_sector_concentration:.2%})"
                    )
                    self._record_risk_breach('sector_concentration', sector_weight * 100, self.max_sector_concentration * 100)
            
            return violations
            
        except Exception as e:
            self.logger.error(f"Concentration limit check failed: {e}")
            return [f"Concentration check failed: {str(e)}"]
    
    def _check_position_limits(self, positions: Dict[str, Dict[str, Any]]) -> List[str]:
        """Check position count and size limits"""
        
        violations = []
        
        try:
            # Position count check
            if len(positions) > self.max_positions:
                violations.append(
                    f"Position count ({len(positions)}) exceeds maximum limit ({self.max_positions})"
                )
                self._record_risk_breach('position_count', len(positions), self.max_positions)
            
            # Check for minimum position sizes (avoid dust positions)
            total_value = sum(pos['market_value'] for pos in positions.values())
            if total_value > 0:
                for symbol, position in positions.items():
                    weight = position['market_value'] / total_value
                    if weight < 0.001:  # Less than 0.1%
                        violations.append(
                            f"Position {symbol} ({weight:.3%}) is below minimum meaningful size (0.1%)"
                        )
            
            return violations
            
        except Exception as e:
            self.logger.error(f"Position limit check failed: {e}")
            return [f"Position check failed: {str(e)}"]
    
    def _check_leverage_limits(self, positions: Dict[str, Dict[str, Any]]) -> List[str]:
        """Check portfolio leverage limits"""
        
        violations = []
        
        try:
            # Calculate current leverage
            portfolio_summary = self.data_service.get_portfolio_summary()
            total_value = portfolio_summary.get('total_open_value', 0)
            cash = portfolio_summary.get('cash', 0)
            
            if cash > 0:
                leverage = total_value / (total_value + cash)
                if leverage > self.max_leverage:
                    violations.append(
                        f"Portfolio leverage ({leverage:.2f}x) exceeds maximum limit ({self.max_leverage:.2f}x)"
                    )
                    self._record_risk_breach('leverage', leverage, self.max_leverage)
            
            return violations
            
        except Exception as e:
            self.logger.error(f"Leverage limit check failed: {e}")
            return []
    
    def _check_cash_reserve_limits(self) -> List[str]:
        """Check minimum cash reserve requirements"""
        
        violations = []
        
        try:
            portfolio_summary = self.data_service.get_portfolio_summary()
            total_value = portfolio_summary.get('total_open_value', 0)
            cash = portfolio_summary.get('cash', 0)
            
            total_portfolio_value = total_value + cash
            
            if total_portfolio_value > 0:
                cash_ratio = cash / total_portfolio_value
                if cash_ratio < self.min_cash_reserve:
                    violations.append(
                        f"Cash reserve ({cash_ratio:.2%}) below minimum requirement ({self.min_cash_reserve:.2%})"
                    )
                    self._record_risk_breach('cash_reserve', cash_ratio * 100, self.min_cash_reserve * 100)
            
            return violations
            
        except Exception as e:
            self.logger.error(f"Cash reserve check failed: {e}")
            return []
    
    def _check_daily_loss_limits(self) -> List[str]:
        """Check daily loss limits"""
        
        violations = []
        
        try:
            portfolio_summary = self.data_service.get_portfolio_summary()
            daily_pnl = portfolio_summary.get('unrealized_pnl', 0)
            total_value = portfolio_summary.get('total_open_value', 0)
            
            if total_value > 0:
                daily_loss_pct = abs(min(daily_pnl, 0)) / total_value
                if daily_loss_pct > self.max_daily_loss:
                    violations.append(
                        f"Daily loss ({daily_loss_pct:.2%}) exceeds maximum limit ({self.max_daily_loss:.2%})"
                    )
                    self._record_risk_breach('daily_loss', daily_loss_pct * 100, self.max_daily_loss * 100)
            
            return violations
            
        except Exception as e:
            self.logger.error(f"Daily loss limit check failed: {e}")
            return []
    
    def _check_emergency_stop_conditions(self, portfolio_risk: RiskMetrics, 
                                       positions: Dict[str, Dict[str, Any]]) -> List[str]:
        """Check for emergency stop conditions"""
        
        violations = []
        
        try:
            # Critical VaR breach
            if portfolio_risk.var_95 > 20.0:  # 20% VaR triggers emergency stop
                violations.append("EMERGENCY: Portfolio VaR exceeds critical threshold (20%)")
                self._trigger_emergency_stop("Critical VaR breach")
            
            # Critical drawdown
            if portfolio_risk.max_drawdown > 25.0:  # 25% drawdown triggers emergency stop
                violations.append("EMERGENCY: Portfolio drawdown exceeds critical threshold (25%)")
                self._trigger_emergency_stop("Critical drawdown")
            
            # Rapid loss detection (would need historical data in production)
            daily_loss_pct = self._get_daily_loss_percentage()
            if daily_loss_pct > 10.0:  # 10% single day loss
                violations.append("EMERGENCY: Single day loss exceeds critical threshold (10%)")
                self._trigger_emergency_stop("Rapid loss event")
            
            # Market volatility spike (simplified check)
            if portfolio_risk.volatility > 100.0:  # 100% annualized volatility
                violations.append("EMERGENCY: Portfolio volatility at dangerous levels")
                self._trigger_emergency_stop("Extreme volatility")
            
            return violations
            
        except Exception as e:
            self.logger.error(f"Emergency stop condition check failed: {e}")
            return []
    
    def _record_risk_breach(self, metric: str, current_value: float, limit_value: float):
        """Record a risk limit breach"""
        
        breach_info = {
            'timestamp': datetime.now().isoformat(),
            'metric': metric,
            'current_value': current_value,
            'limit_value': limit_value,
            'severity': self._get_breach_severity(current_value, limit_value)
        }
        
        self.risk_breaches[metric] = breach_info
        self.logger.warning(f"Risk breach recorded: {metric} = {current_value:.2f} (limit: {limit_value:.2f})")
    
    def _get_breach_severity(self, current_value: float, limit_value: float) -> str:
        """Determine severity of a risk limit breach"""
        
        if limit_value <= 0:
            return "UNKNOWN"
        
        ratio = current_value / limit_value
        
        if ratio <= 0.8:
            return "LOW"
        elif ratio <= 1.0:
            return "MEDIUM"
        elif ratio <= 1.2:
            return "HIGH"
        else:
            return "CRITICAL"
    
    def _trigger_emergency_stop(self, reason: str):
        """Trigger emergency stop for all trading operations"""
        
        if not self.emergency_stop_triggered:
            self.emergency_stop_triggered = True
            self.emergency_stop_reason = reason
            self.logger.critical(f"EMERGENCY STOP TRIGGERED: {reason}")
            
            # In production, this would halt all trading operations
            # For now, just log the event
    
    def _group_symbols_by_sector(self, symbols: List[str]) -> Dict[str, List[str]]:
        """Group symbols by sector (simplified implementation)"""
        
        # This is a simplified mapping - in production, you'd use a proper sector classification
        sector_mapping = {
            'TECH': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA'],
            'FINANCE': ['JPM', 'BAC', 'WFC', 'GS', 'MS', 'C'],
            'HEALTHCARE': ['JNJ', 'PFE', 'UNH', 'MRNA', 'ABBV'],
            'ENERGY': ['XOM', 'CVX', 'COP', 'EOG'],
            'CONSUMER': ['WMT', 'HD', 'PG', 'KO', 'PEP'],
            'ETFS': ['SPY', 'QQQ', 'IWM', 'VTI', 'EFA']
        }
        
        grouped = {}
        unclassified = []
        
        for symbol in symbols:
            classified = False
            for sector, sector_symbols in sector_mapping.items():
                if symbol in sector_symbols:
                    if sector not in grouped:
                        grouped[sector] = []
                    grouped[sector].append(symbol)
                    classified = True
                    break
            
            if not classified:
                unclassified.append(symbol)
        
        if unclassified:
            grouped['OTHER'] = unclassified
        
        return grouped
    
    def _get_daily_loss_percentage(self) -> float:
        """Get current daily loss percentage"""
        
        try:
            portfolio_summary = self.data_service.get_portfolio_summary()
            daily_pnl = portfolio_summary.get('unrealized_pnl', 0)
            total_value = portfolio_summary.get('total_open_value', 0)
            
            if total_value > 0 and daily_pnl < 0:
                return abs(daily_pnl) / total_value * 100
            else:
                return 0.0
                
        except Exception as e:
            self.logger.error(f"Failed to get daily loss percentage: {e}")
            return 0.0
    
    def is_emergency_stop_active(self) -> bool:
        """Check if emergency stop is currently active"""
        return self.emergency_stop_triggered
    
    def reset_emergency_stop(self) -> bool:
        """Reset emergency stop (requires manual intervention)"""
        
        try:
            self.emergency_stop_triggered = False
            self.emergency_stop_reason = None
            self.logger.info("Emergency stop has been manually reset")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to reset emergency stop: {e}")
            return False
    
    def get_risk_breach_summary(self) -> Dict[str, Any]:
        """Get summary of recent risk breaches"""
        
        return {
            'active_breaches': len(self.risk_breaches),
            'breaches': self.risk_breaches,
            'emergency_stop_active': self.emergency_stop_triggered,
            'emergency_stop_reason': self.emergency_stop_reason,
            'last_risk_check': self.last_risk_check.isoformat() if self.last_risk_check else None
        }

# Global risk management service instance
_risk_service = None

def get_risk_service() -> RiskManagementService:
    """Get singleton risk management service instance"""
    global _risk_service
    if _risk_service is None:
        _risk_service = RiskManagementService()
    return _risk_service