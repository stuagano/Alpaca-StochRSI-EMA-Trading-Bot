import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Tuple, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json

from education.indicator_academy import IndicatorAcademy
from backtesting.backtesting_engine import BacktestingEngine
from backtesting.strategies import BacktestingStrategies
from risk_management.position_sizer import PositionSizingMethod

class RuleType(Enum):
    """Types of strategy rules"""
    ENTRY_LONG = "entry_long"
    ENTRY_SHORT = "entry_short"
    EXIT_LONG = "exit_long"
    EXIT_SHORT = "exit_short"
    RISK_MANAGEMENT = "risk_management"

class ConditionOperator(Enum):
    """Logical operators for combining conditions"""
    AND = "and"
    OR = "or"

@dataclass
class IndicatorCondition:
    """Single indicator condition"""
    indicator: str
    parameter1: str  # e.g., 'value', 'k_percent', 'macd'
    operator: str    # e.g., '>', '<', '>=', '<=', '==', 'crosses_above', 'crosses_below'
    parameter2: Optional[str] = None  # e.g., 'd_percent', 'signal_line'
    threshold: Optional[float] = None  # e.g., 30, 70, 0
    lookback: int = 1  # Number of periods to look back for crosses
    
@dataclass
class TradingRule:
    """Complete trading rule with multiple conditions"""
    name: str
    rule_type: RuleType
    conditions: List[IndicatorCondition]
    operator: ConditionOperator = ConditionOperator.AND
    description: str = ""

@dataclass
class StrategyConfig:
    """Complete strategy configuration"""
    name: str
    description: str
    indicators: Dict[str, Dict[str, Any]]  # indicator_name -> parameters
    rules: List[TradingRule]
    risk_management: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)

