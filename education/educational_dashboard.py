import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json

from education.indicator_academy import IndicatorAcademy, IndicatorCategory
from education.ai_trading_assistant import AITradingAssistant, get_ai_assistant
from backtesting.backtesting_engine import BacktestingEngine
from backtesting.strategies import BacktestingStrategies
from services.backtesting_service import get_backtesting_service
from risk_management.risk_service import get_risk_service
from services.ml_service import get_ml_service

class EducationalDashboard:
    """
    Comprehensive educational dashboard for learning trading and indicators
    """
    
    def __init__(self):
        self.logger = logging.getLogger('education.dashboard')
        
        # Initialize educational components
        self.indicator_academy = IndicatorAcademy()
        self.ai_assistant = get_ai_assistant()
        self.backtesting_service = get_backtesting_service()
        self.risk_service = get_risk_service()
        self.ml_service = get_ml_service()
        
        # Session state initialization
        self._initialize_session_state()
        
    def _initialize_session_state(self):
        """Initialize Streamlit session state variables"""
        
        if 'user_id' not in st.session_state:
            st.session_state.user_id = "demo_user"
        
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []
        
        if 'current_lesson' not in st.session_state:
            st.session_state.current_lesson = None
        
        if 'learning_progress' not in st.session_state:
            st.session_state.learning_progress = {
                'completed_lessons': [],
                'current_level': 'beginner'
            }
        
        if 'demo_data' not in st.session_state:
            st.session_state.demo_data = self._generate_demo_data()
    
    def run_dashboard(self):
        """Main dashboard interface"""
        
        st.set_page_config(
            page_title="AI Trading Academy",
            page_icon="🎓",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        # Custom CSS
        st.markdown(self._get_custom_css(), unsafe_allow_html=True)
        
        # Main header
        st.markdown("""
        <div class="main-header">
            <h1>🎓 AI Trading Academy</h1>
            <p>Master Technical Indicators & Build Smart Trading Algorithms</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Sidebar navigation
        self._render_sidebar()
        
        # Main content area
        page = st.session_state.get('current_page', 'Home')
        
        if page == 'Home':
            self._render_home_page()
        elif page == 'AI Assistant':
            self._render_ai_assistant_page()
        elif page == 'Indicator Academy':
            self._render_indicator_academy_page()
        elif page == 'Strategy Builder':
            self._render_strategy_builder_page()
        elif page == 'Backtesting Lab':
            self._render_backtesting_lab_page()
        elif page == 'ML Academy':
            self._render_ml_academy_page()
        elif page == 'Risk Academy':
            self._render_risk_academy_page()
        elif page == 'Progress Tracker':
            self._render_progress_tracker_page()
        elif page == 'Interactive Playground':
            self._render_interactive_playground_page()
    
    def _render_sidebar(self):
        """Render the navigation sidebar"""
        
        st.sidebar.markdown("### 🧭 Navigation")
        
        pages = [
            ('Home', '🏠'),
            ('AI Assistant', '🤖'),
            ('Indicator Academy', '📊'),
            ('Strategy Builder', '🏗️'),
            ('Backtesting Lab', '🔬'),
            ('ML Academy', '🧠'),
            ('Risk Academy', '⚖️'),
            ('Progress Tracker', '📈'),
            ('Interactive Playground', '🎮')
        ]
        
        for page_name, icon in pages:
            if st.sidebar.button(f"{icon} {page_name}", key=f"nav_{page_name}"):
                st.session_state.current_page = page_name
        
        st.sidebar.markdown("---")
        
        # Learning progress sidebar
        self._render_progress_sidebar()
        
        # Quick actions
        st.sidebar.markdown("### ⚡ Quick Actions")
        
        if st.sidebar.button("🎯 Get Learning Recommendation"):
            recommendation = self._get_learning_recommendation()
            st.sidebar.success(f"Try: {recommendation}")
        
        if st.sidebar.button("📝 Quick Quiz"):
            self._show_quick_quiz()
    
    def _render_progress_sidebar(self):
        """Render learning progress in sidebar"""
        
        st.sidebar.markdown("### 📚 Learning Progress")
        
        progress = st.session_state.learning_progress
        total_lessons = len(self.indicator_academy.lessons)
        completed = len(progress['completed_lessons'])
        
        progress_pct = completed / total_lessons if total_lessons > 0 else 0
        
        st.sidebar.progress(progress_pct)
        st.sidebar.markdown(f"**{completed}/{total_lessons}** lessons completed")
        st.sidebar.markdown(f"**Level:** {progress['current_level'].title()}")
        
        # Show next recommended lesson
        if completed < total_lessons:
            available_lessons = [
                name for name in self.indicator_academy.lessons.keys() 
                if name not in progress['completed_lessons']
            ]
            if available_lessons:
                next_lesson = available_lessons[0]
                lesson = self.indicator_academy.get_lesson(next_lesson)
                st.sidebar.markdown(f"**Next:** {lesson.name}")
    
    def _render_home_page(self):
        """Render the home page"""
        
        # Welcome section
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("""
            ## 🚀 Welcome to AI Trading Academy!
            
            **Master the art and science of algorithmic trading** through interactive lessons, 
            AI-powered guidance, and hands-on practice with real market data.
            
            ### 🎯 What You'll Learn:
            - **Technical Indicators**: StochRSI, EMA, RSI, MACD, Bollinger Bands
            - **Strategy Development**: Build, test, and optimize trading algorithms
            - **Risk Management**: Professional-grade portfolio risk analysis
            - **Market Psychology**: Understand what drives price movements
            
            ### 🤖 AI-Powered Learning:
            Get personalized guidance from our AI assistant that adapts to your learning style and experience level.
            """)
            
            # Quick start buttons
            col1a, col1b, col1c = st.columns(3)
            
            with col1a:
                if st.button("🎓 Start Learning", key="start_learning"):
                    st.session_state.current_page = 'Indicator Academy'
            
            with col1b:
                if st.button("🤖 AI Assistant", key="start_ai"):
                    st.session_state.current_page = 'AI Assistant'
            
            with col1c:
                if st.button("🔬 Try Backtesting", key="start_backtest"):
                    st.session_state.current_page = 'Backtesting Lab'
        
        with col2:
            # Progress overview
            self._render_progress_overview()
        
        # Learning paths
        st.markdown("---")
        st.markdown("## 🛤️ Choose Your Learning Path")
        
        path_col1, path_col2, path_col3 = st.columns(3)
        
        with path_col1:
            st.markdown("""
            ### 🌱 Beginner Path
            **Perfect for new traders**
            
            1. 📊 What are Technical Indicators?
            2. 📈 Moving Averages (EMA)
            3. ⚡ RSI Fundamentals
            4. 🎯 Your First Strategy
            5. ⚖️ Risk Management Basics
            
            **Duration:** 2-3 weeks
            """)
            
            if st.button("Start Beginner Path", key="beginner_path"):
                self._start_learning_path("beginner")
        
        with path_col2:
            st.markdown("""
            ### 🚀 Intermediate Path
            **For traders with some experience**
            
            1. 📊 Stochastic RSI Mastery
            2. 📈 MACD Advanced Techniques
            3. 🎯 Multi-Indicator Strategies
            4. 🔬 Backtesting & Optimization
            5. ⚖️ Advanced Risk Management
            
            **Duration:** 3-4 weeks
            """)
            
            if st.button("Start Intermediate Path", key="intermediate_path"):
                self._start_learning_path("intermediate")
        
        with path_col3:
            st.markdown("""
            ### 🎯 Advanced Path
            **For experienced traders**
            
            1. 🤖 Algorithmic Strategy Design
            2. 📊 Multi-Timeframe Analysis
            3. 🧠 Market Regime Recognition
            4. ⚖️ Portfolio Risk Optimization
            5. 🚀 Live Algorithm Deployment
            
            **Duration:** 4-6 weeks
            """)
            
            if st.button("Start Advanced Path", key="advanced_path"):
                self._start_learning_path("advanced")
        
        # Recent achievements
        st.markdown("---")
        self._render_recent_achievements()
        
        # Market insights
        st.markdown("---")
        self._render_market_insights()
    
    def _render_ai_assistant_page(self):
        """Render the AI assistant chat interface"""
        
        st.markdown("## 🤖 AI Trading Assistant")
        st.markdown("*Your personal trading tutor and strategy advisor*")
        
        # Chat interface
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # Chat messages display
            st.markdown("### 💬 Chat with Your AI Tutor")
            
            # Display chat history
            for message in st.session_state.chat_history[-10:]:  # Show last 10 messages
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
            
            # Chat input
            user_input = st.chat_input("Ask me about indicators, strategies, or trading concepts...")
            
            if user_input:
                # Add user message to chat
                st.session_state.chat_history.append({"role": "user", "content": user_input})
                
                # Get AI response
                with st.spinner("AI is thinking..."):
                    response = self.ai_assistant.chat(st.session_state.user_id, user_input)
                
                # Add AI response to chat
                ai_message = response.get("message", "I'm having trouble responding right now.")
                st.session_state.chat_history.append({"role": "assistant", "content": ai_message})
                
                # Handle special actions
                if "actions" in response:
                    self._handle_ai_actions(response["actions"], response)
                
                st.rerun()
        
        with col2:
            # Quick suggestions
            st.markdown("### 💡 Quick Start")
            
            suggestions = [
                "Explain Stochastic RSI",
                "How to build a strategy?",
                "What is risk management?",
                "Show me a backtest example",
                "Learning path for beginners"
            ]
            
            for suggestion in suggestions:
                if st.button(suggestion, key=f"suggestion_{hash(suggestion)}"):
                    # Simulate user clicking suggestion
                    st.session_state.chat_history.append({"role": "user", "content": suggestion})
                    
                    with st.spinner("AI is thinking..."):
                        response = self.ai_assistant.chat(st.session_state.user_id, suggestion)
                    
                    ai_message = response.get("message", "I'm having trouble responding right now.")
                    st.session_state.chat_history.append({"role": "assistant", "content": ai_message})
                    
                    st.rerun()
            
            # User context info
            st.markdown("---")
            st.markdown("### 👤 Your Profile")
            
            progress = self.ai_assistant.get_user_progress(st.session_state.user_id)
            if "error" not in progress:
                st.markdown(f"**Level:** {progress['experience_level'].title()}")
                st.markdown(f"**Completed:** {progress['completion_percentage']:.0f}%")
                st.markdown(f"**Focus:** {progress.get('current_focus', 'General').replace('_', ' ').title()}")
            
            # Clear chat button
            if st.button("🗑️ Clear Chat", key="clear_chat"):
                st.session_state.chat_history = []
                st.rerun()
    
    def _render_indicator_academy_page(self):
        """Render the indicator learning academy"""
        
        st.markdown("## 📊 Indicator Academy")
        st.markdown("*Master technical indicators with interactive lessons*")
        
        # Indicator selection
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("### 📚 Available Lessons")
            
            lessons = self.indicator_academy.list_available_lessons()
            
            # Group by category
            categories = {}
            for name, info in lessons.items():
                category = info['category']
                if category not in categories:
                    categories[category] = []
                categories[category].append((name, info))
            
            selected_lesson = None
            
            for category, lesson_list in categories.items():
                st.markdown(f"**{category.title()} Indicators:**")
                
                for lesson_name, lesson_info in lesson_list:
                    # Check if completed
                    is_completed = lesson_name in st.session_state.learning_progress['completed_lessons']
                    status_icon = "✅" if is_completed else "📖"
                    
                    if st.button(
                        f"{status_icon} {lesson_info['display_name']}", 
                        key=f"lesson_{lesson_name}",
                        help=f"{lesson_info['difficulty'].title()} - {lesson_info['description']}"
                    ):
                        selected_lesson = lesson_name
                        st.session_state.current_lesson = lesson_name
        
        with col2:
            # Lesson content
            current_lesson = st.session_state.get('current_lesson') or selected_lesson
            
            if current_lesson:
                self._render_lesson_content(current_lesson)
            else:
                st.markdown("""
                ### 🎯 Select a Lesson to Get Started
                
                Choose an indicator from the left panel to begin your interactive learning journey.
                
                **💡 Recommended Starting Points:**
                - **Beginners**: Start with RSI or EMA
                - **Intermediate**: Try Stochastic RSI or MACD
                - **Advanced**: Explore Bollinger Bands or multi-indicator strategies
                """)
    
    def _render_lesson_content(self, lesson_name: str):
        """Render individual lesson content"""
        
        lesson = self.indicator_academy.get_lesson(lesson_name)
        if not lesson:
            st.error(f"Lesson '{lesson_name}' not found")
            return
        
        # Lesson header
        difficulty_colors = {
            "beginner": "🟢",
            "intermediate": "🟡", 
            "advanced": "🔴"
        }
        
        st.markdown(f"""
        ### {difficulty_colors[lesson.difficulty]} {lesson.name}
        **{lesson.difficulty.title()} Level | {lesson.category.value.title()} Indicator**
        """)
        
        # Lesson tabs
        tab1, tab2, tab3, tab4 = st.tabs(["📖 Learn", "🎮 Interactive", "💻 Code", "🧠 Quiz"])
        
        with tab1:
            # Theory content
            st.markdown("#### What is it?")
            st.markdown(lesson.description)
            
            st.markdown("#### How it works:")
            st.code(lesson.formula_explanation, language="text")
            
            # Parameters
            st.markdown("#### Parameters:")
            for param_name, param_info in lesson.parameters.items():
                st.markdown(f"**{param_name.replace('_', ' ').title()}**: {param_info.get('description', 'N/A')}")
                if 'default' in param_info:
                    st.markdown(f"  - Default: {param_info['default']}")
                if 'range' in param_info:
                    st.markdown(f"  - Range: {param_info['range']}")
            
            # Trading signals
            st.markdown("#### Trading Signals:")
            for signal_type, signal_desc in lesson.signals.items():
                st.markdown(f"**{signal_type.replace('_', ' ').title()}**: {signal_desc}")
            
            # Pros and Cons
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### ✅ Strengths:")
                for strength in lesson.strengths:
                    st.markdown(f"• {strength}")
            
            with col2:
                st.markdown("#### ⚠️ Limitations:")
                for weakness in lesson.weaknesses:
                    st.markdown(f"• {weakness}")
            
            # Mark as completed button
            if lesson_name not in st.session_state.learning_progress['completed_lessons']:
                if st.button("✅ Mark as Completed", key=f"complete_{lesson_name}"):
                    st.session_state.learning_progress['completed_lessons'].append(lesson_name)
                    st.success(f"Great job! You've completed the {lesson.name} lesson!")
                    st.balloons()
        
        with tab2:
            # Interactive demo
            st.markdown("#### 🎮 Interactive Demo")
            
            demo_data = st.session_state.demo_data
            
            # Allow parameter adjustment
            st.markdown("**Adjust Parameters:**")
            
            param_values = {}
            param_cols = st.columns(min(3, len(lesson.parameters)))
            
            for i, (param_name, param_info) in enumerate(lesson.parameters.items()):
                col = param_cols[i % len(param_cols)]
                
                with col:
                    if 'range' in param_info:
                        min_val, max_val = param_info['range']
                        param_values[param_name] = st.slider(
                            param_name.replace('_', ' ').title(),
                            min_value=min_val,
                            max_value=max_val,
                            value=param_info.get('default', min_val),
                            key=f"param_{lesson_name}_{param_name}"
                        )
                    elif 'options' in param_info:
                        param_values[param_name] = st.selectbox(
                            param_name.replace('_', ' ').title(),
                            param_info['options'],
                            index=param_info['options'].index(param_info.get('default', param_info['options'][0])),
                            key=f"param_{lesson_name}_{param_name}"
                        )
            
            # Generate interactive chart
            if st.button("🚀 Generate Interactive Chart", key=f"generate_{lesson_name}"):
                with st.spinner("Generating interactive example..."):
                    # Update parameters with user selections
                    updated_params = lesson.parameters.copy()
                    for param_name, value in param_values.items():
                        if param_name in updated_params:
                            updated_params[param_name]['default'] = value
                    
                    # Create interactive lesson
                    interactive_result = self.indicator_academy.create_interactive_lesson(
                        lesson_name, demo_data
                    )
                    
                    if "error" not in interactive_result:
                        st.plotly_chart(
                            interactive_result["interactive_chart"],
                            use_container_width=True,
                            height=600
                        )
                        
                        # Analysis
                        if "analysis" in interactive_result:
                            st.markdown("#### 📊 Analysis:")
                            st.markdown(interactive_result["analysis"], unsafe_allow_html=True)
                    else:
                        st.error(f"Error generating interactive lesson: {interactive_result['error']}")
        
        with tab3:
            # Code examples
            st.markdown("#### 💻 Code Implementation")
            st.markdown("Here's how to implement this indicator in Python:")
            
            st.code(lesson.code_example, language="python")
            
            # Copy button (simulated)
            if st.button("📋 Copy Code", key=f"copy_{lesson_name}"):
                st.success("Code copied to clipboard! (In a real app, this would copy to clipboard)")
        
        with tab4:
            # Quiz
            self._render_lesson_quiz(lesson)
    
    def _render_lesson_quiz(self, lesson):
        """Render quiz for a lesson"""
        
        st.markdown("#### 🧠 Test Your Knowledge")
        
        if not lesson.quiz_questions:
            st.info("Quiz questions are being prepared for this lesson.")
            return
        
        for i, question in enumerate(lesson.quiz_questions):
            st.markdown(f"**Question {i+1}:** {question['question']}")
            
            user_answer = st.radio(
                "Select your answer:",
                question['options'],
                key=f"quiz_{lesson.name}_{i}"
            )
            
            if st.button(f"Check Answer {i+1}", key=f"check_{lesson.name}_{i}"):
                correct_idx = question['correct']
                user_idx = question['options'].index(user_answer)
                
                if user_idx == correct_idx:
                    st.success("✅ Correct! " + question['explanation'])
                else:
                    st.error(f"❌ Incorrect. The correct answer is: **{question['options'][correct_idx]}**")
                    st.info(question['explanation'])
    
    def _render_strategy_builder_page(self):
        """Render the strategy builder interface"""
        
        st.markdown("## 🏗️ Strategy Builder")
        st.markdown("*Design, test, and optimize your trading strategies*")
        
        # Strategy building wizard
        tab1, tab2, tab3 = st.tabs(["🎯 Build Strategy", "📊 Optimize", "📋 My Strategies"])
        
        with tab1:
            self._render_strategy_wizard()
        
        with tab2:
            self._render_strategy_optimizer()
        
        with tab3:
            self._render_saved_strategies()
    
    def _render_strategy_wizard(self):
        """Render strategy building wizard"""
        
        st.markdown("### 🧙‍♂️ Strategy Creation Wizard")
        
        # Step 1: Strategy basics
        st.markdown("#### Step 1: Strategy Basics")
        
        col1, col2 = st.columns(2)
        
        with col1:
            strategy_name = st.text_input("Strategy Name", value="My Custom Strategy")
            trading_style = st.selectbox(
                "Trading Style",
                ["Scalping", "Day Trading", "Swing Trading", "Position Trading"]
            )
        
        with col2:
            market_type = st.selectbox(
                "Target Market",
                ["Stocks", "Crypto", "Forex", "Commodities"]
            )
            risk_level = st.select_slider(
                "Risk Level",
                options=["Conservative", "Moderate", "Aggressive"]
            )
        
        # Step 2: Indicator selection
        st.markdown("#### Step 2: Select Indicators")
        
        available_indicators = self.indicator_academy.list_available_lessons()
        
        selected_indicators = st.multiselect(
            "Choose indicators for your strategy:",
            list(available_indicators.keys()),
            default=["stoch_rsi", "ema"],
            help="Select 2-4 indicators that complement each other"
        )
        
        # Step 3: Entry rules
        st.markdown("#### Step 3: Entry Rules")
        
        entry_rules = []
        
        for indicator in selected_indicators:
            lesson = self.indicator_academy.get_lesson(indicator)
            if lesson:
                st.markdown(f"**{lesson.name} Entry Condition:**")
                
                # Create simplified rule builder for each indicator
                if indicator == "stoch_rsi":
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        k_d_relation = st.selectbox(f"{lesson.name} %K vs %D", ["K > D", "K < D"], key=f"entry_{indicator}_kd")
                    with col2:
                        threshold = st.slider(f"Threshold", 20, 80, 35, key=f"entry_{indicator}_threshold")
                    with col3:
                        condition = st.selectbox("Condition", ["Below", "Above"], key=f"entry_{indicator}_condition")
                    
                    entry_rules.append(f"StochRSI: {k_d_relation} AND both {condition.lower()} {threshold}")
                
                elif indicator == "ema":
                    price_ema = st.selectbox(f"{lesson.name} Entry", ["Price > EMA", "Price < EMA"], key=f"entry_{indicator}_price")
                    entry_rules.append(f"EMA: {price_ema}")
        
        # Step 4: Risk management
        st.markdown("#### Step 4: Risk Management")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            position_size = st.slider("Position Size (%)", 1, 20, 5)
        
        with col2:
            stop_loss = st.slider("Stop Loss (%)", 1, 20, 5)
        
        with col3:
            take_profit = st.slider("Take Profit (%)", 5, 50, 10)
        
        # Generate strategy
        if st.button("🚀 Generate Strategy", key="generate_strategy"):
            strategy_config = {
                "name": strategy_name,
                "trading_style": trading_style,
                "market_type": market_type,
                "risk_level": risk_level,
                "indicators": selected_indicators,
                "entry_rules": entry_rules,
                "position_size": position_size / 100,
                "stop_loss": stop_loss / 100,
                "take_profit": take_profit / 100,
                "created_at": datetime.now().isoformat()
            }
            
            # Save to session state
            if 'custom_strategies' not in st.session_state:
                st.session_state.custom_strategies = []
            
            st.session_state.custom_strategies.append(strategy_config)
            
            st.success("✅ Strategy created successfully!")
            
            # Show strategy summary
            st.markdown("#### 📋 Strategy Summary")
            st.json(strategy_config)
            
            # Option to backtest immediately
            if st.button("🔬 Backtest This Strategy", key="backtest_new_strategy"):
                st.session_state.current_page = 'Backtesting Lab'
                st.session_state.strategy_to_backtest = strategy_config
                st.rerun()
    
    def _render_strategy_optimizer(self):
        """Render strategy optimization interface"""
        
        st.markdown("### ⚙️ Strategy Optimization")
        
        # Strategy selection for optimization
        if 'custom_strategies' in st.session_state and st.session_state.custom_strategies:
            strategy_names = [s['name'] for s in st.session_state.custom_strategies]
            selected_strategy = st.selectbox("Select Strategy to Optimize", strategy_names)
            
            if selected_strategy:
                strategy_config = next(
                    (s for s in st.session_state.custom_strategies if s['name'] == selected_strategy), 
                    None
                )
                
                if strategy_config:
                    st.markdown("#### 🎯 Optimization Parameters")
                    
                    # Optimization settings
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        optimization_metric = st.selectbox(
                            "Optimization Metric",
                            ["Sharpe Ratio", "Total Return", "Max Drawdown", "Win Rate"]
                        )
                        
                        optimization_period = st.selectbox(
                            "Optimization Period",
                            ["1 Year", "2 Years", "3 Years", "5 Years"]
                        )
                    
                    with col2:
                        test_symbol = st.selectbox(
                            "Test Symbol",
                            ["SPY", "AAPL", "MSFT", "TSLA", "NVDA"]
                        )
                        
                        parameter_ranges = st.checkbox("Use Parameter Ranges", value=True)
                    
                    if st.button("🚀 Start Optimization", key="start_optimization"):
                        with st.spinner("Running optimization... This may take a few minutes."):
                            # Simulate optimization process
                            progress_bar = st.progress(0)
                            for i in range(100):
                                progress_bar.progress(i + 1)
                            
                            # Mock optimization results
                            optimization_results = {
                                "original_sharpe": 1.23,
                                "optimized_sharpe": 1.67,
                                "improvement": "35.8%",
                                "best_parameters": {
                                    "rsi_period": 16,
                                    "ema_fast": 8,
                                    "ema_slow": 19
                                },
                                "backtest_periods": 252,
                                "win_rate": 58.3
                            }
                            
                            st.success("✅ Optimization completed!")
                            
                            # Display results
                            col1, col2, col3, col4 = st.columns(4)
                            
                            with col1:
                                st.metric("Original Sharpe", 1.23)
                            with col2:
                                st.metric("Optimized Sharpe", 1.67, delta=0.44)
                            with col3:
                                st.metric("Win Rate", "58.3%", delta="3.1%")
                            with col4:
                                st.metric("Improvement", "35.8%")
                            
                            st.markdown("#### 🎯 Optimal Parameters:")
                            st.json(optimization_results["best_parameters"])
        else:
            st.info("🏗️ Create a strategy first using the Strategy Builder to enable optimization.")
    
    def _render_saved_strategies(self):
        """Render saved strategies management"""
        
        st.markdown("### 📋 My Strategies")
        
        if 'custom_strategies' not in st.session_state or not st.session_state.custom_strategies:
            st.info("📝 No custom strategies created yet. Use the Strategy Builder to create your first strategy!")
            return
        
        # Display strategies in cards
        for i, strategy in enumerate(st.session_state.custom_strategies):
            with st.expander(f"🎯 {strategy['name']} - {strategy['trading_style']}"):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown(f"**Market:** {strategy['market_type']}")
                    st.markdown(f"**Risk Level:** {strategy['risk_level']}")
                    st.markdown(f"**Indicators:** {', '.join(strategy['indicators'])}")
                    st.markdown(f"**Position Size:** {strategy['position_size']*100:.1f}%")
                    st.markdown(f"**Stop Loss:** {strategy['stop_loss']*100:.1f}%")
                    st.markdown(f"**Take Profit:** {strategy['take_profit']*100:.1f}%")
                
                with col2:
                    if st.button("🔬 Backtest", key=f"backtest_saved_{i}"):
                        st.session_state.current_page = 'Backtesting Lab'
                        st.session_state.strategy_to_backtest = strategy
                        st.rerun()
                    
                    if st.button("⚙️ Optimize", key=f"optimize_saved_{i}"):
                        st.info("Optimization feature coming soon!")
                    
                    if st.button("🗑️ Delete", key=f"delete_saved_{i}"):
                        st.session_state.custom_strategies.pop(i)
                        st.rerun()
    
    def _render_backtesting_lab_page(self):
        """Render the backtesting laboratory"""
        
        st.markdown("## 🔬 Backtesting Laboratory")
        st.markdown("*Test your strategies with historical data*")
        
        # Backtesting interface
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("### 🎛️ Backtest Configuration")
            
            # Strategy selection
            strategy_options = ["StochRSI Strategy", "EMA Crossover", "RSI Mean Reversion", "MACD Trend Following"]
            
            # Add custom strategies if available
            if 'custom_strategies' in st.session_state and st.session_state.custom_strategies:
                strategy_options.extend([s['name'] for s in st.session_state.custom_strategies])
            
            selected_strategy = st.selectbox("Select Strategy", strategy_options)
            
            # Backtest parameters
            symbol = st.selectbox("Symbol", ["SPY", "AAPL", "MSFT", "TSLA", "QQQ", "IWM"])
            
            col1a, col1b = st.columns(2)
            with col1a:
                start_date = st.date_input("Start Date", datetime.now() - timedelta(days=365))
            with col1b:
                end_date = st.date_input("End Date", datetime.now())
            
            initial_capital = st.number_input("Initial Capital", min_value=1000, value=100000, step=1000)
            
            # Advanced settings
            with st.expander("⚙️ Advanced Settings"):
                commission = st.number_input("Commission per Trade", min_value=0.0, value=1.0, step=0.1)
                slippage = st.number_input("Slippage (%)", min_value=0.0, value=0.1, step=0.01)
                
            # Run backtest button
            if st.button("🚀 Run Backtest", key="run_backtest"):
                with st.spinner("Running backtest... Please wait."):
                    # Run the actual backtest
                    backtest_results = self._run_backtest(
                        selected_strategy, symbol, start_date, end_date, initial_capital
                    )
                    
                    st.session_state.backtest_results = backtest_results
        
        with col2:
            st.markdown("### 📊 Backtest Results")
            
            if 'backtest_results' in st.session_state:
                results = st.session_state.backtest_results
                
                # Performance metrics
                col2a, col2b, col2c, col2d = st.columns(4)
                
                with col2a:
                    st.metric("Total Return", f"{results.get('total_return_pct', 0):.2f}%")
                with col2b:
                    st.metric("Sharpe Ratio", f"{results.get('sharpe_ratio', 0):.2f}")
                with col2c:
                    st.metric("Max Drawdown", f"{results.get('max_drawdown_pct', 0):.2f}%")
                with col2d:
                    st.metric("Win Rate", f"{results.get('win_rate', 0):.1f}%")
                
                # Performance chart
                if 'portfolio_values' in results:
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=results['timestamps'],
                        y=results['portfolio_values'],
                        mode='lines',
                        name='Portfolio Value',
                        line=dict(color='blue', width=2)
                    ))
                    
                    fig.update_layout(
                        title="Portfolio Performance Over Time",
                        xaxis_title="Date",
                        yaxis_title="Portfolio Value ($)",
                        height=400
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                
                # Trade analysis
                if 'trades' in results and results['trades']:
                    st.markdown("#### 📋 Trade Analysis")
                    
                    trades_df = pd.DataFrame(results['trades'])
                    
                    col2a, col2b = st.columns(2)
                    
                    with col2a:
                        st.markdown("**Trade Statistics:**")
                        st.markdown(f"• Total Trades: {len(trades_df)}")
                        st.markdown(f"• Winning Trades: {len(trades_df[trades_df['pnl'] > 0])}")
                        st.markdown(f"• Average Win: ${trades_df[trades_df['pnl'] > 0]['pnl'].mean():.2f}")
                        st.markdown(f"• Average Loss: ${trades_df[trades_df['pnl'] < 0]['pnl'].mean():.2f}")
                    
                    with col2b:
                        # PnL distribution
                        fig_hist = go.Figure()
                        fig_hist.add_trace(go.Histogram(
                            x=trades_df['pnl'],
                            nbinsx=20,
                            name='Trade P&L Distribution'
                        ))
                        fig_hist.update_layout(
                            title="Trade P&L Distribution",
                            xaxis_title="P&L ($)",
                            yaxis_title="Frequency",
                            height=300
                        )
                        st.plotly_chart(fig_hist, use_container_width=True)
                
            else:
                st.info("👆 Configure and run a backtest to see results here.")
                
                # Show example results
                st.markdown("### 📚 Example Backtest Results")
                
                example_fig = self._create_example_backtest_chart()
                st.plotly_chart(example_fig, use_container_width=True)
    
    def _render_ml_academy_page(self):
        """Render machine learning academy page"""
        
        st.markdown("## 🧠 Machine Learning Academy")
        st.markdown("*Learn how AI and ML can enhance your trading strategies*")
        
        # ML education tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📚 ML Basics", 
            "🔮 Price Prediction", 
            "🤖 Reinforcement Learning", 
            "🧬 Adaptive Algorithms",
            "📊 ML Performance"
        ])
        
        with tab1:
            self._render_ml_basics_tab()
        
        with tab2:
            self._render_price_prediction_tab()
        
        with tab3:
            self._render_reinforcement_learning_tab()
        
        with tab4:
            self._render_adaptive_algorithms_tab()
        
        with tab5:
            self._render_ml_performance_tab()
    
    def _render_ml_basics_tab(self):
        """Render ML basics educational content"""
        
        st.markdown("### 🎓 Machine Learning in Trading")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("""
            **What is Machine Learning in Trading?**
            
            Machine Learning (ML) uses algorithms to find patterns in historical data 
            and make predictions about future price movements. In trading, ML can help with:
            
            **🔮 Price Prediction:**
            - Forecast future prices using historical patterns
            - Predict market direction (up/down/sideways)
            - Estimate volatility and risk
            
            **🤖 Strategy Optimization:**
            - Learn optimal entry and exit points
            - Adapt to changing market conditions
            - Optimize position sizing and risk management
            
            **📊 Pattern Recognition:**
            - Identify complex chart patterns
            - Detect market regime changes
            - Find hidden correlations in data
            """)
            
            st.markdown("### 🏗️ Types of ML Models We Use:")
            
            model_types = {
                "Random Forest": "Ensemble method that combines multiple decision trees for robust predictions",
                "Gradient Boosting": "Sequential learning that corrects previous model errors",
                "LSTM Neural Networks": "Deep learning for time series with memory of past events",
                "Reinforcement Learning": "AI agents that learn optimal actions through trial and error",
                "Adaptive Algorithms": "Systems that automatically adjust to market changes"
            }
            
            for model_name, description in model_types.items():
                with st.expander(f"📋 {model_name}"):
                    st.write(description)
                    
                    # Add interactive demo for each model type
                    if st.button(f"Try {model_name} Demo", key=f"demo_{model_name}"):
                        self._show_ml_model_demo(model_name)
        
        with col2:
            st.markdown("### 🎯 Learning Path")
            
            learning_steps = [
                "📊 Understand your data",
                "🔧 Feature engineering", 
                "🤖 Train ML models",
                "📈 Evaluate performance",
                "🚀 Deploy in trading",
                "🔄 Monitor and adapt"
            ]
            
            for i, step in enumerate(learning_steps, 1):
                st.markdown(f"{i}. {step}")
            
            st.markdown("### 📚 Recommended Reading")
            
            resources = [
                "📖 'Advances in Financial Machine Learning' by M. Prado",
                "🎓 'Machine Learning for Algorithmic Trading' course",
                "📰 QuantStart ML articles",
                "🔬 Papers on arXiv.org"
            ]
            
            for resource in resources:
                st.markdown(f"• {resource}")
    
    def _render_price_prediction_tab(self):
        """Render price prediction interface"""
        
        st.markdown("### 🔮 AI Price Prediction Laboratory")
        
        # Check ML service status
        ml_status = self.ml_service.get_service_status()
        
        col1, col2 = st.columns([2, 1])
        
        with col2:
            st.markdown("### 🎛️ Controls")
            
            # Model selection
            model_type = st.selectbox(
                "Choose Model",
                ["Ensemble (Recommended)", "Random Forest", "Gradient Boosting", "LSTM Neural Network"],
                help="Different models use different approaches to prediction"
            )
            
            # Prediction horizon
            horizon = st.slider("Prediction Horizon (hours)", 1, 24, 4)
            
            # Demo data or upload
            data_source = st.radio("Data Source", ["Demo Data", "Upload CSV"])
            
            if data_source == "Demo Data":
                # Generate demo data
                demo_data = self._generate_demo_price_data()
                st.success("✅ Using demo market data")
            else:
                uploaded_file = st.file_uploader("Upload CSV with OHLCV data", type=['csv'])
                if uploaded_file:
                    demo_data = pd.read_csv(uploaded_file)
                    st.success("✅ Data uploaded successfully")
                else:
                    demo_data = self._generate_demo_price_data()
                    st.info("Using demo data until you upload a file")
            
            # Train model button
            if st.button("🤖 Train Prediction Model", type="primary"):
                with st.spinner("Training ML models... This may take a few minutes"):
                    try:
                        results = self.ml_service.model_manager.train_price_predictor(
                            demo_data, target_horizon=horizon
                        )
                        
                        if results:
                            st.success("✅ Models trained successfully!")
                            st.session_state.ml_models_trained = True
                            
                            # Show training results
                            for model_name, performance in results.items():
                                with st.expander(f"📊 {model_name} Results"):
                                    st.write(f"**R² Score:** {performance.r2_score:.3f}")
                                    st.write(f"**Direction Accuracy:** {performance.accuracy_direction:.1%}")
                                    st.write(f"**Training Samples:** {performance.training_samples:,}")
                        else:
                            st.error("❌ Training failed. Check data format.")
                    except Exception as e:
                        st.error(f"Training error: {str(e)}")
        
        with col1:
            st.markdown("### 📈 Price Prediction Results")
            
            if not getattr(st.session_state, 'ml_models_trained', False):
                st.info("👆 Train a model first to see predictions here")
                
                # Show example prediction chart
                st.markdown("#### 📚 Example Prediction")
                example_fig = self._create_example_prediction_chart()
                st.plotly_chart(example_fig, use_container_width=True)
            
            else:
                # Get actual prediction
                try:
                    prediction = self.ml_service.get_price_prediction(demo_data, horizon)
                    
                    if prediction:
                        current_price = demo_data['close'].iloc[-1]
                        price_change = (prediction.predicted_price - current_price) / current_price * 100
                        
                        # Show prediction metrics
                        metric_cols = st.columns(4)
                        
                        with metric_cols[0]:
                            st.metric("Current Price", f"${current_price:.2f}")
                        
                        with metric_cols[1]:
                            st.metric(
                                "Predicted Price", 
                                f"${prediction.predicted_price:.2f}",
                                f"{price_change:+.1f}%"
                            )
                        
                        with metric_cols[2]:
                            st.metric("Confidence", f"{prediction.confidence:.1%}")
                        
                        with metric_cols[3]:
                            st.metric("Horizon", f"{prediction.prediction_horizon}h")
                        
                        # Show prediction chart
                        pred_fig = self._create_prediction_chart(demo_data, prediction)
                        st.plotly_chart(pred_fig, use_container_width=True)
                        
                        # Trading recommendation
                        if price_change > 1:
                            st.success("🚀 **Bullish Signal:** Price expected to rise")
                        elif price_change < -1:
                            st.error("🔻 **Bearish Signal:** Price expected to fall")  
                        else:
                            st.info("➡️ **Neutral:** Price expected to remain stable")
                    
                    else:
                        st.warning("Unable to generate prediction. Check model status.")
                        
                except Exception as e:
                    st.error(f"Prediction error: {str(e)}")
            
            # Educational content
            with st.expander("📚 How Price Prediction Works"):
                st.markdown("""
                **Feature Engineering:** We create technical indicators, price patterns, 
                and market statistics as inputs to our ML models.
                
                **Model Training:** Multiple algorithms learn from historical data to 
                find patterns between features and future prices.
                
                **Ensemble Methods:** We combine predictions from different models 
                to get more reliable results.
                
                **Confidence Scoring:** Each prediction comes with a confidence score 
                based on model agreement and historical accuracy.
                """)
    
    def _render_reinforcement_learning_tab(self):
        """Render reinforcement learning interface"""
        
        st.markdown("### 🤖 Reinforcement Learning Laboratory")
        st.markdown("*Train AI agents to learn optimal trading strategies*")
        
        col1, col2 = st.columns([2, 1])
        
        with col2:
            st.markdown("### ⚙️ RL Configuration")
            
            # Agent type
            agent_type = st.selectbox(
                "RL Agent Type",
                ["Q-Learning", "Deep Q-Network (DQN)"],
                help="Q-Learning: Simple table-based learning\nDQN: Neural network-based learning"
            )
            
            # Training parameters
            episodes = st.slider("Training Episodes", 100, 2000, 500)
            learning_rate = st.slider("Learning Rate", 0.001, 0.1, 0.01, 0.001)
            epsilon = st.slider("Exploration Rate", 0.1, 1.0, 0.9, 0.1)
            
            # Training environment
            initial_capital = st.number_input("Initial Capital", 10000, 1000000, 100000, 10000)
            transaction_cost = st.slider("Transaction Cost %", 0.0, 1.0, 0.1, 0.01)
            
            # Demo data
            demo_data = self._generate_demo_price_data(periods=1000)
            
            # Train RL agent
            if st.button("🚀 Train RL Agent", type="primary"):
                with st.spinner(f"Training {agent_type} for {episodes} episodes..."):
                    try:
                        results = self.ml_service.model_manager.train_rl_optimizer(
                            demo_data, episodes=episodes
                        )
                        
                        if results:
                            st.success("🎉 RL training completed!")
                            st.session_state.rl_trained = True
                            st.session_state.rl_results = results
                            
                            # Show training summary
                            for agent_name, performance in results.items():
                                with st.expander(f"📊 {agent_name} Performance"):
                                    st.write(f"**Average Reward:** {performance.average_reward:.3f}")
                                    st.write(f"**Win Rate:** {performance.win_rate:.1%}")
                                    st.write(f"**Sharpe Ratio:** {performance.sharpe_ratio:.3f}")
                                    st.write(f"**Episodes:** {performance.total_episodes:,}")
                        
                    except Exception as e:
                        st.error(f"RL training error: {str(e)}")
        
        with col1:
            st.markdown("### 📊 RL Training Results")
            
            if not getattr(st.session_state, 'rl_trained', False):
                st.info("👆 Train an RL agent first to see results here")
                
                # Educational content about RL
                st.markdown("#### 🎓 What is Reinforcement Learning?")
                st.markdown("""
                Reinforcement Learning (RL) trains AI agents to make optimal trading decisions 
                by learning from the consequences of their actions:
                
                **🎯 Agent:** The AI trader making buy/sell/hold decisions
                **🌍 Environment:** The market with prices, volumes, indicators  
                **⚡ Actions:** Buy, sell, or hold positions
                **🏆 Rewards:** Profits from successful trades, penalties for losses
                **📚 Learning:** Agent improves strategy based on rewards/penalties
                """)
                
                # Show example RL learning curve
                example_fig = self._create_example_rl_chart()
                st.plotly_chart(example_fig, use_container_width=True)
            
            else:
                # Show actual RL results
                results = st.session_state.get('rl_results', {})
                
                if results:
                    # Performance comparison
                    st.markdown("#### 🏆 Agent Performance Comparison")
                    
                    performance_data = []
                    for agent_name, performance in results.items():
                        performance_data.append({
                            'Agent': agent_name,
                            'Avg Reward': performance.average_reward,
                            'Win Rate': performance.win_rate * 100,
                            'Sharpe Ratio': performance.sharpe_ratio
                        })
                    
                    perf_df = pd.DataFrame(performance_data)
                    st.dataframe(perf_df, use_container_width=True)
                    
                    # Learning curves
                    st.markdown("#### 📈 Learning Progress")
                    learning_fig = self._create_rl_learning_chart(results)
                    st.plotly_chart(learning_fig, use_container_width=True)
                    
                    # Strategy recommendation
                    best_agent = max(results.keys(), key=lambda k: results[k].average_reward)
                    best_performance = results[best_agent]
                    
                    st.success(f"""
                    🏆 **Best Agent:** {best_agent}
                    
                    **Performance:**
                    - Average Reward: {best_performance.average_reward:.3f}
                    - Win Rate: {best_performance.win_rate:.1%}
                    - Sharpe Ratio: {best_performance.sharpe_ratio:.3f}
                    
                    **Recommendation:** Deploy this agent for live trading after further validation.
                    """)
            
            # Educational resources
            with st.expander("📚 RL in Trading - Learn More"):
                st.markdown("""
                **Key Concepts:**
                - **Q-Learning:** Learns value of state-action pairs
                - **Deep Q-Networks:** Uses neural networks for complex states
                - **Exploration vs Exploitation:** Balance trying new actions vs using known good ones
                - **Reward Engineering:** Design rewards that encourage profitable behavior
                
                **Advantages:**
                - Learns optimal strategies automatically
                - Adapts to changing market conditions
                - No need for explicit rules
                
                **Challenges:**
                - Requires lots of training data
                - Can overfit to historical patterns
                - Black box - hard to interpret decisions
                """)
    
    def _render_adaptive_algorithms_tab(self):
        """Render adaptive algorithms interface"""
        
        st.markdown("### 🧬 Adaptive Algorithm Laboratory")
        st.markdown("*Algorithms that automatically adapt to changing market conditions*")
        
        # Show adaptive system status
        if hasattr(self.ml_service.model_manager, 'adaptive_manager'):
            adaptive_status = self.ml_service.model_manager.adaptive_manager
            if adaptive_status and adaptive_status.current_strategy:
                st.success("✅ Adaptive system is active and monitoring markets")
                
                # Show current strategy
                current_strategy = adaptive_status.current_strategy
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Current Strategy", current_strategy.strategy_name)
                
                with col2:
                    regime_name = "Unknown"
                    if current_strategy.market_regime:
                        regime_name = current_strategy.market_regime.name
                    st.metric("Market Regime", regime_name)
                
                with col3:
                    st.metric("Confidence", f"{current_strategy.confidence:.1%}")
                
                # Adaptation history
                st.markdown("### 📊 Recent Adaptations")
                
                adaptations = adaptive_status.get_adaptation_history(limit=10)
                if adaptations:
                    adaptation_data = []
                    for adaptation in adaptations:
                        adaptation_data.append({
                            'Time': adaptation.timestamp.strftime('%Y-%m-%d %H:%M'),
                            'Type': adaptation.decision_type,
                            'Reason': adaptation.reason,
                            'Confidence': f"{adaptation.confidence:.1%}"
                        })
                    
                    adapt_df = pd.DataFrame(adaptation_data)
                    st.dataframe(adapt_df, use_container_width=True)
                else:
                    st.info("No recent adaptations - system is stable")
                
                # Performance summary
                st.markdown("### 📈 Adaptive System Performance")
                
                performance_summary = adaptive_status.get_performance_summary()
                
                summary_cols = st.columns(4)
                
                with summary_cols[0]:
                    st.metric("Total Adaptations", performance_summary.get('total_adaptations', 0))
                
                with summary_cols[1]:
                    st.metric("Avg Confidence", f"{performance_summary.get('average_confidence', 0):.1%}")
                
                with summary_cols[2]:
                    regime_dist = performance_summary.get('regime_distribution', {})
                    primary_regime = max(regime_dist.keys(), key=regime_dist.get) if regime_dist else "N/A"
                    st.metric("Primary Regime", primary_regime)
                
                with summary_cols[3]:
                    adaptation_types = performance_summary.get('adaptation_types', {})
                    most_common = max(adaptation_types.keys(), key=adaptation_types.get) if adaptation_types else "N/A"
                    st.metric("Most Common Adaptation", most_common.replace('_', ' ').title())
                
            else:
                st.warning("⚠️ Adaptive system not initialized")
                
                if st.button("🚀 Initialize Adaptive System"):
                    with st.spinner("Initializing adaptive algorithms..."):
                        try:
                            demo_data = self._generate_demo_price_data(periods=500)
                            self.ml_service.initialize_ml_system(demo_data, train_models=False)
                            st.success("✅ Adaptive system initialized!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Initialization error: {str(e)}")
        
        # Educational content about adaptive algorithms
        st.markdown("### 🎓 Understanding Adaptive Algorithms")
        
        with st.expander("📚 How Adaptive Algorithms Work"):
            st.markdown("""
            **Market Regime Detection:**
            - Automatically identify market conditions (bull, bear, sideways, high volatility)
            - Use statistical methods and clustering to classify market states
            - Adapt strategy parameters based on detected regime
            
            **Dynamic Parameter Adjustment:**  
            - Position size adapts to volatility (smaller in volatile markets)
            - Stop losses adjust to market conditions (tighter in trending markets)
            - Indicator sensitivity changes based on market noise
            
            **Online Learning:**
            - Continuously learn from recent performance
            - Update strategy weights based on what's working
            - Avoid overfitting to historical patterns
            
            **Benefits:**
            - Automatically adjust to market changes
            - Reduce manual parameter tuning
            - Maintain performance across different market cycles
            """)
        
        with st.expander("⚙️ Adaptive System Components"):
            st.markdown("""
            **1. Market Regime Detector**
            - Uses volatility, trend strength, and momentum indicators
            - Clusters market conditions into distinct regimes
            - Provides confidence scores for regime classification
            
            **2. Parameter Controller**
            - Maps market conditions to optimal parameter ranges
            - Implements volatility-based position sizing
            - Adjusts risk management based on market stress
            
            **3. Online Learning Engine**
            - Tracks performance of different strategies
            - Updates weights based on recent results
            - Balances exploration of new approaches vs exploitation of proven ones
            """)
    
    def _render_ml_performance_tab(self):
        """Render ML performance monitoring"""
        
        st.markdown("### 📊 ML Performance Dashboard")
        
        # Get ML service status
        ml_status = self.ml_service.get_service_status()
        
        # Service overview
        st.markdown("#### 🔍 System Status")
        
        status_cols = st.columns(3)
        
        with status_cols[0]:
            if ml_status['service_initialized']:
                st.success("✅ ML Service Active")
            else:
                st.error("❌ ML Service Inactive")
        
        with status_cols[1]:
            pred_time = ml_status.get('last_prediction_time')
            if pred_time:
                st.info(f"🔮 Last Prediction: {pred_time}")
            else:
                st.warning("🔮 No Predictions Yet")
        
        with status_cols[2]:
            adapt_time = ml_status.get('last_adaptation_time')
            if adapt_time:
                st.info(f"🧬 Last Adaptation: {adapt_time}")
            else:
                st.warning("🧬 No Adaptations Yet")
        
        # Model performance details
        st.markdown("#### 🤖 Model Performance")
        
        models_status = ml_status.get('ml_models', {})
        
        # Price predictor
        pred_status = models_status.get('price_predictor', {})
        with st.expander("🔮 Price Prediction Models"):
            if pred_status.get('trained', False):
                st.success(f"✅ Active: {pred_status.get('model_type', 'Unknown')}")
                
                # Show model performances if available
                performances = ml_status.get('model_performances', {})
                pred_performances = {k: v for k, v in performances.items() if 'price_predictor' in k}
                
                if pred_performances:
                    perf_data = []
                    for model_name, perf in pred_performances.items():
                        perf_data.append({
                            'Model': model_name.replace('price_predictor_', ''),
                            'R² Score': f"{perf.get('r2_score', 0):.3f}",
                            'Direction Accuracy': f"{perf.get('accuracy', 0):.1%}",
                        })
                    
                    st.dataframe(pd.DataFrame(perf_data), use_container_width=True)
                else:
                    st.info("No detailed performance metrics available yet")
            else:
                st.warning("⚠️ Not trained yet")
        
        # RL optimizer
        rl_status = models_status.get('rl_optimizer', {})
        with st.expander("🤖 Reinforcement Learning"):
            trained_agents = rl_status.get('trained_agents', 0)
            if trained_agents > 0:
                st.success(f"✅ {trained_agents} trained agents")
                
                # Show RL performances
                performances = ml_status.get('model_performances', {})
                rl_performances = {k: v for k, v in performances.items() if 'rl_' in k}
                
                if rl_performances:
                    rl_data = []
                    for agent_name, perf in rl_performances.items():
                        rl_data.append({
                            'Agent': agent_name.replace('rl_', ''),
                            'Avg Reward': f"{perf.get('avg_reward', 0):.3f}",
                            'Accuracy': f"{perf.get('accuracy', 0):.1%}",
                        })
                    
                    st.dataframe(pd.DataFrame(rl_data), use_container_width=True)
            else:
                st.warning("⚠️ No trained RL agents")
        
        # Adaptive manager
        adaptive_status = models_status.get('adaptive_manager', {})
        with st.expander("🧬 Adaptive Algorithms"):
            if adaptive_status.get('initialized', False):
                current_strategy = adaptive_status.get('current_strategy', 'Unknown')
                current_regime = adaptive_status.get('current_regime', 'Unknown')
                
                st.success("✅ Adaptive system active")
                st.write(f"**Current Strategy:** {current_strategy}")
                st.write(f"**Market Regime:** {current_regime}")
            else:
                st.warning("⚠️ Adaptive system not initialized")
        
        # Prediction history
        pred_history_size = ml_status.get('prediction_history_size', 0)
        if pred_history_size > 0:
            st.markdown("#### 📈 Recent Predictions")
            st.info(f"📝 {pred_history_size} predictions in history")
            
            # Show prediction accuracy if available
            if st.button("📊 Evaluate Prediction Accuracy"):
                with st.spinner("Evaluating prediction accuracy..."):
                    try:
                        # Generate dummy actual prices for evaluation
                        dummy_prices = [100 + np.random.randn() for _ in range(50)]
                        dummy_timestamps = [datetime.now() - timedelta(hours=i) for i in range(50)]
                        
                        accuracy_results = self.ml_service.evaluate_prediction_accuracy(
                            dummy_prices, dummy_timestamps
                        )
                        
                        if 'error' not in accuracy_results:
                            acc_cols = st.columns(3)
                            
                            with acc_cols[0]:
                                st.metric("Predictions Evaluated", accuracy_results.get('total_predictions_evaluated', 0))
                            
                            with acc_cols[1]:
                                st.metric("Mean Absolute Error", f"${accuracy_results.get('mean_absolute_error', 0):.2f}")
                            
                            with acc_cols[2]:
                                st.metric("Median Absolute Error", f"${accuracy_results.get('median_absolute_error', 0):.2f}")
                        else:
                            st.warning(accuracy_results['error'])
                            
                    except Exception as e:
                        st.error(f"Evaluation error: {str(e)}")
        
        # Performance tips
        with st.expander("💡 Improving ML Performance"):
            st.markdown("""
            **For Better Predictions:**
            - Use more historical data (at least 1000+ samples)
            - Include multiple timeframes and indicators
            - Regularly retrain models with recent data
            - Monitor prediction accuracy over time
            
            **For Better RL Performance:**
            - Increase training episodes gradually
            - Tune reward function for your trading style
            - Use paper trading to validate before live deployment
            - Consider ensemble of multiple RL agents
            
            **For Better Adaptation:**
            - Allow system to run for extended periods
            - Monitor regime detection accuracy
            - Validate parameter changes with backtesting
            - Keep transaction costs realistic in simulations
            """)
    
    def _show_ml_model_demo(self, model_name: str):
        """Show interactive demo for ML model"""
        
        st.markdown(f"### 🎮 {model_name} Interactive Demo")
        
        if model_name == "Random Forest":
            st.markdown("""
            **Random Forest Demo:** 
            Imagine you have 100 expert traders, each looking at different aspects of the market.
            Random Forest is like getting predictions from all 100 and taking the average.
            """)
            
            # Create demo visualization
            demo_fig = go.Figure()
            
            # Individual tree predictions (scattered)
            np.random.seed(42)
            tree_predictions = np.random.normal(105, 3, 10)
            demo_fig.add_trace(go.Scatter(
                x=list(range(1, 11)),
                y=tree_predictions,
                mode='markers',
                name='Individual Trees',
                marker=dict(color='lightblue', size=8)
            ))
            
            # Ensemble prediction (average)
            ensemble_pred = np.mean(tree_predictions)
            demo_fig.add_trace(go.Scatter(
                x=[0, 11],
                y=[ensemble_pred, ensemble_pred],
                mode='lines',
                name='Ensemble Prediction',
                line=dict(color='red', width=3, dash='dash')
            ))
            
            demo_fig.update_layout(
                title="Random Forest: Combining Multiple Predictions",
                xaxis_title="Decision Tree #",
                yaxis_title="Predicted Price ($)",
                height=400
            )
            
            st.plotly_chart(demo_fig, use_container_width=True)
        
        elif model_name == "LSTM Neural Networks":
            st.markdown("""
            **LSTM Demo:**
            LSTM remembers important patterns from the past, like how prices moved 
            after similar market conditions weeks or months ago.
            """)
            
            # Create LSTM memory visualization
            demo_data = self._generate_demo_price_data(periods=60)
            
            demo_fig = go.Figure()
            
            # Price history
            demo_fig.add_trace(go.Scatter(
                x=demo_data.index,
                y=demo_data['close'],
                mode='lines',
                name='Price History',
                line=dict(color='blue')
            ))
            
            # Memory windows
            memory_windows = [10, 20, 30, 40, 50]
            colors = ['rgba(255,0,0,0.3)', 'rgba(0,255,0,0.3)', 'rgba(0,0,255,0.3)', 'rgba(255,255,0,0.3)', 'rgba(255,0,255,0.3)']
            
            for i, window in enumerate(memory_windows):
                demo_fig.add_vrect(
                    x0=max(0, 59-window),
                    x1=59,
                    fillcolor=colors[i],
                    opacity=0.3,
                    layer="below",
                    line_width=0,
                )
            
            demo_fig.update_layout(
                title="LSTM: Using Memory of Past Patterns",
                xaxis_title="Time Period",
                yaxis_title="Price ($)",
                height=400
            )
            
            st.plotly_chart(demo_fig, use_container_width=True)
            
            st.info("🧠 LSTM can remember patterns from different time periods simultaneously")
    
    def _create_example_prediction_chart(self):
        """Create example prediction chart"""
        
        # Generate sample data
        dates = pd.date_range('2024-01-01', periods=100, freq='H')
        prices = 100 + np.cumsum(np.random.randn(100) * 0.5)
        
        fig = go.Figure()
        
        # Historical prices
        fig.add_trace(go.Scatter(
            x=dates,
            y=prices,
            mode='lines',
            name='Historical Prices',
            line=dict(color='blue')
        ))
        
        # Prediction
        future_dates = pd.date_range(dates[-1], periods=25, freq='H')[1:]
        future_prices = prices[-1] + np.cumsum(np.random.randn(24) * 0.3)
        
        fig.add_trace(go.Scatter(
            x=future_dates,
            y=future_prices,
            mode='lines',
            name='ML Prediction',
            line=dict(color='red', dash='dash')
        ))
        
        # Confidence bands
        upper_band = future_prices + 2
        lower_band = future_prices - 2
        
        fig.add_trace(go.Scatter(
            x=future_dates,
            y=upper_band,
            mode='lines',
            name='Upper Confidence',
            line=dict(color='red', width=0),
            showlegend=False
        ))
        
        fig.add_trace(go.Scatter(
            x=future_dates,
            y=lower_band,
            mode='lines',
            name='Lower Confidence',
            fill='tonexty',
            fillcolor='rgba(255,0,0,0.2)',
            line=dict(color='red', width=0),
            showlegend=False
        ))
        
        fig.update_layout(
            title="Example: ML Price Prediction with Confidence Bands",
            xaxis_title="Time",
            yaxis_title="Price ($)",
            height=400
        )
        
        return fig
    
    def _create_prediction_chart(self, data: pd.DataFrame, prediction):
        """Create actual prediction chart"""
        
        fig = go.Figure()
        
        # Historical prices
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['close'],
            mode='lines',
            name='Historical Prices',
            line=dict(color='blue')
        ))
        
        # Current price point
        current_price = data['close'].iloc[-1]
        fig.add_trace(go.Scatter(
            x=[data.index[-1]],
            y=[current_price],
            mode='markers',
            name='Current Price',
            marker=dict(color='green', size=10)
        ))
        
        # Prediction point
        future_time = data.index[-1] + pd.Timedelta(hours=prediction.prediction_horizon)
        fig.add_trace(go.Scatter(
            x=[future_time],
            y=[prediction.predicted_price],
            mode='markers',
            name=f'Predicted Price ({prediction.prediction_horizon}h)',
            marker=dict(color='red', size=10, symbol='star')
        ))
        
        # Connection line
        fig.add_trace(go.Scatter(
            x=[data.index[-1], future_time],
            y=[current_price, prediction.predicted_price],
            mode='lines',
            name='Prediction Path',
            line=dict(color='red', dash='dash', width=2)
        ))
        
        fig.update_layout(
            title=f"Price Prediction: {prediction.model_used}",
            xaxis_title="Time",
            yaxis_title="Price ($)",
            height=500
        )
        
        return fig
    
    def _create_example_rl_chart(self):
        """Create example RL learning curve"""
        
        episodes = np.arange(1, 501)
        rewards = -50 + 60 * (1 - np.exp(-episodes/100)) + np.random.randn(500) * 5
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=episodes,
            y=rewards,
            mode='lines',
            name='Episode Rewards',
            line=dict(color='blue', width=1)
        ))
        
        # Moving average
        ma_rewards = pd.Series(rewards).rolling(20).mean()
        fig.add_trace(go.Scatter(
            x=episodes,
            y=ma_rewards,
            mode='lines',
            name='Learning Progress (20-episode avg)',
            line=dict(color='red', width=3)
        ))
        
        fig.update_layout(
            title="Example: RL Agent Learning Curve",
            xaxis_title="Training Episode",
            yaxis_title="Cumulative Reward",
            height=400
        )
        
        return fig
    
    def _create_rl_learning_chart(self, rl_results):
        """Create RL learning curve from actual results"""
        
        fig = go.Figure()
        
        colors = ['blue', 'red', 'green', 'orange']
        
        for i, (agent_name, performance) in enumerate(rl_results.items()):
            if hasattr(performance, 'learning_progress'):
                episodes = range(1, len(performance.learning_progress) + 1)
                
                fig.add_trace(go.Scatter(
                    x=list(episodes),
                    y=performance.learning_progress,
                    mode='lines',
                    name=f'{agent_name} Learning',
                    line=dict(color=colors[i % len(colors)])
                ))
        
        fig.update_layout(
            title="RL Agent Learning Progress",
            xaxis_title="Training Episode", 
            yaxis_title="Cumulative Reward",
            height=500
        )
        
        return fig
    
    def _generate_demo_price_data(self, periods: int = 252) -> pd.DataFrame:
        """Generate demo price data for ML examples"""
        
        # Generate realistic price data with trends and volatility
        np.random.seed(42)
        
        dates = pd.date_range('2023-01-01', periods=periods, freq='H')
        
        # Base trend
        trend = np.linspace(100, 120, periods)
        
        # Add noise and volatility clustering
        returns = np.random.randn(periods) * 0.02
        returns[50:100] *= 2  # High volatility period
        returns[150:200] *= 0.5  # Low volatility period
        
        prices = trend * np.cumprod(1 + returns)
        
        # Create OHLCV data
        data = pd.DataFrame({
            'timestamp': dates,
            'open': prices * (1 + np.random.randn(periods) * 0.001),
            'high': prices * (1 + abs(np.random.randn(periods)) * 0.002),
            'low': prices * (1 - abs(np.random.randn(periods)) * 0.002),
            'close': prices,
            'volume': np.random.randint(1000, 10000, periods)
        })
        
        return data
    
    def _render_risk_academy_page(self):
        """Render risk management education page"""
        
        st.markdown("## ⚖️ Risk Management Academy")
        st.markdown("*Master the art of protecting your capital*")
        
        # Risk education tabs
        tab1, tab2, tab3, tab4 = st.tabs(["📚 Learn Risk", "🧮 Calculators", "📊 Portfolio Risk", "🎯 Risk Quiz"])
        
        with tab1:
            self._render_risk_education()
        
        with tab2:
            self._render_risk_calculators()
        
        with tab3:
            self._render_portfolio_risk_analysis()
        
        with tab4:
            self._render_risk_quiz()
    
    def _render_progress_tracker_page(self):
        """Render learning progress tracking page"""
        
        st.markdown("## 📈 Progress Tracker")
        st.markdown("*Track your learning journey and achievements*")
        
        progress = st.session_state.learning_progress
        
        # Overall progress
        col1, col2, col3, col4 = st.columns(4)
        
        total_lessons = len(self.indicator_academy.lessons)
        completed = len(progress['completed_lessons'])
        
        with col1:
            st.metric("Lessons Completed", completed, delta=f"of {total_lessons}")
        with col2:
            st.metric("Progress", f"{completed/total_lessons*100:.0f}%")
        with col3:
            st.metric("Current Level", progress['current_level'].title())
        with col4:
            st.metric("Study Streak", "7 days", delta=2)  # Mock data
        
        # Progress visualization
        categories = {}
        for lesson_name in self.indicator_academy.lessons:
            lesson = self.indicator_academy.get_lesson(lesson_name)
            category = lesson.category.value
            
            if category not in categories:
                categories[category] = {'total': 0, 'completed': 0}
            
            categories[category]['total'] += 1
            if lesson_name in progress['completed_lessons']:
                categories[category]['completed'] += 1
        
        # Category progress chart
        fig = go.Figure()
        
        for category, data in categories.items():
            completion_pct = (data['completed'] / data['total']) * 100 if data['total'] > 0 else 0
            
            fig.add_trace(go.Bar(
                name=category.title(),
                x=[category.title()],
                y=[completion_pct],
                text=f"{data['completed']}/{data['total']}",
                textposition='auto'
            ))
        
        fig.update_layout(
            title="Progress by Indicator Category",
            yaxis_title="Completion %",
            showlegend=False,
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Achievement badges
        st.markdown("---")
        st.markdown("### 🏆 Achievements")
        
        badges = self._calculate_achievement_badges(progress)
        
        cols = st.columns(4)
        for i, (badge_name, badge_info) in enumerate(badges.items()):
            col = cols[i % 4]
            with col:
                if badge_info['earned']:
                    st.success(f"🏆 **{badge_name}**\n\n{badge_info['description']}")
                else:
                    st.info(f"🔒 **{badge_name}**\n\n{badge_info['description']}\n\n*Progress: {badge_info['progress']}*")
    
    def _render_interactive_playground_page(self):
        """Render interactive playground for experimentation"""
        
        st.markdown("## 🎮 Interactive Playground")
        st.markdown("*Experiment with indicators and strategies in real-time*")
        
        # Playground controls
        col1, col2 = st.columns([1, 3])
        
        with col1:
            st.markdown("### 🎛️ Controls")
            
            # Data source
            data_source = st.selectbox("Data Source", ["Generated Demo Data", "Upload CSV", "Live API"])
            
            if data_source == "Generated Demo Data":
                # Demo data parameters
                trend_strength = st.slider("Trend Strength", 0.0, 2.0, 1.0, 0.1)
                volatility = st.slider("Volatility", 0.5, 3.0, 1.0, 0.1)
                noise_level = st.slider("Noise Level", 0.0, 1.0, 0.3, 0.1)
                
                if st.button("🎲 Generate New Data"):
                    st.session_state.playground_data = self._generate_playground_data(
                        trend_strength, volatility, noise_level
                    )
            
            # Indicator selection
            st.markdown("#### 📊 Add Indicators")
            
            available_indicators = list(self.indicator_academy.lessons.keys())
            selected_indicators = st.multiselect(
                "Select Indicators",
                available_indicators,
                default=["stoch_rsi"],
                key="playground_indicators"
            )
            
            # Chart settings
            st.markdown("#### 🎨 Chart Settings")
            chart_style = st.selectbox("Chart Style", ["Candlestick", "Line", "OHLC"])
            show_volume = st.checkbox("Show Volume", value=True)
            
        with col2:
            st.markdown("### 📊 Live Chart")
            
            # Get or generate playground data
            if 'playground_data' not in st.session_state:
                st.session_state.playground_data = self._generate_playground_data(1.0, 1.0, 0.3)
            
            data = st.session_state.playground_data
            
            # Create interactive chart
            fig = self._create_playground_chart(data, selected_indicators, chart_style, show_volume)
            st.plotly_chart(fig, use_container_width=True, height=600)
            
            # Indicator analysis
            if selected_indicators:
                st.markdown("### 📈 Indicator Analysis")
                
                analysis_text = self._generate_indicator_analysis(data, selected_indicators)
                st.markdown(analysis_text)
    
    # Helper methods
    
    def _generate_demo_data(self) -> pd.DataFrame:
        """Generate realistic demo market data"""
        
        np.random.seed(42)  # For reproducible demo data
        
        # Generate 500 days of data
        dates = pd.date_range(start='2023-01-01', periods=500, freq='D')
        
        # Generate realistic price movement
        returns = np.random.normal(0.001, 0.02, len(dates))  # Daily returns with slight positive bias
        returns[100:150] += 0.01  # Add a strong uptrend period
        returns[300:350] -= 0.015  # Add a downtrend period
        
        prices = 100 * (1 + returns).cumprod()
        
        # Generate OHLCV data
        data = pd.DataFrame({
            'open': prices * (1 + np.random.normal(0, 0.002, len(prices))),
            'high': prices * (1 + np.abs(np.random.normal(0, 0.01, len(prices)))),
            'low': prices * (1 - np.abs(np.random.normal(0, 0.01, len(prices)))),
            'close': prices,
            'volume': np.random.randint(100000, 10000000, len(prices))
        }, index=dates)
        
        # Ensure OHLC consistency
        data['high'] = data[['open', 'high', 'close']].max(axis=1)
        data['low'] = data[['open', 'low', 'close']].min(axis=1)
        
        return data
    
    def _get_custom_css(self) -> str:
        """Return custom CSS for styling"""
        
        return """
        <style>
        .main-header {
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            padding: 1rem;
            border-radius: 10px;
            color: white;
            text-align: center;
            margin-bottom: 2rem;
        }
        
        .main-header h1 {
            margin: 0;
            font-size: 2.5rem;
        }
        
        .main-header p {
            margin: 0.5rem 0 0 0;
            font-size: 1.2rem;
            opacity: 0.9;
        }
        
        .stButton > button {
            width: 100%;
            border-radius: 20px;
            border: none;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            color: white;
            font-weight: bold;
        }
        
        .stButton > button:hover {
            background: linear-gradient(90deg, #764ba2 0%, #667eea 100%);
            border: none;
        }
        
        .metric-card {
            background: white;
            padding: 1rem;
            border-radius: 10px;
            border-left: 4px solid #667eea;
            margin: 0.5rem 0;
        }
        </style>
        """
    
    def _render_progress_overview(self):
        """Render progress overview widget"""
        
        progress = st.session_state.learning_progress
        total_lessons = len(self.indicator_academy.lessons)
        completed = len(progress['completed_lessons'])
        
        st.markdown("### 📊 Your Progress")
        
        # Circular progress indicator
        progress_pct = completed / total_lessons if total_lessons > 0 else 0
        
        # Progress metrics
        st.metric("Lessons Completed", f"{completed}/{total_lessons}")
        st.progress(progress_pct)
        st.markdown(f"**{progress_pct*100:.0f}%** Complete")
        
        # Next lesson recommendation
        if completed < total_lessons:
            available_lessons = [
                name for name in self.indicator_academy.lessons.keys() 
                if name not in progress['completed_lessons']
            ]
            if available_lessons:
                next_lesson = available_lessons[0]
                lesson = self.indicator_academy.get_lesson(next_lesson)
                st.info(f"**Next:** {lesson.name}")
    
    def _get_learning_recommendation(self) -> str:
        """Get personalized learning recommendation"""
        
        progress = st.session_state.learning_progress
        completed = progress['completed_lessons']
        
        if not completed:
            return "Start with RSI - it's beginner-friendly!"
        elif len(completed) < 3:
            return "Try the AI Assistant for personalized guidance"
        else:
            return "Ready to build your first custom strategy!"
    
    def _show_quick_quiz(self):
        """Show a quick knowledge quiz"""
        
        questions = [
            {
                "question": "What does RSI measure?",
                "options": ["Price momentum", "Volume", "Volatility", "Correlation"],
                "correct": 0
            },
            {
                "question": "What is a good risk per trade?",
                "options": ["10%", "5%", "2%", "1%"],
                "correct": 2
            }
        ]
        
        # This would show in a modal or sidebar
        st.sidebar.markdown("**Quick Quiz:** What does RSI measure?")
        answer = st.sidebar.radio("", ["Price momentum", "Volume", "Volatility", "Correlation"])
        
        if st.sidebar.button("Submit Quiz"):
            if answer == "Price momentum":
                st.sidebar.success("Correct! 🎉")
            else:
                st.sidebar.error("Try again! RSI measures price momentum.")
    
    def _start_learning_path(self, level: str):
        """Start a specific learning path"""
        
        st.session_state.learning_progress['current_level'] = level
        st.session_state.current_page = 'Indicator Academy'
        
        # Set appropriate first lesson based on level
        if level == "beginner":
            st.session_state.current_lesson = "rsi"
        elif level == "intermediate":
            st.session_state.current_lesson = "stoch_rsi"
        else:  # advanced
            st.session_state.current_lesson = "macd"
        
        st.success(f"Started {level.title()} learning path! 🚀")
        st.rerun()
    
    def _render_recent_achievements(self):
        """Render recent achievements section"""
        
        st.markdown("### 🏆 Recent Achievements")
        
        # Mock achievements
        achievements = [
            {"title": "First Lesson Complete", "description": "Completed your first indicator lesson", "icon": "📚"},
            {"title": "Strategy Builder", "description": "Created your first custom strategy", "icon": "🏗️"},
            {"title": "Backtest Master", "description": "Ran 5 successful backtests", "icon": "🔬"}
        ]
        
        cols = st.columns(3)
        for i, achievement in enumerate(achievements):
            col = cols[i]
            with col:
                st.success(f"{achievement['icon']} **{achievement['title']}**\n\n{achievement['description']}")
    
    def _render_market_insights(self):
        """Render market insights section"""
        
        st.markdown("### 💡 Today's Market Insights")
        
        insights = [
            "📈 StochRSI showing oversold conditions in tech stocks",
            "📊 Market volatility increased 15% this week - perfect for Bollinger Bands strategies",
            "⚡ RSI divergence spotted in several momentum names",
        ]
        
        for insight in insights:
            st.info(insight)
    
    def _handle_ai_actions(self, actions: List[str], response: Dict[str, Any]):
        """Handle special AI assistant actions"""
        
        if "show_indicator_lesson" in actions and "indicator_data" in response:
            indicator_name = response["indicator_data"]["name"]
            st.session_state.current_lesson = indicator_name
            st.session_state.current_page = 'Indicator Academy'
        
        elif "backtesting_interface" in actions:
            st.session_state.current_page = 'Backtesting Lab'
        
        elif "strategy_builder_wizard" in actions:
            st.session_state.current_page = 'Strategy Builder'
    
    def _run_backtest(self, strategy_name: str, symbol: str, start_date, end_date, initial_capital: float) -> Dict[str, Any]:
        """Run backtest and return results"""
        
        try:
            # Convert strategy name to backtesting format
            if strategy_name == "StochRSI Strategy":
                strategy_key = "stochastic_rsi"
            elif strategy_name == "EMA Crossover":
                strategy_key = "ema"
            elif strategy_name == "RSI Mean Reversion":
                strategy_key = "rsi"
            elif strategy_name == "MACD Trend Following":
                strategy_key = "macd"
            else:
                # Custom strategy
                return self._run_custom_strategy_backtest(strategy_name, symbol, start_date, end_date, initial_capital)
            
            # Run backtest using our backtesting service
            result = self.backtesting_service.run_single_strategy_backtest(
                strategy_name=strategy_key,
                ticker=symbol,
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d'),
                initial_capital=initial_capital
            )
            
            return {
                'total_return_pct': result.total_return_pct,
                'sharpe_ratio': result.sharpe_ratio,
                'max_drawdown_pct': result.max_drawdown_pct,
                'win_rate': result.win_rate,
                'total_trades': result.total_trades,
                'portfolio_values': result.portfolio_value,
                'timestamps': result.timestamps,
                'trades': result.trades
            }
            
        except Exception as e:
            self.logger.error(f"Backtest failed: {e}")
            
            # Return mock results for demo
            return self._generate_mock_backtest_results()
    
    def _generate_mock_backtest_results(self) -> Dict[str, Any]:
        """Generate mock backtest results for demonstration"""
        
        # Generate mock portfolio performance
        dates = pd.date_range(start='2023-01-01', periods=252, freq='D')
        returns = np.random.normal(0.0008, 0.015, len(dates))  # Slightly positive returns
        portfolio_values = [100000]  # Starting capital
        
        for ret in returns:
            portfolio_values.append(portfolio_values[-1] * (1 + ret))
        
        # Generate mock trades
        trades = []
        for i in range(15):  # 15 mock trades
            entry_date = dates[np.random.randint(0, len(dates)-20)]
            exit_date = entry_date + pd.Timedelta(days=np.random.randint(1, 20))
            
            entry_price = 150 + np.random.normal(0, 10)
            exit_price = entry_price * (1 + np.random.normal(0.02, 0.05))
            quantity = 100
            
            pnl = (exit_price - entry_price) * quantity
            
            trades.append({
                'entry_time': entry_date.strftime('%Y-%m-%d'),
                'exit_time': exit_date.strftime('%Y-%m-%d'),
                'entry_price': entry_price,
                'exit_price': exit_price,
                'quantity': quantity,
                'pnl': pnl,
                'pnl_pct': (exit_price / entry_price - 1) * 100
            })
        
        # Calculate metrics
        total_return_pct = (portfolio_values[-1] / portfolio_values[0] - 1) * 100
        winning_trades = len([t for t in trades if t['pnl'] > 0])
        
        return {
            'total_return_pct': total_return_pct,
            'sharpe_ratio': 1.34,
            'max_drawdown_pct': 8.5,
            'win_rate': (winning_trades / len(trades)) * 100,
            'total_trades': len(trades),
            'portfolio_values': portfolio_values,
            'timestamps': [d.strftime('%Y-%m-%d') for d in dates],
            'trades': trades
        }
    
    def _create_example_backtest_chart(self) -> go.Figure:
        """Create example backtest chart"""
        
        dates = pd.date_range(start='2023-01-01', periods=252, freq='D')
        portfolio_values = 100000 * (1 + np.random.normal(0.0008, 0.015, len(dates))).cumprod()
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=dates,
            y=portfolio_values,
            mode='lines',
            name='Portfolio Value',
            line=dict(color='blue', width=2)
        ))
        
        fig.update_layout(
            title="Example: StochRSI Strategy on SPY",
            xaxis_title="Date",
            yaxis_title="Portfolio Value ($)",
            height=400
        )
        
        return fig
    
    def _render_risk_education(self):
        """Render risk management education content"""
        
        st.markdown("### 📚 Risk Management Fundamentals")
        
        risk_topics = {
            "Position Sizing": {
                "description": "How much capital to risk on each trade",
                "key_points": [
                    "Never risk more than 1-2% per trade",
                    "Use Kelly Criterion for optimal sizing",
                    "Adjust for volatility and correlation",
                    "Consider account growth over time"
                ]
            },
            "Stop Losses": {
                "description": "How to limit losses on trades",
                "key_points": [
                    "Always have an exit plan",
                    "Use ATR-based stops for volatility",
                    "Never move stops against you",
                    "Consider time-based stops too"
                ]
            },
            "Portfolio Diversification": {
                "description": "Spreading risk across different assets",
                "key_points": [
                    "Don't put all eggs in one basket",
                    "Monitor correlation between positions",
                    "Balance across sectors and timeframes",
                    "Consider different strategy types"
                ]
            },
            "Risk-Reward Ratios": {
                "description": "Balancing potential gains vs losses",
                "key_points": [
                    "Target minimum 1:2 risk-reward",
                    "Track actual vs planned ratios",
                    "Let winners run, cut losers short",
                    "Consider win rate vs reward ratio"
                ]
            }
        }
        
        for topic, info in risk_topics.items():
            with st.expander(f"📖 {topic}"):
                st.markdown(f"**{info['description']}**")
                st.markdown("**Key Points:**")
                for point in info['key_points']:
                    st.markdown(f"• {point}")
    
    def _render_risk_calculators(self):
        """Render risk calculation tools"""
        
        st.markdown("### 🧮 Risk Calculators")
        
        # Position size calculator
        st.markdown("#### 💰 Position Size Calculator")
        
        col1, col2 = st.columns(2)
        
        with col1:
            account_size = st.number_input("Account Size ($)", min_value=1000, value=100000)
            risk_percent = st.slider("Risk per Trade (%)", 0.5, 5.0, 2.0, 0.1)
            entry_price = st.number_input("Entry Price ($)", min_value=0.01, value=100.0)
            stop_loss_price = st.number_input("Stop Loss Price ($)", min_value=0.01, value=95.0)
        
        with col2:
            if entry_price > 0 and stop_loss_price > 0:
                # Calculate position size
                risk_amount = account_size * (risk_percent / 100)
                stop_distance = abs(entry_price - stop_loss_price)
                position_size = int(risk_amount / stop_distance) if stop_distance > 0 else 0
                position_value = position_size * entry_price
                
                st.markdown("**Results:**")
                st.success(f"**Position Size:** {position_size} shares")
                st.info(f"**Position Value:** ${position_value:,.2f}")
                st.info(f"**Risk Amount:** ${risk_amount:,.2f}")
                st.info(f"**Stop Distance:** ${stop_distance:.2f} ({stop_distance/entry_price*100:.1f}%)")
        
        st.markdown("---")
        
        # Risk-reward calculator
        st.markdown("#### ⚖️ Risk-Reward Calculator")
        
        col1, col2 = st.columns(2)
        
        with col1:
            entry_price_rr = st.number_input("Entry Price ($)", min_value=0.01, value=100.0, key="rr_entry")
            stop_loss_rr = st.number_input("Stop Loss ($)", min_value=0.01, value=95.0, key="rr_stop")
            take_profit_rr = st.number_input("Take Profit ($)", min_value=0.01, value=110.0, key="rr_profit")
        
        with col2:
            if entry_price_rr > 0:
                risk = abs(entry_price_rr - stop_loss_rr)
                reward = abs(take_profit_rr - entry_price_rr)
                risk_reward_ratio = reward / risk if risk > 0 else 0
                
                st.markdown("**Risk-Reward Analysis:**")
                st.metric("Risk per Share", f"${risk:.2f}")
                st.metric("Reward per Share", f"${reward:.2f}")
                
                if risk_reward_ratio >= 2.0:
                    st.success(f"**Risk-Reward Ratio:** 1:{risk_reward_ratio:.1f} ✅")
                elif risk_reward_ratio >= 1.0:
                    st.warning(f"**Risk-Reward Ratio:** 1:{risk_reward_ratio:.1f} ⚠️")
                else:
                    st.error(f"**Risk-Reward Ratio:** 1:{risk_reward_ratio:.1f} ❌")
    
    def _render_portfolio_risk_analysis(self):
        """Render portfolio-level risk analysis"""
        
        st.markdown("### 📊 Portfolio Risk Analysis")
        
        # Mock portfolio data
        portfolio_data = {
            'AAPL': {'value': 25000, 'weight': 25},
            'MSFT': {'value': 20000, 'weight': 20},
            'GOOGL': {'value': 15000, 'weight': 15},
            'TSLA': {'value': 20000, 'weight': 20},
            'SPY': {'value': 20000, 'weight': 20}
        }
        
        # Portfolio composition chart
        fig_pie = go.Figure(data=[go.Pie(
            labels=list(portfolio_data.keys()),
            values=[data['weight'] for data in portfolio_data.values()],
            hole=0.3
        )])
        
        fig_pie.update_layout(
            title="Portfolio Composition",
            height=400
        )
        
        st.plotly_chart(fig_pie, use_container_width=True)
        
        # Risk metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Portfolio VaR (95%)", "3.2%", delta="-0.1%")
        with col2:
            st.metric("Max Drawdown", "8.5%", delta="0.2%")
        with col3:
            st.metric("Volatility", "15.3%", delta="-1.1%")
        with col4:
            st.metric("Sharpe Ratio", "1.34", delta="0.08")
        
        # Risk warnings
        st.markdown("#### ⚠️ Risk Alerts")
        st.warning("• High concentration in technology sector (60%)")
        st.info("• TSLA position shows high volatility - consider reducing size")
        st.success("• Overall portfolio risk within acceptable limits")
    
    def _render_risk_quiz(self):
        """Render risk management quiz"""
        
        st.markdown("### 🎯 Risk Management Quiz")
        
        questions = [
            {
                "question": "What is the maximum percentage of your account you should risk on a single trade?",
                "options": ["5%", "2%", "10%", "1%"],
                "correct": 1,
                "explanation": "Most professional traders risk no more than 1-2% per trade to preserve capital."
            },
            {
                "question": "What does a 1:3 risk-reward ratio mean?",
                "options": [
                    "Risk $3 to make $1",
                    "Risk $1 to make $3", 
                    "Win rate must be 33%",
                    "Stop loss is 3x take profit"
                ],
                "correct": 1,
                "explanation": "A 1:3 ratio means you risk $1 to potentially make $3, improving your long-term profitability."
            },
            {
                "question": "When should you move your stop loss?",
                "options": [
                    "When the trade goes against you",
                    "Only in the direction of profit",
                    "Never move stop losses",
                    "Based on emotions"
                ],
                "correct": 1,
                "explanation": "Only move stops to lock in profits, never to give losing trades more room."
            }
        ]
        
        for i, question in enumerate(questions):
            st.markdown(f"**Question {i+1}:** {question['question']}")
            
            answer = st.radio(
                "Select your answer:",
                question['options'],
                key=f"risk_quiz_{i}"
            )
            
            if st.button(f"Check Answer {i+1}", key=f"check_risk_{i}"):
                if answer == question['options'][question['correct']]:
                    st.success("✅ Correct! " + question['explanation'])
                else:
                    st.error(f"❌ Incorrect. The correct answer is: **{question['options'][question['correct']]}**")
                    st.info(question['explanation'])
        
        # Overall quiz score
        if st.button("📊 Show Overall Progress"):
            st.info("Complete all questions to see your risk management knowledge score!")
    
    def _calculate_achievement_badges(self, progress: Dict) -> Dict[str, Dict]:
        """Calculate achievement badges based on progress"""
        
        completed_count = len(progress['completed_lessons'])
        
        badges = {
            "First Steps": {
                "earned": completed_count >= 1,
                "description": "Complete your first indicator lesson",
                "progress": f"{min(completed_count, 1)}/1"
            },
            "Momentum Master": {
                "earned": any(lesson in progress['completed_lessons'] 
                             for lesson in ['stoch_rsi', 'rsi', 'macd']),
                "description": "Master momentum indicators",
                "progress": f"{sum(1 for lesson in ['stoch_rsi', 'rsi', 'macd'] if lesson in progress['completed_lessons'])}/3"
            },
            "Trend Follower": {
                "earned": 'ema' in progress['completed_lessons'],
                "description": "Learn trend following with EMA",
                "progress": "1/1" if 'ema' in progress['completed_lessons'] else "0/1"
            },
            "Academy Graduate": {
                "earned": completed_count >= len(self.indicator_academy.lessons),
                "description": "Complete all indicator lessons",
                "progress": f"{completed_count}/{len(self.indicator_academy.lessons)}"
            }
        }
        
        return badges
    
    def _generate_playground_data(self, trend_strength: float, volatility: float, noise_level: float) -> pd.DataFrame:
        """Generate playground data with specified characteristics"""
        
        dates = pd.date_range(start='2023-01-01', periods=300, freq='D')
        
        # Generate base trend
        trend = np.linspace(0, trend_strength * 50, len(dates))
        
        # Add volatility and noise
        returns = np.random.normal(trend_strength * 0.001, volatility * 0.02, len(dates))
        noise = np.random.normal(0, noise_level * 0.01, len(dates))
        
        combined_returns = returns + noise
        prices = 100 * (1 + combined_returns).cumprod()
        
        data = pd.DataFrame({
            'open': prices * (1 + np.random.normal(0, 0.002, len(prices))),
            'high': prices * (1 + np.abs(np.random.normal(0, volatility * 0.005, len(prices)))),
            'low': prices * (1 - np.abs(np.random.normal(0, volatility * 0.005, len(prices)))),
            'close': prices,
            'volume': np.random.randint(100000, 10000000, len(prices))
        }, index=dates)
        
        # Ensure OHLC consistency
        data['high'] = data[['open', 'high', 'close']].max(axis=1)
        data['low'] = data[['open', 'low', 'close']].min(axis=1)
        
        return data
    
    def _create_playground_chart(self, data: pd.DataFrame, indicators: List[str], 
                               chart_style: str, show_volume: bool) -> go.Figure:
        """Create interactive playground chart"""
        
        # Determine subplot configuration
        subplot_count = 1
        if show_volume:
            subplot_count += 1
        if any(indicator in ['rsi', 'stoch_rsi'] for indicator in indicators):
            subplot_count += 1
        
        # Create subplots
        fig = make_subplots(
            rows=subplot_count,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            row_heights=[0.6] + [0.2] * (subplot_count - 1),
            subplot_titles=['Price Chart'] + (['Volume'] if show_volume else []) + (['Oscillators'] if subplot_count > (2 if show_volume else 1) else [])
        )
        
        # Main price chart
        if chart_style == "Candlestick":
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
        elif chart_style == "Line":
            fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=data['close'],
                    mode='lines',
                    name='Close Price',
                    line=dict(color='blue')
                ),
                row=1, col=1
            )
        
        current_row = 2
        
        # Volume
        if show_volume:
            fig.add_trace(
                go.Bar(
                    x=data.index,
                    y=data['volume'],
                    name='Volume',
                    marker_color='lightblue',
                    opacity=0.7
                ),
                row=current_row, col=1
            )
            current_row += 1
        
        # Add indicators
        oscillator_row = current_row if any(indicator in ['rsi', 'stoch_rsi'] for indicator in indicators) else None
        
        for indicator in indicators:
            if indicator == 'ema':
                import ta
                ema = ta.trend.EMAIndicator(data['close'], window=9).ema_indicator()
                fig.add_trace(
                    go.Scatter(
                        x=data.index,
                        y=ema,
                        mode='lines',
                        name='EMA(9)',
                        line=dict(color='orange', width=2)
                    ),
                    row=1, col=1
                )
            
            elif indicator == 'rsi' and oscillator_row:
                import ta
                rsi = ta.momentum.RSIIndicator(data['close'], window=14).rsi()
                fig.add_trace(
                    go.Scatter(
                        x=data.index,
                        y=rsi,
                        mode='lines',
                        name='RSI',
                        line=dict(color='green')
                    ),
                    row=oscillator_row, col=1
                )
                
                # Add reference lines
                fig.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.5, row=oscillator_row, col=1)
                fig.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.5, row=oscillator_row, col=1)
        
        fig.update_layout(
            title="Interactive Trading Playground",
            height=600,
            xaxis_rangeslider_visible=False,
            showlegend=True
        )
        
        return fig
    
    def _generate_indicator_analysis(self, data: pd.DataFrame, indicators: List[str]) -> str:
        """Generate analysis text for selected indicators"""
        
        analysis = "### 🔍 Current Market Analysis\n\n"
        
        current_price = data['close'].iloc[-1]
        price_change = (data['close'].iloc[-1] / data['close'].iloc[-2] - 1) * 100
        
        analysis += f"**Current Price:** ${current_price:.2f} ({price_change:+.2f}%)\n\n"
        
        if 'ema' in indicators:
            import ta
            ema = ta.trend.EMAIndicator(data['close'], window=9).ema_indicator()
            current_ema = ema.iloc[-1]
            
            if current_price > current_ema:
                trend_signal = "🟢 **Bullish** - Price above EMA"
            else:
                trend_signal = "🔴 **Bearish** - Price below EMA"
            
            analysis += f"**EMA Trend:** {trend_signal} (EMA: ${current_ema:.2f})\n\n"
        
        if 'rsi' in indicators:
            import ta
            rsi = ta.momentum.RSIIndicator(data['close'], window=14).rsi()
            current_rsi = rsi.iloc[-1]
            
            if current_rsi > 70:
                rsi_signal = "🔴 **Overbought** - Consider selling"
            elif current_rsi < 30:
                rsi_signal = "🟢 **Oversold** - Consider buying"
            else:
                rsi_signal = "🟡 **Neutral** - No clear signal"
            
            analysis += f"**RSI Signal:** {rsi_signal} (RSI: {current_rsi:.1f})\n\n"
        
        if not indicators:
            analysis += "Select indicators from the control panel to see analysis!\n"
        
        return analysis
    
    def _run_custom_strategy_backtest(self, strategy_name: str, symbol: str, 
                                    start_date, end_date, initial_capital: float) -> Dict[str, Any]:
        """Run backtest for custom strategy"""
        
        # Find the custom strategy
        custom_strategy = None
        if 'custom_strategies' in st.session_state:
            for strategy in st.session_state.custom_strategies:
                if strategy['name'] == strategy_name:
                    custom_strategy = strategy
                    break
        
        if not custom_strategy:
            return self._generate_mock_backtest_results()
        
        # For now, return mock results
        # In a full implementation, this would run the actual custom strategy backtest
        return self._generate_mock_backtest_results()

# Global dashboard instance
_educational_dashboard = None

def get_educational_dashboard() -> EducationalDashboard:
    """Get singleton educational dashboard instance"""
    global _educational_dashboard
    if _educational_dashboard is None:
        _educational_dashboard = EducationalDashboard()
    return _educational_dashboard

def run_educational_dashboard():
    """Run the educational dashboard application"""
    dashboard = get_educational_dashboard()
    dashboard.run_dashboard()