/**
 * Comprehensive Trading Signal Visualization Components
 * =====================================================
 * 
 * Features:
 * - Visual markers on charts (arrows, dots, triangles)
 * - Signal strength indicators with confidence scores
 * - Signal history table with filtering
 * - Performance tracking (win/loss analysis)
 * - Alert notifications for new signals
 * - Color-coded signal indicators
 * - Integration with Lightweight Charts
 */

class TradingSignalVisualization {
    constructor(chartContainer, options = {}) {
        this.chartContainer = chartContainer;
        this.chart = null;
        this.candleSeries = null;
        this.signalMarkers = [];
        this.signalHistory = [];
        this.performanceData = {};
        this.alertSystem = null;
        
        // Configuration
        this.config = {
            enableMarkers: true,
            enableStrengthIndicator: true,
            enableHistory: true,
            enablePerformanceTracking: true,
            enableAlerts: true,
            maxHistoryEntries: 1000,
            confidenceThreshold: 0.6,
            alertSoundEnabled: true,
            ...options
        };
        
        // Signal types and their visual properties
        this.signalTypes = {
            BUY: {
                color: '#10B981',
                marker: '▲',
                icon: '📈',
                sound: 'buy_signal.mp3'
            },
            SELL: {
                color: '#EF4444',
                marker: '▼',
                icon: '📉',
                sound: 'sell_signal.mp3'
            },
            OVERSOLD: {
                color: '#F59E0B',
                marker: '◆',
                icon: '⚠️',
                sound: 'oversold_signal.mp3'
            },
            OVERBOUGHT: {
                color: '#8B5CF6',
                marker: '◇',
                icon: '⚠️',
                sound: 'overbought_signal.mp3'
            },
            NEUTRAL: {
                color: '#6B7280',
                marker: '●',
                icon: '⚪',
                sound: null
            }
        };
        
        this.initialize();
    }
    
    initialize() {
        this.createChartInterface();
        this.createSignalStrengthIndicator();
        this.createSignalHistoryTable();
        this.createPerformanceTracker();
        this.createAlertSystem();
        this.setupEventListeners();
        
        console.log('🎯 Trading Signal Visualization initialized');
    }
    
    createChartInterface() {
        // Create main chart container
        this.chartWrapper = document.createElement('div');
        this.chartWrapper.className = 'signal-chart-wrapper';
        this.chartWrapper.innerHTML = `
            <div class="chart-header d-flex justify-content-between align-items-center mb-3">
                <h5><i class="bi bi-graph-up"></i> Trading Signals Chart</h5>
                <div class="chart-controls">
                    <div class="btn-group btn-group-sm" role="group">
                        <button class="btn btn-outline-primary" id="toggleMarkers">
                            <i class="bi bi-geo-alt"></i> Markers
                        </button>
                        <button class="btn btn-outline-info" id="toggleStrength">
                            <i class="bi bi-speedometer2"></i> Strength
                        </button>
                        <button class="btn btn-outline-success" id="clearSignals">
                            <i class="bi bi-eraser"></i> Clear
                        </button>
                    </div>
                </div>
            </div>
            <div class="chart-container" id="signalChart" style="height: 500px; width: 100%;"></div>
            <div class="chart-legend mt-2">
                <div class="d-flex flex-wrap gap-3">
                    <div class="legend-item">
                        <span class="signal-marker buy">▲</span> Buy Signal
                    </div>
                    <div class="legend-item">
                        <span class="signal-marker sell">▼</span> Sell Signal
                    </div>
                    <div class="legend-item">
                        <span class="signal-marker oversold">◆</span> Oversold
                    </div>
                    <div class="legend-item">
                        <span class="signal-marker overbought">◇</span> Overbought
                    </div>
                </div>
            </div>
        `;
        
        this.chartContainer.appendChild(this.chartWrapper);
        
        // Initialize Lightweight Charts
        this.chart = LightweightCharts.createChart(document.getElementById('signalChart'), {
            width: this.chartWrapper.offsetWidth,
            height: 500,
            layout: {
                backgroundColor: '#1a1a2e',
                textColor: '#d9d9d9',
            },
            grid: {
                vertLines: { color: '#2B2B43' },
                horzLines: { color: '#2B2B43' },
            },
            crosshair: {
                mode: LightweightCharts.CrosshairMode.Normal,
            },
            rightPriceScale: {
                borderColor: '#485158',
            },
            timeScale: {
                borderColor: '#485158',
            },
        });
        
        // Create candlestick series
        this.candleSeries = this.chart.addCandlestickSeries({
            upColor: '#26a69a',
            downColor: '#ef5350',
            borderVisible: false,
            wickUpColor: '#26a69a',
            wickDownColor: '#ef5350',
        });
        
        // Add volume series
        this.volumeSeries = this.chart.addHistogramSeries({
            color: '#26a69a',
            priceFormat: {
                type: 'volume',
            },
            priceScaleId: 'volume',
        });
        
        this.chart.priceScale('volume').applyOptions({
            scaleMargins: {
                top: 0.8,
                bottom: 0,
            },
        });
    }
    
