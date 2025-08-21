/**
 * Timeframe Alignment Widget
 * ==========================
 * 
 * Visual component for displaying multi-timeframe trend alignment
 * Provides real-time visualization of consensus status and trend strength
 */

class TimeframeAlignmentWidget {
    constructor(containerId, options = {}) {
        this.containerId = containerId;
        this.options = {
            showTimeframeLabels: true,
            showStrengthBars: true,
            showConsensusIndicator: true,
            updateInterval: 1000,
            animationDuration: 300,
            colorScheme: {
                aligned: '#00ff00',
                partial: '#ffff00',
                misaligned: '#ff0000',
                neutral: '#888888',
                background: '#1a1a1a'
            },
            size: {
                width: 300,
                height: 200
            },
            ...options
        };
        
        this.container = null;
        this.alignmentData = {};
        this.isInitialized = false;
        
        // Event handlers
        this.eventHandlers = new Map();
        
        this.initialize();
    }
    
    /**
     * Initialize the widget
     */
    initialize() {
        this.container = document.getElementById(this.containerId);
        if (!this.container) {
            console.error(`❌ Container with ID '${this.containerId}' not found`);
            return;
        }
        
        this.createWidgetStructure();
        this.setupEventListeners();
        
        this.isInitialized = true;
        console.log('📊 TimeframeAlignmentWidget initialized');
    }
    
    /**
     * Create the widget HTML structure
     */
    createWidgetStructure() {
        this.container.innerHTML = `
            <div class="timeframe-alignment-widget" style="
                width: ${this.options.size.width}px;
                height: ${this.options.size.height}px;
                background: ${this.options.colorScheme.background};
                border-radius: 8px;
                padding: 16px;
                box-sizing: border-box;
                color: white;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                position: relative;
                overflow: hidden;
            ">
                <div class="widget-header" style="
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 12px;
                    font-size: 14px;
                    font-weight: bold;
                ">
                    <span>Timeframe Alignment</span>
                    <div class="consensus-indicator" style="
                        width: 12px;
                        height: 12px;
                        border-radius: 50%;
                        background: ${this.options.colorScheme.neutral};
                        transition: background-color ${this.options.animationDuration}ms ease;
                    "></div>
                </div>
                
                <div class="timeframes-container" style="
                    display: flex;
                    flex-direction: column;
                    gap: 8px;
                    height: calc(100% - 40px);
                ">
                    <!-- Timeframe rows will be populated here -->
                </div>
                
                <div class="widget-footer" style="
                    position: absolute;
                    bottom: 8px;
                    right: 12px;
                    font-size: 10px;
                    color: #888;
                ">
                    <span class="last-update">Never</span>
                </div>
            </div>
        `;
        
        this.createTimeframeRows();
    }
    
    /**
     * Create timeframe rows
     */
    createTimeframeRows() {
        const container = this.container.querySelector('.timeframes-container');
        const timeframes = ['15m', '1h', '1d'];
        
        timeframes.forEach(timeframe => {
            const row = document.createElement('div');
            row.className = `timeframe-row timeframe-${timeframe}`;
            row.style.cssText = `
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 6px 8px;
                background: rgba(255, 255, 255, 0.05);
                border-radius: 4px;
                transition: all ${this.options.animationDuration}ms ease;
                min-height: 28px;
            `;
            
            row.innerHTML = `
                <div class="timeframe-info" style="
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    flex: 1;
                ">
                    <span class="timeframe-label" style="
                        font-size: 12px;
                        font-weight: 500;
                        min-width: 25px;
                    ">${timeframe.toUpperCase()}</span>
                    
                    <div class="trend-indicator" style="
                        width: 8px;
                        height: 8px;
                        border-radius: 50%;
                        background: ${this.options.colorScheme.neutral};
                        transition: background-color ${this.options.animationDuration}ms ease;
                    "></div>
                    
                    <span class="trend-direction" style="
                        font-size: 10px;
                        color: #ccc;
                        flex: 1;
                    ">Neutral</span>
                </div>
                
                ${this.options.showStrengthBars ? `
                <div class="strength-container" style="
                    display: flex;
                    align-items: center;
                    gap: 4px;
                ">
                    <div class="strength-bar" style="
                        width: 40px;
                        height: 4px;
                        background: rgba(255, 255, 255, 0.1);
                        border-radius: 2px;
                        overflow: hidden;
                        position: relative;
                    ">
                        <div class="strength-fill" style="
                            height: 100%;
                            width: 0%;
                            background: ${this.options.colorScheme.neutral};
                            transition: all ${this.options.animationDuration}ms ease;
                            border-radius: 2px;
                        "></div>
                    </div>
                    <span class="strength-value" style="
                        font-size: 9px;
                        color: #999;
                        min-width: 25px;
                        text-align: right;
                    ">0%</span>
                </div>
                ` : ''}
            `;
            
            container.appendChild(row);
        });
    }
    
