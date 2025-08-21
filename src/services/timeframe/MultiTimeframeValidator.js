/**
 * Multi-Timeframe Signal Validation System
 * ========================================
 * 
 * Main orchestrator that integrates TimeframeDataManager, TrendAnalyzer, and ConsensusEngine
 * Provides a unified interface for validating trading signals across multiple timeframes
 */

class MultiTimeframeValidator {
    constructor(config = {}) {
        this.config = {
            timeframes: ['15m', '1h', '1d'],
            enableRealTimeValidation: true,
            autoUpdateInterval: 60000, // 1 minute
            maxConcurrentValidations: 10,
            enablePerformanceTracking: true,
            enableAdaptiveLearning: true,
            ...config
        };
        
        // Core components
        this.dataManager = null;
        this.trendAnalyzer = null;
        this.consensusEngine = null;
        
        // State management
        this.isInitialized = false;
        this.isRunning = false;
        this.validationQueue = [];
        this.activeValidations = new Map();
        
        // Event handling
        this.eventHandlers = new Map();
        
        // Performance tracking
        this.performanceMetrics = {
            totalValidations: 0,
            approvedSignals: 0,
            rejectedSignals: 0,
            avgValidationTime: 0,
            successRate: 0,
            performanceImprovement: 0
        };
        
        // Background processes
        this.updateInterval = null;
        this.cleanupInterval = null;
        
        this.initialize();
    }
    
    /**
     * Initialize the multi-timeframe validator
     */
    async initialize() {
        try {
            console.log('🚀 Initializing Multi-Timeframe Signal Validator...');
            
            // Load configuration
            await this.loadConfiguration();
            
            // Initialize core components
            this.dataManager = new TimeframeDataManager(this.config.dataManager);
            this.trendAnalyzer = new TrendAnalyzer(this.config.trendAnalyzer);
            this.consensusEngine = new ConsensusEngine(this.config.consensusEngine);
            
            // Set up component communication
            this.setupComponentCommunication();
            
            // Start background processes
            this.startBackgroundProcesses();
            
            this.isInitialized = true;
            this.isRunning = true;
            
            console.log('✅ Multi-Timeframe Signal Validator initialized successfully');
            this.emit('initialized', { config: this.config });
            
        } catch (error) {
            console.error('❌ Failed to initialize Multi-Timeframe Validator:', error);
            throw error;
        }
    }
    
    /**
     * Load configuration from file and environment
     */
    async loadConfiguration() {
        try {
            // Load timeframe configuration
            const timeframeConfig = await this.loadTimeframeConfig();
            
            // Merge configurations
            this.config = {
                ...this.config,
                ...timeframeConfig,
                dataManager: {
                    timeframes: timeframeConfig.timeframes ? Object.keys(timeframeConfig.timeframes) : this.config.timeframes,
                    ...timeframeConfig.performance,
                    ...this.config.dataManager
                },
                trendAnalyzer: {
                    timeframes: timeframeConfig.timeframes ? Object.keys(timeframeConfig.timeframes) : this.config.timeframes,
                    weights: timeframeConfig.timeframes ? 
                        Object.fromEntries(Object.entries(timeframeConfig.timeframes).map(([tf, config]) => [tf, config.weight])) : 
                        this.config.weights,
                    ...this.config.trendAnalyzer
                },
                consensusEngine: {
                    ...timeframeConfig.validation,
                    ...this.config.consensusEngine
                }
            };
            
        } catch (error) {
            console.warn('⚠️ Failed to load configuration, using defaults:', error);
        }
    }
    
    /**
     * Load timeframe configuration
     */
    async loadTimeframeConfig() {
        try {
            const response = await fetch('/config/timeframe.json');
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return await response.json();
        } catch (error) {
            console.warn('⚠️ Could not load timeframe config, using defaults');
            return {};
        }
    }
    
    /**
     * Set up communication between components
     */
    setupComponentCommunication() {
        // Data manager events
        this.dataManager.on('dataUpdate', (data) => {
            this.handleDataUpdate(data);
        });
        
        this.dataManager.on('periodicUpdate', (data) => {
            this.handlePeriodicUpdate(data);
        });
        
        // Consensus engine events
        this.consensusEngine.on('validationComplete', (result) => {
            this.handleValidationComplete(result);
        });
    }
    
    /**
     * Start background processes
     */
    startBackgroundProcesses() {
        if (this.config.autoUpdateInterval > 0) {
            this.updateInterval = setInterval(() => {
                this.performPeriodicUpdate();
            }, this.config.autoUpdateInterval);
        }
        
        // Cleanup interval
        this.cleanupInterval = setInterval(() => {
            this.performCleanup();
        }, 5 * 60 * 1000); // Every 5 minutes
    }
    
