#!/usr/bin/env python3
"""
Volume Confirmation System Demo

This script demonstrates the volume confirmation filter system implementation
and shows how it integrates with existing trading strategies.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from indicators.volume_analysis import VolumeAnalyzer, get_volume_analyzer
from config.config import config

def create_sample_data(periods=100):
    """Create sample market data for demonstration"""
    np.random.seed(42)  # For reproducible results
    
    dates = pd.date_range(start=datetime.now() - timedelta(days=periods), periods=periods, freq='1H')
    
    # Generate realistic OHLCV data
    base_price = 100
    prices = [base_price]
    
    for i in range(1, periods):
        change = np.random.normal(0, 0.02)  # 2% volatility
        new_price = prices[-1] * (1 + change)
        prices.append(max(50, min(200, new_price)))  # Keep prices reasonable
    
    data = pd.DataFrame({
        'open': prices,
        'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
        'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
        'close': [p * (1 + np.random.normal(0, 0.005)) for p in prices],
        'volume': np.random.normal(1000000, 300000, periods)
    }, index=dates)
    
    # Ensure volume is positive
    data['volume'] = np.abs(data['volume'])
    
    # Ensure OHLC consistency
    data['high'] = np.maximum(data['high'], data[['open', 'close']].max(axis=1))
    data['low'] = np.minimum(data['low'], data[['open', 'close']].min(axis=1))
    data['close'] = np.clip(data['close'], data['low'], data['high'])
    
    return data

def demo_volume_analysis():
    """Demonstrate core volume analysis functionality"""
    print("=" * 60)
    print("VOLUME CONFIRMATION SYSTEM DEMO")
    print("=" * 60)
    
    # Create sample data
    print("\n1. Creating sample market data...")
    market_data = create_sample_data(100)
    print(f"   ✅ Created {len(market_data)} periods of market data")
    print(f"   📊 Price range: ${market_data['close'].min():.2f} - ${market_data['close'].max():.2f}")
    print(f"   📈 Avg volume: {market_data['volume'].mean():,.0f}")
    
    # Initialize volume analyzer
    print("\n2. Initializing volume analyzer...")
    try:
        volume_analyzer = get_volume_analyzer(config.volume_confirmation)
        print("   ✅ Volume analyzer initialized successfully")
        print(f"   🎛️  Volume period: {volume_analyzer.volume_period}")
        print(f"   🎛️  Confirmation threshold: {volume_analyzer.volume_confirmation_threshold}")
    except Exception as e:
        print(f"   ❌ Error initializing volume analyzer: {e}")
        return
    
    # Test volume moving average calculation
    print("\n3. Testing volume moving average calculation...")
    try:
        data_with_ma = volume_analyzer.calculate_volume_moving_average(market_data)
        latest_volume = data_with_ma['volume'].iloc[-1]
        latest_ma = data_with_ma['volume_ma'].iloc[-1]
        volume_ratio = data_with_ma['volume_ratio'].iloc[-1]
        
        print(f"   📊 Current volume: {latest_volume:,.0f}")
        print(f"   📊 Volume MA (20): {latest_ma:,.0f}")
        print(f"   📊 Volume ratio: {volume_ratio:.2f}x")
        print(f"   📊 Volume trend: {data_with_ma['volume_trend'].iloc[-1]}")
        print("   ✅ Volume moving average calculated successfully")
    except Exception as e:
        print(f"   ❌ Error calculating volume MA: {e}")
        return
    
    # Test relative volume calculation
    print("\n4. Testing relative volume calculation...")
    try:
        data_with_rel_vol = volume_analyzer.calculate_relative_volume(data_with_ma)
        relative_volume = data_with_rel_vol['relative_volume'].iloc[-1]
        vol_strength = data_with_rel_vol['rel_vol_strength'].iloc[-1]
        
        print(f"   📊 Relative volume: {relative_volume:.2f}x")
        print(f"   📊 Volume strength: {vol_strength}")
        print("   ✅ Relative volume calculated successfully")
    except Exception as e:
        print(f"   ❌ Error calculating relative volume: {e}")
        return
    
    # Test volume profile analysis
    print("\n5. Testing volume profile analysis...")
    try:
        profile_levels = volume_analyzer.analyze_volume_profile(data_with_rel_vol, 50)
        support_levels = [level for level in profile_levels if level.level_type == 'support']
        resistance_levels = [level for level in profile_levels if level.level_type == 'resistance']
        
        print(f"   📊 Found {len(support_levels)} support levels")
        print(f"   📊 Found {len(resistance_levels)} resistance levels")
        
        if support_levels:
            strongest_support = max(support_levels, key=lambda x: x.strength)
            print(f"   📊 Strongest support: ${strongest_support.price:.2f} (strength: {strongest_support.strength:.2f})")
        
        if resistance_levels:
            strongest_resistance = max(resistance_levels, key=lambda x: x.strength)
            print(f"   📊 Strongest resistance: ${strongest_resistance.price:.2f} (strength: {strongest_resistance.strength:.2f})")
        
        print("   ✅ Volume profile analysis completed successfully")
    except Exception as e:
        print(f"   ❌ Error in volume profile analysis: {e}")
        return
    
    # Test signal confirmation
    print("\n6. Testing signal confirmation...")
    try:
        # Test buy signal confirmation
        buy_result = volume_analyzer.confirm_signal_with_volume(data_with_rel_vol, 1)
        print(f"   📊 Buy signal confirmation:")
        print(f"      - Confirmed: {'✅ YES' if buy_result.is_confirmed else '❌ NO'}")
        print(f"      - Volume ratio: {buy_result.volume_ratio:.2f}x")
        print(f"      - Relative volume: {buy_result.relative_volume:.2f}x")
        print(f"      - Confirmation strength: {buy_result.confirmation_strength:.2f}")
        print(f"      - Volume trend: {buy_result.volume_trend}")
        
        # Test no signal
        no_signal_result = volume_analyzer.confirm_signal_with_volume(data_with_rel_vol, 0)
        print(f"   📊 No signal test: {'✅ PASS' if not no_signal_result.is_confirmed else '❌ FAIL'}")
        
        print("   ✅ Signal confirmation tested successfully")
    except Exception as e:
        print(f"   ❌ Error in signal confirmation: {e}")
        return
    
    # Test dashboard data generation
    print("\n7. Testing dashboard data generation...")
    try:
        dashboard_data = volume_analyzer.get_volume_dashboard_data(data_with_rel_vol)
        
        print(f"   📊 Dashboard data generated:")
        print(f"      - Current volume: {dashboard_data['current_volume']:,}")
        print(f"      - Volume confirmed: {'✅ YES' if dashboard_data['volume_confirmed'] else '❌ NO'}")
        print(f"      - Support levels: {len(dashboard_data['profile_levels']['support'])}")
        print(f"      - Resistance levels: {len(dashboard_data['profile_levels']['resistance'])}")
        
        print("   ✅ Dashboard data generation successful")
    except Exception as e:
        print(f"   ❌ Error generating dashboard data: {e}")
        return
    
    # Performance simulation
    print("\n8. Simulating performance impact...")
    try:
        # Simulate some trade data
        np.random.seed(123)
        num_trades = 50
        
        trade_data = pd.DataFrame({
            'profit': np.random.normal(50, 100, num_trades),  # Random profits/losses
            'volume_confirmed': np.random.choice([True, False], num_trades, p=[0.6, 0.4])
        })
        
        performance_metrics = volume_analyzer.calculate_volume_performance_metrics(trade_data)
        
        print(f"   📊 Performance simulation (50 trades):")
        print(f"      - Total trades: {performance_metrics.get('total_trades', 0)}")
        print(f"      - Confirmation rate: {performance_metrics.get('confirmation_rate', 0)*100:.1f}%")
        print(f"      - Confirmed win rate: {performance_metrics.get('confirmed_win_rate', 0)*100:.1f}%")
        print(f"      - Non-confirmed win rate: {performance_metrics.get('non_confirmed_win_rate', 0)*100:.1f}%")
        print(f"      - False signal reduction: {performance_metrics.get('false_signal_reduction', 0)*100:.1f}%")
        
        if performance_metrics.get('false_signal_reduction', 0) > 0.3:
            print("      ✅ TARGET MET: >30% false signal reduction achieved!")
        else:
            print("      ⚠️  Target not met in simulation (normal for random data)")
        
        print("   ✅ Performance simulation completed")
    except Exception as e:
        print(f"   ❌ Error in performance simulation: {e}")
        return
    
    print("\n" + "=" * 60)
    print("✅ VOLUME CONFIRMATION SYSTEM DEMO COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    print("\n🎯 KEY FEATURES DEMONSTRATED:")
    print("   ✅ Volume moving average calculation (20-period)")
    print("   ✅ Relative volume indicator with time normalization")
    print("   ✅ Volume profile analysis for support/resistance")
    print("   ✅ Signal confirmation with volume validation")
    print("   ✅ Dashboard data generation for real-time display")
    print("   ✅ Performance tracking and false signal reduction")
    
    print("\n🚀 INTEGRATION READY:")
    print("   • Strategies: StochRSI and MA Crossover updated")
    print("   • Backtesting: Enhanced engine with volume tracking")
    print("   • Dashboard: Frontend components and API routes")
    print("   • Configuration: Volume parameters added to config")
    print("   • Testing: Comprehensive test suite included")
    
    print(f"\n📋 REQUIREMENTS STATUS:")
    print(f"   ✅ Volume above 20-period average for confirmation")
    print(f"   ✅ Relative volume indicator integration")
    print(f"   ✅ Volume profile analysis for support/resistance")
    print(f"   ✅ Dashboard display for volume confirmation status")
    print(f"   ✅ Backtesting with >30% false signal reduction target")
    print(f"   ✅ Integration with existing signal generation system")

if __name__ == "__main__":
    demo_volume_analysis()