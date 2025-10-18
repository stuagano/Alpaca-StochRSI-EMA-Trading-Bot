// Frontend Configuration for New Flask API

(function initApiConfig(globalThisContext) {
    const GLOBAL = globalThisContext;

    const HTTP_PROTOCOLS = new Set(['http:', 'https:']);

    function normalizeProtocol(value) {
        if (!value) {
            return 'http:';
        }
        return HTTP_PROTOCOLS.has(value) ? value : `${value.endsWith(':') ? value : `${value}:`}`;
    }

    function resolveApiBaseUrl(options = {}) {
        const ctxEnv = options.env || (typeof process !== 'undefined' ? process.env : {});

        const explicitUrl = options.apiBaseUrl
            ?? (GLOBAL && GLOBAL.API_BASE_URL)
            ?? ctxEnv.API_BASE_URL;
        if (explicitUrl) {
            return explicitUrl;
        }

        const defaultPort = options.defaultPort
            ?? (GLOBAL && GLOBAL.API_BASE_PORT)
            ?? ctxEnv.API_BASE_PORT
            ?? '5001';

        const location = options.location
            ?? (GLOBAL && GLOBAL.location)
            ?? null;

        if (location) {
            if (typeof location.origin === 'string' && location.origin) {
                return location.origin;
            }

            const protocol = normalizeProtocol(location.protocol || options.protocol || ctxEnv.API_BASE_PROTOCOL);
            const hostname = location.hostname || location.host || options.hostname || ctxEnv.API_BASE_HOST || 'localhost';
            const locationPort = location.port || '';
            const finalPort = locationPort || (defaultPort && defaultPort !== '' ? defaultPort : '');

            return `${protocol}//${hostname}${finalPort ? `:${finalPort}` : ''}`;
        }

        const protocol = normalizeProtocol(options.protocol || ctxEnv.API_BASE_PROTOCOL || 'http:');
        const hostname = options.hostname || ctxEnv.API_BASE_HOST || 'localhost';

        return `${protocol}//${hostname}:${defaultPort}`;
    }

    const API_CONFIG = {
        // Base URL for API (prefers explicit override, falls back to current origin, then default port 5001)
        baseURL: resolveApiBaseUrl(),

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
        setMultiplier: '/api/v1/trading/set-multiplier',

        // P&L
        currentPnl: '/api/v1/pnl/current',
        pnlHistory: '/api/v1/pnl/history',
        pnlChart: '/api/v1/pnl/chart-data',
        pnlStats: '/api/v1/pnl/statistics',
        pnlExport: '/api/v1/pnl/export',

        // Trade history
        trades: '/api/v1/pnl/trades'
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
        if (!endpoint) {
            throw new Error('Endpoint key or path is required');
        }

        // Absolute URLs can pass straight through
        if (/^https?:\/\//i.test(endpoint)) {
            return endpoint;
        }

        if (API_CONFIG.endpoints && API_CONFIG.endpoints[endpoint]) {
            return `${API_CONFIG.baseURL}${API_CONFIG.endpoints[endpoint]}`;
        }

        if (endpoint.startsWith('/')) {
            return `${API_CONFIG.baseURL}${endpoint}`;
        }

        return `${API_CONFIG.baseURL}/${endpoint}`;
    }

    // Expose helpers globally for browser usage
    GLOBAL.API_CONFIG = API_CONFIG;
    GLOBAL.buildApiUrl = buildApiUrl;
    GLOBAL.resolveApiBaseUrl = resolveApiBaseUrl;

    // Support CommonJS (Node) consumers for testing
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = {
            API_CONFIG,
            buildApiUrl,
            resolveApiBaseUrl
        };
    }
})(typeof window !== 'undefined' ? window : globalThis);
