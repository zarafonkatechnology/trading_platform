// src/web/js/dashboard.js
/**
 * Trading Dashboard - Main Logic
 */

class TradingDashboard {
    constructor() {
        this.api = new TradingAPI();
        this.ws = new TradingWebSocket();
        this.charts = new ChartManager();
        this.prices = {};
        this.signals = [];
        this.positions = [];
        this.interval = null;
        this.refreshInterval = 5000; // 5 seconds
        // Bind methods
        this.closePosition = this.closePosition.bind(this);
        this.loadPositions = this.loadPositions.bind(this);
        this.init();
    }
    
    async init() {
        console.log('🚀 Initializing Trading Dashboard...');
        
        // Setup WebSocket
        this.setupWebSocket();
        
        // Load initial data
        await this.loadAllData();
        
        // Setup event listeners
        this.setupEventListeners();
        
        // Start auto-refresh
        this.startAutoRefresh();
        
        // Start clock
        this.startClock();
        
        console.log('✅ Dashboard ready');
    }
    
    setupWebSocket() {
        this.ws.onMessage((data) => {
            if (data.prices) {
                this.updatePrices(data.prices);
            }
            if (data.signals) {
                this.updateSignals(data.signals);
            }
        });
        
        this.ws.connect();
    }
    
    async loadAllData() {
        try {
            // Load prices
            const pricesData = await this.api.getPrices();
            if (pricesData.success) {
                this.updatePrices(pricesData.data.indices);
                this.updatePrices(pricesData.data.forex);
            }
            
            // Load status
            const statusData = await this.api.getStatus();
            if (statusData.success) {
                this.updateStatus(statusData.data);
            }
            
            // Load signals
            const signalsData = await this.api.getSignals();
            if (signalsData.success) {
                this.updateSignals(signalsData.signals || []);
            }
            
        } catch (error) {
            console.error('Error loading data:', error);
        }
    }
    
    updatePrices(prices) {
        if (!prices) return;
        
        // Update price grid
        const grid = document.getElementById('priceGrid');
        let html = '';
        
        for (const [symbol, price] of Object.entries(prices)) {
            if (typeof price !== 'number' || price <= 0) continue;
            
            const change = (Math.random() * 2 - 1) * 0.5; // Simulated change
            const changeClass = change >= 0 ? 'up' : 'down';
            const changeSymbol = change >= 0 ? '▲' : '▼';
            
            html += `
                <div class="price-card" data-symbol="${symbol}">
                    <span class="symbol">${symbol}</span>
                    <span class="type">${this.getSymbolType(symbol)}</span>
                    <div class="price">${price.toFixed(2)}</div>
                    <div class="change ${changeClass}">${changeSymbol} ${Math.abs(change).toFixed(2)}%</div>
                </div>
            `;
        }
        
        grid.innerHTML = html;
        
        // Update stats
        this.updateStats(prices);
    }
    
    getSymbolType(symbol) {
        if (['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD'].includes(symbol)) {
            return 'Forex';
        }
        if (['GOLD', 'SILVER'].includes(symbol)) {
            return 'Metal';
        }
        if (['BRENT_OIL', 'CrudeOIL'].includes(symbol)) {
            return 'Energy';
        }
        if (symbol.startsWith('#')) {
            return 'Index';
        }
        return 'Other';
    }
    
    updateStats(prices) {
        fetch('/api/v1/dashboard/data')
        .then(response => response.json())
        .then(data => {
            if (data && data.data) {
                const account = data.data;
                document.getElementById('balance').textContent = `$${account.balance?.toFixed(2) || '0.00'}`;
                document.getElementById('equity').textContent = `$${account.equity?.toFixed(2) || '0.00'}`;
                const pnl = (account.equity || 0) - (account.balance || 0);
                document.getElementById('pnl').textContent = `$${pnl.toFixed(2)}`;
            }
        })
        .catch(error => {
            console.error('Error fetching account data:', error);
        });
    
                const values = Object.values(prices).filter(v => typeof v === 'number' && v > 0);
        // const count = values.length;
        // const total = values.reduce((a, b) => a + b, 0);
        // const avg = count > 0 ? total / count : 0;
        
        // document.getElementById('balance').textContent = `$${(total / 10).toFixed(2)}`;
        // document.getElementById('equity').textContent = `$${(total / 10 * 1.05).toFixed(2)}`;
        // document.getElementById('pnl').textContent = `$${(total / 100).toFixed(2)}`;
        // document.getElementById('winRate').textContent = `${(Math.random() * 30 + 40).toFixed(1)}%`;
        // document.getElementById('openPositions').textContent = Math.floor(Math.random() * 5);
        // document.getElementById('aiSignals').textContent = Math.floor(Math.random() * 3);
    }
    
