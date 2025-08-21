/**
 * Volume Confirmation Dashboard Component
 * 
 * Provides real-time volume analysis and confirmation status display
 * for the trading dashboard.
 * 
 * Features:
 * - Real-time volume indicators
 * - Volume confirmation status
 * - Volume profile levels
 * - Historical performance metrics
 */

class VolumeDashboard {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.options = {
            updateInterval: 1000,
            showVolumeProfile: true,
            showPerformanceMetrics: true,
            ...options
        };
        
        this.volumeData = {};
        this.performanceData = {};
        this.updateInterval = null;
        
        this.init();
    }
    
    init() {
        this.createLayout();
        this.startUpdating();
    }
    
    createLayout() {
        this.container.innerHTML = `
            <div class="volume-dashboard">
                <div class="volume-header">
                    <h3>Volume Confirmation System</h3>
                    <div class="volume-status" id="volume-status">
                        <span class="status-indicator" id="status-indicator"></span>
                        <span class="status-text" id="status-text">Checking...</span>
                    </div>
                </div>
                
                <div class="volume-metrics-grid">
                    <div class="metric-card">
                        <div class="metric-label">Current Volume</div>
                        <div class="metric-value" id="current-volume">-</div>
                        <div class="metric-change" id="volume-change">-</div>
                    </div>
                    
                    <div class="metric-card">
                        <div class="metric-label">Volume Ratio</div>
                        <div class="metric-value" id="volume-ratio">-</div>
                        <div class="metric-threshold">Threshold: <span id="volume-threshold">1.2</span></div>
                    </div>
                    
                    <div class="metric-card">
                        <div class="metric-label">Relative Volume</div>
                        <div class="metric-value" id="relative-volume">-</div>
                        <div class="metric-strength" id="volume-strength">-</div>
                    </div>
                    
                    <div class="metric-card">
                        <div class="metric-label">Volume Trend</div>
                        <div class="metric-value" id="volume-trend">-</div>
                        <div class="metric-description" id="trend-description">-</div>
                    </div>
                </div>
                
                <div class="volume-profile-section" id="volume-profile-section">
                    <h4>Volume Profile Levels</h4>
                    <div class="profile-levels">
                        <div class="support-levels">
                            <div class="level-header">Support Levels</div>
                            <div class="level-list" id="support-levels">-</div>
                        </div>
                        <div class="resistance-levels">
                            <div class="level-header">Resistance Levels</div>
                            <div class="level-list" id="resistance-levels">-</div>
                        </div>
                    </div>
                </div>
                
                <div class="performance-section" id="performance-section">
                    <h4>Volume Confirmation Performance</h4>
                    <div class="performance-grid">
                        <div class="perf-metric">
                            <div class="perf-label">Confirmation Rate</div>
                            <div class="perf-value" id="confirmation-rate">-</div>
                        </div>
                        <div class="perf-metric">
                            <div class="perf-label">False Signal Reduction</div>
                            <div class="perf-value" id="false-signal-reduction">-</div>
                        </div>
                        <div class="perf-metric">
                            <div class="perf-label">Win Rate Improvement</div>
                            <div class="perf-value" id="win-rate-improvement">-</div>
                        </div>
                    </div>
                </div>
                
                <div class="volume-chart-container" id="volume-chart-container">
                    <canvas id="volume-chart" width="400" height="200"></canvas>
                </div>
            </div>
        `;
        
        this.addStyles();
    }
    
    addStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .volume-dashboard {
                background: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 20px;
                margin: 10px 0;
            }
            
            .volume-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 20px;
                padding-bottom: 10px;
                border-bottom: 1px solid #dee2e6;
            }
            
            .volume-status {
                display: flex;
                align-items: center;
                gap: 8px;
            }
            
            .status-indicator {
                width: 12px;
                height: 12px;
                border-radius: 50%;
                background: #6c757d;
            }
            
            .status-indicator.confirmed {
                background: #28a745;
                box-shadow: 0 0 8px rgba(40, 167, 69, 0.5);
            }
            
            .status-indicator.rejected {
                background: #dc3545;
            }
            
            .status-indicator.checking {
                background: #ffc107;
                animation: pulse 1.5s infinite;
            }
            
            @keyframes pulse {
                0% { opacity: 1; }
                50% { opacity: 0.5; }
                100% { opacity: 1; }
            }
            
            .volume-metrics-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin-bottom: 20px;
            }
            
            .metric-card {
                background: white;
                padding: 15px;
                border-radius: 6px;
                border: 1px solid #e9ecef;
                text-align: center;
            }
            
            .metric-label {
                font-size: 12px;
                color: #6c757d;
                margin-bottom: 5px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            
            .metric-value {
                font-size: 24px;
                font-weight: bold;
                color: #495057;
                margin-bottom: 5px;
            }
            
            .metric-change, .metric-threshold, .metric-strength, .metric-description {
                font-size: 11px;
                color: #6c757d;
            }
            
            .metric-change.positive {
                color: #28a745;
            }
            
            .metric-change.negative {
                color: #dc3545;
            }
            
            .volume-profile-section, .performance-section {
                background: white;
                padding: 15px;
                border-radius: 6px;
                border: 1px solid #e9ecef;
                margin-bottom: 20px;
            }
            
            .profile-levels {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
                margin-top: 10px;
            }
            
            .level-header {
                font-weight: bold;
                margin-bottom: 8px;
                color: #495057;
            }
            
            .level-list {
                font-family: monospace;
                font-size: 12px;
                line-height: 1.4;
            }
            
            .performance-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                gap: 15px;
                margin-top: 10px;
            }
            
            .perf-metric {
                text-align: center;
            }
            
            .perf-label {
                font-size: 11px;
                color: #6c757d;
                margin-bottom: 5px;
                text-transform: uppercase;
            }
            
            .perf-value {
                font-size: 18px;
                font-weight: bold;
                color: #495057;
            }
            
            .perf-value.positive {
                color: #28a745;
            }
            
            .perf-value.negative {
                color: #dc3545;
            }
            
            .volume-chart-container {
                background: white;
                padding: 15px;
                border-radius: 6px;
                border: 1px solid #e9ecef;
                text-align: center;
            }
            
            #volume-chart {
                max-width: 100%;
                height: auto;
            }
        `;
        
        document.head.appendChild(style);
    }
    
    async updateVolumeData() {
        try {
            const response = await fetch('/api/volume-dashboard-data');
            if (!response.ok) throw new Error('Failed to fetch volume data');
            
            const data = await response.json();
            this.volumeData = data.volume_analysis || {};
            this.performanceData = data.performance || {};
            
            this.updateDisplay();
        } catch (error) {
            console.error('Error updating volume data:', error);
            this.showError();
        }
    }
    
    updateDisplay() {
        this.updateStatus();
        this.updateMetrics();
        this.updateProfileLevels();
        this.updatePerformanceMetrics();
        this.updateChart();
    }
    
    updateStatus() {
        const statusIndicator = document.getElementById('status-indicator');
        const statusText = document.getElementById('status-text');
        
        if (this.volumeData.volume_confirmed) {
            statusIndicator.className = 'status-indicator confirmed';
            statusText.textContent = 'Volume Confirmed';
            statusText.style.color = '#28a745';
        } else if (this.volumeData.volume_ratio !== undefined) {
            statusIndicator.className = 'status-indicator rejected';
            statusText.textContent = 'Volume Not Confirmed';
            statusText.style.color = '#dc3545';
        } else {
            statusIndicator.className = 'status-indicator checking';
            statusText.textContent = 'Checking Volume...';
            statusText.style.color = '#ffc107';
        }
    }
    
    updateMetrics() {
        // Current Volume
        const currentVolume = this.volumeData.current_volume || 0;
        document.getElementById('current-volume').textContent = this.formatNumber(currentVolume);
        
        // Volume Ratio
        const volumeRatio = this.volumeData.volume_ratio || 0;
        const volumeRatioEl = document.getElementById('volume-ratio');
        volumeRatioEl.textContent = volumeRatio.toFixed(2) + 'x';
        
        const threshold = this.volumeData.confirmation_threshold || 1.2;
        document.getElementById('volume-threshold').textContent = threshold.toFixed(1);
        
        if (volumeRatio >= threshold) {
            volumeRatioEl.style.color = '#28a745';
        } else {
            volumeRatioEl.style.color = '#dc3545';
        }
        
        // Relative Volume
        const relativeVolume = this.volumeData.relative_volume || 0;
        document.getElementById('relative-volume').textContent = relativeVolume.toFixed(2) + 'x';
        
        const volumeStrength = this.volumeData.volume_strength || 'unknown';
        document.getElementById('volume-strength').textContent = this.formatStrength(volumeStrength);
        
        // Volume Trend
        const volumeTrend = this.volumeData.volume_trend || 'unknown';
        document.getElementById('volume-trend').textContent = this.formatTrend(volumeTrend);
        document.getElementById('trend-description').textContent = this.getTrendDescription(volumeTrend);
    }
    
    updateProfileLevels() {
        const profileLevels = this.volumeData.profile_levels || { support: [], resistance: [] };
        
        // Support levels
        const supportLevels = profileLevels.support || [];
        const supportHtml = supportLevels.length > 0
            ? supportLevels.map((level, i) => `$${level.toFixed(2)}`).join('<br>')
            : 'No levels detected';
        document.getElementById('support-levels').innerHTML = supportHtml;
        
        // Resistance levels
        const resistanceLevels = profileLevels.resistance || [];
        const resistanceHtml = resistanceLevels.length > 0
            ? resistanceLevels.map((level, i) => `$${level.toFixed(2)}`).join('<br>')
            : 'No levels detected';
        document.getElementById('resistance-levels').innerHTML = resistanceHtml;
    }
    
    updatePerformanceMetrics() {
        if (!this.performanceData || Object.keys(this.performanceData).length === 0) {
            return;
        }
        
        // Confirmation Rate
        const confirmationRate = this.performanceData.confirmation_rate || 0;
        const confirmationRateEl = document.getElementById('confirmation-rate');
        confirmationRateEl.textContent = (confirmationRate * 100).toFixed(1) + '%';
        
        // False Signal Reduction
        const falseSignalReduction = this.performanceData.false_signal_reduction || 0;
        const falseSignalEl = document.getElementById('false-signal-reduction');
        falseSignalEl.textContent = (falseSignalReduction * 100).toFixed(1) + '%';
        falseSignalEl.className = falseSignalReduction > 0.3 ? 'perf-value positive' : 'perf-value';
        
        // Win Rate Improvement
        const winRateImprovement = this.performanceData.win_rate_improvement || 0;
        const winRateEl = document.getElementById('win-rate-improvement');
        winRateEl.textContent = (winRateImprovement * 100).toFixed(1) + '%';
        winRateEl.className = winRateImprovement > 0 ? 'perf-value positive' : 'perf-value negative';
    }
    
    updateChart() {
        // Simple volume chart using canvas
        const canvas = document.getElementById('volume-chart');
        const ctx = canvas.getContext('2d');
        
        // Clear canvas
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        if (!this.volumeData.volume_history) {
            ctx.fillStyle = '#6c757d';
            ctx.font = '14px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('Volume chart data not available', canvas.width / 2, canvas.height / 2);
            return;
        }
        
        // Draw simple volume bars (placeholder implementation)
        const volumeHistory = this.volumeData.volume_history || [];
        if (volumeHistory.length > 0) {
            const maxVolume = Math.max(...volumeHistory);
            const barWidth = canvas.width / volumeHistory.length;
            
            volumeHistory.forEach((volume, i) => {
                const barHeight = (volume / maxVolume) * (canvas.height - 20);
                const x = i * barWidth;
                const y = canvas.height - barHeight - 10;
                
                ctx.fillStyle = volume > (this.volumeData.volume_ma || 0) ? '#28a745' : '#6c757d';
                ctx.fillRect(x, y, barWidth - 1, barHeight);
            });
        }
    }
    
    formatNumber(num) {
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        } else if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toString();
    }
    
    formatStrength(strength) {
        const strengthMap = {
            'very_low': 'Very Low',
            'low': 'Low',
            'normal': 'Normal',
            'high': 'High',
            'very_high': 'Very High',
            'unknown': 'Unknown'
        };
        return strengthMap[strength] || strength;
    }
    
    formatTrend(trend) {
        const trendMap = {
            'high': 'High',
            'normal': 'Normal',
            'low': 'Low',
            'unknown': 'Unknown'
        };
        return trendMap[trend] || trend;
    }
    
    getTrendDescription(trend) {
        const descriptions = {
            'high': 'Above average volume',
            'normal': 'Average volume levels',
            'low': 'Below average volume',
            'unknown': 'Insufficient data'
        };
        return descriptions[trend] || '';
    }
    
    showError() {
        document.getElementById('status-text').textContent = 'Error loading data';
        document.getElementById('status-indicator').className = 'status-indicator rejected';
    }
    
    startUpdating() {
        this.updateVolumeData();
        this.updateInterval = setInterval(() => {
            this.updateVolumeData();
        }, this.options.updateInterval);
    }
    
    stopUpdating() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
    }
    
    destroy() {
        this.stopUpdating();
        this.container.innerHTML = '';
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = VolumeDashboard;
}

// Global registration for direct HTML usage
if (typeof window !== 'undefined') {
    window.VolumeDashboard = VolumeDashboard;
}