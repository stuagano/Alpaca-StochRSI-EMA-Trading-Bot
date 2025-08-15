#!/usr/bin/env python3
"""Run the trading bot for a limited time and capture output."""

import sys
import os
import time
import signal
import subprocess
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_bot_with_timeout(duration_seconds=60):
    """Run the bot for a limited duration."""
    print(f"🚀 Starting Alpaca Trading Bot")
    print(f"⏱️  Will run for {duration_seconds} seconds")
    print("=" * 60)
    
    start_time = datetime.now()
    
    # Start the bot as a subprocess
    process = subprocess.Popen(
        [sys.executable, "main.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    output_lines = []
    
    try:
        # Read output for the specified duration
        end_time = time.time() + duration_seconds
        while time.time() < end_time:
            line = process.stdout.readline()
            if line:
                print(line.rstrip())
                output_lines.append(line.rstrip())
            
            # Check if process has ended
            if process.poll() is not None:
                print("\n⚠️  Bot exited early")
                break
                
            time.sleep(0.1)
    
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
    
    finally:
        # Terminate the process
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 EXECUTION SUMMARY")
    print("=" * 60)
    print(f"Duration: {(datetime.now() - start_time).total_seconds():.1f} seconds")
    print(f"Lines captured: {len(output_lines)}")
    
    # Analyze output
    errors = [line for line in output_lines if "ERROR" in line or "error" in line.lower()]
    warnings = [line for line in output_lines if "WARNING" in line or "warning" in line.lower()]
    trades = [line for line in output_lines if "trade" in line.lower() or "order" in line.lower()]
    
    print(f"\n🔴 Errors: {len(errors)}")
    for error in errors[:5]:  # Show first 5 errors
        print(f"  - {error[:100]}")
    
    print(f"\n⚠️  Warnings: {len(warnings)}")
    for warning in warnings[:5]:  # Show first 5 warnings
        print(f"  - {warning[:100]}")
    
    print(f"\n💹 Trade-related messages: {len(trades)}")
    for trade in trades[:5]:  # Show first 5 trade messages
        print(f"  - {trade[:100]}")
    
    # Save full output
    output_file = f"tests/bot_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    with open(output_file, 'w') as f:
        f.write('\n'.join(output_lines))
    print(f"\n💾 Full output saved to: {output_file}")
    
    return output_lines

if __name__ == "__main__":
    # Run for 60 seconds by default
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    run_bot_with_timeout(duration)