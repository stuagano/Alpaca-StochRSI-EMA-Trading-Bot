/**
 * Multi-Timeframe Consensus Engine
 * ================================
 * 
 * Validates trading signals across multiple timeframes using consensus algorithms
 * Implements sophisticated validation logic to reduce losing trades by >25%
 */

class ConsensusEngine {
    constructor(config = {}) {
        this.config = {
            timeframes: ['15m', '1h', '1d'],
            requiredTimeframes: ['15m', '1h', '1d'],
            consensusThreshold: 0.75,
            minimumAgreement: 2,
            signalStrengthThreshold: 0.6,
            trendAlignmentWindow: 5,
            signalConfidenceMultiplier: 1.25,
            volatilityFilter: true,
            volumeConfirmation: false,
            adaptiveThresholds: true,
            marketConditionAdjustment: true,
            ...config
        };
        
        // Validation state
        this.validationCache = new Map(); // symbol -> validation results
        this.signalHistory = new Map(); // symbol -> historical signals
        this.performanceTracker = new PerformanceTracker();
        this.marketConditions = new MarketConditionAnalyzer();
        
        // Decision trees and rules
        this.validationRules = new ValidationRuleEngine(this.config);
        this.adaptiveThresholds = new AdaptiveThresholdManager(this.config);
        
        // Performance metrics
        this.metrics = {
            totalValidations: 0,
            consensusAchieved: 0,
            signalsApproved: 0,
            signalsRejected: 0,
            falsePositiveRate: 0,
            falseNegativeRate: 0,
            avgProcessingTime: 0,
            performanceImprovement: 0
        };
        
        this.initialize();
    }
    
    /**
     * Initialize the consensus engine
     */
    initialize() {
        console.log('🎯 ConsensusEngine initialized with config:', {
            timeframes: this.config.timeframes,
            consensusThreshold: this.config.consensusThreshold,
            minimumAgreement: this.config.minimumAgreement
        });
        
        // Load historical performance data if available
        this.loadPerformanceHistory();
    }
    
    /**
     * Validate a trading signal across multiple timeframes
     */
    async validateSignal(signal, trendData, marketData) {
        const startTime = performance.now();
        
        try {
            this.metrics.totalValidations++;
            
            // Step 1: Basic signal validation
            const basicValidation = this.performBasicValidation(signal);
            if (!basicValidation.valid) {
                return this.createRejectionResult(signal, basicValidation.reason, 'basic_validation');
            }
            
            // Step 2: Trend consensus analysis
            const trendConsensus = this.analyzeTrendConsensus(signal, trendData);
            
            // Step 3: Market condition assessment
            const marketCondition = await this.marketConditions.assessConditions(signal.symbol, marketData);
            
            // Step 4: Adaptive threshold adjustment
            const adjustedThresholds = this.adaptiveThresholds.getAdjustedThresholds(
                signal.symbol, 
                marketCondition
            );
            
            // Step 5: Comprehensive validation
            const validation = this.performComprehensiveValidation(
                signal,
                trendConsensus,
                marketCondition,
                adjustedThresholds
            );
            
            // Step 6: Apply validation rules
            const ruleValidation = this.validationRules.applyRules(
                signal,
                trendConsensus,
                marketCondition,
                validation
            );
            
            // Step 7: Calculate final decision
            const decision = this.calculateFinalDecision(
                signal,
                trendConsensus,
                marketCondition,
                validation,
                ruleValidation,
                adjustedThresholds
            );
            
            // Step 8: Cache and track results
            this.cacheValidationResult(signal, decision);
            this.trackSignalPerformance(signal, decision);
            
            // Update metrics
            const processingTime = performance.now() - startTime;
            this.updateMetrics(decision, processingTime);
            
            return decision;
            
        } catch (error) {
            console.error('❌ Error validating signal:', error);
            return this.createErrorResult(signal, error);
        }
    }
    
    /**
     * Perform basic signal validation
     */
    performBasicValidation(signal) {
        // Check required fields
        if (!signal.symbol || !signal.type || signal.strength === undefined) {
            return { valid: false, reason: 'Missing required signal fields' };
        }
        
        // Check signal strength
        if (signal.strength < 0 || signal.strength > 1) {
            return { valid: false, reason: 'Invalid signal strength' };
        }
        
        // Check signal type
        if (!['BUY', 'SELL', 'OVERSOLD', 'OVERBOUGHT', 'NEUTRAL'].includes(signal.type)) {
            return { valid: false, reason: 'Invalid signal type' };
        }
        
        // Check signal age
        const signalAge = Date.now() - (signal.timestamp || 0);
        if (signalAge > 5 * 60 * 1000) { // 5 minutes
            return { valid: false, reason: 'Signal too old' };
        }
        
        return { valid: true };
    }
    
