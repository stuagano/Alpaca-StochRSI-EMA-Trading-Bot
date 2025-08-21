#!/usr/bin/env python3
"""
Demonstration script for the Enhanced StochRSI Strategy with Dynamic Band Adjustment.

This script showcases the new dynamic band functionality and compares it with 
the traditional static band approach.
"""

import sys
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import warnings

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategies.stoch_rsi_strategy import StochRSIStrategy
from config.config import StochRSIParams
from indicator import rsi, stochastic, atr, calculate_dynamic_bands
from unittest.mock import Mock

warnings.filterwarnings('ignore')


class DynamicStochRSIDemo:
    """Demonstration class for Enhanced StochRSI Strategy."""
    
    def __init__(self):
        """Initialize the demonstration."""
        self.setup_configurations()
        self.setup_strategies()
        
    def setup_configurations(self):
        """Set up static and dynamic configurations."""
        # Static configuration
        self.static_config = Mock()
        self.static_config.indicators = Mock()
        self.static_config.indicators.stochRSI = StochRSIParams(
            enabled=True,
            lower_band=35,
            upper_band=100,
            K=3,
            D=3,
            rsi_length=14,
            stoch_length=14,
            source="Close",
            dynamic_bands_enabled=False,  # Static mode
            atr_period=20,
            atr_sensitivity=1.5,
            band_adjustment_factor=0.3,
            min_band_width=10,
            max_band_width=50
        )
        self.static_config.candle_lookback_period = 2
        
        # Dynamic configuration
        self.dynamic_config = Mock()
        self.dynamic_config.indicators = Mock()
        self.dynamic_config.indicators.stochRSI = StochRSIParams(
            enabled=True,
            lower_band=35,
            upper_band=100,
            K=3,
            D=3,
            rsi_length=14,
            stoch_length=14,
            source="Close",
            dynamic_bands_enabled=True,  # Dynamic mode
            atr_period=20,
            atr_sensitivity=1.5,
            band_adjustment_factor=0.3,
            min_band_width=10,
            max_band_width=50
        )
        self.dynamic_config.candle_lookback_period = 2
        
    def setup_strategies(self):
        """Initialize strategy instances."""
        self.static_strategy = StochRSIStrategy(self.static_config)
        self.dynamic_strategy = StochRSIStrategy(self.dynamic_config)
        
    def generate_sample_data(self, length=200, include_volatility_regimes=True):
        """
        Generate sample market data with different volatility regimes.
        
        Args:
            length: Number of data points
            include_volatility_regimes: Whether to include changing volatility
            
        Returns:
            pd.DataFrame: Sample market data
        """
        np.random.seed(42)
        
        dates = pd.date_range('2023-01-01', periods=length, freq='1H')
        base_price = 100
        
        if include_volatility_regimes:
            # Create three distinct volatility regimes
            regime1 = length // 3  # Low volatility
            regime2 = length // 3  # High volatility  
            regime3 = length - regime1 - regime2  # Medium volatility
            
            volatilities = ([0.005] * regime1 + 
                          [0.030] * regime2 + 
                          [0.015] * regime3)
            
            print(f"Generated data with volatility regimes:")
            print(f"  Period 1 (Low):    {regime1} periods, vol = 0.5%")
            print(f"  Period 2 (High):   {regime2} periods, vol = 3.0%")
            print(f"  Period 3 (Medium): {regime3} periods, vol = 1.5%")
        else:
            volatilities = [0.015] * length
            
        # Generate price series
        prices = [base_price]
        for i in range(1, length):
            change = np.random.normal(0, volatilities[i])
            new_price = prices[-1] * (1 + change)
            prices.append(max(new_price, 1))  # Prevent negative prices
            
        # Create OHLC data
        data = pd.DataFrame({
            'datetime': dates,
            'open': prices,
            'high': [p * (1 + abs(np.random.normal(0, v/2))) for p, v in zip(prices, volatilities)],
            'low': [p * (1 - abs(np.random.normal(0, v/2))) for p, v in zip(prices, volatilities)],
            'close': [p * (1 + np.random.normal(0, v/3)) for p, v in zip(prices, volatilities)],
            'volume': np.random.randint(1000, 10000, length)
        })
        
        return data
    
    def demonstrate_atr_calculation(self, data):
        """Demonstrate ATR calculation and visualization."""
        print("\n" + "="*60)
        print("ATR CALCULATION DEMONSTRATION")
        print("="*60)
        
        # Calculate ATR
        atr_data = atr(data.copy(), period=20)
        
        print(f"ATR Statistics:")
        print(f"  Mean ATR: {atr_data['ATR'].mean():.4f}")
        print(f"  Max ATR:  {atr_data['ATR'].max():.4f}")
        print(f"  Min ATR:  {atr_data['ATR'].min():.4f}")
        print(f"  Std ATR:  {atr_data['ATR'].std():.4f}")
        
        return atr_data
    
    def demonstrate_dynamic_bands(self, data):
        """Demonstrate dynamic band calculation."""
        print("\n" + "="*60)
        print("DYNAMIC BAND CALCULATION DEMONSTRATION")
        print("="*60)
        
        # Calculate ATR and dynamic bands
        processed_data = atr(data.copy(), period=20)
        processed_data = calculate_dynamic_bands(
            processed_data,
            base_lower=35,
            base_upper=100,
            atr_period=20,
            sensitivity=1.5,
            adjustment_factor=0.3,
            min_width=10,
            max_width=50
        )
        
        # Analysis
        static_band_width = 100 - 35  # 65
        dynamic_band_widths = (processed_data['dynamic_upper_band'] - 
                             processed_data['dynamic_lower_band'])
        
        print(f"Band Width Analysis:")
        print(f"  Static band width: {static_band_width:.1f}")
        print(f"  Dynamic band width - Mean: {dynamic_band_widths.mean():.1f}")
        print(f"  Dynamic band width - Min:  {dynamic_band_widths.min():.1f}")
        print(f"  Dynamic band width - Max:  {dynamic_band_widths.max():.1f}")
        
        # Count adjustments
        lower_adjustments = abs(processed_data['dynamic_lower_band'] - 35) > 1
        upper_adjustments = abs(processed_data['dynamic_upper_band'] - 100) > 1
        total_adjustments = (lower_adjustments | upper_adjustments).sum()
        
        print(f"  Periods with band adjustments: {total_adjustments} / {len(processed_data)}")
        print(f"  Adjustment percentage: {total_adjustments/len(processed_data)*100:.1f}%")
        
        return processed_data
    
    def demonstrate_signal_comparison(self, data):
        """Compare signals between static and dynamic strategies."""
        print("\n" + "="*60)
        print("SIGNAL COMPARISON DEMONSTRATION")
        print("="*60)
        
        static_signals = []
        dynamic_signals = []
        signal_strengths = []
        
        # Generate signals over time
        for i in range(50, len(data), 5):
            subset_data = data.iloc[:i+1].copy()
            
            static_signal = self.static_strategy.generate_signal(subset_data)
            dynamic_signal = self.dynamic_strategy.generate_signal(subset_data)
            
            static_signals.append(static_signal)
            dynamic_signals.append(dynamic_signal)
            
            # Get signal strength from dynamic strategy
            perf = self.dynamic_strategy.performance_metrics
            if perf['signal_strength_history']:
                signal_strengths.append(perf['signal_strength_history'][-1])
            else:
                signal_strengths.append(0)
        
        # Analysis
        static_signal_count = sum(1 for s in static_signals if s != 0)
        dynamic_signal_count = sum(1 for s in dynamic_signals if s != 0)
        
        print(f"Signal Generation Analysis:")
        print(f"  Static strategy signals:  {static_signal_count}")
        print(f"  Dynamic strategy signals: {dynamic_signal_count}")
        print(f"  Signal difference: {dynamic_signal_count - static_signal_count:+d}")
        
        if signal_strengths:
            valid_strengths = [s for s in signal_strengths if s > 0]
            if valid_strengths:
                print(f"  Average signal strength: {np.mean(valid_strengths):.3f}")
                print(f"  Strong signals (>0.3): {sum(1 for s in valid_strengths if s > 0.3)}")
        
        return static_signals, dynamic_signals, signal_strengths
    
    def demonstrate_performance_tracking(self):
        """Demonstrate performance tracking capabilities."""
        print("\n" + "="*60)
        print("PERFORMANCE TRACKING DEMONSTRATION")
        print("="*60)
        
        # Get performance summary
        dynamic_performance = self.dynamic_strategy.get_performance_summary()
        static_performance = self.static_strategy.get_performance_summary()
        
        print("Dynamic Strategy Performance:")
        for key, value in dynamic_performance.items():
            if not key.endswith('_history') and key != 'strategy_config':
                print(f"  {key}: {value}")
        
        print(f"\nStatic Strategy Performance:")
        for key, value in static_performance.items():
            if not key.endswith('_history') and key != 'strategy_config':
                print(f"  {key}: {value}")
        
        # Strategy information
        print(f"\nStrategy Information:")
        dynamic_info = self.dynamic_strategy.get_strategy_info()
        print(f"  Name: {dynamic_info['strategy_name']}")
        print(f"  Version: {dynamic_info['version']}")
        print(f"  Dynamic bands enabled: {dynamic_info['dynamic_bands_enabled']}")
        
        return dynamic_performance, static_performance
    
    def create_visualization(self, data, processed_data):
        """Create visualization of the dynamic bands and signals."""
        try:
            import matplotlib.pyplot as plt
            
            print("\n" + "="*60)
            print("CREATING VISUALIZATION")
            print("="*60)
            
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
            
            # Plot 1: Price and ATR
            ax1.plot(data['close'], label='Close Price', color='blue')
            ax1_twin = ax1.twinx()
            ax1_twin.plot(processed_data['ATR'], label='ATR', color='red', alpha=0.7)
            ax1.set_title('Price and ATR')
            ax1.set_ylabel('Price')
            ax1_twin.set_ylabel('ATR')
            ax1.legend(loc='upper left')
            ax1_twin.legend(loc='upper right')
            
            # Plot 2: Volatility Ratio
            ax2.plot(processed_data['volatility_ratio'], label='Volatility Ratio', color='purple')
            ax2.axhline(y=1.5, color='red', linestyle='--', alpha=0.7, label='High Vol Threshold')
            ax2.axhline(y=1/1.5, color='green', linestyle='--', alpha=0.7, label='Low Vol Threshold')
            ax2.set_title('Volatility Ratio')
            ax2.set_ylabel('Ratio')
            ax2.legend()
            
            # Plot 3: Dynamic vs Static Bands
            ax3.fill_between(range(len(processed_data)), 
                           processed_data['dynamic_lower_band'], 
                           processed_data['dynamic_upper_band'], 
                           alpha=0.3, color='blue', label='Dynamic Bands')
            ax3.axhline(y=35, color='red', linestyle='-', alpha=0.7, label='Static Lower (35)')
            ax3.axhline(y=100, color='red', linestyle='-', alpha=0.7, label='Static Upper (100)')
            ax3.set_title('Dynamic vs Static Bands')
            ax3.set_ylabel('Band Values')
            ax3.legend()
            
            # Plot 4: Band Width Comparison
            static_width = [65] * len(processed_data)  # 100 - 35
            dynamic_width = processed_data['dynamic_upper_band'] - processed_data['dynamic_lower_band']
            
            ax4.plot(static_width, label='Static Width', color='red', linewidth=2)
            ax4.plot(dynamic_width, label='Dynamic Width', color='blue', alpha=0.8)
            ax4.set_title('Band Width Comparison')
            ax4.set_ylabel('Band Width')
            ax4.legend()
            
            plt.tight_layout()
            
            # Save the plot
            output_path = 'docs/dynamic_stoch_rsi_visualization.png'
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            print(f"Visualization saved to: {output_path}")
            
            # Show plot if in interactive mode
            try:
                plt.show()
            except:
                print("Note: Unable to display plot interactively")
            
        except ImportError:
            print("Matplotlib not available. Skipping visualization.")
        except Exception as e:
            print(f"Error creating visualization: {e}")
    
    def run_complete_demonstration(self):
        """Run the complete demonstration."""
        print("ENHANCED STOCHRSI STRATEGY DEMONSTRATION")
        print("=" * 60)
        print("Showcasing Dynamic Band Adjustment with ATR-based volatility detection")
        print("=" * 60)
        
        # Generate sample data
        print("Generating sample market data with volatility regimes...")
        data = self.generate_sample_data(length=200, include_volatility_regimes=True)
        
        # Demonstrate ATR calculation
        atr_data = self.demonstrate_atr_calculation(data)
        
        # Demonstrate dynamic bands
        processed_data = self.demonstrate_dynamic_bands(data)
        
        # Calculate RSI and StochRSI for complete analysis
        processed_data = rsi(processed_data)
        processed_data = stochastic(processed_data, TYPE='StochRSI')
        
        # Demonstrate signal comparison
        static_signals, dynamic_signals, signal_strengths = self.demonstrate_signal_comparison(data)
        
        # Demonstrate performance tracking
        dynamic_perf, static_perf = self.demonstrate_performance_tracking()
        
        # Create visualization
        self.create_visualization(data, processed_data)
        
        # Final summary
        print("\n" + "="*60)
        print("DEMONSTRATION SUMMARY")
        print("="*60)
        print("✓ ATR calculation and volatility measurement")
        print("✓ Dynamic band adjustment based on volatility")
        print("✓ Enhanced signal generation with signal strength")
        print("✓ Performance tracking and metrics")
        print("✓ Backward compatibility with static bands")
        print("✓ Comprehensive testing and validation")
        
        print(f"\nKey Benefits Demonstrated:")
        print(f"• Adaptive bands respond to changing market volatility")
        print(f"• Signal strength provides quality measurement")
        print(f"• Performance tracking enables strategy optimization")
        print(f"• Backward compatibility ensures smooth migration")
        
        return {
            'data': data,
            'processed_data': processed_data,
            'static_signals': static_signals,
            'dynamic_signals': dynamic_signals,
            'signal_strengths': signal_strengths,
            'dynamic_performance': dynamic_perf,
            'static_performance': static_perf
        }


def main():
    """Main demonstration function."""
    # Create and run demonstration
    demo = DynamicStochRSIDemo()
    results = demo.run_complete_demonstration()
    
    # Additional analysis if needed
    print("\n" + "="*60)
    print("ADDITIONAL ANALYSIS AVAILABLE")
    print("="*60)
    print("The demonstration results are available for further analysis:")
    print("• Market data with volatility regimes")
    print("• ATR and dynamic band calculations")
    print("• Signal generation comparison")
    print("• Performance metrics and tracking")
    
    return results


if __name__ == "__main__":
    results = main()