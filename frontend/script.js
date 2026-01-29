// Crypto Trading Dashboard JavaScript
class CryptoDashboard {
    constructor() {
        this.autoRefresh = true;
        this.refreshInterval = null;
        this.lastUpdate = null;
        this.pnlChart = null;
        this.botStatus = null;
        this.positionMultiplier = 1;
        
        // WebSocket connection
        this.socket = null;
        this.socketConnected = false;
        this.useWebSocket = false; // Disabled - using HTTP polling (no Socket.IO server)

        // Activity log state
        this.lastActivityTimestamp = null;
        this.activityEntries = [];

        this.init();
    }

    init() {
        // Initialize WebSocket connection first
        this.initializeWebSocket();
        
        // Initialize dashboard on page load
        this.updateConnectionStatus('connecting');
        this.initializeChart();
        
        // Load initial data if WebSocket is not available
        if (!this.useWebSocket) {
            this.loadAllData();
            this.loadBotStatus();
            this.loadThresholds();
            this.loadTradeHistory();
            this.loadSignalAnalysis();
            this.loadMarketSnapshots();
            this.loadActivityLog();
            this.loadLearningInsights();  // Phase 4: Learning Insights
            this.updateChart();
            this.startAutoRefresh();
            this.startActivityPolling();
        }

        // Set up event listeners
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Handle window focus to refresh data
        window.addEventListener('focus', () => {
            if (!this.useWebSocket || !this.socketConnected) {
                this.loadAllData();
                this.loadBotStatus();
            }
        });
    }

    // ==================== WEBSOCKET METHODS ====================
    
    initializeWebSocket() {
        if (!this.useWebSocket) {
            console.log('WebSocket disabled, using HTTP polling');
            return;
        }

        try {
            // Initialize Socket.IO connection
            this.socket = io({
                transports: ['websocket', 'polling'], // Fall back to polling if WebSocket fails
                upgrade: true,
                rememberUpgrade: true,
                timeout: 20000,
                forceNew: false
            });

            this.setupWebSocketEventHandlers();
            
        } catch (error) {
            console.error('Failed to initialize WebSocket:', error);
            this.updateConnectionStatus('error');
            this.fallbackToPolling();
        }
    }

    setupWebSocketEventHandlers() {
        // Connection events
        this.socket.on('connect', () => {
            console.log('WebSocket connected');
            this.socketConnected = true;
            this.updateConnectionStatus('connected');
            
            // Subscribe to real-time updates
            this.subscribeToUpdates();
        });

        this.socket.on('disconnect', (reason) => {
            console.log('WebSocket disconnected:', reason);
            this.socketConnected = false;
            this.updateConnectionStatus('error');
            
            // Attempt to reconnect if this was an unexpected disconnect
            if (reason === 'io server disconnect') {
                // Server disconnected, reconnect manually
                this.socket.connect();
            }
        });

        this.socket.on('connect_error', (error) => {
            console.error('WebSocket connection error:', error);
            this.updateConnectionStatus('error');
            
            // Fallback to HTTP polling after multiple failed attempts
            this.fallbackToPolling();
        });

        this.socket.on('reconnect', (attemptNumber) => {
            console.log(`WebSocket reconnected after ${attemptNumber} attempts`);
            this.socketConnected = true;
            this.updateConnectionStatus('connected');
            this.subscribeToUpdates();
        });

        // Real-time data events
        this.socket.on('connection_status', (data) => {
            console.log('Connection status:', data);
        });

        this.socket.on('bot_status_update', (data) => {
            console.log('Bot status update:', data);
            if (data.data) {
                this.updateBotStatus(data.data);
            }
        });

        this.socket.on('positions_update', (data) => {
            console.log('Positions update:', data);
            if (data.data) {
                this.updatePositions(data.data);
                this.updatePerformance(data.data);
            }
        });

        this.socket.on('pnl_update', (data) => {
            console.log('P&L update:', data);
            if (data.data) {
                this.updatePnL(data.data);
            }
        });

        this.socket.on('activity_update', (data) => {
            console.log('Activity update:', data);
            if (data.data) {
                this.updateActivityFeed(data.data);
            }
        });

        this.socket.on('trade_update', (data) => {
            console.log('Trade update:', data);
            if (data.data) {
                this.handleTradeUpdate(data.data);
            }
        });

        this.socket.on('error_update', (data) => {
            console.error('Error from server:', data);
            if (data.data) {
                this.showNotification(data.data.message || 'Server error occurred', 'error');
            }
        });

        this.socket.on('subscribed', (data) => {
            console.log('Subscribed to room:', data);
        });

        this.socket.on('unsubscribed', (data) => {
            console.log('Unsubscribed from room:', data);
        });
    }

    subscribeToUpdates() {
        if (!this.socket || !this.socketConnected) return;

        // Subscribe to all real-time update rooms
        this.socket.emit('subscribe', { room: 'positions' });
        this.socket.emit('subscribe', { room: 'pnl' });
        this.socket.emit('subscribe', { room: 'signals' });
        this.socket.emit('subscribe', { room: 'activity' });
        
        console.log('Subscribed to real-time updates');
    }

    unsubscribeFromUpdates() {
        if (!this.socket) return;

        this.socket.emit('unsubscribe', { room: 'positions' });
        this.socket.emit('unsubscribe', { room: 'pnl' });
        this.socket.emit('unsubscribe', { room: 'signals' });
        this.socket.emit('unsubscribe', { room: 'activity' });
    }

    requestManualUpdate(type = 'all') {
        if (this.socket && this.socketConnected) {
            this.socket.emit('request_update', { type: type });
        }
    }

    fallbackToPolling() {
        console.log('Falling back to HTTP polling');
        this.useWebSocket = false;

        // Start HTTP polling if not already started
        if (!this.refreshInterval) {
            this.loadAllData();
            this.loadBotStatus();
            this.loadThresholds();
            this.loadTradeHistory();
            this.loadSignalAnalysis();
            this.loadLearningInsights();
            this.updateChart();
            this.startAutoRefresh();
        }
    }

