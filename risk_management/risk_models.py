import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import warnings

# Optional scipy imports
try:
    from scipy import stats
    from scipy.optimize import minimize
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    stats = None
    minimize = None

@dataclass
class RiskMetrics:
    """Container for risk metrics"""
    var_95: float = 0.0
    var_99: float = 0.0
    cvar_95: float = 0.0
    cvar_99: float = 0.0
    max_drawdown: float = 0.0
    volatility: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    beta: float = 0.0
    correlation_risk: float = 0.0
    concentration_risk: float = 0.0
    liquidity_risk: float = 0.0
    
@dataclass 
class PositionRisk:
    """Risk assessment for individual position"""
    symbol: str
    position_size: float
    market_value: float
    weight: float
    var_contribution: float
    beta: float
    volatility: float
    correlation_risk: float
    liquidity_score: float
    risk_score: float

class VolatilityModel:
    """
    Advanced volatility modeling using various methods
    """
    
    def __init__(self):
        self.logger = logging.getLogger('risk.volatility')
        
    def garch_volatility(self, returns: pd.Series, window: int = 252) -> pd.Series:
        """
        GARCH(1,1) volatility estimation
        Simplified implementation for educational purposes
        """
        
        try:
            # Parameters for GARCH(1,1): omega + alpha * lag_resid^2 + beta * lag_vol^2
            omega = 0.000001  # Base volatility
            alpha = 0.1       # Reaction to market shocks
            beta = 0.85       # Persistence of volatility
            
            # Initialize
            volatility = pd.Series(index=returns.index, dtype=float)
            volatility.iloc[0] = returns.std()
            
            # Calculate GARCH volatility
            for i in range(1, len(returns)):
                lag_return = returns.iloc[i-1] ** 2
                lag_vol = volatility.iloc[i-1] ** 2
                
                volatility.iloc[i] = np.sqrt(
                    omega + alpha * lag_return + beta * lag_vol
                )
            
            self.logger.debug(f"GARCH volatility calculated for {len(returns)} observations")
            return volatility * np.sqrt(252)  # Annualized
            
        except Exception as e:
            self.logger.error(f"GARCH volatility calculation failed: {e}")
            return returns.rolling(window=min(window, len(returns))).std() * np.sqrt(252)
    
    def ewma_volatility(self, returns: pd.Series, lambda_decay: float = 0.94) -> pd.Series:
        """
        Exponentially Weighted Moving Average volatility
        """
        
        try:
            # Initialize with first return squared
            ewma_var = returns.iloc[0] ** 2
            volatility = [np.sqrt(ewma_var)]
            
            # Calculate EWMA variance
            for ret in returns.iloc[1:]:
                ewma_var = lambda_decay * ewma_var + (1 - lambda_decay) * ret ** 2
                volatility.append(np.sqrt(ewma_var))
            
            result = pd.Series(volatility, index=returns.index) * np.sqrt(252)
            self.logger.debug(f"EWMA volatility calculated with lambda={lambda_decay}")
            return result
            
        except Exception as e:
            self.logger.error(f"EWMA volatility calculation failed: {e}")
            return returns.rolling(window=30).std() * np.sqrt(252)
    
    def realized_volatility(self, prices: pd.Series, window: int = 30) -> pd.Series:
        """
        Realized volatility from high-frequency data
        """
        
        try:
            returns = prices.pct_change().dropna()
            realized_vol = returns.rolling(window=window).std() * np.sqrt(252)
            
            self.logger.debug(f"Realized volatility calculated with window={window}")
            return realized_vol
            
        except Exception as e:
            self.logger.error(f"Realized volatility calculation failed: {e}")
            return pd.Series(index=prices.index, dtype=float).fillna(0.2)  # 20% default