    updateStatus(status) {
        if (status.indices) {
            const indicesStatus = status.indices.status || {};
            document.getElementById('positionCount').textContent = indicesStatus.active_positions || 0;
        }
    }
    
    updateSignals(signals) {
        const feed = document.getElementById('signalFeed');
        
        if (!signals || signals.length === 0) {
            feed.innerHTML = `
                <div class="signal-placeholder">
                    <i class="fas fa-robot"></i>
                    <p>No active signals</p>
                </div>
            `;
            return;
        }
        
        let html = '';
        for (const signal of signals) {
            const type = signal.type || 'BUY';
            const typeClass = type.toLowerCase();
            const confidence = signal.confidence || 50;
            const confClass = confidence >= 70 ? 'high' : confidence >= 50 ? 'medium' : 'low';
            
            html += `
                <div class="signal-item ${typeClass}">
                    <div class="signal-icon ${typeClass}">
                        <i class="fas fa-${type === 'BUY' ? 'arrow-up' : 'arrow-down'}"></i>
                    </div>
                    <div class="signal-info">
                        <div class="signal-symbol">${signal.symbol || 'Unknown'}</div>
                        <div class="signal-detail">${type} • ${signal.reasoning || 'AI Signal'}</div>
                    </div>
                    <div class="signal-confidence ${confClass}">${confidence}%</div>
                </div>
            `;
        }
        
        feed.innerHTML = html;
        document.getElementById('signalBadge').textContent = `${signals.length} Active`;
        document.getElementById('signalCount').textContent = signals.length;
    }
    async loadAllData() {
        try {
            // Load prices
            const pricesData = await this.api.getPrices();
            console.log('Prices data:', pricesData); // Debug log
            
            if (pricesData && pricesData.success && pricesData.data) {
                // Combine indices and forex prices
                const allPrices = {
                    ...(pricesData.data.indices || {}),
                    ...(pricesData.data.forex || {})
                };
                
                if (Object.keys(allPrices).length > 0) {
                    this.updatePrices(allPrices);
                } else {
                    console.warn('No prices received from API');
                    this.showError('No price data available');
                }
            } else {
                console.warn('No price data in response');
                this.showError('Failed to load prices');
            }
            
            // Load status
            const statusData = await this.api.getStatus();
            if (statusData && statusData.success) {
                this.updateStatus(statusData.data);
            }
            
            // Load signals
            const signalsData = await this.api.getSignals();
            console.log('Signals data:', signalsData); // Debug log
            
            if (signalsData && signalsData.success) {
                this.updateSignals(signalsData.signals || []);
            } else {
                // Use mock signals if API fails
                this.updateSignals([
                    { symbol: 'EURUSD', type: 'BUY', confidence: 78, reasoning: 'AI Signal' },
                    { symbol: 'GOLD', type: 'SELL', confidence: 65, reasoning: 'AI Signal' }
                ]);
            }
            
        } catch (error) {
            console.error('Error loading data:', error);
            this.showError('Failed to load data');
            
            // Show mock data for testing
            this.showMockData();
        }
    }
    
    showMockData() {
        // Show mock prices for testing
        const mockPrices = {
            'EURUSD': 1.0945,
            'GBPUSD': 1.2680,
            'USDJPY': 162.426,
            'GOLD': 4010.20,
            'SILVER': 55.90,
            '#NASDAQ100': 28952.62,
            '#S&P500': 7521.74,
            '#DJ30': 52536.00
        };
        this.updatePrices(mockPrices);
        
        // Show mock signals
        this.updateSignals([
            { symbol: 'EURUSD', type: 'BUY', confidence: 78, reasoning: 'Mock AI Signal' },
            { symbol: 'GOLD', type: 'SELL', confidence: 65, reasoning: 'Mock AI Signal' }
        ]);
    }
    
