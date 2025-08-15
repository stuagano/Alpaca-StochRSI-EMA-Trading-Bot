import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

# Optional scipy import
try:
    from scipy.optimize import minimize
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    minimize = None

class PositionSizingMethod(Enum):
    """Position sizing methods"""
    FIXED_PERCENTAGE = "fixed_percentage"
    VOLATILITY_ADJUSTED = "volatility_adjusted"
    KELLY_CRITERION = "kelly_criterion"
    RISK_PARITY = "risk_parity"
    MAX_DRAWDOWN_BASED = "max_drawdown_based"
    ATR_BASED = "atr_based"

@dataclass
class PositionSizeRecommendation:
    """Position size recommendation"""
    symbol: str
    recommended_size: float
    max_safe_size: float
    risk_adjusted_size: float
    method_used: str
    risk_per_trade: float
    stop_loss_distance: float
    confidence_score: float
    warnings: List[str]

class DynamicPositionSizer:
    """
    Advanced position sizing with multiple methods and risk controls
    """
    
    def __init__(self):
        self.logger = logging.getLogger('risk.position_sizer')
        
        # Risk parameters
        self.max_risk_per_trade = 0.02  # 2% max risk per trade
        self.max_portfolio_risk = 0.20  # 20% max portfolio risk
        self.max_correlation_allocation = 0.60  # 60% max in correlated assets
        self.min_position_size = 0.001  # Minimum position size
        self.max_position_size = 0.20   # Maximum position size (20% of portfolio)
        
    def calculate_position_size(self, 
                              symbol: str,
                              entry_price: float,
                              stop_loss_price: float,
                              portfolio_value: float,
                              method: PositionSizingMethod = PositionSizingMethod.VOLATILITY_ADJUSTED,
                              historical_data: pd.DataFrame = None,
                              **kwargs) -> PositionSizeRecommendation:
        """
        Calculate optimal position size using specified method
        
        Args:
            symbol: Trading symbol
            entry_price: Intended entry price
            stop_loss_price: Stop loss price
            portfolio_value: Current portfolio value
            method: Position sizing method to use
            historical_data: Historical price data for the symbol
            **kwargs: Additional parameters for specific methods
            
        Returns:
            PositionSizeRecommendation object
        """
        
        self.logger.info(f"Calculating position size for {symbol} using {method.value}")
        
        try:
            warnings = []
            
            # Basic risk calculations
            stop_loss_distance = abs(entry_price - stop_loss_price) / entry_price
            
            if stop_loss_distance < 0.005:  # Less than 0.5%
                warnings.append("Very tight stop loss - consider wider stop")
            elif stop_loss_distance > 0.20:  # More than 20%
                warnings.append("Very wide stop loss - high risk per trade")
            
            # Validate all inputs before calculation
            if entry_price <= 0:
                raise ValueError(f"Invalid entry price: {entry_price}")
            if stop_loss_price <= 0:
                raise ValueError(f"Invalid stop loss price: {stop_loss_price}")
            if portfolio_value <= 0:
                raise ValueError(f"Invalid portfolio value: {portfolio_value}")
            
            # Calculate position size based on method
            if method == PositionSizingMethod.FIXED_PERCENTAGE:
                recommended_size = self._fixed_percentage_sizing(
                    portfolio_value, entry_price, **kwargs
                )
            
            elif method == PositionSizingMethod.VOLATILITY_ADJUSTED:
                recommended_size = self._volatility_adjusted_sizing(
                    symbol, entry_price, stop_loss_price, portfolio_value, 
                    historical_data, **kwargs
                )
            
            elif method == PositionSizingMethod.KELLY_CRITERION:
                recommended_size = self._kelly_criterion_sizing(
                    symbol, entry_price, stop_loss_price, portfolio_value,
                    historical_data, **kwargs
                )
            
            elif method == PositionSizingMethod.RISK_PARITY:
                recommended_size = self._risk_parity_sizing(
                    symbol, entry_price, portfolio_value, historical_data, **kwargs
                )
            
            elif method == PositionSizingMethod.ATR_BASED:
                recommended_size = self._atr_based_sizing(
                    symbol, entry_price, portfolio_value, historical_data, **kwargs
                )
            
            else:
                # Default to fixed percentage
                recommended_size = self._fixed_percentage_sizing(
                    portfolio_value, entry_price
                )
            
            # Ensure recommended size is never negative or NaN
            if recommended_size <= 0 or pd.isna(recommended_size):
                self.logger.warning(f"Invalid recommended size: {recommended_size}, using minimum")
                recommended_size = self.min_position_size
            
            # Apply risk controls
            max_safe_size = self._calculate_max_safe_size(
                entry_price, stop_loss_price, portfolio_value
            )
            
            risk_adjusted_size = min(recommended_size, max_safe_size)
            
            # Additional safety checks
            risk_adjusted_size = max(risk_adjusted_size, self.min_position_size)
            risk_adjusted_size = min(risk_adjusted_size, self.max_position_size)
            
            # Calculate actual risk per trade
            position_value = risk_adjusted_size * portfolio_value
            max_loss = position_value * stop_loss_distance
            risk_per_trade = max_loss / portfolio_value
            
            # Confidence score based on data quality and risk levels
            confidence_score = self._calculate_confidence_score(
                historical_data, stop_loss_distance, risk_per_trade, method
            )
            
            # Additional warnings
            if risk_per_trade > self.max_risk_per_trade:
                warnings.append(f"Risk per trade ({risk_per_trade:.2%}) exceeds limit ({self.max_risk_per_trade:.2%})")
            
            if risk_adjusted_size < recommended_size * 0.5:
                warnings.append("Position size significantly reduced due to risk controls")
            
            recommendation = PositionSizeRecommendation(
                symbol=symbol,
                recommended_size=recommended_size,
                max_safe_size=max_safe_size,
                risk_adjusted_size=risk_adjusted_size,
                method_used=method.value,
                risk_per_trade=risk_per_trade,
                stop_loss_distance=stop_loss_distance,
                confidence_score=confidence_score,
                warnings=warnings
            )
            
            self.logger.info(f"Position size calculated: {risk_adjusted_size:.3%} of portfolio "
                           f"({position_value:.0f} units), Risk: {risk_per_trade:.2%}")
            
            return recommendation
            
        except Exception as e:
            self.logger.error(f"Position size calculation failed for {symbol}: {e}")
            
            # Return conservative fallback
            return PositionSizeRecommendation(
                symbol=symbol,
                recommended_size=0.05,  # 5% fallback
                max_safe_size=0.05,
                risk_adjusted_size=0.05,
                method_used="fallback",
                risk_per_trade=0.01,
                stop_loss_distance=stop_loss_distance if 'stop_loss_distance' in locals() else 0.05,
                confidence_score=0.1,
                warnings=[f"Calculation failed: {str(e)}"]
            )
    
    def _fixed_percentage_sizing(self, portfolio_value: float, entry_price: float,
                               percentage: float = 0.05) -> float:
        """Fixed percentage position sizing"""
        return percentage
    
    def _volatility_adjusted_sizing(self, symbol: str, entry_price: float, 
                                  stop_loss_price: float, portfolio_value: float,
                                  historical_data: pd.DataFrame = None,
                                  target_volatility: float = 0.15) -> float:
        """Volatility-adjusted position sizing with enhanced validation"""
        
        try:
            # Input validation
            if entry_price <= 0 or stop_loss_price <= 0 or portfolio_value <= 0:
                self.logger.error(f"Invalid inputs: entry={entry_price}, stop={stop_loss_price}, portfolio={portfolio_value}")
                return self.min_position_size
            
            if historical_data is None or len(historical_data) < 30:
                self.logger.warning(f"Insufficient data for volatility calculation for {symbol}")
                return max(0.05, self.min_position_size)  # Default 5% or minimum
            
            # Calculate historical volatility with validation
            returns = historical_data['close'].pct_change().dropna()
            
            if len(returns) < 20:
                self.logger.warning(f"Insufficient return data for {symbol}")
                return max(0.05, self.min_position_size)
            
            volatility = returns.std() * np.sqrt(252)  # Annualized
            
            # Validate volatility calculation
            if volatility <= 0 or pd.isna(volatility) or np.isinf(volatility):
                self.logger.warning(f"Invalid volatility calculated for {symbol}: {volatility}")
                return max(0.05, self.min_position_size)
            
            # Cap extreme volatility values
            volatility = min(volatility, 2.0)  # Cap at 200% volatility
            volatility = max(volatility, 0.01)  # Minimum 1% volatility
            
            # Inverse volatility scaling with bounds
            target_volatility = max(target_volatility, 0.05)  # Minimum target volatility
            volatility_adjustment = target_volatility / volatility
            volatility_adjustment = min(volatility_adjustment, 5.0)  # Cap adjustment
            volatility_adjustment = max(volatility_adjustment, 0.2)  # Floor adjustment
            
            base_size = 0.10  # 10% base allocation
            adjusted_size = base_size * volatility_adjustment
            
            # Additional adjustment based on stop loss distance
            stop_distance = abs(entry_price - stop_loss_price) / entry_price
            stop_distance = max(stop_distance, 0.005)  # Minimum 0.5% stop
            stop_distance = min(stop_distance, 0.50)   # Maximum 50% stop
            
            if stop_distance > 0:
                # Smaller position for wider stops
                stop_adjustment = min(0.02 / stop_distance, 2.0)  # Cap at 2x
                stop_adjustment = max(stop_adjustment, 0.1)  # Floor at 0.1x
                adjusted_size *= stop_adjustment
            
            # Final validation and bounds
            adjusted_size = max(adjusted_size, self.min_position_size)
            adjusted_size = min(adjusted_size, self.max_position_size)
            
            self.logger.debug(f"Volatility sizing for {symbol}: vol={volatility:.3f}, adj={volatility_adjustment:.3f}, size={adjusted_size:.3f}")
            
            return adjusted_size
            
        except Exception as e:
            self.logger.error(f"Volatility-adjusted sizing failed for {symbol}: {e}")
            return max(0.05, self.min_position_size)
    
    def _kelly_criterion_sizing(self, symbol: str, entry_price: float,
                              stop_loss_price: float, portfolio_value: float,
                              historical_data: pd.DataFrame = None,
                              win_rate: float = None, avg_win: float = None,
                              avg_loss: float = None) -> float:
        """Kelly Criterion position sizing"""
        
        try:
            # If parameters not provided, estimate from historical data
            if historical_data is not None and len(historical_data) > 50:
                returns = historical_data['close'].pct_change().dropna()
                
                if win_rate is None or avg_win is None or avg_loss is None:
                    wins = returns[returns > 0]
                    losses = returns[returns < 0]
                    
                    win_rate = len(wins) / len(returns) if len(returns) > 0 else 0.5
                    avg_win = wins.mean() if len(wins) > 0 else 0.02
                    avg_loss = abs(losses.mean()) if len(losses) > 0 else 0.02
            
            # Default estimates if still not available
            if win_rate is None: win_rate = 0.55  # Slightly better than 50/50
            if avg_win is None: avg_win = 0.03    # 3% average win
            if avg_loss is None: avg_loss = 0.02  # 2% average loss
            
            # Kelly formula: f = (bp - q) / b
            # where b = avg_win/avg_loss, p = win_rate, q = 1-win_rate
            if avg_loss > 0:
                b = avg_win / avg_loss
                p = win_rate
                q = 1 - win_rate
                
                kelly_fraction = (b * p - q) / b
                
                # Apply Kelly fraction but with conservative scaling
                kelly_fraction = max(0, kelly_fraction)  # No negative positions
                kelly_fraction = min(kelly_fraction, 0.25)  # Cap at 25%
                
                # Use fractional Kelly (often 1/4 or 1/2 Kelly for safety)
                conservative_kelly = kelly_fraction * 0.5  # Half-Kelly
                
                return conservative_kelly
            else:
                return 0.05
                
        except Exception as e:
            self.logger.error(f"Kelly criterion sizing failed: {e}")
            return 0.05
    
    def _risk_parity_sizing(self, symbol: str, entry_price: float,
                          portfolio_value: float, historical_data: pd.DataFrame = None,
                          target_risk_contribution: float = 0.10) -> float:
        """Risk parity position sizing"""
        
        try:
            if historical_data is None or len(historical_data) < 30:
                return target_risk_contribution
            
            # Calculate asset volatility
            returns = historical_data['close'].pct_change().dropna()
            volatility = returns.std() * np.sqrt(252)
            
            if volatility <= 0:
                return target_risk_contribution
            
            # Risk parity: inverse volatility weighting
            # Higher volatility assets get smaller weights
            base_volatility = 0.15  # 15% reference volatility
            risk_parity_weight = base_volatility / volatility
            
            # Scale by target risk contribution
            position_size = risk_parity_weight * target_risk_contribution
            
            return min(position_size, 0.20)  # Cap at 20%
            
        except Exception as e:
            self.logger.error(f"Risk parity sizing failed: {e}")
            return target_risk_contribution
    
    def _atr_based_sizing(self, symbol: str, entry_price: float,
                        portfolio_value: float, historical_data: pd.DataFrame = None,
                        atr_multiplier: float = 2.0, target_risk: float = 0.02) -> float:
        """ATR-based position sizing with enhanced validation"""
        
        try:
            # Input validation
            if entry_price <= 0 or portfolio_value <= 0:
                self.logger.error(f"Invalid inputs for ATR sizing: entry={entry_price}, portfolio={portfolio_value}")
                return self.min_position_size
            
            if historical_data is None or len(historical_data) < 20:
                self.logger.warning(f"Insufficient data for ATR calculation for {symbol}")
                return max(0.05, self.min_position_size)
            
            # Validate required columns
            required_cols = ['high', 'low', 'close']
            if not all(col in historical_data.columns for col in required_cols):
                self.logger.error(f"Missing required columns for ATR calculation: {required_cols}")
                return max(0.05, self.min_position_size)
            
            # Calculate ATR (Average True Range) with validation
            high = historical_data['high']
            low = historical_data['low']
            close = historical_data['close']
            
            # Validate OHLC data consistency
            if len(high) != len(low) or len(high) != len(close):
                self.logger.error(f"Inconsistent OHLC data lengths for {symbol}")
                return max(0.05, self.min_position_size)
            
            # True Range calculation with validation
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            
            # Check for invalid price data
            if tr1.min() < 0 or tr2.isna().all() or tr3.isna().all():
                self.logger.warning(f"Invalid price data detected for {symbol}")
                return max(0.05, self.min_position_size)
            
            true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            
            # Calculate ATR with minimum periods
            atr_window = min(14, len(true_range) - 1)
            if atr_window < 5:
                self.logger.warning(f"Insufficient data for reliable ATR: {atr_window} periods")
                return max(0.05, self.min_position_size)
            
            atr = true_range.rolling(window=atr_window).mean().iloc[-1]
            
            # Validate ATR calculation
            if pd.isna(atr) or atr <= 0 or np.isinf(atr):
                self.logger.warning(f"Invalid ATR calculated for {symbol}: {atr}")
                return max(0.05, self.min_position_size)
            
            # Validate and bound ATR multiplier
            atr_multiplier = max(atr_multiplier, 0.5)  # Minimum 0.5x
            atr_multiplier = min(atr_multiplier, 5.0)  # Maximum 5x
            
            # Validate and bound target risk
            target_risk = max(target_risk, 0.005)  # Minimum 0.5% risk
            target_risk = min(target_risk, self.max_risk_per_trade)  # Respect class limit
            
            # Calculate stop distance based on ATR
            stop_distance = (atr_multiplier * atr) / entry_price
            
            # Validate stop distance
            if stop_distance <= 0 or pd.isna(stop_distance) or np.isinf(stop_distance):
                self.logger.warning(f"Invalid stop distance for {symbol}: {stop_distance}")
                return max(0.05, self.min_position_size)
            
            # Bound stop distance to reasonable ranges
            stop_distance = max(stop_distance, 0.005)  # Minimum 0.5%
            stop_distance = min(stop_distance, 0.50)   # Maximum 50%
            
            # Position size to risk target_risk of portfolio
            position_size = target_risk / stop_distance
            
            # Apply safety bounds
            position_size = max(position_size, self.min_position_size)
            position_size = min(position_size, self.max_position_size)
            
            self.logger.debug(f"ATR sizing for {symbol}: atr={atr:.6f}, stop_dist={stop_distance:.4f}, size={position_size:.4f}")
            
            return position_size
                
        except Exception as e:
            self.logger.error(f"ATR-based sizing failed for {symbol}: {e}")
            return max(0.05, self.min_position_size)
    
    def _calculate_max_safe_size(self, entry_price: float, stop_loss_price: float,
                               portfolio_value: float) -> float:
        """Calculate maximum safe position size based on risk limits"""
        
        # Validate inputs
        if entry_price <= 0:
            self.logger.error(f"Invalid entry price: {entry_price}")
            return 0.0
        
        if stop_loss_price <= 0:
            self.logger.error(f"Invalid stop loss price: {stop_loss_price}")
            return 0.0
            
        if portfolio_value <= 0:
            self.logger.error(f"Invalid portfolio value: {portfolio_value}")
            return 0.0
        
        stop_loss_distance = abs(entry_price - stop_loss_price) / entry_price
        
        # Ensure stop loss distance is reasonable (between 0.1% and 50%)
        if stop_loss_distance <= 0.001:  # Less than 0.1%
            self.logger.warning(f"Stop loss too tight: {stop_loss_distance:.4f}, using minimum 0.1%")
            stop_loss_distance = 0.001
        elif stop_loss_distance > 0.50:  # More than 50%
            self.logger.warning(f"Stop loss too wide: {stop_loss_distance:.4f}, capping at 50%")
            stop_loss_distance = 0.50
        
        # Maximum position size to not exceed max risk per trade
        max_size_risk = self.max_risk_per_trade / stop_loss_distance
        
        # Apply overall position size limit
        max_safe_size = min(max_size_risk, self.max_position_size)
        
        # Ensure position size is never negative or zero
        max_safe_size = max(max_safe_size, self.min_position_size)
        
        # Additional safety check - never exceed 25% of portfolio regardless of calculations
        max_safe_size = min(max_safe_size, 0.25)
        
        self.logger.debug(f"Max safe size calculated: {max_safe_size:.4f} for stop distance: {stop_loss_distance:.4f}")
        
        return max_safe_size
    
    def _calculate_confidence_score(self, historical_data: pd.DataFrame,
                                  stop_loss_distance: float, risk_per_trade: float,
                                  method: PositionSizingMethod) -> float:
        """Calculate confidence score for position size recommendation"""
        
        confidence = 0.5  # Base confidence
        
        # Data quality factor
        if historical_data is not None:
            data_length = len(historical_data)
            if data_length >= 252:  # 1 year of data
                confidence += 0.3
            elif data_length >= 60:  # 2+ months
                confidence += 0.2
            elif data_length >= 30:  # 1+ month
                confidence += 0.1
        
        # Risk level factor
        if risk_per_trade <= self.max_risk_per_trade:
            confidence += 0.1
        else:
            confidence -= 0.2
        
        # Stop loss reasonableness
        if 0.01 <= stop_loss_distance <= 0.10:  # 1-10% stop
            confidence += 0.1
        else:
            confidence -= 0.1
        
        # Method sophistication factor
        sophisticated_methods = [
            PositionSizingMethod.VOLATILITY_ADJUSTED,
            PositionSizingMethod.KELLY_CRITERION,
            PositionSizingMethod.RISK_PARITY
        ]
        
        if method in sophisticated_methods:
            confidence += 0.1
        
        return max(0.0, min(1.0, confidence))
    
    def calculate_portfolio_sizing(self, opportunities: List[Dict[str, Any]],
                                 portfolio_value: float,
                                 current_positions: Dict[str, float] = None) -> Dict[str, PositionSizeRecommendation]:
        """
        Calculate position sizes for multiple opportunities considering portfolio constraints
        
        Args:
            opportunities: List of trading opportunities with symbol, entry_price, stop_loss, etc.
            portfolio_value: Current portfolio value
            current_positions: Current position weights by symbol
            
        Returns:
            Dictionary of symbol -> PositionSizeRecommendation
        """
        
        if current_positions is None:
            current_positions = {}
        
        recommendations = {}
        total_new_allocation = 0
        
        # Calculate individual position sizes
        for opportunity in opportunities:
            symbol = opportunity['symbol']
            entry_price = opportunity['entry_price']
            stop_loss_price = opportunity.get('stop_loss_price', entry_price * 0.95)
            method = opportunity.get('method', PositionSizingMethod.VOLATILITY_ADJUSTED)
            historical_data = opportunity.get('historical_data')
            
            # Calculate position size
            recommendation = self.calculate_position_size(
                symbol=symbol,
                entry_price=entry_price,
                stop_loss_price=stop_loss_price,
                portfolio_value=portfolio_value,
                method=method,
                historical_data=historical_data,
                **opportunity.get('kwargs', {})
            )
            
            recommendations[symbol] = recommendation
            total_new_allocation += recommendation.risk_adjusted_size
        
        # Check portfolio-level constraints
        current_allocation = sum(current_positions.values())
        total_allocation = current_allocation + total_new_allocation
        
        if total_allocation > 1.0:  # Over-allocated
            # Scale down new positions proportionally
            scale_factor = (1.0 - current_allocation) / total_new_allocation
            scale_factor = max(0.1, scale_factor)  # Minimum 10% scaling
            
            for symbol in recommendations:
                old_size = recommendations[symbol].risk_adjusted_size
                new_size = old_size * scale_factor
                
                # Update recommendation
                recommendations[symbol].risk_adjusted_size = new_size
                recommendations[symbol].warnings.append(
                    f"Position scaled down by {scale_factor:.2%} due to portfolio constraints"
                )
        
        self.logger.info(f"Portfolio sizing calculated for {len(recommendations)} opportunities")
        
        return recommendations

