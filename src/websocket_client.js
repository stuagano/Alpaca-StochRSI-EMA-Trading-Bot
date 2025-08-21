/**
 * Enhanced WebSocket client for trading bot real-time data
 * Optimized for <100ms latency with automatic reconnection and compression support
 */

class TradingBotWebSocketClient {
    constructor(url = window.location.origin, options = {}) {
        this.url = url;
        this.options = {
            // Connection settings
            reconnectAttempts: 10,
            reconnectDelay: 500,
            maxReconnectDelay: 30000,
            connectionTimeout: 5000,
            
            // Performance settings
            heartbeatInterval: 5000,
            pingInterval: 10000,
            latencyTarget: 50, // Target <50ms latency
            
            // Compression settings
            compressionThreshold: 1024,
            
            // Custom options
            ...options
        };
        
        // Connection state
        this.socket = null;
        this.reconnectCount = 0;
        this.isConnected = false;
        this.connectionId = null;
        
        // Subscription management
        this.subscriptions = new Map();
        this.pendingSubscriptions = new Set();
        
        // Event handling
        this.eventHandlers = new Map();
        
        // Performance monitoring
        this.latencyHistory = [];
        this.lastPingTime = 0;
        this.performanceStats = {
            messagesReceived: 0,
            bytesReceived: 0,
            avgLatency: 0,
            peakLatency: 0,
            connectionUptime: 0,
            reconnections: 0
        };
        this.connectionStartTime = 0;
        
        // Data processing
        this.messageQueue = [];
        this.processingQueue = false;
        
        // Auto-connect
        this.connect();
        this.startPerformanceMonitoring();
    }
    
    /**
     * Establish WebSocket connection
     */
    connect() {
        try {
            console.log(`[WebSocket] Connecting to ${this.url}...`);
            
            this.socket = io(this.url, {
                transports: ['websocket', 'polling'],
                timeout: this.options.connectionTimeout,
                forceNew: true,
                upgrade: true,
                compression: true
            });
            
            this.setupEventHandlers();
            this.connectionStartTime = Date.now();
            
        } catch (error) {
            console.error('[WebSocket] Connection error:', error);
            this.handleReconnect();
        }
    }
    