    createSignalStrengthIndicator() {
        this.strengthIndicator = document.createElement('div');
        this.strengthIndicator.className = 'signal-strength-indicator card mt-3';
        this.strengthIndicator.innerHTML = `
            <div class="card-header">
                <h6><i class="bi bi-speedometer2"></i> Signal Strength Analysis</h6>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-6">
                        <div class="strength-gauge">
                            <canvas id="strengthGauge" width="200" height="100"></canvas>
                            <div class="text-center mt-2">
                                <div class="h4" id="strengthValue">0%</div>
                                <small class="text-muted">Confidence Score</small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="strength-details">
                            <div class="strength-component mb-2">
                                <div class="d-flex justify-content-between">
                                    <span>StochRSI:</span>
                                    <span id="stochRSIStrength">--</span>
                                </div>
                                <div class="progress" style="height: 4px;">
                                    <div class="progress-bar" id="stochRSIBar" style="width: 0%"></div>
                                </div>
                            </div>
                            <div class="strength-component mb-2">
                                <div class="d-flex justify-content-between">
                                    <span>EMA:</span>
                                    <span id="emaStrength">--</span>
                                </div>
                                <div class="progress" style="height: 4px;">
                                    <div class="progress-bar bg-info" id="emaBar" style="width: 0%"></div>
                                </div>
                            </div>
                            <div class="strength-component mb-2">
                                <div class="d-flex justify-content-between">
                                    <span>Volume:</span>
                                    <span id="volumeStrength">--</span>
                                </div>
                                <div class="progress" style="height: 4px;">
                                    <div class="progress-bar bg-warning" id="volumeBar" style="width: 0%"></div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        this.chartContainer.appendChild(this.strengthIndicator);
        this.initializeStrengthGauge();
    }
    
    createSignalHistoryTable() {
        this.historyTable = document.createElement('div');
        this.historyTable.className = 'signal-history-table card mt-3';
        this.historyTable.innerHTML = `
            <div class="card-header d-flex justify-content-between align-items-center">
                <h6><i class="bi bi-clock-history"></i> Signal History</h6>
                <div class="history-controls">
                    <div class="btn-group btn-group-sm" role="group">
                        <button class="btn btn-outline-primary" id="filterAll">All</button>
                        <button class="btn btn-outline-success" id="filterBuy">Buy</button>
                        <button class="btn btn-outline-danger" id="filterSell">Sell</button>
                        <button class="btn btn-outline-warning" id="filterOversold">Oversold</button>
                    </div>
                    <button class="btn btn-sm btn-outline-secondary ms-2" id="exportHistory">
                        <i class="bi bi-download"></i> Export
                    </button>
                </div>
            </div>
            <div class="card-body p-0">
                <div class="table-responsive" style="max-height: 400px;">
                    <table class="table table-dark table-hover mb-0">
                        <thead class="table-dark sticky-top">
                            <tr>
                                <th>Time</th>
                                <th>Symbol</th>
                                <th>Signal</th>
                                <th>Strength</th>
                                <th>Price</th>
                                <th>Reason</th>
                                <th>Performance</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody id="historyTableBody">
                            <tr>
                                <td colspan="8" class="text-center text-muted">No signals recorded yet</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        `;
        
        this.chartContainer.appendChild(this.historyTable);
    }
    
    createPerformanceTracker() {
        this.performanceTracker = document.createElement('div');
        this.performanceTracker.className = 'performance-tracker card mt-3';
        this.performanceTracker.innerHTML = `
            <div class="card-header">
                <h6><i class="bi bi-trophy"></i> Signal Performance Analysis</h6>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-3">
                        <div class="performance-stat text-center">
                            <div class="stat-value text-success" id="winRate">0%</div>
                            <div class="stat-label">Win Rate</div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="performance-stat text-center">
                            <div class="stat-value text-info" id="totalSignals">0</div>
                            <div class="stat-label">Total Signals</div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="performance-stat text-center">
                            <div class="stat-value text-primary" id="avgStrength">0%</div>
                            <div class="stat-label">Avg Strength</div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="performance-stat text-center">
                            <div class="stat-value" id="bestStrategy">--</div>
                            <div class="stat-label">Best Strategy</div>
                        </div>
                    </div>
                </div>
                <div class="row mt-3">
                    <div class="col-12">
                        <canvas id="performanceChart" height="100"></canvas>
                    </div>
                </div>
            </div>
        `;
        
        this.chartContainer.appendChild(this.performanceTracker);
        this.initializePerformanceChart();
    }
    
    createAlertSystem() {
        this.alertSystem = document.createElement('div');
        this.alertSystem.className = 'alert-system';
        this.alertSystem.innerHTML = `
            <div class="alert-container" id="alertContainer"></div>
            <div class="alert-settings d-none">
                <div class="card">
                    <div class="card-header">
                        <h6><i class="bi bi-bell"></i> Alert Settings</h6>
                    </div>
                    <div class="card-body">
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" id="enableAudio" checked>
                            <label class="form-check-label" for="enableAudio">
                                Audio Alerts
                            </label>
                        </div>
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" id="enableBrowser" checked>
                            <label class="form-check-label" for="enableBrowser">
                                Browser Notifications
                            </label>
                        </div>
                        <div class="mb-3">
                            <label for="minStrength" class="form-label">Minimum Signal Strength</label>
                            <input type="range" class="form-range" id="minStrength" min="0" max="100" value="60">
                            <div class="d-flex justify-content-between">
                                <small>0%</small>
                                <small>100%</small>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        this.chartContainer.appendChild(this.alertSystem);
        this.initializeNotifications();
    }
    