    /**
     * Analyze trend consensus across timeframes
     */
    analyzeTrendConsensus(signal, trendData) {
        const analysis = {
            consensusAchieved: false,
            agreement: 0,
            strength: 0,
            confidence: 0,
            alignedTimeframes: [],
            conflictingTimeframes: [],
            details: {}
        };
        
        if (!trendData || !trendData.trends) {
            analysis.reason = 'No trend data available';
            return analysis;
        }
        
        const trends = trendData.trends;
        const validTimeframes = this.config.requiredTimeframes.filter(tf => trends[tf]);
        
        if (validTimeframes.length < this.config.minimumAgreement) {
            analysis.reason = `Insufficient timeframe data (${validTimeframes.length}/${this.config.minimumAgreement})`;
            return analysis;
        }
        
        // Analyze alignment for buy/sell signals
        let alignedCount = 0;
        let totalWeight = 0;
        let alignedWeight = 0;
        let totalStrength = 0;
        let totalConfidence = 0;
        
        validTimeframes.forEach(timeframe => {
            const trend = trends[timeframe];
            const weight = trend.weight || 1.0;
            
            totalWeight += weight;
            totalStrength += trend.strength * weight;
            totalConfidence += trend.confidence * weight;
            
            // Check if trend aligns with signal
            const isAligned = this.checkTrendSignalAlignment(signal, trend);
            
            if (isAligned) {
                alignedCount++;
                alignedWeight += weight;
                analysis.alignedTimeframes.push(timeframe);
            } else {
                analysis.conflictingTimeframes.push(timeframe);
            }
            
            analysis.details[timeframe] = {
                direction: trend.direction,
                strength: trend.strength,
                confidence: trend.confidence,
                aligned: isAligned,
                weight: weight
            };
        });
        
        // Calculate consensus metrics
        analysis.agreement = totalWeight > 0 ? alignedWeight / totalWeight : 0;
        analysis.strength = totalWeight > 0 ? totalStrength / totalWeight : 0;
        analysis.confidence = totalWeight > 0 ? totalConfidence / totalWeight : 0;
        analysis.consensusAchieved = analysis.agreement >= this.config.consensusThreshold &&
                                    alignedCount >= this.config.minimumAgreement;
        
        return analysis;
    }
    
    /**
     * Check if trend aligns with signal direction
     */
    checkTrendSignalAlignment(signal, trend) {
        if (trend.direction === 'neutral') {
            return false; // Neutral trends don't support any signal
        }
        
        switch (signal.type) {
            case 'BUY':
            case 'OVERSOLD':
                return trend.direction === 'bullish';
            case 'SELL':
            case 'OVERBOUGHT':
                return trend.direction === 'bearish';
            default:
                return false;
        }
    }
    
    /**
     * Perform comprehensive validation
     */
    performComprehensiveValidation(signal, trendConsensus, marketCondition, adjustedThresholds) {
        const validation = {
            score: 0,
            factors: {},
            weights: {},
            totalWeight: 0
        };
        
        // Factor 1: Trend Consensus (40% weight)
        const consensusWeight = 4.0;
        validation.factors.trendConsensus = trendConsensus.consensusAchieved ? 
            trendConsensus.agreement * trendConsensus.strength : 0;
        validation.weights.trendConsensus = consensusWeight;
        validation.score += validation.factors.trendConsensus * consensusWeight;
        validation.totalWeight += consensusWeight;
        
        // Factor 2: Signal Strength (20% weight)
        const strengthWeight = 2.0;
        validation.factors.signalStrength = signal.strength >= adjustedThresholds.signalStrength ? 
            signal.strength : 0;
        validation.weights.signalStrength = strengthWeight;
        validation.score += validation.factors.signalStrength * strengthWeight;
        validation.totalWeight += strengthWeight;
        
        // Factor 3: Market Conditions (20% weight)
        const marketWeight = 2.0;
        validation.factors.marketConditions = this.evaluateMarketConditions(marketCondition);
        validation.weights.marketConditions = marketWeight;
        validation.score += validation.factors.marketConditions * marketWeight;
        validation.totalWeight += marketWeight;
        
        // Factor 4: Signal Quality (10% weight)
        const qualityWeight = 1.0;
        validation.factors.signalQuality = this.evaluateSignalQuality(signal);
        validation.weights.signalQuality = qualityWeight;
        validation.score += validation.factors.signalQuality * qualityWeight;
        validation.totalWeight += qualityWeight;
        
        // Factor 5: Historical Performance (10% weight)
        const historyWeight = 1.0;
        validation.factors.historicalPerformance = this.evaluateHistoricalPerformance(signal);
        validation.weights.historicalPerformance = historyWeight;
        validation.score += validation.factors.historicalPerformance * historyWeight;
        validation.totalWeight += historyWeight;
        
        // Normalize score
        validation.normalizedScore = validation.totalWeight > 0 ? 
            validation.score / validation.totalWeight : 0;
        
        return validation;
    }
    
