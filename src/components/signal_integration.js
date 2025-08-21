/**
 * Signal Integration Layer
 * ========================
 * 
 * Integrates the signal visualization with:
 * - Existing WebSocket streaming
 * - Trading bot signal generation
 * - Real-time market data
 * - Performance tracking
 */

class SignalIntegration {
    constructor(options = {}) {
        this.config = {
            websocketUrl: window.location.origin,
            autoConnect: true,
            enableRealTimeUpdates: true,
            signalUpdateInterval: 1000,
            performanceUpdateInterval: 5000,
            maxSignalHistory: 1000,
            ...options
        };
        
        // Core components
        this.socket = null;
        this.signalViz = null;
        this.marketData = new Map();
        this.activeSymbols = new Set();
        this.signalProcessors = new Map();
        this.performanceTracker = new PerformanceTracker();
        
        // State management
        this.isConnected = false;
        this.isStreaming = false;
        this.lastUpdate = 0;
        this.updateCount = 0;
        
        // Signal processing
        this.signalQueue = [];
        this.processingQueue = false;
        
        this.initialize();
    }
    
    initialize() {
        this.setupWebSocketConnection();
        this.initializeSignalProcessors();
        this.startSignalProcessing();
        
        console.log('🔌 Signal Integration initialized');
    }
    
    setupWebSocketConnection() {
        if (!this.config.autoConnect) return;
        
        try {
            this.socket = io(this.config.websocketUrl, {
                transports: ['websocket', 'polling'],
                timeout: 20000,
                forceNew: true
            });
            
            this.socket.on('connect', () => {
                this.isConnected = true;
                console.log('✅ Signal integration connected to WebSocket');
                this.onWebSocketConnect();
            });
            
            this.socket.on('disconnect', (reason) => {
                this.isConnected = false;
                console.log('❌ Signal integration disconnected:', reason);
                this.onWebSocketDisconnect(reason);
            });
            
            this.socket.on('real_time_update', (data) => {
                this.handleRealTimeUpdate(data);
            });
            
            this.socket.on('signal_update', (data) => {
                this.handleSignalUpdate(data);
            });
            
            this.socket.on('market_data', (data) => {
                this.handleMarketDataUpdate(data);
            });
            
            this.socket.on('position_update', (data) => {
                this.handlePositionUpdate(data);
            });
            
            this.socket.on('order_update', (data) => {
                this.handleOrderUpdate(data);
            });
            
        } catch (error) {
            console.error('❌ Error setting up WebSocket connection:', error);
        }
    }
    
    initializeSignalProcessors() {
        // StochRSI signal processor
        this.signalProcessors.set('stochRSI', new StochRSIProcessor());
        
        // EMA signal processor  
        this.signalProcessors.set('ema', new EMAProcessor());
        
        // SuperTrend signal processor
        this.signalProcessors.set('supertrend', new SuperTrendProcessor());
        
        // Volume signal processor
        this.signalProcessors.set('volume', new VolumeProcessor());
        
        // Composite signal processor
        this.signalProcessors.set('composite', new CompositeProcessor(this.signalProcessors));
    }
    
    // Connect signal visualization component
    connectSignalVisualization(signalVisualizationInstance) {
        this.signalViz = signalVisualizationInstance;
        
        // Set up bidirectional communication
        this.signalViz.onSignalRequest = (symbol) => this.requestSignalUpdate(symbol);
        this.signalViz.onPerformanceRequest = () => this.getPerformanceData();
        
        console.log('🎯 Signal visualization connected');
    }
    
    // WebSocket event handlers
    onWebSocketConnect() {
        // Start streaming when connected
        if (this.config.enableRealTimeUpdates) {
            this.socket.emit('start_streaming', {
                interval: this.config.signalUpdateInterval / 1000
            });
            this.isStreaming = true;
        }
        
        // Request initial signal data
        this.requestInitialData();
    }
    
    onWebSocketDisconnect(reason) {
        this.isStreaming = false;
        
        // Attempt reconnection after delay
        setTimeout(() => {
            if (!this.isConnected) {
                console.log('🔄 Attempting to reconnect...');
                this.socket.connect();
            }
        }, 5000);
    }
    