    /**
     * Validate a trading signal across multiple timeframes
     */
    async validateSignal(signal) {
        const startTime = performance.now();
        const validationId = this.generateValidationId(signal);
        
        try {
            console.log(`🔍 Validating signal ${validationId} for ${signal.symbol} (${signal.type})`);
            
            // Check if we're at max concurrent validations
            if (this.activeValidations.size >= this.config.maxConcurrentValidations) {
                return this.createQueuedResult(signal, 'Max concurrent validations reached');
            }
            
            // Track active validation
            this.activeValidations.set(validationId, {
                signal,
                startTime,
                status: 'processing'
            });
            
            // Step 1: Fetch multi-timeframe data
            const timeframeData = await this.dataManager.getMultiTimeframeData(signal.symbol);
            
            // Step 2: Analyze trends across timeframes
            const trendAnalysis = await this.trendAnalyzer.analyzeMultiTimeframeTrend(signal.symbol, timeframeData);
            
            // Step 3: Perform consensus validation
            const validationResult = await this.consensusEngine.validateSignal(signal, trendAnalysis, timeframeData);
            
            // Step 4: Enhance result with additional metadata
            const enhancedResult = this.enhanceValidationResult(validationResult, trendAnalysis, timeframeData, startTime);
            
            // Step 5: Update performance metrics
            this.updatePerformanceMetrics(enhancedResult, performance.now() - startTime);
            
            // Step 6: Emit validation event
            this.emit('signalValidated', enhancedResult);
            
            console.log(`✅ Signal validation completed: ${enhancedResult.approved ? 'APPROVED' : 'REJECTED'} (${(performance.now() - startTime).toFixed(2)}ms)`);
            
            return enhancedResult;
            
        } catch (error) {
            console.error(`❌ Error validating signal ${validationId}:`, error);
            
            const errorResult = this.createErrorResult(signal, error, performance.now() - startTime);
            this.emit('validationError', errorResult);
            
            return errorResult;
            
        } finally {
            // Clean up active validation
            this.activeValidations.delete(validationId);
        }
    }
    
    /**
     * Batch validate multiple signals
     */
    async batchValidateSignals(signals) {
        console.log(`🔄 Batch validating ${signals.length} signals`);
        
        const validationPromises = signals.map(signal => 
            this.validateSignal(signal).catch(error => ({
                signal,
                error,
                approved: false,
                reason: `Validation error: ${error.message}`
            }))
        );
        
        const results = await Promise.all(validationPromises);
        
        const summary = {
            total: results.length,
            approved: results.filter(r => r.approved).length,
            rejected: results.filter(r => !r.approved).length,
            errors: results.filter(r => r.error).length
        };
        
        console.log(`📊 Batch validation completed:`, summary);
        this.emit('batchValidationComplete', { results, summary });
        
        return { results, summary };
    }
    
    /**
     * Check if signal passes quick validation filters
     */
    quickValidate(signal) {
        // Fast pre-validation checks
        if (!signal || !signal.symbol || !signal.type) {
            return { valid: false, reason: 'Invalid signal format' };
        }
        
        if (signal.strength < 0.3) {
            return { valid: false, reason: 'Signal strength too low' };
        }
        
        const signalAge = Date.now() - (signal.timestamp || 0);
        if (signalAge > 5 * 60 * 1000) { // 5 minutes
            return { valid: false, reason: 'Signal too old' };
        }
        
        return { valid: true };
    }
    
    /**
     * Get trend alignment status for a symbol
     */
    async getTrendAlignment(symbol, timeframes = null) {
        try {
            const targetTimeframes = timeframes || this.config.timeframes;
            
            // Get cached trend data
            const alignment = this.trendAnalyzer.checkTrendAlignment(symbol, targetTimeframes);
            
            if (!alignment.aligned) {
                // Try to refresh data if alignment failed
                const timeframeData = await this.dataManager.getMultiTimeframeData(symbol);
                const trendAnalysis = await this.trendAnalyzer.analyzeMultiTimeframeTrend(symbol, timeframeData);
                
                return this.trendAnalyzer.checkTrendAlignment(symbol, targetTimeframes);
            }
            
            return alignment;
            
        } catch (error) {
            console.error(`❌ Error getting trend alignment for ${symbol}:`, error);
            return { aligned: false, reason: `Error: ${error.message}` };
        }
    }
    
