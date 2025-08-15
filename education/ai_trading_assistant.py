import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Tuple, Optional, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import re

from education.indicator_academy import IndicatorAcademy, IndicatorCategory
from backtesting.backtesting_engine import BacktestingEngine
from backtesting.strategies import BacktestingStrategies
from services.backtesting_service import get_backtesting_service
from risk_management.risk_service import get_risk_service

class ConversationState(Enum):
    """AI Assistant conversation states"""
    GREETING = "greeting"
    INDICATOR_LEARNING = "indicator_learning"
    STRATEGY_BUILDING = "strategy_building"
    BACKTESTING = "backtesting"
    RISK_ANALYSIS = "risk_analysis"
    GENERAL_HELP = "general_help"

@dataclass
class UserContext:
    """User learning context and preferences"""
    experience_level: str = "beginner"  # beginner, intermediate, advanced
    learning_goals: List[str] = None
    completed_lessons: List[str] = None
    current_focus: str = None
    preferred_indicators: List[str] = None
    risk_tolerance: str = "moderate"  # conservative, moderate, aggressive
    trading_style: str = "swing"  # scalping, day, swing, position
    conversation_history: List[Dict[str, str]] = None
    
    def __post_init__(self):
        if self.learning_goals is None:
            self.learning_goals = []
        if self.completed_lessons is None:
            self.completed_lessons = []
        if self.conversation_history is None:
            self.conversation_history = []
        if self.preferred_indicators is None:
            self.preferred_indicators = []

