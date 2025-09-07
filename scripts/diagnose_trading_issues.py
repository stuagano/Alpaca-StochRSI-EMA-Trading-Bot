#!/usr/bin/env python3
"""
Comprehensive diagnostic script to identify trading bot issues
"""

import os
import sys
import json
import importlib.util

def check_environment():
    """Check environment setup"""
    print("\n" + "="*60)
    print("🔍 ENVIRONMENT DIAGNOSTICS")
    print("="*60)
    
    issues = []
    
    # Check Python version
    print(f"\n📦 Python Version: {sys.version}")
    if sys.version_info < (3, 7):
        issues.append("Python 3.7+ required")
    
    # Check required packages
    required_packages = [
        'alpaca_trade_api',
        'alpaca',
        'pandas',
        'numpy',
        'fastapi',
        'uvicorn',
        'websocket'
    ]
    
    print("\n📚 Package Status:")
    for package in required_packages:
        spec = importlib.util.find_spec(package.replace('-', '_'))
        if spec is None:
            print(f"  ❌ {package}: NOT INSTALLED")
            issues.append(f"Missing package: {package}")
        else:
            print(f"  ✅ {package}: Installed")
    
    return issues

def check_credentials():
    """Check API credentials"""
    print("\n" + "="*60)
    print("🔑 CREDENTIALS CHECK")
    print("="*60)
    
    issues = []
    
    # Check AUTH file
    auth_file = 'AUTH/authAlpaca.txt'
    if os.path.exists(auth_file):
        print(f"✅ AUTH file exists: {auth_file}")
        try:
            with open(auth_file, 'r') as f:
                auth_data = json.load(f)
                
            required_keys = ['APCA-API-KEY-ID', 'APCA-API-SECRET-KEY', 'BASE-URL']
            for key in required_keys:
                if key in auth_data:
                    if key == 'APCA-API-KEY-ID':
                        print(f"  ✅ {key}: {auth_data[key][:10]}...")
                    elif key == 'BASE-URL':
                        print(f"  ✅ {key}: {auth_data[key]}")
                    else:
                        print(f"  ✅ {key}: ***hidden***")
                else:
                    print(f"  ❌ {key}: MISSING")
                    issues.append(f"Missing credential: {key}")
                    
        except json.JSONDecodeError as e:
            issues.append(f"Invalid JSON in AUTH file: {e}")
        except Exception as e:
            issues.append(f"Error reading AUTH file: {e}")
    else:
        print(f"❌ AUTH file not found: {auth_file}")
        issues.append("AUTH/authAlpaca.txt file not found")
    
    # Check environment variables
    print("\n📝 Environment Variables:")
    env_vars = ['APCA_API_KEY_ID', 'APCA_API_SECRET_KEY', 'APCA_API_BASE_URL']
    for var in env_vars:
        value = os.getenv(var)
        if value:
            if 'KEY' in var:
                print(f"  ✅ {var}: {value[:10]}...")
            else:
                print(f"  ✅ {var}: {value}")
        else:
            print(f"  ⚠️ {var}: Not set (will use AUTH file)")
    
    return issues

def test_api_connection():
    """Test Alpaca API connection"""
    print("\n" + "="*60)
    print("🌐 API CONNECTION TEST")
    print("="*60)
    
    issues = []
    
    try:
        import alpaca_trade_api as tradeapi
        
        # Load credentials
        auth_file = 'AUTH/authAlpaca.txt'
        if os.path.exists(auth_file):
            with open(auth_file, 'r') as f:
                auth_data = json.load(f)
                api_key = auth_data.get('APCA-API-KEY-ID')
                api_secret = auth_data.get('APCA-API-SECRET-KEY')
                base_url = auth_data.get('BASE-URL', 'https://paper-api.alpaca.markets')
        else:
            api_key = os.getenv('APCA_API_KEY_ID')
            api_secret = os.getenv('APCA_API_SECRET_KEY')
            base_url = os.getenv('APCA_API_BASE_URL', 'https://paper-api.alpaca.markets')
        
        # Test connection
        api = tradeapi.REST(api_key, api_secret, base_url, api_version='v2')
        account = api.get_account()
        
        print(f"✅ API Connection Successful!")
        print(f"  Account Status: {account.status}")
        print(f"  Buying Power: ${float(account.buying_power):,.2f}")
        print(f"  Cash: ${float(account.cash):,.2f}")
        print(f"  Crypto Status: {account.crypto_status}")
        print(f"  Pattern Day Trader: {account.pattern_day_trader}")
        print(f"  Trading Blocked: {account.trading_blocked}")
        
        # Check account issues
        if account.crypto_status != 'ACTIVE':
            issues.append("Crypto trading not enabled - Enable in Alpaca dashboard")
        
        if account.trading_blocked:
            issues.append("Trading is blocked on this account")
        
        if float(account.buying_power) < 10:
            issues.append(f"Insufficient buying power (${float(account.buying_power):.2f} < $10 minimum)")
        
        # Test crypto assets
        print("\n🪙 Crypto Assets Test:")
        try:
            btc = api.get_asset('BTCUSD')
            print(f"  ✅ BTC/USD: Tradable={btc.tradable}, Status={btc.status}")
            
            eth = api.get_asset('ETHUSD')
            print(f"  ✅ ETH/USD: Tradable={eth.tradable}, Status={eth.status}")
            
        except Exception as e:
            issues.append(f"Cannot access crypto assets: {e}")
            print(f"  ❌ Error accessing crypto assets: {e}")
        
    except Exception as e:
        issues.append(f"API connection failed: {e}")
        print(f"❌ API Connection Failed: {e}")
    
    return issues

