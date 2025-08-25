#!/usr/bin/env python3
"""
Command-line interface for the trading training system
Quick way to start collaborative learning and backtesting
"""

import os
import sys
import argparse
from datetime import datetime, timedelta
import json

# Add training directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from training_engine import TrainingDatabase, BacktestEngine, CollaborativeLearning

class TrainingCLI:
    def __init__(self):
        self.db = TrainingDatabase()
        self.backtest_engine = BacktestEngine(self.db)
        self.collaborative_learning = CollaborativeLearning(self.db)
        
    def run_quick_backtest(self, symbol='AAPL', strategy='stoch_rsi_ema', days=365):
        """Run a quick backtest with default parameters"""
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        print(f"\n🚀 Running backtest: {strategy} on {symbol}")
        print(f"📅 Period: {start_date} to {end_date}")
        print("-" * 50)
        
        try:
            performance = self.backtest_engine.run_backtest(
                strategy_name=strategy,
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                strategy_params={'rsi_oversold': 20, 'rsi_overbought': 80},
                initial_capital=10000
            )
            
            print(f"📊 RESULTS:")
            print(f"   Total Return: {performance['total_return']:+.2f}%")
            print(f"   Total Trades: {performance['total_trades']}")
            print(f"   Win Rate: {performance['win_rate']:.1f}%")
            print(f"   Avg Trade: {performance['avg_trade_return']:+.2f}%")
            print(f"   Sharpe Ratio: {performance['sharpe_ratio']:.2f}")
            print(f"   Max Drawdown: {performance['max_drawdown']:.2f}%")
            print(f"   Total P&L: ${performance['total_pnl']:+,.2f}")
            
            # Color coding
            if performance['total_return'] > 10:
                print("\n🎉 Excellent performance!")
            elif performance['total_return'] > 0:
                print("\n✅ Profitable strategy")
            else:
                print("\n⚠️  Strategy needs improvement")
                
            return performance
            
        except Exception as e:
            print(f"❌ Backtest failed: {e}")
            return None
    
    def start_collaborative_session(self, symbol='AAPL'):
        """Start an interactive collaborative decision session"""
        print(f"\n🤝 Starting collaborative session for {symbol}")
        print("=" * 50)
        
        # Get market analysis
        try:
            analysis = self.collaborative_learning.analyze_current_market(symbol)
            
            print(f"\n📈 Current Price: ${analysis['current_price']:.2f}")
            print(f"🎯 Trend Strength: {analysis['trend_strength']:.2f}/1.0")
            print(f"📊 Volatility: {analysis['volatility']:.1f}%")
            
            # Display key indicators
            indicators = analysis['indicators']
            print(f"\n📊 Key Indicators:")
            print(f"   RSI: {indicators['rsi']:.1f}")
            print(f"   StochRSI: {indicators['stoch_k']:.1f}")
            print(f"   EMA 9: ${indicators['ema_9']:.2f}")
            print(f"   EMA 21: ${indicators['ema_21']:.2f}")
            print(f"   Volume Ratio: {indicators['volume_ratio']:.1f}x")
            
            # Display AI analysis
            ai_analysis = analysis['ai_analysis']
            print(f"\n🤖 AI Analysis:")
            print(f"   Recommendation: {ai_analysis['recommendation'].upper()}")
            print(f"   Confidence: {ai_analysis['confidence']:.1%}")
            print(f"   Reasoning:")
            for reason in ai_analysis['reasoning']:
                print(f"     • {reason}")
            
            if ai_analysis['opportunity_factors']:
                print(f"   🟢 Opportunities:")
                for opp in ai_analysis['opportunity_factors']:
                    print(f"     • {opp}")
            
            if ai_analysis['risk_factors']:
                print(f"   🔴 Risks:")
                for risk in ai_analysis['risk_factors']:
                    print(f"     • {risk}")
            
            # Get human input
            print("\n" + "=" * 50)
            print("YOUR TURN! What's your decision?")
            
            while True:
                human_decision = input("\n📝 Your decision (buy/sell/hold): ").lower().strip()
                if human_decision in ['buy', 'sell', 'hold']:
                    break
                print("⚠️  Please enter 'buy', 'sell', or 'hold'")
            
            human_reasoning = input("💭 Your reasoning: ").strip()
            
            while True:
                try:
                    human_confidence = float(input("🎯 Your confidence (0-1): "))
                    if 0 <= human_confidence <= 1:
                        break
                    print("⚠️  Please enter a number between 0 and 1")
                except ValueError:
                    print("⚠️  Please enter a valid number")
            
            # Process collaborative decision
            session_data = self.collaborative_learning.create_decision_session(
                f"CLI_Session_{datetime.now().strftime('%Y%m%d_%H%M%S')}", 
                symbol
            )
            
            result = self.collaborative_learning.process_human_decision(
                session_data=session_data,
                human_decision=human_decision,
                human_reasoning=human_reasoning,
                human_confidence=human_confidence
            )
            
            # Display results
            print("\n" + "=" * 50)
            print("🤝 COLLABORATIVE RESULT")
            print("=" * 50)
            
            print(f"👤 Human: {result['human_decision'].upper()} (confidence: {result['human_confidence']:.1%})")
            print(f"🤖 AI: {result['ai_decision'].upper()} (confidence: {result['ai_confidence']:.1%})")
            print(f"🎯 Final Action: {result['final_action'].upper()}")
            
            print(f"\n📚 Learning Opportunities:")
            for opportunity in result['learning_opportunities']:
                print(f"   • {opportunity}")
                
            # Store for tracking
            print(f"\n💾 Session stored with ID: {result['session_id']}")
            
            return result
            
        except Exception as e:
            print(f"❌ Session failed: {e}")
            return None
    
    def compare_strategies(self, symbol='AAPL', days=180):
        """Compare multiple strategies on the same data"""
        strategies = ['stoch_rsi_ema', 'bollinger_mean_reversion', 'momentum_breakout']
        results = {}
        
        print(f"\n🏆 Strategy Comparison on {symbol}")
        print("=" * 60)
        
        for strategy in strategies:
            print(f"Testing {strategy}...")
            performance = self.run_quick_backtest(symbol, strategy, days)
            if performance:
                results[strategy] = performance
        
        if results:
            print(f"\n📊 COMPARISON SUMMARY")
            print("-" * 60)
            print(f"{'Strategy':<25} {'Return':<10} {'Win Rate':<10} {'Sharpe':<8} {'Drawdown'}")
            print("-" * 60)
            
            # Sort by total return
            sorted_results = sorted(results.items(), key=lambda x: x[1]['total_return'], reverse=True)
            
            for strategy, perf in sorted_results:
                print(f"{strategy:<25} {perf['total_return']:+6.1f}%    {perf['win_rate']:5.1f}%     {perf['sharpe_ratio']:5.2f}   {perf['max_drawdown']:6.1f}%")
            
            winner = sorted_results[0]
            print(f"\n🏆 Best Strategy: {winner[0]} with {winner[1]['total_return']:+.1f}% return")
        
        return results
    
    def learning_session(self, symbol='AAPL'):
        """Complete learning session with backtest + collaborative decision"""
        print(f"\n🎓 LEARNING SESSION: {symbol}")
        print("=" * 60)
        
        # Step 1: Historical analysis
        print("Step 1: Running historical backtest for context...")
        backtest_result = self.run_quick_backtest(symbol, days=90)
        
        # Step 2: Current collaborative decision
        print("\nStep 2: Current market analysis and decision...")
        decision_result = self.start_collaborative_session(symbol)
        
        # Step 3: Learning synthesis
        if backtest_result and decision_result:
            print("\n🧠 LEARNING SYNTHESIS")
            print("=" * 40)
            
            historical_performance = backtest_result['total_return']
            current_decision = decision_result['final_action']
            
            print(f"📈 Historical Performance: {historical_performance:+.1f}%")
            print(f"🎯 Current Decision: {current_decision.upper()}")
            
            # Generate learning insights
            insights = []
            
            if historical_performance > 5 and current_decision == 'buy':
                insights.append("✅ Consistent with profitable historical pattern")
            elif historical_performance < -5 and current_decision == 'sell':
                insights.append("✅ Learning from historical losses")
            elif abs(historical_performance) < 2:
                insights.append("⚠️  Historical data shows sideways market - be cautious")
            
            if backtest_result['win_rate'] > 60:
                insights.append("📊 Strategy shows good win rate historically")
            elif backtest_result['win_rate'] < 40:
                insights.append("⚠️  Strategy historically has low win rate")
            
            print(f"\n💡 Key Insights:")
            for insight in insights:
                print(f"   {insight}")
            
            return {
                'historical': backtest_result,
                'current': decision_result,
                'insights': insights
            }
        
        return None