class RiskAdjustedRebalancer:
    """
    Portfolio rebalancing with risk considerations
    """
    
    def __init__(self):
        self.logger = logging.getLogger('risk.rebalancer')
        self.position_sizer = DynamicPositionSizer()
    
    def calculate_rebalancing_trades(self, current_portfolio: Dict[str, float],
                                   target_portfolio: Dict[str, float],
                                   portfolio_value: float,
                                   price_data: Dict[str, float],
                                   min_trade_threshold: float = 0.01) -> List[Dict[str, Any]]:
        """
        Calculate trades needed to rebalance portfolio to target weights
        
        Args:
            current_portfolio: Current weights by symbol
            target_portfolio: Target weights by symbol
            portfolio_value: Total portfolio value
            price_data: Current prices by symbol
            min_trade_threshold: Minimum weight difference to trigger trade
            
        Returns:
            List of trade recommendations
        """
        
        trades = []
        
        # Find all symbols in either portfolio
        all_symbols = set(current_portfolio.keys()) | set(target_portfolio.keys())
        
        for symbol in all_symbols:
            current_weight = current_portfolio.get(symbol, 0.0)
            target_weight = target_portfolio.get(symbol, 0.0)
            weight_diff = target_weight - current_weight
            
            # Only trade if difference exceeds threshold
            if abs(weight_diff) >= min_trade_threshold:
                current_price = price_data.get(symbol, 100.0)  # Default price
                
                # Calculate trade size
                trade_value = abs(weight_diff) * portfolio_value
                trade_quantity = trade_value / current_price
                
                trade_type = "BUY" if weight_diff > 0 else "SELL"
                
                trade = {
                    'symbol': symbol,
                    'action': trade_type,
                    'quantity': trade_quantity,
                    'value': trade_value,
                    'current_weight': current_weight,
                    'target_weight': target_weight,
                    'weight_change': weight_diff,
                    'price': current_price
                }
                
                trades.append(trade)
        
        # Sort by trade value (largest first)
        trades.sort(key=lambda x: x['value'], reverse=True)
        
        self.logger.info(f"Calculated {len(trades)} rebalancing trades")
        
        return trades
    
    def optimize_trade_execution(self, trades: List[Dict[str, Any]],
                               market_impact_model: callable = None) -> List[Dict[str, Any]]:
        """
        Optimize trade execution order and timing
        """
        
        if not trades:
            return []
        
        # Simple optimization: execute sells before buys to free up cash
        sells = [trade for trade in trades if trade['action'] == 'SELL']
        buys = [trade for trade in trades if trade['action'] == 'BUY']
        
        # Sort sells by liquidity (larger positions first)
        sells.sort(key=lambda x: x['value'], reverse=True)
        
        # Sort buys by priority (smaller positions first to minimize impact)
        buys.sort(key=lambda x: x['value'])
        
        optimized_trades = sells + buys
        
        # Add execution timing recommendations
        for i, trade in enumerate(optimized_trades):
            trade['execution_order'] = i + 1
            trade['execution_priority'] = 'HIGH' if i < 3 else 'NORMAL'
            
            # Add market impact estimate
            if market_impact_model:
                trade['estimated_impact'] = market_impact_model(trade)
            else:
                # Simple impact estimate based on trade size
                impact_pct = min(trade['value'] / 1000000 * 0.001, 0.005)  # Max 0.5%
                trade['estimated_impact'] = impact_pct
        
        return optimized_trades