    showError(message) {
        const grid = document.getElementById('priceGrid');
        grid.innerHTML = `
            <div style="grid-column: 1/-1; text-align: center; padding: 40px; color: #ef4444;">
                <i class="fas fa-exclamation-circle" style="font-size: 32px; display: block; margin-bottom: 12px;"></i>
                <p>${message}</p>
                <button onclick="location.reload()" style="margin-top: 12px; padding: 8px 24px; background: #3b82f6; border: none; border-radius: 8px; color: white; cursor: pointer;">
                    Refresh
                </button>
            </div>
        `;
    }
    
    
    updatePrices(prices) {
        if (!prices || Object.keys(prices).length === 0) {
            console.warn('No prices to display');
            return;
        }
        
        const grid = document.getElementById('priceGrid');
        let html = '';
        let count = 0;
        
        // Filter out invalid prices
        const validPrices = Object.entries(prices)
            .filter(([symbol, price]) => typeof price === 'number' && price > 0)
            .slice(0, 30); // Limit to 30 symbols
        
        if (validPrices.length === 0) {
            grid.innerHTML = `
                <div style="grid-column: 1/-1; text-align: center; padding: 40px; color: #94a3b8;">
                    <i class="fas fa-database" style="font-size: 32px; display: block; margin-bottom: 12px;"></i>
                    <p>No price data available</p>
                </div>
            `;
            return;
        }
        
        for (const [symbol, price] of validPrices) {
            count++;
            const change = (Math.random() * 2 - 1) * 0.5;
            const changeClass = change >= 0 ? 'up' : 'down';
            const changeSymbol = change >= 0 ? '▲' : '▼';
            const type = this.getSymbolType(symbol);
            
            html += `
                <div class="price-card fade-in" data-symbol="${symbol}" style="animation-delay: ${count * 0.05}s">
                    <span class="symbol">${symbol}</span>
                    <span class="type">${type}</span>
                    <div class="price">${typeof price === 'number' ? price.toFixed(2) : price}</div>
                    <div class="change ${changeClass}">${changeSymbol} ${Math.abs(change).toFixed(2)}%</div>
                </div>
            `;
        }
        
        grid.innerHTML = html;
        
        // Update stats with first few prices
        this.updateStats(prices);
    }
    setupEventListeners() {
        // Refresh button
        document.getElementById('refreshBtn').addEventListener('click', () => {
            const btn = document.getElementById('refreshBtn');
            btn.classList.add('spinning');
            this.loadAllData().finally(() => {
                setTimeout(() => btn.classList.remove('spinning'), 1000);
            });
        });
        
        // Search
        document.getElementById('searchInput').addEventListener('input', (e) => {
            this.filterPrices(e.target.value);
        });
        
        // Filter buttons
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.filterPrices(null, btn.dataset.filter);
            });
        });
        
        // Time buttons
        document.querySelectorAll('.time-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.time-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                // Update chart
                this.charts.updatePeriod(btn.dataset.period);
            });
        });
        
        // Navigation
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
                item.classList.add('active');
                // Page navigation logic here
            });
        });
    }
    
    filterPrices(search, filter) {
        const cards = document.querySelectorAll('.price-card');
        
        cards.forEach(card => {
            const symbol = card.dataset.symbol || '';
            const type = card.querySelector('.type')?.textContent || '';
            
            let show = true;
            
            if (search) {
                show = symbol.toLowerCase().includes(search.toLowerCase());
            }
            
            if (filter && filter !== 'all') {
                const typeLower = type.toLowerCase();
                if (filter === 'forex' && typeLower !== 'forex') show = false;
                if (filter === 'indices' && typeLower !== 'index') show = false;
                if (filter === 'metals' && typeLower !== 'metal') show = false;
                if (filter === 'energy' && typeLower !== 'energy') show = false;
            }
            
            card.style.display = show ? 'block' : 'none';
        });
    }
    
    startAutoRefresh() {
        this.interval = setInterval(() => {
            this.loadAllData();
        }, this.refreshInterval);
    }
    
    startClock() {
        const updateClock = () => {
            const now = new Date();
            document.getElementById('timeDisplay').textContent = now.toLocaleTimeString();
        };
        updateClock();
        setInterval(updateClock, 1000);
    }
    
    destroy() {
        if (this.interval) {
            clearInterval(this.interval);
        }
        if (this.ws) {
            this.ws.disconnect();
        }
    }
    // src/web/js/dashboard.js - Add position tracking