    disconnectWebSocket() {
        if (this.socket) {
            this.unsubscribeFromUpdates();
            this.socket.disconnect();
            this.socket = null;
            this.socketConnected = false;
        }
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
            const [statusData, accountData, positionsData] = await Promise.all([
                this.fetchData('status'),
                this.fetchData('account'),
                this.fetchData('positions')
            ]);

            // Update all sections
            this.updateAccountInfo(accountData);
            this.updatePositions(positionsData);
            this.updatePerformance(positionsData);

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

    updatePerformance(positionsData) {
        let totalPnL = 0;
        let dailyPnL = 0;

        const totalPnLElement = document.getElementById('total-pnl');
        const dailyPnLElement = document.getElementById('daily-pnl');

        if (positionsData && positionsData.length > 0) {
            totalPnL = positionsData.reduce((sum, pos) => sum + (pos.unrealized_pl || 0), 0);
        }

        totalPnLElement.textContent = this.formatCurrency(totalPnL);
        totalPnLElement.className = 'value pnl ' + (totalPnL >= 0 ? 'positive' : 'negative');

        // Daily P&L would need to come from a separate endpoint or bot status
        // For now, show unrealized P&L as the daily metric
        dailyPnLElement.textContent = this.formatCurrency(totalPnL);
        dailyPnLElement.className = 'value pnl ' + (totalPnL >= 0 ? 'positive' : 'negative');
    }

    formatCurrency(amount) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 2,
            maximumFractionDigits: 4
        }).format(amount);
    }

    formatPrice(price) {
        // Format price without currency symbol for cleaner display in tables
        if (price === null || price === undefined) return '-';
        // Use more decimal places for crypto prices
        const decimals = price < 1 ? 6 : (price < 100 ? 4 : 2);
        return new Intl.NumberFormat('en-US', {
            minimumFractionDigits: 2,
            maximumFractionDigits: decimals
        }).format(price);
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
                        tension: 0,  // No smoothing - show raw data
                        borderWidth: 2,
                        pointRadius: 3,
                        pointBackgroundColor: 'rgb(75, 192, 192)',
                        fill: true,
                        yAxisID: 'y'
                    },
                    {
                        label: 'Cumulative P&L',
                        data: [],
                        borderColor: 'rgb(255, 99, 132)',
                        backgroundColor: 'rgba(255, 99, 132, 0.1)',
                        tension: 0,  // No smoothing - show raw data
                        borderWidth: 2,
                        pointRadius: 3,
                        pointBackgroundColor: 'rgb(255, 99, 132)',
                        fill: false,
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
                        ticks: {
                            color: '#888',
                            maxRotation: 45,
                            autoSkip: true,
                            maxTicksLimit: 20  // Don't show all 72 labels
                        }
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

    updateBotStatus(data) {
        this.updateBotStatusUI(data);
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
            // FAKE DATA BLOCKED: Show NO DATA instead of fake metrics
            document.getElementById('bot-positions-count').textContent = 'NO DATA';
            document.getElementById('bot-total-trades').textContent = 'NO DATA';
            document.getElementById('bot-win-rate').textContent = 'NO DATA';
            document.getElementById('bot-unrealized-pnl').textContent = 'NO DATA';
            document.getElementById('bot-positions-list').innerHTML = '<div class="no-data">Bot not running - NO DATA AVAILABLE</div>';
            document.getElementById('bot-positions-list-count').textContent = 'NO DATA';
        }
    }

    updateBotPositionsList(positions) {
        const container = document.getElementById('bot-positions-list');
        document.getElementById('bot-positions-list-count').textContent = positions.length;

        if (!positions || positions.length === 0) {
            container.innerHTML = '<div class="no-data">No positions being managed by bot</div>';
            return;
        }

        // Use new Position Lifecycle Cards (Phase 1)
        let html = '';
        positions.forEach(pos => {
            html += this.renderPositionLifecycle(pos);
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

    // ==================== TRADE HISTORY METHODS ====================

    async loadTradeHistory() {
        try {
            const response = await fetch(`${API_CONFIG.baseURL}/api/v1/pnl/trades`);
            if (!response.ok) {
                console.log('Trade history endpoint not available');
                return;
            }
            const data = await response.json();

            this.updateTradeHistory(data.trades || []);
        } catch (error) {
            console.log('Trade history not available:', error.message);
        }
    }

    updateTradeHistory(trades) {
        const container = document.getElementById('trade-history');
        if (!container) return;

        if (!trades || trades.length === 0) {
            container.innerHTML = '<div class="no-data">No trades yet</div>';
            return;
        }

        // Check if we have enriched trade data (with entry/exit info)
        const hasStoryData = trades.some(t => t.entry_time || t.exit_time || t.pnl !== undefined);

        let html = '';
        if (hasStoryData) {
            // Phase 5: Use Trade Story Cards for enriched data
            trades.slice(0, 20).forEach(trade => {
                html += this.renderTradeStory(trade);
            });
        } else {
            // Fallback to simple trade list for basic data
            trades.slice(0, 30).forEach(trade => {
                const time = this.formatTradeTime(trade.time || trade.timestamp);
                const side = trade.side || 'unknown';
                const symbol = trade.symbol || 'Unknown';
                const qty = parseFloat(trade.qty || 0).toFixed(6);
                const price = parseFloat(trade.price || 0).toFixed(2);

                html += `
                    <div class="trade-item ${side}">
                        <div class="trade-info">
                            <span class="trade-symbol">${symbol}</span>
                            <span class="trade-details">${qty} @ $${price}</span>
                        </div>
                        <div style="text-align: right;">
                            <span class="trade-side ${side}">${side.toUpperCase()}</span>
                            <div class="trade-time">${time}</div>
                        </div>
                    </div>
                `;
            });
        }

        container.innerHTML = html;

        const statusEl = document.getElementById('trade-history-status');
        if (statusEl) {
            statusEl.textContent = `${trades.length} trades`;
        }
    }

    formatTradeTime(timestamp) {
        if (!timestamp) return '';
        const date = new Date(timestamp);
        return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
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

    // ==================== SIGNAL ANALYSIS METHODS ====================

    async loadSignalAnalysis() {
        try {
            const data = await this.fetchData('signalAnalysis');
            this.renderBotWatchlist(data);
            this.renderSignalAnalysisTable(data);
        } catch (error) {
            console.log('Signal analysis not available:', error.message);
            const container = document.getElementById('bot-watchlist');
            if (container) {
                container.innerHTML = '<div class="no-data">Watchlist unavailable</div>';
            }
        }
    }

    renderSignalAnalysisTable(data) {
        const tbody = document.getElementById('signal-analysis-body');
        const countEl = document.getElementById('symbols-count');

        if (!tbody) return;

        if (!data || !data.signals || data.signals.length === 0) {
            tbody.innerHTML = '<tr><td colspan="10" class="no-data">Scanner initializing...</td></tr>';
            return;
        }

        const signals = data.signals;
        const minScore = data.min_score_required || 4;

        if (countEl) countEl.textContent = signals.length;

        let html = '';
        signals.forEach(signal => {
            const ind = signal.indicators || {};
            const rsi = ind.rsi;
            const stochK = ind.stoch_k;
            const macdHist = ind.macd_histogram;
            const emaCross = ind.ema_cross || '-';
            const volSurge = ind.volume_surge;

            // Format values
            const rsiStr = rsi !== null && rsi !== undefined ? rsi.toFixed(1) : '-';
            const stochStr = stochK !== null && stochK !== undefined ? stochK.toFixed(1) : '-';
            const macdStr = macdHist !== null && macdHist !== undefined
                ? (macdHist > 0 ? '+' : '') + macdHist.toFixed(6) : '-';

            // Color classes
            const rsiClass = rsi < 30 ? 'buy' : rsi > 70 ? 'sell' : '';
            const stochClass = stochK < 20 ? 'buy' : stochK > 80 ? 'sell' : '';
            const macdClass = macdHist > 0 ? 'buy' : macdHist < 0 ? 'sell' : '';
            const emaClass = emaCross === 'bullish' ? 'buy' : emaCross === 'bearish' ? 'sell' : '';

            // Score and signal
            const score = signal.would_trade ? signal.buy_score :
                         (signal.buy_score > 0 ? signal.buy_score : signal.sell_score);
            const scoreClass = signal.would_trade ? 'buy' :
                              (signal.buy_score >= 2 ? 'warming' : '');

            const signalText = signal.would_trade ? 'BUY READY' :
                              signal.action === 'SELL' ? 'OVERBOUGHT' :
                              signal.buy_score >= 2 ? 'WARMING UP' : 'WATCHING';
            const signalClass = signal.would_trade ? 'buy' :
                               signal.action === 'SELL' ? 'sell' : '';

            // Reasons/Analysis
            const reasons = (signal.reasons || []).slice(0, 2).join(', ') || 'Monitoring...';

            // Price formatting
            const priceStr = this.formatPrice(signal.price);

            html += `
                <tr class="${signal.would_trade ? 'highlight-row' : ''}" onclick="dashboard.openSymbolModal('${signal.symbol}')" style="cursor: pointer;">
                    <td class="symbol">${signal.symbol.replace('USD', '/USD')}</td>
                    <td>$${priceStr}</td>
                    <td class="${rsiClass}">${rsiStr}</td>
                    <td class="${stochClass}">${stochStr}</td>
                    <td class="${macdClass}">${macdStr}</td>
                    <td class="${emaClass}">${emaCross}</td>
                    <td>${volSurge ? '<span class="buy">YES</span>' : '-'}</td>
                    <td class="${scoreClass}">${score}/${minScore}</td>
                    <td class="${signalClass}">${signalText}</td>
                    <td class="analysis-text">${reasons}</td>
                </tr>
            `;
        });

        tbody.innerHTML = html;
    }

    renderBotWatchlist(data) {
        const container = document.getElementById('bot-watchlist');
        const statusEl = document.getElementById('watchlist-status');

        if (!container) return;

        if (!data || !data.signals || data.signals.length === 0) {
            container.innerHTML = '<div class="no-data">Scanner initializing...</div>';
            return;
        }

        const signals = data.signals;
        const minScore = data.min_score_required || 3;
        const maxScore = 10; // Max possible score for percentage calculation
        
        // Count states
        const readyCount = signals.filter(s => s.would_trade).length;
        const closeCount = signals.filter(s => !s.would_trade && s.buy_score >= 2).length;

        if (statusEl) {
            statusEl.textContent = readyCount > 0 
                ? `${readyCount} ready to trade` 
                : `Watching ${signals.length} symbols`;
        }

        let html = '';
        signals.forEach(signal => {
            const buyPct = Math.min((signal.buy_score / maxScore) * 100, 100);
            const sellPct = Math.min((signal.sell_score / maxScore) * 100, 100);
            const thresholdPct = (minScore / maxScore) * 100;
            
            // Determine status
            let status, statusClass, itemClass;
            if (signal.would_trade) {
                status = 'READY';
                statusClass = 'ready';
                itemClass = 'hot';
            } else if (signal.buy_score >= 2) {
                status = `${signal.buy_score}/${minScore}`;
                statusClass = 'close';
                itemClass = 'warming';
            } else if (signal.sell_score >= minScore) {
                status = 'OVERBOUGHT';
                statusClass = 'overbought';
                itemClass = '';
            } else {
                status = 'WATCHING';
                statusClass = 'watching';
                itemClass = '';
            }

            // Build indicator gauges (Phase 2: Visual Understanding)
            const indicators = signal.indicators || {};
            const rsi = indicators.rsi;
            const stochK = indicators.stoch_k;
            const macdHist = indicators.macd_histogram;
            const emaCross = indicators.ema_cross;

            // Build compact indicator gauges
            let indicatorGauges = '<div style="display: flex; flex-direction: column; gap: 4px;">';

            // RSI mini gauge
            if (rsi !== null && rsi !== undefined) {
                const rsiPos = Math.min(100, Math.max(0, rsi));
                let rsiClass = 'neutral';
                if (rsi < 30) rsiClass = 'bullish';
                else if (rsi > 70) rsiClass = 'bearish';
                indicatorGauges += `
                    <div style="display: flex; align-items: center; gap: 6px; font-size: 10px;">
                        <span style="color: #666; width: 40px;">RSI</span>
                        <div style="flex: 1; height: 6px; background: #1a1a1a; border-radius: 3px; position: relative; overflow: hidden;">
                            <div style="position: absolute; left: 0; width: 30%; height: 100%; background: rgba(0,255,136,0.15);"></div>
                            <div style="position: absolute; right: 0; width: 30%; height: 100%; background: rgba(255,68,68,0.15);"></div>
                            <div style="position: absolute; left: ${rsiPos}%; top: -1px; width: 4px; height: 8px; background: #fff; border-radius: 2px; transform: translateX(-50%);"></div>
                        </div>
                        <span style="width: 28px; text-align: right;" class="indicator-pill ${rsiClass}">${rsi.toFixed(0)}</span>
                    </div>
                `;
            }

            // StochRSI mini gauge
            if (stochK !== null && stochK !== undefined) {
                const stochPos = Math.min(100, Math.max(0, stochK));
                let stochClass = 'neutral';
                if (stochK < 20) stochClass = 'bullish';
                else if (stochK > 80) stochClass = 'bearish';
                indicatorGauges += `
                    <div style="display: flex; align-items: center; gap: 6px; font-size: 10px;">
                        <span style="color: #666; width: 40px;">Stoch</span>
                        <div style="flex: 1; height: 6px; background: #1a1a1a; border-radius: 3px; position: relative; overflow: hidden;">
                            <div style="position: absolute; left: 0; width: 20%; height: 100%; background: rgba(0,255,136,0.15);"></div>
                            <div style="position: absolute; right: 0; width: 20%; height: 100%; background: rgba(255,68,68,0.15);"></div>
                            <div style="position: absolute; left: ${stochPos}%; top: -1px; width: 4px; height: 8px; background: #fff; border-radius: 2px; transform: translateX(-50%);"></div>
                        </div>
                        <span style="width: 28px; text-align: right;" class="indicator-pill ${stochClass}">${stochK.toFixed(0)}</span>
                    </div>
                `;
            }

            indicatorGauges += '</div>';

            // Also build pills for MACD and EMA (these don't make sense as gauges)
            let indicatorPills = '';
            if (macdHist !== null && macdHist !== undefined) {
                const macdClass = macdHist > 0 ? 'bullish' : 'bearish';
                indicatorPills += `<span class="indicator-pill ${macdClass}">MACD ${macdHist > 0 ? '+' : ''}${macdHist.toFixed(4)}</span>`;
            }
            if (emaCross) {
                const emaClass = emaCross === 'bullish' ? 'bullish' : emaCross === 'bearish' ? 'bearish' : 'neutral';
                indicatorPills += `<span class="indicator-pill ${emaClass}">EMA ${emaCross}</span>`;
            }

            // Generate insight text
            let insight = this.generateWatchlistInsight(signal, minScore);

            // Format price
            const priceStr = signal.price >= 1000 
                ? `$${signal.price.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`
                : signal.price >= 1 
                    ? `$${signal.price.toFixed(4)}`
                    : `$${signal.price.toFixed(6)}`;

            html += `
                <div class="watchlist-item ${itemClass}" onclick="dashboard.openSymbolModal('${signal.symbol}')">
                    <div class="watchlist-header">
                        <div>
                            <span class="watchlist-symbol">${signal.symbol.replace('USD', '')}</span>
                            <span class="watchlist-price">${priceStr}</span>
                        </div>
                        <span class="watchlist-status ${statusClass}">${status}</span>
                    </div>

                    <div class="signal-meter">
                        <div class="meter-label">
                            <span>Buy Signal</span>
                            <span>${signal.buy_score}/${minScore} pts</span>
                        </div>
                        <div class="meter-bar">
                            <div class="meter-fill buy" style="width: ${buyPct}%"></div>
                            <div class="meter-threshold" style="left: ${thresholdPct}%"></div>
                        </div>
                    </div>

                    <!-- Phase 2: Visual Indicator Gauges -->
                    ${indicatorGauges}

                    <div class="watchlist-indicators" style="margin-top: 6px;">
                        ${indicatorPills}
                    </div>

                    <div class="watchlist-insight">${insight}</div>
                </div>
            `;
        });

        container.innerHTML = html;
    }

    generateWatchlistInsight(signal, minScore) {
        const indicators = signal.indicators || {};
        const buyScore = signal.buy_score;
        const sellScore = signal.sell_score;
        
        if (signal.would_trade) {
            return `<span style="color: #00ff88;">Ready to buy - all conditions met</span>`;
        }
        
        if (buyScore >= 2) {
            const needed = minScore - buyScore;
            const hints = [];
            if (indicators.rsi > 35) hints.push('RSI to drop below 35');
            if (indicators.stoch_k > 30) hints.push('StochRSI to drop below 30');
            if (indicators.ema_cross !== 'bullish') hints.push('EMA bullish cross');
            if (indicators.macd_histogram <= 0) hints.push('MACD to turn positive');
            
            return `Need ${needed} more point${needed > 1 ? 's' : ''} - waiting for ${hints.slice(0, 2).join(' or ')}`;
        }
        
        if (sellScore >= minScore) {
            return `Overbought - watching for reversal to buy opportunity`;
        }
        
        // Neutral - give context on what would trigger
        const rsi = indicators.rsi || 50;
        const stochK = indicators.stoch_k || 50;
        
        if (rsi > 50 && stochK > 50) {
            return `Neutral zone - waiting for pullback (RSI ${rsi.toFixed(0)}, Stoch ${stochK.toFixed(0)})`;
        }
        
        return `Monitoring - no strong signals yet`;
    }

    // ==================== ACTIVITY LOG METHODS ====================

    async loadActivityLog() {
        try {
            const params = this.lastActivityTimestamp
                ? `?since=${encodeURIComponent(this.lastActivityTimestamp)}`
                : '?limit=50';

            const baseUrl = typeof buildApiUrl === 'function' ? buildApiUrl('activity') : '/api/v1/activity';
            const response = await fetch(`${baseUrl}${params}`);
            if (!response.ok) return;

            const data = await response.json();
            if (data.entries && data.entries.length > 0) {
                // Update last timestamp for next poll
                this.lastActivityTimestamp = data.entries[0].timestamp;

                // Add new entries (they come newest-first, so reverse for display)
                const newEntries = data.entries.reverse();
                this.activityEntries.push(...newEntries);

                // Keep only last 200
                if (this.activityEntries.length > 200) {
                    this.activityEntries = this.activityEntries.slice(-200);
                }

                this.renderActivityLog(newEntries);
            }

            // Update count
            const countEl = document.getElementById('activity-count');
            if (countEl) {
                countEl.textContent = `${this.activityEntries.length} entries`;
            }
        } catch (error) {
            console.log('Activity log not available:', error.message);
        }
    }

    renderActivityLog(newEntries) {
        const container = document.getElementById('activity-log');
        if (!container) return;

        // Remove "waiting" message if present
        const waiting = container.querySelector('.activity-entry.info');
        if (waiting && waiting.textContent.includes('Waiting')) {
            waiting.remove();
        }

        // Append new entries
        newEntries.forEach(entry => {
            const div = document.createElement('div');
            div.className = `activity-entry ${entry.level || 'info'}`;

            const symbolPart = entry.symbol
                ? `<span class="symbol">${entry.symbol.replace('USD', '')}</span>`
                : '';

            // Phase 3: If entry has signal analysis data, render decision checklist
            if (entry.signal_data || entry.analysis) {
                const signal = entry.signal_data || entry.analysis;
                const checklistHtml = this.renderDecisionChecklist({
                    symbol: entry.symbol,
                    indicators: signal.indicators || {},
                    buy_score: signal.buy_score || signal.score || 0,
                    min_required: signal.min_required || 3,
                    would_trade: signal.would_trade || signal.accepted,
                    reasons: signal.reasons || []
                });

                div.innerHTML = `
                    <span class="time">${entry.time || ''}</span>
                    ${symbolPart}
                    <span class="message">${entry.message}</span>
                    ${checklistHtml}
                `;
            } else {
                div.innerHTML = `
                    <span class="time">${entry.time || ''}</span>
                    ${symbolPart}
                    <span class="message">${entry.message}</span>
                `;
            }

            container.appendChild(div);
        });

        // Auto-scroll if enabled
        const autoScroll = document.getElementById('activity-auto-scroll');
        if (autoScroll && autoScroll.checked) {
            container.scrollTop = container.scrollHeight;
        }
    }

    startActivityPolling() {
        // Poll activity log every 2 seconds for near-real-time updates
        this.activityInterval = setInterval(() => {
            this.loadActivityLog();
        }, 2000);
    }

    clearActivityLog() {
        this.activityEntries = [];
        this.lastActivityTimestamp = null;

        const container = document.getElementById('activity-log');
        if (container) {
            container.innerHTML = '<div class="activity-entry info">Log cleared. Waiting for new activity...</div>';
        }

        const countEl = document.getElementById('activity-count');
        if (countEl) {
            countEl.textContent = '0 entries';
        }
    }

    // ==================== MARKET DATA METHODS ====================

    async loadMarketSnapshots() {
        try {
            const data = await this.fetchData('marketSnapshots');
            this.renderMarketSnapshots(data);
        } catch (error) {
            console.log('Market snapshots not available:', error.message);
            const tbody = document.getElementById('market-snapshots-body');
            if (tbody) {
                tbody.innerHTML = '<tr><td colspan="6" class="no-data">Snapshots unavailable</td></tr>';
            }
        }
    }

    renderMarketSnapshots(data) {
        const tbody = document.getElementById('market-snapshots-body');
        if (!tbody) return;

        if (!data || Object.keys(data).length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="no-data">No price data available</td></tr>';
            return;
        }

        let html = '';
        Object.entries(data).forEach(([symbol, snap]) => {
            const lastPrice = snap.latest_trade?.price;
            const bid = snap.latest_quote?.bid;
            const ask = snap.latest_quote?.ask;
            const spread = (bid && ask) ? ((ask - bid) / ask * 100).toFixed(3) : '-';
            
            // Calculate daily change if we have daily bar data
            let dailyChange = '-';
            let changeClass = '';
            if (snap.daily_bar?.open && snap.daily_bar?.close) {
                const change = ((snap.daily_bar.close - snap.daily_bar.open) / snap.daily_bar.open * 100);
                dailyChange = `${change >= 0 ? '+' : ''}${change.toFixed(2)}%`;
                changeClass = change >= 0 ? 'positive' : 'negative';
            }

            html += `
                <tr onclick="dashboard.openSymbolModal('${symbol}')" style="cursor: pointer;" class="clickable-row">
                    <td style="color: #00ff88; font-weight: 600;" class="clickable-symbol">${symbol}</td>
                    <td>${lastPrice ? this.formatPrice(lastPrice) : '-'}</td>
                    <td>${bid ? this.formatPrice(bid) : '-'}</td>
                    <td>${ask ? this.formatPrice(ask) : '-'}</td>
                    <td>${spread}%</td>
                    <td class="${changeClass}">${dailyChange}</td>
                </tr>
            `;
        });

        tbody.innerHTML = html;
    }

    // ==================== WEBSOCKET UPDATE METHODS ====================
    
    updatePnL(pnlData) {
        // Update P&L display with real-time data
        if (pnlData.current_pnl !== undefined) {
            const pnlElement = document.getElementById('bot-unrealized-pnl');
            if (pnlElement) {
                pnlElement.textContent = this.formatCurrency(pnlData.current_pnl);
            }
        }

        if (pnlData.daily_pnl !== undefined) {
            const dailyPnlElement = document.querySelector('[data-daily-pnl]');
            if (dailyPnlElement) {
                dailyPnlElement.textContent = this.formatCurrency(pnlData.daily_pnl);
            }
        }

        // Update chart if available
        if (this.pnlChart && pnlData.chart_data) {
            this.updateChartData(pnlData.chart_data);
        }
    }

    updateActivityFeed(activityData) {
        // Log activity updates - could be expanded to show in UI
        console.log('Activity:', activityData);

        // Refresh signal analysis when activity comes in
        this.loadSignalAnalysis();
    }

    handleTradeUpdate(tradeData) {
        console.log('New trade:', tradeData);

        // Show notification for new trade
        const message = tradeData.side === 'buy' 
            ? `Bought ${tradeData.symbol} at ${this.formatPrice(tradeData.price)}`
            : `Sold ${tradeData.symbol} at ${this.formatPrice(tradeData.price)}`;
            
        this.showNotification(message, tradeData.side === 'buy' ? 'success' : 'info');

        // Refresh positions after trade
        if (this.socket && this.socketConnected) {
            this.socket.emit('request_update', { type: 'positions' });
        }
    }

    formatActivityTime(timestamp) {
        if (!timestamp) return 'Just now';
        
        const date = new Date(timestamp);
        const now = new Date();
        const diff = now - date;
        
        if (diff < 60000) return 'Just now';
        if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
        if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
        
        return date.toLocaleDateString();
    }

    // ==================== WEBSOCKET UTILITY METHODS ====================
    
    updateChartData(chartData) {
        if (!this.pnlChart || !chartData) return;

        try {
            // Update chart with new data
            if (chartData.timestamps && chartData.pnl_values) {
                this.pnlChart.data.labels = chartData.timestamps.map(ts => 
                    new Date(ts).toLocaleTimeString()
                );
                this.pnlChart.data.datasets[0].data = chartData.pnl_values;
                
                if (chartData.cumulative_pnl) {
                    if (this.pnlChart.data.datasets[1]) {
                        this.pnlChart.data.datasets[1].data = chartData.cumulative_pnl;
                    }
                }
                
                this.pnlChart.update('none'); // Update without animation for real-time
            }
        } catch (error) {
            console.error('Error updating chart:', error);
        }
    }

    // Override existing methods to use WebSocket when available
    startAutoRefresh() {
        // Clear existing interval
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }

        // Don't start polling if WebSocket is connected
        if (this.useWebSocket && this.socketConnected) {
            console.log('WebSocket active, skipping HTTP polling');
            return;
        }

        if (this.autoRefresh) {
            this.refreshInterval = setInterval(() => {
                if (!this.useWebSocket || !this.socketConnected) {
                    this.loadAllData();
                    this.loadBotStatus();
                    this.loadTradeHistory();
                    this.loadSignalAnalysis();
                    this.loadMarketSnapshots();
                    this.updateChart();
                }
            }, 10000); // Refresh every 10 seconds

            // Refresh learning insights less frequently (every 60 seconds)
            if (!this.insightsRefreshInterval) {
                this.insightsRefreshInterval = setInterval(() => {
                    this.loadLearningInsights();
                }, 60000);
            }
        }
    }

    // ==================== SYMBOL DEEP DIVE MODAL ====================

    openSymbolModal(symbol) {
        // Store current symbol - normalize to "BTC/USD" format
        // Handle formats: "BTCUSD", "BTC-USD", "BTC/USD"
        let normalized = symbol.replace('-', '/');
        if (!normalized.includes('/') && normalized.endsWith('USD')) {
            // "BTCUSD" -> "BTC/USD"
            normalized = normalized.slice(0, -3) + '/USD';
        } else if (!normalized.endsWith('/USD')) {
            normalized = `${normalized}/USD`;
        }
        this.currentSymbol = normalized;

        // Show modal
        const modal = document.getElementById('symbol-modal');
        modal.style.display = 'flex';

        // Update symbol name in header
        document.getElementById('modal-symbol').textContent = this.currentSymbol;

        // Reset refresh rate dropdown to default (10s to avoid rate limits)
        const refreshSelect = document.getElementById('refresh-rate-select');
        if (refreshSelect) refreshSelect.value = '10000';

        // Reset scroll tracking for new modal
        this.userHasScrolled = false;
        this.pendingEntryTime = null;  // Clear any stale entry time

        // Initialize chart
        this.initSymbolChart();

        // Load all symbol data
        this.refreshSymbolData();

        // Start fast quote polling (1.5s for live bid/ask/price)
        this.startFastQuotePolling();

        // Start chart/indicator refresh (5s default)
        const refreshRate = parseInt(refreshSelect?.value || '5000');
        if (refreshRate > 0) {
            this.symbolRefreshInterval = setInterval(() => {
                this.loadSymbolIndicators();
                this.loadSymbolChart();
            }, refreshRate);
        }
    }

    closeSymbolModal() {
        const modal = document.getElementById('symbol-modal');
        modal.style.display = 'none';

        // Clear chart refresh interval
        if (this.symbolRefreshInterval) {
            clearInterval(this.symbolRefreshInterval);
            this.symbolRefreshInterval = null;
        }

        // Stop fast quote polling
        this.stopFastQuotePolling();

        // Remove price line
        if (this.priceLine && this.candlestickSeries) {
            try {
                this.candlestickSeries.removePriceLine(this.priceLine);
            } catch (e) {}
            this.priceLine = null;
        }
        
        // Remove forecast series
        if (this.forecastSeries && this.symbolChart) {
            try {
                this.symbolChart.removeSeries(this.forecastSeries);
            } catch (e) {}
            this.forecastSeries = null;
        }

        // Destroy main chart
        if (this.symbolChart) {
            this.symbolChart.remove();
            this.symbolChart = null;
        }

        // Destroy indicator charts
        if (this.indicatorCharts) {
            this.indicatorCharts.forEach(chart => chart.remove());
            this.indicatorCharts = [];
        }

        // Reset scroll tracking
        this.userHasScrolled = false;
        this.currentSymbol = null;
    }

    initSymbolChart() {
        const container = document.getElementById('symbol-chart');
        container.innerHTML = ''; // Clear any existing chart

        // Create chart using TradingView Lightweight Charts
        this.symbolChart = LightweightCharts.createChart(container, {
            width: container.clientWidth,
            height: container.clientHeight,
            layout: {
                background: { color: '#0a0a0a' },
                textColor: '#888',
            },
            grid: {
                vertLines: { color: '#1a1a1a' },
                horzLines: { color: '#1a1a1a' },
            },
            crosshair: {
                mode: LightweightCharts.CrosshairMode.Normal,
            },
            rightPriceScale: {
                borderColor: '#252525',
            },
            timeScale: {
                borderColor: '#252525',
                timeVisible: true,
                secondsVisible: false,
                rightOffset: 20, // Empty space on the right (20 bars worth)
                shiftVisibleRangeOnNewBar: false, // Don't auto-scroll on new data
            },
        });
        
        // Track if user has manually scrolled
        this.userHasScrolled = false;
        this.symbolChart.timeScale().subscribeVisibleLogicalRangeChange(() => {
            this.userHasScrolled = true;
        });

        // Store position price levels for auto-scale
        this.positionPriceLevels = { entry: null, stop: null, target: null };

        // Add candlestick series with autoscale provider to include position lines
        this.candlestickSeries = this.symbolChart.addCandlestickSeries({
            upColor: '#00ff88',
            downColor: '#ff4444',
            borderUpColor: '#00ff88',
            borderDownColor: '#ff4444',
            wickUpColor: '#00ff88',
            wickDownColor: '#ff4444',
            autoscaleInfoProvider: () => {
                // Include position price levels in auto-scale range
                const prices = [
                    this.positionPriceLevels?.entry,
                    this.positionPriceLevels?.stop,
                    this.positionPriceLevels?.target,
                ].filter(p => p != null);

                if (prices.length === 0) return null;

                return {
                    priceRange: {
                        minValue: Math.min(...prices),
                        maxValue: Math.max(...prices),
                    },
                };
            },
        });

        // Add volume series
        this.volumeSeries = this.symbolChart.addHistogramSeries({
            color: '#26a69a',
            priceFormat: {
                type: 'volume',
            },
            priceScaleId: '',
            scaleMargins: {
                top: 0.85,
                bottom: 0,
            },
        });

        // Handle resize
        window.addEventListener('resize', () => {
            if (this.symbolChart && container.clientWidth > 0) {
                this.symbolChart.applyOptions({
                    width: container.clientWidth,
                    height: container.clientHeight,
                });
            }
        });
    }

    async refreshSymbolData() {
        if (!this.currentSymbol) return;

        // Load all data in parallel
        await Promise.all([
            this.loadSymbolChart(),
            this.loadSymbolQuote(),
            this.loadSymbolIndicators(),
            this.loadSymbolPosition(),
            this.loadSymbolTrades(),
        ]);
    }

    async loadSymbolChart() {
        if (!this.currentSymbol) return;

        const timeframe = document.getElementById('timeframe-select').value;
        const symbolPath = this.currentSymbol.replace('/', '-');

        try {
            const response = await fetch(`${API_CONFIG.baseURL}/api/v1/symbol/${symbolPath}/chart?timeframe=${timeframe}&limit=200`);
            const data = await response.json();

            if (data.error) {
                console.error('Chart error:', data.error);
                return;
            }

            if (data.bars && data.bars.length > 0) {
                // Save current visible range before updating (to preserve user scroll)
                const currentRange = this.userHasScrolled ? 
                    this.symbolChart.timeScale().getVisibleLogicalRange() : null;
                
                // Format data for Lightweight Charts
                const candleData = data.bars.map(bar => ({
                    time: Math.floor(bar.timestamp / 1000),
                    open: bar.open,
                    high: bar.high,
                    low: bar.low,
                    close: bar.close,
                }));

                const volumeData = data.bars.map(bar => ({
                    time: Math.floor(bar.timestamp / 1000),
                    value: bar.volume,
                    color: bar.close >= bar.open ? 'rgba(0, 255, 136, 0.3)' : 'rgba(255, 68, 68, 0.3)',
                }));

                this.candlestickSeries.setData(candleData);
                this.volumeSeries.setData(volumeData);
                
                // Store last price for forecast line
                const lastBar = data.bars[data.bars.length - 1];
                this.lastBarTime = Math.floor(lastBar.timestamp / 1000);
                this.lastClosePrice = lastBar.close;
                
                // Add forecast dotted line extending into future
                this.updateForecastLine(lastBar.close, this.lastBarTime, timeframe);

                // Restore scroll position or set initial centered view
                if (currentRange) {
                    // User has scrolled - preserve their position
                    this.symbolChart.timeScale().setVisibleLogicalRange(currentRange);
                } else if (this.pendingEntryTime) {
                    // Scroll to show entry time for active position
                    this.scrollToEntryTime(this.pendingEntryTime);
                    this.pendingEntryTime = null;
                } else {
                    // Initial load - center current price with space on right
                    const barsToShow = 60; // Show ~60 bars
                    const totalBars = candleData.length;
                    this.symbolChart.timeScale().setVisibleLogicalRange({
                        from: totalBars - barsToShow,
                        to: totalBars + 20, // 20 bars of empty space on right
                    });
                }
            }

        } catch (error) {
            console.error('Error loading chart:', error);
        }
    }

    async loadSymbolQuote() {
        if (!this.currentSymbol) return;

        const symbolPath = this.currentSymbol.replace('/', '-');

        try {
            const response = await fetch(`${API_CONFIG.baseURL}/api/v1/symbol/${symbolPath}/quote`);
            const data = await response.json();

            if (data.error) {
                console.error('Quote error:', data.error);
                return;
            }

            // Update header
            if (data.last_price) {
                document.getElementById('modal-price').textContent = this.formatCurrency(data.last_price);
            }

            if (data.daily_change_pct !== null) {
                const changeEl = document.getElementById('modal-change');
                const pct = data.daily_change_pct;
                changeEl.textContent = `${pct >= 0 ? '+' : ''}${pct.toFixed(2)}%`;
                changeEl.className = `symbol-change ${pct >= 0 ? 'positive' : 'negative'}`;
            }

            // Update quote panel
            document.getElementById('quote-bid').textContent = data.bid ? this.formatPrice(data.bid) : '-';
            document.getElementById('quote-ask').textContent = data.ask ? this.formatPrice(data.ask) : '-';
            document.getElementById('quote-spread').textContent = data.spread_pct ? `${data.spread_pct.toFixed(3)}%` : '-';
            document.getElementById('quote-volume').textContent = data.daily_volume ? this.formatVolume(data.daily_volume) : '-';
            document.getElementById('quote-high').textContent = data.daily_high ? this.formatPrice(data.daily_high) : '-';
            document.getElementById('quote-low').textContent = data.daily_low ? this.formatPrice(data.daily_low) : '-';

        } catch (error) {
            console.error('Error loading quote:', error);
        }
    }

    async loadSymbolIndicators() {
        if (!this.currentSymbol) return;

        const symbolPath = this.currentSymbol.replace('/', '-');
        const timeframe = document.getElementById('timeframe-select').value;

        try {
            // Load indicator history for charts
            const response = await fetch(`${API_CONFIG.baseURL}/api/v1/symbol/${symbolPath}/indicators/history?timeframe=${timeframe}&limit=100`);
            const data = await response.json();

            if (data.error) {
                console.error('Indicator history error:', data.error);
                return;
            }

            // Render RSI chart
            this.renderIndicatorChart('rsi-chart', data.data, 'rsi', data.thresholds, '#ffaa00');
            
            // Render StochRSI chart (K and D lines)
            this.renderStochChart('stoch-chart', data.data, data.thresholds);

            // Update current values
            const latest = data.data[data.data.length - 1];
            if (latest) {
                document.getElementById('rsi-value').textContent = latest.rsi ? latest.rsi.toFixed(1) : '-';
                document.getElementById('rsi-value').className = `indicator-chart-value ${this.getRSIClass(latest.rsi)}`;
                
                document.getElementById('stoch-value').textContent = 
                    `K: ${latest.stoch_k?.toFixed(1) || '-'} / D: ${latest.stoch_d?.toFixed(1) || '-'}`;
            }

            // Update signal status bar
            if (data.current_signal) {
                const sig = data.current_signal;
                const pct = Math.min((sig.buy_score / 10) * 100, 100);
                document.getElementById('buy-signal-fill').style.width = `${pct}%`;
                document.getElementById('buy-signal-score').textContent = `${sig.buy_score}/${sig.min_required}`;
                document.getElementById('buy-signal-score').style.color = sig.would_trade ? '#00ff88' : '#888';
                
                // Update insight
                const insightEl = document.getElementById('signal-insight');
                if (sig.would_trade) {
                    insightEl.innerHTML = '<span style="color: #00ff88;">Signal ready - conditions met for buy</span>';
                } else if (sig.buy_score >= 2) {
                    insightEl.textContent = `${sig.min_required - sig.buy_score} more point${sig.min_required - sig.buy_score > 1 ? 's' : ''} needed to trigger buy`;
                } else {
                    insightEl.textContent = 'Watching for oversold conditions...';
                }

                // Update signal factors
                this.updateSignalFactors(latest, sig.factors);
            }

        } catch (error) {
            console.error('Error loading indicators:', error);
        }
    }

    renderIndicatorChart(containerId, data, field, thresholds, color) {
        const container = document.getElementById(containerId);
        if (!container) return;

        container.innerHTML = '';

        const chart = LightweightCharts.createChart(container, {
            width: container.clientWidth,
            height: 80,
            layout: {
                background: { color: 'transparent' },
                textColor: '#666',
            },
            grid: {
                vertLines: { visible: false },
                horzLines: { color: '#1a1a1a' },
            },
            rightPriceScale: {
                borderVisible: false,
                scaleMargins: { top: 0.1, bottom: 0.1 },
            },
            timeScale: {
                visible: false,
            },
            crosshair: {
                horzLine: { visible: false },
                vertLine: { visible: false },
            },
        });

        // Add line series
        const lineSeries = chart.addLineSeries({
            color: color,
            lineWidth: 2,
            priceLineVisible: false,
            lastValueVisible: true,
        });

        const lineData = data
            .filter(d => d[field] !== null)
            .map(d => ({
                time: Math.floor(d.timestamp / 1000),
                value: d[field],
            }));

        lineSeries.setData(lineData);

        // Add threshold lines for RSI
        if (field === 'rsi') {
            // Oversold line (30)
            const oversoldLine = chart.addLineSeries({
                color: '#00ff88',
                lineWidth: 1,
                lineStyle: 2, // Dashed
                priceLineVisible: false,
                lastValueVisible: false,
            });
            oversoldLine.setData(lineData.map(d => ({ time: d.time, value: thresholds.rsi_oversold })));

            // Overbought line (70)
            const overboughtLine = chart.addLineSeries({
                color: '#ff4444',
                lineWidth: 1,
                lineStyle: 2,
                priceLineVisible: false,
                lastValueVisible: false,
            });
            overboughtLine.setData(lineData.map(d => ({ time: d.time, value: thresholds.rsi_overbought })));
        }

        chart.timeScale().fitContent();
        
        // Store for cleanup
        if (!this.indicatorCharts) this.indicatorCharts = [];
        this.indicatorCharts.push(chart);
    }

    renderStochChart(containerId, data, thresholds) {
        const container = document.getElementById(containerId);
        if (!container) return;

        container.innerHTML = '';

        const chart = LightweightCharts.createChart(container, {
            width: container.clientWidth,
            height: 80,
            layout: {
                background: { color: 'transparent' },
                textColor: '#666',
            },
            grid: {
                vertLines: { visible: false },
                horzLines: { color: '#1a1a1a' },
            },
            rightPriceScale: {
                borderVisible: false,
                scaleMargins: { top: 0.1, bottom: 0.1 },
            },
            timeScale: {
                visible: false,
            },
            crosshair: {
                horzLine: { visible: false },
                vertLine: { visible: false },
            },
        });

        // K line (fast)
        const kSeries = chart.addLineSeries({
            color: '#00ff88',
            lineWidth: 2,
            priceLineVisible: false,
            lastValueVisible: true,
        });

        // D line (slow)
        const dSeries = chart.addLineSeries({
            color: '#ff6b6b',
            lineWidth: 1,
            priceLineVisible: false,
            lastValueVisible: false,
        });

        const kData = data
            .filter(d => d.stoch_k !== null)
            .map(d => ({
                time: Math.floor(d.timestamp / 1000),
                value: d.stoch_k,
            }));

        const dData = data
            .filter(d => d.stoch_d !== null)
            .map(d => ({
                time: Math.floor(d.timestamp / 1000),
                value: d.stoch_d,
            }));

        kSeries.setData(kData);
        dSeries.setData(dData);

        // Add threshold lines
        if (kData.length > 0) {
            // Oversold line (20)
            const oversoldLine = chart.addLineSeries({
                color: '#00ff88',
                lineWidth: 1,
                lineStyle: 2,
                priceLineVisible: false,
                lastValueVisible: false,
            });
            oversoldLine.setData(kData.map(d => ({ time: d.time, value: thresholds.stoch_oversold })));

            // Overbought line (80)
            const overboughtLine = chart.addLineSeries({
                color: '#ff4444',
                lineWidth: 1,
                lineStyle: 2,
                priceLineVisible: false,
                lastValueVisible: false,
            });
            overboughtLine.setData(kData.map(d => ({ time: d.time, value: thresholds.stoch_overbought })));
        }

        chart.timeScale().fitContent();
        
        if (!this.indicatorCharts) this.indicatorCharts = [];
        this.indicatorCharts.push(chart);
    }

    updateSignalFactors(latest, factors) {
        if (!latest) return;

        // RSI factor
        const rsiEl = document.getElementById('factor-rsi');
        const rsi = latest.rsi;
        if (rsiEl && rsi !== null) {
            const isActive = rsi < 35;
            const isClose = rsi < 40 && rsi >= 35;
            rsiEl.className = `factor-item ${isActive ? 'active' : isClose ? 'close' : ''}`;
            rsiEl.querySelector('.factor-icon').textContent = isActive ? '●' : '○';
            document.getElementById('factor-rsi-val').textContent = rsi.toFixed(1);
        }

        // StochRSI factor
        const stochEl = document.getElementById('factor-stoch');
        const stoch = latest.stoch_k;
        if (stochEl && stoch !== null) {
            const isActive = stoch < 30;
            const isClose = stoch < 40 && stoch >= 30;
            stochEl.className = `factor-item ${isActive ? 'active' : isClose ? 'close' : ''}`;
            stochEl.querySelector('.factor-icon').textContent = isActive ? '●' : '○';
            document.getElementById('factor-stoch-val').textContent = stoch.toFixed(1);
        }

        // MACD factor
        const macdEl = document.getElementById('factor-macd');
        const macd = latest.macd_hist;
        if (macdEl && macd !== null) {
            const isActive = macd > 0;
            macdEl.className = `factor-item ${isActive ? 'active' : ''}`;
            macdEl.querySelector('.factor-icon').textContent = isActive ? '●' : '○';
            document.getElementById('factor-macd-val').textContent = macd > 0 ? '+' : macd.toFixed(4);
        }

        // EMA factor - need to get this from indicators endpoint
        // For now, we'll update it separately or leave as is
    }

    async loadSymbolPosition() {
        if (!this.currentSymbol) return;

        const symbolPath = this.currentSymbol.replace('/', '-');

        try {
            const response = await fetch(`${API_CONFIG.baseURL}/api/v1/symbol/${symbolPath}/position`);
            const data = await response.json();

            const positionSection = document.getElementById('position-section');
            const closeBtn = document.getElementById('close-position-btn');

            // Clear any existing position lines
            this.clearPositionLines();

            if (data.has_position) {
                positionSection.style.display = 'block';
                closeBtn.style.display = 'block';

                document.getElementById('pos-qty').textContent = data.qty.toFixed(6);
                document.getElementById('pos-entry').textContent = this.formatCurrency(data.avg_entry_price);
                document.getElementById('pos-value').textContent = this.formatCurrency(data.market_value);

                const pnlEl = document.getElementById('pos-pnl');
                // Show per-unit price change for better relative understanding
                const priceChange = data.current_price - data.avg_entry_price;
                const pctChange = data.unrealized_plpc || ((priceChange / data.avg_entry_price) * 100);
                pnlEl.textContent = `${priceChange >= 0 ? '+' : ''}${this.formatPrice(priceChange)} per unit (${pctChange >= 0 ? '+' : ''}${pctChange.toFixed(2)}%)`;
                pnlEl.className = priceChange >= 0 ? 'positive' : 'negative';

                // 1. Time in trade
                const timeEl = document.getElementById('pos-time');
                if (data.is_synced) {
                    // Position was synced, we don't know the real entry time
                    timeEl.textContent = '(synced)';
                    timeEl.title = 'Position existed before bot started - entry time unknown';
                } else if (data.entry_time) {
                    const durationMs = Date.now() - data.entry_time;
                    const mins = Math.floor(durationMs / 60000);
                    const hours = Math.floor(mins / 60);
                    if (hours > 0) {
                        timeEl.textContent = `${hours}h ${mins % 60}m`;
                    } else {
                        timeEl.textContent = `${mins} min`;
                    }
                } else {
                    timeEl.textContent = '-';
                }

                // 2. Progress bar and distance to stop/target
                const entryPrice = data.bot_entry_price || data.avg_entry_price;
                const stopPrice = data.stop_price;
                const targetPrice = data.target_price;
                const currentPrice = data.current_price;

                if (stopPrice && targetPrice) {
                    // Calculate distances
                    const distToStop = ((currentPrice - stopPrice) / currentPrice * 100);
                    const distToTarget = ((targetPrice - currentPrice) / currentPrice * 100);

                    document.getElementById('pos-stop-pct').textContent = `${distToStop.toFixed(2)}% to stop`;
                    document.getElementById('pos-target-pct').textContent = `${distToTarget.toFixed(2)}% to target`;

                    // Calculate marker position (0% = stop, 50% = entry, 100% = target)
                    // Map current price to position in stop-to-target range
                    const range = targetPrice - stopPrice;
                    const positionInRange = (currentPrice - stopPrice) / range;
                    const markerPct = Math.max(0, Math.min(100, positionInRange * 100));

                    document.getElementById('pos-marker').style.left = `${markerPct}%`;
                }

                // 3. Entry reasons
                const reasonsSection = document.getElementById('pos-reasons');
                const reasonsList = document.getElementById('pos-reasons-list');
                if (data.entry_reasons && data.entry_reasons.length > 0) {
                    reasonsSection.style.display = 'block';
                    reasonsList.innerHTML = data.entry_reasons.map(reason => {
                        const isNegative = reason.toLowerCase().includes('blocked') || reason.toLowerCase().includes('warning');
                        return `<span class="reason-tag ${isNegative ? 'negative' : ''}">${reason}</span>`;
                    }).join('');
                } else {
                    reasonsSection.style.display = 'none';
                }

                // Add position lines to chart (entry, stop, target)
                this.addPositionLines(data);

                // Store entry time - will be applied after chart loads
                if (data.entry_time) {
                    this.pendingEntryTime = data.entry_time;
                    // Try to scroll if chart is already loaded
                    if (this.symbolChart && this.candlestickSeries) {
                        this.scrollToEntryTime(data.entry_time);
                    }
                }
            } else {
                positionSection.style.display = 'none';
                closeBtn.style.display = 'none';
            }

        } catch (error) {
            console.error('Error loading position:', error);
        }
    }

    clearPositionLines() {
        // Remove existing position lines from chart
        if (this.candlestickSeries) {
            if (this.entryLine) {
                try { this.candlestickSeries.removePriceLine(this.entryLine); } catch (e) {}
                this.entryLine = null;
            }
            if (this.stopLine) {
                try { this.candlestickSeries.removePriceLine(this.stopLine); } catch (e) {}
                this.stopLine = null;
            }
            if (this.targetLine) {
                try { this.candlestickSeries.removePriceLine(this.targetLine); } catch (e) {}
                this.targetLine = null;
            }
        }
        // Clear price levels for autoscale
        this.positionPriceLevels = { entry: null, stop: null, target: null };
        // Clear entry marker
        if (this.candlestickSeries) {
            try { this.candlestickSeries.setMarkers([]); } catch (e) {}
        }
    }

    addPositionLines(positionData) {
        if (!this.candlestickSeries) return;

        // Prefer bot's tracked entry price, fall back to Alpaca's avg entry
        const entryPrice = positionData.bot_entry_price || positionData.avg_entry_price;
        const stopPrice = positionData.stop_price;
        const targetPrice = positionData.target_price;

        // Store price levels for autoscale provider
        this.positionPriceLevels = {
            entry: entryPrice,
            stop: stopPrice,
            target: targetPrice,
        };

        // Entry price line (green, solid)
        if (entryPrice) {
            this.entryLine = this.candlestickSeries.createPriceLine({
                price: entryPrice,
                color: '#00ff88',
                lineWidth: 2,
                lineStyle: 0, // Solid
                axisLabelVisible: true,
                title: 'Entry',
            });
        }

        // Stop loss line (red, dashed)
        if (stopPrice) {
            this.stopLine = this.candlestickSeries.createPriceLine({
                price: stopPrice,
                color: '#ff4444',
                lineWidth: 1,
                lineStyle: 2, // Dashed
                axisLabelVisible: true,
                title: 'Stop',
            });
        }

        // Target price line (cyan, dashed)
        if (targetPrice) {
            this.targetLine = this.candlestickSeries.createPriceLine({
                price: targetPrice,
                color: '#00d4ff',
                lineWidth: 1,
                lineStyle: 2, // Dashed
                axisLabelVisible: true,
                title: 'Target',
            });
        }

        // Trigger re-scale to include position price levels
        if (this.symbolChart) {
            // Reset auto-scale to include new price levels from autoscaleInfoProvider
            this.symbolChart.priceScale('right').applyOptions({
                autoScale: true,
            });

            // Fit content to trigger re-calculation
            this.symbolChart.timeScale().fitContent();
        }
    }

    scrollToEntryTime(entryTimeMs) {
        if (!this.symbolChart || !this.candlestickSeries) return;

        // Convert ms to seconds for TradingView
        const entryTimeSec = Math.floor(entryTimeMs / 1000);

        // Get the candle data to find the entry bar index
        const data = this.candlestickSeries.data ? this.candlestickSeries.data() : null;
        if (!data || data.length === 0) {
            console.log('No candle data yet for scroll');
            return;
        }

        // Find the bar closest to entry time
        let entryBarIndex = 0;
        for (let i = 0; i < data.length; i++) {
            if (data[i].time >= entryTimeSec) {
                entryBarIndex = Math.max(0, i - 1); // Bar just before or at entry
                break;
            }
            entryBarIndex = i; // Entry is after all data, use last bar
        }

        // Calculate how many bars to show: from entry to end, plus padding
        const totalBars = data.length;
        const barsFromEntryToEnd = totalBars - entryBarIndex;
        const paddingBefore = Math.max(5, Math.floor(barsFromEntryToEnd * 0.15)); // 15% padding before
        const paddingAfter = 15; // 15 bars of space on right

        // Set visible range from before entry to after current
        this.symbolChart.timeScale().setVisibleLogicalRange({
            from: Math.max(0, entryBarIndex - paddingBefore),
            to: totalBars + paddingAfter,
        });

        // Store entry time for adding a marker
        this.entryTimeSec = entryTimeSec;

        // Add marker at entry candle
        const entryBar = data[entryBarIndex];
        if (entryBar) {
            this.candlestickSeries.setMarkers([{
                time: entryBar.time,
                position: 'belowBar',
                color: '#00ff88',
                shape: 'arrowUp',
                text: 'Entry',
            }]);
        }

        console.log(`Scrolled to entry: bar ${entryBarIndex} of ${totalBars}, time ${new Date(entryTimeMs).toLocaleTimeString()}`);
    }

    async loadSymbolTrades() {
        if (!this.currentSymbol) return;

        const symbolPath = this.currentSymbol.replace('/', '-');

        try {
            const response = await fetch(`${API_CONFIG.baseURL}/api/v1/symbol/${symbolPath}/trades`);
            const data = await response.json();

            const container = document.getElementById('symbol-trades');

            if (!data.trades || data.trades.length === 0) {
                container.innerHTML = '<div class="no-data">No trades for this symbol</div>';
                return;
            }

            let html = '';
            data.trades.slice(0, 10).forEach(trade => {
                html += `
                    <div class="trade-item">
                        <span class="${trade.side}">${trade.side.toUpperCase()}</span>
                        <span>${trade.qty.toFixed(6)}</span>
                        <span>${this.formatCurrency(trade.price)}</span>
                        <span style="color: #666;">${this.formatTime(trade.time)}</span>
                    </div>
                `;
            });

            container.innerHTML = html;

        } catch (error) {
            console.error('Error loading trades:', error);
        }
    }

    changeTimeframe(timeframe) {
        this.loadSymbolChart();
        this.loadSymbolIndicators();
    }

    changeRefreshRate(rate) {
        const rateMs = parseInt(rate);
        
        // Clear existing chart refresh interval
        if (this.symbolRefreshInterval) {
            clearInterval(this.symbolRefreshInterval);
            this.symbolRefreshInterval = null;
        }
        
        // Set new interval (0 = manual only)
        if (rateMs > 0) {
            this.symbolRefreshInterval = setInterval(() => {
                this.loadSymbolIndicators();
                // Only refresh chart on slower intervals (5s+)
                if (rateMs >= 5000) {
                    this.loadSymbolChart();
                }
            }, rateMs);
        }
        
        console.log(`Chart refresh rate: ${rateMs === 0 ? 'manual' : rateMs + 'ms'}`);
    }

    startFastQuotePolling() {
        // Fast quote polling runs every 3 seconds to avoid rate limits
        if (this.fastQuoteInterval) {
            clearInterval(this.fastQuoteInterval);
        }
        
        this.fastQuoteInterval = setInterval(() => {
            this.loadLiveQuote();
        }, 3000);
        
        // Initial load
        this.loadLiveQuote();
    }

    stopFastQuotePolling() {
        if (this.fastQuoteInterval) {
            clearInterval(this.fastQuoteInterval);
            this.fastQuoteInterval = null;
        }
    }

    async loadLiveQuote() {
        if (!this.currentSymbol) return;

        const symbolPath = this.currentSymbol.replace('/', '-');

        try {
            const response = await fetch(`${API_CONFIG.baseURL}/api/v1/symbol/${symbolPath}/quote`);
            const data = await response.json();

            if (data.error) return;

            // Update header price with flash animation
            if (data.last_price) {
                const priceEl = document.getElementById('modal-price');
                const newPrice = this.formatCurrency(data.last_price);
                const oldPrice = priceEl.textContent;
                
                if (oldPrice !== newPrice) {
                    priceEl.textContent = newPrice;
                    // Flash animation
                    const isUp = parseFloat(newPrice.replace(/[^0-9.-]/g, '')) > parseFloat(oldPrice.replace(/[^0-9.-]/g, ''));
                    priceEl.classList.remove('flash-up', 'flash-down');
                    void priceEl.offsetWidth; // Trigger reflow
                    priceEl.classList.add(isUp ? 'flash-up' : 'flash-down');
                }
            }

            // Update live bid/ask in header
            const liveBid = document.getElementById('live-bid');
            const liveAsk = document.getElementById('live-ask');
            
            if (liveBid && data.bid) {
                const newBid = this.formatPrice(data.bid);
                if (liveBid.textContent !== newBid) {
                    liveBid.textContent = newBid;
                    liveBid.classList.remove('tick-flash');
                    void liveBid.offsetWidth;
                    liveBid.classList.add('tick-flash');
                }
            }
            
            if (liveAsk && data.ask) {
                const newAsk = this.formatPrice(data.ask);
                if (liveAsk.textContent !== newAsk) {
                    liveAsk.textContent = newAsk;
                    liveAsk.classList.remove('tick-flash');
                    void liveAsk.offsetWidth;
                    liveAsk.classList.add('tick-flash');
                }
            }

            // Update last update timestamp
            const lastUpdateEl = document.getElementById('last-update');
            if (lastUpdateEl) {
                const now = new Date();
                lastUpdateEl.textContent = now.toLocaleTimeString();
            }

            // Also update quote panel values
            document.getElementById('quote-bid').textContent = data.bid ? this.formatPrice(data.bid) : '-';
            document.getElementById('quote-ask').textContent = data.ask ? this.formatPrice(data.ask) : '-';
            document.getElementById('quote-spread').textContent = data.spread_pct ? `${data.spread_pct.toFixed(3)}%` : '-';

            // Update real-time price line on chart
            if (this.candlestickSeries && data.last_price) {
                this.updatePriceLine(data.last_price, data.bid, data.ask);
            }

        } catch (error) {
            console.error('Error loading live quote:', error);
        }
    }

    updatePriceLine(price, bid, ask) {
        // Remove existing price line
        if (this.priceLine) {
            this.candlestickSeries.removePriceLine(this.priceLine);
        }
        
        // Add current price line
        this.priceLine = this.candlestickSeries.createPriceLine({
            price: price,
            color: '#ffaa00',
            lineWidth: 1,
            lineStyle: 2, // Dashed
            axisLabelVisible: true,
            title: 'Last',
        });
    }

    updateForecastLine(lastPrice, lastTime, timeframe) {
        // Remove existing forecast series
        if (this.forecastSeries) {
            this.symbolChart.removeSeries(this.forecastSeries);
            this.forecastSeries = null;
        }
        
        // Calculate time interval based on timeframe
        const intervals = {
            '1Min': 60,
            '5Min': 300,
            '15Min': 900,
            '1Hour': 3600,
        };
        const interval = intervals[timeframe] || 60;
        
        // Create forecast line extending 15 bars into the future
        const forecastData = [];
        for (let i = 0; i <= 15; i++) {
            forecastData.push({
                time: lastTime + (i * interval),
                value: lastPrice,
            });
        }
        
        // Add dotted forecast line series
        this.forecastSeries = this.symbolChart.addLineSeries({
            color: 'rgba(255, 170, 0, 0.4)',
            lineWidth: 1,
            lineStyle: 1, // Dotted
            priceLineVisible: false,
            lastValueVisible: false,
            crosshairMarkerVisible: false,
        });
        
        this.forecastSeries.setData(forecastData);
    }

    async buySymbol() {
        if (!this.currentSymbol) return;

        const amount = document.getElementById('trade-amount').value;
        if (!amount || amount <= 0) {
            this.showNotification('Please enter a valid amount', 'error');
            return;
        }

        const symbolPath = this.currentSymbol.replace('/', '-');

        try {
            this.showNotification(`Placing buy order for ${this.currentSymbol}...`, 'info');
            
            const response = await fetch(`${API_CONFIG.baseURL}/api/v1/symbol/${symbolPath}/buy`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ notional: parseFloat(amount) }),
            });

            const data = await response.json();

            if (data.error) {
                this.showNotification(`Buy failed: ${data.error}`, 'error');
            } else {
                // Show initial status and start polling for fill
                this.showOrderStatus(data, 'buy');
                this.pollOrderStatus(data.order_id, 'buy');
            }

        } catch (error) {
            this.showNotification(`Buy failed: ${error.message}`, 'error');
        }
    }

    async sellSymbol() {
        if (!this.currentSymbol) return;

        const amount = document.getElementById('trade-amount').value;
        const symbolPath = this.currentSymbol.replace('/', '-');

        // Check if we have a position
        try {
            const posResponse = await fetch(`${API_CONFIG.baseURL}/api/v1/symbol/${symbolPath}/position`);
            const posData = await posResponse.json();

            if (!posData.has_position) {
                this.showNotification('No position to sell', 'error');
                return;
            }

            this.showNotification(`Placing sell order for ${this.currentSymbol}...`, 'info');

            // Calculate quantity to sell based on dollar amount
            const qtyToSell = parseFloat(amount) / posData.current_price;

            const response = await fetch(`${API_CONFIG.baseURL}/api/v1/symbol/${symbolPath}/sell`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ qty: qtyToSell }),
            });

            const data = await response.json();

            if (data.error) {
                this.showNotification(`Sell failed: ${data.error}`, 'error');
            } else {
                this.showOrderStatus(data, 'sell');
                this.pollOrderStatus(data.order_id, 'sell');
            }

        } catch (error) {
            this.showNotification(`Sell failed: ${error.message}`, 'error');
        }
    }

    async closePosition() {
        if (!this.currentSymbol) return;

        const symbolPath = this.currentSymbol.replace('/', '-');

        try {
            this.showNotification(`Closing position for ${this.currentSymbol}...`, 'info');
            
            const response = await fetch(`${API_CONFIG.baseURL}/api/v1/symbol/${symbolPath}/sell`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ close_all: true }),
            });

            const data = await response.json();

            if (data.error) {
                this.showNotification(`Close failed: ${data.error}`, 'error');
            } else {
                this.showNotification(`Position closed for ${this.currentSymbol}`, 'success');
                setTimeout(() => {
                    this.loadSymbolPosition();
                    this.loadSymbolTrades();
                    this.loadTradeHistory();
                }, 1000);
            }

        } catch (error) {
            this.showNotification(`Close failed: ${error.message}`, 'error');
        }
    }

    showOrderStatus(orderData, side) {
        const status = orderData.order_status || 'pending';
        const statusText = this.getOrderStatusText(status);
        const sideText = side === 'buy' ? 'Buy' : 'Sell';
        
        if (status === 'filled') {
            const price = orderData.filled_avg_price ? `@ $${parseFloat(orderData.filled_avg_price).toFixed(2)}` : '';
            this.showNotification(`${sideText} FILLED ${price}`, 'success');
        } else if (status === 'partially_filled') {
            this.showNotification(`${sideText} order partially filled (${orderData.filled_qty}/${orderData.qty})`, 'info');
        } else {
            this.showNotification(`${sideText} order ${statusText}`, 'info');
        }
    }

    getOrderStatusText(status) {
        const statusMap = {
            'new': 'submitted',
            'accepted': 'accepted',
            'pending_new': 'pending',
            'accepted_for_bidding': 'accepted',
            'filled': 'filled',
            'partially_filled': 'partially filled',
            'done_for_day': 'done for day',
            'canceled': 'canceled',
            'expired': 'expired',
            'replaced': 'replaced',
            'pending_cancel': 'canceling',
            'pending_replace': 'replacing',
            'stopped': 'stopped',
            'rejected': 'rejected',
            'suspended': 'suspended',
            'calculated': 'calculated',
        };
        return statusMap[status] || status;
    }

    async pollOrderStatus(orderId, side) {
        if (!orderId) return;
        
        let attempts = 0;
        const maxAttempts = 20; // Poll for up to 20 seconds
        
        const poll = async () => {
            attempts++;
            
            try {
                const response = await fetch(`${API_CONFIG.baseURL}/api/v1/order/${orderId}`);
                const data = await response.json();
                
                if (data.error) {
                    console.error('Order status error:', data.error);
                    return;
                }
                
                const status = data.status;
                
                if (status === 'filled') {
                    const price = data.filled_avg_price ? parseFloat(data.filled_avg_price).toFixed(2) : '?';
                    const qty = data.filled_qty || data.qty;
                    this.showNotification(
                        `${side === 'buy' ? 'Buy' : 'Sell'} FILLED: ${qty} @ $${price}`, 
                        'success'
                    );
                    // Refresh data
                    this.loadSymbolPosition();
                    this.loadSymbolTrades();
                    this.loadTradeHistory();
                    return; // Stop polling
                    
                } else if (status === 'canceled' || status === 'rejected' || status === 'expired') {
                    this.showNotification(`Order ${status}: ${data.symbol}`, 'error');
                    return; // Stop polling
                    
                } else if (status === 'partially_filled') {
                    this.showNotification(
                        `Partially filled: ${data.filled_qty}/${data.qty}`, 
                        'info'
                    );
                }
                
                // Continue polling if not done
                if (attempts < maxAttempts) {
                    setTimeout(poll, 1000);
                } else {
                    // Timeout - order may still be pending
                    this.showNotification(
                        `Order still ${this.getOrderStatusText(status)} - check positions`, 
                        'warning'
                    );
                    this.loadSymbolPosition();
                }
                
            } catch (error) {
                console.error('Poll order status error:', error);
                if (attempts < maxAttempts) {
                    setTimeout(poll, 1000);
                }
            }
        };
        
        // Start polling after 500ms (give order time to process)
        setTimeout(poll, 500);
    }

    getRSIClass(rsi) {
        if (!rsi) return '';
        if (rsi >= 70) return 'negative'; // Overbought
        if (rsi <= 30) return 'positive'; // Oversold
        return '';
    }

    formatVolume(volume) {
        if (volume >= 1e9) return (volume / 1e9).toFixed(2) + 'B';
        if (volume >= 1e6) return (volume / 1e6).toFixed(2) + 'M';
        if (volume >= 1e3) return (volume / 1e3).toFixed(2) + 'K';
        return volume.toFixed(2);
    }

    // ==================== PHASE 1: POSITION LIFECYCLE CARDS ====================

    /**
     * Renders a visual position lifecycle card showing the trade's journey
     * from stop loss through entry to target.
     *
     * @param {Object} pos - Position data with entry_price, current_price, stop_price, target_price
     * @returns {string} HTML for the lifecycle card
     */
    renderPositionLifecycle(pos) {
        const entryPrice = pos.entry_price || pos.avg_entry_price || 0;
        const currentPrice = pos.current_price || entryPrice;
        const stopPrice = pos.stop_price || (entryPrice * 0.985);  // Default 1.5% stop
        const targetPrice = pos.target_price || (entryPrice * 1.02); // Default 2% target

        // Calculate position in the range (0% = stop, 100% = target)
        const range = targetPrice - stopPrice;
        const positionInRange = range > 0 ? ((currentPrice - stopPrice) / range) * 100 : 50;
        const clampedPosition = Math.max(0, Math.min(100, positionInRange));

        // Calculate P&L percentage
        const pnlPct = entryPrice > 0 ? ((currentPrice - entryPrice) / entryPrice) * 100 : 0;
        const pnlValue = pos.unrealized_pnl || (pos.quantity * (currentPrice - entryPrice));
        const isProfit = pnlPct >= 0;

        // Entry point position
        const entryPosition = range > 0 ? ((entryPrice - stopPrice) / range) * 100 : 50;

        // Danger zone is 0-30%, profit zone is 70-100%
        const dangerZoneWidth = Math.min(30, entryPosition);
        const profitZoneStart = Math.max(70, entryPosition);

        // Format hold time
        const holdTimeStr = this.formatHoldTime(pos.hold_time_seconds || 0);

        // Entry reason (from bot)
        const entryReason = pos.entry_reason || pos.signal_reason || 'Signal triggered';

        // Make symbol clickable to open modal
        const clickableSymbol = pos.symbol?.replace('/USD', 'USD') || pos.symbol;

        return `
            <div class="position-lifecycle ${isProfit ? 'in-profit' : 'in-loss'}" style="cursor: pointer;" onclick="dashboard.openSymbolModal('${clickableSymbol}')">
                <div class="lifecycle-header">
                    <div>
                        <span class="lifecycle-symbol">${pos.symbol?.replace('USD', '/USD') || pos.symbol}</span>
                        <span class="lifecycle-side ${pos.side === 'long' ? 'long' : 'short'}">${pos.side || 'Long'}</span>
                    </div>
                    <span class="lifecycle-pnl ${isProfit ? 'positive' : 'negative'}">
                        ${isProfit ? '+' : ''}${pnlPct.toFixed(2)}%
                    </span>
                </div>

                <div class="lifecycle-labels">
                    <span class="stop">STOP LOSS</span>
                    <span>ENTRY</span>
                    <span class="target">TARGET</span>
                </div>

                <div class="lifecycle-track">
                    <div class="lifecycle-danger-zone" style="width: ${dangerZoneWidth}%"></div>
                    <div class="lifecycle-profit-zone" style="width: ${100 - profitZoneStart}%"></div>
                    <div class="lifecycle-entry-marker" style="left: ${entryPosition}%"></div>
                    <div class="lifecycle-current-marker ${isProfit ? '' : 'in-loss'}" style="left: ${clampedPosition}%">
                        ${isProfit ? '●' : '●'}
                    </div>
                </div>

                <div class="lifecycle-prices">
                    <span class="stop">
                        <span class="label">Stop</span>
                        <span class="value">${this.formatPrice(stopPrice)}</span>
                        <span class="label">-${((entryPrice - stopPrice) / entryPrice * 100).toFixed(1)}%</span>
                    </span>
                    <span>
                        <span class="label">Entry</span>
                        <span class="value">${this.formatPrice(entryPrice)}</span>
                    </span>
                    <span>
                        <span class="label">Current</span>
                        <span class="value" style="color: ${isProfit ? '#00ff88' : '#ff4444'}">${this.formatPrice(currentPrice)}</span>
                    </span>
                    <span class="target">
                        <span class="label">Target</span>
                        <span class="value">${this.formatPrice(targetPrice)}</span>
                        <span class="label">+${((targetPrice - entryPrice) / entryPrice * 100).toFixed(1)}%</span>
                    </span>
                </div>

                <div class="lifecycle-reason">
                    <strong>Entry:</strong> "${entryReason}"
                </div>

                <div class="lifecycle-footer">
                    <span class="lifecycle-time">Time in trade: <span>${holdTimeStr}</span></span>
                    <span class="lifecycle-pnl ${isProfit ? 'positive' : 'negative'}">
                        ${isProfit ? '+' : ''}${this.formatCurrency(pnlValue)}
                    </span>
                    <button class="btn danger small" onclick="event.stopPropagation(); dashboard.liquidatePosition('${pos.symbol}')">Close</button>
                </div>
            </div>
        `;
    }

    // ==================== PHASE 2: INDICATOR GAUGES ====================

    /**
     * Renders a visual gauge for an indicator value within a range.
     * Shows oversold/overbought zones with color coding.
     *
     * @param {string} label - Indicator name (e.g., "RSI", "StochK")
     * @param {number} value - Current indicator value
     * @param {number} min - Minimum value (default 0)
     * @param {number} max - Maximum value (default 100)
     * @param {number} oversold - Oversold threshold (default 30)
     * @param {number} overbought - Overbought threshold (default 70)
     * @returns {string} HTML for the gauge
     */
    renderIndicatorGauge(label, value, min = 0, max = 100, oversold = 30, overbought = 70) {
        if (value === null || value === undefined) {
            return `
                <div class="indicator-gauge">
                    <div class="gauge-header">
                        <span class="gauge-label">${label}</span>
                        <span class="gauge-value">-</span>
                    </div>
                    <div class="gauge-track">
                        <div class="gauge-zones">
                            <div class="gauge-zone oversold" style="width: ${(oversold - min) / (max - min) * 100}%"></div>
                            <div class="gauge-zone neutral"></div>
                            <div class="gauge-zone overbought" style="width: ${(max - overbought) / (max - min) * 100}%"></div>
                        </div>
                    </div>
                </div>
            `;
        }

        const position = ((value - min) / (max - min)) * 100;
        const clampedPos = Math.max(0, Math.min(100, position));

        let valueClass = 'neutral';
        if (value <= oversold) valueClass = 'bullish';
        else if (value >= overbought) valueClass = 'bearish';

        return `
            <div class="indicator-gauge">
                <div class="gauge-header">
                    <span class="gauge-label">${label}</span>
                    <span class="gauge-value ${valueClass}">${value.toFixed(1)}</span>
                </div>
                <div class="gauge-track">
                    <div class="gauge-zones">
                        <div class="gauge-zone oversold" style="width: ${(oversold - min) / (max - min) * 100}%"></div>
                        <div class="gauge-zone neutral" style="width: ${(overbought - oversold) / (max - min) * 100}%"></div>
                        <div class="gauge-zone overbought" style="width: ${(max - overbought) / (max - min) * 100}%"></div>
                    </div>
                    <div class="gauge-marker" style="left: ${clampedPos}%"></div>
                </div>
                <div class="gauge-scale">
                    <span>${min}</span>
                    <span>${oversold}</span>
                    <span>${Math.round((min + max) / 2)}</span>
                    <span>${overbought}</span>
                    <span>${max}</span>
                </div>
            </div>
        `;
    }

    // ==================== PHASE 3: DECISION CHECKLIST ====================

    /**
     * Renders a decision checklist showing which signal conditions passed/failed.
     *
     * @param {Object} signal - Signal data with indicators and reasons
     * @returns {string} HTML for the checklist
     */
    renderDecisionChecklist(signal) {
        const indicators = signal.indicators || {};
        const buyScore = signal.buy_score || 0;
        const minScore = signal.min_required || 3;

        // Build checklist items from indicators
        const checks = [];

        // RSI check
        const rsi = indicators.rsi;
        if (rsi !== null && rsi !== undefined) {
            let passed = rsi < 40;
            let partial = rsi < 50 && rsi >= 40;
            let points = rsi < 25 ? 4 : rsi < 30 ? 3 : rsi < 40 ? 2 : rsi < 50 ? 1 : 0;
            checks.push({
                name: `RSI in buy zone (<40)`,
                value: rsi.toFixed(1),
                passed,
                partial,
                points
            });
        }

        // StochRSI check
        const stochK = indicators.stoch_k;
        if (stochK !== null && stochK !== undefined) {
            let passed = stochK < 30;
            let partial = stochK < 50 && stochK >= 30;
            let points = stochK < 15 ? 4 : stochK < 25 ? 3 : stochK < 40 ? 2 : stochK < 50 ? 1 : 0;
            checks.push({
                name: `StochRSI low (<30)`,
                value: stochK.toFixed(1),
                passed,
                partial,
                points
            });
        }

        // MACD check
        const macd = indicators.macd_histogram;
        if (macd !== null && macd !== undefined) {
            let passed = macd > 0;
            checks.push({
                name: `MACD positive`,
                value: (macd > 0 ? '+' : '') + macd.toFixed(4),
                passed,
                partial: false,
                points: passed ? 1 : 0
            });
        }

        // EMA check
        const ema = indicators.ema_cross;
        if (ema) {
            let passed = ema === 'bullish';
            checks.push({
                name: `EMA trend bullish`,
                value: ema,
                passed,
                partial: false,
                points: passed ? 1 : 0
            });
        }

        // Volume surge check
        if (indicators.volume_surge !== undefined) {
            let passed = indicators.volume_surge;
            checks.push({
                name: `Volume surge`,
                value: passed ? 'Yes' : 'No',
                passed,
                partial: false,
                points: passed ? 1 : 0
            });
        }

        // Determine overall status
        let scoreClass = 'watching';
        if (signal.would_trade) scoreClass = 'ready';
        else if (buyScore >= 2) scoreClass = 'close';

        // Build HTML
        let itemsHtml = checks.map(check => {
            let iconClass = check.passed ? 'pass' : check.partial ? 'partial' : 'fail';
            let icon = check.passed ? '✓' : check.partial ? '◐' : '✗';
            return `
                <div class="checklist-item ${check.passed ? 'pass' : ''}">
                    <span class="checklist-icon ${iconClass}">${icon}</span>
                    <span class="checklist-text">${check.name}</span>
                    <span class="checklist-points">${check.passed || check.partial ? `+${check.points}` : '0'}</span>
                </div>
            `;
        }).join('');

        return `
            <div class="decision-checklist">
                <div class="checklist-header" onclick="this.nextElementSibling.classList.toggle('expanded'); this.querySelector('.expand-icon').textContent = this.nextElementSibling.classList.contains('expanded') ? '▼' : '▶'">
                    <span class="checklist-symbol">${signal.symbol?.replace('USD', '/USD')}</span>
                    <span class="checklist-score ${scoreClass}">${buyScore}/${minScore} pts</span>
                    <span class="expand-icon" style="color: #666; font-size: 10px;">▶</span>
                </div>
                <div class="checklist-items">
                    ${itemsHtml}
                </div>
            </div>
        `;
    }

    // ==================== PHASE 4: LEARNING INSIGHTS ====================

    async loadLearningInsights() {
        try {
            const response = await fetch(`${API_CONFIG.baseURL}/api/v1/learning/insights`);
            const data = await response.json();

            if (data.error) {
                console.error('Learning insights error:', data.error);
                document.getElementById('learning-insights').innerHTML =
                    '<div class="no-data">Learning system initializing...</div>';
                return;
            }

            this.renderLearningInsights(data);
        } catch (error) {
            console.log('Learning insights not available:', error.message);
            document.getElementById('learning-insights').innerHTML =
                '<div class="no-data">Learning insights unavailable</div>';
        }
    }

    renderLearningInsights(data) {
        const container = document.getElementById('learning-insights');
        if (!container) return;

        // Parse API response (strings like "50.0%" need to be converted to numbers)
        const parsePercent = (str) => {
            if (!str) return 0;
            if (typeof str === 'number') return str;
            return parseFloat(str.replace('%', '')) || 0;
        };

        const totalTrades = data.total_trades_analyzed || data.total_trades || 0;
        const winRate = parsePercent(data.win_rate);
        const profitFactor = parseFloat(data.profit_factor) || 0;
        const avgWin = parsePercent(data.avg_win);
        const avgLoss = parsePercent(data.avg_loss);

        // Optimal ranges (strings like "25-40")
        const optimalRsiRange = data.optimal_rsi_range || '--';
        const optimalStochRange = data.optimal_stoch_range || '--';
        const avoidRsiAbove = data.avoid_rsi_above || '--';
        const avoidStochAbove = data.avoid_stoch_above || '--';

        // Symbol performance
        const symbolPerf = data.symbol_performance || {};
        const sortedSymbols = Object.entries(symbolPerf);

        // Best/worst hours
        const bestHours = data.best_hours || [];
        const worstHours = data.worst_hours || [];

        // Build HTML
        let html = `
            <!-- Performance Summary -->
            <div class="insights-section">
                <div class="insights-title">Performance</div>
                <div class="insights-stat">
                    <span class="label">Total Trades</span>
                    <span class="value">${totalTrades}</span>
                </div>
                <div class="insights-stat">
                    <span class="label">Win Rate</span>
                    <span class="value ${winRate >= 50 ? 'positive' : winRate > 0 ? 'negative' : ''}">${data.win_rate || '0%'}</span>
                </div>
                <div class="insights-stat">
                    <span class="label">Profit Factor</span>
                    <span class="value ${profitFactor >= 1 ? 'positive' : profitFactor > 0 ? 'negative' : ''}">${data.profit_factor || '0'}</span>
                </div>
                <div class="insights-stat">
                    <span class="label">Avg Win / Loss</span>
                    <span class="value"><span class="positive">${data.avg_win || '0%'}</span> / <span class="negative">${data.avg_loss || '0%'}</span></span>
                </div>
            </div>
        `;

        // Optimal entry conditions (learned patterns)
        if (totalTrades >= 5) {
            html += `
                <div class="insights-section">
                    <div class="insights-title">Learned Optimal Entry</div>
                    <div class="insights-stat">
                        <span class="label">RSI Range</span>
                        <span class="value positive">${optimalRsiRange}</span>
                    </div>
                    <div class="insights-stat">
                        <span class="label">StochRSI Range</span>
                        <span class="value positive">${optimalStochRange}</span>
                    </div>
                    <div class="insights-stat">
                        <span class="label">Avoid RSI Above</span>
                        <span class="value negative">${avoidRsiAbove}</span>
                    </div>
                    <div class="insights-stat">
                        <span class="label">Avoid Stoch Above</span>
                        <span class="value negative">${avoidStochAbove}</span>
                    </div>
                </div>
            `;
        }

        // Symbol performance section
        if (sortedSymbols.length > 0) {
            html += `
                <div class="insights-section">
                    <div class="insights-title">Symbol Performance</div>
                    <div class="insights-list">
                        ${sortedSymbols.slice(0, 5).map(([symbol, winRateStr], i) => `
                            <div class="insights-list-item">
                                <span class="rank">${i + 1}.</span>
                                <span class="name">${symbol.replace('USD', '')}</span>
                                <span class="metric">${winRateStr}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }

        // Time patterns
        if (bestHours.length > 0 || worstHours.length > 0) {
            html += `
                <div class="insights-section">
                    <div class="insights-title">Time Patterns</div>
                    ${bestHours.length > 0 ? `
                        <div class="insights-pattern">
                            <strong>Best Hours (UTC):</strong> ${bestHours.join(', ')}:00
                        </div>
                    ` : ''}
                    ${worstHours.length > 0 ? `
                        <div class="insights-pattern" style="border-left-color: #ff4444;">
                            <strong>Worst Hours (UTC):</strong> ${worstHours.join(', ')}:00
                        </div>
                    ` : ''}
                </div>
            `;
        }

        // Suggested parameters
        const suggestedParams = data.suggested_params || {};
        if (Object.keys(suggestedParams).length > 0 && totalTrades >= 5) {
            html += `
                <div class="insights-section">
                    <div class="insights-title">Suggested Adjustments</div>
                    <div class="insights-pattern">
                        ${suggestedParams.stop_loss ? `<strong>Stop Loss:</strong> ${(suggestedParams.stop_loss * 100).toFixed(2)}%<br>` : ''}
                        ${suggestedParams.take_profit ? `<strong>Take Profit:</strong> ${(suggestedParams.take_profit * 100).toFixed(2)}%<br>` : ''}
                        ${suggestedParams.min_score ? `<strong>Min Signal Score:</strong> ${suggestedParams.min_score}` : ''}
                    </div>
                </div>
            `;
        }

        // If no data yet
        if (totalTrades === 0) {
            html = `
                <div class="insights-section">
                    <div class="insights-title">Learning System</div>
                    <div class="insights-pattern">
                        <strong>Collecting data...</strong> The learning system will analyze your trades
                        and identify patterns as you trade. Check back after a few completed trades.
                    </div>
                </div>
            `;
        }

        // Last updated
        if (data.last_updated) {
            const lastUpdate = new Date(data.last_updated);
            html += `
                <div style="text-align: right; font-size: 9px; color: #444; margin-top: 8px;">
                    Last analyzed: ${lastUpdate.toLocaleString()}
                </div>
            `;
        }

        container.innerHTML = html;
    }

    // ==================== PHASE 5: TRADE STORY CARDS ====================

    /**
     * Renders a trade as a narrative story card with entry/exit context.
     *
     * @param {Object} trade - Trade data with entry/exit info
     * @returns {string} HTML for the trade story
     */
    renderTradeStory(trade) {
        const isWin = (trade.pnl || 0) >= 0;
        const emoji = isWin ? '📈' : '📉';
        const outcomeText = isWin ? 'WINNER' : 'LOSS';
        const outcomeClass = isWin ? 'win' : 'loss';

        // Format P&L
        const pnlStr = `${isWin ? '+' : ''}${this.formatCurrency(trade.pnl || 0)} (${isWin ? '+' : ''}${(trade.pnl_pct || 0).toFixed(2)}%)`;

        // Entry phase
        const entryTime = trade.entry_time ? this.formatTime(trade.entry_time) : '--:--';
        const entryReason = trade.entry_reason || trade.signal_reason || 'Signal triggered';
        const entryRsi = trade.entry_indicators?.rsi;

        // Exit phase
        const exitTime = trade.exit_time ? this.formatTime(trade.exit_time) : '--:--';
        const exitReason = trade.exit_reason || (isWin ? 'Target hit' : 'Stop loss');
        const exitRsi = trade.exit_indicators?.rsi;

        // Duration
        const duration = trade.hold_time_seconds ? this.formatHoldTime(trade.hold_time_seconds) : '--';

        return `
            <div class="trade-story ${isWin ? '' : 'loss'}">
                <div class="trade-story-header">
                    <div class="trade-story-result">
                        <span class="trade-story-emoji">${emoji}</span>
                        <div>
                            <div class="trade-story-outcome ${outcomeClass}">${outcomeText} ${pnlStr}</div>
                            <div class="trade-story-symbol">${trade.symbol?.replace('USD', '/USD') || trade.symbol}</div>
                        </div>
                    </div>
                </div>

                <div class="trade-story-phase">
                    <div class="trade-story-phase-header">
                        <span class="trade-story-phase-label">ENTRY</span>
                        <span class="trade-story-phase-time">${entryTime}</span>
                    </div>
                    <div class="trade-story-phase-reason">"${entryReason}"</div>
                    ${entryRsi !== undefined ? `
                        <div class="trade-story-gauge">
                            <span class="label">RSI</span>
                            <div class="track">
                                <div class="fill" style="width: ${entryRsi}%"></div>
                            </div>
                            <span class="value">${entryRsi.toFixed(0)}</span>
                        </div>
                    ` : ''}
                </div>

                <div class="trade-story-phase">
                    <div class="trade-story-phase-header">
                        <span class="trade-story-phase-label" style="color: ${isWin ? '#00ff88' : '#ff4444'}">EXIT</span>
                        <span class="trade-story-phase-time">${exitTime}</span>
                    </div>
                    <div class="trade-story-phase-reason">"${exitReason}"</div>
                    ${exitRsi !== undefined ? `
                        <div class="trade-story-gauge">
                            <span class="label">RSI</span>
                            <div class="track">
                                <div class="fill" style="width: ${exitRsi}%"></div>
                            </div>
                            <span class="value">${exitRsi.toFixed(0)}</span>
                        </div>
                    ` : ''}
                </div>

                <div class="trade-story-meta">
                    <span>Duration: <span>${duration}</span></span>
                    <span>Strategy: <span>${trade.strategy || 'Scalping'}</span></span>
                </div>
            </div>
        `;
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