    // Real-time data handlers
    handleRealTimeUpdate(data) {
        this.lastUpdate = Date.now();
        this.updateCount++;
        
        try {
            // Process ticker signals
            if (data.ticker_signals) {
                Object.entries(data.ticker_signals).forEach(([symbol, signalData]) => {
                    this.processSignalData(symbol, signalData);
                });
            }
            
            // Process market data
            if (data.ticker_prices) {
                Object.entries(data.ticker_prices).forEach(([symbol, price]) => {
                    this.updateMarketData(symbol, { price, timestamp: Date.now() });
                });
            }
            
            // Process positions
            if (data.positions) {
                this.processPositionUpdates(data.positions);
            }
            
        } catch (error) {
            console.error('❌ Error handling real-time update:', error);
        }
    }
    
    handleSignalUpdate(data) {
        const signal = this.parseSignalData(data);
        if (signal) {
            this.queueSignal(signal);
        }
    }
    
    handleMarketDataUpdate(data) {
        if (Array.isArray(data.updates)) {
            data.updates.forEach(update => {
                this.updateMarketData(update.symbol, update);
            });
        } else {
            this.updateMarketData(data.symbol, data);
        }
    }
    
    handlePositionUpdate(data) {
        this.processPositionUpdates(Array.isArray(data) ? data : [data]);
    }
    
    handleOrderUpdate(data) {
        this.processOrderUpdate(data);
    }
    
    // Signal processing methods
    processSignalData(symbol, signalData) {
        try {
            const processedSignals = [];
            
            // Process each signal type
            for (const [signalType, processor] of this.signalProcessors.entries()) {
                if (signalType === 'composite') continue; // Process composite signals separately
                
                const signal = processor.process(symbol, signalData, this.getMarketContext(symbol));
                if (signal) {
                    processedSignals.push(signal);
                }
            }
            
            // Generate composite signal
            if (processedSignals.length > 0) {
                const compositeProcessor = this.signalProcessors.get('composite');
                const compositeSignal = compositeProcessor.process(symbol, processedSignals, this.getMarketContext(symbol));
                
                if (compositeSignal) {
                    this.queueSignal(compositeSignal);
                }
            }
            
            // Queue individual signals
            processedSignals.forEach(signal => this.queueSignal(signal));
            
        } catch (error) {
            console.error(`❌ Error processing signal data for ${symbol}:`, error);
        }
    }
    
