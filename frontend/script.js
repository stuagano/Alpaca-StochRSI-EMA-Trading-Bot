// Crypto Trading Dashboard JavaScript
class CryptoDashboard {
    constructor() {
        this.autoRefresh = true;
        this.refreshInterval = null;
        this.lastUpdate = null;
        this.pnlChart = null;

        this.init();
    }

    init() {
        // Initialize dashboard on page load
        this.updateConnectionStatus('connecting');
        this.initializeChart();
        this.loadAllData();
        this.updateChart();
        this.startAutoRefresh();

        // Set up event listeners
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Handle window focus to refresh data
        window.addEventListener('focus', () => {
            this.loadAllData();
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
                            <span>${signal.rsi}</span>
                        </div>
                        <div class="detail">
                            <span>Price:</span>
                            <span>${this.formatCurrency(signal.price)}</span>
                        </div>
                        <div class="detail">
                            <span>Strength:</span>
                            <span class="${strengthClass}">${signal.strength}</span>
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
        tradesArray.slice(-10).reverse().forEach(trade => { // Show last 10 trades, newest first
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
                        label: 'Daily P&L',
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
                            text: 'Daily P&L',
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