    /**
     * Update alignment data
     */
    updateAlignment(symbol, alignmentData) {
        if (!this.isInitialized) return;
        
        this.alignmentData[symbol] = {
            ...alignmentData,
            timestamp: Date.now()
        };
        
        this.renderAlignment(alignmentData);
        this.updateConsensusIndicator(alignmentData);
        this.updateLastUpdateTime();
        
        this.emit('alignmentUpdated', { symbol, alignmentData });
    }
    
    /**
     * Render alignment visualization
     */
    renderAlignment(alignmentData) {
        const { trends = {}, consensus = {} } = alignmentData;
        
        // Update each timeframe row
        Object.entries(trends).forEach(([timeframe, trendData]) => {
            this.updateTimeframeRow(timeframe, trendData);
        });
        
        // Update overall consensus
        this.updateConsensusDisplay(consensus);
    }
    
    /**
     * Update individual timeframe row
     */
    updateTimeframeRow(timeframe, trendData) {
        const row = this.container.querySelector(`.timeframe-${timeframe}`);
        if (!row) return;
        
        const indicator = row.querySelector('.trend-indicator');
        const direction = row.querySelector('.trend-direction');
        const strengthFill = row.querySelector('.strength-fill');
        const strengthValue = row.querySelector('.strength-value');
        
        // Update trend direction
        const directionText = this.formatDirection(trendData.direction);
        const directionColor = this.getTrendColor(trendData.direction);
        
        if (direction) {
            direction.textContent = directionText;
            direction.style.color = directionColor;
        }
        
        if (indicator) {
            indicator.style.background = directionColor;
        }
        
        // Update strength bar
        if (strengthFill && strengthValue) {
            const strength = (trendData.strength || 0) * 100;
            strengthFill.style.width = `${strength}%`;
            strengthFill.style.background = directionColor;
            strengthValue.textContent = `${Math.round(strength)}%`;
        }
        
        // Update row styling based on confidence
        const confidence = trendData.confidence || 0;
        row.style.opacity = Math.max(0.6, confidence);
        
        if (confidence > 0.7) {
            row.style.borderLeft = `3px solid ${directionColor}`;
        } else {
            row.style.borderLeft = 'none';
        }
    }
    
