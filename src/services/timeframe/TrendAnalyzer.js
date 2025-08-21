/**
 * Multi-Timeframe Trend Analyzer
 * ===============================
 * 
 * Analyzes trends across multiple timeframes using various technical indicators
 * Provides consensus-based trend direction and strength measurements
 */

class TrendAnalyzer {
    constructor(config = {}) {
        this.config = {
            timeframes: ['15m', '1h', '1d'],
            indicators: {
                ema: { fast: 9, slow: 21, signal: 9 },
                sma: { short: 10, medium: 20, long: 50 },
                rsi: { period: 14, overbought: 70, oversold: 30 },
                macd: { fast: 12, slow: 26, signal: 9 },
                stochRSI: { period: 14, k: 3, d: 3 },
                adx: { period: 14, threshold: 25 }
            },
            weights: {
                '15m': 1.0,
                '1h': 1.5,
                '1d': 2.0
            },
            trendStrengthThreshold: 0.6,
            consensusThreshold: 0.75,
            ...config
        };
        
        // Trend state tracking
        this.trendCache = new Map(); // symbol -> timeframe -> trend data
        this.consensusCache = new Map(); // symbol -> consensus data
        this.performanceMetrics = {
            analysisCount: 0,
            consensusAchieved: 0,
            trendChanges: 0,
            avgProcessingTime: 0
        };
        
        // Technical indicator calculators
        this.indicators = {
            ema: new EMACalculator(),
            sma: new SMACalculator(),
            rsi: new RSICalculator(),
            macd: new MACDCalculator(),
            stochRSI: new StochRSICalculator(),
            adx: new ADXCalculator()
        };
        
        this.initialize();
    }
    
    /**
     * Initialize the trend analyzer
     */
    initialize() {
        console.log('📈 TrendAnalyzer initialized with timeframes:', this.config.timeframes);
    }
    
    /**
     * Analyze trend for a single timeframe
     */
    analyzeTrend(symbol, timeframe, marketData) {
        const startTime = performance.now();
        
        try {
            if (!marketData || !marketData.bars || marketData.bars.length < 50) {
                throw new Error('Insufficient data for trend analysis');
            }
            
            const bars = marketData.bars;
            const closes = bars.map(bar => bar.close);
            const highs = bars.map(bar => bar.high);
            const lows = bars.map(bar => bar.low);
            const volumes = bars.map(bar => bar.volume);
            
            // Calculate all indicators
            const indicators = this.calculateIndicators(closes, highs, lows, volumes);
            
            // Determine trend direction and strength
            const trend = this.determineTrend(indicators, timeframe);
            
            // Cache the result
            this.cacheTrendData(symbol, timeframe, trend);
            
            // Update performance metrics
            const processingTime = performance.now() - startTime;
            this.updatePerformanceMetrics(processingTime);
            
            return trend;
            
        } catch (error) {
            console.error(`❌ Error analyzing trend for ${symbol}/${timeframe}:`, error);
            return this.createNeutralTrend(timeframe);
        }
    }
    
    /**
     * Analyze trends across all timeframes for a symbol
     */
    async analyzeMultiTimeframeTrend(symbol, timeframeData) {
        const trends = {};
        
        // Analyze each timeframe
        for (const [timeframe, data] of Object.entries(timeframeData)) {
            if (data && this.config.timeframes.includes(timeframe)) {
                trends[timeframe] = this.analyzeTrend(symbol, timeframe, data);
            }
        }
        
        // Calculate consensus
        const consensus = this.calculateConsensus(symbol, trends);
        
        // Cache consensus result
        this.consensusCache.set(symbol, {
            ...consensus,
            timestamp: Date.now(),
            timeframes: Object.keys(trends)
        });
        
        return {
            trends,
            consensus,
            symbol,
            timestamp: Date.now()
        };
    }
    