// Add to TradingDashboard class

async loadPositions() {
    try {
        const response = await fetch('/api/v1/trades/positions');
        const data = await response.json();
        
        if (data && data.success) {
            this.updatePositions(data.positions || []);
        } else {
            console.warn('No positions data:', data);
            this.updatePositions([]);
        }
    } catch (error) {
        console.error('Error loading positions:', error);
        this.updatePositions([]);
    }
}

updatePositions(positions) {
    const container = document.getElementById('positionsList');
    const badge = document.getElementById('positionBadge');
    
    if (!positions || positions.length === 0) {
        container.innerHTML = `
            <div class="position-placeholder">
                <i class="fas fa-briefcase"></i>
                <p>No open positions</p>
            </div>
        `;
        if (badge) badge.textContent = '0';
        return;
    }
    
    let html = '';
    let totalPnL = 0;
    
    for (const pos of positions) {
        const pnl = pos.pnl || 0;
        totalPnL += pnl;
        const pnlClass = pnl >= 0 ? 'positive' : 'negative';
        const typeClass = pos.type?.toLowerCase() || 'unknown';
        
        html += `
            <div class="position-item fade-in" style="animation-delay: ${positions.indexOf(pos) * 0.1}s">
                <div class="position-info">
                    <span class="position-symbol">${pos.symbol}</span>
                    <span class="position-type ${typeClass}">${pos.type || 'UNKNOWN'}</span>
                </div>
                <div class="position-details">
                    <span class="position-volume">${pos.volume || 0} lots</span>
                    <span class="position-price">@ ${pos.entry_price?.toFixed(2) || '0.00'}</span>
                </div>
                <div class="position-pnl ${pnlClass}">
                    ${pnl >= 0 ? '+' : ''}$${pnl.toFixed(2)}
                </div>
                <button class="position-close" onclick="closePosition('${pos.symbol}')">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
    }
    
    container.innerHTML = html;
    if (badge) badge.textContent = positions.length;
    
    // Update total positions in stats
    document.getElementById('openPositions').textContent = positions.length;
}
async closePosition(symbol) {
        if (!confirm(`Close position for ${symbol}?`)) return;
        
        try {
            const response = await fetch(`/api/v1/trades/close/${symbol}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            const data = await response.json();
            
            if (data.success) {
                showToast(`Position ${symbol} closed successfully!`, 'success');
                // Reload positions
                await this.loadPositions();
                // Also reload prices/stats
                await this.loadAllData();
            } else {
                showToast(`Failed to close position: ${data.error}`, 'error');
            }
        } catch (error) {
            console.error('Error closing position:', error);
            showToast(`Error closing position: ${error.message}`, 'error');
        }
    }
}

// Global function for closing positions
window.closePosition = async function(symbol) {
    if (!confirm(`Close position for ${symbol}?`)) return;
    
    try {
        const response = await fetch(`/api/v1/trades/close/${symbol}`, {
            method: 'POST'
        });
        const data = await response.json();
        
        if (data.success) {
            alert(`Position ${symbol} closed successfully!`);
            window.dashboard.loadPositions();
            window.dashboard.loadAllData();
        } else {
            alert(`Failed to close position: ${data.error}`);
        }
    } catch (error) {
        alert(`Error closing position: ${error.message}`);
    }
};




// ===== API Class =====
// src/web/js/dashboard.js - Fixed API calls

class TradingAPI {
    constructor(baseUrl = 'http://localhost:8000/api/v1') {
        this.baseUrl = baseUrl;
    }
    
    async request(endpoint) {
        try {
            const response = await fetch(`${this.baseUrl}${endpoint}`, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                },
            });
            
            if (!response.ok) {
                console.warn(`API error: ${response.status} for ${endpoint}`);
                return { success: false, error: `HTTP ${response.status}` };
            }
            
