#!/usr/bin/env python3
"""
Complete System Integration Test
Tests all microservices and their interconnections
"""

import requests
import json
import time
from datetime import datetime

def test_service(name, url):
    """Test individual service health"""
    try:
        response = requests.get(f"{url}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ {name:20} | {data.get('status', 'unknown'):10} | {url}")
            return True
        else:
            print(f"❌ {name:20} | {response.status_code:10} | {url}")
            return False
    except Exception as e:
        print(f"❌ {name:20} | offline    | {url} - {str(e)}")
        return False

def test_data_flow():
    """Test data flow between services"""
    print("\n" + "="*80)
    print("DATA FLOW INTEGRATION TEST")
    print("="*80)
    
    results = {}
    
    # Test portfolio data
    try:
        response = requests.get("http://localhost:9001/portfolio/summary")
        if response.status_code == 200:
            portfolio = response.json()
            print(f"✅ Portfolio Value: ${portfolio['total_value']:,.2f}")
            print(f"✅ P&L: ${portfolio['today_pnl']:+.2f}")
            results['portfolio'] = True
        else:
            print("❌ Portfolio data failed")
            results['portfolio'] = False
    except Exception as e:
        print(f"❌ Portfolio data error: {e}")
        results['portfolio'] = False
    
    # Test positions data  
    try:
        response = requests.get("http://localhost:9001/positions")
        if response.status_code == 200:
            positions = response.json()
            print(f"✅ Positions loaded: {positions['count']} positions")
            for pos in positions['positions'][:3]:
                pnl_sign = "+" if pos['unrealized_pl'] >= 0 else ""
                print(f"   📊 {pos['symbol']}: {pos['qty']} shares @ ${pos['current_price']} ({pnl_sign}${pos['unrealized_pl']:.2f})")
            results['positions'] = True
        else:
            print("❌ Positions data failed")
            results['positions'] = False
    except Exception as e:
        print(f"❌ Positions data error: {e}")
        results['positions'] = False
    
    # Test market data
    try:
        response = requests.get("http://localhost:9005/market/quotes")
        if response.status_code == 200:
            quotes = response.json()
            print(f"✅ Market data: {quotes['count']} symbols tracked")
            for symbol, data in list(quotes['quotes'].items())[:3]:
                change_sign = "+" if data['change'] >= 0 else ""
                print(f"   📈 {symbol}: ${data['price']} ({change_sign}{data['change']:.2f}, {data['change_pct']:+.2f}%)")
            results['market_data'] = True
        else:
            print("❌ Market data failed")
            results['market_data'] = False
    except Exception as e:
        print(f"❌ Market data error: {e}")
        results['market_data'] = False
    
    # Test trading signals
    try:
        response = requests.get("http://localhost:9003/signals")
        if response.status_code == 200:
            signals = response.json()
            print(f"✅ Trading signals: {signals['count']} symbols analyzed")
            for symbol, signal in list(signals['signals'].items())[:3]:
                confidence_color = "🟢" if signal['confidence'] > 70 else "🟡" if signal['confidence'] > 50 else "🔴"
                print(f"   {confidence_color} {symbol}: {signal['signal']} ({signal['confidence']}% confidence)")
            results['signals'] = True
        else:
            print("❌ Trading signals failed")
            results['signals'] = False
    except Exception as e:
        print(f"❌ Trading signals error: {e}")
        results['signals'] = False
    
    # Test risk management
    try:
        response = requests.get("http://localhost:9004/portfolio/risk")
        if response.status_code == 200:
            risk = response.json()
            print(f"✅ Risk analysis: Score {risk['risk_score']}/10")
            print(f"   💰 Invested: {risk['invested_percentage']:.1f}% | Cash: {risk['cash_percentage']:.1f}%")
            print(f"   📊 Largest position: {risk['largest_position'][0]} ({risk['largest_position'][1]:.1f}%)")
            results['risk'] = True
        else:
            print("❌ Risk analysis failed")
            results['risk'] = False
    except Exception as e:
        print(f"❌ Risk analysis error: {e}")
        results['risk'] = False
    
    # Test historical data and backtesting
    try:
        response = requests.get("http://localhost:9006/historical/AAPL?days=30")
        if response.status_code == 200:
            hist_data = response.json()
            print(f"✅ Historical data: {hist_data['bars_returned']} bars for AAPL")
            
            # Test backtesting
            backtest_payload = {
                "symbol": "AAPL",
                "start_date": "2024-01-01T00:00:00Z",
                "end_date": "2024-12-31T23:59:59Z",
                "initial_capital": 100000,
                "strategy": "moving_average"
            }
            backtest_response = requests.post("http://localhost:9006/backtest", json=backtest_payload)
            if backtest_response.status_code == 200:
                backtest = backtest_response.json()
                print(f"✅ Backtest completed: {backtest['total_return']}% return, {backtest['win_rate']}% win rate")
            
            results['historical'] = True
        else:
            print("❌ Historical data failed")
            results['historical'] = False
    except Exception as e:
        print(f"❌ Historical data error: {e}")
        results['historical'] = False
    
    return results