class ValueAtRisk:
    """
    Comprehensive Value at Risk calculations
    """
    
    def __init__(self):
        self.logger = logging.getLogger('risk.var')
        
    def parametric_var(self, returns: pd.Series, 
                      confidence_level: float = 0.95,
                      holding_period: int = 1) -> float:
        """
        Parametric VaR assuming normal distribution
        """
        
        try:
            if len(returns) < 30:
                self.logger.warning("Insufficient data for reliable VaR calculation")
                return 0.0
            
            if not SCIPY_AVAILABLE:
                self.logger.warning("SciPy not available, using simplified VaR calculation")
                # Simple approximation: -2 std dev for ~95% confidence
                std_return = returns.std()
                var = 2 * std_return * np.sqrt(holding_period)
                return var
            
            # Calculate statistics
            mean_return = returns.mean()
            std_return = returns.std()
            
            # Get critical value from normal distribution
            alpha = 1 - confidence_level
            z_score = stats.norm.ppf(alpha)
            
            # Calculate VaR
            var = -(mean_return + z_score * std_return) * np.sqrt(holding_period)
            
            self.logger.debug(f"Parametric VaR calculated: {var:.4f}")
            return var
            
        except Exception as e:
            self.logger.error(f"Parametric VaR calculation failed: {e}")
            return 0.05  # Default 5% VaR
    
    def historical_var(self, returns: pd.Series, 
                      confidence_level: float = 0.95,
                      holding_period: int = 1) -> float:
        """
        Historical simulation VaR
        """
        
        try:
            if len(returns) < 100:
                self.logger.warning("Insufficient data for historical VaR")
                return self.parametric_var(returns, confidence_level, holding_period)
            
            # Adjust returns for holding period
            if holding_period > 1:
                adjusted_returns = returns * np.sqrt(holding_period)
            else:
                adjusted_returns = returns
            
            # Calculate percentile
            alpha = 1 - confidence_level
            var = -np.percentile(adjusted_returns, alpha * 100)
            
            self.logger.debug(f"Historical VaR calculated: {var:.4f}")
            return var
            
        except Exception as e:
            self.logger.error(f"Historical VaR calculation failed: {e}")
            return self.parametric_var(returns, confidence_level, holding_period)
    
    def monte_carlo_var(self, returns: pd.Series, 
                       confidence_level: float = 0.95,
                       holding_period: int = 1,
                       num_simulations: int = 10000) -> float:
        """
        Monte Carlo simulation VaR
        """
        
        try:
            if len(returns) < 30:
                return self.parametric_var(returns, confidence_level, holding_period)
            
            # Estimate parameters
            mean_return = returns.mean()
            std_return = returns.std()
            
            # Generate random scenarios
            np.random.seed(42)  # For reproducible results
            simulated_returns = np.random.normal(
                mean_return * holding_period,
                std_return * np.sqrt(holding_period),
                num_simulations
            )
            
            # Calculate VaR
            alpha = 1 - confidence_level
            var = -np.percentile(simulated_returns, alpha * 100)
            
            self.logger.debug(f"Monte Carlo VaR calculated with {num_simulations} simulations")
            return var
            
        except Exception as e:
            self.logger.error(f"Monte Carlo VaR calculation failed: {e}")
            return self.parametric_var(returns, confidence_level, holding_period)
    
    def conditional_var(self, returns: pd.Series, 
                       confidence_level: float = 0.95,
                       holding_period: int = 1) -> float:
        """
        Conditional VaR (Expected Shortfall)
        """
        
        try:
            # First calculate VaR
            var_threshold = self.historical_var(returns, confidence_level, holding_period)
            
            # Adjust returns for holding period
            if holding_period > 1:
                adjusted_returns = returns * np.sqrt(holding_period)
            else:
                adjusted_returns = returns
            
            # Calculate expected value of returns beyond VaR threshold
            tail_returns = adjusted_returns[adjusted_returns <= -var_threshold]
            
            if len(tail_returns) > 0:
                cvar = -tail_returns.mean()
            else:
                if SCIPY_AVAILABLE:
                    # Fallback to parametric estimation
                    alpha = 1 - confidence_level
                    z_score = stats.norm.ppf(alpha)
                    mean_return = adjusted_returns.mean()
                    std_return = adjusted_returns.std()
                    
                    # Expected shortfall formula for normal distribution
                    cvar = -(mean_return - std_return * stats.norm.pdf(z_score) / alpha)
                else:
                    # Simple approximation without scipy
                    cvar = var_threshold * 1.3  # Approximately 30% worse than VaR
            
            self.logger.debug(f"Conditional VaR calculated: {cvar:.4f}")
            return cvar
            
        except Exception as e:
            self.logger.error(f"Conditional VaR calculation failed: {e}")
            return self.historical_var(returns, confidence_level, holding_period) * 1.3

