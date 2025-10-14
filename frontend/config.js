// Frontend Configuration for New Flask API

const API_CONFIG = {
    // Base URL for API
    baseURL: window.location.origin,

    // API version
    version: 'v1',

    // Endpoints
    endpoints: {
        // Core API
        status: '/api/v1/status',
        account: '/api/v1/account',
        positions: '/api/v1/positions',
        signals: '/api/v1/signals',
        orders: '/api/v1/orders',
        symbols: '/api/v1/symbols',

        // Trading
        startTrading: '/api/v1/trading/start',
        stopTrading: '/api/v1/trading/stop',
        buy: '/api/v1/trading/buy',
        sell: '/api/v1/trading/sell',
        closePosition: '/api/v1/trading/close',
        closeAll: '/api/v1/trading/close-all',

        // P&L
        currentPnl: '/api/v1/pnl/current',
        pnlHistory: '/api/v1/pnl/history',
        pnlChart: '/api/v1/pnl/chart-data',
        pnlStats: '/api/v1/pnl/statistics',
        pnlExport: '/api/v1/pnl/export'
    },

    // WebSocket configuration
    websocket: {
        enabled: true,
        reconnect: true,
        reconnectDelay: 5000
    },

    // Update intervals (milliseconds)
    updateIntervals: {
        account: 30000,    // 30 seconds
        positions: 5000,   // 5 seconds
        signals: 10000,    // 10 seconds
        pnl: 5000         // 5 seconds
    }
};

// Helper function to build full API URL
function buildApiUrl(endpoint) {
    return `${API_CONFIG.baseURL}${API_CONFIG.endpoints[endpoint]}`;
}

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = API_CONFIG;
}