    parseSignalData(data) {
        try {
            return {
                id: `signal_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
                timestamp: data.timestamp || Date.now(),
                symbol: data.symbol,
                type: this.determineSignalType(data),
                strength: this.calculateSignalStrength(data),
                price: data.price || this.getLatestPrice(data.symbol),
                reason: this.generateSignalReason(data),
                indicators: data.indicators || {},
                metadata: {
                    source: 'websocket',
                    confidence: data.confidence || 0.5,
                    strategies: this.identifyStrategies(data)
                }
            };
        } catch (error) {
            console.error('❌ Error parsing signal data:', error);
            return null;
        }
    }
    
    determineSignalType(data) {
        // Analyze signal data to determine type
        if (data.signals) {
            if (data.signals.stochRSI && data.signals.stochRSI.signal === 1) {
                return data.signals.stochRSI.status === 'OVERSOLD' ? 'OVERSOLD' : 'BUY';
            }
            if (data.signals.supertrend && data.signals.supertrend.signal === 1) {
                return 'BUY';
            }
            if (data.signals.supertrend && data.signals.supertrend.signal === -1) {
                return 'SELL';
            }
        }
        
        // Legacy format support
        if (data.stochRSI) {
            if (data.stochRSI.signal === 1) {
                return data.stochRSI.status === 'OVERSOLD' ? 'OVERSOLD' : 'BUY';
            }
        }
        
        return 'NEUTRAL';
    }
    
    calculateSignalStrength(data) {
        let strength = 0;
        let components = 0;
        
        // StochRSI strength
        if (data.signals?.stochRSI || data.stochRSI) {
            const stochData = data.signals?.stochRSI || data.stochRSI;
            strength += stochData.strength || 0.5;
            components++;
        }
        
        // EMA strength  
        if (data.signals?.ema || data.ema) {
            const emaData = data.signals?.ema || data.ema;
            strength += emaData.strength || 0.5;
            components++;
        }
        
        // SuperTrend strength
        if (data.signals?.supertrend || data.supertrend_signal !== undefined) {
            const stData = data.signals?.supertrend || { signal: data.supertrend_signal };
            strength += Math.abs(stData.signal || 0);
            components++;
        }
        
        return components > 0 ? strength / components : 0.5;
    }
    
    generateSignalReason(data) {
        const reasons = [];
        
        if (data.signals?.stochRSI || data.stochRSI) {
            const stochData = data.signals?.stochRSI || data.stochRSI;
            if (stochData.signal === 1) {
                reasons.push(`StochRSI ${stochData.status || 'signal'}`);
            }
        }
        
        if (data.signals?.ema || data.ema) {
            const emaData = data.signals?.ema || data.ema;
            if (emaData.signal === 1) {
                reasons.push(`EMA ${emaData.status || 'bullish'}`);
            }
        }
        
        if (data.signals?.supertrend || data.supertrend_signal !== undefined) {
            const stData = data.signals?.supertrend || { signal: data.supertrend_signal };
            if (stData.signal === 1) {
                reasons.push('SuperTrend bullish');
            } else if (stData.signal === -1) {
                reasons.push('SuperTrend bearish');
            }
        }
        
        return reasons.join(', ') || 'Multiple indicators';
    }
    
    identifyStrategies(data) {
        const strategies = [];
        
        if (data.signals?.stochRSI || data.stochRSI) {
            strategies.push('StochRSI');
        }
        if (data.signals?.ema || data.ema) {
            strategies.push('EMA');
        }
        if (data.signals?.supertrend || data.supertrend_signal !== undefined) {
            strategies.push('SuperTrend');
        }
        
        return strategies;
    }
    
    // Signal queue management
    queueSignal(signal) {
        this.signalQueue.push(signal);
        
        if (!this.processingQueue) {
            this.processSignalQueue();
        }
    }
    
    async processSignalQueue() {
        if (this.processingQueue || this.signalQueue.length === 0) {
            return;
        }
        
        this.processingQueue = true;
        
        while (this.signalQueue.length > 0) {
            const signal = this.signalQueue.shift();
            
            try {
                // Add signal to visualization
                if (this.signalViz) {
                    this.signalViz.addSignal(signal);
                }
                
                // Track performance
                this.performanceTracker.trackSignal(signal);
                
                // Update active symbols
                this.activeSymbols.add(signal.symbol);
                
                // Small delay to prevent overwhelming the UI
                await this.delay(50);
                
            } catch (error) {
                console.error('❌ Error processing signal:', error);
            }
        }
        
        this.processingQueue = false;
    }
    
    // Market data management
    updateMarketData(symbol, data) {
        const existing = this.marketData.get(symbol) || {};
        const updated = {
            ...existing,
            ...data,
            lastUpdate: Date.now()
        };
        
        this.marketData.set(symbol, updated);
        
        // Update chart data if visualization is connected
        if (this.signalViz && this.signalViz.chart) {
            this.updateChartData(symbol, updated);
        }
    }
    
    updateChartData(symbol, marketData) {
        // Convert market data to chart format
        if (marketData.price) {
            const candle = {
                time: Math.floor(marketData.timestamp / 1000),
                open: marketData.open || marketData.price,
                high: marketData.high || marketData.price,
                low: marketData.low || marketData.price,
                close: marketData.price
            };
            
            this.signalViz.updateChartData(candle);
        }
    }
    
    getMarketContext(symbol) {
        const marketData = this.marketData.get(symbol);
        const performance = this.performanceTracker.getSymbolPerformance(symbol);
        
        return {
            marketData,
            performance,
            isActive: this.activeSymbols.has(symbol),
            lastUpdate: this.lastUpdate,
            updateCount: this.updateCount
        };
    }
    
    getLatestPrice(symbol) {
        const marketData = this.marketData.get(symbol);
        return marketData?.price || 0;
    }
    
    // Position and order tracking
    processPositionUpdates(positions) {
        positions.forEach(position => {
            this.performanceTracker.updatePosition(position);
        });
    }
    
    processOrderUpdate(orderData) {
        this.performanceTracker.trackOrder(orderData);
    }
    
    // API methods for external access
    requestSignalUpdate(symbol) {
        if (this.socket && this.isConnected) {
            this.socket.emit('request_signal_update', { symbol });
        }
    }
    
    requestInitialData() {
        if (this.socket && this.isConnected) {
            this.socket.emit('request_initial_data', {
                include_signals: true,
                include_market_data: true,
                include_performance: true
            });
        }
    }
    
    getPerformanceData() {
        return this.performanceTracker.getOverallPerformance();
    }
    
    getSignalHistory(symbol = null, limit = 100) {
        return this.performanceTracker.getSignalHistory(symbol, limit);
    }
    
    // Configuration methods
    updateConfig(newConfig) {
        this.config = { ...this.config, ...newConfig };
        
        if (newConfig.signalUpdateInterval && this.socket && this.isStreaming) {
            this.socket.emit('update_streaming_interval', {
                interval: newConfig.signalUpdateInterval / 1000
            });
        }
    }
    
    enableRealTimeUpdates(enabled = true) {
        this.config.enableRealTimeUpdates = enabled;
        
        if (this.socket && this.isConnected) {
            if (enabled && !this.isStreaming) {
                this.socket.emit('start_streaming', {
                    interval: this.config.signalUpdateInterval / 1000
                });
                this.isStreaming = true;
            } else if (!enabled && this.isStreaming) {
                this.socket.emit('stop_streaming');
                this.isStreaming = false;
            }
        }
    }
    
    // Utility methods
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
    
    getConnectionStatus() {
        return {
            connected: this.isConnected,
            streaming: this.isStreaming,
            lastUpdate: this.lastUpdate,
            updateCount: this.updateCount,
            activeSymbols: Array.from(this.activeSymbols),
            queueSize: this.signalQueue.length
        };
    }
    
    // Cleanup
    disconnect() {
        if (this.socket) {
            this.socket.disconnect();
        }
        
        this.isConnected = false;
        this.isStreaming = false;
        this.signalQueue = [];
        this.processingQueue = false;
        
        console.log('🔌 Signal integration disconnected');
    }
    
    destroy() {
        this.disconnect();
        
        if (this.signalViz) {
            this.signalViz.destroy();
        }
        
        this.marketData.clear();
        this.activeSymbols.clear();
        this.signalProcessors.clear();
        
        console.log('🗑️ Signal integration destroyed');
    }
}

// Signal Processor Classes
class BaseSignalProcessor {
    process(symbol, data, context) {
        throw new Error('process method must be implemented');
    }
}

class StochRSIProcessor extends BaseSignalProcessor {
    process(symbol, data, context) {
        const stochData = data.signals?.stochRSI || data.stochRSI;
        if (!stochData || stochData.signal !== 1) return null;
        
        return {
            id: `stochrsi_${symbol}_${Date.now()}`,
            timestamp: Date.now(),
            symbol,
            type: stochData.status === 'OVERSOLD' ? 'OVERSOLD' : 'BUY',
            strength: stochData.strength || 0.5,
            price: context.marketData?.price || 0,
            reason: `StochRSI ${stochData.status || 'signal'}`,
            indicators: { stochRSI: stochData },
            metadata: {
                source: 'stochRSI_processor',
                confidence: stochData.strength || 0.5,
                strategies: ['StochRSI']
            }
        };
    }
}

class EMAProcessor extends BaseSignalProcessor {
    process(symbol, data, context) {
        const emaData = data.signals?.ema || data.ema;
        if (!emaData || emaData.signal !== 1) return null;
        
        return {
            id: `ema_${symbol}_${Date.now()}`,
            timestamp: Date.now(),
            symbol,
            type: 'BUY',
            strength: emaData.strength || 0.5,
            price: context.marketData?.price || emaData.price || 0,
            reason: `EMA ${emaData.status || 'bullish'}`,
            indicators: { ema: emaData },
            metadata: {
                source: 'ema_processor',
                confidence: emaData.strength || 0.5,
                strategies: ['EMA']
            }
        };
    }
}

class SuperTrendProcessor extends BaseSignalProcessor {
    process(symbol, data, context) {
        const stData = data.signals?.supertrend;
        const legacySignal = data.supertrend_signal;
        
        if (!stData && legacySignal === undefined) return null;
        
        const signal = stData?.signal || legacySignal;
        if (signal === 0) return null;
        
        return {
            id: `supertrend_${symbol}_${Date.now()}`,
            timestamp: Date.now(),
            symbol,
            type: signal === 1 ? 'BUY' : 'SELL',
            strength: Math.abs(signal),
            price: context.marketData?.price || stData?.price || 0,
            reason: `SuperTrend ${signal === 1 ? 'bullish' : 'bearish'}`,
            indicators: { supertrend: stData || { signal } },
            metadata: {
                source: 'supertrend_processor',
                confidence: Math.abs(signal),
                strategies: ['SuperTrend']
            }
        };
    }
}

class VolumeProcessor extends BaseSignalProcessor {
    process(symbol, data, context) {
        const volumeData = data.volume;
        if (!volumeData) return null;
        
        // Simple volume analysis
        const volumeRatio = volumeData.current / (volumeData.average || 1);
        if (volumeRatio < 1.5) return null; // Only signal on high volume
        
        return {
            id: `volume_${symbol}_${Date.now()}`,
            timestamp: Date.now(),
            symbol,
            type: 'NEUTRAL',
            strength: Math.min(volumeRatio / 3, 1), // Scale volume ratio
            price: context.marketData?.price || 0,
            reason: `High volume (${volumeRatio.toFixed(1)}x average)`,
            indicators: { volume: volumeData },
            metadata: {
                source: 'volume_processor',
                confidence: Math.min(volumeRatio / 3, 1),
                strategies: ['Volume']
            }
        };
    }
}

class CompositeProcessor extends BaseSignalProcessor {
    constructor(processors) {
        super();
        this.processors = processors;
    }
    
    process(symbol, signals, context) {
        if (!Array.isArray(signals) || signals.length < 2) return null;
        
        // Combine signals into composite
        const totalStrength = signals.reduce((sum, signal) => sum + signal.strength, 0);
        const avgStrength = totalStrength / signals.length;
        
        // Determine composite signal type
        const buySignals = signals.filter(s => s.type === 'BUY' || s.type === 'OVERSOLD').length;
        const sellSignals = signals.filter(s => s.type === 'SELL').length;
        
        let compositeType = 'NEUTRAL';
        if (buySignals > sellSignals && avgStrength > 0.6) {
            compositeType = 'BUY';
        } else if (sellSignals > buySignals && avgStrength > 0.6) {
            compositeType = 'SELL';
        }
        
        if (compositeType === 'NEUTRAL') return null;
        
        return {
            id: `composite_${symbol}_${Date.now()}`,
            timestamp: Date.now(),
            symbol,
            type: compositeType,
            strength: avgStrength,
            price: context.marketData?.price || 0,
            reason: `Composite signal from ${signals.length} indicators`,
            indicators: signals.reduce((acc, signal) => ({ ...acc, ...signal.indicators }), {}),
            metadata: {
                source: 'composite_processor',
                confidence: avgStrength,
                strategies: [...new Set(signals.flatMap(s => s.metadata.strategies || []))],
                componentSignals: signals.map(s => s.id)
            }
        };
    }
}

// Performance Tracker Class
class PerformanceTracker {
    constructor() {
        this.signals = [];
        this.positions = new Map();
        this.orders = [];
        this.performance = {
            totalSignals: 0,
            successfulSignals: 0,
            winRate: 0,
            avgStrength: 0,
            bestStrategy: null,
            worstStrategy: null
        };
    }
    
    trackSignal(signal) {
        this.signals.push({
            ...signal,
            tracked: true,
            trackingTime: Date.now()
        });
        
        this.updatePerformanceMetrics();
    }
    
    updatePosition(position) {
        this.positions.set(position.symbol, position);
        this.calculateSignalPerformance();
    }
    
    trackOrder(order) {
        this.orders.push({
            ...order,
            tracked: true,
            trackingTime: Date.now()
        });
    }
    
    calculateSignalPerformance() {
        // Implementation for calculating how well signals performed
        // This would track signals and correlate them with subsequent price movements
    }
    
    updatePerformanceMetrics() {
        this.performance.totalSignals = this.signals.length;
        
        if (this.signals.length > 0) {
            this.performance.avgStrength = this.signals.reduce((sum, s) => sum + s.strength, 0) / this.signals.length;
        }
        
        // Additional performance calculations would go here
    }
    
    getOverallPerformance() {
        return { ...this.performance };
    }
    
    getSymbolPerformance(symbol) {
        const symbolSignals = this.signals.filter(s => s.symbol === symbol);
        return {
            totalSignals: symbolSignals.length,
            avgStrength: symbolSignals.length > 0 ? 
                symbolSignals.reduce((sum, s) => sum + s.strength, 0) / symbolSignals.length : 0,
            lastSignal: symbolSignals[symbolSignals.length - 1]
        };
    }
    
    getSignalHistory(symbol = null, limit = 100) {
        let history = symbol ? 
            this.signals.filter(s => s.symbol === symbol) : 
            this.signals;
        
        return history.slice(-limit);
    }
}

// Global instance and exports
window.SignalIntegration = SignalIntegration;

if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        SignalIntegration,
        StochRSIProcessor,
        EMAProcessor,
        SuperTrendProcessor,
        VolumeProcessor,
        CompositeProcessor,
        PerformanceTracker
    };
}