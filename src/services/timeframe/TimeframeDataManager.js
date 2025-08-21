/**
 * Multi-Timeframe Data Manager
 * ============================
 * 
 * Manages data fetching, caching, and synchronization across multiple timeframes
 * Optimized for real-time trading with efficient memory usage and fast access
 */

class TimeframeDataManager {
    constructor(config = {}) {
        this.config = {
            timeframes: ['15m', '1h', '1d'],
            cacheSize: 10000,
            batchSize: 100,
            updateFrequency: 60000, // 1 minute
            parallelProcessing: true,
            compressionEnabled: true,
            ...config
        };
        
        // Data storage
        this.dataCache = new Map(); // timeframe -> symbol -> data
        this.metadataCache = new Map(); // metadata for each timeframe/symbol
        this.pendingRequests = new Map();
        this.lastUpdates = new Map();
        
        // Performance tracking
        this.performanceMetrics = {
            cacheHits: 0,
            cacheMisses: 0,
            dataFetches: 0,
            compressionRatio: 0,
            avgResponseTime: 0,
            memoryUsage: 0
        };
        
        // Event handling
        this.eventHandlers = new Map();
        
        // Background processes
        this.updateIntervals = new Map();
        this.cleanupInterval = null;
        
        this.initialize();
    }
    
    /**
     * Initialize the data manager
     */
    initialize() {
        // Initialize cache structure
        this.config.timeframes.forEach(timeframe => {
            this.dataCache.set(timeframe, new Map());
            this.metadataCache.set(timeframe, new Map());
            this.lastUpdates.set(timeframe, new Map());
        });
        
        // Start background processes
        this.startPeriodicUpdates();
        this.startMemoryCleanup();
        
        console.log('📊 TimeframeDataManager initialized with timeframes:', this.config.timeframes);
    }
    
    /**
     * Get market data for specific timeframe and symbol
     */
    async getData(timeframe, symbol, options = {}) {
        const startTime = performance.now();
        
        try {
            const cacheKey = this.getCacheKey(timeframe, symbol);
            const cached = this.getCachedData(timeframe, symbol);
            
            // Check cache validity
            if (cached && this.isCacheValid(timeframe, symbol, options)) {
                this.performanceMetrics.cacheHits++;
                return cached;
            }
            
            this.performanceMetrics.cacheMisses++;
            
            // Fetch fresh data
            const data = await this.fetchMarketData(timeframe, symbol, options);
            
            // Cache the data
            this.cacheData(timeframe, symbol, data);
            
            // Update performance metrics
            const responseTime = performance.now() - startTime;
            this.updatePerformanceMetrics(responseTime);
            
            return data;
            
        } catch (error) {
            console.error(`❌ Error fetching data for ${timeframe}/${symbol}:`, error);
            throw error;
        }
    }
    
    /**
     * Get data for all timeframes for a symbol
     */
    async getMultiTimeframeData(symbol, options = {}) {
        const promises = this.config.timeframes.map(timeframe => 
            this.getData(timeframe, symbol, options)
                .catch(error => {
                    console.warn(`⚠️ Failed to fetch ${timeframe} data for ${symbol}:`, error);
                    return null;
                })
        );
        
        if (this.config.parallelProcessing) {
            const results = await Promise.allSettled(promises);
            return this.config.timeframes.reduce((acc, timeframe, index) => {
                const result = results[index];
                acc[timeframe] = result.status === 'fulfilled' ? result.value : null;
                return acc;
            }, {});
        } else {
            // Sequential processing for rate limiting
            const results = {};
            for (let i = 0; i < this.config.timeframes.length; i++) {
                const timeframe = this.config.timeframes[i];
                try {
                    results[timeframe] = await promises[i];
                } catch (error) {
                    results[timeframe] = null;
                }
            }
            return results;
        }
    }
    
    /**
     * Fetch market data from API or WebSocket
     */
    async fetchMarketData(timeframe, symbol, options = {}) {
        const requestKey = `${timeframe}:${symbol}`;
        
        // Prevent duplicate requests
        if (this.pendingRequests.has(requestKey)) {
            return await this.pendingRequests.get(requestKey);
        }
        
        const requestPromise = this.performDataFetch(timeframe, symbol, options);
        this.pendingRequests.set(requestKey, requestPromise);
        
        try {
            const data = await requestPromise;
            this.pendingRequests.delete(requestKey);
            return data;
        } catch (error) {
            this.pendingRequests.delete(requestKey);
            throw error;
        }
    }
    