    /**
     * Evaluate market conditions factor
     */
    evaluateMarketConditions(marketCondition) {
        if (!marketCondition) return 0.5;
        
        let score = 0.5;
        
        // Volatility assessment
        if (marketCondition.volatility) {
            if (marketCondition.volatility.level === 'low') {
                score += 0.2; // Low volatility is better for signals
            } else if (marketCondition.volatility.level === 'high') {
                score -= 0.2; // High volatility increases risk
            }
        }
        
        // Volume assessment
        if (marketCondition.volume) {
            if (marketCondition.volume.level === 'high') {
                score += 0.2; // High volume confirms signals
            } else if (marketCondition.volume.level === 'low') {
                score -= 0.1; // Low volume reduces confidence
            }
        }
        
        // Market hours assessment
        if (marketCondition.marketHours) {
            if (marketCondition.marketHours.isOpen) {
                score += 0.1; // Regular market hours are preferred
            } else {
                score -= 0.2; // After hours trading is riskier
            }
        }
        
        return Math.max(0, Math.min(1, score));
    }
    
    /**
     * Evaluate signal quality
     */
    evaluateSignalQuality(signal) {
        let score = 0.5;
        
        // Signal confidence
        if (signal.metadata && signal.metadata.confidence) {
            score += signal.metadata.confidence * 0.3;
        }
        
        // Strategy count
        if (signal.metadata && signal.metadata.strategies) {
            const strategyBonus = Math.min(signal.metadata.strategies.length * 0.1, 0.3);
            score += strategyBonus;
        }
        
        // Indicator agreement
        if (signal.indicators) {
            const indicatorCount = Object.keys(signal.indicators).length;
            const indicatorBonus = Math.min(indicatorCount * 0.05, 0.2);
            score += indicatorBonus;
        }
        
        return Math.max(0, Math.min(1, score));
    }
    
    /**
     * Evaluate historical performance
     */
    evaluateHistoricalPerformance(signal) {
        const history = this.signalHistory.get(signal.symbol);
        if (!history || history.length === 0) {
            return 0.5; // Neutral score for no history
        }
        
        // Calculate recent signal performance
        const recentSignals = history.slice(-20); // Last 20 signals
        const successfulSignals = recentSignals.filter(s => s.successful).length;
        const successRate = successfulSignals / recentSignals.length;
        
        // Weight recent performance more heavily
        return Math.max(0.1, Math.min(0.9, successRate));
    }
    
    /**
     * Calculate final decision
     */
    calculateFinalDecision(signal, trendConsensus, marketCondition, validation, ruleValidation, adjustedThresholds) {
        const decision = {
            approved: false,
            confidence: 0,
            score: validation.normalizedScore,
            reason: '',
            factors: validation.factors,
            adjustments: {},
            metadata: {}
        };
        
        // Apply rule validation
        if (!ruleValidation.passed) {
            decision.approved = false;
            decision.reason = ruleValidation.reason;
            decision.ruleViolations = ruleValidation.violations;
            this.metrics.signalsRejected++;
            return decision;
        }
        
        // Check if score meets threshold
        const requiredScore = adjustedThresholds.consensusThreshold;
        if (validation.normalizedScore >= requiredScore) {
            decision.approved = true;
            decision.confidence = this.calculateSignalConfidence(
                signal,
                trendConsensus,
                validation,
                adjustedThresholds
            );
            decision.reason = 'Signal validation passed';
            this.metrics.signalsApproved++;
        } else {
            decision.approved = false;
            decision.reason = `Validation score ${validation.normalizedScore.toFixed(3)} below threshold ${requiredScore.toFixed(3)}`;
            this.metrics.signalsRejected++;
        }
        
        // Add metadata
        decision.metadata = {
            validationScore: validation.normalizedScore,
            requiredScore: requiredScore,
            trendConsensus: trendConsensus.consensusAchieved,
            marketCondition: marketCondition.summary || 'unknown',
            adjustedThresholds: adjustedThresholds,
            processingTime: Date.now() - signal.timestamp
        };
        
        return decision;
    }
    
