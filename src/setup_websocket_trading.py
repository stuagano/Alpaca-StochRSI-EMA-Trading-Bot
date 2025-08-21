#!/usr/bin/env python3
"""
Setup script for WebSocket-enabled trading bot.
This script integrates the new WebSocket functionality with the existing trading bot system.
"""

import sys
import os
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from flask import Flask
from src.enhanced_flask_app import create_enhanced_app
from src.websocket_trading_bot import create_websocket_trading_bot, upgrade_existing_bot_to_websocket
from src.trading_websocket_integration import setup_trading_websockets

logger = logging.getLogger(__name__)

def setup_websocket_trading_system():
    """
    Complete setup of the WebSocket-enabled trading system.
    This replaces the existing flask_app.py with enhanced WebSocket functionality.
    """
    
    print("🚀 Setting up WebSocket-enabled Trading Bot System...")
    
    try:
        # 1. Create enhanced Flask app with WebSocket integration
        print("📡 Initializing enhanced Flask app with WebSocket server...")
        enhanced_app = create_enhanced_app()
        
        # 2. Verify WebSocket service is running
        if enhanced_app.trading_websocket_service:
            stats = enhanced_app.trading_websocket_service.get_streaming_stats()
            print(f"✅ WebSocket service active: {stats['streaming_active']}")
            print(f"📊 Streaming interval: {stats['streaming_interval']}s")
            print(f"👥 Connected clients: {stats['connected_clients']}")
        else:
            print("❌ WebSocket service not initialized")
            return False
        
        # 3. Create WebSocket-enabled trading bot
        print("🤖 Creating WebSocket-enabled trading bot...")
        
        # Get data manager and create strategy
        data_manager = enhanced_app.data_manager
        
        # Import and create strategy (using existing strategy system)
        from main import get_strategy
        from config.unified_config import get_config
        
        config = get_config()
        strategy = get_strategy(config.strategy, config)
        
        # Create WebSocket trading bot
        websocket_bot = create_websocket_trading_bot(
            data_manager, 
            strategy, 
            enhanced_app.trading_websocket_service
        )
        
        print("✅ WebSocket trading bot created successfully")
        
        # 4. Configure performance optimizations
        print("⚡ Configuring performance optimizations...")
        
        # Set aggressive streaming for low latency
        websocket_bot.set_notification_throttle(0.1)  # 100ms throttle
        enhanced_app.trading_websocket_service.set_streaming_interval(0.5)  # 500ms updates
        
        print("🎯 Target latency: <50ms")
        print("📡 Notification throttle: 100ms")
        print("🔄 Streaming interval: 500ms")
        
        # 5. Display system information
        print("\n📋 System Configuration:")
        print(f"   Flask Host: 0.0.0.0:8765")
        print(f"   WebSocket Protocol: Socket.IO")
        print(f"   Compression: Enabled")
        print(f"   Auto-reconnection: Enabled (10 attempts)")
        print(f"   Heartbeat: 5s intervals")
        print(f"   Ping: 10s intervals")
        
        # 6. Available data streams
        print("\n📊 Available Data Streams:")
        print("   • market_data - Real-time price updates")
        print("   • positions - Position updates")
        print("   • signals - Trading signal notifications")
        print("   • orders - Order execution updates")
        print("   • account - Account information")
        print("   • system_health - System performance metrics")
        
        # 7. Display WebSocket endpoints
        print("\n🔗 WebSocket Management Endpoints:")
        print("   GET  /api/websocket/stats - Performance statistics")
        print("   GET  /api/websocket/performance - Detailed performance")
        print("   GET  /api/websocket/latency - Current latency stats")
        print("   GET  /api/websocket/clients - Connected clients info")
        print("   POST /api/websocket/start - Start streaming")
        print("   POST /api/websocket/stop - Stop streaming")
        print("   GET  /api/websocket/config - Get/set configuration")
        
        return enhanced_app, websocket_bot
        
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        logger.error(f"WebSocket setup error: {e}", exc_info=True)
        return None, None

