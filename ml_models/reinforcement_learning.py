#!/usr/bin/env python3
"""
AI Trading Academy - Reinforcement Learning for Strategy Optimization
===================================================================

Advanced reinforcement learning implementation for adaptive trading strategies:
- Q-Learning for discrete action spaces
- Deep Q-Network (DQN) for complex state spaces  
- Policy Gradient methods for continuous actions
- Multi-agent environments for strategy competition

Educational focus: Learn how AI agents can learn optimal trading policies
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, Union
import warnings
from dataclasses import dataclass
from datetime import datetime
import logging
import random
from collections import deque
import json

# Try to import deep learning libraries
try:
    import tensorflow as tf
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import Dense, Dropout
    from tensorflow.keras.optimizers import Adam
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False
    warnings.warn("TensorFlow not available. Deep RL models will be disabled.")

warnings.filterwarnings('ignore', category=FutureWarning)

@dataclass
class TradingAction:
    """Represents a trading action"""
    action_type: str  # 'buy', 'sell', 'hold'
    position_size: float  # 0.0 to 1.0 (percentage of capital)
    confidence: float
    timestamp: datetime
    reasoning: str = ""

@dataclass
class MarketState:
    """Represents the current market state"""
    price: float
    volume: float
    technical_indicators: Dict[str, float]
    position: float  # Current position (-1 to 1, negative = short)
    cash: float
    portfolio_value: float
    market_features: List[float]  # Normalized features for neural networks
    timestamp: datetime

@dataclass
class TradeResult:
    """Result of a trading action"""
    action: TradingAction
    initial_state: MarketState
    final_state: MarketState
    reward: float
    profit_loss: float
    was_successful: bool

@dataclass
class RLAgentPerformance:
    """Performance metrics for RL agent"""
    agent_name: str
    total_episodes: int
    total_reward: float
    average_reward: float
    win_rate: float
    sharpe_ratio: float
    max_drawdown: float
    learning_progress: List[float]  # Rewards over time
    strategy_evolution: Dict[str, Any]  # How strategy changed over time

class TradingEnvironment:
    """Trading environment for reinforcement learning"""
    
    def __init__(self, data: pd.DataFrame, initial_capital: float = 100000, 
                 transaction_cost: float = 0.001, max_position: float = 1.0):
        
        self.data = data.reset_index(drop=True)
        self.initial_capital = initial_capital
        self.transaction_cost = transaction_cost
        self.max_position = max_position
        
        # Current state
        self.current_step = 0
        self.cash = initial_capital
        self.position = 0.0  # -1 to 1 (short to long)
        self.portfolio_value = initial_capital
        
        # History tracking
        self.trade_history = []
        self.portfolio_history = []
        self.action_history = []
        
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Precompute technical indicators
        self._prepare_features()
    
    def _prepare_features(self):
        """Prepare technical indicators and features"""
        
        # Basic price features
        self.data['returns'] = self.data['close'].pct_change()
        self.data['volatility'] = self.data['returns'].rolling(10).std()
        
        # Moving averages
        self.data['sma_5'] = self.data['close'].rolling(5).mean()
        self.data['sma_20'] = self.data['close'].rolling(20).mean()
        self.data['ema_12'] = self.data['close'].ewm(span=12).mean()
        
        # RSI
        delta = self.data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        self.data['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        ema_26 = self.data['close'].ewm(span=26).mean()
        self.data['macd'] = self.data['ema_12'] - ema_26
        self.data['macd_signal'] = self.data['macd'].ewm(span=9).mean()
        
        # Normalize features for neural networks
        feature_cols = ['returns', 'volatility', 'rsi', 'macd']
        self.feature_cols = feature_cols
        
        for col in feature_cols:
            self.data[f'{col}_norm'] = (self.data[col] - self.data[col].mean()) / self.data[col].std()
        
        # Fill NaN values
        self.data = self.data.fillna(method='bfill').fillna(0)
    
    def reset(self) -> MarketState:
        """Reset environment to initial state"""
        
        self.current_step = 30  # Start after indicators are computed
        self.cash = self.initial_capital
        self.position = 0.0
        self.portfolio_value = self.initial_capital
        
        self.trade_history = []
        self.portfolio_history = []
        self.action_history = []
        
        return self._get_current_state()
    
    def _get_current_state(self) -> MarketState:
        """Get current market state"""
        
        if self.current_step >= len(self.data):
            raise ValueError("Environment episode ended")
        
        row = self.data.iloc[self.current_step]
        
        # Technical indicators
        indicators = {
            'rsi': row['rsi'],
            'macd': row['macd'],
            'macd_signal': row['macd_signal'],
            'sma_5': row['sma_5'],
            'sma_20': row['sma_20'],
            'ema_12': row['ema_12'],
            'volatility': row['volatility']
        }
        
        # Normalized features for neural networks
        market_features = [
            row[f'{col}_norm'] for col in self.feature_cols
        ] + [
            self.position,  # Current position
            self.cash / self.initial_capital,  # Cash ratio
            self.portfolio_value / self.initial_capital  # Portfolio ratio
        ]
        
        return MarketState(
            price=row['close'],
            volume=row['volume'],
            technical_indicators=indicators,
            position=self.position,
            cash=self.cash,
            portfolio_value=self.portfolio_value,
            market_features=market_features,
            timestamp=row.get('timestamp', datetime.now())
        )
    
    def step(self, action: TradingAction) -> Tuple[MarketState, float, bool]:
        """Execute trading action and return new state, reward, done"""
        
        if self.current_step >= len(self.data) - 1:
            return self._get_current_state(), 0, True
        
        initial_state = self._get_current_state()
        
        # Execute action
        reward = self._execute_action(action, initial_state)
        
        # Move to next time step
        self.current_step += 1
        
        # Get new state
        new_state = self._get_current_state()
        
        # Check if episode is done
        done = (self.current_step >= len(self.data) - 1) or (self.portfolio_value <= self.initial_capital * 0.1)
        
        # Track history
        self.action_history.append(action)
        self.portfolio_history.append(self.portfolio_value)
        
        return new_state, reward, done
    
    def _execute_action(self, action: TradingAction, state: MarketState) -> float:
        """Execute trading action and calculate reward"""
        
        current_price = state.price
        initial_portfolio_value = self.portfolio_value
        
        # Calculate position change
        target_position = 0
        if action.action_type == 'buy':
            target_position = action.position_size
        elif action.action_type == 'sell':
            target_position = -action.position_size
        # hold keeps current position
        
        # Clamp position to allowed range
        target_position = np.clip(target_position, -self.max_position, self.max_position)
        
        # Calculate position change
        position_change = target_position - self.position
        
        # Execute trade if there's a position change
        if abs(position_change) > 0.01:  # Minimum trade size
            trade_value = position_change * self.initial_capital
            transaction_cost = abs(trade_value) * self.transaction_cost
            
            # Update cash and position
            self.cash -= trade_value + transaction_cost
            self.position = target_position
            
            # Track trade
            self.trade_history.append({
                'timestamp': state.timestamp,
                'action': action.action_type,
                'position_change': position_change,
                'price': current_price,
                'cost': transaction_cost
            })
        
        # Update portfolio value
        position_value = self.position * self.initial_capital * current_price / self.data.iloc[0]['close']
        self.portfolio_value = self.cash + position_value
        
        # Calculate reward
        reward = self._calculate_reward(initial_portfolio_value, self.portfolio_value, action, state)
        
        return reward
    
    def _calculate_reward(self, initial_value: float, final_value: float, 
                         action: TradingAction, state: MarketState) -> float:
        """Calculate reward for the action"""
        
        # Portfolio return
        portfolio_return = (final_value - initial_value) / initial_value
        
        # Base reward is portfolio return
        reward = portfolio_return * 100  # Scale up
        
        # Penalty for excessive trading (encourages holding)
        if action.action_type != 'hold':
            reward -= 0.1
        
        # Bonus for high confidence correct predictions
        if action.action_type == 'buy' and portfolio_return > 0:
            reward += action.confidence * 0.5
        elif action.action_type == 'sell' and portfolio_return > 0:
            reward += action.confidence * 0.5
        
        # Penalty for wrong direction
        if action.action_type == 'buy' and portfolio_return < -0.001:
            reward -= 1.0
        elif action.action_type == 'sell' and portfolio_return < -0.001:
            reward -= 1.0
        
        return reward
    
    def get_performance_metrics(self) -> Dict[str, float]:
        """Calculate performance metrics for the episode"""
        
        if len(self.portfolio_history) < 2:
            return {}
        
        returns = np.array(self.portfolio_history[1:]) / np.array(self.portfolio_history[:-1]) - 1
        
        total_return = (self.portfolio_value - self.initial_capital) / self.initial_capital
        sharpe_ratio = np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0
        
        # Drawdown calculation
        peak = self.initial_capital
        max_drawdown = 0
        for value in self.portfolio_history:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak
            max_drawdown = max(max_drawdown, drawdown)
        
        # Win rate
        profitable_trades = sum(1 for trade in self.trade_history 
                               if 'profit' in trade and trade['profit'] > 0)
        total_trades = len(self.trade_history)
        win_rate = profitable_trades / total_trades if total_trades > 0 else 0
        
        return {
            'total_return': total_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'total_trades': total_trades,
            'final_portfolio_value': self.portfolio_value
        }

class QLearningAgent:
    """Q-Learning agent for discrete trading actions"""
    
    def __init__(self, state_size: int = 10, action_size: int = 3, 
                 learning_rate: float = 0.1, discount_factor: float = 0.95,
                 epsilon: float = 1.0, epsilon_decay: float = 0.995, epsilon_min: float = 0.01):
        
        self.state_size = state_size
        self.action_size = action_size  # hold, buy, sell
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        
        # Exploration parameters
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.epsilon_min = epsilon_min
        
        # Q-table (simplified state space)
        self.q_table = np.zeros((1000, action_size))  # Discretized state space
        
        # Performance tracking
        self.episode_rewards = []
        self.episode_count = 0
        
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def _discretize_state(self, state: MarketState) -> int:
        """Convert continuous state to discrete state index"""
        
        # Simple discretization based on key indicators
        rsi = state.technical_indicators.get('rsi', 50)
        macd = state.technical_indicators.get('macd', 0)
        position = state.position
        
        # Discretize each feature
        rsi_bucket = min(9, max(0, int(rsi / 10)))  # 0-9
        macd_bucket = min(4, max(0, int((macd + 2) / 1)))  # 0-4
        position_bucket = min(2, max(0, int((position + 1) / 1)))  # 0-2
        
        # Combine into single state index
        state_index = rsi_bucket * 15 + macd_bucket * 3 + position_bucket
        
        return min(state_index, len(self.q_table) - 1)
    
    def choose_action(self, state: MarketState) -> TradingAction:
        """Choose action using epsilon-greedy policy"""
        
        state_index = self._discretize_state(state)
        
        # Epsilon-greedy action selection
        if np.random.random() < self.epsilon:
            action_index = np.random.randint(self.action_size)
        else:
            action_index = np.argmax(self.q_table[state_index])
        
        # Convert action index to TradingAction
        action_types = ['hold', 'buy', 'sell']
        action_type = action_types[action_index]
        
        position_size = 0.5 if action_type in ['buy', 'sell'] else 0.0
        confidence = 1 - self.epsilon  # Higher confidence when exploiting
        
        return TradingAction(
            action_type=action_type,
            position_size=position_size,
            confidence=confidence,
            timestamp=datetime.now(),
            reasoning=f"Q-Learning action (ε={self.epsilon:.3f})"
        )
    
    def learn(self, state: MarketState, action: TradingAction, reward: float, 
              next_state: MarketState, done: bool):
        """Update Q-table based on experience"""
        
        state_index = self._discretize_state(state)
        next_state_index = self._discretize_state(next_state)
        
        # Convert action to index
        action_types = ['hold', 'buy', 'sell']
        action_index = action_types.index(action.action_type)
        
        # Q-learning update
        current_q = self.q_table[state_index, action_index]
        
        if done:
            target_q = reward
        else:
            next_max_q = np.max(self.q_table[next_state_index])
            target_q = reward + self.discount_factor * next_max_q
        
        # Update Q-value
        self.q_table[state_index, action_index] += self.learning_rate * (target_q - current_q)
        
        # Decay epsilon
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
    
    def train(self, environment: TradingEnvironment, episodes: int = 1000) -> RLAgentPerformance:
        """Train the Q-Learning agent"""
        
        self.logger.info(f"Starting Q-Learning training for {episodes} episodes...")
        
        episode_rewards = []
        episode_returns = []
        
        for episode in range(episodes):
            state = environment.reset()
            total_reward = 0
            step_count = 0
            
            while True:
                # Choose and execute action
                action = self.choose_action(state)
                next_state, reward, done = environment.step(action)
                
                # Learn from experience
                self.learn(state, action, reward, next_state, done)
                
                total_reward += reward
                state = next_state
                step_count += 1
                
                if done:
                    break
            
            episode_rewards.append(total_reward)
            
            # Calculate episode return
            performance = environment.get_performance_metrics()
            episode_return = performance.get('total_return', 0)
            episode_returns.append(episode_return)
            
            # Log progress
            if (episode + 1) % 100 == 0:
                avg_reward = np.mean(episode_rewards[-100:])
                avg_return = np.mean(episode_returns[-100:])
                self.logger.info(f"Episode {episode + 1}: Avg Reward = {avg_reward:.3f}, Avg Return = {avg_return:.3f}, ε = {self.epsilon:.3f}")
        
        self.episode_rewards = episode_rewards
        self.episode_count = episodes
        
        # Calculate final performance
        final_performance = environment.get_performance_metrics()
        
        performance = RLAgentPerformance(
            agent_name="Q-Learning",
            total_episodes=episodes,
            total_reward=sum(episode_rewards),
            average_reward=np.mean(episode_rewards),
            win_rate=final_performance.get('win_rate', 0),
            sharpe_ratio=final_performance.get('sharpe_ratio', 0),
            max_drawdown=final_performance.get('max_drawdown', 0),
            learning_progress=episode_rewards,
            strategy_evolution={'epsilon_decay': self.epsilon_decay, 'final_epsilon': self.epsilon}
        )
        
        self.logger.info(f"Q-Learning training completed. Final performance: {performance.average_reward:.3f} avg reward")
        
        return performance

if TENSORFLOW_AVAILABLE:
    class DQNAgent:
        """Deep Q-Network agent for complex state spaces"""
        
        def __init__(self, state_size: int = 10, action_size: int = 3,
                     learning_rate: float = 0.001, discount_factor: float = 0.95,
                     epsilon: float = 1.0, epsilon_decay: float = 0.995, epsilon_min: float = 0.01,
                     memory_size: int = 10000, batch_size: int = 32):
            
            self.state_size = state_size
            self.action_size = action_size
            self.learning_rate = learning_rate
            self.discount_factor = discount_factor
            
            # Exploration parameters
            self.epsilon = epsilon
            self.epsilon_decay = epsilon_decay
            self.epsilon_min = epsilon_min
            
            # Experience replay
            self.memory = deque(maxlen=memory_size)
            self.batch_size = batch_size
            
            # Neural networks
            self.main_network = self._build_model()
            self.target_network = self._build_model()
            self.update_target_network()
            
            # Performance tracking
            self.episode_rewards = []
            self.episode_count = 0
            
            self.logger = logging.getLogger(self.__class__.__name__)
        
        def _build_model(self):
            """Build the neural network model"""
            
            model = Sequential([
                Dense(128, input_dim=self.state_size, activation='relu'),
                Dropout(0.2),
                Dense(64, activation='relu'),
                Dropout(0.2),
                Dense(32, activation='relu'),
                Dense(self.action_size, activation='linear')
            ])
            
            model.compile(optimizer=Adam(learning_rate=self.learning_rate), loss='mse')
            return model
        
        def update_target_network(self):
            """Update target network weights"""
            self.target_network.set_weights(self.main_network.get_weights())
        
        def remember(self, state, action, reward, next_state, done):
            """Store experience in replay memory"""
            self.memory.append((state, action, reward, next_state, done))
        
        def choose_action(self, state: MarketState) -> TradingAction:
            """Choose action using epsilon-greedy policy with neural network"""
            
            state_vector = np.array(state.market_features).reshape(1, -1)
            
            # Ensure state vector has correct size
            if state_vector.shape[1] != self.state_size:
                # Pad or truncate to correct size
                if state_vector.shape[1] < self.state_size:
                    padding = np.zeros((1, self.state_size - state_vector.shape[1]))
                    state_vector = np.hstack([state_vector, padding])
                else:
                    state_vector = state_vector[:, :self.state_size]
            
            # Epsilon-greedy action selection
            if np.random.random() < self.epsilon:
                action_index = np.random.randint(self.action_size)
            else:
                q_values = self.main_network.predict(state_vector, verbose=0)
                action_index = np.argmax(q_values[0])
            
            # Convert action index to TradingAction
            action_types = ['hold', 'buy', 'sell']
            action_type = action_types[action_index]
            
            position_size = 0.5 if action_type in ['buy', 'sell'] else 0.0
            confidence = 1 - self.epsilon
            
            return TradingAction(
                action_type=action_type,
                position_size=position_size,
                confidence=confidence,
                timestamp=datetime.now(),
                reasoning=f"DQN action (ε={self.epsilon:.3f})"
            )
        
        def replay(self):
            """Train the network on a batch of experiences"""
            
            if len(self.memory) < self.batch_size:
                return
            
            # Sample batch
            batch = random.sample(self.memory, self.batch_size)
            
            states = np.array([e[0] for e in batch])
            actions = np.array([e[1] for e in batch])
            rewards = np.array([e[2] for e in batch])
            next_states = np.array([e[3] for e in batch])
            dones = np.array([e[4] for e in batch])
            
            # Current Q-values
            current_q_values = self.main_network.predict(states, verbose=0)
            
            # Next Q-values from target network
            next_q_values = self.target_network.predict(next_states, verbose=0)
            
            # Update Q-values
            for i in range(self.batch_size):
                if dones[i]:
                    current_q_values[i][actions[i]] = rewards[i]
                else:
                    current_q_values[i][actions[i]] = rewards[i] + self.discount_factor * np.max(next_q_values[i])
            
            # Train the network
            self.main_network.fit(states, current_q_values, verbose=0, epochs=1)
            
            # Decay epsilon
            if self.epsilon > self.epsilon_min:
                self.epsilon *= self.epsilon_decay
        
        def train(self, environment: TradingEnvironment, episodes: int = 1000, 
                  update_target_freq: int = 100) -> RLAgentPerformance:
            """Train the DQN agent"""
            
            self.logger.info(f"Starting DQN training for {episodes} episodes...")
            
            episode_rewards = []
            episode_returns = []
            
            for episode in range(episodes):
                state = environment.reset()
                total_reward = 0
                step_count = 0
                
                while True:
                    # Choose and execute action
                    action = self.choose_action(state)
                    next_state, reward, done = environment.step(action)
                    
                    # Store experience
                    state_vector = np.array(state.market_features)
                    if len(state_vector) != self.state_size:
                        # Adjust state vector size
                        if len(state_vector) < self.state_size:
                            state_vector = np.pad(state_vector, (0, self.state_size - len(state_vector)))
                        else:
                            state_vector = state_vector[:self.state_size]
                    
                    next_state_vector = np.array(next_state.market_features)
                    if len(next_state_vector) != self.state_size:
                        # Adjust next state vector size
                        if len(next_state_vector) < self.state_size:
                            next_state_vector = np.pad(next_state_vector, (0, self.state_size - len(next_state_vector)))
                        else:
                            next_state_vector = next_state_vector[:self.state_size]
                    
                    action_types = ['hold', 'buy', 'sell']
                    action_index = action_types.index(action.action_type)
                    
                    self.remember(state_vector, action_index, reward, next_state_vector, done)
                    
                    # Train network
                    self.replay()
                    
                    total_reward += reward
                    state = next_state
                    step_count += 1
                    
                    if done:
                        break
                
                episode_rewards.append(total_reward)
                
                # Update target network periodically
                if (episode + 1) % update_target_freq == 0:
                    self.update_target_network()
                
                # Calculate episode return
                performance = environment.get_performance_metrics()
                episode_return = performance.get('total_return', 0)
                episode_returns.append(episode_return)
                
                # Log progress
                if (episode + 1) % 100 == 0:
                    avg_reward = np.mean(episode_rewards[-100:])
                    avg_return = np.mean(episode_returns[-100:])
                    self.logger.info(f"Episode {episode + 1}: Avg Reward = {avg_reward:.3f}, Avg Return = {avg_return:.3f}, ε = {self.epsilon:.3f}")
            
            self.episode_rewards = episode_rewards
            self.episode_count = episodes
            
            # Calculate final performance
            final_performance = environment.get_performance_metrics()
            
            performance = RLAgentPerformance(
                agent_name="DQN",
                total_episodes=episodes,
                total_reward=sum(episode_rewards),
                average_reward=np.mean(episode_rewards),
                win_rate=final_performance.get('win_rate', 0),
                sharpe_ratio=final_performance.get('sharpe_ratio', 0),
                max_drawdown=final_performance.get('max_drawdown', 0),
                learning_progress=episode_rewards,
                strategy_evolution={'epsilon_decay': self.epsilon_decay, 'final_epsilon': self.epsilon}
            )
            
            self.logger.info(f"DQN training completed. Final performance: {performance.average_reward:.3f} avg reward")
            
            return performance

class AdaptiveStrategyOptimizer:
    """Main class for adaptive strategy optimization using RL"""
    
    def __init__(self, use_deep_learning: bool = True):
        self.use_deep_learning = use_deep_learning and TENSORFLOW_AVAILABLE
        self.agents = {}
        self.trained_agents = {}
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def create_agent(self, agent_type: str, **kwargs) -> Union[QLearningAgent, 'DQNAgent']:
        """Create an RL agent"""
        
        if agent_type.lower() == 'qlearning':
            agent = QLearningAgent(**kwargs)
        elif agent_type.lower() == 'dqn' and TENSORFLOW_AVAILABLE:
            agent = DQNAgent(**kwargs)
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")
        
        self.agents[agent_type] = agent
        return agent
    
    def train_agent(self, agent_type: str, data: pd.DataFrame, 
                   episodes: int = 1000, **env_kwargs) -> RLAgentPerformance:
        """Train an RL agent"""
        
        if agent_type not in self.agents:
            self.create_agent(agent_type)
        
        agent = self.agents[agent_type]
        
        # Create environment
        environment = TradingEnvironment(data, **env_kwargs)
        
        # Train agent
        performance = agent.train(environment, episodes)
        
        # Store trained agent
        self.trained_agents[agent_type] = {
            'agent': agent,
            'performance': performance,
            'data_shape': data.shape,
            'training_episodes': episodes
        }
        
        return performance
    
    def compare_agents(self, data: pd.DataFrame, episodes: int = 500) -> Dict[str, RLAgentPerformance]:
        """Train and compare multiple RL agents"""
        
        agent_types = ['qlearning']
        if TENSORFLOW_AVAILABLE:
            agent_types.append('dqn')
        
        performances = {}
        
        for agent_type in agent_types:
            self.logger.info(f"Training {agent_type} agent...")
            try:
                performance = self.train_agent(agent_type, data, episodes)
                performances[agent_type] = performance
            except Exception as e:
                self.logger.error(f"Failed to train {agent_type}: {e}")
                continue
        
        # Log comparison
        self.logger.info("Agent Comparison Results:")
        for agent_type, performance in performances.items():
            self.logger.info(f"  {agent_type}: Avg Reward = {performance.average_reward:.3f}, "
                           f"Sharpe = {performance.sharpe_ratio:.3f}")
        
        return performances
    
    def get_best_agent(self) -> Tuple[str, Union[QLearningAgent, 'DQNAgent']]:
        """Get the best performing trained agent"""
        
        if not self.trained_agents:
            raise ValueError("No agents have been trained")
        
        best_agent_type = None
        best_performance = float('-inf')
        
        for agent_type, info in self.trained_agents.items():
            performance = info['performance']
            # Use average reward as the primary metric
            if performance.average_reward > best_performance:
                best_performance = performance.average_reward
                best_agent_type = agent_type
        
        return best_agent_type, self.trained_agents[best_agent_type]['agent']
    
    def optimize_trading_strategy(self, data: pd.DataFrame, base_strategy_params: Dict[str, Any],
                                episodes: int = 1000) -> Dict[str, Any]:
        """Use RL to optimize trading strategy parameters"""
        
        self.logger.info("Starting RL-based strategy optimization...")
        
        # Train agents
        performances = self.compare_agents(data, episodes)
        
        # Get best agent
        best_agent_type, best_agent = self.get_best_agent()
        
        # Extract optimized parameters from best agent
        optimized_params = base_strategy_params.copy()
        
        # For Q-Learning, analyze Q-table to extract insights
        if isinstance(best_agent, QLearningAgent):
            # Find most frequent actions in different market conditions
            # This is a simplified approach - in practice you'd want more sophisticated analysis
            optimized_params['rl_insights'] = {
                'preferred_agent': best_agent_type,
                'exploration_rate': best_agent.epsilon,
                'learning_rate': best_agent.learning_rate,
                'avg_reward': performances[best_agent_type].average_reward
            }
        
        if TENSORFLOW_AVAILABLE and hasattr(best_agent, 'main_network'):
            # For DQN, you could analyze network weights or feature importance
            optimized_params['rl_insights']['network_layers'] = len(best_agent.main_network.layers)
        
        self.logger.info(f"Strategy optimization completed using {best_agent_type} agent")
        
        return optimized_params
    
    def save_agents(self, filepath: str):
        """Save trained agents"""
        
        save_data = {}
        for agent_type, info in self.trained_agents.items():
            agent_data = {
                'performance': info['performance'].__dict__,
                'training_info': {
                    'data_shape': info['data_shape'],
                    'training_episodes': info['training_episodes']
                }
            }
            
            # Save agent-specific data
            agent = info['agent']
            if isinstance(agent, QLearningAgent):
                agent_data['q_table'] = agent.q_table.tolist()
                agent_data['epsilon'] = agent.epsilon
            
            save_data[agent_type] = agent_data
        
        with open(filepath, 'w') as f:
            json.dump(save_data, f, default=str, indent=2)
        
        self.logger.info(f"Agents saved to {filepath}")

def create_adaptive_optimizer(use_deep_learning: bool = True) -> AdaptiveStrategyOptimizer:
    """Factory function to create adaptive strategy optimizer"""
    return AdaptiveStrategyOptimizer(use_deep_learning=use_deep_learning)