    /**
     * Get consensus status for a symbol
     */
    getTrendConsensus(symbol) {
        return this.trendAnalyzer.getTrendConsensus(symbol);
    }
    
    /**
     * Subscribe to real-time updates for symbols
     */
    subscribeToSymbols(symbols) {
        if (!Array.isArray(symbols)) {
            symbols = [symbols];
        }
        
        symbols.forEach(symbol => {
            this.dataManager.subscribeToUpdates(symbol, this.config.timeframes);
        });
        
        console.log(`📡 Subscribed to real-time updates for symbols:`, symbols);
        this.emit('subscriptionUpdated', { symbols });
    }
    
    /**
     * Handle real-time data updates
     */
    handleDataUpdate(data) {
        const { symbol, timeframe } = data;
        
        // Trigger trend re-analysis for updated timeframe
        this.updateTrendAnalysis(symbol, timeframe);
        
        this.emit('dataUpdated', data);
    }
    
    /**
     * Handle periodic data updates
     */
    handlePeriodicUpdate(data) {
        console.log(`🔄 Periodic update completed for ${data.symbols.length} symbols`);
        this.emit('periodicUpdateComplete', data);
    }
    
    /**
     * Update trend analysis for specific symbol/timeframe
     */
    async updateTrendAnalysis(symbol, timeframe = null) {
        try {
            if (timeframe) {
                // Update specific timeframe
                const data = await this.dataManager.getData(timeframe, symbol);
                if (data) {
                    this.trendAnalyzer.analyzeTrend(symbol, timeframe, data);
                }
            } else {
                // Update all timeframes
                const timeframeData = await this.dataManager.getMultiTimeframeData(symbol);
                await this.trendAnalyzer.analyzeMultiTimeframeTrend(symbol, timeframeData);
            }
        } catch (error) {
            console.warn(`⚠️ Failed to update trend analysis for ${symbol}/${timeframe}:`, error);
        }
    }
    
    /**
     * Enhance validation result with additional metadata
     */
    enhanceValidationResult(result, trendAnalysis, timeframeData, startTime) {
        const processingTime = performance.now() - startTime;
        
        return {
            ...result,
            trendAnalysis: {
                consensus: trendAnalysis.consensus,
                alignment: this.trendAnalyzer.checkTrendAlignment(result.signal.symbol),
                timeframeDetails: Object.keys(trendAnalysis.trends).map(tf => ({
                    timeframe: tf,
                    direction: trendAnalysis.trends[tf].direction,
                    strength: trendAnalysis.trends[tf].strength,
                    confidence: trendAnalysis.trends[tf].confidence
                }))
            },
            performance: {
                processingTime: processingTime,
                dataFreshness: this.calculateDataFreshness(timeframeData),
                cacheHitRate: this.dataManager.getPerformanceMetrics().hitRate
            },
            validation: {
                timestamp: Date.now(),
                version: '1.0.0',
                config: {
                    timeframes: this.config.timeframes,
                    consensusThreshold: this.config.consensusEngine?.consensusThreshold || 0.75
                }
            }
        };
    }
    
    /**
     * Calculate data freshness across timeframes
     */
    calculateDataFreshness(timeframeData) {
        const freshness = {};
        const now = Date.now();
        
        Object.entries(timeframeData).forEach(([timeframe, data]) => {
            if (data && data.metadata && data.metadata.lastUpdate) {
                const age = now - data.metadata.lastUpdate;
                freshness[timeframe] = {
                    age: age,
                    fresh: age < 5 * 60 * 1000 // Consider fresh if < 5 minutes old
                };
            }
        });
        
        return freshness;
    }
    
    /**
     * Create queued result for delayed processing
     */
    createQueuedResult(signal, reason) {
        return {
            signal,
            approved: false,
            queued: true,
            reason: reason,
            timestamp: Date.now(),
            processingTime: 0
        };
    }
    
    /**
     * Create error result
     */
    createErrorResult(signal, error, processingTime) {
        return {
            signal,
            approved: false,
            error: true,
            reason: `Validation error: ${error.message}`,
            errorDetails: {
                name: error.name,
                message: error.message,
                stack: error.stack
            },
            timestamp: Date.now(),
            processingTime: processingTime
        };
    }
    