class PortfolioRiskAnalyzer:
    """
    Comprehensive portfolio-level risk analysis
    """
    
    def __init__(self):
        self.logger = logging.getLogger('risk.portfolio')
        self.volatility_model = VolatilityModel()
        self.var_model = ValueAtRisk()
        
    def calculate_portfolio_risk(self, positions: Dict[str, Dict[str, Any]], 
                               market_data: Dict[str, pd.DataFrame],
                               benchmark_data: pd.DataFrame = None) -> RiskMetrics:
        """
        Calculate comprehensive portfolio risk metrics
        """
        
        self.logger.info("Calculating portfolio risk metrics")
        
        try:
            if not positions:
                return RiskMetrics()
            
            # Calculate portfolio returns
            portfolio_returns = self._calculate_portfolio_returns(positions, market_data)
            
            if len(portfolio_returns) < 30:
                self.logger.warning("Insufficient data for comprehensive risk analysis")
                return RiskMetrics()
            
            # Basic risk metrics
            volatility = portfolio_returns.std() * np.sqrt(252) * 100  # Annualized %
            
            # VaR calculations
            var_95 = self.var_model.historical_var(portfolio_returns, 0.95) * 100
            var_99 = self.var_model.historical_var(portfolio_returns, 0.99) * 100
            cvar_95 = self.var_model.conditional_var(portfolio_returns, 0.95) * 100
            cvar_99 = self.var_model.conditional_var(portfolio_returns, 0.99) * 100
            
            # Drawdown analysis
            cumulative_returns = (1 + portfolio_returns).cumprod()
            running_max = cumulative_returns.expanding().max()
            drawdown = (cumulative_returns - running_max) / running_max
            max_drawdown = abs(drawdown.min()) * 100
            
            # Performance ratios
            mean_return = portfolio_returns.mean()
            risk_free_rate = 0.02 / 252  # 2% annual risk-free rate
            
            sharpe_ratio = (mean_return - risk_free_rate) / portfolio_returns.std() * np.sqrt(252) if portfolio_returns.std() > 0 else 0
            
            # Sortino ratio (downside deviation)
            downside_returns = portfolio_returns[portfolio_returns < risk_free_rate]
            downside_std = downside_returns.std() if len(downside_returns) > 0 else portfolio_returns.std()
            sortino_ratio = (mean_return - risk_free_rate) / downside_std * np.sqrt(252) if downside_std > 0 else 0
            
            # Calmar ratio
            annualized_return = (1 + mean_return) ** 252 - 1
            calmar_ratio = annualized_return / (max_drawdown / 100) if max_drawdown > 0 else 0
            
            # Beta calculation (if benchmark provided)
            beta = 0.0
            if benchmark_data is not None:
                benchmark_returns = benchmark_data['close'].pct_change().dropna()
                if len(benchmark_returns) > 0:
                    aligned_portfolio, aligned_benchmark = portfolio_returns.align(benchmark_returns, join='inner')
                    if len(aligned_portfolio) > 30:
                        covariance = np.cov(aligned_portfolio, aligned_benchmark)[0, 1]
                        benchmark_variance = aligned_benchmark.var()
                        beta = covariance / benchmark_variance if benchmark_variance > 0 else 0
            
            # Portfolio-specific risks
            correlation_risk = self._calculate_correlation_risk(positions, market_data)
            concentration_risk = self._calculate_concentration_risk(positions)
            liquidity_risk = self._calculate_liquidity_risk(positions, market_data)
            
            risk_metrics = RiskMetrics(
                var_95=var_95,
                var_99=var_99,
                cvar_95=cvar_95,
                cvar_99=cvar_99,
                max_drawdown=max_drawdown,
                volatility=volatility,
                sharpe_ratio=sharpe_ratio,
                sortino_ratio=sortino_ratio,
                calmar_ratio=calmar_ratio,
                beta=beta,
                correlation_risk=correlation_risk,
                concentration_risk=concentration_risk,
                liquidity_risk=liquidity_risk
            )
            
            self.logger.info(f"Portfolio risk calculated: VaR 95%: {var_95:.2f}%, "
                           f"Volatility: {volatility:.2f}%, Sharpe: {sharpe_ratio:.2f}")
            
            return risk_metrics
            
        except Exception as e:
            self.logger.error(f"Portfolio risk calculation failed: {e}")
            return RiskMetrics()
    
    def analyze_position_risk(self, positions: Dict[str, Dict[str, Any]], 
                            market_data: Dict[str, pd.DataFrame]) -> List[PositionRisk]:
        """
        Analyze risk for individual positions
        """
        
        position_risks = []
        total_portfolio_value = sum(pos['market_value'] for pos in positions.values())
        
        for symbol, position in positions.items():
            try:
                if symbol not in market_data:
                    continue
                
                # Basic position metrics
                market_value = position['market_value']
                weight = market_value / total_portfolio_value if total_portfolio_value > 0 else 0
                
                # Calculate returns for this position
                prices = market_data[symbol]['close']
                returns = prices.pct_change().dropna()
                
                if len(returns) < 30:
                    continue
                
                # Position volatility
                volatility = returns.std() * np.sqrt(252) * 100
                
                # Position VaR contribution
                var_contribution = weight * self.var_model.historical_var(returns, 0.95) * 100
                
                # Beta calculation (simplified - against equally weighted portfolio)
                portfolio_returns = self._calculate_simple_portfolio_returns(positions, market_data)
                if len(portfolio_returns) > 30:
                    aligned_returns, aligned_portfolio = returns.align(portfolio_returns, join='inner')
                    if len(aligned_returns) > 30:
                        covariance = np.cov(aligned_returns, aligned_portfolio)[0, 1]
                        portfolio_variance = aligned_portfolio.var()
                        beta = covariance / portfolio_variance if portfolio_variance > 0 else 1.0
                    else:
                        beta = 1.0
                else:
                    beta = 1.0
                
                # Correlation risk (average correlation with other positions)
                correlation_risk = self._calculate_position_correlation_risk(
                    symbol, positions, market_data
                )
                
                # Liquidity score (simplified)
                liquidity_score = self._calculate_liquidity_score(symbol, market_data[symbol])
                
                # Overall risk score (weighted combination)
                risk_score = (
                    0.3 * min(volatility / 50, 1.0) +  # Volatility component
                    0.2 * min(abs(var_contribution) / 5, 1.0) +  # VaR component
                    0.2 * min(weight / 0.2, 1.0) +  # Concentration component
                    0.15 * min(correlation_risk, 1.0) +  # Correlation component
                    0.15 * (1 - liquidity_score)  # Liquidity component
                ) * 100
                
                position_risk = PositionRisk(
                    symbol=symbol,
                    position_size=position.get('quantity', 0),
                    market_value=market_value,
                    weight=weight * 100,
                    var_contribution=var_contribution,
                    beta=beta,
                    volatility=volatility,
                    correlation_risk=correlation_risk * 100,
                    liquidity_score=liquidity_score * 100,
                    risk_score=risk_score
                )
                
                position_risks.append(position_risk)
                
            except Exception as e:
                self.logger.error(f"Position risk analysis failed for {symbol}: {e}")
                continue
        
        # Sort by risk score
        position_risks.sort(key=lambda x: x.risk_score, reverse=True)
        
        self.logger.info(f"Analyzed risk for {len(position_risks)} positions")
        return position_risks
    
    def calculate_risk_budget(self, positions: Dict[str, Dict[str, Any]], 
                            target_risk: float = 0.15) -> Dict[str, float]:
        """
        Calculate optimal risk budget allocation
        """
        
        try:
            position_risks = self.analyze_position_risk(positions, {})
            
            if not position_risks:
                return {}
            
            # Simple equal risk contribution approach
            total_positions = len(position_risks)
            equal_risk_budget = target_risk / total_positions
            
            risk_budget = {}
            for pos_risk in position_risks:
                # Adjust based on risk score (lower risk = higher allocation)
                risk_adjustment = 1.0 / (1.0 + pos_risk.risk_score / 100)
                risk_budget[pos_risk.symbol] = equal_risk_budget * risk_adjustment
            
            # Normalize to target risk
            total_allocated_risk = sum(risk_budget.values())
            if total_allocated_risk > 0:
                normalization_factor = target_risk / total_allocated_risk
                for symbol in risk_budget:
                    risk_budget[symbol] *= normalization_factor
            
            self.logger.info(f"Risk budget calculated for {len(risk_budget)} positions")
            return risk_budget
            
        except Exception as e:
            self.logger.error(f"Risk budget calculation failed: {e}")
            return {}
    
    def _calculate_portfolio_returns(self, positions: Dict[str, Dict[str, Any]], 
                                   market_data: Dict[str, pd.DataFrame]) -> pd.Series:
        """Calculate portfolio returns from positions and market data"""
        
        portfolio_returns = pd.Series(dtype=float)
        total_value = sum(pos['market_value'] for pos in positions.values())
        
        if total_value == 0:
            return portfolio_returns
        
        for symbol, position in positions.items():
            if symbol not in market_data:
                continue
            
            weight = position['market_value'] / total_value
            prices = market_data[symbol]['close']
            returns = prices.pct_change().dropna()
            
            weighted_returns = returns * weight
            
            if portfolio_returns.empty:
                portfolio_returns = weighted_returns
            else:
                portfolio_returns, weighted_returns = portfolio_returns.align(
                    weighted_returns, join='outer', fill_value=0
                )
                portfolio_returns += weighted_returns
        
        return portfolio_returns.dropna()
    
    def _calculate_simple_portfolio_returns(self, positions: Dict[str, Dict[str, Any]], 
                                          market_data: Dict[str, pd.DataFrame]) -> pd.Series:
        """Simplified portfolio returns calculation"""
        
        # Use equally weighted portfolio for beta calculation
        all_returns = []
        
        for symbol in positions.keys():
            if symbol in market_data:
                returns = market_data[symbol]['close'].pct_change().dropna()
                all_returns.append(returns)
        
        if not all_returns:
            return pd.Series(dtype=float)
        
        # Align all series
        aligned_returns = pd.concat(all_returns, axis=1).dropna()
        
        if aligned_returns.empty:
            return pd.Series(dtype=float)
        
        # Equal weight portfolio
        return aligned_returns.mean(axis=1)
    
    def _calculate_correlation_risk(self, positions: Dict[str, Dict[str, Any]], 
                                  market_data: Dict[str, pd.DataFrame]) -> float:
        """Calculate portfolio correlation risk"""
        
        try:
            symbols = list(positions.keys())
            if len(symbols) < 2:
                return 0.0
            
            # Get returns for all positions
            returns_data = {}
            for symbol in symbols:
                if symbol in market_data:
                    returns = market_data[symbol]['close'].pct_change().dropna()
                    returns_data[symbol] = returns
            
            if len(returns_data) < 2:
                return 0.0
            
            # Create correlation matrix
            returns_df = pd.DataFrame(returns_data).dropna()
            
            if len(returns_df) < 30:
                return 0.5  # Default moderate correlation risk
            
            corr_matrix = returns_df.corr()
            
            # Calculate average correlation
            n = len(corr_matrix)
            total_correlations = 0
            count = 0
            
            for i in range(n):
                for j in range(i + 1, n):
                    total_correlations += abs(corr_matrix.iloc[i, j])
                    count += 1
            
            avg_correlation = total_correlations / count if count > 0 else 0
            
            # Higher correlation = higher risk
            return min(avg_correlation, 1.0)
            
        except Exception as e:
            self.logger.error(f"Correlation risk calculation failed: {e}")
            return 0.5
    
    def _calculate_concentration_risk(self, positions: Dict[str, Dict[str, Any]]) -> float:
        """Calculate portfolio concentration risk"""
        
        try:
            total_value = sum(pos['market_value'] for pos in positions.values())
            if total_value == 0:
                return 0.0
            
            # Calculate weights
            weights = [pos['market_value'] / total_value for pos in positions.values()]
            
            # Herfindahl-Hirschman Index (HHI)
            hhi = sum(w ** 2 for w in weights)
            
            # Convert to risk score (higher HHI = more concentrated = higher risk)
            # HHI ranges from 1/n (equal weights) to 1 (single position)
            n = len(positions)
            min_hhi = 1.0 / n if n > 0 else 1.0
            max_hhi = 1.0
            
            if max_hhi > min_hhi:
                concentration_risk = (hhi - min_hhi) / (max_hhi - min_hhi)
            else:
                concentration_risk = 0.0
            
            return min(concentration_risk, 1.0)
            
        except Exception as e:
            self.logger.error(f"Concentration risk calculation failed: {e}")
            return 0.5
    
    def _calculate_liquidity_risk(self, positions: Dict[str, Dict[str, Any]], 
                                market_data: Dict[str, pd.DataFrame]) -> float:
        """Calculate portfolio liquidity risk"""
        
        try:
            total_value = sum(pos['market_value'] for pos in positions.values())
            if total_value == 0:
                return 0.0
            
            weighted_liquidity_risk = 0.0
            
            for symbol, position in positions.items():
                if symbol not in market_data:
                    continue
                
                weight = position['market_value'] / total_value
                liquidity_score = self._calculate_liquidity_score(symbol, market_data[symbol])
                liquidity_risk = 1.0 - liquidity_score  # Higher score = lower risk
                
                weighted_liquidity_risk += weight * liquidity_risk
            
            return min(weighted_liquidity_risk, 1.0)
            
        except Exception as e:
            self.logger.error(f"Liquidity risk calculation failed: {e}")
            return 0.5
    
    def _calculate_liquidity_score(self, symbol: str, data: pd.DataFrame) -> float:
        """Calculate liquidity score for a single position"""
        
        try:
            if 'volume' not in data.columns:
                return 0.7  # Default moderate liquidity
            
            # Recent average volume
            recent_volume = data['volume'].tail(30).mean()
            
            # Volume volatility (consistency of trading)
            volume_std = data['volume'].tail(30).std()
            volume_cv = volume_std / recent_volume if recent_volume > 0 else 1.0
            
            # Price impact (simplified - based on volatility)
            price_volatility = data['close'].pct_change().tail(30).std()
            
            # Liquidity score (higher volume, lower volatility = better liquidity)
            volume_score = min(recent_volume / 1000000, 1.0)  # Normalize to millions
            consistency_score = max(0, 1.0 - volume_cv)
            volatility_score = max(0, 1.0 - price_volatility * 50)  # Scale volatility
            
            liquidity_score = (
                0.5 * volume_score +
                0.3 * consistency_score +
                0.2 * volatility_score
            )
            
            return min(liquidity_score, 1.0)
            
        except Exception as e:
            self.logger.error(f"Liquidity score calculation failed for {symbol}: {e}")
            return 0.5
    
    def _calculate_position_correlation_risk(self, target_symbol: str, 
                                           positions: Dict[str, Dict[str, Any]], 
                                           market_data: Dict[str, pd.DataFrame]) -> float:
        """Calculate correlation risk for a specific position"""
        
        try:
            if target_symbol not in market_data:
                return 0.5
            
            target_returns = market_data[target_symbol]['close'].pct_change().dropna()
            correlations = []
            
            for symbol in positions.keys():
                if symbol != target_symbol and symbol in market_data:
                    other_returns = market_data[symbol]['close'].pct_change().dropna()
                    
                    # Align series
                    aligned_target, aligned_other = target_returns.align(
                        other_returns, join='inner'
                    )
                    
                    if len(aligned_target) > 30:
                        correlation = aligned_target.corr(aligned_other)
                        if not np.isnan(correlation):
                            correlations.append(abs(correlation))
            
            if correlations:
                return np.mean(correlations)
            else:
                return 0.3  # Default low correlation risk
                
        except Exception as e:
            self.logger.error(f"Position correlation risk calculation failed: {e}")
            return 0.5