def run_websocket_trading_system():
    """Run the complete WebSocket trading system"""
    
    print("🚀 Starting WebSocket Trading Bot System...\n")
    
    # Setup the system
    enhanced_app, websocket_bot = setup_websocket_trading_system()
    
    if not enhanced_app:
        print("❌ Failed to setup WebSocket trading system")
        return
    
    print("\n🎉 Setup completed successfully!")
    print("\n" + "="*60)
    print("🚀 WEBSOCKET TRADING BOT DASHBOARD")
    print("="*60)
    print("🌐 Dashboard URL: http://localhost:8765")
    print("📡 WebSocket URL: ws://localhost:8765")
    print("📊 Real-time updates: ENABLED")
    print("⚡ Latency target: <50ms")
    print("="*60)
    
    # Optional: Start the trading bot in background
    # Uncomment the following lines if you want to auto-start trading
    # print("\n🤖 Starting trading bot...")
    # import threading
    # bot_thread = threading.Thread(target=websocket_bot.run, daemon=True)
    # bot_thread.start()
    # print("✅ Trading bot started in background")
    
    try:
        # Run the enhanced Flask app
        enhanced_app.run(host='0.0.0.0', port=8765, debug=False)
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Shutting down WebSocket Trading Bot System...")
        enhanced_app.shutdown()
        print("✅ System shutdown complete")