    /**
     * Update consensus indicator
     */
    updateConsensusIndicator(alignmentData) {
        const indicator = this.container.querySelector('.consensus-indicator');
        if (!indicator) return;
        
        const { consensus = {} } = alignmentData;
        
        let color = this.options.colorScheme.neutral;\n        \n        if (consensus.consensusAchieved) {\n            color = this.options.colorScheme.aligned;\n        } else if (consensus.agreement > 0.5) {\n            color = this.options.colorScheme.partial;\n        } else if (consensus.agreement > 0) {\n            color = this.options.colorScheme.misaligned;\n        }\n        \n        indicator.style.background = color;\n        indicator.title = this.getConsensusTooltip(consensus);\n    }\n    \n    /**\n     * Update consensus display\n     */\n    updateConsensusDisplay(consensus) {\n        // Add consensus summary if not exists\n        let summaryEl = this.container.querySelector('.consensus-summary');\n        if (!summaryEl) {\n            summaryEl = document.createElement('div');\n            summaryEl.className = 'consensus-summary';\n            summaryEl.style.cssText = `\n                font-size: 10px;\n                color: #ccc;\n                text-align: center;\n                margin-top: 8px;\n                padding: 4px;\n                background: rgba(255, 255, 255, 0.05);\n                border-radius: 4px;\n            `;\n            \n            const container = this.container.querySelector('.timeframes-container');\n            container.appendChild(summaryEl);\n        }\n        \n        // Update consensus text\n        const agreementPct = Math.round((consensus.agreement || 0) * 100);\n        const strengthPct = Math.round((consensus.strength || 0) * 100);\n        \n        summaryEl.innerHTML = `\n            <div>Agreement: ${agreementPct}%</div>\n            <div>Strength: ${strengthPct}%</div>\n            <div style=\"margin-top: 2px; font-weight: bold; color: ${this.getConsensusColor(consensus)};\">\n                ${consensus.consensusAchieved ? '✓ ALIGNED' : '✗ NOT ALIGNED'}\n            </div>\n        `;\n    }\n    \n    /**\n     * Format trend direction text\n     */\n    formatDirection(direction) {\n        switch (direction) {\n            case 'bullish': return '↗ Bullish';\n            case 'bearish': return '↘ Bearish';\n            case 'neutral': return '→ Neutral';\n            default: return '? Unknown';\n        }\n    }\n    \n    /**\n     * Get color for trend direction\n     */\n    getTrendColor(direction) {\n        switch (direction) {\n            case 'bullish': return this.options.colorScheme.aligned;\n            case 'bearish': return this.options.colorScheme.misaligned;\n            case 'neutral': return this.options.colorScheme.neutral;\n            default: return this.options.colorScheme.neutral;\n        }\n    }\n    \n    /**\n     * Get consensus color\n     */\n    getConsensusColor(consensus) {\n        if (consensus.consensusAchieved) {\n            return this.options.colorScheme.aligned;\n        } else if (consensus.agreement > 0.5) {\n            return this.options.colorScheme.partial;\n        } else {\n            return this.options.colorScheme.misaligned;\n        }\n    }\n    \n    /**\n     * Get consensus tooltip text\n     */\n    getConsensusTooltip(consensus) {\n        const agreement = Math.round((consensus.agreement || 0) * 100);\n        const strength = Math.round((consensus.strength || 0) * 100);\n        const status = consensus.consensusAchieved ? 'ALIGNED' : 'NOT ALIGNED';\n        \n        return `Consensus: ${status}\\nAgreement: ${agreement}%\\nStrength: ${strength}%`;\n    }\n    \n    /**\n     * Update last update timestamp\n     */\n    updateLastUpdateTime() {\n        const lastUpdateEl = this.container.querySelector('.last-update');\n        if (lastUpdateEl) {\n            const now = new Date();\n            lastUpdateEl.textContent = now.toLocaleTimeString();\n        }\n    }\n    \n    /**\n     * Set up event listeners\n     */\n    setupEventListeners() {\n        // Add click handlers for interactive features\n        this.container.addEventListener('click', (event) => {\n            const timeframeRow = event.target.closest('.timeframe-row');\n            if (timeframeRow) {\n                const timeframe = timeframeRow.className.match(/timeframe-([^\\s]+)/)[1];\n                this.emit('timeframeClicked', { timeframe });\n            }\n        });\n        \n        // Add hover effects\n        this.container.addEventListener('mouseover', (event) => {\n            const timeframeRow = event.target.closest('.timeframe-row');\n            if (timeframeRow) {\n                timeframeRow.style.background = 'rgba(255, 255, 255, 0.1)';\n            }\n        });\n        \n        this.container.addEventListener('mouseout', (event) => {\n            const timeframeRow = event.target.closest('.timeframe-row');\n            if (timeframeRow) {\n                timeframeRow.style.background = 'rgba(255, 255, 255, 0.05)';\n            }\n        });\n    }\n    \n    /**\n     * Show loading state\n     */\n    showLoading() {\n        const rows = this.container.querySelectorAll('.timeframe-row');\n        rows.forEach(row => {\n            row.style.opacity = '0.5';\n            const direction = row.querySelector('.trend-direction');\n            if (direction) {\n                direction.textContent = 'Loading...';\n            }\n        });\n    }\n    \n    /**\n     * Show error state\n     */\n    showError(message = 'Error loading data') {\n        const rows = this.container.querySelectorAll('.timeframe-row');\n        rows.forEach(row => {\n            row.style.opacity = '0.5';\n            const direction = row.querySelector('.trend-direction');\n            if (direction) {\n                direction.textContent = 'Error';\n                direction.style.color = this.options.colorScheme.misaligned;\n            }\n        });\n        \n        // Update consensus indicator\n        const indicator = this.container.querySelector('.consensus-indicator');\n        if (indicator) {\n            indicator.style.background = this.options.colorScheme.misaligned;\n            indicator.title = message;\n        }\n    }\n    \n    /**\n     * Reset widget to neutral state\n     */\n    reset() {\n        const rows = this.container.querySelectorAll('.timeframe-row');\n        rows.forEach(row => {\n            row.style.opacity = '1';\n            row.style.borderLeft = 'none';\n            \n            const indicator = row.querySelector('.trend-indicator');\n            const direction = row.querySelector('.trend-direction');\n            const strengthFill = row.querySelector('.strength-fill');\n            const strengthValue = row.querySelector('.strength-value');\n            \n            if (indicator) {\n                indicator.style.background = this.options.colorScheme.neutral;\n            }\n            if (direction) {\n                direction.textContent = 'Neutral';\n                direction.style.color = '#ccc';\n            }\n            if (strengthFill) {\n                strengthFill.style.width = '0%';\n            }\n            if (strengthValue) {\n                strengthValue.textContent = '0%';\n            }\n        });\n        \n        // Reset consensus indicator\n        const consensusIndicator = this.container.querySelector('.consensus-indicator');\n        if (consensusIndicator) {\n            consensusIndicator.style.background = this.options.colorScheme.neutral;\n            consensusIndicator.title = 'No data';\n        }\n        \n        // Clear consensus summary\n        const summary = this.container.querySelector('.consensus-summary');\n        if (summary) {\n            summary.remove();\n        }\n    }\n    \n    /**\n     * Update widget configuration\n     */\n    updateConfig(newOptions) {\n        this.options = { ...this.options, ...newOptions };\n        \n        // Re-create widget if structure options changed\n        if (newOptions.showStrengthBars !== undefined || newOptions.colorScheme) {\n            this.createWidgetStructure();\n        }\n    }\n    \n    /**\n     * Get current alignment data\n     */\n    getAlignmentData(symbol) {\n        return this.alignmentData[symbol] || null;\n    }\n    \n    /**\n     * Event handling\n     */\n    on(event, handler) {\n        if (!this.eventHandlers.has(event)) {\n            this.eventHandlers.set(event, new Set());\n        }\n        this.eventHandlers.get(event).add(handler);\n    }\n    \n    off(event, handler) {\n        if (this.eventHandlers.has(event)) {\n            this.eventHandlers.get(event).delete(handler);\n        }\n    }\n    \n    emit(event, data) {\n        if (this.eventHandlers.has(event)) {\n            this.eventHandlers.get(event).forEach(handler => {\n                try {\n                    handler(data);\n                } catch (error) {\n                    console.error(`❌ Event handler error for '${event}':`, error);\n                }\n            });\n        }\n    }\n    \n    /**\n     * Destroy widget\n     */\n    destroy() {\n        if (this.container) {\n            this.container.innerHTML = '';\n        }\n        \n        this.eventHandlers.clear();\n        this.alignmentData = {};\n        this.isInitialized = false;\n        \n        console.log('🗑️ TimeframeAlignmentWidget destroyed');\n    }\n}\n\n// Export for module systems\nif (typeof module !== 'undefined' && module.exports) {\n    module.exports = TimeframeAlignmentWidget;\n}\n\n// Global assignment for direct HTML inclusion\nif (typeof window !== 'undefined') {\n    window.TimeframeAlignmentWidget = TimeframeAlignmentWidget;\n}"