#!/usr/bin/env python3
"""
After-Hours Trading Simulation
Realistic experience during non-market hours: pre-market, after-hours, overnight
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime, timedelta
import random
from typing import Dict, List

class AfterHoursSimulator:
    def __init__(self):
        self.signal_service = "http://localhost:9003"
        self.execution_service = "http://localhost:9002"
        self.current_session = "CLOSED"  # CLOSED, PRE_MARKET, REGULAR, AFTER_HOURS
        self.running = False
        
        # Market hours (ET)
        self.market_schedule = {
            "pre_market": {"start": "04:00", "end": "09:30"},
            "regular": {"start": "09:30", "end": "16:00"},
            "after_hours": {"start": "16:00", "end": "20:00"},
            "closed": {"start": "20:00", "end": "04:00"}
        }
        
        # Trading characteristics by session
        self.session_characteristics = {
            "PRE_MARKET": {
                "volume_factor": 0.3,  # 30% of regular volume
                "volatility_factor": 1.8,  # 80% higher volatility
                "spread_factor": 2.5,  # Wider spreads
                "trade_frequency": 0.4,  # 40% of regular frequency
                "description": "Pre-Market (4:00 AM - 9:30 AM ET)"
            },
            "AFTER_HOURS": {
                "volume_factor": 0.2,  # 20% of regular volume
                "volatility_factor": 2.2,  # 120% higher volatility
                "spread_factor": 3.0,  # Much wider spreads
                "trade_frequency": 0.25,  # 25% of regular frequency
                "description": "After-Hours (4:00 PM - 8:00 PM ET)"
            },
            "CLOSED": {
                "volume_factor": 0.05,  # 5% of regular volume
                "volatility_factor": 0.8,  # Lower volatility overnight
                "spread_factor": 5.0,  # Very wide spreads
                "trade_frequency": 0.1,  # 10% of regular frequency
                "description": "Market Closed (8:00 PM - 4:00 AM ET)"
            }
        }
        
        print("🌙 After-Hours Trading Simulator Initialized")

    def get_current_session(self):
        """Determine current trading session based on time"""
        # For simulation, we'll cycle through sessions quickly
        current_hour = datetime.now().hour
        
        if 4 <= current_hour < 9:
            return "PRE_MARKET"
        elif 9 <= current_hour < 16:
            return "REGULAR"
        elif 16 <= current_hour < 20:
            return "AFTER_HOURS"
        else:
            return "CLOSED"

    def simulate_session_change(self):
        """Simulate changing market sessions for demo"""
        sessions = ["CLOSED", "PRE_MARKET", "AFTER_HOURS", "CLOSED"]
        return random.choice(sessions)

    async def get_session_signals(self, session: str):
        """Get trading signals adjusted for current session"""
        try:
            async with aiohttp.ClientSession() as client:
                async with client.get(f"{self.signal_service}/hot-signals") as response:
                    if response.status == 200:
                        data = await response.json()
                        signals = data.get("hot_signals", [])
                        
                        # Adjust signals based on session characteristics
                        characteristics = self.session_characteristics.get(session, {})
                        adjusted_signals = []
                        
                        for signal in signals:
                            # Reduce signal frequency based on session
                            if random.random() < characteristics.get("trade_frequency", 1.0):
                                # Adjust confidence and volatility
                                signal["confidence"] *= characteristics.get("volatility_factor", 1.0) * 0.5
                                signal["confidence"] = min(95, max(20, signal["confidence"]))
                                
                                # Add session-specific metadata
                                signal["session"] = session
                                signal["session_note"] = self.get_session_note(session, signal["symbol"])
                                signal["liquidity"] = self.get_liquidity_rating(session)
                                
                                adjusted_signals.append(signal)
                        
                        return adjusted_signals[:5]  # Fewer opportunities in off-hours
                        
        except Exception as e:
            print(f"❌ Error getting session signals: {e}")
            return []

    def get_session_note(self, session: str, symbol: str):
        """Get session-specific trading notes"""
        notes = {
            "PRE_MARKET": [
                f"📈 {symbol} showing pre-market momentum",
                f"⚠️ {symbol} gapping up/down pre-market",
                f"📰 {symbol} reacting to overnight news",
                f"🌅 {symbol} early morning volatility"
            ],
            "AFTER_HOURS": [
                f"📊 {symbol} after-hours earnings reaction", 
                f"📺 {symbol} responding to after-hours news",
                f"🌆 {symbol} extended hours movement",
                f"⚡ {symbol} late session breakout"
            ],
            "CLOSED": [
                f"🌙 {symbol} overnight futures tracking",
                f"🌍 {symbol} following international markets",
                f"📱 {symbol} crypto correlation overnight",
                f"⏰ {symbol} holding for market open"
            ]
        }
        return random.choice(notes.get(session, [f"{symbol} session activity"]))

    def get_liquidity_rating(self, session: str):
        """Get liquidity rating for session"""
        ratings = {
            "PRE_MARKET": "LOW",
            "AFTER_HOURS": "VERY_LOW", 
            "CLOSED": "MINIMAL"
        }
        return ratings.get(session, "NORMAL")

    async def simulate_overnight_holds(self):
        """Simulate overnight position management"""
        print("\n🌙 OVERNIGHT POSITION SIMULATION")
        print("=" * 50)
        
        # Simulate positions held overnight
        overnight_positions = [
            {"symbol": "TSLA", "quantity": 100, "entry": 210.50, "current": 215.30},
            {"symbol": "NVDA", "quantity": 50, "entry": 475.20, "current": 478.90},
            {"symbol": "GME", "quantity": 200, "entry": 15.10, "current": 14.85},
        ]
        
        print("💼 Positions held through market close:")
        for pos in overnight_positions:
            pnl = (pos["current"] - pos["entry"]) * pos["quantity"]
            pnl_pct = ((pos["current"] - pos["entry"]) / pos["entry"]) * 100
            
            status = "🟢" if pnl > 0 else "🔴" if pnl < 0 else "🟡"
            print(f"   {status} {pos['symbol']}: {pos['quantity']} shares @ ${pos['entry']:.2f}")
            print(f"      Current: ${pos['current']:.2f} | P&L: ${pnl:+.2f} ({pnl_pct:+.1f}%)")
        
        print(f"\n⚠️  Overnight Risks:")
        print(f"   • Gap risk on market open")
        print(f"   • Limited liquidity if stop needed")
        print(f"   • International market impact")
        print(f"   • Earnings/news after-hours")

    async def simulate_premarket_activity(self):
        """Simulate pre-market trading activity"""
        print("\n🌅 PRE-MARKET TRADING SESSION (4:00 AM - 9:30 AM ET)")
        print("=" * 55)
        
        session_signals = await self.get_session_signals("PRE_MARKET")
        
        if session_signals:
            print("📊 Pre-Market Opportunities:")
            for i, signal in enumerate(session_signals[:3], 1):
                print(f"\n   {i}. {signal['symbol']} - {signal['signal']}")
                print(f"      💪 Confidence: {signal['confidence']:.1f}%")
                print(f"      📝 Note: {signal['session_note']}")
                print(f"      💧 Liquidity: {signal['liquidity']}")
                print(f"      ⚠️  Risk: Wider spreads, lower volume")
        
        print(f"\n🎯 Pre-Market Trading Tips:")
        print(f"   • Use limit orders only")
        print(f"   • Expect wider bid-ask spreads")
        print(f"   • Volume is 70% lower than regular hours")
        print(f"   • Watch for overnight news gaps")

    async def simulate_afterhours_activity(self):
        """Simulate after-hours trading activity"""
        print("\n🌆 AFTER-HOURS TRADING SESSION (4:00 PM - 8:00 PM ET)")
        print("=" * 57)
        
        session_signals = await self.get_session_signals("AFTER_HOURS")
        
        if session_signals:
            print("📊 After-Hours Opportunities:")
            for i, signal in enumerate(session_signals[:3], 1):
                print(f"\n   {i}. {signal['symbol']} - {signal['signal']}")
                print(f"      💪 Confidence: {signal['confidence']:.1f}%")
                print(f"      📝 Note: {signal['session_note']}")
                print(f"      💧 Liquidity: {signal['liquidity']}")
                print(f"      📈 After-hours premium/discount")
        
        # Simulate earnings reactions
        earnings_reactions = [
            {"symbol": "AAPL", "reaction": "+2.8%", "reason": "Beat earnings"},
            {"symbol": "MSFT", "reaction": "-1.4%", "reason": "Missed revenue"},
            {"symbol": "GOOGL", "reaction": "+4.2%", "reason": "Strong guidance"}
        ]
        
        print(f"\n📈 After-Hours Earnings Reactions:")
        for reaction in earnings_reactions:
            print(f"   {reaction['symbol']}: {reaction['reaction']} - {reaction['reason']}")
        
        print(f"\n🎯 After-Hours Trading Tips:")
        print(f"   • Even lower volume (80% less)")
        print(f"   • Earnings announcements cause volatility")
        print(f"   • News reactions can be extreme")
        print(f"   • Consider overnight hold risks")

    async def simulate_market_closed_period(self):
        """Simulate overnight market closed period"""
        print("\n🌙 MARKET CLOSED PERIOD (8:00 PM - 4:00 AM ET)")
        print("=" * 48)
        
        # International market updates
        international_markets = [
            {"market": "Nikkei 225", "change": "+0.8%", "impact": "Tech stocks positive"},
            {"market": "FTSE 100", "change": "-0.3%", "impact": "Energy sector weak"},
            {"market": "DAX", "change": "+1.2%", "impact": "Manufacturing strong"}
        ]
        
        print("🌍 International Markets (Overnight):")
        for market in international_markets:
            print(f"   {market['market']}: {market['change']} - {market['impact']}")
        
        # Overnight futures
        futures_data = [
            {"symbol": "ES", "description": "S&P 500 Futures", "change": "+0.4%"},
            {"symbol": "NQ", "description": "Nasdaq Futures", "change": "+0.7%"},
            {"symbol": "RTY", "description": "Russell 2000 Futures", "change": "-0.2%"}
        ]
        
        print(f"\n📊 Overnight Futures:")
        for future in futures_data:
            print(f"   {future['symbol']} ({future['description']}): {future['change']}")
        
        # Crypto correlation
        crypto_data = [
            {"symbol": "BTC", "change": "+2.1%", "impact": "Risk-on sentiment"},
            {"symbol": "ETH", "change": "+3.4%", "impact": "DeFi momentum"}
        ]
        
        print(f"\n₿ Crypto Markets (24/7):")
        for crypto in crypto_data:
            print(f"   {crypto['symbol']}: {crypto['change']} - {crypto['impact']}")
        
        print(f"\n💡 Overnight Strategy:")
        print(f"   • Monitor futures for market open direction")
        print(f"   • Watch international market trends")
        print(f"   • Prepare for gap opens")
        print(f"   • Set alerts for breaking news")

    async def simulate_session_transition(self, from_session: str, to_session: str):
        """Simulate transitioning between trading sessions"""
        print(f"\n⏰ SESSION TRANSITION: {from_session} → {to_session}")
        print("=" * 50)
        
        if to_session == "PRE_MARKET":
            print("🌅 Pre-market opening...")
            print("   • Early price discovery begins")
            print("   • Institutional order flow")
            print("   • Gap analysis vs. previous close")
            
        elif to_session == "AFTER_HOURS":
            print("🌆 After-hours session starting...")
            print("   • Earnings announcements expected")
            print("   • Reduced liquidity begins")
            print("   • Extended hours strategies activate")
            
        elif to_session == "CLOSED":
            print("🌙 Market closed for the night...")
            print("   • Overnight risk assessment")
            print("   • Position review required")
            print("   • International market watch")
        
        await asyncio.sleep(2)

    async def run_afterhours_experience(self, duration_minutes: int = 30):
        """Run complete after-hours experience simulation"""
        print("🌙 AFTER-HOURS TRADING EXPERIENCE SIMULATION")
        print("🕐 Simulating different market sessions")
        print("=" * 60)
        
        self.running = True
        end_time = datetime.now() + timedelta(minutes=duration_minutes)
        
        # Start with current session
        current_session = self.simulate_session_change()
        print(f"📍 Current Session: {current_session}")
        print(f"📝 {self.session_characteristics[current_session]['description']}")
        
        while self.running and datetime.now() < end_time:
            try:
                # Simulate different session activities
                if current_session == "PRE_MARKET":
                    await self.simulate_premarket_activity()
                elif current_session == "AFTER_HOURS":
                    await self.simulate_afterhours_activity()
                elif current_session == "CLOSED":
                    await self.simulate_market_closed_period()
                    await self.simulate_overnight_holds()
                
                # Wait and potentially change sessions
                await asyncio.sleep(10)
                
                # Randomly change sessions for demo
                if random.random() < 0.3:  # 30% chance to change session
                    new_session = self.simulate_session_change()
                    if new_session != current_session:
                        await self.simulate_session_transition(current_session, new_session)
                        current_session = new_session
                
            except KeyboardInterrupt:
                self.running = False
                break
            except Exception as e:
                print(f"❌ Simulation error: {e}")
                await asyncio.sleep(5)
        
        print("\n🏁 AFTER-HOURS SIMULATION COMPLETED")
        print("=" * 40)

    async def show_session_comparison(self):
        """Show comparison between different trading sessions"""
        print("\n📊 TRADING SESSION COMPARISON")
        print("=" * 50)
        
        for session, characteristics in self.session_characteristics.items():
            print(f"\n🕐 {characteristics['description']}")
            print(f"   📊 Volume: {characteristics['volume_factor']*100:.0f}% of regular hours")
            print(f"   📈 Volatility: {characteristics['volatility_factor']*100:.0f}% of regular hours")
            print(f"   💰 Spreads: {characteristics['spread_factor']:.1f}x wider")
            print(f"   🎯 Opportunities: {characteristics['trade_frequency']*100:.0f}% frequency")
        
        print(f"\n💡 Key Differences:")
        print(f"   • Lower liquidity = Higher slippage")
        print(f"   • Wider spreads = Higher transaction costs")
        print(f"   • Higher volatility = More opportunity & risk")
        print(f"   • Fewer participants = Less price discovery")

async def main():
    """Main function for after-hours simulation"""
    simulator = AfterHoursSimulator()
    
    print("🌙 AFTER-HOURS TRADING SIMULATION")
    print("Choose simulation mode:")
    print("1. Full after-hours experience (30 minutes)")
    print("2. Session comparison only")
    print("3. Quick demo (5 minutes)")
    
    try:
        choice = input("Enter choice (1-3): ").strip()
        
        if choice == "1":
            await simulator.run_afterhours_experience(30)
        elif choice == "2":
            await simulator.show_session_comparison()
        elif choice == "3":
            await simulator.run_afterhours_experience(5)
        else:
            print("Starting default experience...")
            await simulator.run_afterhours_experience(15)
            
    except KeyboardInterrupt:
        print("\n⚠️  Simulation interrupted by user")
        simulator.running = False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    
    print("\n👋 After-Hours Simulation Complete")

if __name__ == "__main__":
    asyncio.run(main())