    /**
     * Calculate technical indicators
     */
    calculateIndicators(closes, highs, lows, volumes) {
        const indicators = {};
        
        try {
            // EMA indicators
            indicators.ema = {
                fast: this.indicators.ema.calculate(closes, this.config.indicators.ema.fast),
                slow: this.indicators.ema.calculate(closes, this.config.indicators.ema.slow),
                signal: this.indicators.ema.calculate(closes, this.config.indicators.ema.signal)
            };
            
            // SMA indicators
            indicators.sma = {
                short: this.indicators.sma.calculate(closes, this.config.indicators.sma.short),
                medium: this.indicators.sma.calculate(closes, this.config.indicators.sma.medium),
                long: this.indicators.sma.calculate(closes, this.config.indicators.sma.long)
            };
            
            // RSI
            indicators.rsi = this.indicators.rsi.calculate(closes, this.config.indicators.rsi.period);
            
            // MACD
            indicators.macd = this.indicators.macd.calculate(
                closes, 
                this.config.indicators.macd.fast,
                this.config.indicators.macd.slow,
                this.config.indicators.macd.signal
            );
            
            // Stochastic RSI
            indicators.stochRSI = this.indicators.stochRSI.calculate(
                closes,
                this.config.indicators.stochRSI.period,
                this.config.indicators.stochRSI.k,
                this.config.indicators.stochRSI.d
            );
            
            // ADX (Average Directional Index)
            indicators.adx = this.indicators.adx.calculate(
                highs, lows, closes,
                this.config.indicators.adx.period
            );
            
        } catch (error) {
            console.error('❌ Error calculating indicators:', error);
        }
        
        return indicators;
    }
    
    /**
     * Determine trend direction and strength from indicators
     */
    determineTrend(indicators, timeframe) {
        const signals = [];
        let totalWeight = 0;
        let bullishWeight = 0;
        let bearishWeight = 0;
        
        // EMA trend analysis
        if (indicators.ema && indicators.ema.fast && indicators.ema.slow) {
            const emaFast = indicators.ema.fast.slice(-1)[0];
            const emaSlow = indicators.ema.slow.slice(-1)[0];
            
            if (emaFast > emaSlow) {
                bullishWeight += 2;
                signals.push({ type: 'EMA', direction: 'bullish', strength: 0.8 });
            } else {
                bearishWeight += 2;
                signals.push({ type: 'EMA', direction: 'bearish', strength: 0.8 });
            }
            totalWeight += 2;
        }
        
        // SMA trend analysis
        if (indicators.sma && indicators.sma.short && indicators.sma.medium && indicators.sma.long) {
            const smaShort = indicators.sma.short.slice(-1)[0];
            const smaMedium = indicators.sma.medium.slice(-1)[0];
            const smaLong = indicators.sma.long.slice(-1)[0];
            
            if (smaShort > smaMedium && smaMedium > smaLong) {
                bullishWeight += 3;
                signals.push({ type: 'SMA', direction: 'bullish', strength: 0.9 });
            } else if (smaShort < smaMedium && smaMedium < smaLong) {
                bearishWeight += 3;
                signals.push({ type: 'SMA', direction: 'bearish', strength: 0.9 });
            } else {
                // Mixed signals
                signals.push({ type: 'SMA', direction: 'neutral', strength: 0.3 });
            }
            totalWeight += 3;
        }
        
        // RSI momentum analysis
        if (indicators.rsi && indicators.rsi.length > 0) {
            const rsi = indicators.rsi.slice(-1)[0];
            const rsiPrev = indicators.rsi.slice(-2)[0] || rsi;
            
            if (rsi > 50 && rsi > rsiPrev) {
                bullishWeight += 1;
                signals.push({ type: 'RSI', direction: 'bullish', strength: (rsi - 50) / 50 });
            } else if (rsi < 50 && rsi < rsiPrev) {
                bearishWeight += 1;
                signals.push({ type: 'RSI', direction: 'bearish', strength: (50 - rsi) / 50 });
            }
            totalWeight += 1;
        }
        
        // MACD trend analysis
        if (indicators.macd && indicators.macd.macd && indicators.macd.signal) {
            const macd = indicators.macd.macd.slice(-1)[0];
            const signal = indicators.macd.signal.slice(-1)[0];
            const histogram = indicators.macd.histogram.slice(-1)[0];
            
            if (macd > signal && histogram > 0) {
                bullishWeight += 2;
                signals.push({ type: 'MACD', direction: 'bullish', strength: 0.7 });
            } else if (macd < signal && histogram < 0) {
                bearishWeight += 2;
                signals.push({ type: 'MACD', direction: 'bearish', strength: 0.7 });
            }
            totalWeight += 2;
        }
        
        // ADX trend strength
        let trendStrength = 0.5;
        if (indicators.adx && indicators.adx.adx && indicators.adx.adx.length > 0) {
            const adx = indicators.adx.adx.slice(-1)[0];
            trendStrength = Math.min(adx / 50, 1.0); // Normalize ADX to 0-1
            
            if (adx > this.config.indicators.adx.threshold) {
                signals.push({ type: 'ADX', direction: 'strong', strength: trendStrength });
            }
        }
        
        // Calculate overall trend
        const netWeight = bullishWeight - bearishWeight;
        const trendDirection = netWeight > 0 ? 'bullish' : netWeight < 0 ? 'bearish' : 'neutral';
        const confidence = totalWeight > 0 ? Math.abs(netWeight) / totalWeight : 0;
        
        return {
            timeframe,
            direction: trendDirection,
            strength: trendStrength,
            confidence: confidence,
            weight: this.config.weights[timeframe] || 1.0,
            signals: signals,
            indicators: indicators,
            timestamp: Date.now(),
            metadata: {
                totalWeight,
                bullishWeight,
                bearishWeight,
                netWeight,
                signalCount: signals.length
            }
        };
    }
    