    setupEventListeners() {
        // Chart controls
        document.getElementById('toggleMarkers')?.addEventListener('click', () => {
            this.config.enableMarkers = !this.config.enableMarkers;
            this.toggleMarkers();
        });
        
        document.getElementById('toggleStrength')?.addEventListener('click', () => {
            this.config.enableStrengthIndicator = !this.config.enableStrengthIndicator;
            this.toggleStrengthIndicator();
        });
        
        document.getElementById('clearSignals')?.addEventListener('click', () => {
            this.clearAllSignals();
        });
        
        // History filters
        document.getElementById('filterAll')?.addEventListener('click', () => this.filterHistory('ALL'));
        document.getElementById('filterBuy')?.addEventListener('click', () => this.filterHistory('BUY'));
        document.getElementById('filterSell')?.addEventListener('click', () => this.filterHistory('SELL'));
        document.getElementById('filterOversold')?.addEventListener('click', () => this.filterHistory('OVERSOLD'));
        
        // Export functionality
        document.getElementById('exportHistory')?.addEventListener('click', () => {
            this.exportSignalHistory();
        });
        
        // Window resize handler
        window.addEventListener('resize', () => {
            if (this.chart) {
                this.chart.applyOptions({
                    width: this.chartWrapper.offsetWidth
                });
            }
        });
    }
    
