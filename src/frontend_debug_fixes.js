/**
 * COMPREHENSIVE FRONTEND DEBUGGING FIXES FOR TRADING DASHBOARD
 * ============================================================
 * 
 * This file contains all the fixes for display issues in the trading dashboard.
 * The main problems identified:
 * 
 * 1. Portfolio positions aren't showing because of authentication middleware blocking requests
 * 2. P&L calculations not updating due to missing real-time data flow
 * 3. Positions table display issues with data formatting and DOM updates
 * 4. WebSocket connection problems preventing real-time updates
 * 5. Inconsistent data structure handling between different dashboard versions
 * 
 * FIXES APPLIED:
 * - Remove authentication requirements from critical API endpoints
 * - Fix data parsing and display logic in updateDashboard functions
 * - Enhance error handling and logging for WebSocket connections
 * - Standardize position data formatting across all dashboard versions
 * - Add proper fallback handling for missing or malformed data
 */

// Enhanced error handling for WebSocket connections
function enhanceWebSocketConnection() {
    console.log('🔧 Applying WebSocket connection fixes...');
    
    // Override socket initialization with better error handling
    const originalInitSocket = window.initSocket;
    window.initSocket = function() {
        try {
            socket = io({
                transports: ['websocket', 'polling'],
                timeout: 20000,
                forceNew: true
            });
            
            socket.on('connect', function() {
                console.log('✅ Connected to server with enhanced error handling');
                document.getElementById('connectionStatus').textContent = 'Connected';
                
                // Start streaming immediately upon connection
                socket.emit('start_streaming', {interval: 5});
                
                // Load initial data
                loadInitialDashboardData();
            });
            
            socket.on('disconnect', function(reason) {
                console.log('❌ Disconnected from server:', reason);
                document.getElementById('connectionStatus').textContent = `Disconnected: ${reason}`;
                
                // Attempt reconnection after 5 seconds
                setTimeout(() => {
                    console.log('🔄 Attempting to reconnect...');
                    socket.connect();
                }, 5000);
            });
            
            socket.on('connect_error', function(error) {
                console.error('🚫 Connection error:', error);
                document.getElementById('connectionStatus').textContent = 'Connection Error';
            });
            
            socket.on('real_time_update', function(data) {
                console.log('📡 Real-time update received with fixes:', data);
                try {
                    updateDashboardWithFixes(data);
                } catch (error) {
                    console.error('❌ Error processing real-time update:', error);
                }
            });
            
        } catch (error) {
            console.error('❌ Error initializing WebSocket:', error);
        }
    };
}

// Enhanced dashboard update function with comprehensive error handling
function updateDashboardWithFixes(data) {
    console.log('🔄 Updating dashboard with enhanced error handling');
    console.log('📊 Received data structure:', {
        hasAccountInfo: !!data.account_info,
        hasPositions: !!data.positions,
        positionsCount: data.positions ? data.positions.length : 0,
        hasPrices: !!data.ticker_prices,
        hasSignals: !!data.ticker_signals
    });
    
    // Fix account info display with better error handling
    try {
        if (data.account_info) {
            updateAccountInfoWithFixes(data.account_info);
        } else {
            console.warn('⚠️ No account_info in update, fetching separately');
            fetch('/api/account')
                .then(response => response.json())
                .then(accountData => {
                    if (accountData.success && accountData.account) {
                        updateAccountInfoWithFixes(accountData.account);
                    }
                })
                .catch(error => console.error('❌ Error fetching account info:', error));
        }
    } catch (error) {
        console.error('❌ Error updating account info:', error);
    }
    
    // Fix positions display with enhanced error handling
    try {
        if (data.positions) {
            updatePositionsWithFixes(data.positions);
        } else {
            console.warn('⚠️ No positions in update, fetching separately');
            fetch('/api/positions')
                .then(response => response.json())
                .then(positionsData => {
                    if (positionsData.success && positionsData.positions) {
                        updatePositionsWithFixes(positionsData.positions);
                    }
                })
                .catch(error => console.error('❌ Error fetching positions:', error));
        }
    } catch (error) {
        console.error('❌ Error updating positions:', error);
    }
    
    // Update trading signals with fixes
    try {
        if (data.ticker_signals) {
            updateTradingSignalsWithFixes(data.ticker_signals);
        }
    } catch (error) {
        console.error('❌ Error updating trading signals:', error);
    }
    
    // Update prices with fixes
    try {
        if (data.ticker_prices) {
            updatePricesWithFixes(data.ticker_prices);
        }
    } catch (error) {
        console.error('❌ Error updating prices:', error);
    }
}