    /**
     * Calculate consensus across timeframes
     */
    calculateConsensus(symbol, trends) {
        const validTrends = Object.values(trends).filter(trend => trend && trend.direction !== 'neutral');
        
        if (validTrends.length === 0) {
            return this.createNeutralConsensus();
        }
        
        let totalWeight = 0;
        let bullishWeight = 0;
        let bearishWeight = 0;
        let totalStrength = 0;
        let totalConfidence = 0;
        
        // Calculate weighted scores
        validTrends.forEach(trend => {
            const weight = trend.weight * trend.confidence;
            totalWeight += weight;
            totalStrength += trend.strength * weight;
            totalConfidence += trend.confidence * weight;
            
            if (trend.direction === 'bullish') {
                bullishWeight += weight;
            } else if (trend.direction === 'bearish') {
                bearishWeight += weight;
            }
        });
        
        // Determine consensus
        const netWeight = bullishWeight - bearishWeight;
        const consensusDirection = netWeight > 0 ? 'bullish' : netWeight < 0 ? 'bearish' : 'neutral';
        const consensusStrength = totalWeight > 0 ? totalStrength / totalWeight : 0;
        const consensusConfidence = totalWeight > 0 ? totalConfidence / totalWeight : 0;
        
        // Check if consensus threshold is met
        const agreement = totalWeight > 0 ? Math.abs(netWeight) / totalWeight : 0;
        const consensusAchieved = agreement >= this.config.consensusThreshold && 
                                  consensusStrength >= this.config.trendStrengthThreshold;
        
        // Update performance metrics
        if (consensusAchieved) {
            this.performanceMetrics.consensusAchieved++;
        }
        
        return {
            direction: consensusDirection,
            strength: consensusStrength,
            confidence: consensusConfidence,
            agreement: agreement,
            consensusAchieved: consensusAchieved,
            timeframeCount: validTrends.length,
            weightedScore: netWeight,
            trends: trends,
            metadata: {
                totalWeight,
                bullishWeight,
                bearishWeight,
                validTrends: validTrends.length,
                requiredAgreement: this.config.consensusThreshold,
                requiredStrength: this.config.trendStrengthThreshold
            }
        };
    }
    
    /**
     * Get trend consensus for a symbol
     */
    getTrendConsensus(symbol) {
        return this.consensusCache.get(symbol) || this.createNeutralConsensus();
    }
    
    /**
     * Get trend data for specific timeframe
     */
    getTrendData(symbol, timeframe) {
        const symbolCache = this.trendCache.get(symbol);
        return symbolCache ? symbolCache.get(timeframe) : null;
    }
    
    /**
     * Check if trends are aligned across timeframes
     */
    checkTrendAlignment(symbol, requiredTimeframes = null) {
        const targetTimeframes = requiredTimeframes || this.config.timeframes;
        const symbolCache = this.trendCache.get(symbol);
        
        if (!symbolCache) {
            return { aligned: false, reason: 'No trend data available' };
        }
        
        const trends = targetTimeframes
            .map(tf => symbolCache.get(tf))
            .filter(trend => trend && trend.direction !== 'neutral');
        
        if (trends.length < 2) {
            return { aligned: false, reason: 'Insufficient trend data' };
        }
        
        // Check if all trends agree on direction
        const directions = trends.map(trend => trend.direction);
        const uniqueDirections = [...new Set(directions)];
        
        if (uniqueDirections.length === 1) {
            const avgStrength = trends.reduce((sum, trend) => sum + trend.strength, 0) / trends.length;
            const avgConfidence = trends.reduce((sum, trend) => sum + trend.confidence, 0) / trends.length;
            
            return {
                aligned: true,
                direction: uniqueDirections[0],
                strength: avgStrength,
                confidence: avgConfidence,
                timeframes: targetTimeframes,
                trendCount: trends.length
            };
        }
        
        return {
            aligned: false,
            reason: 'Conflicting trend directions',
            directions: directions,
            timeframes: targetTimeframes
        };
    }
    