            const data = await response.json();
            return data;
        } catch (error) {
            console.error(`API request error: ${error}`);
            return { success: false, error: error.message };
        }
    }
    
    async getPrices() {
        const data = await this.request('/controllers/all/prices');
        return data;
    }
    
    async getStatus() {
        const data = await this.request('/controllers/all/status');
        return data;
    }
    
    async getSignals() {
        const data = await this.request('/signals');
        return data;
    }
    
    async getSymbols() {
        return this.request('/trades/symbols');
    }
    
    async executeTrade(symbol, type, volume) {
        try {
            const response = await fetch(`${this.baseUrl}/trades/execute`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({ symbol, order_type: type, volume })
            });
            return response.json();
        } catch (error) {
            return { success: false, error: error.message };
        }
    }
    
}
// ===== WebSocket Class =====
class TradingWebSocket {
    constructor(url = 'ws://localhost:8000/ws/prices') {
        this.url = url;
        this.ws = null;
        this.messageHandler = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
    }
    
    connect() {
        try {
            this.ws = new WebSocket(this.url);
            
            this.ws.onopen = () => {
                console.log('✅ WebSocket connected');
                this.reconnectAttempts = 0;
            };
            
            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    if (this.messageHandler) {
                        this.messageHandler(data);
                    }
                } catch (e) {
                    console.error('WebSocket message error:', e);
                }
            };
            
            this.ws.onclose = () => {
                console.log('WebSocket disconnected');
                this.reconnect();
            };
            
            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };
            
        } catch (error) {
            console.error('WebSocket connection error:', error);
        }
    }
    
    reconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`Reconnecting... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
            setTimeout(() => this.connect(), 3000);
        }
    }
    
    onMessage(handler) {
        this.messageHandler = handler;
    }
    
    disconnect() {
        if (this.ws) {
            this.ws.close();
        }
    }
}

// ===== Chart Manager =====
class ChartManager {
    constructor() {
        this.chart = null;
        this.currentPeriod = '1H';
        this.init();
    }
    
    init() {
        const ctx = document.getElementById('marketChart').getContext('2d');
        
        this.chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: this.generateLabels(50),
                datasets: [{
                    label: 'Price',
                    data: this.generateData(50),
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 0
                }, {
                    label: 'MA 20',
                    data: this.generateData(50, 0.003),
                    borderColor: '#8b5cf6',
                    borderDash: [5, 5],
                    fill: false,
                    tension: 0.4,
                    pointRadius: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        backgroundColor: 'rgba(17, 24, 39, 0.9)',
                        borderColor: 'rgba(255, 255, 255, 0.1)',
                        borderWidth: 1,
                        titleColor: '#f1f5f9',
                        bodyColor: '#94a3b8'
                    }
                },
                scales: {
                    x: {
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        ticks: { color: '#64748b' }
                    },
                    y: {
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        ticks: { color: '#64748b' }
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                }
            }
        });
        
        // Simulate live updates
        setInterval(() => this.updateLive(), 2000);
    }
    
    generateLabels(count) {
        const labels = [];
        for (let i = count; i > 0; i--) {
            labels.push(`${i}m`);
        }
        return labels;
    }
    
    generateData(count, volatility = 0.005) {
        const data = [];
        let value = 100;
        for (let i = 0; i < count; i++) {
            value += (Math.random() - 0.5) * value * volatility;
            data.push(value);
        }
        return data;
    }
    
    updateLive() {
        if (!this.chart) return;
        
        const lastValue = this.chart.data.datasets[0].data[this.chart.data.datasets[0].data.length - 1];
        const change = (Math.random() - 0.5) * lastValue * 0.002;
        const newValue = lastValue + change;
        
        // Update main data
        this.chart.data.datasets[0].data.push(newValue);
        this.chart.data.datasets[0].data.shift();
        
        // Update MA
        const maData = this.chart.data.datasets[1].data;
        const avg = maData.slice(-20).reduce((a, b) => a + b, 0) / maData.length;
        maData.push(avg + (Math.random() - 0.5) * 0.1);
        maData.shift();
        
        // Update labels
        const label = `${this.chart.data.labels.length}m`;
        this.chart.data.labels.push(label);
        this.chart.data.labels.shift();
        
        this.chart.update('none');
    }
    
    updatePeriod(period) {
        this.currentPeriod = period;
        // Update chart data based on period
        console.log(`Chart period changed to: ${period}`);
    }
}


// ===== Initialize Dashboard =====
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new TradingDashboard();
});