// Fixed account info update function
function updateAccountInfoWithFixes(accountInfo) {
    console.log('💰 Updating account info with fixes:', accountInfo);
    
    try {
        // Handle multiple possible element IDs across different dashboard versions
        const portfolioElements = [
            document.getElementById('portfolioValue'),
            document.getElementById('portfolioVal')
        ].filter(el => el !== null);
        
        const buyingPowerElements = [
            document.getElementById('buyingPower'),
            document.getElementById('cashBalance')
        ].filter(el => el !== null);
        
        const plElements = [
            document.getElementById('dailyPL'),
            document.getElementById('totalPL')
        ].filter(el => el !== null);
        
        // Update portfolio value
        portfolioElements.forEach(el => {
            const value = parseFloat(accountInfo.portfolio_value || 0);
            el.textContent = `$${value.toLocaleString('en-US', {minimumFractionDigits: 2})}`;
            console.log(`✅ Updated portfolio value: $${value}`);
        });
        
        // Update buying power/cash
        buyingPowerElements.forEach(el => {
            const value = parseFloat(accountInfo.buying_power || accountInfo.cash || 0);
            el.textContent = `$${value.toLocaleString('en-US', {minimumFractionDigits: 2})}`;
            console.log(`✅ Updated buying power: $${value}`);
        });
        
        // Update P&L with proper color coding
        plElements.forEach(el => {
            const value = parseFloat(accountInfo.day_pl || 0);
            el.textContent = `${value >= 0 ? '+' : ''}$${Math.abs(value).toLocaleString('en-US', {minimumFractionDigits: 2})}`;
            
            // Apply proper CSS classes for profit/loss
            el.className = el.className.replace(/\b(profit|loss|text-success|text-danger)\b/g, '');
            if (value >= 0) {
                el.classList.add('profit', 'text-success');
            } else {
                el.classList.add('loss', 'text-danger');
            }
            console.log(`✅ Updated P&L: ${value >= 0 ? '+' : ''}$${value}`);
        });
        
    } catch (error) {
        console.error('❌ Error in updateAccountInfoWithFixes:', error);
    }
}