    // Main method to add a new signal
    addSignal(signalData) {
        const signal = {
            id: Date.now() + Math.random(),
            timestamp: signalData.timestamp || Date.now(),
            symbol: signalData.symbol,
            type: signalData.type || 'NEUTRAL',
            strength: signalData.strength || 0,
            price: signalData.price || 0,
            reason: signalData.reason || '',
            indicators: signalData.indicators || {},
            performance: null,
            ...signalData
        };
        
        // Add to history
        this.signalHistory.unshift(signal);
        if (this.signalHistory.length > this.config.maxHistoryEntries) {
            this.signalHistory = this.signalHistory.slice(0, this.config.maxHistoryEntries);
        }
        
        // Add visual marker to chart
        if (this.config.enableMarkers) {
            this.addChartMarker(signal);
        }
        
        // Update strength indicator
        if (this.config.enableStrengthIndicator) {
            this.updateStrengthIndicator(signal);
        }
        
        // Update history table
        this.updateHistoryTable();
        
        // Show alert if strength is above threshold
        if (signal.strength >= this.config.confidenceThreshold) {
            this.showAlert(signal);
        }
        
        // Update performance data
        this.updatePerformanceData(signal);
        
        console.log('🎯 New signal added:', signal);
    }
    
    addChartMarker(signal) {
        const signalConfig = this.signalTypes[signal.type] || this.signalTypes.NEUTRAL;
        
        // Create marker for the chart
        const marker = {
            time: signal.timestamp / 1000, // Convert to seconds
            position: signal.type === 'BUY' || signal.type === 'OVERSOLD' ? 'belowBar' : 'aboveBar',
            color: signalConfig.color,
            shape: signal.type === 'BUY' ? 'arrowUp' : signal.type === 'SELL' ? 'arrowDown' : 'circle',
            text: `${signal.type} (${(signal.strength * 100).toFixed(0)}%)`,
            size: 1 + (signal.strength * 2) // Size based on strength
        };
        
        this.signalMarkers.push(marker);
        
        // Apply markers to candlestick series
        if (this.candleSeries) {
            this.candleSeries.setMarkers(this.signalMarkers);
        }
    }
    
    updateStrengthIndicator(signal) {
        // Update gauge
        this.drawStrengthGauge(signal.strength);
        
        // Update strength value
        document.getElementById('strengthValue').textContent = `${(signal.strength * 100).toFixed(0)}%`;
        
        // Update component strengths
        if (signal.indicators) {
            this.updateComponentStrengths(signal.indicators);
        }
    }
    
    updateComponentStrengths(indicators) {
        // StochRSI strength
        if (indicators.stochRSI) {
            const stochStrength = this.calculateStochRSIStrength(indicators.stochRSI);
            document.getElementById('stochRSIStrength').textContent = `${(stochStrength * 100).toFixed(0)}%`;
            document.getElementById('stochRSIBar').style.width = `${stochStrength * 100}%`;
        }
        
        // EMA strength
        if (indicators.ema) {
            const emaStrength = this.calculateEMAStrength(indicators.ema);
            document.getElementById('emaStrength').textContent = `${(emaStrength * 100).toFixed(0)}%`;
            document.getElementById('emaBar').style.width = `${emaStrength * 100}%`;
        }
        
        // Volume strength
        if (indicators.volume) {
            const volumeStrength = this.calculateVolumeStrength(indicators.volume);
            document.getElementById('volumeStrength').textContent = `${(volumeStrength * 100).toFixed(0)}%`;
            document.getElementById('volumeBar').style.width = `${volumeStrength * 100}%`;
        }
    }
    
