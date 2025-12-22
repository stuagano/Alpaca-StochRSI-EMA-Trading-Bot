// Crypto Trading Dashboard JavaScript
class CryptoDashboard {
    constructor() {
        this.autoRefresh = true;
        this.refreshInterval = null;
        this.lastUpdate = null;
        this.pnlChart = null;
        this.botStatus = null;
        this.positionMultiplier = 1;

        this.init();
    }

    init() {
        // Initialize dashboard on page load
        this.updateConnectionStatus('connecting');
        this.initializeChart();
        this.loadAllData();
        this.loadBotStatus();
        this.loadThresholds();
        this.loadActivity();
        this.updateChart();
        this.startAutoRefresh();

        // Set up event listeners
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Handle window focus to refresh data
        window.addEventListener('focus', () => {
            this.loadAllData();
            this.loadBotStatus();
        });
    }

    updateConnectionStatus(status) {
        const statusIndicator = document.getElementById('connection-status');
        const statusDot = statusIndicator.querySelector('.status-dot');
        const statusText = statusIndicator.querySelector('.status-text');

        statusDot.className = 'status-dot';

        switch (status) {
            case 'connected':
                statusDot.classList.add('connected');
                statusText.textContent = 'Connected';
                break;
            case 'connecting':
                statusDot.classList.add('connecting');
                statusText.textContent = 'Connecting...';
                break;
            case 'error':
                statusDot.classList.add('error');
                statusText.textContent = 'Connection Error';
                break;
        }
    }

    async loadAllData() {
        try {
            this.updateConnectionStatus('connecting');

            // Load all data concurrently
            const [statusData, accountData, positionsData, signalsData, tradesData] = await Promise.all([
                this.fetchData('status'),
                this.fetchData('account'),
                this.fetchData('positions'),
                this.fetchData('signals'),
                this.fetchData('trades')
            ]);

            // Update all sections
            this.updateAccountInfo(accountData);
            this.updatePositions(positionsData);
            this.updateSignals(signalsData);
            this.updatePerformance(positionsData);
            this.updateTrades(tradesData);

            this.updateConnectionStatus('connected');
            this.updateLastRefreshTime();

        } catch (error) {
            console.error('Error loading dashboard data:', error);
            this.updateConnectionStatus('error');
        }
    }

