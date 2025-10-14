#!/usr/bin/env python3
"""
Flask Dashboard Runner
Starts the Flask app and opens the dashboard in browser
"""

import os
import sys
import time
import webbrowser
import subprocess
import signal
from pathlib import Path

def find_free_port(start_port=5001):
    """Find a free port starting from start_port"""
    import socket
    for port in range(start_port, start_port + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('', port))
                return port
            except OSError:
                continue
    return None

def main():
    """Run Flask dashboard"""
    project_root = Path(__file__).parent
    port = find_free_port(5001)

    if not port:
        print("❌ Error: No free ports available")
        sys.exit(1)

    print("=" * 60)
    print("🚀 STARTING FLASK TRADING DASHBOARD")
    print("=" * 60)
    print(f"📍 Port: {port}")
    print(f"🌐 URL: http://localhost:{port}")
    print("=" * 60)

    # Start Flask app
    flask_cmd = [
        sys.executable,
        str(project_root / "backend" / "api" / "app.py")
    ]

    # Add port to environment
    env = os.environ.copy()
    env['FLASK_RUN_PORT'] = str(port)

    try:
        # Start Flask process
        print("\n📦 Starting Flask server...")
        process = subprocess.Popen(
            flask_cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )

        # Wait for server to start
        print("⏳ Waiting for server to start...")
        time.sleep(3)

        # Open browser
        dashboard_url = f"http://localhost:{port}/frontend/dashboard.html"
        print(f"\n🌐 Opening dashboard: {dashboard_url}")
        webbrowser.open(dashboard_url)

        print("\n✅ Dashboard is running!")
        print("\n" + "=" * 60)
        print("DASHBOARD FEATURES:")
        print("=" * 60)
        print("📊 Real-time position tracking")
        print("💰 P&L monitoring with charts")
        print("📈 Trading signals with RSI indicators")
        print("🔄 WebSocket updates")
        print("📥 Export data to CSV")
        print("=" * 60)
        print("\nPress Ctrl+C to stop the server\n")

        # Stream output
        for line in process.stdout:
            if line.strip():
                print(f"  {line.strip()}")

        # Wait for process
        process.wait()

    except KeyboardInterrupt:
        print("\n\n⏹ Shutting down Flask server...")
        process.terminate()
        time.sleep(1)
        process.kill()
        print("✅ Server stopped")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()