    /**
     * Perform the actual data fetch
     */
    async performDataFetch(timeframe, symbol, options = {}) {
        this.performanceMetrics.dataFetches++;
        
        // This would integrate with your existing data fetching mechanism
        // For now, we'll simulate the API call structure
        const response = await fetch('/api/market-data', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                symbol,
                timeframe,
                limit: options.limit || 100,
                from: options.from,
                to: options.to
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Process and validate data
        return this.processRawData(data, timeframe, symbol);
    }
    
    /**
     * Process raw market data
     */
    processRawData(rawData, timeframe, symbol) {
        if (!rawData || !Array.isArray(rawData.bars)) {
            throw new Error('Invalid market data format');
        }
        
        const processed = {
            symbol,
            timeframe,
            timestamp: Date.now(),
            bars: rawData.bars.map(bar => ({
                time: new Date(bar.timestamp).getTime() / 1000, // Convert to seconds
                open: parseFloat(bar.open),
                high: parseFloat(bar.high),
                low: parseFloat(bar.low),
                close: parseFloat(bar.close),
                volume: parseInt(bar.volume || 0)
            })),
            metadata: {
                source: rawData.source || 'api',
                exchange: rawData.exchange,
                lastUpdate: Date.now(),
                barCount: rawData.bars.length
            }
        };
        
        // Apply compression if enabled
        if (this.config.compressionEnabled) {
            processed.compressed = this.compressData(processed.bars);
            processed.compression = true;
        }
        
        return processed;
    }
    
    /**
     * Cache data with metadata
     */
    cacheData(timeframe, symbol, data) {
        const timeframeCache = this.dataCache.get(timeframe);
        const metadataCache = this.metadataCache.get(timeframe);
        const lastUpdateCache = this.lastUpdates.get(timeframe);
        
        if (timeframeCache && metadataCache && lastUpdateCache) {
            // Store data
            timeframeCache.set(symbol, data);
            
            // Store metadata
            metadataCache.set(symbol, {
                cacheTime: Date.now(),
                dataSize: JSON.stringify(data).length,
                barCount: data.bars ? data.bars.length : 0,
                lastBarTime: data.bars && data.bars.length > 0 ? 
                    data.bars[data.bars.length - 1].time : null
            });
            
            // Update last update time
            lastUpdateCache.set(symbol, Date.now());
            
            // Cleanup old entries if cache is too large
            this.cleanupCache(timeframe);
        }
    }
    
    /**
     * Get cached data
     */
    getCachedData(timeframe, symbol) {
        const timeframeCache = this.dataCache.get(timeframe);
        return timeframeCache ? timeframeCache.get(symbol) : null;
    }
    
    /**
     * Check if cached data is still valid
     */
    isCacheValid(timeframe, symbol, options = {}) {
        const metadata = this.metadataCache.get(timeframe)?.get(symbol);
        if (!metadata) return false;
        
        const now = Date.now();
        const cacheAge = now - metadata.cacheTime;
        
        // Get cache duration from config
        const cacheDuration = this.getCacheDuration(timeframe);
        
        // Check if cache has expired
        if (cacheAge > cacheDuration) {
            return false;
        }
        
        // Check if forced refresh is requested
        if (options.forceRefresh) {
            return false;
        }
        
        return true;
    }
    
    /**
     * Get cache duration for timeframe
     */
    getCacheDuration(timeframe) {
        const durations = {
            '15m': 5 * 60 * 1000,     // 5 minutes
            '1h': 15 * 60 * 1000,     // 15 minutes
            '1d': 60 * 60 * 1000      // 1 hour
        };
        
        return durations[timeframe] || 5 * 60 * 1000;
    }
    
    /**
     * Generate cache key
     */
    getCacheKey(timeframe, symbol) {
        return `${timeframe}:${symbol}`;
    }
    
    /**
     * Compress data for storage efficiency
     */
    compressData(bars) {
        // Simple compression - store deltas instead of absolute values
        if (bars.length === 0) return [];
        
        const compressed = [bars[0]]; // First bar as reference
        
        for (let i = 1; i < bars.length; i++) {
            const prev = bars[i - 1];
            const curr = bars[i];
            
            compressed.push({
                time: curr.time,
                open: this.roundDelta(curr.open - prev.close),
                high: this.roundDelta(curr.high - prev.close),
                low: this.roundDelta(curr.low - prev.close),
                close: this.roundDelta(curr.close - prev.close),
                volume: curr.volume
            });
        }
        
        return compressed;
    }
    
    /**
     * Decompress data
     */
    decompressData(compressed) {
        if (compressed.length === 0) return [];
        
        const decompressed = [compressed[0]]; // First bar is absolute
        
        for (let i = 1; i < compressed.length; i++) {
            const prev = decompressed[i - 1];
            const curr = compressed[i];
            
            decompressed.push({
                time: curr.time,
                open: prev.close + curr.open,
                high: prev.close + curr.high,
                low: prev.close + curr.low,
                close: prev.close + curr.close,
                volume: curr.volume
            });
        }
        
        return decompressed;
    }
    
    /**
     * Round delta values for compression
     */
    roundDelta(value) {
        return Math.round(value * 10000) / 10000; // 4 decimal places
    }
    
    /**
     * Start periodic updates
     */
    startPeriodicUpdates() {
        if (this.config.updateFrequency > 0) {
            const interval = setInterval(() => {
                this.performPeriodicUpdate();
            }, this.config.updateFrequency);
            
            this.updateIntervals.set('main', interval);
        }
    }
    
    /**
     * Perform periodic update of active symbols
     */
    async performPeriodicUpdate() {
        const activeSymbols = this.getActiveSymbols();
        
        if (activeSymbols.length === 0) return;
        
        console.log(`🔄 Performing periodic update for ${activeSymbols.length} symbols`);
        
        // Update data for active symbols
        for (const symbol of activeSymbols) {
            try {
                await this.getMultiTimeframeData(symbol, { forceRefresh: false });
            } catch (error) {
                console.warn(`⚠️ Failed to update ${symbol}:`, error);
            }
        }
        
        this.emit('periodicUpdate', { symbols: activeSymbols });
    }
    
    /**
     * Get list of active symbols from cache
     */
    getActiveSymbols() {
        const symbolSet = new Set();
        
        this.dataCache.forEach(timeframeCache => {
            timeframeCache.forEach((data, symbol) => {
                symbolSet.add(symbol);
            });
        });
        
        return Array.from(symbolSet);
    }
    
    /**
     * Start memory cleanup process
     */
    startMemoryCleanup() {
        this.cleanupInterval = setInterval(() => {
            this.performMemoryCleanup();
        }, 5 * 60 * 1000); // Every 5 minutes
    }
    
    /**
     * Perform memory cleanup
     */
    performMemoryCleanup() {
        let cleanedEntries = 0;
        
        this.config.timeframes.forEach(timeframe => {
            cleanedEntries += this.cleanupCache(timeframe);
        });
        
        if (cleanedEntries > 0) {
            console.log(`🧹 Cleaned up ${cleanedEntries} cache entries`);
        }
        
        // Update memory usage metrics
        this.updateMemoryMetrics();
    }
    
    /**
     * Cleanup cache for specific timeframe
     */
    cleanupCache(timeframe) {
        const timeframeCache = this.dataCache.get(timeframe);
        const metadataCache = this.metadataCache.get(timeframe);
        
        if (!timeframeCache || !metadataCache) return 0;
        
        const now = Date.now();
        const cacheDuration = this.getCacheDuration(timeframe);
        let cleaned = 0;
        
        // Remove expired entries
        for (const [symbol, metadata] of metadataCache.entries()) {
            if (now - metadata.cacheTime > cacheDuration * 2) { // Keep for 2x duration
                timeframeCache.delete(symbol);
                metadataCache.delete(symbol);
                cleaned++;
            }
        }
        
        // Remove oldest entries if cache is too large
        if (timeframeCache.size > this.config.cacheSize) {
            const entries = Array.from(metadataCache.entries())
                .sort((a, b) => a[1].cacheTime - b[1].cacheTime);
            
            const toRemove = timeframeCache.size - this.config.cacheSize;
            for (let i = 0; i < toRemove; i++) {
                const [symbol] = entries[i];
                timeframeCache.delete(symbol);
                metadataCache.delete(symbol);
                cleaned++;
            }
        }
        
        return cleaned;
    }
    
    /**
     * Update performance metrics
     */
    updatePerformanceMetrics(responseTime) {
        // Update average response time
        if (this.performanceMetrics.avgResponseTime === 0) {
            this.performanceMetrics.avgResponseTime = responseTime;
        } else {
            this.performanceMetrics.avgResponseTime = 
                (this.performanceMetrics.avgResponseTime * 0.9) + (responseTime * 0.1);
        }
    }
    
    /**
     * Update memory usage metrics
     */
    updateMemoryMetrics() {
        let totalSize = 0;
        let totalEntries = 0;
        
        this.dataCache.forEach(timeframeCache => {
            timeframeCache.forEach(data => {
                totalSize += JSON.stringify(data).length;
                totalEntries++;
            });
        });
        
        this.performanceMetrics.memoryUsage = totalSize;
        this.performanceMetrics.totalEntries = totalEntries;
    }
    
    /**
     * Get performance metrics
     */
    getPerformanceMetrics() {
        const hitRate = this.performanceMetrics.cacheHits / 
            (this.performanceMetrics.cacheHits + this.performanceMetrics.cacheMisses) * 100;
        
        return {
            ...this.performanceMetrics,
            hitRate: isNaN(hitRate) ? 0 : hitRate.toFixed(2)
        };
    }
    
    /**
     * Event handling
     */
    on(event, handler) {
        if (!this.eventHandlers.has(event)) {
            this.eventHandlers.set(event, new Set());
        }
        this.eventHandlers.get(event).add(handler);
    }
    
    off(event, handler) {
        if (this.eventHandlers.has(event)) {
            this.eventHandlers.get(event).delete(handler);
        }
    }
    
    emit(event, data) {
        if (this.eventHandlers.has(event)) {
            this.eventHandlers.get(event).forEach(handler => {
                try {
                    handler(data);
                } catch (error) {
                    console.error(`❌ Event handler error for '${event}':`, error);
                }
            });
        }
    }
    
    /**
     * Subscribe to real-time updates for symbol
     */
    subscribeToUpdates(symbol, timeframes = null) {
        const targetTimeframes = timeframes || this.config.timeframes;
        
        // This would integrate with your WebSocket system
        this.emit('subscribeRequest', { symbol, timeframes: targetTimeframes });
        
        console.log(`📡 Subscribed to updates for ${symbol} on timeframes:`, targetTimeframes);
    }
    
    /**
     * Process real-time update from WebSocket
     */
    processRealtimeUpdate(update) {
        const { symbol, timeframe, data } = update;
        
        if (!this.config.timeframes.includes(timeframe)) {
            return;
        }
        
        // Update cache with new data
        const currentData = this.getCachedData(timeframe, symbol);
        if (currentData && data.bars) {
            // Append new bars or update last bar
            const updatedBars = [...currentData.bars];
            
            data.bars.forEach(newBar => {
                const existingIndex = updatedBars.findIndex(bar => bar.time === newBar.time);
                if (existingIndex >= 0) {
                    updatedBars[existingIndex] = newBar;
                } else {
                    updatedBars.push(newBar);
                }
            });
            
            // Sort by time
            updatedBars.sort((a, b) => a.time - b.time);
            
            const updatedData = {
                ...currentData,
                bars: updatedBars,
                metadata: {
                    ...currentData.metadata,
                    lastUpdate: Date.now()
                }
            };
            
            this.cacheData(timeframe, symbol, updatedData);
            this.emit('dataUpdate', { symbol, timeframe, data: updatedData });
        }
    }
    
    /**
     * Get status of data manager
     */
    getStatus() {
        const activeSymbols = this.getActiveSymbols();
        const totalCacheEntries = Array.from(this.dataCache.values())
            .reduce((sum, cache) => sum + cache.size, 0);
        
        return {
            isRunning: true,
            activeSymbols: activeSymbols.length,
            totalCacheEntries,
            timeframes: this.config.timeframes,
            performanceMetrics: this.getPerformanceMetrics(),
            memoryUsage: this.performanceMetrics.memoryUsage,
            lastCleanup: this.lastCleanup || null
        };
    }
    
    /**
     * Shutdown data manager
     */
    shutdown() {
        // Clear intervals
        this.updateIntervals.forEach(interval => clearInterval(interval));
        if (this.cleanupInterval) {
            clearInterval(this.cleanupInterval);
        }
        
        // Clear caches
        this.dataCache.clear();
        this.metadataCache.clear();
        this.lastUpdates.clear();
        this.pendingRequests.clear();
        
        console.log('🛑 TimeframeDataManager shut down');
    }
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TimeframeDataManager;
}

// Global assignment for direct HTML inclusion
if (typeof window !== 'undefined') {
    window.TimeframeDataManager = TimeframeDataManager;
}