    updateHistoryTable() {
        const tbody = document.getElementById('historyTableBody');
        if (!tbody) return;
        
        if (this.signalHistory.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">No signals recorded yet</td></tr>';
            return;
        }
        
        tbody.innerHTML = this.signalHistory.slice(0, 50).map(signal => {
            const signalConfig = this.signalTypes[signal.type] || this.signalTypes.NEUTRAL;
            const performanceClass = signal.performance ? 
                (signal.performance > 0 ? 'text-success' : 'text-danger') : 'text-muted';
            
            return `
                <tr data-signal-id="${signal.id}" data-signal-type="${signal.type}">
                    <td class="small">${new Date(signal.timestamp).toLocaleTimeString()}</td>
                    <td><span class="badge bg-secondary">${signal.symbol}</span></td>
                    <td>
                        <span class="signal-badge" style="color: ${signalConfig.color}">
                            ${signalConfig.marker} ${signal.type}
                        </span>
                    </td>
                    <td>
                        <div class="strength-bar-small">
                            <div class="strength-fill" style="width: ${signal.strength * 100}%; background-color: ${signalConfig.color}"></div>
                            <span class="strength-text">${(signal.strength * 100).toFixed(0)}%</span>
                        </div>
                    </td>
                    <td>$${signal.price.toFixed(4)}</td>
                    <td class="small">${signal.reason}</td>
                    <td class="${performanceClass}">
                        ${signal.performance ? (signal.performance > 0 ? '+' : '') + signal.performance.toFixed(2) + '%' : '--'}
                    </td>
                    <td>
                        <button class="btn btn-sm btn-outline-info" onclick="window.signalViz.showSignalDetails('${signal.id}')">
                            <i class="bi bi-eye"></i>
                        </button>
                    </td>
                </tr>
            `;
        }).join('');
    }
    
    initializeStrengthGauge() {
        this.gaugeCanvas = document.getElementById('strengthGauge');
        this.gaugeCtx = this.gaugeCanvas.getContext('2d');
        this.drawStrengthGauge(0);
    }
    
    drawStrengthGauge(strength) {
        const ctx = this.gaugeCtx;
        const canvas = this.gaugeCanvas;
        const centerX = canvas.width / 2;
        const centerY = canvas.height - 10;
        const radius = 80;
        
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        // Background arc
        ctx.beginPath();
        ctx.arc(centerX, centerY, radius, Math.PI, 0);
        ctx.strokeStyle = '#2B2B43';
        ctx.lineWidth = 10;
        ctx.stroke();
        
        // Strength arc
        const strengthAngle = Math.PI * strength;
        ctx.beginPath();
        ctx.arc(centerX, centerY, radius, Math.PI, Math.PI + strengthAngle);
        
        // Color based on strength
        let color;
        if (strength < 0.3) color = '#EF4444';
        else if (strength < 0.6) color = '#F59E0B';
        else color = '#10B981';
        
        ctx.strokeStyle = color;
        ctx.lineWidth = 10;
        ctx.stroke();
        
        // Needle
        const needleAngle = Math.PI + strengthAngle;
        ctx.beginPath();
        ctx.moveTo(centerX, centerY);
        ctx.lineTo(
            centerX + Math.cos(needleAngle) * (radius - 15),
            centerY + Math.sin(needleAngle) * (radius - 15)
        );
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 3;
        ctx.stroke();
        
        // Center circle
        ctx.beginPath();
        ctx.arc(centerX, centerY, 5, 0, 2 * Math.PI);
        ctx.fillStyle = '#ffffff';
        ctx.fill();
    }
    