    /**
     * Generate validation ID
     */
    generateValidationId(signal) {
        return `val_${signal.symbol}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }
    
    /**
     * Update performance metrics
     */
    updatePerformanceMetrics(result, processingTime) {
        this.performanceMetrics.totalValidations++;
        
        if (result.approved) {
            this.performanceMetrics.approvedSignals++;
        } else {
            this.performanceMetrics.rejectedSignals++;
        }
        
        // Update average processing time
        if (this.performanceMetrics.avgValidationTime === 0) {
            this.performanceMetrics.avgValidationTime = processingTime;
        } else {
            this.performanceMetrics.avgValidationTime = 
                (this.performanceMetrics.avgValidationTime * 0.9) + (processingTime * 0.1);
        }
        
        // Calculate success rate (this would be updated from actual trading results)
        this.performanceMetrics.successRate = this.performanceMetrics.totalValidations > 0 ?
            this.performanceMetrics.approvedSignals / this.performanceMetrics.totalValidations : 0;
    }
    
    /**
     * Perform periodic maintenance
     */
    async performPeriodicUpdate() {
        if (!this.isRunning) return;
        
        try {
            // Update trend analysis for active symbols
            const activeSymbols = this.dataManager.getActiveSymbols();
            
            for (const symbol of activeSymbols.slice(0, 5)) { // Limit to 5 symbols per update
                await this.updateTrendAnalysis(symbol);
            }
            
            this.emit('periodicMaintenanceComplete', { updatedSymbols: activeSymbols.length });
            
        } catch (error) {
            console.error('❌ Error during periodic update:', error);
        }
    }
    
    /**
     * Perform cleanup operations
     */
    performCleanup() {
        // Clean up old validation entries
        const cutoff = Date.now() - 30 * 60 * 1000; // 30 minutes
        let cleaned = 0;
        
        for (const [id, validation] of this.activeValidations.entries()) {
            if (validation.startTime < cutoff) {
                this.activeValidations.delete(id);
                cleaned++;
            }
        }
        
        if (cleaned > 0) {
            console.log(`🧹 Cleaned up ${cleaned} stale validations`);
        }
    }
    
    /**
     * Get comprehensive status
     */
    getStatus() {
        return {
            isInitialized: this.isInitialized,
            isRunning: this.isRunning,
            activeValidations: this.activeValidations.size,
            performanceMetrics: this.performanceMetrics,
            components: {
                dataManager: this.dataManager ? this.dataManager.getStatus() : null,
                trendAnalyzer: this.trendAnalyzer ? this.trendAnalyzer.getStatus() : null,
                consensusEngine: this.consensusEngine ? this.consensusEngine.getStatus() : null
            },
            config: {
                timeframes: this.config.timeframes,
                enableRealTimeValidation: this.config.enableRealTimeValidation,
                maxConcurrentValidations: this.config.maxConcurrentValidations
            }
        };
    }
    
    /**
     * Get performance statistics
     */
    getPerformanceStats() {
        const approvalRate = this.performanceMetrics.totalValidations > 0 ?
            (this.performanceMetrics.approvedSignals / this.performanceMetrics.totalValidations * 100) : 0;
        
        return {
            ...this.performanceMetrics,
            approvalRate: approvalRate.toFixed(2),
            dataManagerStats: this.dataManager ? this.dataManager.getPerformanceMetrics() : null,
            trendAnalyzerStats: this.trendAnalyzer ? this.trendAnalyzer.getPerformanceMetrics() : null,
            consensusEngineStats: this.consensusEngine ? this.consensusEngine.getValidationStats() : null
        };
    }
    
    /**
     * Update signal outcome for learning
     */
    updateSignalOutcome(signalId, successful, profitLoss = null) {
        if (this.consensusEngine) {
            this.consensusEngine.updateSignalOutcome(signalId, successful, profitLoss);
        }
        
        this.emit('signalOutcomeUpdated', { signalId, successful, profitLoss });
    }
    
    /**
     * Event handling methods
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
     * Shutdown the validator
     */
    async shutdown() {
        console.log('🛑 Shutting down Multi-Timeframe Validator...');
        
        this.isRunning = false;
        
        // Clear intervals
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }
        if (this.cleanupInterval) {
            clearInterval(this.cleanupInterval);
        }
        
        // Shutdown components
        if (this.dataManager) {
            this.dataManager.shutdown();
        }
        
        // Clear active validations
        this.activeValidations.clear();
        
        this.isInitialized = false;
        
        console.log('✅ Multi-Timeframe Validator shut down successfully');
        this.emit('shutdown');
    }
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MultiTimeframeValidator;
}

// Global assignment for direct HTML inclusion
if (typeof window !== 'undefined') {
    window.MultiTimeframeValidator = MultiTimeframeValidator;
}