def check_services():
    """Check if services can be imported and initialized"""
    print("\n" + "="*60)
    print("⚙️ SERVICES CHECK")
    print("="*60)
    
    issues = []
    
    # Check unified trading service
    try:
        from unified_trading_service_with_frontend import get_alpaca_api, trading_state
        print("✅ Unified trading service can be imported")
    except ImportError as e:
        issues.append(f"Cannot import unified service: {e}")
        print(f"❌ Cannot import unified service: {e}")
    except Exception as e:
        issues.append(f"Error in unified service: {e}")
        print(f"❌ Error in unified service: {e}")
    
    # Check scalping strategy
    try:
        from strategies.crypto_scalping_strategy import CryptoDayTradingBot, CryptoVolatilityScanner
        print("✅ Crypto scalping strategy can be imported")
    except ImportError as e:
        issues.append(f"Cannot import scalping strategy: {e}")
        print(f"❌ Cannot import scalping strategy: {e}")
    except Exception as e:
        issues.append(f"Error in scalping strategy: {e}")
        print(f"❌ Error in scalping strategy: {e}")
    
    # Check new scalping bot
    try:
        from strategies.crypto_scalping_bot import AlpacaScalpingBot
        print("✅ New scalping bot can be imported")
    except ImportError as e:
        issues.append(f"Cannot import new scalping bot: {e}")
        print(f"❌ Cannot import new scalping bot: {e}")
    except Exception as e:
        issues.append(f"Error in new scalping bot: {e}")
        print(f"❌ Error in new scalping bot: {e}")
    
    return issues

def check_directories():
    """Check required directories"""
    print("\n" + "="*60)
    print("📁 DIRECTORY STRUCTURE")
    print("="*60)
    
    issues = []
    
    required_dirs = [
        'AUTH',
        'strategies',
        'frontend-shadcn',
        'logs',
        'config',
        'scripts'
    ]
    
    for dir_name in required_dirs:
        if os.path.exists(dir_name):
            print(f"✅ {dir_name}/")
        else:
            print(f"⚠️ {dir_name}/ (missing - will be created)")
            if dir_name == 'logs':
                os.makedirs(dir_name, exist_ok=True)
                print(f"  ✅ Created {dir_name}/")
    
    return issues

def main():
    """Run all diagnostics"""
    print("""
╔════════════════════════════════════════════════════════════╗
║         TRADING BOT DIAGNOSTIC REPORT                      ║
╚════════════════════════════════════════════════════════════╝
    """)
    
    all_issues = []
    
    # Run all checks
    all_issues.extend(check_directories())
    all_issues.extend(check_environment())
    all_issues.extend(check_credentials())
    all_issues.extend(test_api_connection())
    all_issues.extend(check_services())
    
    # Summary
    print("\n" + "="*60)
    print("📊 DIAGNOSTIC SUMMARY")
    print("="*60)
    
    if all_issues:
        print("\n⚠️ ISSUES FOUND:")
        for i, issue in enumerate(all_issues, 1):
            print(f"{i}. {issue}")
        
        print("\n🔧 RECOMMENDED FIXES:")
        
        if any("package" in issue.lower() for issue in all_issues):
            print("\n1. Install missing packages:")
            print("   pip install alpaca-trade-api alpaca-py pandas numpy fastapi uvicorn websocket-client")
        
        if any("crypto trading not enabled" in issue for issue in all_issues):
            print("\n2. Enable crypto trading:")
            print("   - Log into your Alpaca account")
            print("   - Go to account settings")
            print("   - Enable cryptocurrency trading")
        
        if any("insufficient buying power" in issue.lower() for issue in all_issues):
            print("\n3. Add funds to your paper trading account:")
            print("   - Alpaca paper accounts reset daily")
            print("   - Minimum $10 required for crypto trades")
        
    else:
        print("\n✅ ALL CHECKS PASSED!")
        print("\n🚀 Your trading bot is ready to run!")
        print("\n📝 Next steps:")
        print("1. Run unified service: python unified_trading_service_with_frontend.py")
        print("2. Run scalping bot: python scripts/run_scalping_bot.py --dry-run")
        print("3. Or use the new bot: python strategies/crypto_scalping_bot.py --dry-run")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    main()