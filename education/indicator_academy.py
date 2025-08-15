import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import ta
import logging
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

class IndicatorCategory(Enum):
    """Categories of technical indicators"""
    MOMENTUM = "momentum"
    TREND = "trend"
    VOLATILITY = "volatility"
    VOLUME = "volume"
    OVERLAP = "overlap"

@dataclass
class IndicatorLesson:
    """Individual indicator lesson structure"""
    name: str
    category: IndicatorCategory
    difficulty: str  # "beginner", "intermediate", "advanced"
    description: str
    formula_explanation: str
    parameters: Dict[str, Any]
    signals: Dict[str, str]
    strengths: List[str]
    weaknesses: List[str]
    best_markets: List[str]
    code_example: str
    interactive_example: callable
    quiz_questions: List[Dict[str, Any]]

class IndicatorAcademy:
    """
    Comprehensive educational system for technical indicators
    """
    
    def __init__(self):
        self.logger = logging.getLogger('education.indicators')
        self.lessons = {}
        self._initialize_lessons()
        
    def _initialize_lessons(self):
        """Initialize all indicator lessons"""
        
        # StochRSI Lesson
        self.lessons['stoch_rsi'] = IndicatorLesson(
            name="Stochastic RSI",
            category=IndicatorCategory.MOMENTUM,
            difficulty="intermediate",
            description="""
            The Stochastic RSI combines the best of both RSI and Stochastic oscillators. 
            It applies the Stochastic formula to RSI values rather than price data, creating 
            a more sensitive momentum indicator that oscillates between 0 and 1.
            
            This indicator helps identify overbought and oversold conditions with greater 
            sensitivity than traditional RSI, making it excellent for timing entries and exits.
            """,
            formula_explanation="""
            1. First calculate RSI: RSI = 100 - [100 / (1 + RS)]
               where RS = Average Gain / Average Loss over n periods
            
            2. Then apply Stochastic formula to RSI:
               %K = (RSI - Lowest Low RSI) / (Highest High RSI - Lowest Low RSI) × 100
               %D = SMA of %K over d periods
            
            Parameters:
            - RSI Period (typically 14)
            - Stochastic Period (typically 14) 
            - %K Smoothing (typically 3)
            - %D Smoothing (typically 3)
            """,
            parameters={
                "rsi_period": {"default": 14, "range": (10, 21), "description": "RSI calculation period"},
                "stoch_period": {"default": 14, "range": (10, 21), "description": "Stochastic period for RSI values"},
                "k_smooth": {"default": 3, "range": (1, 5), "description": "%K line smoothing"},
                "d_smooth": {"default": 3, "range": (1, 5), "description": "%D line smoothing"}
            },
            signals={
                "buy": "%K crosses above %D while both below 35 (oversold)",
                "sell": "%K crosses below %D while both above 80 (overbought)",
                "strong_buy": "Both %K and %D below 20 with bullish crossover",
                "strong_sell": "Both %K and %D above 80 with bearish crossover"
            },
            strengths=[
                "More sensitive than regular RSI",
                "Excellent for timing entries in trending markets",
                "Clear overbought/oversold signals",
                "Works well with other momentum indicators"
            ],
            weaknesses=[
                "Can be too sensitive in choppy markets",
                "May generate false signals in strong trends",
                "Requires confirmation from other indicators",
                "Not effective in sideways markets"
            ],
            best_markets=[
                "Trending stocks and crypto",
                "Forex pairs with clear momentum",
                "Individual stocks with volatility",
                "Not ideal for low-volatility markets"
            ],
            code_example="""
# Calculate Stochastic RSI
def calculate_stoch_rsi(data, rsi_period=14, stoch_period=14, k_smooth=3, d_smooth=3):
    # Calculate RSI
    rsi = ta.momentum.RSIIndicator(data['close'], window=rsi_period).rsi()
    
    # Apply Stochastic to RSI
    rsi_high = rsi.rolling(window=stoch_period).max()
    rsi_low = rsi.rolling(window=stoch_period).min()
    
    # Calculate %K
    k_percent = 100 * (rsi - rsi_low) / (rsi_high - rsi_low)
    k_percent = k_percent.rolling(window=k_smooth).mean()
    
    # Calculate %D
    d_percent = k_percent.rolling(window=d_smooth).mean()
    
    return k_percent, d_percent

# Generate trading signals
def stoch_rsi_signals(k_percent, d_percent, oversold=35, overbought=80):
    signals = pd.Series(0, index=k_percent.index)
    
    # Buy signal: %K crosses above %D in oversold region
    buy_condition = (
        (k_percent > d_percent) & 
        (k_percent.shift(1) <= d_percent.shift(1)) &
        (k_percent < oversold)
    )
    
    # Sell signal: %K crosses below %D in overbought region  
    sell_condition = (
        (k_percent < d_percent) & 
        (k_percent.shift(1) >= d_percent.shift(1)) &
        (k_percent > overbought)
    )
    
    signals[buy_condition] = 1
    signals[sell_condition] = -1
    
    return signals
            """,
            interactive_example=self._create_stoch_rsi_interactive,
            quiz_questions=[
                {
                    "question": "What makes Stochastic RSI more sensitive than regular RSI?",
                    "options": [
                        "It uses shorter time periods",
                        "It applies Stochastic formula to RSI values", 
                        "It includes volume data",
                        "It uses different price data"
                    ],
                    "correct": 1,
                    "explanation": "Stochastic RSI applies the Stochastic oscillator formula to RSI values rather than price, creating faster signals."
                },
                {
                    "question": "What is the typical oversold threshold for Stochastic RSI?",
                    "options": ["20", "30", "35", "40"],
                    "correct": 2,
                    "explanation": "35 is commonly used as the oversold threshold, though this can be adjusted based on market conditions."
                }
            ]
        )
        
        # EMA Lesson
        self.lessons['ema'] = IndicatorLesson(
            name="Exponential Moving Average (EMA)",
            category=IndicatorCategory.TREND,
            difficulty="beginner",
            description="""
            The Exponential Moving Average gives more weight to recent prices, making it more 
            responsive to new information than Simple Moving Averages. This responsiveness 
            makes EMAs excellent for trend-following strategies.
            
            EMAs are fundamental building blocks for many trading strategies and are often 
            used in crossover systems, trend identification, and dynamic support/resistance.
            """,
            formula_explanation="""
            EMA = (Close × Multiplier) + (Previous EMA × (1 - Multiplier))
            
            Where Multiplier = 2 / (Period + 1)
            
            For a 9-period EMA: Multiplier = 2 / (9 + 1) = 0.2
            
            This means today's price gets 20% weight, and the previous EMA gets 80% weight.
            The longer the period, the less weight given to the current price.
            """,
            parameters={
                "period": {"default": 9, "range": (5, 50), "description": "Number of periods for calculation"},
                "price_type": {"default": "close", "options": ["close", "high", "low", "hl2", "hlc3"], "description": "Price data to use"}
            },
            signals={
                "buy": "Price crosses above EMA or Fast EMA crosses above Slow EMA",
                "sell": "Price crosses below EMA or Fast EMA crosses below Slow EMA",
                "trend_up": "Price consistently above rising EMA",
                "trend_down": "Price consistently below falling EMA"
            },
            strengths=[
                "Responsive to recent price changes",
                "Smooth trend identification", 
                "Works well in trending markets",
                "Foundation for many other indicators"
            ],
            weaknesses=[
                "Can generate false signals in choppy markets",
                "Lags behind price (though less than SMA)",
                "Not effective in sideways markets",
                "May whipsaw in volatile conditions"
            ],
            best_markets=[
                "Trending stocks and indices",
                "Forex major pairs",
                "Cryptocurrency with clear trends",
                "Any market with sustained momentum"
            ],
            code_example="""
# Calculate EMA
def calculate_ema(data, period=9):
    return ta.trend.EMAIndicator(data['close'], window=period).ema_indicator()

# EMA Crossover Strategy
def ema_crossover_signals(data, fast_period=9, slow_period=21):
    fast_ema = calculate_ema(data, fast_period)
    slow_ema = calculate_ema(data, slow_period)
    
    signals = pd.Series(0, index=data.index)
    
    # Buy when fast EMA crosses above slow EMA
    buy_condition = (fast_ema > slow_ema) & (fast_ema.shift(1) <= slow_ema.shift(1))
    
    # Sell when fast EMA crosses below slow EMA
    sell_condition = (fast_ema < slow_ema) & (fast_ema.shift(1) >= slow_ema.shift(1))
    
    signals[buy_condition] = 1
    signals[sell_condition] = -1
    
    return signals, fast_ema, slow_ema
            """,
            interactive_example=self._create_ema_interactive,
            quiz_questions=[
                {
                    "question": "What makes EMA different from Simple Moving Average?",
                    "options": [
                        "Uses different time periods",
                        "Gives more weight to recent prices",
                        "Uses volume data",
                        "Only works on daily timeframes"
                    ],
                    "correct": 1,
                    "explanation": "EMA gives exponentially more weight to recent prices, making it more responsive than SMA."
                }
            ]
        )
        
        # Add more indicator lessons...
        self._add_rsi_lesson()
        self._add_macd_lesson()
        self._add_bollinger_bands_lesson()
        
        self.logger.info(f"Initialized {len(self.lessons)} indicator lessons")
    
    def _add_rsi_lesson(self):
        """Add RSI lesson"""
        self.lessons['rsi'] = IndicatorLesson(
            name="Relative Strength Index (RSI)",
            category=IndicatorCategory.MOMENTUM,
            difficulty="beginner",
            description="""
            RSI measures the speed and change of price movements, oscillating between 0 and 100.
            It's one of the most popular momentum indicators for identifying overbought and 
            oversold conditions.
            """,
            formula_explanation="""
            RSI = 100 - [100 / (1 + RS)]
            Where RS = Average Gain / Average Loss over n periods
            
            Typically calculated over 14 periods.
            Values above 70 suggest overbought conditions.
            Values below 30 suggest oversold conditions.
            """,
            parameters={
                "period": {"default": 14, "range": (10, 25), "description": "Calculation period"},
                "overbought": {"default": 70, "range": (65, 80), "description": "Overbought threshold"},
                "oversold": {"default": 30, "range": (20, 35), "description": "Oversold threshold"}
            },
            signals={
                "buy": "RSI crosses above 30 from oversold region",
                "sell": "RSI crosses below 70 from overbought region",
                "divergence_buy": "Price makes lower lows while RSI makes higher lows",
                "divergence_sell": "Price makes higher highs while RSI makes lower highs"
            },
            strengths=[
                "Clear overbought/oversold levels",
                "Works well with divergence analysis",
                "Widely understood and used",
                "Good for swing trading"
            ],
            weaknesses=[
                "Can stay overbought/oversold for extended periods",
                "Less effective in strong trends",
                "May generate false signals",
                "Requires confirmation"
            ],
            best_markets=[
                "Range-bound markets",
                "Individual stocks",
                "Forex pairs in consolidation",
                "Markets with regular cycles"
            ],
            code_example="""
# Calculate RSI
def calculate_rsi(data, period=14):
    return ta.momentum.RSIIndicator(data['close'], window=period).rsi()

# RSI Trading Signals
def rsi_signals(data, period=14, oversold=30, overbought=70):
    rsi = calculate_rsi(data, period)
    signals = pd.Series(0, index=data.index)
    
    # Buy when RSI crosses above oversold level
    buy_condition = (rsi > oversold) & (rsi.shift(1) <= oversold)
    
    # Sell when RSI crosses below overbought level
    sell_condition = (rsi < overbought) & (rsi.shift(1) >= overbought)
    
    signals[buy_condition] = 1
    signals[sell_condition] = -1
    
    return signals, rsi
            """,
            interactive_example=self._create_rsi_interactive,
            quiz_questions=[
                {
                    "question": "What do RSI values above 70 typically indicate?",
                    "options": ["Oversold", "Overbought", "Neutral", "Strong trend"],
                    "correct": 1,
                    "explanation": "RSI above 70 typically indicates overbought conditions where price may be due for a pullback."
                }
            ]
        )
    
    def _add_macd_lesson(self):
        """Add MACD lesson"""
        self.lessons['macd'] = IndicatorLesson(
            name="Moving Average Convergence Divergence (MACD)",
            category=IndicatorCategory.MOMENTUM,
            difficulty="intermediate",
            description="""
            MACD is a trend-following momentum indicator that shows the relationship 
            between two moving averages of a security's price. It consists of three components:
            MACD Line, Signal Line, and Histogram.
            """,
            formula_explanation="""
            MACD Line = 12-period EMA - 26-period EMA
            Signal Line = 9-period EMA of MACD Line
            MACD Histogram = MACD Line - Signal Line
            
            The MACD oscillates around zero, with crossovers above and below 
            zero line indicating potential trend changes.
            """,
            parameters={
                "fast_period": {"default": 12, "range": (8, 16), "description": "Fast EMA period"},
                "slow_period": {"default": 26, "range": (20, 32), "description": "Slow EMA period"},
                "signal_period": {"default": 9, "range": (6, 12), "description": "Signal line EMA period"}
            },
            signals={
                "buy": "MACD crosses above signal line or crosses above zero",
                "sell": "MACD crosses below signal line or crosses below zero",
                "bullish_divergence": "Price makes lower lows, MACD makes higher lows",
                "bearish_divergence": "Price makes higher highs, MACD makes lower highs"
            },
            strengths=[
                "Combines trend and momentum",
                "Clear visual signals",
                "Works well with divergence",
                "Effective in trending markets"
            ],
            weaknesses=[
                "Lagging indicator",
                "Can give false signals in choppy markets",
                "Not effective in sideways markets",
                "Requires confirmation"
            ],
            best_markets=[
                "Trending markets",
                "Major stock indices",
                "Large-cap stocks",
                "Forex majors with clear trends"
            ],
            code_example="""
# Calculate MACD
def calculate_macd(data, fast=12, slow=26, signal=9):
    macd_indicator = ta.trend.MACD(
        close=data['close'],
        window_fast=fast,
        window_slow=slow,
        window_sign=signal
    )
    
    macd = macd_indicator.macd()
    signal_line = macd_indicator.macd_signal()
    histogram = macd_indicator.macd_diff()
    
    return macd, signal_line, histogram

# MACD Trading Signals
def macd_signals(data, fast=12, slow=26, signal=9):
    macd, signal_line, histogram = calculate_macd(data, fast, slow, signal)
    signals = pd.Series(0, index=data.index)
    
    # Buy when MACD crosses above signal line
    buy_condition = (macd > signal_line) & (macd.shift(1) <= signal_line.shift(1))
    
    # Sell when MACD crosses below signal line
    sell_condition = (macd < signal_line) & (macd.shift(1) >= signal_line.shift(1))
    
    signals[buy_condition] = 1
    signals[sell_condition] = -1
    
    return signals, macd, signal_line, histogram
            """,
            interactive_example=self._create_macd_interactive,
            quiz_questions=[
                {
                    "question": "What does the MACD histogram represent?",
                    "options": [
                        "The difference between fast and slow EMAs",
                        "The difference between MACD and signal line",
                        "The volume of trades",
                        "The price momentum"
                    ],
                    "correct": 1,
                    "explanation": "MACD histogram shows the difference between the MACD line and signal line, indicating momentum changes."
                }
            ]
        )
    
    def _add_bollinger_bands_lesson(self):
        """Add Bollinger Bands lesson"""
        self.lessons['bollinger_bands'] = IndicatorLesson(
            name="Bollinger Bands",
            category=IndicatorCategory.VOLATILITY,
            difficulty="intermediate",
            description="""
            Bollinger Bands consist of a middle line (20-period SMA) and two outer bands 
            that are standard deviations away from the middle line. They expand and contract 
            based on market volatility, providing dynamic support and resistance levels.
            """,
            formula_explanation="""
            Middle Line = 20-period Simple Moving Average
            Upper Band = Middle Line + (2 × Standard Deviation)
            Lower Band = Middle Line - (2 × Standard Deviation)
            
            The bands widen during volatile periods and narrow during consolidation.
            Price tends to bounce between the bands in normal conditions.
            """,
            parameters={
                "period": {"default": 20, "range": (15, 25), "description": "Moving average period"},
                "std_dev": {"default": 2.0, "range": (1.5, 2.5), "description": "Standard deviation multiplier"}
            },
            signals={
                "buy": "Price touches lower band and moves back up",
                "sell": "Price touches upper band and moves back down",
                "squeeze": "Bands narrow significantly (low volatility)",
                "expansion": "Bands widen significantly (high volatility)"
            },
            strengths=[
                "Adapts to market volatility",
                "Provides dynamic support/resistance",
                "Good for mean reversion strategies",
                "Visual and intuitive"
            ],
            weaknesses=[
                "Not effective in trending markets",
                "Can give false signals during trends",
                "Requires volatility to function well",
                "Lagging indicator"
            ],
            best_markets=[
                "Range-bound markets",
                "Stocks in consolidation",
                "Forex during low volatility",
                "Markets with regular volatility cycles"
            ],
            code_example="""
# Calculate Bollinger Bands
def calculate_bollinger_bands(data, period=20, std_dev=2.0):
    bb = ta.volatility.BollingerBands(
        close=data['close'],
        window=period,
        window_dev=std_dev
    )
    
    upper_band = bb.bollinger_hband()
    lower_band = bb.bollinger_lband()
    middle_band = bb.bollinger_mavg()
    
    return upper_band, middle_band, lower_band

# Bollinger Bands Signals
def bollinger_signals(data, period=20, std_dev=2.0):
    upper, middle, lower = calculate_bollinger_bands(data, period, std_dev)
    signals = pd.Series(0, index=data.index)
    
    # Buy when price touches lower band
    buy_condition = (data['close'] <= lower) & (data['close'].shift(1) > lower.shift(1))
    
    # Sell when price touches upper band
    sell_condition = (data['close'] >= upper) & (data['close'].shift(1) < upper.shift(1))
    
    signals[buy_condition] = 1
    signals[sell_condition] = -1
    
    return signals, upper, middle, lower
            """,
            interactive_example=self._create_bollinger_interactive,
            quiz_questions=[
                {
                    "question": "What happens to Bollinger Bands during high volatility?",
                    "options": ["They narrow", "They widen", "They disappear", "They invert"],
                    "correct": 1,
                    "explanation": "Bollinger Bands widen during periods of high volatility and narrow during low volatility periods."
                }
            ]
        )
    
    def get_lesson(self, indicator_name: str) -> Optional[IndicatorLesson]:
        """Get a specific indicator lesson"""
        return self.lessons.get(indicator_name.lower())
    
    def list_available_lessons(self) -> Dict[str, Dict[str, str]]:
        """List all available lessons with basic info"""
        lesson_list = {}
        
        for name, lesson in self.lessons.items():
            lesson_list[name] = {
                "display_name": lesson.name,
                "category": lesson.category.value,
                "difficulty": lesson.difficulty,
                "description": lesson.description.split('.')[0] + '.'  # First sentence
            }
        
        return lesson_list
    
    def get_lessons_by_category(self, category: IndicatorCategory) -> Dict[str, IndicatorLesson]:
        """Get all lessons in a specific category"""
        return {
            name: lesson for name, lesson in self.lessons.items()
            if lesson.category == category
        }
    
    def get_lessons_by_difficulty(self, difficulty: str) -> Dict[str, IndicatorLesson]:
        """Get all lessons of a specific difficulty"""
        return {
            name: lesson for name, lesson in self.lessons.items()
            if lesson.difficulty == difficulty
        }
    
    def create_interactive_lesson(self, indicator_name: str, 
                                market_data: pd.DataFrame) -> Dict[str, Any]:
        """Create interactive lesson with real market data"""
        
        lesson = self.get_lesson(indicator_name)
        if not lesson:
            return {"error": f"Lesson for {indicator_name} not found"}
        
        try:
            # Generate interactive example
            interactive_result = lesson.interactive_example(market_data, lesson.parameters)
            
            return {
                "lesson": lesson,
                "interactive_chart": interactive_result["chart"],
                "analysis": interactive_result["analysis"],
                "signals": interactive_result["signals"],
                "performance": interactive_result.get("performance", {})
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create interactive lesson for {indicator_name}: {e}")
            return {"error": str(e)}
    
    def _create_stoch_rsi_interactive(self, data: pd.DataFrame, parameters: Dict) -> Dict[str, Any]:
        """Create interactive Stochastic RSI example"""
        
        # Calculate indicator with default parameters
        rsi_period = parameters.get("rsi_period", {}).get("default", 14)
        stoch_period = parameters.get("stoch_period", {}).get("default", 14)
        k_smooth = parameters.get("k_smooth", {}).get("default", 3)
        d_smooth = parameters.get("d_smooth", {}).get("default", 3)
        
        # Calculate RSI
        rsi = ta.momentum.RSIIndicator(data['close'], window=rsi_period).rsi()
        
        # Apply Stochastic to RSI
        rsi_high = rsi.rolling(window=stoch_period).max()
        rsi_low = rsi.rolling(window=stoch_period).min()
        
        k_percent = 100 * (rsi - rsi_low) / (rsi_high - rsi_low)
        k_percent = k_percent.rolling(window=k_smooth).mean()
        d_percent = k_percent.rolling(window=d_smooth).mean()
        
        # Generate signals
        signals = pd.Series(0, index=data.index)
        buy_condition = (
            (k_percent > d_percent) & 
            (k_percent.shift(1) <= d_percent.shift(1)) &
            (k_percent < 35)
        )
        sell_condition = (
            (k_percent < d_percent) & 
            (k_percent.shift(1) >= d_percent.shift(1)) &
            (k_percent > 80)
        )
        signals[buy_condition] = 1
        signals[sell_condition] = -1
        
        # Create chart
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.1,
            subplot_titles=['Price Chart', 'Stochastic RSI'],
            row_heights=[0.7, 0.3]
        )
        
        # Price chart
        fig.add_trace(
            go.Candlestick(
                x=data.index,
                open=data['open'],
                high=data['high'],
                low=data['low'],
                close=data['close'],
                name='Price'
            ),
            row=1, col=1
        )
        
        # Add buy/sell signals on price chart
        buy_signals = data[signals == 1]
        sell_signals = data[signals == -1]
        
        if not buy_signals.empty:
            fig.add_trace(
                go.Scatter(
                    x=buy_signals.index,
                    y=buy_signals['close'],
                    mode='markers',
                    marker=dict(symbol='triangle-up', size=10, color='green'),
                    name='Buy Signal'
                ),
                row=1, col=1
            )
        
        if not sell_signals.empty:
            fig.add_trace(
                go.Scatter(
                    x=sell_signals.index,
                    y=sell_signals['close'],
                    mode='markers',
                    marker=dict(symbol='triangle-down', size=10, color='red'),
                    name='Sell Signal'
                ),
                row=1, col=1
            )
        
        # Stochastic RSI subplot
        fig.add_trace(
            go.Scatter(
                x=data.index,
                y=k_percent,
                mode='lines',
                name='%K',
                line=dict(color='blue')
            ),
            row=2, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=data.index,
                y=d_percent,
                mode='lines',
                name='%D',
                line=dict(color='red')
            ),
            row=2, col=1
        )
        
        # Add reference lines
        fig.add_hline(y=80, line_dash="dash", line_color="red", opacity=0.5, row=2, col=1)
        fig.add_hline(y=35, line_dash="dash", line_color="green", opacity=0.5, row=2, col=1)
        fig.add_hline(y=20, line_dash="dash", line_color="orange", opacity=0.5, row=2, col=1)
        
        fig.update_layout(
            title="Interactive Stochastic RSI Example",
            xaxis_rangeslider_visible=False,
            height=600
        )
        
        # Analysis
        total_signals = len(buy_signals) + len(sell_signals)
        analysis = f"""
        <b>Stochastic RSI Analysis:</b><br>
        • Generated {len(buy_signals)} buy signals and {len(sell_signals)} sell signals<br>
        • Average %K: {k_percent.mean():.1f}<br>
        • Average %D: {d_percent.mean():.1f}<br>
        • Time in overbought (>80): {(k_percent > 80).sum() / len(k_percent) * 100:.1f}%<br>
        • Time in oversold (<35): {(k_percent < 35).sum() / len(k_percent) * 100:.1f}%<br>
        
        <b>Key Observations:</b><br>
        • Stochastic RSI is more sensitive than regular RSI<br>
        • Best signals occur when both lines are in extreme zones<br>
        • Crossovers in neutral zone (35-80) may be less reliable
        """
        
        return {
            "chart": fig,
            "analysis": analysis,
            "signals": {
                "buy_count": len(buy_signals),
                "sell_count": len(sell_signals),
                "total_signals": total_signals
            }
        }
    
    def _create_ema_interactive(self, data: pd.DataFrame, parameters: Dict) -> Dict[str, Any]:
        """Create interactive EMA example"""
        
        period = parameters.get("period", {}).get("default", 9)
        
        # Calculate EMA
        ema = ta.trend.EMAIndicator(data['close'], window=period).ema_indicator()
        
        # Generate signals (price vs EMA)
        signals = pd.Series(0, index=data.index)
        buy_condition = (data['close'] > ema) & (data['close'].shift(1) <= ema.shift(1))
        sell_condition = (data['close'] < ema) & (data['close'].shift(1) >= ema.shift(1))
        
        signals[buy_condition] = 1
        signals[sell_condition] = -1
        
        # Create chart
        fig = go.Figure()
        
        # Candlestick chart
        fig.add_trace(
            go.Candlestick(
                x=data.index,
                open=data['open'],
                high=data['high'],
                low=data['low'],
                close=data['close'],
                name='Price'
            )
        )
        
        # EMA line
        fig.add_trace(
            go.Scatter(
                x=data.index,
                y=ema,
                mode='lines',
                name=f'EMA({period})',
                line=dict(color='purple', width=2)
            )
        )
        
        # Signals
        buy_signals = data[signals == 1]
        sell_signals = data[signals == -1]
        
        if not buy_signals.empty:
            fig.add_trace(
                go.Scatter(
                    x=buy_signals.index,
                    y=buy_signals['close'],
                    mode='markers',
                    marker=dict(symbol='triangle-up', size=12, color='green'),
                    name='Buy Signal'
                )
            )
        
        if not sell_signals.empty:
            fig.add_trace(
                go.Scatter(
                    x=sell_signals.index,
                    y=sell_signals['close'],
                    mode='markers',
                    marker=dict(symbol='triangle-down', size=12, color='red'),
                    name='Sell Signal'
                )
            )
        
        fig.update_layout(
            title=f"Interactive EMA({period}) Example",
            xaxis_rangeslider_visible=False,
            height=500
        )
        
        # Calculate EMA slope for trend analysis
        ema_slope = ema.diff().rolling(window=5).mean()
        trending_up = (ema_slope > 0).sum() / len(ema_slope) * 100
        
        analysis = f"""
        <b>EMA({period}) Analysis:</b><br>
        • Generated {len(buy_signals)} buy signals and {len(sell_signals)} sell signals<br>
        • Current EMA: ${ema.iloc[-1]:.2f}<br>
        • Current Price: ${data['close'].iloc[-1]:.2f}<br>
        • Price above EMA: {(data['close'] > ema).sum() / len(data) * 100:.1f}% of time<br>
        • EMA trending up: {trending_up:.1f}% of time<br>
        
        <b>Trend Analysis:</b><br>
        • EMA slope indicates overall trend direction<br>
        • Price above rising EMA suggests bullish trend<br>
        • Price below falling EMA suggests bearish trend
        """
        
        return {
            "chart": fig,
            "analysis": analysis,
            "signals": {
                "buy_count": len(buy_signals),
                "sell_count": len(sell_signals)
            }
        }
    
    def _create_rsi_interactive(self, data: pd.DataFrame, parameters: Dict) -> Dict[str, Any]:
        """Create interactive RSI example"""
        # Implementation similar to others...
        # Shortened for brevity
        return {"chart": go.Figure(), "analysis": "RSI analysis", "signals": {}}
    
    def _create_macd_interactive(self, data: pd.DataFrame, parameters: Dict) -> Dict[str, Any]:
        """Create interactive MACD example"""
        # Implementation similar to others...
        return {"chart": go.Figure(), "analysis": "MACD analysis", "signals": {}}
    
    def _create_bollinger_interactive(self, data: pd.DataFrame, parameters: Dict) -> Dict[str, Any]:
        """Create interactive Bollinger Bands example"""
        # Implementation similar to others...
        return {"chart": go.Figure(), "analysis": "Bollinger Bands analysis", "signals": {}}
    
    def generate_study_path(self, experience_level: str = "beginner") -> List[str]:
        """Generate recommended learning path based on experience level"""
        
        paths = {
            "beginner": ["rsi", "ema", "stoch_rsi", "macd", "bollinger_bands"],
            "intermediate": ["stoch_rsi", "macd", "bollinger_bands", "rsi", "ema"],
            "advanced": ["macd", "stoch_rsi", "bollinger_bands", "rsi", "ema"]
        }
        
        return paths.get(experience_level, paths["beginner"])
    
    def create_indicator_comparison(self, indicators: List[str], 
                                  market_data: pd.DataFrame) -> Dict[str, Any]:
        """Compare multiple indicators on the same data"""
        
        comparison_results = {}
        
        for indicator in indicators:
            lesson = self.get_lesson(indicator)
            if lesson:
                interactive_result = self.create_interactive_lesson(indicator, market_data)
                if "error" not in interactive_result:
                    comparison_results[indicator] = {
                        "signals": interactive_result["signals"],
                        "lesson": lesson
                    }
        
        return comparison_results