    /**
     * Calculate signal confidence with multipliers
     */
    calculateSignalConfidence(signal, trendConsensus, validation, adjustedThresholds) {
        let confidence = validation.normalizedScore;
        
        // Apply consensus multiplier
        if (trendConsensus.consensusAchieved) {
            confidence *= this.config.signalConfidenceMultiplier;
        }
        
        // Apply strength multiplier
        if (signal.strength >= adjustedThresholds.signalStrength) {
            confidence *= 1.1;
        }
        
        // Apply trend alignment multiplier
        if (trendConsensus.agreement >= 0.8) {
            confidence *= 1.15;
        }
        
        return Math.min(1.0, confidence);
    }
    
    /**
     * Create rejection result
     */
    createRejectionResult(signal, reason, stage) {
        this.metrics.signalsRejected++;
        
        return {
            approved: false,
            confidence: 0,
            score: 0,
            reason: reason,
            stage: stage,
            signal: signal,
            timestamp: Date.now()
        };
    }
    
    /**
     * Create error result
     */
    createErrorResult(signal, error) {
        this.metrics.signalsRejected++;
        
        return {
            approved: false,
            confidence: 0,
            score: 0,
            reason: `Validation error: ${error.message}`,
            stage: 'error',
            error: error,
            signal: signal,
            timestamp: Date.now()
        };
    }
    
    /**
     * Cache validation result
     */
    cacheValidationResult(signal, decision) {
        const key = `${signal.symbol}_${signal.timestamp}`;
        this.validationCache.set(key, {
            signal,
            decision,
            timestamp: Date.now()
        });
        
        // Cleanup old entries
        if (this.validationCache.size > 1000) {
            const entries = Array.from(this.validationCache.entries());
            entries.sort((a, b) => a[1].timestamp - b[1].timestamp);
            
            // Remove oldest 100 entries
            for (let i = 0; i < 100; i++) {
                this.validationCache.delete(entries[i][0]);
            }
        }
    }
    
    /**
     * Track signal performance for learning
     */
    trackSignalPerformance(signal, decision) {
        if (!this.signalHistory.has(signal.symbol)) {
            this.signalHistory.set(signal.symbol, []);
        }
        
        const history = this.signalHistory.get(signal.symbol);
        history.push({
            signal,
            decision,
            timestamp: Date.now(),
            successful: null // Will be updated later based on actual performance
        });
        
        // Keep only recent history
        if (history.length > 100) {
            history.splice(0, history.length - 100);
        }
    }
    
    /**
     * Update performance metrics
     */
    updateMetrics(decision, processingTime) {
        if (decision.approved) {
            this.metrics.consensusAchieved++;
        }
        
        // Update average processing time
        if (this.metrics.avgProcessingTime === 0) {
            this.metrics.avgProcessingTime = processingTime;
        } else {
            this.metrics.avgProcessingTime = 
                (this.metrics.avgProcessingTime * 0.9) + (processingTime * 0.1);
        }
    }
    
    /**
     * Get validation statistics
     */
    getValidationStats() {
        const approvalRate = this.metrics.totalValidations > 0 ?
            (this.metrics.signalsApproved / this.metrics.totalValidations * 100) : 0;
        
        const consensusRate = this.metrics.totalValidations > 0 ?
            (this.metrics.consensusAchieved / this.metrics.totalValidations * 100) : 0;
        
        return {
            ...this.metrics,
            approvalRate: approvalRate.toFixed(2),
            consensusRate: consensusRate.toFixed(2)
        };
    }
    
    /**
     * Get performance improvement metrics
     */
    getPerformanceImprovement() {
        return this.performanceTracker.getImprovementMetrics();
    }
    
    /**
     * Load historical performance data
     */
    loadPerformanceHistory() {
        // This would load from persistent storage
        console.log('📊 Loading historical performance data...');
    }
    