    async fetchData(endpointKey) {
        const url = typeof buildApiUrl === 'function'
            ? buildApiUrl(endpointKey)
            : endpointKey;
        console.log('Fetching:', endpointKey, url);


        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status} (${url})`);
        }
        return await response.json();
    }

    updateAccountInfo(accountData) {
        document.getElementById('portfolio-value').textContent = this.formatCurrency(accountData.portfolio_value);
        document.getElementById('buying-power').textContent = this.formatCurrency(accountData.buying_power);
        document.getElementById('cash').textContent = this.formatCurrency(accountData.cash);
        document.getElementById('account-status').textContent = accountData.status;
    }

    updatePositions(positionsData) {
        const positionsContainer = document.getElementById('positions-list');

        if (!positionsData || positionsData.length === 0) {
            positionsContainer.innerHTML = '<div class="no-data">No open crypto positions</div>';
            document.getElementById('positions-count').textContent = '0';
            return;
        }

        document.getElementById('positions-count').textContent = positionsData.length;

        let html = '<div class="positions-grid">';
        positionsData.forEach(position => {
            const pnlClass = position.unrealized_pl >= 0 ? 'positive' : 'negative';
            const pnlSymbol = position.unrealized_pl >= 0 ? '+' : '';

            html += `
                <div class="position-item">
                    <div class="position-header">
                        <span class="symbol">${position.symbol}</span>
                        <span class="pnl ${pnlClass}">
                            ${pnlSymbol}${this.formatCurrency(position.unrealized_pl)}
                        </span>
                    </div>
                    <div class="position-details">
                        <div class="detail">
                            <span>Qty:</span>
                            <span>${position.qty}</span>
                        </div>
                        <div class="detail">
                            <span>Avg Price:</span>
                            <span>${this.formatCurrency(position.avg_price)}</span>
                        </div>
                        <div class="detail">
                            <span>Current:</span>
                            <span>${this.formatCurrency(position.current_price)}</span>
                        </div>
                        <div class="detail">
                            <span>P&L %:</span>
                            <span class="${pnlClass}">${this.formatPercent(position.unrealized_plpc)}</span>
                        </div>
                    </div>
                </div>
            `;
        });
        html += '</div>';

        positionsContainer.innerHTML = html;
    }

    updateSignals(signalsData) {
        const signalsContainer = document.getElementById('signals-list');

        if (!signalsData || signalsData.length === 0) {
            signalsContainer.innerHTML = '<div class="no-data">No signals available</div>';
            return;
        }

        let html = '<div class="signals-grid">';
        signalsData.forEach(signal => {
            const actionClass = signal.action.toLowerCase();
            const strengthClass = signal.strength.toLowerCase();

            html += `
                <div class="signal-item">
                    <div class="signal-header">
                        <span class="symbol">${signal.symbol}</span>
                        <span class="action ${actionClass}">${signal.action}</span>
                    </div>
                    <div class="signal-details">
                        <div class="detail">
                            <span>RSI:</span>
                            <span>${signal.rsi || 'N/A'}</span>
                        </div>
                        <div class="detail">
                            <span>Price:</span>
                            <span>${this.formatCurrency(signal.price)}</span>
                        </div>
                        <div class="detail">
                            <span>Strength:</span>
                            <span class="${strengthClass}">${signal.strength || 'Normal'}</span>
                        </div>
                    </div>
                </div>
            `;
        });
        html += '</div>';

        signalsContainer.innerHTML = html;
    }

    updatePerformance(positionsData) {
        let totalPnL = 0;
        let dailyPnL = 0;

        if (positionsData && positionsData.length > 0) {
            totalPnL = positionsData.reduce((sum, pos) => sum + pos.unrealized_pl, 0);
            // For simplicity, using unrealized P&L as daily P&L
            dailyPnL = totalPnL;
        }

        const totalPnLElement = document.getElementById('total-pnl');
        const dailyPnLElement = document.getElementById('daily-pnl');

        totalPnLElement.textContent = this.formatCurrency(totalPnL);
        totalPnLElement.className = 'value pnl ' + (totalPnL >= 0 ? 'positive' : 'negative');

        dailyPnLElement.textContent = this.formatCurrency(dailyPnL);
        dailyPnLElement.className = 'value pnl ' + (dailyPnL >= 0 ? 'positive' : 'negative');
    }

    updateTrades(tradesData) {
        const tradesArray = Array.isArray(tradesData)
            ? tradesData
            : (tradesData && Array.isArray(tradesData.trades) ? tradesData.trades : []);

        const tradesBody = document.getElementById('trades-body');

        if (!tradesArray || tradesArray.length === 0) {
            tradesBody.innerHTML = '<tr><td colspan="6" class="no-data">No recent trades</td></tr>';
            return;
        }

        let html = '';
        tradesArray.slice(0, 10).forEach(trade => { // Show first 10 trades (API returns newest first)
            const sideClass = trade.side === 'buy' ? 'buy' : 'sell';
            const value = trade.qty * trade.price;

            html += `
                <tr>
                    <td>${this.formatTime(trade.time || trade.timestamp)}</td>
                    <td class="symbol">${trade.symbol}</td>
                    <td class="side ${sideClass}">${trade.side.toUpperCase()}</td>
                    <td>${trade.qty}</td>
                    <td>${this.formatCurrency(trade.price)}</td>
                    <td>${this.formatCurrency(value)}</td>
                </tr>
            `;
        });

        tradesBody.innerHTML = html;
    }

    formatCurrency(amount) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 2,
            maximumFractionDigits: 4
        }).format(amount);
    }

    initializeChart() {
        const canvas = document.getElementById('pnlChart');
        if (!canvas) {
            console.warn('Chart canvas not found');
            return;
        }

        const ctx = canvas.getContext('2d');
        this.pnlChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Hourly P&L',
                        data: [],
                        borderColor: 'rgb(75, 192, 192)',
                        backgroundColor: 'rgba(75, 192, 192, 0.2)',
                        tension: 0.4,
                        yAxisID: 'y'
                    },
                    {
                        label: 'Cumulative P&L',
                        data: [],
                        borderColor: 'rgb(255, 99, 132)',
                        backgroundColor: 'rgba(255, 99, 132, 0.2)',
                        tension: 0.4,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                        labels: {
                            color: '#888',
                            usePointStyle: true,
                            padding: 15
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                let label = context.dataset.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                if (context.parsed.y !== null) {
                                    label += '$' + context.parsed.y.toFixed(2);
                                }
                                return label;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        grid: { color: 'rgba(75, 192, 192, 0.1)' },
                        ticks: {
                            color: 'rgb(75, 192, 192)',
                            callback: function (value) {
                                return '$' + value.toFixed(2);
                            }
                        },
                        title: {
                            display: true,
                            text: 'Hourly P&L',
                            color: 'rgb(75, 192, 192)'
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        grid: { drawOnChartArea: false },
                        ticks: {
                            color: 'rgb(255, 99, 132)',
                            callback: function (value) {
                                return '$' + value.toFixed(2);
                            }
                        },
                        title: {
                            display: true,
                            text: 'Cumulative P&L',
                            color: 'rgb(255, 99, 132)'
                        }
                    },
                    x: {
                        grid: { color: 'rgba(255, 255, 255, 0.1)' },
                        ticks: { color: '#888' }
                    }
                }
            }
        });
    }

    async updateChart() {
        if (!this.pnlChart) {
            return;
        }

        try {
            const chartData = await this.fetchData('pnlChart');
            if (!chartData) return;

            this.pnlChart.data.labels = chartData.labels || [];

            // Update both datasets
            if (chartData.datasets && chartData.datasets.length > 0) {
                this.pnlChart.data.datasets[0].data = chartData.datasets[0]?.data || [];

                // Update second dataset if available
                if (chartData.datasets.length > 1 && this.pnlChart.data.datasets.length > 1) {
                    this.pnlChart.data.datasets[1].data = chartData.datasets[1]?.data || [];
                }
            }

            this.pnlChart.update('none'); // Use 'none' mode for faster updates
        } catch (error) {
            console.error('Error updating P&L chart:', error);
        }
    }

    formatPercent(value) {
        return new Intl.NumberFormat('en-US', {
            style: 'percent',
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(value);
    }

    formatTime(timestamp) {
        const date = new Date(timestamp);
        return date.toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    }

    updateLastRefreshTime() {
        const now = new Date();
        document.getElementById('last-update').textContent = now.toLocaleTimeString();
        this.lastUpdate = now;
    }

    startAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }

        if (this.autoRefresh) {
            this.refreshInterval = setInterval(() => {
                this.loadAllData();
                this.loadBotStatus();
                this.loadActivity();
                this.updateChart();
            }, 10000); // Refresh every 10 seconds
        }
    }

    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }

    // ==================== BOT CONTROL METHODS ====================

    async startTrading() {
        try {
            const response = await fetch(buildApiUrl('tradingStart'), { method: 'POST' });
            const data = await response.json();

            if (response.ok) {
                this.showNotification('Trading started successfully', 'success');
                await this.loadBotStatus();
                await this.loadAllData();
            } else {
                this.showNotification(data.error || 'Failed to start trading', 'error');
            }
        } catch (error) {
            console.error('Error starting trading:', error);
            this.showNotification('Error starting trading', 'error');
        }
    }

    async stopTrading() {
        if (!confirm('Are you sure you want to stop trading?')) return;

        try {
            const response = await fetch(buildApiUrl('tradingStop'), { method: 'POST' });
            const data = await response.json();

            if (response.ok) {
                this.showNotification('Trading stopped', 'success');
                await this.loadBotStatus();
                await this.loadAllData();
            } else {
                this.showNotification(data.error || 'Failed to stop trading', 'error');
            }
        } catch (error) {
            console.error('Error stopping trading:', error);
            this.showNotification('Error stopping trading', 'error');
        }
    }

    async liquidateAll() {
        if (!confirm('⚠️ LIQUIDATE ALL POSITIONS?\n\nThis will close ALL open positions immediately at market price.')) return;

        try {
            const response = await fetch(buildApiUrl('liquidateAll'), { method: 'POST' });
            const data = await response.json();

            if (response.ok) {
                this.showNotification(`Liquidated ${data.orders?.length || 0} positions`, 'success');
                await this.loadBotStatus();
                await this.loadAllData();
            } else {
                this.showNotification(data.error || 'Failed to liquidate positions', 'error');
            }
        } catch (error) {
            console.error('Error liquidating positions:', error);
            this.showNotification('Error liquidating positions', 'error');
        }
    }

    async liquidatePosition(symbol) {
        if (!confirm(`Close position for ${symbol}?`)) return;

        try {
            const response = await fetch(buildApiUrl('liquidate').replace('{symbol}', symbol), { method: 'POST' });
            const data = await response.json();

            if (response.ok) {
                this.showNotification(`Position ${symbol} closed`, 'success');
                await this.loadBotStatus();
                await this.loadAllData();
            } else {
                this.showNotification(data.error || `Failed to close ${symbol}`, 'error');
            }
        } catch (error) {
            console.error(`Error closing position ${symbol}:`, error);
            this.showNotification(`Error closing ${symbol}`, 'error');
        }
    }

    async resetDailyLimits() {
        if (!confirm('Reset daily trading limits? This will allow trading to resume if daily loss limit was hit.')) return;

        try {
            const response = await fetch(buildApiUrl('resetDaily'), { method: 'POST' });
            const data = await response.json();

            if (response.ok) {
                this.showNotification('Daily limits reset - trading resumed', 'success');
                await this.loadBotStatus();
            } else {
                this.showNotification(data.error || 'Failed to reset daily limits', 'error');
            }
        } catch (error) {
            console.error('Error resetting daily limits:', error);
            this.showNotification('Error resetting daily limits', 'error');
        }
    }

    // ==================== BOT STATUS METHODS ====================

    async loadBotStatus() {
        try {
            const data = await this.fetchData('botStatus');
            this.botStatus = data;
            this.updateBotStatusUI(data);
        } catch (error) {
            console.error('Error loading bot status:', error);
            this.updateBotStatusUI({ status: 'error', bot: null });
        }
    }

    updateBotStatusUI(data) {
        const badge = document.getElementById('bot-status-badge');
        const status = data.status || 'not_started';

        badge.textContent = status.charAt(0).toUpperCase() + status.slice(1).replace('_', ' ');
        badge.className = 'bot-status-badge ' + status;

        const bot = data.bot;
        if (bot) {
            document.getElementById('bot-positions-count').textContent = bot.active_positions_count || 0;
            document.getElementById('bot-total-trades').textContent = bot.total_trades || 0;
            document.getElementById('bot-win-rate').textContent = (bot.win_rate || 0) + '%';

            const unrealizedPnl = bot.total_unrealized_pnl || 0;
            const pnlElement = document.getElementById('bot-unrealized-pnl');
            pnlElement.textContent = this.formatCurrency(unrealizedPnl);
            pnlElement.className = 'stat-value ' + (unrealizedPnl >= 0 ? 'positive' : 'negative');

            // Update bot positions list
            this.updateBotPositionsList(bot.positions || []);
        } else {
            document.getElementById('bot-positions-count').textContent = '0';
            document.getElementById('bot-total-trades').textContent = '0';
            document.getElementById('bot-win-rate').textContent = '0%';
            document.getElementById('bot-unrealized-pnl').textContent = '$0.00';
            document.getElementById('bot-positions-list').innerHTML = '<div class="no-data">Bot not running - Start trading to manage positions</div>';
            document.getElementById('bot-positions-list-count').textContent = '0';
        }
    }

    updateBotPositionsList(positions) {
        const container = document.getElementById('bot-positions-list');
        document.getElementById('bot-positions-list-count').textContent = positions.length;

        if (!positions || positions.length === 0) {
            container.innerHTML = '<div class="no-data">No positions being managed by bot</div>';
            return;
        }

        let html = '';
        positions.forEach(pos => {
            const pnlClass = pos.pnl_pct >= 0 ? 'positive' : 'negative';
            const holdProgress = Math.min(100, (pos.hold_time_seconds / 3600) * 100); // 1 hour = 100%

            html += `
                <div class="position-card">
                    <div class="position-card-header">
                        <span class="position-symbol">${pos.symbol}</span>
                        <span class="position-pnl ${pnlClass}">
                            ${pos.pnl_pct >= 0 ? '+' : ''}${pos.pnl_pct}% (${this.formatCurrency(pos.unrealized_pnl)})
                        </span>
                    </div>
                    <div class="position-details-grid">
                        <div class="position-detail">
                            <span class="position-detail-label">Entry</span>
                            <span class="position-detail-value">${this.formatCurrency(pos.entry_price)}</span>
                        </div>
                        <div class="position-detail">
                            <span class="position-detail-label">Current</span>
                            <span class="position-detail-value">${this.formatCurrency(pos.current_price)}</span>
                        </div>
                        <div class="position-detail">
                            <span class="position-detail-label">Qty</span>
                            <span class="position-detail-value">${pos.quantity}</span>
                        </div>
                        <div class="position-detail">
                            <span class="position-detail-label">Stop</span>
                            <span class="position-detail-value negative">${this.formatCurrency(pos.stop_price)}</span>
                        </div>
                        <div class="position-detail">
                            <span class="position-detail-label">Target</span>
                            <span class="position-detail-value positive">${this.formatCurrency(pos.target_price)}</span>
                        </div>
                        <div class="position-detail">
                            <span class="position-detail-label">Hold Time</span>
                            <span class="position-detail-value">${this.formatHoldTime(pos.hold_time_seconds)}</span>
                        </div>
                    </div>
                    <div class="hold-time-bar">
                        <div class="hold-time-progress" style="width: ${holdProgress}%"></div>
                    </div>
                    <div class="position-actions">
                        ${pos.synced_from_alpaca ? '<span style="color: #888; font-size: 11px;">Synced from Alpaca</span>' : ''}
                        <button class="btn danger small" onclick="dashboard.liquidatePosition('${pos.symbol}')">Close Position</button>
                    </div>
                </div>
            `;
        });

        container.innerHTML = html;
    }

    formatHoldTime(seconds) {
        if (seconds < 60) return `${seconds}s`;
        if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
        return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
    }

    // ==================== THRESHOLD METHODS ====================

    async loadThresholds() {
        try {
            const data = await this.fetchData('botThresholds');
            if (data && !data.error) {
                document.getElementById('threshold-stop-loss').value = (data.stop_loss_pct * 100).toFixed(1);
                document.getElementById('threshold-take-profit').value = (data.take_profit_pct * 100).toFixed(1);
                document.getElementById('threshold-trailing-stop').value = (data.trailing_stop_pct * 100).toFixed(1);
                document.getElementById('threshold-max-hold').value = Math.floor(data.max_hold_time_seconds / 60);
            }
        } catch (error) {
            console.log('Could not load thresholds (bot may not be running):', error);
        }
    }

    async updateThresholds() {
        const thresholds = {
            stop_loss_pct: parseFloat(document.getElementById('threshold-stop-loss').value) / 100,
            take_profit_pct: parseFloat(document.getElementById('threshold-take-profit').value) / 100,
            trailing_stop_pct: parseFloat(document.getElementById('threshold-trailing-stop').value) / 100,
            max_hold_time_seconds: parseInt(document.getElementById('threshold-max-hold').value) * 60
        };

        try {
            const response = await fetch(buildApiUrl('botThresholds'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(thresholds)
            });

            const data = await response.json();

            if (response.ok) {
                this.showNotification('Thresholds updated successfully', 'success');
                await this.loadBotStatus(); // Refresh to show updated stops/targets
            } else {
                this.showNotification(data.error || 'Failed to update thresholds', 'error');
            }
        } catch (error) {
            console.error('Error updating thresholds:', error);
            this.showNotification('Error updating thresholds', 'error');
        }
    }

    // ==================== NOTIFICATION HELPER ====================

    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 25px;
            border-radius: 8px;
            color: #fff;
            font-weight: 600;
            z-index: 10000;
            animation: slideIn 0.3s ease;
            background: ${type === 'success' ? '#00ff88' : type === 'error' ? '#ff4444' : '#ffaa00'};
            color: ${type === 'success' ? '#000' : '#fff'};
        `;
        notification.textContent = message;
        document.body.appendChild(notification);

        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }

    // ==================== ACTIVITY FEED METHODS ====================

    async loadActivity() {
        try {
            const response = await fetch('/api/v1/activity/summary');
            if (!response.ok) {
                console.log('Activity endpoint not available');
                return;
            }
            const data = await response.json();

            this.updateActivityFeed(data.activity || []);
            this.updateSignalAnalysis(data.signals || []);
            this.updateScannerStatus(data.scanner || {});
        } catch (error) {
            console.log('Activity feed not available:', error.message);
        }
    }

    updateActivityFeed(activities) {
        const container = document.getElementById('activity-feed');
        if (!container) return;

        if (!activities || activities.length === 0) {
            container.innerHTML = '<div class="no-data">No activity yet</div>';
            return;
        }

        let html = '';
        activities.slice(0, 50).forEach(entry => {
            const time = this.formatActivityTime(entry.timestamp);
            const typeColors = {
                'scan': '#4ecdc4',
                'signal': '#00ff88',
                'decision': '#ffaa00',
                'trade': '#ff6b6b',
                'info': '#666',
                'warning': '#ffaa00'
            };

            html += `
                <div class="activity-item ${entry.type}">
                    <span class="activity-time">${time}</span>
                    <span class="activity-type" style="color: ${typeColors[entry.type] || '#666'}">${entry.type}</span>
                    <span>${entry.message}</span>
                </div>
            `;
        });

        container.innerHTML = html;

        const statusEl = document.getElementById('activity-status');
        if (statusEl) {
            statusEl.textContent = `${activities.length} entries`;
        }
    }

    updateSignalAnalysis(signals) {
        const container = document.getElementById('signal-analysis');
        if (!container) return;

        if (!signals || signals.length === 0) {
            container.innerHTML = '<div style="text-align: center; color: #666; padding: 20px;">No signals cached</div>';
            return;
        }

        let html = '<div style="display: flex; flex-direction: column; gap: 8px;">';
        signals.slice(0, 10).forEach(signal => {
            const actionColor = signal.action === 'buy' ? '#00ff88' : signal.action === 'sell' ? '#ff6b6b' : '#888';
            const acceptedBadge = signal.accepted
                ? '<span style="background: #00ff88; color: #000; padding: 2px 6px; border-radius: 4px; font-size: 10px;">ACCEPTED</span>'
                : '<span style="background: #ff6b6b; color: #fff; padding: 2px 6px; border-radius: 4px; font-size: 10px;">REJECTED</span>';

            html += `
                <div style="padding: 8px; background: rgba(255,255,255,0.03); border-radius: 6px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                        <span style="color: #4ecdc4; font-weight: 600;">${signal.symbol || 'Unknown'}</span>
                        ${acceptedBadge}
                    </div>
                    <div style="display: flex; gap: 10px; font-size: 12px;">
                        <span style="color: ${actionColor}; text-transform: uppercase; font-weight: 600;">${signal.action || 'HOLD'}</span>
                        <span style="color: #888;">Conf: ${((signal.confidence || 0) * 100).toFixed(0)}%</span>
                        <span style="color: #888;">$${(signal.price || 0).toFixed(4)}</span>
                    </div>
                    ${signal.reason ? `<div style="color: #666; font-size: 11px; margin-top: 4px;">${signal.reason}</div>` : ''}
                </div>
            `;
        });
        html += '</div>';

        container.innerHTML = html;
    }

    updateScannerStatus(scanner) {
        const setElement = (id, value) => {
            const el = document.getElementById(id);
            if (el) el.textContent = value;
        };

        setElement('scanner-symbols', scanner.symbols_tracked || 0);
        setElement('scanner-last-scan', scanner.last_scan ? this.formatActivityTime(scanner.last_scan) : 'Never');
        setElement('scanner-signals-count', scanner.signals_generated || 0);
        setElement('scanner-rejected-count', scanner.signals_rejected || 0);
        setElement('scanner-avg-confidence', scanner.avg_confidence ? `${(scanner.avg_confidence * 100).toFixed(1)}%` : '-');
    }

    formatActivityTime(timestamp) {
        if (!timestamp) return '';
        const date = new Date(timestamp);
        const now = new Date();
        const diff = (now - date) / 1000;

        if (diff < 60) return `${Math.floor(diff)}s ago`;
        if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
        if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
        return date.toLocaleDateString();
    }

    // ==================== MULTIPLIER METHODS ====================

    async doubleDown() {
        this.positionMultiplier *= 2;
        if (this.positionMultiplier > 10) this.positionMultiplier = 10;
        this.updateMultiplierUI();

        try {
            const url = typeof buildApiUrl === 'function' ? buildApiUrl('setMultiplier') : '/api/v1/trading/set-multiplier';
            const response = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ multiplier: this.positionMultiplier })
            });

            if (response.ok) {
                this.showNotification(`Multiplier set to ${this.positionMultiplier}x! 🚀`, 'success');
            }
        } catch (error) {
            console.error('Error setting multiplier:', error);
        }
    }

    async resetMultiplier() {
        this.positionMultiplier = 1;
        this.updateMultiplierUI();

        try {
            const url = typeof buildApiUrl === 'function' ? buildApiUrl('setMultiplier') : '/api/v1/trading/set-multiplier';
            await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ multiplier: 1 })
            });
            this.showNotification('Multiplier reset to 1x', 'info');
        } catch (error) {
            console.error('Error resetting multiplier:', error);
        }
    }

    updateMultiplierUI() {
        const valElem = document.getElementById('bot-multiplier-value');
        const nextElem = document.getElementById('next-trade-multiplier');
        if (valElem) valElem.textContent = this.positionMultiplier + 'x';
        if (nextElem) nextElem.textContent = this.positionMultiplier + 'x';
    }
}

// Global functions for button handlers
function refreshDashboard() {
    dashboard.loadAllData();
}

function toggleAutoRefresh() {
    dashboard.autoRefresh = !dashboard.autoRefresh;
    const autoRefreshText = document.getElementById('auto-refresh-text');

    if (dashboard.autoRefresh) {
        autoRefreshText.textContent = 'Auto Refresh: ON';
        dashboard.startAutoRefresh();
    } else {
        autoRefreshText.textContent = 'Auto Refresh: OFF';
        dashboard.stopAutoRefresh();
    }
}

// Initialize dashboard when page loads
let dashboard;
document.addEventListener('DOMContentLoaded', function () {
    dashboard = new CryptoDashboard();
});