def main():
    parser = argparse.ArgumentParser(description='Trading Training CLI')
    parser.add_argument('command', choices=['backtest', 'collaborate', 'compare', 'learn'], 
                       help='Command to run')
    parser.add_argument('--symbol', default='AAPL', help='Stock symbol (default: AAPL)')
    parser.add_argument('--strategy', default='stoch_rsi_ema', 
                       choices=['stoch_rsi_ema', 'bollinger_mean_reversion', 'momentum_breakout'],
                       help='Trading strategy (default: stoch_rsi_ema)')
    parser.add_argument('--days', type=int, default=365, help='Backtest period in days (default: 365)')
    
    args = parser.parse_args()
    
    cli = TrainingCLI()
    
    print("🎯 Trading Training System CLI")
    print("Collaborative learning for human + AI trading strategies")
    
    if args.command == 'backtest':
        cli.run_quick_backtest(args.symbol, args.strategy, args.days)
        
    elif args.command == 'collaborate':
        cli.start_collaborative_session(args.symbol)
        
    elif args.command == 'compare':
        cli.compare_strategies(args.symbol, args.days)
        
    elif args.command == 'learn':
        cli.learning_session(args.symbol)
    
    print(f"\n💾 All data stored in: {cli.db.db_path}")
    print("🌐 For full dashboard experience, run: python training_dashboard.py")

if __name__ == "__main__":
    main()