class AITradingAssistant:
    """
    AI-powered trading assistant for education and guidance
    """
    
    def __init__(self):
        self.logger = logging.getLogger('education.ai_assistant')
        
        # Initialize components
        self.indicator_academy = IndicatorAcademy()
        self.backtesting_service = get_backtesting_service()
        self.risk_service = get_risk_service()
        
        # User contexts (in production, this would be persistent storage)
        self.user_contexts: Dict[str, UserContext] = {}
        
        # Conversation state tracking
        self.current_state = ConversationState.GREETING
        
        # Knowledge base
        self.knowledge_base = self._initialize_knowledge_base()
        
        self.logger.info("AI Trading Assistant initialized")
    
    def _initialize_knowledge_base(self) -> Dict[str, Any]:
        """Initialize the assistant's knowledge base"""
        
        return {
            "indicator_explanations": {
                "what_are_indicators": """
                Technical indicators are mathematical calculations based on price, volume, or open interest 
                that help traders analyze market trends and make informed decisions. They fall into several categories:
                
                📈 **Trend Indicators** (like EMA, MACD): Show market direction
                ⚡ **Momentum Indicators** (like RSI, Stochastic RSI): Show speed of price changes  
                📊 **Volatility Indicators** (like Bollinger Bands): Show market volatility
                📦 **Volume Indicators**: Show trading activity levels
                """,
                
                "how_to_use_indicators": """
                Indicators work best when used together! Here's how:
                
                1. **Confirm Signals**: Use 2-3 indicators to confirm each other
                2. **Understand Context**: Consider market conditions and timeframes
                3. **Manage Risk**: Always use stop-losses and position sizing
                4. **Practice First**: Backtest your strategies before live trading
                5. **Stay Disciplined**: Stick to your rules and don't chase trades
                """,
                
                "common_mistakes": """
                ⚠️ **Avoid These Common Mistakes:**
                
                • Using too many indicators (analysis paralysis)
                • Ignoring market context and overall trend
                • Not understanding what each indicator actually measures
                • Over-optimizing based on historical data
                • Trading without proper risk management
                • Expecting indicators to predict the future perfectly
                """
            },
            
            "strategy_building": {
                "beginner_strategies": [
                    "Simple EMA crossover (9 and 21 periods)",
                    "RSI oversold/overbought reversal",
                    "Bollinger Bands mean reversion"
                ],
                "intermediate_strategies": [
                    "Stochastic RSI with trend confirmation",
                    "MACD with EMA filter",
                    "Multi-timeframe analysis"
                ],
                "advanced_strategies": [
                    "Multi-indicator confluence systems",
                    "Market regime adaptive strategies",
                    "Options strategies with technical analysis"
                ]
            },
            
            "risk_management_principles": [
                "Never risk more than 1-2% of your account per trade",
                "Use stop-losses on every trade",
                "Diversify across different assets and strategies",
                "Size positions based on volatility and risk",
                "Review and adjust your risk rules regularly"
            ],
            
            "market_wisdom": [
                "The trend is your friend (until it ends)",
                "Cut your losses short, let your winners run",
                "Don't try to catch a falling knife",
                "The market can stay irrational longer than you can stay solvent",
                "Plan your trade, trade your plan"
            ]
        }
    
    def chat(self, user_id: str, message: str) -> Dict[str, Any]:
        """
        Main chat interface for the AI assistant
        
        Args:
            user_id: Unique identifier for the user
            message: User's message/question
            
        Returns:
            Dictionary with assistant's response and actions
        """
        
        # Get or create user context
        if user_id not in self.user_contexts:
            self.user_contexts[user_id] = UserContext()
        
        context = self.user_contexts[user_id]
        
        # Add message to conversation history
        context.conversation_history.append({
            "timestamp": datetime.now().isoformat(),
            "user": message,
            "state": self.current_state.value
        })
        
        # Process the message and generate response
        response = self._process_message(message, context)
        
        # Add response to conversation history
        context.conversation_history.append({
            "timestamp": datetime.now().isoformat(),
            "assistant": response["message"],
            "state": self.current_state.value
        })
        
        # Update user context based on interaction
        self._update_user_context(context, message, response)
        
        self.logger.info(f"Processed chat message for user {user_id}")
        
        return response
    
    def _process_message(self, message: str, context: UserContext) -> Dict[str, Any]:
        """Process user message and generate appropriate response"""
        
        message_lower = message.lower()
        
        # Detect intent
        intent = self._detect_intent(message_lower)
        
        # Generate response based on intent
        if intent == "greeting":
            return self._handle_greeting(context)
        
        elif intent == "indicator_question":
            return self._handle_indicator_question(message, context)
        
        elif intent == "strategy_help":
            return self._handle_strategy_help(message, context)
        
        elif intent == "backtesting_request":
            return self._handle_backtesting_request(message, context)
        
        elif intent == "risk_management":
            return self._handle_risk_management(message, context)
        
        elif intent == "learning_path":
            return self._handle_learning_path(message, context)
        
        elif intent == "performance_analysis":
            return self._handle_performance_analysis(message, context)
        
        else:
            return self._handle_general_question(message, context)
    
    def _detect_intent(self, message: str) -> str:
        """Detect user intent from message"""
        
        intent_patterns = {
            "greeting": [r"hello", r"hi", r"hey", r"start", r"help", r"guide"],
            "indicator_question": [
                r"what is", r"how does.*work", r"explain", r"stochrsi", r"rsi", 
                r"ema", r"macd", r"bollinger", r"indicator", r"oscillator"
            ],
            "strategy_help": [
                r"strategy", r"trading.*system", r"build.*strategy", r"create.*strategy",
                r"combine.*indicators", r"trading.*rules"
            ],
            "backtesting_request": [
                r"backtest", r"test.*strategy", r"historical.*test", r"performance.*test",
                r"how.*perform", r"results"
            ],
            "risk_management": [
                r"risk", r"position.*siz", r"stop.*loss", r"money.*management", 
                r"risk.*management", r"safe.*trading"
            ],
            "learning_path": [
                r"learn", r"start.*with", r"beginner", r"where.*begin", r"study.*path",
                r"curriculum", r"course"
            ],
            "performance_analysis": [
                r"analyze.*performance", r"portfolio.*analysis", r"how.*doing", 
                r"performance.*report", r"results"
            ]
        }
        
        for intent, patterns in intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, message):
                    return intent
        
        return "general"
    
    def _handle_greeting(self, context: UserContext) -> Dict[str, Any]:
        """Handle greeting and introduction"""
        
        greeting_message = f"""
        👋 **Welcome to your AI Trading Assistant!** 
        
        I'm here to help you learn about technical indicators and build smart trading algorithms. 
        
        **What I can help you with:**
        📚 Learn about technical indicators (StochRSI, EMA, RSI, MACD, etc.)
        🏗️ Build and optimize trading strategies  
        🔬 Backtest your strategies with historical data
        ⚖️ Understand risk management principles
        📊 Analyze your trading performance
        
        **Your Learning Level:** {context.experience_level.title()}
        
        **Quick Start Options:**
        • Type "**explain stochrsi**" to learn about your current strategy
        • Type "**build a strategy**" to create a new trading system
        • Type "**backtest my strategy**" to test performance
        • Type "**learning path**" for a personalized curriculum
        
        What would you like to explore first? 🚀
        """
        
        return {
            "message": greeting_message,
            "actions": ["show_quick_start_options"],
            "suggestions": [
                "Explain StochRSI indicator",
                "Show me a simple strategy", 
                "Create learning path",
                "Risk management basics"
            ]
        }
    
    def _handle_indicator_question(self, message: str, context: UserContext) -> Dict[str, Any]:
        """Handle questions about specific indicators"""
        
        # Extract indicator name from message
        indicator_name = self._extract_indicator_name(message)
        
        if indicator_name:
            lesson = self.indicator_academy.get_lesson(indicator_name)
            
            if lesson:
                # Generate comprehensive explanation
                explanation = f"""
                ## 📈 {lesson.name} - {lesson.difficulty.title()} Level
                
                **What it is:**
                {lesson.description}
                
                **How it works:**
                {lesson.formula_explanation}
                
                **Trading Signals:**
                """
                
                for signal_type, signal_desc in lesson.signals.items():
                    explanation += f"\n• **{signal_type.replace('_', ' ').title()}:** {signal_desc}"
                
                explanation += f"""
                
                **✅ Strengths:**
                """
                for strength in lesson.strengths:
                    explanation += f"\n• {strength}"
                
                explanation += f"""
                
                **⚠️ Limitations:**
                """
                for weakness in lesson.weaknesses:
                    explanation += f"\n• {weakness}"
                
                explanation += f"""
                
                **💡 Pro Tips:**
                • Best used in {', '.join(lesson.best_markets[:3])}
                • Combine with other indicators for confirmation
                • Always use proper risk management
                
                **Want to see it in action?** Type "**show {indicator_name} example**" for an interactive demo!
                """
                
                # Add to completed lessons
                if indicator_name not in context.completed_lessons:
                    context.completed_lessons.append(indicator_name)
                
                return {
                    "message": explanation,
                    "actions": ["show_indicator_lesson"],
                    "indicator_data": {
                        "name": indicator_name,
                        "lesson": lesson
                    },
                    "suggestions": [
                        f"Show {indicator_name} example",
                        f"How to use {indicator_name} in strategy",
                        "Compare with other indicators",
                        "Build strategy with this indicator"
                    ]
                }
            else:
                available_indicators = list(self.indicator_academy.lessons.keys())
                return {
                    "message": f"""
                    I don't have a lesson for "{indicator_name}" yet, but I can teach you about:
                    
                    **Available Indicators:**
                    {', '.join([name.replace('_', ' ').title() for name in available_indicators])}
                    
                    Which one interests you most? 🤔
                    """,
                    "suggestions": [f"Explain {name}" for name in available_indicators[:4]]
                }
        else:
            return {
                "message": """
                I'd love to explain an indicator for you! Here are the ones I can teach:
                
                **📊 Momentum Indicators:**
                • Stochastic RSI - Your current strategy indicator
                • RSI (Relative Strength Index)
                • MACD (Moving Average Convergence Divergence)
                
                **📈 Trend Indicators:**  
                • EMA (Exponential Moving Average)
                
                **📉 Volatility Indicators:**
                • Bollinger Bands
                
                Just ask me about any of these! For example: "**Explain Stochastic RSI**" 
                """,
                "suggestions": [
                    "Explain Stochastic RSI",
                    "What is RSI?",
                    "How does MACD work?",
                    "Tell me about EMA"
                ]
            }
    
    def _handle_strategy_help(self, message: str, context: UserContext) -> Dict[str, Any]:
        """Handle strategy building assistance"""
        
        if "build" in message.lower() or "create" in message.lower():
            return self._strategy_builder_wizard(context)
        else:
            return self._provide_strategy_guidance(context)
    
    def _strategy_builder_wizard(self, context: UserContext) -> Dict[str, Any]:
        """Interactive strategy building wizard"""
        
        message = f"""
        🏗️ **Strategy Builder Wizard**
        
        Let's build you a personalized trading strategy! I'll ask a few questions to understand your preferences.
        
        **Step 1: Trading Style**
        What's your preferred trading timeframe?
        
        🕐 **Scalping** (minutes): Quick trades, high frequency
        📅 **Day Trading** (hours): Trades within a single day  
        📊 **Swing Trading** (days/weeks): Medium-term position holds
        📈 **Position Trading** (weeks/months): Long-term trend following
        
        **Current Selection:** {context.trading_style.title()}
        
        **Step 2: Risk Tolerance**
        How much risk are you comfortable with?
        
        🛡️ **Conservative**: Lower returns, lower risk
        ⚖️ **Moderate**: Balanced risk/reward
        🎯 **Aggressive**: Higher potential returns, higher risk
        
        **Current Selection:** {context.risk_tolerance.title()}
        
        Based on your profile, I recommend starting with a **{self._recommend_strategy(context)}** strategy.
        
        Would you like me to:
        • **Design** a custom strategy for you
        • **Explain** the recommended strategy  
        • **Show examples** of similar strategies
        • **Backtest** a strategy idea
        """
        
        return {
            "message": message,
            "actions": ["strategy_builder_wizard"],
            "suggestions": [
                "Design custom strategy",
                "Explain recommended strategy", 
                "Show strategy examples",
                "Let's backtest something"
            ]
        }
    
    def _recommend_strategy(self, context: UserContext) -> str:
        """Recommend strategy based on user context"""
        
        if context.experience_level == "beginner":
            if context.trading_style == "swing":
                return "EMA Crossover with RSI Confirmation"
            else:
                return "Simple RSI Mean Reversion"
        
        elif context.experience_level == "intermediate":
            if context.trading_style in ["day", "swing"]:
                return "Stochastic RSI with Trend Filter"
            else:
                return "MACD with Multiple Timeframe Analysis"
        
        else:  # advanced
            return "Multi-Indicator Confluence System"
    
    def _handle_backtesting_request(self, message: str, context: UserContext) -> Dict[str, Any]:
        """Handle backtesting requests"""
        
        return {
            "message": """
            🔬 **Backtesting Lab**
            
            Great choice! Backtesting is crucial for validating trading strategies. 
            
            **What I can test for you:**
            
            📊 **Available Strategies:**
            • Stochastic RSI (your current setup)
            • EMA Crossover systems
            • RSI mean reversion  
            • MACD trend following
            • Multi-indicator combinations
            
            📈 **Test Parameters:**
            • Symbol: Any stock/ETF (default: SPY)
            • Time period: 1 month to 5 years
            • Initial capital: $10K - $1M
            • Risk management rules
            
            **Example Commands:**
            • "**Backtest StochRSI on AAPL**"
            • "**Test EMA crossover strategy**" 
            • "**Compare RSI vs StochRSI performance**"
            
            What strategy would you like to test? 🧪
            """,
            "actions": ["backtesting_interface"],
            "suggestions": [
                "Backtest StochRSI strategy",
                "Test EMA crossover",
                "Compare multiple strategies",
                "Optimize strategy parameters"
            ]
        }
    
    def _handle_risk_management(self, message: str, context: UserContext) -> Dict[str, Any]:
        """Handle risk management education"""
        
        return {
            "message": f"""
            ⚖️ **Risk Management Mastery**
            
            Excellent question! Risk management is the #1 factor in trading success.
            
            **🛡️ Core Principles:**
            
            **1. Position Sizing**
            • Risk only 1-2% of account per trade
            • Your current risk tolerance: **{context.risk_tolerance}**
            • Use our position calculator for optimal sizing
            
            **2. Stop Loss Strategy**  
            • Always have an exit plan before entering
            • Use ATR-based stops for market volatility
            • Never move stops against your position
            
            **3. Portfolio Diversification**
            • Don't put all eggs in one basket
            • Spread risk across different assets/strategies
            • Monitor correlation between positions
            
            **4. Risk-Reward Ratios**
            • Target minimum 1:2 risk-reward ratio
            • Let winners run, cut losses short
            • Track your win rate vs average win/loss
            
            **🧮 Want me to calculate optimal position sizes for your trades?**
            
            **📊 Or analyze your current portfolio risk?**
            
            The risk management tools are built right into this system!
            """,
            "actions": ["risk_management_tools"],
            "suggestions": [
                "Calculate position size",
                "Analyze portfolio risk", 
                "Set up stop-loss rules",
                "Risk-reward calculator"
            ]
        }
    
    def _handle_learning_path(self, message: str, context: UserContext) -> Dict[str, Any]:
        """Handle learning path requests"""
        
        path = self.indicator_academy.generate_study_path(context.experience_level)
        completed = set(context.completed_lessons)
        
        path_message = f"""
        📚 **Your Personalized Learning Path** - {context.experience_level.title()} Level
        
        Here's your recommended study sequence:
        
        """
        
        for i, indicator in enumerate(path, 1):
            lesson = self.indicator_academy.get_lesson(indicator)
            status = "✅" if indicator in completed else "📖"
            
            path_message += f"""
        **{i}. {status} {lesson.name}** - {lesson.category.value.title()}
        {lesson.description.split('.')[0]}.
        {'*Completed!*' if indicator in completed else '*Ready to learn*'}
        
        """
        
        next_lesson = None
        for indicator in path:
            if indicator not in completed:
                next_lesson = indicator
                break
        
        if next_lesson:
            path_message += f"""
        **🎯 Next Up: {self.indicator_academy.get_lesson(next_lesson).name}**
        
        Ready to continue? Type "**explain {next_lesson}**" to start your next lesson!
        """
        else:
            path_message += """
        **🎉 Congratulations!** You've completed the core curriculum!
        
        Ready for advanced topics:
        • Multi-indicator strategies
        • Market regime analysis  
        • Advanced risk management
        • Algorithm development
        """
        
        return {
            "message": path_message,
            "actions": ["learning_path"],
            "learning_data": {
                "path": path,
                "completed": list(completed),
                "next_lesson": next_lesson
            },
            "suggestions": [
                f"Explain {next_lesson}" if next_lesson else "Advanced strategies",
                "Show my progress",
                "Quiz me on indicators",
                "Build a strategy"
            ]
        }
    
    def _handle_performance_analysis(self, message: str, context: UserContext) -> Dict[str, Any]:
        """Handle performance analysis requests"""
        
        return {
            "message": """
            📊 **Performance Analysis Center**
            
            I can help you analyze trading performance in several ways:
            
            **📈 Strategy Performance**
            • Backtest results analysis
            • Win rate and profit factor metrics
            • Risk-adjusted returns (Sharpe, Sortino ratios)
            • Maximum drawdown analysis
            
            **💼 Portfolio Analysis**  
            • Current position risk assessment
            • Correlation analysis between holdings
            • Value at Risk (VaR) calculations
            • Diversification recommendations
            
            **📋 Trade Analysis**
            • Individual trade performance
            • Entry/exit timing analysis
            • Risk management effectiveness
            • Pattern recognition in winners/losers
            
            **🎯 Optimization**
            • Parameter optimization suggestions
            • Strategy improvement recommendations
            • Risk management adjustments
            
            What type of analysis would you like to run?
            """,
            "actions": ["performance_analysis"],
            "suggestions": [
                "Analyze current portfolio",
                "Review strategy performance",
                "Calculate portfolio VaR",
                "Optimize strategy parameters"
            ]
        }
    
    def _handle_general_question(self, message: str, context: UserContext) -> Dict[str, Any]:
        """Handle general trading questions"""
        
        # Check if question matches knowledge base topics
        message_lower = message.lower()
        
        if any(word in message_lower for word in ["trend", "trending", "direction"]):
            return self._explain_trend_analysis()
        elif any(word in message_lower for word in ["volume", "liquidity"]):
            return self._explain_volume_analysis()
        elif any(word in message_lower for word in ["support", "resistance", "levels"]):
            return self._explain_support_resistance()
        else:
            return {
                "message": f"""
                I'm here to help with technical analysis and algorithmic trading! 
                
                **🤔 Not sure what you're looking for?** Try these:
                
                **📚 Learning:**
                • "Explain [indicator name]" - Learn about indicators
                • "Learning path" - Get personalized curriculum
                • "Strategy examples" - See trading strategies
                
                **🏗️ Building:**  
                • "Build a strategy" - Create custom strategy
                • "Backtest [strategy]" - Test performance
                • "Risk analysis" - Analyze portfolio risk
                
                **💡 Quick Tips:**
                • Ask specific questions about indicators
                • Request examples and demonstrations
                • Get help with strategy development
                
                What specific aspect of trading would you like to explore? 🎯
                """,
                "suggestions": [
                    "Show available indicators",
                    "Explain trend analysis",
                    "Risk management basics",
                    "Strategy building guide"
                ]
            }
    
    def _extract_indicator_name(self, message: str) -> Optional[str]:
        """Extract indicator name from user message"""
        
        indicator_keywords = {
            "stochrsi": "stoch_rsi",
            "stochastic rsi": "stoch_rsi", 
            "stoch rsi": "stoch_rsi",
            "rsi": "rsi",
            "relative strength": "rsi",
            "ema": "ema",
            "exponential moving average": "ema",
            "moving average": "ema",
            "macd": "macd",
            "bollinger": "bollinger_bands",
            "bollinger bands": "bollinger_bands"
        }
        
        message_lower = message.lower()
        
        for keyword, indicator in indicator_keywords.items():
            if keyword in message_lower:
                return indicator
        
        return None
    
    def _update_user_context(self, context: UserContext, message: str, response: Dict[str, Any]):
        """Update user context based on interaction"""
        
        # Update current focus based on conversation
        if "actions" in response:
            if "show_indicator_lesson" in response["actions"]:
                context.current_focus = "indicator_learning"
            elif "strategy_builder_wizard" in response["actions"]:
                context.current_focus = "strategy_building"
            elif "backtesting_interface" in response["actions"]:
                context.current_focus = "backtesting"
            elif "risk_management_tools" in response["actions"]:
                context.current_focus = "risk_analysis"
        
        # Update learning goals based on questions
        message_lower = message.lower()
        if "learn" in message_lower and context.current_focus not in context.learning_goals:
            context.learning_goals.append(context.current_focus)
    
    def _explain_trend_analysis(self) -> Dict[str, Any]:
        """Explain trend analysis concepts"""
        
        return {
            "message": """
            📈 **Trend Analysis Fundamentals**
            
            **What is a Trend?**
            A trend is the general direction of price movement over time.
            
            **📊 Types of Trends:**
            • **Uptrend**: Higher highs and higher lows
            • **Downtrend**: Lower highs and lower lows  
            • **Sideways**: Price moves in a range
            
            **🔍 Identifying Trends:**
            • **Moving Averages**: EMA/SMA direction and slope
            • **Trendlines**: Connect swing highs/lows
            • **Price Action**: Series of higher/lower highs and lows
            
            **⚡ Trend Strength Indicators:**
            • **MACD**: Shows momentum behind trends
            • **RSI**: Identifies if trend is overextended
            • **Volume**: Confirms trend validity
            
            **💡 Trading with Trends:**
            • "Trend is your friend" - trade in trend direction
            • Use pullbacks as entry opportunities
            • Exit when trend shows signs of reversal
            
            Want to learn about specific trend indicators? 🎯
            """,
            "suggestions": [
                "Explain EMA for trends",
                "How to draw trendlines",  
                "MACD trend analysis",
                "Trend reversal signals"
            ]
        }
    
    def _explain_volume_analysis(self) -> Dict[str, Any]:
        """Explain volume analysis concepts"""
        
        return {
            "message": """
            📊 **Volume Analysis Essentials**
            
            **What is Volume?**
            Volume is the number of shares/contracts traded in a given period.
            
            **🔑 Key Volume Principles:**
            • **Confirmation**: Volume should confirm price moves
            • **Breakouts**: High volume confirms valid breakouts
            • **Reversals**: Volume spikes often mark turning points
            
            **📈 Volume Patterns:**
            • **High Volume + Up**: Strong buying pressure
            • **High Volume + Down**: Strong selling pressure
            • **Low Volume**: Lack of conviction, potential reversal
            • **Increasing Volume**: Trend gaining strength
            
            **⚖️ Volume Indicators:**
            • **Volume Moving Average**: Smooth volume trends
            • **Volume Oscillator**: Compare current to average volume
            • **OBV (On-Balance Volume)**: Cumulative volume indicator
            
            **💡 Trading Applications:**
            • Confirm breakouts with volume spikes
            • Watch for volume divergences
            • Use low volume for better entry prices
            
            Volume is the fuel that drives price movements! 🚀
            """,
            "suggestions": [
                "Volume breakout strategies",
                "How to read volume charts",
                "Volume divergence signals", 
                "OBV indicator explanation"
            ]
        }
    
    def _explain_support_resistance(self) -> Dict[str, Any]:
        """Explain support and resistance concepts"""
        
        return {
            "message": """
            🏗️ **Support & Resistance Mastery**
            
            **What are Support & Resistance?**
            • **Support**: Price level where buying pressure exceeds selling
            • **Resistance**: Price level where selling pressure exceeds buying
            
            **🎯 Types of S&R Levels:**
            
            **Horizontal Levels:**
            • Previous highs/lows
            • Round numbers (100, 200, etc.)
            • Psychological levels
            
            **Dynamic Levels:**  
            • Moving averages (EMA/SMA)
            • Trendlines
            • Bollinger Bands
            
            **📊 Identifying Strong Levels:**
            • **Multiple touches**: More tests = stronger level
            • **Volume**: High volume at level confirms importance
            • **Time**: Older levels often more significant
            • **Round numbers**: Psychological significance
            
            **💡 Trading S&R:**
            • **Buy at support**, sell at resistance
            • **Breakouts**: Enter when price breaks through
            • **Role reversal**: Support becomes resistance (and vice versa)
            • **Stop placement**: Just beyond S&R levels
            
            **⚠️ Pro Tips:**
            • S&R are zones, not exact lines
            • Combine with other indicators for confirmation
            • Watch for false breakouts (common trap!)
            
            These levels are the foundation of technical analysis! 🎯
            """,
            "suggestions": [
                "How to draw support lines",
                "Breakout trading strategies",
                "Dynamic support with EMAs",
                "False breakout identification"
            ]
        }
    
    def get_user_progress(self, user_id: str) -> Dict[str, Any]:
        """Get user's learning progress"""
        
        if user_id not in self.user_contexts:
            return {"error": "User not found"}
        
        context = self.user_contexts[user_id]
        
        total_lessons = len(self.indicator_academy.lessons)
        completed_count = len(context.completed_lessons)
        
        progress = {
            "experience_level": context.experience_level,
            "completed_lessons": context.completed_lessons,
            "total_lessons": total_lessons,
            "completion_percentage": (completed_count / total_lessons) * 100,
            "learning_goals": context.learning_goals,
            "current_focus": context.current_focus,
            "recommended_next": self._get_next_recommendation(context),
            "conversation_count": len([msg for msg in context.conversation_history if "user" in msg])
        }
        
        return progress
    
    def _get_next_recommendation(self, context: UserContext) -> str:
        """Get next learning recommendation for user"""
        
        path = self.indicator_academy.generate_study_path(context.experience_level)
        
        for indicator in path:
            if indicator not in context.completed_lessons:
                lesson = self.indicator_academy.get_lesson(indicator)
                return f"Learn about {lesson.name}"
        
        return "Explore advanced strategies and multi-indicator systems"
    
    def create_personalized_strategy(self, user_id: str, preferences: Dict[str, Any]) -> Dict[str, Any]:
        """Create personalized strategy based on user preferences"""
        
        if user_id not in self.user_contexts:
            return {"error": "User not found"}
        
        context = self.user_contexts[user_id]
        
        # Generate strategy based on preferences and experience level
        strategy_config = {
            "name": f"Personalized_{context.experience_level}_Strategy",
            "indicators": self._select_indicators(context, preferences),
            "parameters": self._optimize_parameters(context, preferences),
            "risk_rules": self._create_risk_rules(context, preferences),
            "entry_rules": [],
            "exit_rules": []
        }
        
        # Generate entry/exit rules based on selected indicators
        strategy_config["entry_rules"] = self._generate_entry_rules(strategy_config["indicators"])
        strategy_config["exit_rules"] = self._generate_exit_rules(context)
        
        return {
            "strategy": strategy_config,
            "explanation": self._explain_strategy(strategy_config),
            "next_steps": [
                "Backtest the strategy",
                "Optimize parameters",
                "Paper trade first",
                "Implement risk management"
            ]
        }
    
    def _select_indicators(self, context: UserContext, preferences: Dict[str, Any]) -> List[str]:
        """Select optimal indicators based on user profile"""
        
        base_indicators = ["stoch_rsi", "ema"]  # Always include current setup
        
        if context.experience_level == "beginner":
            return base_indicators + ["rsi"]
        elif context.experience_level == "intermediate":
            return base_indicators + ["macd", "bollinger_bands"]
        else:  # advanced
            return base_indicators + ["macd", "bollinger_bands", "rsi"]
    
    def _optimize_parameters(self, context: UserContext, preferences: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize parameters based on trading style and risk tolerance"""
        
        base_params = {
            "stoch_rsi": {
                "rsi_period": 14,
                "stoch_period": 14,
                "k_smooth": 3,
                "d_smooth": 3,
                "oversold": 35,
                "overbought": 80
            },
            "ema_fast": 9,
            "ema_slow": 21
        }
        
        # Adjust based on trading style
        if context.trading_style == "scalping":
            base_params["stoch_rsi"]["oversold"] = 30
            base_params["stoch_rsi"]["overbought"] = 70
            base_params["ema_fast"] = 7
        elif context.trading_style == "position":
            base_params["ema_fast"] = 12
            base_params["ema_slow"] = 26
        
        return base_params
    
    def _create_risk_rules(self, context: UserContext, preferences: Dict[str, Any]) -> Dict[str, Any]:
        """Create risk management rules"""
        
        risk_multipliers = {
            "conservative": 0.5,
            "moderate": 1.0,
            "aggressive": 1.5
        }
        
        multiplier = risk_multipliers.get(context.risk_tolerance, 1.0)
        
        return {
            "max_risk_per_trade": 0.02 * multiplier,  # 1-3% based on tolerance
            "max_positions": 3 if context.experience_level == "beginner" else 5,
            "stop_loss_atr_multiple": 2.0,
            "take_profit_ratio": 2.0,  # 2:1 risk-reward
            "trailing_stop": True if context.trading_style in ["swing", "position"] else False
        }
    
    def _generate_entry_rules(self, indicators: List[str]) -> List[str]:
        """Generate entry rules based on selected indicators"""
        
        rules = []
        
        if "stoch_rsi" in indicators:
            rules.append("StochRSI %K > %D and both < 35 (oversold region)")
        
        if "ema" in indicators:
            rules.append("Price above fast EMA and fast EMA > slow EMA (trend confirmation)")
        
        if "rsi" in indicators:
            rules.append("RSI < 40 (not overbought)")
        
        if "macd" in indicators:
            rules.append("MACD > Signal line (momentum confirmation)")
        
        return rules
    
    def _generate_exit_rules(self, context: UserContext) -> List[str]:
        """Generate exit rules based on user profile"""
        
        rules = [
            "Stop loss: 2x ATR below entry",
            "Take profit: 2x stop loss distance (2:1 R:R)",
        ]
        
        if context.trading_style in ["swing", "position"]:
            rules.append("Trailing stop: Move stop to breakeven when 1R profit reached")
        
        if context.risk_tolerance == "conservative":
            rules.append("Exit 50% at 1:1 R:R, let remainder run to target")
        
        return rules
    
    def _explain_strategy(self, strategy_config: Dict[str, Any]) -> str:
        """Generate human-readable strategy explanation"""
        
        explanation = f"""
        **🎯 {strategy_config['name']} Explanation**
        
        **Indicators Used:**
        """
        
        for indicator in strategy_config['indicators']:
            lesson = self.indicator_academy.get_lesson(indicator)
            if lesson:
                explanation += f"\n• **{lesson.name}**: {lesson.description.split('.')[0]}"
        
        explanation += """
        
        **📈 Entry Conditions:**
        """
        
        for rule in strategy_config['entry_rules']:
            explanation += f"\n• {rule}"
        
        explanation += """
        
        **📉 Exit Conditions:**
        """
        
        for rule in strategy_config['exit_rules']:
            explanation += f"\n• {rule}"
        
        explanation += f"""
        
        **⚖️ Risk Management:**
        • Maximum risk per trade: {strategy_config['risk_rules']['max_risk_per_trade']*100:.1f}%
        • Maximum positions: {strategy_config['risk_rules']['max_positions']}
        • Risk-reward ratio: 1:{strategy_config['risk_rules']['take_profit_ratio']}
        
        This strategy is designed to capture momentum reversals while maintaining strict risk control.
        """
        
        return explanation

# Global AI assistant instance
_ai_assistant = None

def get_ai_assistant() -> AITradingAssistant:
    """Get singleton AI trading assistant instance"""
    global _ai_assistant
    if _ai_assistant is None:
        _ai_assistant = AITradingAssistant()
    return _ai_assistant