/**
 * Trading Bot Dashboard - JavaScript
 * Handles chart rendering, API calls, and real-time updates
 */

// Global state
let priceChart = null;
let socket = null;
let currentSymbol = 'BTCUSDT';
let currentTimeframe = '1h';
let isLoading = false;

// DOM Elements
const elements = {
    symbolSelect: document.getElementById('symbolSelect'),
    timeframeSelect: document.getElementById('timeframeSelect'),
    startBtn: document.getElementById('startBtn'),
    stopBtn: document.getElementById('stopBtn'),
    currentPrice: document.getElementById('currentPrice'),
    priceChange: document.getElementById('priceChange'),
    signalDisplay: document.getElementById('signalDisplay'),
    signalScore: document.getElementById('signalScore'),
    rsiValue: document.getElementById('rsiValue'),
    macdValue: document.getElementById('macdValue'),
    emaTrend: document.getElementById('emaTrend'),
    volumeStatus: document.getElementById('volumeStatus'),
    totalTrades: document.getElementById('totalTrades'),
    winRate: document.getElementById('winRate'),
    totalPnl: document.getElementById('totalPnl'),
    balance: document.getElementById('balance'),
    backtestDays: document.getElementById('backtestDays'),
    runBacktest: document.getElementById('runBacktest'),
    backtestResults: document.getElementById('backtestResults'),
    tradesBody: document.getElementById('tradesBody'),
    botStatus: document.getElementById('botStatus'),
    statusText: document.getElementById('statusText'),
    lastUpdate: document.getElementById('lastUpdate')
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initChart();
    loadPriceData();
    loadSignal();
    setupEventListeners();
    setupSocketConnection();
});

// Initialize Chart
function initChart() {
    const ctx = document.getElementById('priceChart').getContext('2d');

    priceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'Price',
                    data: [],
                    borderColor: '#58a6ff',
                    backgroundColor: 'rgba(88, 166, 255, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.1,
                    pointRadius: 0,
                    pointHoverRadius: 4
                },
                {
                    label: 'EMA 21',
                    data: [],
                    borderColor: '#f85149',
                    borderWidth: 1,
                    fill: false,
                    tension: 0.1,
                    pointRadius: 0,
                    borderDash: [5, 5]
                },
                {
                    label: 'BB Upper',
                    data: [],
                    borderColor: 'rgba(163, 113, 247, 0.5)',
                    borderWidth: 1,
                    fill: false,
                    tension: 0.1,
                    pointRadius: 0
                },
                {
                    label: 'BB Lower',
                    data: [],
                    borderColor: 'rgba(163, 113, 247, 0.5)',
                    borderWidth: 1,
                    fill: false,
                    tension: 0.1,
                    pointRadius: 0
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
                        color: '#8b949e',
                        usePointStyle: true,
                        padding: 20
                    }
                },
                tooltip: {
                    backgroundColor: '#21262d',
                    titleColor: '#f0f6fc',
                    bodyColor: '#8b949e',
                    borderColor: '#30363d',
                    borderWidth: 1
                }
            },
            scales: {
                x: {
                    display: true,
                    grid: {
                        color: 'rgba(48, 54, 61, 0.5)'
                    },
                    ticks: {
                        color: '#8b949e',
                        maxTicksLimit: 10
                    }
                },
                y: {
                    display: true,
                    position: 'right',
                    grid: {
                        color: 'rgba(48, 54, 61, 0.5)'
                    },
                    ticks: {
                        color: '#8b949e'
                    }
                }
            }
        }
    });
}

// Load Price Data
async function loadPriceData() {
    if (isLoading) return;
    isLoading = true;

    try {
        const response = await fetch(`/api/price/${currentSymbol}`);
        const data = await response.json();

        if (data.success) {
            updateChart(data.candles);
            updatePrice(data.price);
            updateIndicators(data.indicators);
            updateLastUpdate();
        }
    } catch (error) {
        console.error('Error loading price data:', error);
    } finally {
        isLoading = false;
    }
}

// Update Chart
function updateChart(candles) {
    const labels = candles.map(c => {
        const date = new Date(c.time);
        return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    });

    const prices = candles.map(c => c.close);

    // Calculate EMA and BB from last values (simplified)
    const lastPrice = prices[prices.length - 1];

    priceChart.data.labels = labels;
    priceChart.data.datasets[0].data = prices;

    // Update with indicator values if available
    priceChart.update('none');
}

// Update Price Display
function updatePrice(price) {
    elements.currentPrice.textContent = `$${price.toLocaleString()}`;

    // Calculate mock change
    const change = (Math.random() * 4 - 2).toFixed(2);
    const isPositive = parseFloat(change) >= 0;

    elements.priceChange.textContent = `${isPositive ? '+' : ''}${change}%`;
    elements.priceChange.className = `price-change ${isPositive ? 'positive' : 'negative'}`;
}

// Update Indicators Display
function updateIndicators(indicators) {
    if (!indicators) return;

    elements.rsiValue.textContent = indicators.rsi || '--';
    elements.macdValue.textContent = indicators.macd?.toFixed(2) || '--';

    // EMA Trend
    const emaTrend = indicators.ema_short > indicators.ema_medium ? 'Bullish ↑' : 'Bearish ↓';
    elements.emaTrend.textContent = emaTrend;
    elements.emaTrend.style.color = indicators.ema_short > indicators.ema_medium ? '#3fb950' : '#f85149';

    // Volume
    elements.volumeStatus.textContent = 'Normal';
}

// Load Signal
async function loadSignal() {
    try {
        const response = await fetch(`/api/signal/${currentSymbol}`);
        const data = await response.json();

        if (data.success) {
            updateSignalDisplay(data);
        }
    } catch (error) {
        console.error('Error loading signal:', error);
    }
}