    /**
     * Cache trend data
     */
    cacheTrendData(symbol, timeframe, trendData) {
        if (!this.trendCache.has(symbol)) {
            this.trendCache.set(symbol, new Map());
        }
        
        this.trendCache.get(symbol).set(timeframe, trendData);
    }
    
    /**
     * Create neutral trend object
     */
    createNeutralTrend(timeframe) {
        return {
            timeframe,
            direction: 'neutral',
            strength: 0.5,
            confidence: 0.0,
            weight: this.config.weights[timeframe] || 1.0,
            signals: [],
            indicators: {},
            timestamp: Date.now(),
            metadata: {
                totalWeight: 0,
                bullishWeight: 0,
                bearishWeight: 0,
                netWeight: 0,
                signalCount: 0
            }
        };
    }
    
    /**
     * Create neutral consensus object
     */
    createNeutralConsensus() {
        return {
            direction: 'neutral',
            strength: 0.5,
            confidence: 0.0,
            agreement: 0.0,
            consensusAchieved: false,
            timeframeCount: 0,
            weightedScore: 0,
            trends: {},
            metadata: {
                totalWeight: 0,
                bullishWeight: 0,
                bearishWeight: 0,
                validTrends: 0,
                requiredAgreement: this.config.consensusThreshold,
                requiredStrength: this.config.trendStrengthThreshold
            }
        };
    }
    
    /**
     * Update performance metrics
     */
    updatePerformanceMetrics(processingTime) {
        this.performanceMetrics.analysisCount++;
        
        if (this.performanceMetrics.avgProcessingTime === 0) {
            this.performanceMetrics.avgProcessingTime = processingTime;
        } else {
            this.performanceMetrics.avgProcessingTime = 
                (this.performanceMetrics.avgProcessingTime * 0.9) + (processingTime * 0.1);
        }
    }
    
    /**
     * Get performance metrics
     */
    getPerformanceMetrics() {
        const consensusRate = this.performanceMetrics.analysisCount > 0 ?
            (this.performanceMetrics.consensusAchieved / this.performanceMetrics.analysisCount * 100) : 0;
        
        return {
            ...this.performanceMetrics,
            consensusRate: consensusRate.toFixed(2)
        };
    }
    
    /**
     * Clear cache for symbol
     */
    clearCache(symbol = null) {
        if (symbol) {
            this.trendCache.delete(symbol);
            this.consensusCache.delete(symbol);
        } else {
            this.trendCache.clear();
            this.consensusCache.clear();
        }
    }
    
    /**
     * Get status of trend analyzer
     */
    getStatus() {
        return {
            isRunning: true,
            cachedSymbols: this.trendCache.size,
            consensusCache: this.consensusCache.size,
            timeframes: this.config.timeframes,
            performanceMetrics: this.getPerformanceMetrics()
        };
    }
}

// Technical Indicator Calculators
class EMACalculator {
    calculate(prices, period) {
        if (prices.length < period) return [];
        
        const multiplier = 2 / (period + 1);
        const ema = [prices[0]];
        
        for (let i = 1; i < prices.length; i++) {
            ema.push((prices[i] * multiplier) + (ema[i - 1] * (1 - multiplier)));
        }
        
        return ema;
    }
}

class SMACalculator {
    calculate(prices, period) {
        if (prices.length < period) return [];
        
        const sma = [];
        for (let i = period - 1; i < prices.length; i++) {
            const sum = prices.slice(i - period + 1, i + 1).reduce((a, b) => a + b, 0);
            sma.push(sum / period);
        }
        
        return sma;
    }
}

class RSICalculator {
    calculate(prices, period = 14) {
        if (prices.length < period + 1) return [];
        
        const gains = [];
        const losses = [];
        
        for (let i = 1; i < prices.length; i++) {
            const change = prices[i] - prices[i - 1];
            gains.push(change > 0 ? change : 0);
            losses.push(change < 0 ? Math.abs(change) : 0);
        }
        
        const rsi = [];
        let avgGain = gains.slice(0, period).reduce((a, b) => a + b, 0) / period;
        let avgLoss = losses.slice(0, period).reduce((a, b) => a + b, 0) / period;
        
        rsi.push(100 - (100 / (1 + (avgGain / avgLoss))));
        
        for (let i = period; i < gains.length; i++) {
            avgGain = ((avgGain * (period - 1)) + gains[i]) / period;
            avgLoss = ((avgLoss * (period - 1)) + losses[i]) / period;
            rsi.push(100 - (100 / (1 + (avgGain / avgLoss))));
        }
        
        return rsi;
    }
}