    /**
     * Update signal outcome for learning
     */
    updateSignalOutcome(signalId, successful, profitLoss = null) {
        // Find the signal in history and update its outcome
        for (const [symbol, history] of this.signalHistory.entries()) {
            const signalRecord = history.find(record => 
                record.signal.id === signalId || 
                `${record.signal.symbol}_${record.signal.timestamp}` === signalId
            );
            
            if (signalRecord) {
                signalRecord.successful = successful;
                signalRecord.profitLoss = profitLoss;
                signalRecord.outcomeTimestamp = Date.now();
                
                // Update performance tracker
                this.performanceTracker.recordOutcome(signalRecord);
                
                // Update adaptive thresholds
                this.adaptiveThresholds.updateFromOutcome(signalRecord);
                
                break;
            }
        }
    }
    
    /**
     * Get consensus engine status
     */
    getStatus() {
        return {
            isRunning: true,
            cachedValidations: this.validationCache.size,
            symbolsTracked: this.signalHistory.size,
            validationStats: this.getValidationStats(),
            performanceImprovement: this.getPerformanceImprovement(),
            config: this.config
        };
    }
}

// Supporting Classes

class ValidationRuleEngine {
    constructor(config) {
        this.config = config;
        this.rules = this.initializeRules();
    }
    
    initializeRules() {
        return [
            {
                name: 'minimum_timeframe_agreement',
                check: (signal, trendConsensus) => 
                    trendConsensus.alignedTimeframes.length >= this.config.minimumAgreement,
                message: 'Insufficient timeframe agreement'
            },
            {
                name: 'trend_strength_threshold',
                check: (signal, trendConsensus) => 
                    trendConsensus.strength >= this.config.signalStrengthThreshold,
                message: 'Trend strength below threshold'
            },
            {
                name: 'signal_confidence',
                check: (signal) => 
                    !signal.metadata?.confidence || signal.metadata.confidence >= 0.3,
                message: 'Signal confidence too low'
            }
        ];
    }
    
    applyRules(signal, trendConsensus, marketCondition, validation) {
        const violations = [];
        
        for (const rule of this.rules) {
            try {
                if (!rule.check(signal, trendConsensus, marketCondition, validation)) {
                    violations.push({
                        rule: rule.name,
                        message: rule.message
                    });
                }
            } catch (error) {
                console.warn(`⚠️ Rule check error for ${rule.name}:`, error);
            }
        }
        
        return {
            passed: violations.length === 0,
            violations: violations,
            reason: violations.length > 0 ? violations[0].message : null
        };
    }
}

class AdaptiveThresholdManager {
    constructor(config) {
        this.config = config;
        this.baselines = {
            consensusThreshold: config.consensusThreshold,
            signalStrength: config.signalStrengthThreshold,
            minimumAgreement: config.minimumAgreement
        };
        this.adjustments = new Map(); // symbol -> adjustments
    }
    
    getAdjustedThresholds(symbol, marketCondition) {
        const baseThresholds = { ...this.baselines };
        const symbolAdjustments = this.adjustments.get(symbol) || {};
        
        // Apply symbol-specific adjustments
        Object.keys(baseThresholds).forEach(key => {
            if (symbolAdjustments[key]) {
                baseThresholds[key] += symbolAdjustments[key];
            }
        });
        
        // Apply market condition adjustments
        if (marketCondition) {
            if (marketCondition.volatility?.level === 'high') {
                baseThresholds.consensusThreshold += 0.1;
                baseThresholds.signalStrength += 0.1;
            }
            
            if (marketCondition.volume?.level === 'low') {
                baseThresholds.consensusThreshold += 0.05;
            }
        }
        
        // Ensure thresholds stay within valid ranges
        baseThresholds.consensusThreshold = Math.max(0.5, Math.min(0.95, baseThresholds.consensusThreshold));
        baseThresholds.signalStrength = Math.max(0.3, Math.min(0.9, baseThresholds.signalStrength));
        baseThresholds.minimumAgreement = Math.max(1, Math.min(this.config.timeframes.length, baseThresholds.minimumAgreement));
        
        return baseThresholds;
    }
    
    updateFromOutcome(signalRecord) {
        // Implement learning from signal outcomes
        // This is a simplified version - in practice, you'd use more sophisticated ML
        const symbol = signalRecord.signal.symbol;
        const successful = signalRecord.successful;
        
        if (!this.adjustments.has(symbol)) {
            this.adjustments.set(symbol, {
                consensusThreshold: 0,
                signalStrength: 0,
                minimumAgreement: 0,
                sampleCount: 0
            });
        }
        
        const adjustments = this.adjustments.get(symbol);
        adjustments.sampleCount++;
        
        // Simple adjustment logic
        const learningRate = 0.01;
        if (!successful) {
            // Signal failed - make thresholds stricter
            adjustments.consensusThreshold += learningRate;
            adjustments.signalStrength += learningRate;
        } else {
            // Signal succeeded - can slightly relax thresholds
            adjustments.consensusThreshold -= learningRate * 0.5;
            adjustments.signalStrength -= learningRate * 0.5;
        }
        
        // Cap adjustments
        adjustments.consensusThreshold = Math.max(-0.2, Math.min(0.2, adjustments.consensusThreshold));
        adjustments.signalStrength = Math.max(-0.2, Math.min(0.2, adjustments.signalStrength));
    }
}

