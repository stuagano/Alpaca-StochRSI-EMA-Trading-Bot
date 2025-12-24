#!/usr/bin/env python3
"""
Check Learning Stats
View the current state of the swarm learning system and pattern analysis.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.swarm_learning_service import get_learning_service


def main():
    """Display learning statistics and pattern analysis."""
    print("=" * 60)
    print("🧠 Swarm Learning System Status")
    print("=" * 60)

    # Get the learning service
    service = get_learning_service()

    # Get stats
    stats = service.get_learning_stats()
    print("\n📊 Learning Statistics:")
    print(f"  Total trades processed: {stats['total_trades_processed']}")
    print(f"  Profitable trades: {stats['profitable_trades']}")
    print(f"  Losing trades: {stats['losing_trades']}")
    print(f"  Win rate: {stats['win_rate']:.1f}%")
    print(f"  Cumulative reward: {stats['cumulative_reward']:.2f}")
    print(f"  Last adaptation: {stats['last_adaptation'] or 'Never'}")

    # Get pattern analysis
    analysis = service.get_pattern_analysis()

    print("\n📈 Profitable Symbols:")
    if analysis['profitable_symbols']:
        for symbol, data in analysis['profitable_symbols'].items():
            print(f"  {symbol}: {data['count']} trades, ${data['total_pnl']:.2f} total P&L")
    else:
        print("  No profitable patterns recorded yet")

    print("\n📉 Losing Symbols:")
    if analysis['losing_symbols']:
        for symbol, data in analysis['losing_symbols'].items():
            print(f"  {symbol}: {data['count']} trades, ${data['total_pnl']:.2f} total P&L")
    else:
        print("  No losing patterns recorded yet")

    print("\n💡 Recommendations:")
    if analysis['recommendations']:
        for rec in analysis['recommendations']:
            print(f"  • {rec}")
    else:
        print("  • Continue trading to gather more data for analysis")

    # Check swarm memory
    swarm_memory_path = Path('.swarm/memory.db')
    if swarm_memory_path.exists():
        import sqlite3
        conn = sqlite3.connect(swarm_memory_path)
        cursor = conn.cursor()

        # Check learning history
        try:
            cursor.execute("SELECT COUNT(*) FROM learning_history")
            count = cursor.fetchone()[0]
            print(f"\n💾 Swarm Memory: {count} learning events stored")
        except:
            print("\n💾 Swarm Memory: No learning history table yet")

        conn.close()
    else:
        print("\n💾 Swarm Memory: Not initialized yet")

    print("\n" + "=" * 60)
    print("Run trading bot to start collecting learning data")
    print("=" * 60)


if __name__ == "__main__":
    main()
