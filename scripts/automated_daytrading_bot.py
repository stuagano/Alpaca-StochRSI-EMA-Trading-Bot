#!/usr/bin/env python3
"""
Automated Day Trading Bot
Connects signal processing to execution engine for high-frequency trading
Executes hundreds of trades per session with rapid profit-taking
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List
import random

class DayTradingBot:
    def __init__(self):
        self.signal_service = "http://localhost:9003"
        self.execution_service = "http://localhost:9002" 
        self.running = False
        self.trades_executed = 0
        self.target_trades_per_hour = 50  # Aggressive trading
        self.min_confidence = 70
        self.min_urgency = ["HIGH", "CRITICAL"]
        self.max_position_time = 300  # 5 minutes max hold time
        
        # Performance tracking
        self.successful_trades = 0
        self.failed_trades = 0
        self.total_profit = 0.0
        self.session_start = None
        
        print("🚀 Day Trading Bot Initialized")
        print(f"📊 Target: {self.target_trades_per_hour} trades/hour")
        print(f"⚡ Min confidence: {self.min_confidence}%")
        print(f"⏱️  Max hold time: {self.max_position_time}s")

    async def get_hot_signals(self):
        """Get the hottest trading signals"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.signal_service}/hot-signals") as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("hot_signals", [])
                    return []
        except Exception as e:
            print(f"❌ Error getting signals: {e}")
            return []

    async def get_scalping_opportunities(self):
        """Get immediate scalping opportunities"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.signal_service}/scalping-opportunities") as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("scalping_opportunities", [])
                    return []
        except Exception as e:
            print(f"❌ Error getting scalping opportunities: {e}")
            return []

    async def execute_signal(self, signal: Dict):
        """Execute a trading signal"""
        try:
            payload = {
                "symbol": signal["symbol"],
                "signal": signal["signal"],
                "confidence": signal["confidence"],
                "urgency": signal["urgency"],
                "entry_price": signal["entry_price"]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.execution_service}/execute/signal",
                    params=payload
                ) as response:
                    result = await response.json()
                    
                    if result.get("success"):
                        self.trades_executed += 1
                        self.successful_trades += 1
                        
                        print(f"✅ TRADE #{self.trades_executed}: {signal['signal']} {signal['symbol']} @ ${signal['entry_price']:.2f}")
                        print(f"   📊 Confidence: {signal['confidence']}% | Urgency: {signal['urgency']}")
                        print(f"   💰 Expected: {signal.get('expected_move', 0)}% | Stop: ${signal.get('stop_loss', 0):.2f}")
                        
                        return True
                    else:
                        self.failed_trades += 1
                        print(f"❌ Trade failed: {result.get('message', 'Unknown error')}")
                        return False
                        
        except Exception as e:
            self.failed_trades += 1
            print(f"❌ Execution error: {e}")
            return False

    async def scalp_opportunity(self, opportunity: Dict):
        """Execute scalping opportunity"""
        try:
            # Determine direction based on VWAP deviation
            if opportunity["vwap_deviation"] > 0.05:
                signal_direction = "SELL"  # Price above VWAP, sell
            elif opportunity["vwap_deviation"] < -0.05:
                signal_direction = "BUY"   # Price below VWAP, buy
            else:
                return False
            
            payload = {
                "symbol": opportunity["symbol"],
                "current_price": opportunity["current_price"],
                "signal_direction": signal_direction
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.execution_service}/orders/scalp",
                    params=payload
                ) as response:
                    result = await response.json()
                    
                    if result.get("success"):
                        self.trades_executed += 1
                        self.successful_trades += 1
                        
                        print(f"⚡ SCALP #{self.trades_executed}: {signal_direction} {opportunity['symbol']} @ ${opportunity['current_price']:.2f}")
                        print(f"   📈 VWAP Dev: {opportunity['vwap_deviation']}% | Expected: ${opportunity['expected_profit']:.2f}")
                        
                        return True
                    else:
                        print(f"❌ Scalp failed: {result.get('message', 'Unknown error')}")
                        return False
                        
        except Exception as e:
            print(f"❌ Scalping error: {e}")
            return False

    async def monitor_performance(self):
        """Monitor trading performance"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.execution_service}/performance") as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        print(f"\n📊 PERFORMANCE UPDATE:")
                        print(f"   🎯 Total Trades: {data.get('total_trades', 0)}")
                        print(f"   📈 Win Rate: {data.get('win_rate', 0)}%")
                        print(f"   💰 Daily P&L: ${data.get('daily_pnl', 0):.2f}")
                        print(f"   💵 Net P&L: ${data.get('net_pnl', 0):.2f}")
                        print(f"   📊 Trades/Hour: {data.get('trades_per_hour', 0)}")
                        print(f"   🏃 Day Trades: {data.get('day_trades', 0)}")
                        
                        return data
                        
        except Exception as e:
            print(f"❌ Performance monitoring error: {e}")
            return {}

    async def get_account_status(self):
        """Get account status"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.execution_service}/account") as response:
                    if response.status == 200:
                        return await response.json()
        except Exception as e:
            print(f"❌ Account status error: {e}")
        return {}

    def calculate_session_stats(self):
        """Calculate session statistics"""
        if not self.session_start:
            return
        
        session_time = (datetime.utcnow() - self.session_start).total_seconds() / 3600  # hours
        trades_per_hour = self.trades_executed / max(session_time, 0.1)
        win_rate = (self.successful_trades / max(self.trades_executed, 1)) * 100
        
        print(f"\n📈 SESSION STATISTICS:")
        print(f"   ⏱️  Session Time: {session_time:.1f} hours")
        print(f"   🎯 Trades Executed: {self.trades_executed}")
        print(f"   ✅ Successful: {self.successful_trades}")
        print(f"   ❌ Failed: {self.failed_trades}")
        print(f"   📊 Win Rate: {win_rate:.1f}%")
        print(f"   ⚡ Trades/Hour: {trades_per_hour:.1f}")

    async def trading_loop(self):
        """Main trading loop"""
        print("\n🎯 STARTING AUTOMATED DAY TRADING SESSION")
        print("=" * 60)
        
        self.session_start = datetime.utcnow()
        trade_interval = 3600 / self.target_trades_per_hour  # seconds between trades
        
        while self.running:
            cycle_start = time.time()
            
            try:
                # Get account status
                account = await self.get_account_status()
                if account.get("day_trades_used", 0) >= 3:
                    print("⚠️  Day trade limit reached, switching to position trading")
                    await asyncio.sleep(30)
                    continue
                
                # Check for hot signals
                hot_signals = await self.get_hot_signals()
                
                for signal in hot_signals[:3]:  # Process top 3 signals
                    if (signal.get("confidence", 0) >= self.min_confidence and 
                        signal.get("urgency") in self.min_urgency):
                        
                        success = await self.execute_signal(signal)
                        if success:
                            # Brief pause between trades
                            await asyncio.sleep(1)
                
                # Check for scalping opportunities
                scalping_ops = await self.get_scalping_opportunities()
                
                for opportunity in scalping_ops[:2]:  # Process top 2 scalping opportunities
                    if opportunity.get("expected_profit", 0) > 0.1:  # Minimum 0.1% expected profit
                        success = await self.scalp_opportunity(opportunity)
                        if success:
                            await asyncio.sleep(1)
                
                # Performance monitoring every 10th cycle
                if self.trades_executed % 10 == 0 and self.trades_executed > 0:
                    await self.monitor_performance()
                
                # Calculate time to next cycle
                cycle_time = time.time() - cycle_start
                sleep_time = max(0, trade_interval - cycle_time)
                
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                    
            except Exception as e:
                print(f"❌ Trading loop error: {e}")
                await asyncio.sleep(5)

    async def start_trading(self, duration_hours: float = 6.5):
        """Start automated trading session"""
        self.running = True
        
        # Start trading loop
        trading_task = asyncio.create_task(self.trading_loop())
        
        # Run for specified duration (market hours)
        print(f"🕐 Trading session will run for {duration_hours} hours")
        await asyncio.sleep(duration_hours * 3600)
        
        # Stop trading
        self.running = False
        trading_task.cancel()
        
        print("\n🏁 TRADING SESSION COMPLETED")
        print("=" * 60)
        
        # Final statistics
        self.calculate_session_stats()
        await self.monitor_performance()

    async def aggressive_scalping_mode(self, duration_minutes: int = 60):
        """Ultra-aggressive scalping mode for maximum trades"""
        print(f"\n⚡ ENTERING AGGRESSIVE SCALPING MODE - {duration_minutes} MINUTES")
        print("🎯 Target: Maximum trades with rapid profit-taking")
        
        self.running = True
        end_time = datetime.utcnow() + timedelta(minutes=duration_minutes)
        
        while self.running and datetime.utcnow() < end_time:
            try:
                # Get all scalping opportunities
                opportunities = await self.get_scalping_opportunities()
                
                # Execute multiple opportunities in parallel
                tasks = []
                for opp in opportunities[:5]:  # Top 5 opportunities
                    if opp.get("expected_profit", 0) > 0.05:  # 0.05% minimum
                        tasks.append(self.scalp_opportunity(opp))
                
                if tasks:
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    successful = sum(1 for r in results if r is True)
                    print(f"⚡ Scalping burst: {successful}/{len(tasks)} successful")
                
                # Very short pause - ultra high frequency
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"❌ Aggressive scalping error: {e}")
                await asyncio.sleep(1)
        
        self.running = False
        print("⚡ AGGRESSIVE SCALPING MODE COMPLETED")
        self.calculate_session_stats()

async def main():
    """Main function"""
    bot = DayTradingBot()
    
    print("🤖 AUTOMATED DAY TRADING BOT")
    print("Choose trading mode:")
    print("1. Standard day trading (6.5 hours)")
    print("2. Aggressive scalping (1 hour)")
    print("3. Quick test (5 minutes)")
    
    try:
        choice = input("Enter choice (1-3): ").strip()
        
        if choice == "1":
            await bot.start_trading(6.5)
        elif choice == "2":
            await bot.aggressive_scalping_mode(60)
        elif choice == "3":
            await bot.aggressive_scalping_mode(5)
        else:
            print("Starting default 15-minute test session...")
            await bot.aggressive_scalping_mode(15)
            
    except KeyboardInterrupt:
        print("\n⚠️  Trading session interrupted by user")
        bot.running = False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    
    print("\n👋 Day Trading Bot Shutdown Complete")

if __name__ == "__main__":
    asyncio.run(main())