    /**
     * Setup all WebSocket event handlers
     */
    setupEventHandlers() {
        // Connection events
        this.socket.on('connect', () => {
            console.log('[WebSocket] Connected successfully');
            this.isConnected = true;
            this.reconnectCount = 0;
            this.connectionStartTime = Date.now();
            
            // Resubscribe to all streams
            this.resubscribeAll();
            
            this.emit('connected', {\n                connectionId: this.connectionId,\n                reconnections: this.performanceStats.reconnections\n            });\n        });\n        \n        this.socket.on('disconnect', (reason) => {\n            console.log('[WebSocket] Disconnected:', reason);\n            this.isConnected = false;\n            \n            this.emit('disconnected', { reason });\n            \n            // Auto-reconnect for certain disconnect reasons\n            if (reason === 'io server disconnect' || reason === 'transport close') {\n                this.handleReconnect();\n            }\n        });\n        \n        this.socket.on('connect_error', (error) => {\n            console.error('[WebSocket] Connection error:', error);\n            this.handleReconnect();\n        });\n        \n        // Server events\n        this.socket.on('connected', (data) => {\n            this.connectionId = data.client_id;\n            console.log('[WebSocket] Server acknowledged connection:', this.connectionId);\n        });\n        \n        this.socket.on('heartbeat', (data) => {\n            this.emit('heartbeat', data);\n        });\n        \n        this.socket.on('pong', (data) => {\n            const latency = Date.now() - this.lastPingTime;\n            this.recordLatency(latency);\n            \n            this.emit('latency_update', {\n                current: latency,\n                average: this.performanceStats.avgLatency,\n                target: this.options.latencyTarget,\n                withinTarget: latency <= this.options.latencyTarget\n            });\n        });\n        \n        // Data stream events\n        this.socket.on('stream_data', (data) => {\n            this.processStreamData(data);\n        });\n        \n        this.socket.on('compressed_data', (data) => {\n            this.processCompressedData(data);\n        });\n        \n        // Subscription events\n        this.socket.on('subscription_confirmed', (data) => {\n            const key = this.getSubscriptionKey(data.stream_types, data.symbols);\n            this.pendingSubscriptions.delete(key);\n            console.log('[WebSocket] Subscription confirmed:', data);\n            this.emit('subscription_confirmed', data);\n        });\n        \n        this.socket.on('unsubscription_confirmed', (data) => {\n            const key = this.getSubscriptionKey(data.stream_types, data.symbols);\n            this.subscriptions.delete(key);\n            console.log('[WebSocket] Unsubscription confirmed:', data);\n            this.emit('unsubscription_confirmed', data);\n        });\n        \n        // Performance events\n        this.socket.on('performance_update', (stats) => {\n            this.emit('server_performance', stats);\n        });\n        \n        // Error handling\n        this.socket.on('error', (error) => {\n            console.error('[WebSocket] Server error:', error);\n            this.emit('error', error);\n        });\n    }\n    \n    /**\n     * Handle automatic reconnection with exponential backoff\n     */\n    handleReconnect() {\n        if (this.reconnectCount >= this.options.reconnectAttempts) {\n            console.error('[WebSocket] Max reconnection attempts reached');\n            this.emit('max_reconnects_reached');\n            return;\n        }\n        \n        const delay = Math.min(\n            this.options.reconnectDelay * Math.pow(2, this.reconnectCount),\n            this.options.maxReconnectDelay\n        );\n        \n        console.log(`[WebSocket] Reconnecting in ${delay}ms (attempt ${this.reconnectCount + 1}/${this.options.reconnectAttempts})`);\n        \n        setTimeout(() => {\n            this.reconnectCount++;\n            this.performanceStats.reconnections++;\n            this.connect();\n        }, delay);\n    }\n    \n    /**\n     * Subscribe to data streams\n     */\n    subscribe(streamTypes, symbols = []) {\n        if (!Array.isArray(streamTypes)) {\n            streamTypes = [streamTypes];\n        }\n        \n        const subscription = {\n            stream_types: streamTypes,\n            symbols: symbols\n        };\n        \n        const key = this.getSubscriptionKey(streamTypes, symbols);\n        this.subscriptions.set(key, subscription);\n        this.pendingSubscriptions.add(key);\n        \n        if (this.isConnected) {\n            this.socket.emit('subscribe', subscription);\n            console.log('[WebSocket] Subscribing to:', subscription);\n        }\n        \n        return key;\n    }\n    \n    /**\n     * Unsubscribe from data streams\n     */\n    unsubscribe(streamTypes, symbols = []) {\n        if (!Array.isArray(streamTypes)) {\n            streamTypes = [streamTypes];\n        }\n        \n        const subscription = {\n            stream_types: streamTypes,\n            symbols: symbols\n        };\n        \n        const key = this.getSubscriptionKey(streamTypes, symbols);\n        \n        if (this.isConnected) {\n            this.socket.emit('unsubscribe', subscription);\n            console.log('[WebSocket] Unsubscribing from:', subscription);\n        }\n        \n        return key;\n    }\n    \n    /**\n     * Resubscribe to all active streams\n     */\n    resubscribeAll() {\n        console.log(`[WebSocket] Resubscribing to ${this.subscriptions.size} streams`);\n        \n        this.subscriptions.forEach(subscription => {\n            this.socket.emit('subscribe', subscription);\n        });\n    }\n    \n    /**\n     * Process incoming stream data\n     */\n    processStreamData(data) {\n        this.performanceStats.messagesReceived++;\n        this.performanceStats.bytesReceived += JSON.stringify(data).length;\n        \n        // Add to processing queue for batch processing\n        this.messageQueue.push(data);\n        this.processMessageQueue();\n    }\n    \n    /**\n     * Process compressed data\n     */\n    processCompressedData(data) {\n        if (data.compressed) {\n            // In a real implementation, you would decompress the data here\n            console.log('[WebSocket] Received compressed data:', data.data.length, 'bytes');\n            this.emit('compressed_data', data);\n        }\n    }\n    \n    /**\n     * Process message queue in batches for better performance\n     */\n    async processMessageQueue() {\n        if (this.processingQueue || this.messageQueue.length === 0) {\n            return;\n        }\n        \n        this.processingQueue = true;\n        \n        while (this.messageQueue.length > 0) {\n            const data = this.messageQueue.shift();\n            \n            try {\n                // Emit based on stream type\n                if (data.stream_type) {\n                    this.emit(`stream_${data.stream_type}`, data);\n                    this.emit('stream_data', data);\n                    \n                    // Emit symbol-specific events\n                    if (data.symbols) {\n                        data.symbols.forEach(symbol => {\n                            this.emit(`symbol_${symbol}`, data);\n                        });\n                    }\n                }\n                \n            } catch (error) {\n                console.error('[WebSocket] Error processing message:', error);\n            }\n            \n            // Yield control periodically to prevent blocking\n            if (this.messageQueue.length > 10) {\n                await new Promise(resolve => setTimeout(resolve, 0));\n            }\n        }\n        \n        this.processingQueue = false;\n    }\n    \n    /**\n     * Send ping to measure latency\n     */\n    ping() {\n        if (this.isConnected) {\n            this.lastPingTime = Date.now();\n            this.socket.emit('ping', { timestamp: this.lastPingTime / 1000 });\n        }\n    }\n    \n    /**\n     * Record latency measurement\n     */\n    recordLatency(latency) {\n        this.latencyHistory.push(latency);\n        if (this.latencyHistory.length > 100) {\n            this.latencyHistory.shift();\n        }\n        \n        this.performanceStats.avgLatency = \n            this.latencyHistory.reduce((a, b) => a + b, 0) / this.latencyHistory.length;\n        this.performanceStats.peakLatency = Math.max(...this.latencyHistory);\n    }\n    \n    /**\n     * Start performance monitoring\n     */\n    startPerformanceMonitoring() {\n        // Send ping every interval\n        setInterval(() => {\n            if (this.isConnected) {\n                this.ping();\n            }\n        }, this.options.pingInterval);\n        \n        // Update connection uptime\n        setInterval(() => {\n            if (this.isConnected && this.connectionStartTime) {\n                this.performanceStats.connectionUptime = Date.now() - this.connectionStartTime;\n            }\n        }, 1000);\n        \n        // Emit performance stats periodically\n        setInterval(() => {\n            this.emit('performance_stats', this.getPerformanceStats());\n        }, 10000); // Every 10 seconds\n    }\n    \n    /**\n     * Get current performance statistics\n     */\n    getPerformanceStats() {\n        return {\n            ...this.performanceStats,\n            isConnected: this.isConnected,\n            subscriptions: this.subscriptions.size,\n            latencyHistory: [...this.latencyHistory],\n            connectionId: this.connectionId\n        };\n    }\n    \n    /**\n     * Get subscription key for tracking\n     */\n    getSubscriptionKey(streamTypes, symbols) {\n        return JSON.stringify({ streamTypes: streamTypes.sort(), symbols: symbols.sort() });\n    }\n    \n    /**\n     * Add event listener\n     */\n    on(event, handler) {\n        if (!this.eventHandlers.has(event)) {\n            this.eventHandlers.set(event, new Set());\n        }\n        this.eventHandlers.get(event).add(handler);\n    }\n    \n    /**\n     * Remove event listener\n     */\n    off(event, handler) {\n        if (this.eventHandlers.has(event)) {\n            this.eventHandlers.get(event).delete(handler);\n            if (this.eventHandlers.get(event).size === 0) {\n                this.eventHandlers.delete(event);\n            }\n        }\n    }\n    \n    /**\n     * Emit event to all listeners\n     */\n    emit(event, data = null) {\n        if (this.eventHandlers.has(event)) {\n            this.eventHandlers.get(event).forEach(handler => {\n                try {\n                    handler(data);\n                } catch (error) {\n                    console.error(`[WebSocket] Event handler error for '${event}':`, error);\n                }\n            });\n        }\n    }\n    \n    /**\n     * Disconnect from server\n     */\n    disconnect() {\n        if (this.socket) {\n            this.socket.disconnect();\n            this.isConnected = false;\n        }\n    }\n    \n    /**\n     * Get connection status\n     */\n    getConnectionStatus() {\n        return {\n            connected: this.isConnected,\n            connectionId: this.connectionId,\n            reconnectCount: this.reconnectCount,\n            uptime: this.performanceStats.connectionUptime\n        };\n    }\n}\n\n/**\n * Convenient wrapper for common trading data subscriptions\n */\nclass TradingDataSubscriber {\n    constructor(wsClient) {\n        this.wsClient = wsClient;\n        this.subscriptions = new Map();\n    }\n    \n    /**\n     * Subscribe to market data for symbols\n     */\n    subscribeToMarketData(symbols) {\n        const key = this.wsClient.subscribe(['market_data'], symbols);\n        this.subscriptions.set('market_data', key);\n        return key;\n    }\n    \n    /**\n     * Subscribe to trading signals for symbols\n     */\n    subscribeToSignals(symbols) {\n        const key = this.wsClient.subscribe(['signals'], symbols);\n        this.subscriptions.set('signals', key);\n        return key;\n    }\n    \n    /**\n     * Subscribe to position updates\n     */\n    subscribeToPositions() {\n        const key = this.wsClient.subscribe(['positions']);\n        this.subscriptions.set('positions', key);\n        return key;\n    }\n    \n    /**\n     * Subscribe to order updates\n     */\n    subscribeToOrders() {\n        const key = this.wsClient.subscribe(['orders']);\n        this.subscriptions.set('orders', key);\n        return key;\n    }\n    \n    /**\n     * Subscribe to account updates\n     */\n    subscribeToAccount() {\n        const key = this.wsClient.subscribe(['account']);\n        this.subscriptions.set('account', key);\n        return key;\n    }\n    \n    /**\n     * Subscribe to all trading data\n     */\n    subscribeToAll(symbols = []) {\n        this.subscribeToMarketData(symbols);\n        this.subscribeToSignals(symbols);\n        this.subscribeToPositions();\n        this.subscribeToOrders();\n        this.subscribeToAccount();\n    }\n    \n    /**\n     * Unsubscribe from all\n     */\n    unsubscribeFromAll() {\n        this.subscriptions.forEach((key, type) => {\n            // This would need the original parameters to unsubscribe properly\n            // For now, we'll just clear our tracking\n        });\n        this.subscriptions.clear();\n    }\n}\n\n// Export for module systems\nif (typeof module !== 'undefined' && module.exports) {\n    module.exports = { TradingBotWebSocketClient, TradingDataSubscriber };\n}\n\n// Global assignment for direct HTML inclusion\nif (typeof window !== 'undefined') {\n    window.TradingBotWebSocketClient = TradingBotWebSocketClient;\n    window.TradingDataSubscriber = TradingDataSubscriber;\n}\n\n/**\n * Usage Examples:\n * \n * // Basic usage\n * const wsClient = new TradingBotWebSocketClient();\n * wsClient.subscribe(['market_data', 'signals'], ['AAPL', 'MSFT']);\n * \n * // Listen for data\n * wsClient.on('stream_market_data', (data) => {\n *     console.log('Market data:', data);\n * });\n * \n * // Listen for specific symbol\n * wsClient.on('symbol_AAPL', (data) => {\n *     console.log('AAPL data:', data);\n * });\n * \n * // Monitor performance\n * wsClient.on('latency_update', (stats) => {\n *     if (!stats.withinTarget) {\n *         console.warn('High latency detected:', stats.current, 'ms');\n *     }\n * });\n * \n * // Using the subscriber helper\n * const subscriber = new TradingDataSubscriber(wsClient);\n * subscriber.subscribeToAll(['AAPL', 'MSFT', 'GOOGL']);\n */"