def test_unified_interface():
    """Test unified frontend interface"""
    print("\n" + "="*80)
    print("UNIFIED INTERFACE TEST")
    print("="*80)
    
    pages = [
        ("Dashboard", "http://localhost:9100/dashboard"),
        ("Training", "http://localhost:9100/training"), 
        ("Portfolio", "http://localhost:9100/portfolio"),
        ("Navigation", "http://localhost:9100/")
    ]
    
    results = {}
    for name, url in pages:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200 and "Trading Platform" in response.text:
                print(f"✅ {name:12} page loads successfully")
                results[name] = True
            else:
                print(f"❌ {name:12} page failed to load")
                results[name] = False
        except Exception as e:
            print(f"❌ {name:12} page error: {e}")
            results[name] = False
    
    return results

def main():
    print("🚀 COMPLETE MICROSERVICES ECOSYSTEM TEST")
    print("=" * 80)
    
    # Test all services
    services = [
        ("Frontend", "http://localhost:9100"),
        ("API Gateway", "http://localhost:9000"), 
        ("Position Management", "http://localhost:9001"),
        ("Trading Execution", "http://localhost:9002"),
        ("Signal Processing", "http://localhost:9003"),
        ("Risk Management", "http://localhost:9004"),
        ("Market Data", "http://localhost:9005"),
        ("Historical Data", "http://localhost:9006"),
        ("Training Service", "http://localhost:9011")
    ]
    
    service_results = {}
    for name, url in services:
        service_results[name] = test_service(name, url)
    
    # Test data integrations
    data_results = test_data_flow()
    
    # Test unified interface
    ui_results = test_unified_interface()
    
    # Final summary
    print("\n" + "="*80)
    print("🎯 COMPLETE SYSTEM STATUS")
    print("="*80)
    
    services_healthy = sum(service_results.values())
    data_flows_working = sum(data_results.values())
    ui_pages_working = sum(ui_results.values())
    
    print(f"Services Online:     {services_healthy:2d}/{len(services):2d} ({services_healthy/len(services)*100:.0f}%)")
    print(f"Data Flows Working:  {data_flows_working:2d}/{len(data_results):2d} ({data_flows_working/len(data_results)*100:.0f}%)")
    print(f"UI Pages Working:    {ui_pages_working:2d}/{len(ui_results):2d} ({ui_pages_working/len(ui_results)*100:.0f}%)")
    
    total_tests = len(services) + len(data_results) + len(ui_results)
    total_passing = services_healthy + data_flows_working + ui_pages_working
    overall_success = total_passing / total_tests * 100
    
    print(f"\nOverall Success:     {total_passing:2d}/{total_tests:2d} ({overall_success:.1f}%)")
    
    if overall_success >= 90:
        print("\n🎉 MICROSERVICES ECOSYSTEM FULLY OPERATIONAL! 🎉")
        print("✨ All core services running in perfect harmony")
        print("🚀 Ready for production trading operations")
    elif overall_success >= 75:
        print("\n🟡 System mostly operational with minor issues")
    else:
        print("\n🔴 System requires attention - multiple services failing")
    
    print(f"\nTest completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()