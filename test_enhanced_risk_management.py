#!/usr/bin/env python3
"""
Test script for enhanced risk management system
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from risk_management.enhanced_risk_manager import get_enhanced_risk_manager
from risk_management.risk_config import get_risk_config, RiskLevel, RiskConfig
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def test_enhanced_risk_manager():
    """Test the enhanced risk management system"""
    
    print("=" * 60)
    print("TESTING ENHANCED RISK MANAGEMENT SYSTEM")
    print("=" * 60)
    
    # Test 1: Load risk configuration
    print("\n1. Testing Risk Configuration...")
    try:
        risk_config = get_risk_config()
        print(f"✓ Risk config loaded successfully")
        print(f"  - Risk level: {risk_config.get_risk_level().value}")
        print(f"  - Max daily loss: {risk_config.max_daily_loss:.2%}")
        print(f"  - Max position size: {risk_config.max_position_size:.2%}")
        print(f"  - Max positions: {risk_config.max_positions}")
    except Exception as e:
        print(f"✗ Error loading risk config: {e}")
        return False
    
    # Test 2: Initialize enhanced risk manager
    print("\n2. Testing Enhanced Risk Manager Initialization...")
    try:
        risk_manager = get_enhanced_risk_manager()
        print(f"✓ Enhanced risk manager initialized successfully")
    except Exception as e:
        print(f"✗ Error initializing risk manager: {e}")
        return False
    
    # Test 3: Position size validation
    print("\n3. Testing Position Size Validation...")
    try:
        # Test valid position
        result = risk_manager.validate_position_size(
            symbol="AAPL",
            proposed_size=100,
            entry_price=150.0,
            stop_loss_price=145.0
        )
        print(f"✓ Valid position validation:")
        print(f"  - Approved: {result.approved}")
        print(f"  - Risk score: {result.risk_score:.1f}")
        print(f"  - Confidence: {result.confidence_score:.2f}")
        print(f"  - Warnings: {len(result.warnings)}")
        
        # Test oversized position
        result2 = risk_manager.validate_position_size(
            symbol="AAPL",
            proposed_size=10000,  # Very large position
            entry_price=150.0,
            stop_loss_price=145.0
        )
        print(f"✓ Oversized position validation:")
        print(f"  - Approved: {result2.approved}")
        print(f"  - Risk score: {result2.risk_score:.1f}")
        print(f"  - Violations: {len(result2.violations)}")
        
    except Exception as e:
        print(f"✗ Error in position validation: {e}")
    
    # Test 4: Optimal position sizing
    print("\n4. Testing Optimal Position Sizing...")
    try:
        recommendation = risk_manager.calculate_optimal_position_size(
            symbol="AAPL",
            entry_price=150.0,
            stop_loss_price=145.0
        )
        print(f"✓ Position size recommendation:")
        print(f"  - Recommended size: {recommendation.risk_adjusted_size:.3f}")
        print(f"  - Risk per trade: {recommendation.risk_per_trade:.2%}")
        print(f"  - Method used: {recommendation.method_used}")
        print(f"  - Confidence: {recommendation.confidence_score:.2f}")
        
    except Exception as e:
        print(f"✗ Error in optimal position sizing: {e}")
    
    # Test 5: Trailing stop creation
    print("\n5. Testing Trailing Stop Creation...")
    try:
        success = risk_manager.create_trailing_stop(
            symbol="AAPL",
            entry_price=150.0,
            position_size=100
        )
        print(f"✓ Trailing stop creation: {success}")
        
        # Get trailing stop status
        status = risk_manager.trailing_stop_manager.get_stop_status("AAPL")
        if status:
            print(f"  - Stop price: ${status['stop_price']:.2f}")
            print(f"  - Activation price: ${status['activation_price']:.2f}")
            print(f"  - Is activated: {status['is_activated']}")
        
    except Exception as e:
        print(f"✗ Error in trailing stop creation: {e}")
    
    # Test 6: Position tracking
    print("\n6. Testing Position Tracking...")
    try:
        # Add position
        success = risk_manager.add_position(
            symbol="AAPL",
            entry_price=150.0,
            position_size=100,
            stop_loss_price=145.0
        )
        print(f"✓ Position added: {success}")
        
        # Update price
        trigger_info = risk_manager.update_position_price("AAPL", 155.0)
        print(f"✓ Price updated to $155.0")
        print(f"  - Stop triggered: {trigger_info is not None}")
        
    except Exception as e:
        print(f"✗ Error in position tracking: {e}")
    
    # Test 7: Portfolio risk summary
    print("\n7. Testing Portfolio Risk Summary...")
    try:
        summary = risk_manager.get_portfolio_risk_summary()
        print(f"✓ Portfolio risk summary generated:")
        print(f"  - Risk level: {summary.get('risk_level', 'Unknown')}")
        print(f"  - Total positions: {summary.get('position_metrics', {}).get('total_positions', 0)}")
        print(f"  - Validation stats: {summary.get('validation_stats', {}).get('total_validations', 0)} validations")
        
    except Exception as e:
        print(f"✗ Error generating portfolio summary: {e}")
    
    # Test 8: Emergency override
    print("\n8. Testing Emergency Override...")
    try:
        # Enable override
        success1 = risk_manager.enable_emergency_override("Testing emergency override", 1)
        print(f"✓ Emergency override enabled: {success1}")
        
        # Disable override
        success2 = risk_manager.disable_emergency_override()
        print(f"✓ Emergency override disabled: {success2}")
        
    except Exception as e:
        print(f"✗ Error in emergency override: {e}")
    
    # Test 9: Different risk configurations
    print("\n9. Testing Different Risk Configurations...")
    try:
        # Conservative config
        conservative_config = RiskConfig.create_preset(RiskLevel.CONSERVATIVE)
        print(f"✓ Conservative config:")
        print(f"  - Max daily loss: {conservative_config.max_daily_loss:.2%}")
        print(f"  - Max position size: {conservative_config.max_position_size:.2%}")
        
        # Aggressive config
        aggressive_config = RiskConfig.create_preset(RiskLevel.AGGRESSIVE)
        print(f"✓ Aggressive config:")
        print(f"  - Max daily loss: {aggressive_config.max_daily_loss:.2%}")
        print(f"  - Max position size: {aggressive_config.max_position_size:.2%}")
        
    except Exception as e:
        print(f"✗ Error in risk configurations: {e}")
    
    print("\n" + "=" * 60)
    print("ENHANCED RISK MANAGEMENT TEST COMPLETED")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    test_enhanced_risk_manager()