def create_test_client_html():
    """Create a test HTML page for WebSocket functionality"""
    
    html_content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WebSocket Trading Bot Test Client</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.2/socket.io.js"></script>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .panel { background: white; border-radius: 8px; padding: 20px; margin: 10px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .status { padding: 10px; border-radius: 4px; margin: 10px 0; }
        .connected { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .disconnected { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .low-latency { color: #28a745; font-weight: bold; }
        .high-latency { color: #dc3545; font-weight: bold; }
        .controls { display: flex; gap: 10px; flex-wrap: wrap; }
        .btn { padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; }
        .btn-primary { background-color: #007bff; color: white; }
        .btn-success { background-color: #28a745; color: white; }
        .btn-warning { background-color: #ffc107; color: black; }
        .btn-danger { background-color: #dc3545; color: white; }
        .data-stream { background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 4px; padding: 10px; margin: 5px 0; font-family: monospace; }
        .latency-display { font-size: 24px; font-weight: bold; text-align: center; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; }
        .stat-item { text-align: center; padding: 10px; background-color: #e9ecef; border-radius: 4px; }
        input, select { padding: 8px; border: 1px solid #ccc; border-radius: 4px; }
        #logContainer { max-height: 300px; overflow-y: auto; background-color: #000; color: #00ff00; padding: 10px; font-family: monospace; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 WebSocket Trading Bot Test Client</h1>
        
        <!-- Connection Status -->
        <div class="panel">
            <h2>📡 Connection Status</h2>
            <div id="connectionStatus" class="status disconnected">Disconnected</div>
            <div id="latencyDisplay" class="latency-display">-- ms</div>
            <div class="controls">
                <button id="connectBtn" class="btn btn-success">Connect</button>
                <button id="disconnectBtn" class="btn btn-danger">Disconnect</button>
                <button id="pingBtn" class="btn btn-primary">Send Ping</button>
            </div>
        </div>
        
        <!-- Performance Stats -->
        <div class="panel">
            <h2>📊 Performance Statistics</h2>
            <div class="stats-grid">
                <div class="stat-item">
                    <div>Messages Received</div>
                    <div id="messagesCount">0</div>
                </div>
                <div class="stat-item">
                    <div>Average Latency</div>
                    <div id="avgLatency">-- ms</div>
                </div>
                <div class="stat-item">
                    <div>Peak Latency</div>
                    <div id="peakLatency">-- ms</div>
                </div>
                <div class="stat-item">
                    <div>Connection Uptime</div>
                    <div id="uptime">--</div>
                </div>
            </div>
        </div>
        
        <!-- Subscriptions -->
        <div class="panel">
            <h2>📋 Data Stream Subscriptions</h2>
            <div class="controls">
                <select id="streamType">
                    <option value="market_data">Market Data</option>
                    <option value="signals">Trading Signals</option>
                    <option value="positions">Positions</option>
                    <option value="orders">Orders</option>
                    <option value="account">Account Info</option>
                    <option value="system_health">System Health</option>
                </select>
                <input type="text" id="symbolInput" placeholder="Symbol (e.g., AAPL)" value="AAPL">
                <button id="subscribeBtn" class="btn btn-primary">Subscribe</button>
                <button id="unsubscribeBtn" class="btn btn-warning">Unsubscribe</button>
                <button id="subscribeAllBtn" class="btn btn-success">Subscribe to All</button>
            </div>
            <div id="subscriptionsList"></div>
        </div>
        
        <!-- Live Data Streams -->
        <div class="panel">
            <h2>📈 Live Data Streams</h2>
            <div style="max-height: 400px; overflow-y: auto;">
                <div id="dataStreams"></div>
            </div>
        </div>
        
        <!-- Debug Log -->
        <div class="panel">
            <h2>🔍 Debug Log</h2>
            <div id="logContainer"></div>
            <button id="clearLogBtn" class="btn btn-warning">Clear Log</button>
        </div>
    </div>

    <script src="/src/websocket_client.js"></script>
    <script>
        // Initialize WebSocket client
        let wsClient = null;
        let stats = {
            messagesReceived: 0,
            connectTime: null,
            subscriptions: new Set()
        };
        
        // DOM elements
        const connectionStatus = document.getElementById('connectionStatus');
        const latencyDisplay = document.getElementById('latencyDisplay');
        const logContainer = document.getElementById('logContainer');
        const dataStreams = document.getElementById('dataStreams');
        
        function log(message, type = 'info') {
            const timestamp = new Date().toLocaleTimeString();
            const color = type === 'error' ? '#ff6b6b' : type === 'success' ? '#51cf66' : '#00ff00';
            logContainer.innerHTML += `<div style="color: ${color}">[${timestamp}] ${message}</div>`;
            logContainer.scrollTop = logContainer.scrollHeight;
        }
        
        function updateConnectionStatus(connected) {
            connectionStatus.className = `status ${connected ? 'connected' : 'disconnected'}`;
            connectionStatus.textContent = connected ? 'Connected ✅' : 'Disconnected ❌';
            
            if (connected) {
                stats.connectTime = Date.now();
            }
        }
        
        function updateLatency(latency) {
            latencyDisplay.textContent = `${latency}ms`;
            latencyDisplay.className = `latency-display ${latency <= 50 ? 'low-latency' : 'high-latency'}`;
            document.getElementById('avgLatency').textContent = `${latency}ms`;
        }
        
        function updateStats() {
            document.getElementById('messagesCount').textContent = stats.messagesReceived;
            
            if (stats.connectTime) {
                const uptime = Math.floor((Date.now() - stats.connectTime) / 1000);
                document.getElementById('uptime').textContent = `${uptime}s`;
            }
        }
        
        function displayStreamData(data) {
            const streamDiv = document.createElement('div');
            streamDiv.className = 'data-stream';
            streamDiv.innerHTML = `
                <strong>${data.stream_type || 'Unknown'}</strong> - ${new Date(data.timestamp * 1000).toLocaleTimeString()}
                <br><pre>${JSON.stringify(data.data, null, 2)}</pre>
            `;
            
            dataStreams.insertBefore(streamDiv, dataStreams.firstChild);
            
            // Keep only last 10 items
            while (dataStreams.children.length > 10) {
                dataStreams.removeChild(dataStreams.lastChild);
            }
            
            stats.messagesReceived++;
            updateStats();
        }
        
        // Event handlers
        document.getElementById('connectBtn').onclick = () => {
            if (!wsClient) {
                log('Connecting to WebSocket server...', 'info');
                
                wsClient = new TradingBotWebSocketClient(window.location.origin, {
                    reconnectAttempts: 10,
                    reconnectDelay: 500,
                    latencyTarget: 50
                });
                
                // Setup event handlers
                wsClient.on('connected', () => {
                    log('Connected to WebSocket server', 'success');
                    updateConnectionStatus(true);
                });
                
                wsClient.on('disconnected', (data) => {
                    log(`Disconnected: ${data.reason}`, 'error');
                    updateConnectionStatus(false);
                });
                
                wsClient.on('latency_update', (data) => {
                    updateLatency(Math.round(data.current));
                    if (!data.withinTarget) {
                        log(`High latency detected: ${data.current}ms`, 'error');
                    }
                });
                
                wsClient.on('stream_data', (data) => {
                    displayStreamData(data);
                });
                
                wsClient.on('error', (error) => {
                    log(`WebSocket error: ${error.message || error}`, 'error');
                });
                
                wsClient.on('performance_stats', (stats) => {
                    log(`Performance: ${stats.messagesReceived} msgs, ${stats.avgLatency.toFixed(1)}ms avg`, 'info');
                });
            }
        };
        
        document.getElementById('disconnectBtn').onclick = () => {
            if (wsClient) {
                wsClient.disconnect();
                wsClient = null;
                updateConnectionStatus(false);
                log('Disconnected from server', 'info');
            }
        };
        
        document.getElementById('pingBtn').onclick = () => {
            if (wsClient && wsClient.isConnected) {
                wsClient.ping();
                log('Ping sent', 'info');
            }
        };
        
        document.getElementById('subscribeBtn').onclick = () => {
            if (wsClient && wsClient.isConnected) {
                const streamType = document.getElementById('streamType').value;
                const symbol = document.getElementById('symbolInput').value.toUpperCase();
                
                const symbols = symbol ? [symbol] : [];
                wsClient.subscribe([streamType], symbols);
                
                stats.subscriptions.add(`${streamType}:${symbol}`);
                log(`Subscribed to ${streamType} for ${symbol || 'all symbols'}`, 'success');
            }
        };
        
        document.getElementById('unsubscribeBtn').onclick = () => {
            if (wsClient && wsClient.isConnected) {
                const streamType = document.getElementById('streamType').value;
                const symbol = document.getElementById('symbolInput').value.toUpperCase();
                
                const symbols = symbol ? [symbol] : [];
                wsClient.unsubscribe([streamType], symbols);
                
                stats.subscriptions.delete(`${streamType}:${symbol}`);
                log(`Unsubscribed from ${streamType} for ${symbol || 'all symbols'}`, 'info');
            }
        };
        
        document.getElementById('subscribeAllBtn').onclick = () => {
            if (wsClient && wsClient.isConnected) {
                const symbol = document.getElementById('symbolInput').value.toUpperCase();
                const symbols = symbol ? [symbol] : [];
                
                ['market_data', 'signals', 'positions', 'orders', 'account'].forEach(streamType => {
                    wsClient.subscribe([streamType], symbols);
                    stats.subscriptions.add(`${streamType}:${symbol}`);
                });
                
                log(`Subscribed to all streams for ${symbol || 'all symbols'}`, 'success');
            }
        };
        
        document.getElementById('clearLogBtn').onclick = () => {
            logContainer.innerHTML = '';
        };
        
        // Auto-connect on page load
        setTimeout(() => {
            document.getElementById('connectBtn').click();
        }, 1000);
        
        // Update stats every second
        setInterval(updateStats, 1000);
    </script>
</body>
</html>'''
    
    # Write to templates directory
    templates_dir = project_root / 'templates'
    templates_dir.mkdir(exist_ok=True)
    
    test_client_path = templates_dir / 'websocket_test_client.html'
    with open(test_client_path, 'w') as f:
        f.write(html_content)
    
    print(f"✅ WebSocket test client created: {test_client_path}")
    print("🌐 Access at: http://localhost:8765/websocket_test_client.html")

def main():
    """Main function"""
    
    print("🚀 WebSocket Trading Bot Setup\n")
    print("Choose an option:")
    print("1. Run complete WebSocket trading system")
    print("2. Create test client HTML only")
    print("3. Setup and create test client")
    
    try:
        choice = input("\nEnter choice (1-3): ").strip()
        
        if choice == '1':
            run_websocket_trading_system()
        elif choice == '2':
            create_test_client_html()
            print("\n✅ Test client created successfully")
        elif choice == '3':
            create_test_client_html()
            print("\n🚀 Starting WebSocket trading system...\n")
            run_websocket_trading_system()
        else:
            print("❌ Invalid choice")
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Setup cancelled")
    except Exception as e:
        print(f"\n❌ Setup error: {e}")
        logger.error(f"Setup error: {e}", exc_info=True)

if __name__ == '__main__':
    main()