class VisualStrategyBuilder:
    """
    Visual drag-and-drop style strategy builder
    """
    
    def __init__(self):
        self.logger = logging.getLogger('education.strategy_builder')
        self.indicator_academy = IndicatorAcademy()
        self.backtesting_engine = BacktestingEngine()
        
        # Available operators for different data types
        self.numeric_operators = ['>', '<', '>=', '<=', '==', '!=']
        self.crossover_operators = ['crosses_above', 'crosses_below']
        self.all_operators = self.numeric_operators + self.crossover_operators
        
        self.logger.info("Visual Strategy Builder initialized")
    
    def get_indicator_templates(self) -> Dict[str, Dict[str, Any]]:
        """Get available indicator templates with their parameters"""
        
        templates = {}
        
        for indicator_name, lesson in self.indicator_academy.lessons.items():
            templates[indicator_name] = {
                "name": lesson.name,
                "category": lesson.category.value,
                "difficulty": lesson.difficulty,
                "parameters": lesson.parameters,
                "available_outputs": self._get_indicator_outputs(indicator_name),
                "common_thresholds": self._get_common_thresholds(indicator_name),
                "description": lesson.description.split('.')[0] + '.'
            }
        
        return templates
    
    def _get_indicator_outputs(self, indicator_name: str) -> List[Dict[str, str]]:
        """Get available outputs for an indicator"""
        
        outputs = {
            "stoch_rsi": [
                {"key": "k_percent", "name": "%K Line", "type": "numeric"},
                {"key": "d_percent", "name": "%D Line", "type": "numeric"}
            ],
            "rsi": [
                {"key": "value", "name": "RSI Value", "type": "numeric"}
            ],
            "ema": [
                {"key": "value", "name": "EMA Value", "type": "numeric"}
            ],
            "macd": [
                {"key": "macd", "name": "MACD Line", "type": "numeric"},
                {"key": "signal", "name": "Signal Line", "type": "numeric"},
                {"key": "histogram", "name": "MACD Histogram", "type": "numeric"}
            ],
            "bollinger_bands": [
                {"key": "upper", "name": "Upper Band", "type": "numeric"},
                {"key": "middle", "name": "Middle Band", "type": "numeric"},
                {"key": "lower", "name": "Lower Band", "type": "numeric"}
            ]
        }
        
        return outputs.get(indicator_name, [{"key": "value", "name": "Value", "type": "numeric"}])
    
    def _get_common_thresholds(self, indicator_name: str) -> Dict[str, List[float]]:
        """Get common threshold values for indicators"""
        
        thresholds = {
            "stoch_rsi": {
                "oversold": [20, 25, 30, 35],
                "overbought": [65, 70, 75, 80]
            },
            "rsi": {
                "oversold": [25, 30, 35],
                "overbought": [65, 70, 75]
            },
            "macd": {
                "zero_line": [0]
            },
            "bollinger_bands": {
                "band_touch": []  # Dynamic based on bands
            }
        }
        
        return thresholds.get(indicator_name, {})
    
    def create_strategy_template(self, strategy_type: str, experience_level: str = "beginner") -> StrategyConfig:
        """Create pre-built strategy templates"""
        
        templates = {
            "stoch_rsi_basic": self._create_stoch_rsi_template(),
            "ema_crossover": self._create_ema_crossover_template(),
            "rsi_mean_reversion": self._create_rsi_mean_reversion_template(),
            "macd_trend_following": self._create_macd_trend_template(),
            "multi_indicator_confluence": self._create_confluence_template()
        }
        
        if strategy_type in templates:
            strategy = templates[strategy_type]
            strategy.metadata["created_from_template"] = strategy_type
            strategy.metadata["experience_level"] = experience_level
            return strategy
        else:
            return self._create_empty_strategy()
    
    def _create_stoch_rsi_template(self) -> StrategyConfig:
        """Create StochRSI strategy template"""
        
        # Define indicators
        indicators = {
            "stoch_rsi": {
                "rsi_period": 14,
                "stoch_period": 14,
                "k_smooth": 3,
                "d_smooth": 3
            }
        }
        
        # Entry rule: StochRSI bullish crossover in oversold region
        entry_long = TradingRule(
            name="StochRSI Bullish Entry",
            rule_type=RuleType.ENTRY_LONG,
            conditions=[
                IndicatorCondition(
                    indicator="stoch_rsi",
                    parameter1="k_percent",
                    operator="crosses_above",
                    parameter2="d_percent"
                ),
                IndicatorCondition(
                    indicator="stoch_rsi", 
                    parameter1="k_percent",
                    operator="<",
                    threshold=35
                )
            ],
            operator=ConditionOperator.AND,
            description="Enter long when %K crosses above %D in oversold region (< 35)"
        )
        
        # Exit rule: StochRSI bearish crossover in overbought region
        exit_long = TradingRule(
            name="StochRSI Bearish Exit",
            rule_type=RuleType.EXIT_LONG,
            conditions=[
                IndicatorCondition(
                    indicator="stoch_rsi",
                    parameter1="k_percent", 
                    operator="crosses_below",
                    parameter2="d_percent"
                ),
                IndicatorCondition(
                    indicator="stoch_rsi",
                    parameter1="k_percent",
                    operator=">",
                    threshold=80
                )
            ],
            operator=ConditionOperator.AND,
            description="Exit long when %K crosses below %D in overbought region (> 80)"
        )
        
        # Risk management
        risk_management = {
            "position_sizing_method": PositionSizingMethod.VOLATILITY_ADJUSTED,
            "max_risk_per_trade": 0.02,  # 2%
            "stop_loss_atr_multiple": 2.0,
            "take_profit_ratio": 2.0,  # 2:1 risk-reward
            "max_positions": 3
        }
        
        return StrategyConfig(
            name="StochRSI Momentum Strategy",
            description="Captures momentum reversals using StochRSI crossovers in extreme zones",
            indicators=indicators,
            rules=[entry_long, exit_long],
            risk_management=risk_management,
            metadata={
                "strategy_type": "momentum",
                "best_markets": ["trending", "volatile"],
                "timeframes": ["15m", "1h", "4h"]
            }
        )
    
    def _create_ema_crossover_template(self) -> StrategyConfig:
        """Create EMA crossover strategy template"""
        
        indicators = {
            "ema_fast": {"period": 9},
            "ema_slow": {"period": 21}
        }
        
        entry_long = TradingRule(
            name="EMA Bullish Crossover",
            rule_type=RuleType.ENTRY_LONG,
            conditions=[
                IndicatorCondition(
                    indicator="ema_fast",
                    parameter1="value",
                    operator="crosses_above",
                    parameter2="ema_slow.value"
                )
            ],
            description="Enter long when fast EMA crosses above slow EMA"
        )
        
        exit_long = TradingRule(
            name="EMA Bearish Crossover", 
            rule_type=RuleType.EXIT_LONG,
            conditions=[
                IndicatorCondition(
                    indicator="ema_fast",
                    parameter1="value",
                    operator="crosses_below",
                    parameter2="ema_slow.value"
                )
            ],
            description="Exit long when fast EMA crosses below slow EMA"
        )
        
        risk_management = {
            "position_sizing_method": PositionSizingMethod.FIXED_PERCENTAGE,
            "position_size": 0.10,  # 10% of portfolio
            "stop_loss_percentage": 0.05,  # 5%
            "take_profit_percentage": 0.10,  # 10%
            "max_positions": 5
        }
        
        return StrategyConfig(
            name="EMA Crossover Strategy",
            description="Classic trend-following strategy using EMA crossovers",
            indicators=indicators,
            rules=[entry_long, exit_long],
            risk_management=risk_management,
            metadata={
                "strategy_type": "trend_following",
                "best_markets": ["trending", "stocks", "forex"],
                "timeframes": ["1h", "4h", "1d"]
            }
        )
    
    def _create_rsi_mean_reversion_template(self) -> StrategyConfig:
        """Create RSI mean reversion strategy template"""
        
        indicators = {
            "rsi": {"period": 14}
        }
        
        entry_long = TradingRule(
            name="RSI Oversold Entry",
            rule_type=RuleType.ENTRY_LONG,
            conditions=[
                IndicatorCondition(
                    indicator="rsi",
                    parameter1="value",
                    operator="<",
                    threshold=30
                ),
                IndicatorCondition(
                    indicator="rsi",
                    parameter1="value", 
                    operator="crosses_above",
                    threshold=30
                )
            ],
            operator=ConditionOperator.AND,
            description="Enter long when RSI crosses above 30 from oversold region"
        )
        
        exit_long = TradingRule(
            name="RSI Overbought Exit",
            rule_type=RuleType.EXIT_LONG,
            conditions=[
                IndicatorCondition(
                    indicator="rsi",
                    parameter1="value",
                    operator=">", 
                    threshold=70
                )
            ],
            description="Exit long when RSI reaches overbought level (70)"
        )
        
        risk_management = {
            "position_sizing_method": PositionSizingMethod.KELLY_CRITERION,
            "max_risk_per_trade": 0.015,  # 1.5%
            "stop_loss_percentage": 0.03,  # 3%
            "take_profit_percentage": 0.06,  # 6% (2:1 R:R)
            "max_positions": 4
        }
        
        return StrategyConfig(
            name="RSI Mean Reversion Strategy", 
            description="Buys oversold conditions and sells when overbought using RSI",
            indicators=indicators,
            rules=[entry_long, exit_long],
            risk_management=risk_management,
            metadata={
                "strategy_type": "mean_reversion",
                "best_markets": ["ranging", "stocks", "crypto"],
                "timeframes": ["30m", "1h", "4h"]
            }
        )
    
    def _create_macd_trend_template(self) -> StrategyConfig:
        """Create MACD trend following strategy template"""
        
        indicators = {
            "macd": {
                "fast_period": 12,
                "slow_period": 26,
                "signal_period": 9
            }
        }
        
        entry_long = TradingRule(
            name="MACD Bullish Signal",
            rule_type=RuleType.ENTRY_LONG,
            conditions=[
                IndicatorCondition(
                    indicator="macd",
                    parameter1="macd",
                    operator="crosses_above",
                    parameter2="signal"
                ),
                IndicatorCondition(
                    indicator="macd",
                    parameter1="macd",
                    operator=">",
                    threshold=0
                )
            ],
            operator=ConditionOperator.AND,
            description="Enter long when MACD crosses above signal line and MACD > 0"
        )
        
        exit_long = TradingRule(
            name="MACD Bearish Signal",
            rule_type=RuleType.EXIT_LONG,
            conditions=[
                IndicatorCondition(
                    indicator="macd",
                    parameter1="macd",
                    operator="crosses_below",
                    parameter2="signal"
                )
            ],
            description="Exit long when MACD crosses below signal line"
        )
        
        risk_management = {
            "position_sizing_method": PositionSizingMethod.ATR_BASED,
            "atr_period": 14,
            "atr_multiplier": 2.0,
            "max_risk_per_trade": 0.02,
            "take_profit_ratio": 3.0,  # 3:1 R:R for trend following
            "max_positions": 3
        }
        
        return StrategyConfig(
            name="MACD Trend Following Strategy",
            description="Follows trends using MACD crossovers with trend confirmation",
            indicators=indicators,
            rules=[entry_long, exit_long],
            risk_management=risk_management,
            metadata={
                "strategy_type": "trend_following",
                "best_markets": ["trending", "indices", "forex"],
                "timeframes": ["4h", "1d"]
            }
        )
    
    def _create_confluence_template(self) -> StrategyConfig:
        """Create multi-indicator confluence strategy"""
        
        indicators = {
            "stoch_rsi": {
                "rsi_period": 14,
                "stoch_period": 14,
                "k_smooth": 3,
                "d_smooth": 3
            },
            "ema": {"period": 21},
            "rsi": {"period": 14}
        }
        
        entry_long = TradingRule(
            name="Multi-Indicator Bullish Confluence",
            rule_type=RuleType.ENTRY_LONG,
            conditions=[
                # StochRSI oversold crossover
                IndicatorCondition(
                    indicator="stoch_rsi",
                    parameter1="k_percent",
                    operator="crosses_above",
                    parameter2="d_percent"
                ),
                IndicatorCondition(
                    indicator="stoch_rsi",
                    parameter1="k_percent",
                    operator="<",
                    threshold=35
                ),
                # Price above EMA (trend filter)
                IndicatorCondition(
                    indicator="price",
                    parameter1="close",
                    operator=">",
                    parameter2="ema.value"
                ),
                # RSI not overbought
                IndicatorCondition(
                    indicator="rsi",
                    parameter1="value",
                    operator="<",
                    threshold=65
                )
            ],
            operator=ConditionOperator.AND,
            description="Enter when StochRSI bullish crossover in oversold region, price above EMA, and RSI not overbought"
        )
        
        exit_long = TradingRule(
            name="Multi-Indicator Bearish Signal",
            rule_type=RuleType.EXIT_LONG,
            conditions=[
                IndicatorCondition(
                    indicator="stoch_rsi",
                    parameter1="k_percent",
                    operator="crosses_below",
                    parameter2="d_percent"
                ),
                IndicatorCondition(
                    indicator="stoch_rsi",
                    parameter1="k_percent",
                    operator=">",
                    threshold=75
                )
            ],
            operator=ConditionOperator.AND,
            description="Exit when StochRSI bearish crossover in overbought region"
        )
        
        risk_management = {
            "position_sizing_method": PositionSizingMethod.RISK_PARITY,
            "target_risk_contribution": 0.08,  # 8% risk allocation
            "max_risk_per_trade": 0.015,  # 1.5%
            "stop_loss_atr_multiple": 2.5,
            "take_profit_ratio": 2.5,
            "trailing_stop": True,
            "max_positions": 2  # Conservative with confluence
        }
        
        return StrategyConfig(
            name="Multi-Indicator Confluence Strategy",
            description="High-probability trades using confluence of StochRSI, EMA trend, and RSI confirmation",
            indicators=indicators,
            rules=[entry_long, exit_long],
            risk_management=risk_management,
            metadata={
                "strategy_type": "confluence",
                "best_markets": ["trending", "volatile"],
                "timeframes": ["1h", "4h"],
                "complexity": "advanced"
            }
        )
    
    def _create_empty_strategy(self) -> StrategyConfig:
        """Create empty strategy for custom building"""
        
        return StrategyConfig(
            name="Custom Strategy",
            description="Build your own strategy",
            indicators={},
            rules=[],
            risk_management={
                "position_sizing_method": PositionSizingMethod.FIXED_PERCENTAGE,
                "position_size": 0.05,  # 5%
                "max_risk_per_trade": 0.02,  # 2%
                "max_positions": 3
            },
            metadata={"custom_built": True}
        )
    
    def add_indicator(self, strategy: StrategyConfig, indicator_name: str, 
                     parameters: Dict[str, Any] = None) -> StrategyConfig:
        """Add indicator to strategy"""
        
        lesson = self.indicator_academy.get_lesson(indicator_name)
        if not lesson:
            raise ValueError(f"Unknown indicator: {indicator_name}")
        
        # Use provided parameters or defaults
        if parameters is None:
            parameters = {}
            for param_name, param_info in lesson.parameters.items():
                parameters[param_name] = param_info["default"]
        
        strategy.indicators[indicator_name] = parameters
        
        self.logger.info(f"Added {indicator_name} indicator to strategy {strategy.name}")
        
        return strategy
    
    def add_rule(self, strategy: StrategyConfig, rule: TradingRule) -> StrategyConfig:
        """Add trading rule to strategy"""
        
        # Validate rule conditions reference existing indicators
        for condition in rule.conditions:
            if condition.indicator not in strategy.indicators and condition.indicator != "price":
                raise ValueError(f"Condition references unknown indicator: {condition.indicator}")
        
        strategy.rules.append(rule)
        
        self.logger.info(f"Added rule '{rule.name}' to strategy {strategy.name}")
        
        return strategy
    
    def create_condition(self, indicator: str, parameter1: str, operator: str,
                        parameter2: str = None, threshold: float = None) -> IndicatorCondition:
        """Create indicator condition with validation"""
        
        # Validate operator
        if operator not in self.all_operators:
            raise ValueError(f"Unknown operator: {operator}. Use one of: {self.all_operators}")
        
        # Validate crossover operators require parameter2
        if operator in self.crossover_operators and parameter2 is None:
            raise ValueError(f"Crossover operator '{operator}' requires parameter2")
        
        # Validate threshold operators require threshold
        if operator in self.numeric_operators and threshold is None and parameter2 is None:
            raise ValueError(f"Numeric operator '{operator}' requires threshold or parameter2")
        
        return IndicatorCondition(
            indicator=indicator,
            parameter1=parameter1,
            operator=operator,
            parameter2=parameter2,
            threshold=threshold
        )
    
    def validate_strategy(self, strategy: StrategyConfig) -> Dict[str, Any]:
        """Validate strategy configuration"""
        
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "suggestions": []
        }
        
        # Check for indicators
        if not strategy.indicators:
            validation_result["errors"].append("Strategy must have at least one indicator")
            validation_result["valid"] = False
        
        # Check for entry rules
        entry_rules = [rule for rule in strategy.rules if rule.rule_type == RuleType.ENTRY_LONG]
        if not entry_rules:
            validation_result["errors"].append("Strategy must have at least one entry rule")
            validation_result["valid"] = False
        
        # Check for exit rules
        exit_rules = [rule for rule in strategy.rules if rule.rule_type == RuleType.EXIT_LONG]
        if not exit_rules:
            validation_result["warnings"].append("Strategy should have exit rules for better risk management")
        
        # Validate rule conditions
        for rule in strategy.rules:
            for condition in rule.conditions:
                if condition.indicator not in strategy.indicators and condition.indicator != "price":
                    validation_result["errors"].append(
                        f"Rule '{rule.name}' references undefined indicator: {condition.indicator}"
                    )
                    validation_result["valid"] = False
        
        # Risk management validation
        if "max_risk_per_trade" not in strategy.risk_management:
            validation_result["warnings"].append("Consider setting maximum risk per trade")
        
        if "max_positions" not in strategy.risk_management:
            validation_result["warnings"].append("Consider setting maximum number of positions")
        
        # Suggestions for improvement
        if len(strategy.indicators) == 1:
            validation_result["suggestions"].append("Consider adding another indicator for confirmation")
        
        if len(entry_rules) == 1 and len(entry_rules[0].conditions) == 1:
            validation_result["suggestions"].append("Consider adding more conditions for higher probability trades")
        
        return validation_result
    
    def compile_strategy(self, strategy: StrategyConfig) -> Callable:
        """Compile strategy into executable function"""
        
        def compiled_strategy(data: pd.DataFrame, **kwargs) -> pd.Series:
            """
            Compiled strategy function that generates trading signals
            """
            
            signals = pd.Series(0, index=data.index)
            
            try:
                # Calculate all indicators
                indicator_values = {}
                
                for indicator_name, params in strategy.indicators.items():
                    if indicator_name == "stoch_rsi":
                        k, d = self._calculate_stoch_rsi(data, **params)
                        indicator_values[indicator_name] = {"k_percent": k, "d_percent": d}
                    
                    elif indicator_name == "rsi":
                        rsi = self._calculate_rsi(data, **params)
                        indicator_values[indicator_name] = {"value": rsi}
                    
                    elif indicator_name == "ema" or indicator_name.startswith("ema_"):
                        ema = self._calculate_ema(data, **params)
                        indicator_values[indicator_name] = {"value": ema}
                    
                    elif indicator_name == "macd":
                        macd, signal, histogram = self._calculate_macd(data, **params)
                        indicator_values[indicator_name] = {
                            "macd": macd, "signal": signal, "histogram": histogram
                        }
                    
                    elif indicator_name == "bollinger_bands":
                        upper, middle, lower = self._calculate_bollinger_bands(data, **params)
                        indicator_values[indicator_name] = {
                            "upper": upper, "middle": middle, "lower": lower
                        }
                
                # Evaluate entry rules
                for rule in strategy.rules:
                    if rule.rule_type == RuleType.ENTRY_LONG:
                        rule_signals = self._evaluate_rule(rule, data, indicator_values)
                        signals = signals + rule_signals  # Combine signals
                
                # Apply exit logic (simplified for now)
                # In production, this would track positions and apply exit rules
                
                # Clean up signals (remove duplicates, etc.)
                signals = signals.clip(-1, 1)  # Ensure signals are in [-1, 0, 1] range
                
                return signals
                
            except Exception as e:
                self.logger.error(f"Strategy execution failed: {e}")
                return pd.Series(0, index=data.index)
        
        # Add metadata to function
        compiled_strategy.strategy_config = strategy
        compiled_strategy.strategy_name = strategy.name
        
        return compiled_strategy
    
    def _evaluate_rule(self, rule: TradingRule, data: pd.DataFrame, 
                      indicator_values: Dict[str, Any]) -> pd.Series:
        """Evaluate a trading rule and return signals"""
        
        rule_results = []
        
        for condition in rule.conditions:
            condition_result = self._evaluate_condition(condition, data, indicator_values)
            rule_results.append(condition_result)
        
        # Combine conditions based on operator
        if rule.operator == ConditionOperator.AND:
            combined_result = pd.Series(True, index=data.index)
            for result in rule_results:
                combined_result &= result
        else:  # OR
            combined_result = pd.Series(False, index=data.index)
            for result in rule_results:
                combined_result |= result
        
        # Convert boolean to signals
        signals = pd.Series(0, index=data.index)
        if rule.rule_type == RuleType.ENTRY_LONG:
            signals[combined_result] = 1
        elif rule.rule_type == RuleType.ENTRY_SHORT:
            signals[combined_result] = -1
        
        return signals
    
    def _evaluate_condition(self, condition: IndicatorCondition, data: pd.DataFrame,
                           indicator_values: Dict[str, Any]) -> pd.Series:
        """Evaluate individual condition"""
        
        try:
            # Get parameter 1 value
            if condition.indicator == "price":
                param1_value = data[condition.parameter1]
            else:
                param1_value = indicator_values[condition.indicator][condition.parameter1]
            
            # Handle different operators
            if condition.operator in self.numeric_operators:
                if condition.threshold is not None:
                    # Compare with threshold
                    if condition.operator == '>':
                        return param1_value > condition.threshold
                    elif condition.operator == '<':
                        return param1_value < condition.threshold
                    elif condition.operator == '>=':
                        return param1_value >= condition.threshold
                    elif condition.operator == '<=':
                        return param1_value <= condition.threshold
                    elif condition.operator == '==':
                        return param1_value == condition.threshold
                    elif condition.operator == '!=':
                        return param1_value != condition.threshold
                
                elif condition.parameter2:
                    # Compare with another parameter
                    if '.' in condition.parameter2:
                        # Reference to another indicator (e.g., "ema_slow.value")
                        indicator_ref, param_ref = condition.parameter2.split('.')
                        param2_value = indicator_values[indicator_ref][param_ref]
                    else:
                        # Reference to same indicator
                        param2_value = indicator_values[condition.indicator][condition.parameter2]
                    
                    if condition.operator == '>':
                        return param1_value > param2_value
                    elif condition.operator == '<':
                        return param1_value < param2_value
                    # Add other operators as needed
            
            elif condition.operator in self.crossover_operators:
                # Handle crossover conditions
                if condition.parameter2:
                    if '.' in condition.parameter2:
                        indicator_ref, param_ref = condition.parameter2.split('.')
                        param2_value = indicator_values[indicator_ref][param_ref]
                    else:
                        param2_value = indicator_values[condition.indicator][condition.parameter2]
                elif condition.threshold is not None:
                    param2_value = pd.Series(condition.threshold, index=data.index)
                else:
                    raise ValueError("Crossover condition requires parameter2 or threshold")
                
                if condition.operator == 'crosses_above':
                    return (param1_value > param2_value) & (param1_value.shift(1) <= param2_value.shift(1))
                elif condition.operator == 'crosses_below':
                    return (param1_value < param2_value) & (param1_value.shift(1) >= param2_value.shift(1))
            
            # Default case
            return pd.Series(False, index=data.index)
            
        except Exception as e:
            self.logger.error(f"Condition evaluation failed: {e}")
            return pd.Series(False, index=data.index)
    
    # Helper methods for indicator calculations
    def _calculate_stoch_rsi(self, data: pd.DataFrame, rsi_period: int = 14, 
                            stoch_period: int = 14, k_smooth: int = 3, 
                            d_smooth: int = 3) -> Tuple[pd.Series, pd.Series]:
        """Calculate Stochastic RSI"""
        import ta
        
        rsi = ta.momentum.RSIIndicator(data['close'], window=rsi_period).rsi()
        rsi_high = rsi.rolling(window=stoch_period).max()
        rsi_low = rsi.rolling(window=stoch_period).min()
        
        k_percent = 100 * (rsi - rsi_low) / (rsi_high - rsi_low)
        k_percent = k_percent.rolling(window=k_smooth).mean()
        d_percent = k_percent.rolling(window=d_smooth).mean()
        
        return k_percent, d_percent
    
    def _calculate_rsi(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate RSI"""
        import ta
        return ta.momentum.RSIIndicator(data['close'], window=period).rsi()
    
    def _calculate_ema(self, data: pd.DataFrame, period: int = 9) -> pd.Series:
        """Calculate EMA"""
        import ta
        return ta.trend.EMAIndicator(data['close'], window=period).ema_indicator()
    
    def _calculate_macd(self, data: pd.DataFrame, fast_period: int = 12,
                       slow_period: int = 26, signal_period: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate MACD"""
        import ta
        
        macd_indicator = ta.trend.MACD(
            close=data['close'],
            window_fast=fast_period,
            window_slow=slow_period,
            window_sign=signal_period
        )
        
        return (
            macd_indicator.macd(),
            macd_indicator.macd_signal(),
            macd_indicator.macd_diff()
        )
    
    def _calculate_bollinger_bands(self, data: pd.DataFrame, period: int = 20,
                                  std_dev: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate Bollinger Bands"""
        import ta
        
        bb = ta.volatility.BollingerBands(
            close=data['close'],
            window=period,
            window_dev=std_dev
        )
        
        return bb.bollinger_hband(), bb.bollinger_mavg(), bb.bollinger_lband()
    
    def export_strategy(self, strategy: StrategyConfig, file_path: str = None) -> str:
        """Export strategy to JSON file"""
        
        if file_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = f"strategies/{strategy.name}_{timestamp}.json"
        
        # Convert strategy to dictionary
        strategy_dict = {
            "name": strategy.name,
            "description": strategy.description,
            "indicators": strategy.indicators,
            "rules": [
                {
                    "name": rule.name,
                    "rule_type": rule.rule_type.value,
                    "operator": rule.operator.value,
                    "description": rule.description,
                    "conditions": [
                        {
                            "indicator": cond.indicator,
                            "parameter1": cond.parameter1,
                            "operator": cond.operator,
                            "parameter2": cond.parameter2,
                            "threshold": cond.threshold,
                            "lookback": cond.lookback
                        }
                        for cond in rule.conditions
                    ]
                }
                for rule in strategy.rules
            ],
            "risk_management": strategy.risk_management,
            "metadata": strategy.metadata
        }
        
        # Ensure directory exists
        import os
        os.makedirs(os.path.dirname(file_path) if os.path.dirname(file_path) else '.', exist_ok=True)
        
        # Write to file
        with open(file_path, 'w') as f:
            json.dump(strategy_dict, f, indent=2, default=str)
        
        self.logger.info(f"Strategy exported to {file_path}")
        return file_path
    
    def import_strategy(self, file_path: str) -> StrategyConfig:
        """Import strategy from JSON file"""
        
        with open(file_path, 'r') as f:
            strategy_dict = json.load(f)
        
        # Reconstruct strategy object
        strategy = StrategyConfig(
            name=strategy_dict["name"],
            description=strategy_dict["description"],
            indicators=strategy_dict["indicators"],
            rules=[],
            risk_management=strategy_dict["risk_management"],
            metadata=strategy_dict.get("metadata", {})
        )
        
        # Reconstruct rules
        for rule_dict in strategy_dict["rules"]:
            conditions = [
                IndicatorCondition(
                    indicator=cond["indicator"],
                    parameter1=cond["parameter1"], 
                    operator=cond["operator"],
                    parameter2=cond.get("parameter2"),
                    threshold=cond.get("threshold"),
                    lookback=cond.get("lookback", 1)
                )
                for cond in rule_dict["conditions"]
            ]
            
            rule = TradingRule(
                name=rule_dict["name"],
                rule_type=RuleType(rule_dict["rule_type"]),
                conditions=conditions,
                operator=ConditionOperator(rule_dict["operator"]),
                description=rule_dict["description"]
            )
            
            strategy.rules.append(rule)
        
        self.logger.info(f"Strategy imported from {file_path}")
        return strategy
    
    def get_strategy_summary(self, strategy: StrategyConfig) -> Dict[str, Any]:
        """Get human-readable strategy summary"""
        
        summary = {
            "name": strategy.name,
            "description": strategy.description,
            "complexity": len(strategy.indicators) + len(strategy.rules),
            "indicators_used": list(strategy.indicators.keys()),
            "entry_conditions": len([r for r in strategy.rules if r.rule_type == RuleType.ENTRY_LONG]),
            "exit_conditions": len([r for r in strategy.rules if r.rule_type == RuleType.EXIT_LONG]),
            "risk_management_enabled": bool(strategy.risk_management),
            "estimated_difficulty": self._estimate_difficulty(strategy),
            "recommended_markets": strategy.metadata.get("best_markets", ["general"]),
            "recommended_timeframes": strategy.metadata.get("timeframes", ["1h", "4h"])
        }
        
        return summary
    
    def _estimate_difficulty(self, strategy: StrategyConfig) -> str:
        """Estimate strategy difficulty level"""
        
        complexity_score = 0
        
        # Indicator complexity
        complexity_score += len(strategy.indicators)
        
        # Rule complexity
        for rule in strategy.rules:
            complexity_score += len(rule.conditions)
            if rule.operator == ConditionOperator.OR:
                complexity_score += 0.5  # OR conditions add complexity
        
        # Risk management complexity
        if len(strategy.risk_management) > 3:
            complexity_score += 1
        
        if complexity_score <= 3:
            return "beginner"
        elif complexity_score <= 7:
            return "intermediate"
        else:
            return "advanced"

# Global strategy builder instance
_strategy_builder = None

def get_strategy_builder() -> VisualStrategyBuilder:
    """Get singleton strategy builder instance"""
    global _strategy_builder
    if _strategy_builder is None:
        _strategy_builder = VisualStrategyBuilder()
    return _strategy_builder