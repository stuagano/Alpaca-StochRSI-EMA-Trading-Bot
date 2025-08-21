#!/usr/bin/env python3
"""
Test Dynamic StochRSI Bands with Live Market Data
"""

import pandas as pd
import numpy as np
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from indicator import calculate_dynamic_bands, atr

def test_dynamic_bands():
    print("🧪 Testing Dynamic StochRSI Bands")
    print("=" * 50)
    
    # Create test data with realistic price movements
    dates = pd.date_range('2024-01-01', periods=50, freq='1H')
    np.random.seed(42)
    prices = 100 + np.cumsum(np.random.randn(50) * 0.5)
    df = pd.DataFrame({
        'datetime': dates,
        'open': prices + np.random.randn(50) * 0.1,
        'high': prices + abs(np.random.randn(50) * 0.3),
        'low': prices - abs(np.random.randn(50) * 0.3),
        'close': prices,
        'volume': np.random.randint(1000, 10000, 50)
    })
    
    # Calculate ATR and dynamic bands with new sensitivity
    df = atr(df)
    df = calculate_dynamic_bands(df, sensitivity=0.7)
    
    # Test results
    print(f"📊 Data points: {len(df)}")
    print(f"📈 ATR range: {df['ATR'].min():.2f} - {df['ATR'].max():.2f}")
    print(f"🎯 Dynamic lower band range: {df['dynamic_lower_band'].min():.2f} - {df['dynamic_lower_band'].max():.2f}")
    print(f"🎯 Dynamic upper band range: {df['dynamic_upper_band'].min():.2f} - {df['dynamic_upper_band'].max():.2f}")
    
    # Check if bands actually changed from base values
    base_lower, base_upper = 35, 100
    lower_changed = not (df['dynamic_lower_band'] == base_lower).all()
    upper_changed = not (df['dynamic_upper_band'] == base_upper).all()
    bands_changed = lower_changed or upper_changed
    
    print(f"✅ Bands adjusted from base values: {bands_changed}")
    
    if bands_changed:
        print("🎉 SUCCESS: Dynamic bands are working!")
        # Show volatility ratio analysis
        df_temp = df.copy()
        df_temp['ATR_MA'] = df_temp['ATR'].rolling(window=20).mean()
        df_temp['volatility_ratio'] = df_temp['ATR'] / df_temp['ATR_MA']
        
        high_vol_count = (df_temp['volatility_ratio'] > 0.7).sum()
        low_vol_count = (df_temp['volatility_ratio'] < (1/0.7)).sum()
        
        print(f"📊 High volatility periods (>0.7): {high_vol_count}")
        print(f"📊 Low volatility periods (<{1/0.7:.2f}): {low_vol_count}")
    else:
        print("❌ FAILED: Dynamic bands are not adjusting")
        print("🔍 Debugging info:")
        df_temp = df.copy()
        df_temp['ATR_MA'] = df_temp['ATR'].rolling(window=20).mean()
        df_temp['volatility_ratio'] = df_temp['ATR'] / df_temp['ATR_MA']
        print(f"   Volatility ratio range: {df_temp['volatility_ratio'].min():.3f} - {df_temp['volatility_ratio'].max():.3f}")
        print(f"   Sensitivity threshold: 0.7")
        print(f"   High vol trigger (>0.7): {(df_temp['volatility_ratio'] > 0.7).sum()} periods")
        print(f"   Low vol trigger (<{1/0.7:.3f}): {(df_temp['volatility_ratio'] < (1/0.7)).sum()} periods")
    
    # Show recent values
    print("\n📋 Recent 5 rows:")
    display_cols = ['ATR', 'dynamic_lower_band', 'dynamic_upper_band']
    if 'ATR_MA' in df.columns:
        df_temp = df.copy()
        df_temp['ATR_MA'] = df_temp['ATR'].rolling(window=20).mean()
        df_temp['volatility_ratio'] = df_temp['ATR'] / df_temp['ATR_MA']
        display_cols.extend(['ATR_MA', 'volatility_ratio'])
        print(df_temp[display_cols].tail().round(3))
    else:
        print(df[display_cols].tail().round(3))
    
    return bands_changed

if __name__ == "__main__":
    success = test_dynamic_bands()
    sys.exit(0 if success else 1)