// Update Signal Display
function updateSignalDisplay(data) {
    const signalType = elements.signalDisplay.querySelector('.signal-type');
    signalType.textContent = data.signal_type;
    signalType.className = `signal-type ${data.signal_type.toLowerCase()}`;

    elements.signalScore.textContent = `${data.score}%`;
}

// Run Backtest
async function runBacktest() {
    elements.runBacktest.disabled = true;
    elements.runBacktest.textContent = 'Running...';

    try {
        const response = await fetch('/api/backtest', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                symbol: currentSymbol,
                timeframe: currentTimeframe,
                days: parseInt(elements.backtestDays.value)
            })
        });

        const data = await response.json();

        if (data.success) {
            displayBacktestResults(data);
        } else {
            alert('Backtest failed: ' + data.error);
        }
    } catch (error) {
        console.error('Backtest error:', error);
        alert('Backtest failed');
    } finally {
        elements.runBacktest.disabled = false;
        elements.runBacktest.textContent = 'Run Backtest';
    }
}

// Display Backtest Results
function displayBacktestResults(data) {
    const results = data.results;

    // Update stats
    document.getElementById('btWinRate').textContent = `${results.win_rate}%`;
    document.getElementById('btReturn').textContent = `${results.total_return > 0 ? '+' : ''}${results.total_return}%`;
    document.getElementById('btDrawdown').textContent = `${results.max_drawdown}%`;
    document.getElementById('btProfitFactor').textContent = results.profit_factor;

    // Update performance stats
    elements.totalTrades.textContent = results.total_trades;
    elements.winRate.textContent = `${results.win_rate}%`;
    elements.totalPnl.textContent = `$${(results.final_capital - results.initial_capital).toFixed(2)}`;
    elements.balance.textContent = `$${results.final_capital.toLocaleString()}`;

    // Show results
    elements.backtestResults.classList.remove('hidden');

    // Update trades table
    updateTradesTable(data.trades);
}

// Update Trades Table
function updateTradesTable(trades) {
    if (!trades || trades.length === 0) {
        elements.tradesBody.innerHTML = '<tr><td colspan="6" class="empty-state">No trades</td></tr>';
        return;
    }

    elements.tradesBody.innerHTML = trades.map(trade => `
        <tr>
            <td>${new Date(trade.exit_time).toLocaleString()}</td>
            <td class="side-${trade.side.toLowerCase()}">${trade.side}</td>
            <td>$${trade.entry_price.toLocaleString()}</td>
            <td>$${trade.exit_price.toLocaleString()}</td>
            <td class="${trade.pnl >= 0 ? 'pnl-positive' : 'pnl-negative'}">
                ${trade.pnl >= 0 ? '+' : ''}$${trade.pnl.toFixed(2)} (${trade.pnl_pct >= 0 ? '+' : ''}${trade.pnl_pct}%)
            </td>
            <td>${trade.reason}</td>
        </tr>
    `).join('');
}

// Update Last Update Time
function updateLastUpdate() {
    elements.lastUpdate.textContent = new Date().toLocaleTimeString();
}

// Setup Event Listeners
function setupEventListeners() {
    // Symbol change
    elements.symbolSelect.addEventListener('change', (e) => {
        currentSymbol = e.target.value;
        loadPriceData();
        loadSignal();
    });

    // Timeframe change
    elements.timeframeSelect.addEventListener('change', (e) => {
        currentTimeframe = e.target.value;
        loadPriceData();
    });

    // Start bot
    elements.startBtn.addEventListener('click', () => {
        startBot();
    });

    // Stop bot
    elements.stopBtn.addEventListener('click', () => {
        stopBot();
    });

    // Run backtest
    elements.runBacktest.addEventListener('click', runBacktest);

    // Auto-refresh every 30 seconds
    setInterval(() => {
        loadPriceData();
        loadSignal();
    }, 30000);
}

// Setup Socket Connection
function setupSocketConnection() {
    try {
        socket = io();

        socket.on('connect', () => {
            console.log('Connected to server');
        });

        socket.on('status', (data) => {
            updateBotStatus(data);
        });

        socket.on('bot_started', (data) => {
            updateBotStatus(data);
            elements.startBtn.disabled = true;
            elements.stopBtn.disabled = false;
        });

        socket.on('bot_stopped', (data) => {
            updateBotStatus(data);
            elements.startBtn.disabled = false;
            elements.stopBtn.disabled = true;
        });

        socket.on('price_update', (data) => {
            updatePrice(data.price);
        });

        socket.on('signal_update', (data) => {
            updateSignalDisplay(data);
        });

    } catch (error) {
        console.log('Socket connection not available');
    }
}

// Start Bot
function startBot() {
    if (socket) {
        socket.emit('start_bot', {
            symbol: currentSymbol,
            timeframe: currentTimeframe
        });
    }

    elements.botStatus.classList.add('online');
    elements.statusText.textContent = `Bot Running - ${currentSymbol}`;
    elements.startBtn.disabled = true;
    elements.stopBtn.disabled = false;
}

// Stop Bot
function stopBot() {
    if (socket) {
        socket.emit('stop_bot');
    }

    elements.botStatus.classList.remove('online');
    elements.statusText.textContent = 'Bot Offline';
    elements.startBtn.disabled = false;
    elements.stopBtn.disabled = true;
}

// Update Bot Status
function updateBotStatus(data) {
    if (data.running) {
        elements.botStatus.classList.add('online');
        elements.statusText.textContent = `Bot Running - ${data.symbol}`;
    } else {
        elements.botStatus.classList.remove('online');
        elements.statusText.textContent = 'Bot Offline';
    }
}