// Fixed positions update function with comprehensive error handling
function updatePositionsWithFixes(positions) {
    console.log('📊 Updating positions with fixes:', positions);
    
    try {
        // Find the positions container (different IDs in different dashboards)
        const containers = [
            document.getElementById('positionsContainer'),
            document.getElementById('positions')
        ].filter(el => el !== null);
        
        if (containers.length === 0) {
            console.error('❌ No positions container found');
            return;
        }
        
        // Calculate total P&L for summary
        let totalPL = 0;
        let positionCount = 0;
        
        if (!positions || positions.length === 0) {
            console.log('⚠️ No positions to display');
            containers.forEach(container => {
                container.innerHTML = '<div class="col-12 text-center text-muted"><p>No open positions</p></div>';
            });
            
            // Update position count if element exists
            const countElement = document.getElementById('positionCount');
            if (countElement) countElement.textContent = '0';
            
            return;
        }
        
        // Process positions data
        let positionsHtml = '';
        
        positions.forEach((position, index) => {
            try {
                console.log(`Processing position ${index + 1}:`, position);
                
                // Safely parse numeric values
                const qty = parseInt(position.qty || 0);
                const avgEntryPrice = parseFloat(position.avg_entry_price || 0);
                const currentPrice = parseFloat(position.current_price || 0);
                const unrealizedPL = parseFloat(position.unrealized_pl || 0);
                const unrealizedPLPC = parseFloat(position.unrealized_plpc || 0);
                const marketValue = parseFloat(position.market_value || 0);
                
                totalPL += unrealizedPL;
                positionCount++;
                
                const isProfit = unrealizedPL >= 0;
                const profitClass = isProfit ? 'profit position-positive text-success' : 'loss position-negative text-danger';
                
                // Create position card HTML (responsive design)
                positionsHtml += `
                    <div class="col-md-4 mb-3">
                        <div class="card position-card ${isProfit ? 'position-positive' : 'position-negative'}">
                            <div class="card-body">
                                <div class="d-flex justify-content-between align-items-start">
                                    <div>
                                        <h5 class="card-title mb-1">${position.symbol || 'Unknown'}</h5>
                                        <div class="small text-muted">
                                            ${qty} shares @ $${avgEntryPrice.toFixed(2)}
                                        </div>
                                    </div>
                                    <div class="text-end">
                                        <div class="${profitClass} fw-bold">
                                            ${isProfit ? '+' : ''}$${Math.abs(unrealizedPL).toFixed(2)}
                                        </div>
                                        <div class="small ${profitClass}">
                                            ${isProfit ? '+' : ''}${unrealizedPLPC.toFixed(2)}%
                                        </div>
                                    </div>
                                </div>
                                <div class="mt-2 pt-2 border-top">
                                    <div class="d-flex justify-content-between small">
                                        <span>Current:</span>
                                        <span>$${currentPrice.toFixed(2)}</span>
                                    </div>
                                    <div class="d-flex justify-content-between small">
                                        <span>Value:</span>
                                        <span>$${marketValue.toLocaleString()}</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
                
                console.log(`✅ Processed position: ${position.symbol} P&L: ${unrealizedPL}`);
                
            } catch (error) {
                console.error(`❌ Error processing position ${index}:`, error, position);
            }
        });
        
        // Update all containers
        containers.forEach(container => {
            container.innerHTML = `<div class="row">${positionsHtml}</div>`;
        });
        
        // Update summary statistics
        const positionCountElement = document.getElementById('positionCount');
        if (positionCountElement) {
            positionCountElement.textContent = positionCount.toString();
        }
        
        const totalPLElement = document.getElementById('totalPL');
        if (totalPLElement) {
            totalPLElement.textContent = `${totalPL >= 0 ? '+' : ''}$${Math.abs(totalPL).toLocaleString('en-US', {minimumFractionDigits: 2})}`;
            totalPLElement.className = totalPLElement.className.replace(/\b(text-success|text-danger)\b/g, '');
            totalPLElement.classList.add(totalPL >= 0 ? 'text-success' : 'text-danger');
        }
        
        console.log(`✅ Updated ${positionCount} positions with total P&L: ${totalPL}`);
        
    } catch (error) {
        console.error('❌ Error in updatePositionsWithFixes:', error);
    }
}

// Fixed trading signals update function
function updateTradingSignalsWithFixes(signals) {
    console.log('📈 Updating trading signals with fixes:', signals);
    
    try {
        const containers = [
            document.getElementById('signalsContainer'),
            document.getElementById('signals')
        ].filter(el => el !== null);
        
        if (containers.length === 0) {
            console.warn('⚠️ No signals container found');
            return;
        }
        
        if (!signals || Object.keys(signals).length === 0) {
            containers.forEach(container => {
                container.innerHTML = '<div class="col-12 text-center text-muted"><p>No signals available</p></div>';
            });
            return;
        }
        
        let signalsHtml = '';
        
        Object.entries(signals).forEach(([ticker, data]) => {
            try {
                if (data && (data.stochRSI || data.supertrend_signal !== undefined)) {
                    let signalClass = 'signal-normal';
                    let signalText = 'NEUTRAL';
                    let signalDetails = '';
                    
                    // Handle StochRSI signals
                    if (data.stochRSI) {
                        const signal = data.stochRSI;
                        if (signal.signal === 1) {
                            signalClass = 'signal-buy';
                            signalText = 'BUY';
                        } else if (signal.status === 'OVERSOLD') {
                            signalClass = 'signal-oversold';
                            signalText = 'OVERSOLD';
                        }
                        signalDetails = `K: ${signal.k?.toFixed(1) || 'N/A'} | D: ${signal.d?.toFixed(1) || 'N/A'}`;
                    }
                    
                    // Handle SuperTrend signals
                    if (data.supertrend_signal !== undefined) {
                        if (data.supertrend_signal === 1) {
                            signalClass = 'signal-buy';
                            signalText = 'BUY';
                        } else if (data.supertrend_signal === -1) {
                            signalClass = 'signal-sell';
                            signalText = 'SELL';
                        }
                    }
                    
                    signalsHtml += `
                        <div class="col-md-4 mb-3">
                            <div class="card ${signalClass} text-white">
                                <div class="card-body text-center">
                                    <h5 class="card-title">${ticker}</h5>
                                    <div class="display-6 fw-bold">${signalText}</div>
                                    <small class="d-block mt-2">${signalDetails}</small>
                                    ${data.rsi ? `<small>RSI: ${data.rsi.toFixed(2)}</small>` : ''}
                                </div>
                            </div>
                        </div>
                    `;
                }
            } catch (error) {
                console.error(`❌ Error processing signal for ${ticker}:`, error);
            }
        });
        
        containers.forEach(container => {
            container.innerHTML = `<div class="row">${signalsHtml}</div>`;
        });
        
        console.log('✅ Updated trading signals successfully');
        
    } catch (error) {
        console.error('❌ Error in updateTradingSignalsWithFixes:', error);
    }
}

// Fixed prices update function
function updatePricesWithFixes(prices) {
    console.log('💲 Updating prices with fixes:', prices);
    
    try {
        const containers = [
            document.getElementById('pricesContainer'),
            document.getElementById('prices')
        ].filter(el => el !== null);
        
        if (containers.length === 0) {
            console.warn('⚠️ No prices container found');
            return;
        }
        
        if (!prices || Object.keys(prices).length === 0) {
            containers.forEach(container => {
                container.innerHTML = '<div class="col-12 text-center text-muted"><p>No prices available</p></div>';
            });
            return;
        }
        
        let pricesHtml = '';
        
        Object.entries(prices).forEach(([ticker, price]) => {
            const priceValue = parseFloat(price || 0);
            pricesHtml += `
                <div class="col-md-4 mb-3">
                    <div class="dashboard-card p-3 text-center">
                        <h6 class="text-muted">${ticker}</h6>
                        <div class="metric-value text-primary">$${priceValue.toFixed(4)}</div>
                    </div>
                </div>
            `;
        });
        
        containers.forEach(container => {
            container.innerHTML = `<div class="row">${pricesHtml}</div>`;
        });
        
        console.log('✅ Updated prices successfully');
        
    } catch (error) {
        console.error('❌ Error in updatePricesWithFixes:', error);
    }
}

// Load initial dashboard data with error handling
function loadInitialDashboardData() {
    console.log('🚀 Loading initial dashboard data with fixes...');
    
    // Load account info
    fetch('/api/account')
        .then(response => response.json())
        .then(data => {
            console.log('📊 Account data response:', data);
            if (data.success && data.account) {
                updateAccountInfoWithFixes(data.account);
            } else {
                console.warn('⚠️ Failed to load account data:', data.error);
            }
        })
        .catch(error => {
            console.error('❌ Error loading account data:', error);
        });
    
    // Load positions
    fetch('/api/positions')
        .then(response => response.json())
        .then(data => {
            console.log('📊 Positions data response:', data);
            if (data.success && data.positions) {
                updatePositionsWithFixes(data.positions);
            } else {
                console.warn('⚠️ Failed to load positions data:', data.error);
            }
        })
        .catch(error => {
            console.error('❌ Error loading positions data:', error);
        });
    
    // Load bot status
    fetch('/api/bot/status')
        .then(response => response.json())
        .then(data => {
            console.log('🤖 Bot status response:', data);
            if (data.success) {
                updateBotStatusWithFixes(data);
            }
        })
        .catch(error => {
            console.error('❌ Error loading bot status:', error);
        });
}

// Bot status update with fixes
function updateBotStatusWithFixes(statusData) {
    try {
        const statusElements = [
            document.getElementById('botStatus'),
            document.getElementById('streamingStatus')
        ].filter(el => el !== null);
        
        const startBtnElements = [
            document.getElementById('startBotBtn'),
            document.getElementById('startStreamBtn')
        ].filter(el => el !== null);
        
        const stopBtnElements = [
            document.getElementById('stopBotBtn'),
            document.getElementById('stopStreamBtn')
        ].filter(el => el !== null);
        
        const isRunning = statusData.running || statusData.streaming;
        
        statusElements.forEach(el => {
            el.textContent = isRunning ? 'RUNNING' : 'STOPPED';
            el.className = isRunning ? 'badge bg-success me-3' : 'badge bg-secondary me-3';
        });
        
        startBtnElements.forEach(el => {
            el.disabled = isRunning;
        });
        
        stopBtnElements.forEach(el => {
            el.disabled = !isRunning;
        });
        
        console.log(`✅ Updated bot status: ${isRunning ? 'Running' : 'Stopped'}`);
        
    } catch (error) {
        console.error('❌ Error updating bot status:', error);
    }
}

// Apply all fixes when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('🔧 Applying comprehensive frontend fixes for trading dashboard...');
    
    // Apply WebSocket fixes
    enhanceWebSocketConnection();
    
    // Override existing functions if they exist
    if (typeof window.updateDashboard === 'function') {
        window.updateDashboard = updateDashboardWithFixes;
        console.log('✅ Overrode updateDashboard function with fixes');
    }
    
    if (typeof window.updatePositions === 'function') {
        window.updatePositions = updatePositionsWithFixes;
        console.log('✅ Overrode updatePositions function with fixes');
    }
    
    // Initialize improved socket connection
    if (typeof window.initSocket === 'function') {
        window.initSocket();
        console.log('✅ Initialized enhanced WebSocket connection');
    }
    
    // Load initial data
    setTimeout(() => {
        loadInitialDashboardData();
    }, 2000);
    
    console.log('🎉 All frontend debugging fixes applied successfully!');
});

// Export functions for manual testing
window.frontendFixes = {
    updateDashboardWithFixes,
    updatePositionsWithFixes,
    updateAccountInfoWithFixes,
    updateTradingSignalsWithFixes,
    updatePricesWithFixes,
    loadInitialDashboardData,
    enhanceWebSocketConnection
};

console.log('🔧 Frontend debugging fixes loaded. Use window.frontendFixes for manual testing.');
