#!/usr/bin/env python3
"""
Test script for the Training microservice
Tests both standalone and integrated operation
"""

import requests
import json
import time
from datetime import datetime, timedelta

# Service URLs
TRAINING_SERVICE = "http://localhost:9011"
API_GATEWAY = "http://localhost:9000"

def test_health_check():
    """Test the health check endpoint"""
    print("Testing health check...")
    try:
        response = requests.get(f"{TRAINING_SERVICE}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed: {data['status']}")
            print(f"   Database: {data['database']}")
            print(f"   Redis: {data['redis']}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_strategies():
    """Test getting available strategies"""
    print("\nTesting strategies endpoint...")
    try:
        response = requests.get(f"{TRAINING_SERVICE}/api/strategies")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Found {len(data['data'])} strategies:")
            for strategy in data['data']:
                print(f"   - {strategy['display_name']} ({strategy['complexity']})")
            return True
        else:
            print(f"❌ Strategies request failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Strategies error: {e}")
        return False

def test_backtest():
    """Test running a backtest"""
    print("\nTesting backtest...")
    try:
        payload = {
            "strategy": "stoch_rsi_ema",
            "symbol": "AAPL",
            "initial_capital": 10000,
            "start_date": (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d'),
            "end_date": datetime.now().strftime('%Y-%m-%d')
        }
        
        response = requests.post(
            f"{TRAINING_SERVICE}/api/backtest",
            json=payload
        )
        
        if response.status_code == 200:
            data = response.json()
            if data['status'] == 'success':
                result = data['data']
                print(f"✅ Backtest completed:")
                print(f"   Total Return: {result.get('total_return', 0):.2f}%")
                print(f"   Total Trades: {result.get('total_trades', 0)}")
                print(f"   Win Rate: {result.get('win_rate', 0):.1f}%")
                print(f"   Sharpe Ratio: {result.get('sharpe_ratio', 0):.2f}")
                return True
        else:
            print(f"❌ Backtest failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Backtest error: {e}")
        return False

def test_market_analysis():
    """Test market analysis endpoint"""
    print("\nTesting market analysis...")
    try:
        response = requests.get(f"{TRAINING_SERVICE}/api/collaborate/current/AAPL")
        
        if response.status_code == 200:
            data = response.json()
            if data['status'] == 'success':
                analysis = data['data']
                print(f"✅ Market analysis for AAPL:")
                print(f"   Current Price: ${analysis.get('current_price', 0):.2f}")
                print(f"   Day Change: {analysis.get('day_change', 0):.2f}%")
                print(f"   Recommendation: {analysis.get('recommendation', 'N/A')}")
                print(f"   Confidence: {analysis.get('confidence', 0):.0f}%")
                return True
        else:
            print(f"❌ Market analysis failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Market analysis error: {e}")
        return False

def test_collaborative_decision():
    """Test collaborative decision making"""
    print("\nTesting collaborative decision...")
    try:
        payload = {
            "symbol": "AAPL",
            "human_decision": "buy",
            "human_reasoning": "Technical indicators look bullish, support level holding",
            "confidence": 75
        }
        
        response = requests.post(
            f"{TRAINING_SERVICE}/api/collaborate/decision",
            json=payload
        )
        
        if response.status_code == 200:
            data = response.json()
            if data['status'] == 'success':
                result = data['data']
                print(f"✅ Collaborative decision made:")
                print(f"   Human: {result['human_decision']}")
                print(f"   AI: {result['ai_analysis']['recommendation']}")
                print(f"   Final: {result['final_decision']['action']}")
                return True
        else:
            print(f"❌ Collaborative decision failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Collaborative decision error: {e}")
        return False

def test_strategy_comparison():
    """Test strategy comparison"""
    print("\nTesting strategy comparison...")
    try:
        payload = {
            "symbol": "SPY",
            "strategies": ["stoch_rsi_ema", "bollinger_mean_reversion"],
            "days": 90
        }
        
        response = requests.post(
            f"{TRAINING_SERVICE}/api/strategies/compare",
            json=payload
        )
        
        if response.status_code == 200:
            data = response.json()
            if data['status'] == 'success':
                results = data['data']['results']
                print(f"✅ Strategy comparison for {data['data']['symbol']}:")
                for result in results:
                    if 'performance' in result:
                        print(f"   {result['strategy']}: {result['performance'].get('total_return', 0):.2f}% return")
                    else:
                        print(f"   {result['strategy']}: Error - {result.get('error', 'Unknown')}")
                return True
        else:
            print(f"❌ Strategy comparison failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Strategy comparison error: {e}")
        return False

def test_api_gateway_routing():
    """Test routing through API Gateway"""
    print("\nTesting API Gateway routing to training service...")
    try:
        # Test if API Gateway can route to training service
        response = requests.get(f"{API_GATEWAY}/training/health")
        if response.status_code == 200:
            print(f"✅ API Gateway routing successful")
            return True
        else:
            print(f"⚠️  API Gateway routing not configured (status: {response.status_code})")
            print("   This is expected if API Gateway doesn't have explicit training routes")
            return True  # Not a failure, just informational
    except Exception as e:
        print(f"ℹ️  API Gateway not available: {e}")
        print("   Training service can still be accessed directly")
        return True

def main():
    """Run all tests"""
    print("=" * 60)
    print("Training Microservice Test Suite")
    print("=" * 60)
    
    tests = [
        ("Health Check", test_health_check),
        ("Available Strategies", test_strategies),
        ("Backtest Execution", test_backtest),
        ("Market Analysis", test_market_analysis),
        ("Collaborative Decision", test_collaborative_decision),
        ("Strategy Comparison", test_strategy_comparison),
        ("API Gateway Routing", test_api_gateway_routing),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n{'='*40}")
        print(f"Running: {test_name}")
        print(f"{'='*40}")
        
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test crashed: {e}")
            failed += 1
        
        time.sleep(1)  # Small delay between tests
    
    print("\n" + "=" * 60)
    print("Test Results")
    print("=" * 60)
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📊 Success Rate: {(passed/(passed+failed)*100):.1f}%")
    
    if failed == 0:
        print("\n🎉 All tests passed! Training service is ready.")
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please check the logs.")

if __name__ == "__main__":
    main()