class MACDCalculator {
    calculate(prices, fastPeriod = 12, slowPeriod = 26, signalPeriod = 9) {
        const emaCalculator = new EMACalculator();
        
        const emaFast = emaCalculator.calculate(prices, fastPeriod);
        const emaSlow = emaCalculator.calculate(prices, slowPeriod);
        
        const macd = [];
        const startIndex = Math.max(emaFast.length, emaSlow.length) - Math.min(emaFast.length, emaSlow.length);
        
        for (let i = startIndex; i < Math.min(emaFast.length, emaSlow.length); i++) {
            macd.push(emaFast[i] - emaSlow[i]);
        }
        
        const signal = emaCalculator.calculate(macd, signalPeriod);
        const histogram = [];
        
        for (let i = 0; i < signal.length; i++) {
            histogram.push(macd[macd.length - signal.length + i] - signal[i]);
        }
        
        return { macd, signal, histogram };
    }
}

class StochRSICalculator {
    calculate(prices, rsiPeriod = 14, stochPeriod = 14, kPeriod = 3, dPeriod = 3) {
        const rsiCalculator = new RSICalculator();
        const rsi = rsiCalculator.calculate(prices, rsiPeriod);
        
        if (rsi.length < stochPeriod) return { k: [], d: [] };
        
        const stochRSI = [];
        
        for (let i = stochPeriod - 1; i < rsi.length; i++) {
            const rsiSlice = rsi.slice(i - stochPeriod + 1, i + 1);
            const minRSI = Math.min(...rsiSlice);
            const maxRSI = Math.max(...rsiSlice);
            
            if (maxRSI === minRSI) {
                stochRSI.push(0);
            } else {
                stochRSI.push((rsi[i] - minRSI) / (maxRSI - minRSI) * 100);
            }
        }
        
        const smaCalculator = new SMACalculator();
        const k = smaCalculator.calculate(stochRSI, kPeriod);
        const d = smaCalculator.calculate(k, dPeriod);
        
        return { k, d, stochRSI };
    }
}

class ADXCalculator {
    calculate(highs, lows, closes, period = 14) {
        if (highs.length < period + 1) return { adx: [], di_plus: [], di_minus: [] };
        
        const tr = [];
        const dm_plus = [];
        const dm_minus = [];
        
        for (let i = 1; i < highs.length; i++) {
            // True Range
            const tr1 = highs[i] - lows[i];
            const tr2 = Math.abs(highs[i] - closes[i - 1]);
            const tr3 = Math.abs(lows[i] - closes[i - 1]);
            tr.push(Math.max(tr1, tr2, tr3));
            
            // Directional Movement
            const dmPlus = highs[i] - highs[i - 1] > lows[i - 1] - lows[i] ? 
                Math.max(highs[i] - highs[i - 1], 0) : 0;
            const dmMinus = lows[i - 1] - lows[i] > highs[i] - highs[i - 1] ? 
                Math.max(lows[i - 1] - lows[i], 0) : 0;
            
            dm_plus.push(dmPlus);
            dm_minus.push(dmMinus);
        }
        
        // Smooth the values
        const emaCalculator = new EMACalculator();
        const smoothedTR = emaCalculator.calculate(tr, period);
        const smoothedDMPlus = emaCalculator.calculate(dm_plus, period);
        const smoothedDMMinus = emaCalculator.calculate(dm_minus, period);
        
        const di_plus = [];
        const di_minus = [];
        const dx = [];
        
        for (let i = 0; i < smoothedTR.length; i++) {
            const diPlus = (smoothedDMPlus[i] / smoothedTR[i]) * 100;
            const diMinus = (smoothedDMMinus[i] / smoothedTR[i]) * 100;
            
            di_plus.push(diPlus);
            di_minus.push(diMinus);
            
            const sum = diPlus + diMinus;
            if (sum > 0) {
                dx.push((Math.abs(diPlus - diMinus) / sum) * 100);
            } else {
                dx.push(0);
            }
        }
        
        const adx = emaCalculator.calculate(dx, period);
        
        return { adx, di_plus, di_minus };
    }
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        TrendAnalyzer,
        EMACalculator,
        SMACalculator,
        RSICalculator,
        MACDCalculator,
        StochRSICalculator,
        ADXCalculator
    };
}

// Global assignment for direct HTML inclusion
if (typeof window !== 'undefined') {
    window.TrendAnalyzer = TrendAnalyzer;
    window.EMACalculator = EMACalculator;
    window.SMACalculator = SMACalculator;
    window.RSICalculator = RSICalculator;
    window.MACDCalculator = MACDCalculator;
    window.StochRSICalculator = StochRSICalculator;
    window.ADXCalculator = ADXCalculator;
}