class MarketConditionAnalyzer {
    async assessConditions(symbol, marketData) {
        // Simplified market condition assessment
        // In a real implementation, this would be much more sophisticated
        
        const condition = {
            summary: 'normal',
            volatility: { level: 'normal', value: 0.5 },
            volume: { level: 'normal', value: 0.5 },
            marketHours: { isOpen: true },
            trend: { direction: 'neutral', strength: 0.5 }
        };
        
        if (marketData && marketData.bars && marketData.bars.length > 20) {
            const bars = marketData.bars.slice(-20);
            
            // Calculate volatility
            const returns = bars.slice(1).map((bar, i) => 
                (bar.close - bars[i].close) / bars[i].close
            );
            const volatility = Math.sqrt(returns.reduce((sum, r) => sum + r * r, 0) / returns.length);
            
            condition.volatility.value = volatility;
            if (volatility > 0.02) {
                condition.volatility.level = 'high';
            } else if (volatility < 0.005) {
                condition.volatility.level = 'low';
            }
            
            // Calculate average volume
            const avgVolume = bars.reduce((sum, bar) => sum + bar.volume, 0) / bars.length;
            const currentVolume = bars[bars.length - 1].volume;
            const volumeRatio = currentVolume / avgVolume;
            
            condition.volume.value = volumeRatio;
            if (volumeRatio > 1.5) {
                condition.volume.level = 'high';
            } else if (volumeRatio < 0.5) {
                condition.volume.level = 'low';
            }
        }
        
        return condition;
    }
}

class PerformanceTracker {
    constructor() {
        this.outcomes = [];
        this.metrics = {
            totalSignals: 0,
            successfulSignals: 0,
            failedSignals: 0,
            avgProfitLoss: 0,
            winRate: 0,
            improvementRate: 0
        };
    }
    
    recordOutcome(signalRecord) {
        this.outcomes.push(signalRecord);
        this.updateMetrics();
    }
    
    updateMetrics() {
        const outcomes = this.outcomes.filter(o => o.successful !== null);
        
        this.metrics.totalSignals = outcomes.length;
        this.metrics.successfulSignals = outcomes.filter(o => o.successful).length;
        this.metrics.failedSignals = outcomes.filter(o => !o.successful).length;
        this.metrics.winRate = this.metrics.totalSignals > 0 ? 
            this.metrics.successfulSignals / this.metrics.totalSignals : 0;
        
        // Calculate average profit/loss if available
        const profitLossData = outcomes.filter(o => o.profitLoss !== null);
        if (profitLossData.length > 0) {
            this.metrics.avgProfitLoss = profitLossData.reduce((sum, o) => sum + o.profitLoss, 0) / profitLossData.length;
        }
    }
    
    getImprovementMetrics() {
        // Calculate improvement over time
        // This would compare recent performance to historical baseline
        return {
            currentWinRate: this.metrics.winRate,
            targetImprovement: 0.25, // 25% reduction in losing trades
            actualImprovement: this.metrics.improvementRate,
            performanceGrade: this.calculatePerformanceGrade()
        };
    }
    
    calculatePerformanceGrade() {
        if (this.metrics.winRate >= 0.75) return 'A';
        if (this.metrics.winRate >= 0.65) return 'B';
        if (this.metrics.winRate >= 0.55) return 'C';
        if (this.metrics.winRate >= 0.45) return 'D';
        return 'F';
    }
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        ConsensusEngine,
        ValidationRuleEngine,
        AdaptiveThresholdManager,
        MarketConditionAnalyzer,
        PerformanceTracker
    };
}

// Global assignment for direct HTML inclusion
if (typeof window !== 'undefined') {
    window.ConsensusEngine = ConsensusEngine;
    window.ValidationRuleEngine = ValidationRuleEngine;
    window.AdaptiveThresholdManager = AdaptiveThresholdManager;
    window.MarketConditionAnalyzer = MarketConditionAnalyzer;
    window.PerformanceTracker = PerformanceTracker;
}