    initializePerformanceChart() {
        const ctx = document.getElementById('performanceChart').getContext('2d');
        
        this.performanceChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Win Rate %',
                    data: [],
                    borderColor: '#10B981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    fill: true
                }, {
                    label: 'Signal Count',
                    data: [],
                    borderColor: '#3B82F6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    yAxisID: 'y1'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: {
                            color: '#d9d9d9'
                        }
                    }
                },
                scales: {
                    x: {
                        ticks: { color: '#d9d9d9' },
                        grid: { color: '#2B2B43' }
                    },
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        ticks: { color: '#d9d9d9' },
                        grid: { color: '#2B2B43' }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        ticks: { color: '#d9d9d9' },
                        grid: { drawOnChartArea: false }
                    }
                }
            }
        });
    }
    
    showAlert(signal) {
        if (!this.config.enableAlerts) return;
        
        const signalConfig = this.signalTypes[signal.type] || this.signalTypes.NEUTRAL;
        
        // Create alert element
        const alert = document.createElement('div');
        alert.className = 'alert alert-dismissible fade show';
        alert.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 1050;
            min-width: 300px;
            border-left: 4px solid ${signalConfig.color};
        `;
        
        alert.innerHTML = `
            <div class="d-flex align-items-center">
                <div class="me-3" style="font-size: 24px;">${signalConfig.icon}</div>
                <div class="flex-grow-1">
                    <h6 class="mb-1">${signal.type} Signal - ${signal.symbol}</h6>
                    <small>Strength: ${(signal.strength * 100).toFixed(0)}% | Price: $${signal.price.toFixed(4)}</small>
                </div>
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        document.getElementById('alertContainer').appendChild(alert);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (alert.parentNode) {
                alert.parentNode.removeChild(alert);
            }
        }, 5000);
        
        // Play sound if enabled
        if (this.config.alertSoundEnabled && signalConfig.sound) {
            this.playAlertSound(signalConfig.sound);
        }
        
        // Browser notification if enabled and permitted
        this.showBrowserNotification(signal);
    }
    
    // Utility methods
    calculateStochRSIStrength(stochRSIData) {
        if (!stochRSIData.k || !stochRSIData.d) return 0;
        
        const k = stochRSIData.k;
        const d = stochRSIData.d;
        const lower = stochRSIData.lower_band || 20;
        const upper = stochRSIData.upper_band || 80;
        
        if (k < lower && k > d) return 0.8; // Strong oversold signal
        if (k > upper && k < d) return 0.8; // Strong overbought signal
        if (k > d && k < 50) return 0.6; // Moderate bullish
        if (k < d && k > 50) return 0.4; // Moderate bearish
        
        return 0.2; // Weak signal
    }
    
    calculateEMAStrength(emaData) {
        if (!emaData.price || !emaData.ema) return 0;
        
        const deviation = Math.abs(emaData.price - emaData.ema) / emaData.ema;
        return Math.min(deviation * 10, 1); // Scale deviation to 0-1
    }
    
    calculateVolumeStrength(volumeData) {
        if (!volumeData.current || !volumeData.average) return 0;
        
        const ratio = volumeData.current / volumeData.average;
        return Math.min((ratio - 1) * 2, 1); // Above average volume increases strength
    }
    
    // Chart data methods
    setChartData(candleData, volumeData = null) {
        if (this.candleSeries) {
            this.candleSeries.setData(candleData);
        }
        
        if (this.volumeSeries && volumeData) {
            this.volumeSeries.setData(volumeData);
        }
    }
    
    updateChartData(newCandle, newVolume = null) {
        if (this.candleSeries) {
            this.candleSeries.update(newCandle);
        }
        
        if (this.volumeSeries && newVolume) {
            this.volumeSeries.update(newVolume);
        }
    }
    
    // Filter and export methods
    filterHistory(type) {
        const rows = document.querySelectorAll('#historyTableBody tr[data-signal-type]');
        
        rows.forEach(row => {
            const signalType = row.getAttribute('data-signal-type');
            if (type === 'ALL' || signalType === type) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
        
        // Update active filter button
        document.querySelectorAll('.history-controls .btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.getElementById(`filter${type === 'ALL' ? 'All' : type.charAt(0) + type.slice(1).toLowerCase()}`).classList.add('active');
    }
    
    exportSignalHistory() {
        const csvContent = this.generateCSV();
        const blob = new Blob([csvContent], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `signal_history_${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
        
        window.URL.revokeObjectURL(url);
    }
    
    generateCSV() {
        const headers = ['Timestamp', 'Symbol', 'Type', 'Strength', 'Price', 'Reason', 'Performance'];
        const rows = this.signalHistory.map(signal => [
            new Date(signal.timestamp).toISOString(),
            signal.symbol,
            signal.type,
            signal.strength,
            signal.price,
            signal.reason,
            signal.performance || ''
        ]);
        
        return [headers, ...rows].map(row => row.join(',')).join('\n');
    }
    
    // Performance tracking
    updatePerformanceData(signal) {
        // Update overall statistics
        this.updatePerformanceStats();
        
        // Update performance chart
        this.updatePerformanceChart();
    }
    
    updatePerformanceStats() {
        const total = this.signalHistory.length;
        const wins = this.signalHistory.filter(s => s.performance && s.performance > 0).length;
        const winRate = total > 0 ? (wins / total) * 100 : 0;
        const avgStrength = total > 0 ? 
            this.signalHistory.reduce((sum, s) => sum + s.strength, 0) / total * 100 : 0;
        
        document.getElementById('winRate').textContent = `${winRate.toFixed(1)}%`;
        document.getElementById('totalSignals').textContent = total.toString();
        document.getElementById('avgStrength').textContent = `${avgStrength.toFixed(1)}%`;
        
        // Determine best strategy
        const strategyPerformance = {};
        this.signalHistory.forEach(signal => {
            if (!strategyPerformance[signal.type]) {
                strategyPerformance[signal.type] = { wins: 0, total: 0 };
            }
            strategyPerformance[signal.type].total++;
            if (signal.performance && signal.performance > 0) {
                strategyPerformance[signal.type].wins++;
            }
        });
        
        let bestStrategy = '--';
        let bestRate = 0;
        Object.entries(strategyPerformance).forEach(([type, data]) => {
            const rate = data.total > 0 ? data.wins / data.total : 0;
            if (rate > bestRate) {
                bestRate = rate;
                bestStrategy = type;
            }
        });
        
        document.getElementById('bestStrategy').textContent = bestStrategy;
    }
    
    updatePerformanceChart() {
        // Implementation for updating the performance chart with historical data
        // This would include win rates over time, signal frequency, etc.
    }
    
    // Notification system
    initializeNotifications() {
        if ('Notification' in window) {
            Notification.requestPermission();
        }
    }
    
    showBrowserNotification(signal) {
        if (!('Notification' in window) || Notification.permission !== 'granted') {
            return;
        }
        
        const signalConfig = this.signalTypes[signal.type] || this.signalTypes.NEUTRAL;
        
        new Notification(`Trading Signal: ${signal.type}`, {
            body: `${signal.symbol} - Strength: ${(signal.strength * 100).toFixed(0)}%`,
            icon: '/static/icons/signal-icon.png',
            badge: signalConfig.icon
        });
    }
    
    playAlertSound(soundFile) {
        try {
            const audio = new Audio(`/static/sounds/${soundFile}`);
            audio.volume = 0.5;
            audio.play().catch(e => console.log('Audio play failed:', e));
        } catch (e) {
            console.log('Audio not available:', e);
        }
    }
    
    // Control methods
    toggleMarkers() {
        if (this.config.enableMarkers) {
            this.candleSeries?.setMarkers(this.signalMarkers);
        } else {
            this.candleSeries?.setMarkers([]);
        }
    }
    
    toggleStrengthIndicator() {
        const indicator = this.strengthIndicator;
        if (this.config.enableStrengthIndicator) {
            indicator.style.display = 'block';
        } else {
            indicator.style.display = 'none';
        }
    }
    
    clearAllSignals() {
        this.signalMarkers = [];
        this.signalHistory = [];
        this.candleSeries?.setMarkers([]);
        this.updateHistoryTable();
        this.updatePerformanceStats();
        console.log('🧹 All signals cleared');
    }
    
    // Method to show detailed signal information
    showSignalDetails(signalId) {
        const signal = this.signalHistory.find(s => s.id == signalId);
        if (!signal) return;
        
        // Create modal or detailed view for signal
        console.log('📊 Signal details:', signal);
        // Implementation for detailed signal view
    }
    
    // Cleanup method
    destroy() {
        if (this.chart) {
            this.chart.remove();
        }
        if (this.performanceChart) {
            this.performanceChart.destroy();
        }
        this.chartContainer.innerHTML = '';
    }
}

// Global instance for easy access
window.TradingSignalVisualization = TradingSignalVisualization;

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TradingSignalVisualization;
}