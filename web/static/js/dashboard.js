/**
 * Trading Bot Dashboard - JavaScript
 * Handles chart rendering, API calls, and real-time updates
 */

// Global state
let priceChart = null;
let currentSymbol = 'BTCUSDT';
let currentTimeframe = '1h';
let isLoading = false;

// DOM Elements - with null checks
const elements = {};

// Initialize DOM elements safely
function initElements() {
    elements.symbolSelect = document.getElementById('symbolSelect');
    elements.timeframeSelect = document.getElementById('timeframeSelect');
    elements.startBtn = document.getElementById('startBtn');
    elements.stopBtn = document.getElementById('stopBtn');
    elements.currentPrice = document.getElementById('currentPrice');
    elements.priceChange = document.getElementById('priceChange');
    elements.signalDisplay = document.getElementById('signalDisplay');
    elements.signalScore = document.getElementById('signalScore');
    elements.rsiValue = document.getElementById('rsiValue');
    elements.macdValue = document.getElementById('macdValue');
    elements.emaTrend = document.getElementById('emaTrend');
    elements.volumeStatus = document.getElementById('volumeStatus');
    elements.totalTrades = document.getElementById('totalTrades');
    elements.winRate = document.getElementById('winRate');
    elements.totalPnl = document.getElementById('totalPnl');
    elements.balance = document.getElementById('balance');
    elements.backtestDays = document.getElementById('backtestDays');
    elements.runBacktest = document.getElementById('runBacktest');
    elements.backtestResults = document.getElementById('backtestResults');
    elements.tradesBody = document.getElementById('tradesBody');
    elements.botStatus = document.getElementById('botStatus');
    elements.statusText = document.getElementById('statusText');
    elements.lastUpdate = document.getElementById('lastUpdate');
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('Dashboard initializing...');
    initElements();
    initChart();
    loadPriceData();
    loadSignal();
    setupEventListeners();
    console.log('Dashboard initialized');
});

// Initialize Chart
function initChart() {
    const canvas = document.getElementById('priceChart');
    if (!canvas) {
        console.error('Price chart canvas not found');
        return;
    }

    const ctx = canvas.getContext('2d');

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
                    grid: { color: 'rgba(48, 54, 61, 0.5)' },
                    ticks: { color: '#8b949e', maxTicksLimit: 10 }
                },
                y: {
                    display: true,
                    position: 'right',
                    grid: { color: 'rgba(48, 54, 61, 0.5)' },
                    ticks: { color: '#8b949e' }
                }
            }
        }
    });

    console.log('Chart initialized');
}

// Load Price Data
async function loadPriceData() {
    if (isLoading) return;
    isLoading = true;

    console.log('Loading price data for', currentSymbol);

    try {
        const response = await fetch(`/api/price/${currentSymbol}`);
        const data = await response.json();

        console.log('Price data response:', data);

        if (data.success) {
            updateChart(data.candles);
            updatePrice(data.price);
            updateIndicators(data.indicators);
            updateLastUpdate();
        } else {
            console.error('Price data error:', data.error);
        }
    } catch (error) {
        console.error('Error loading price data:', error);
    } finally {
        isLoading = false;
    }
}

// Update Chart
function updateChart(candles) {
    if (!priceChart || !candles || candles.length === 0) {
        console.error('Cannot update chart - missing data');
        return;
    }

    const labels = candles.map(c => {
        const date = new Date(c.time);
        return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    });

    const prices = candles.map(c => c.close);

    priceChart.data.labels = labels;
    priceChart.data.datasets[0].data = prices;

    // Simple EMA calculation for display
    const emaData = calculateEMA(prices, 21);
    priceChart.data.datasets[1].data = emaData;

    priceChart.update('none');
    console.log('Chart updated with', prices.length, 'candles');
}

// Simple EMA calculation
function calculateEMA(prices, period) {
    const k = 2 / (period + 1);
    let ema = [prices[0]];

    for (let i = 1; i < prices.length; i++) {
        ema.push(prices[i] * k + ema[i - 1] * (1 - k));
    }

    return ema;
}

// Update Price Display
function updatePrice(price) {
    if (elements.currentPrice) {
        elements.currentPrice.textContent = `$${price.toLocaleString()}`;
    }

    if (elements.priceChange) {
        const change = (Math.random() * 4 - 2).toFixed(2);
        const isPositive = parseFloat(change) >= 0;
        elements.priceChange.textContent = `${isPositive ? '+' : ''}${change}%`;
        elements.priceChange.className = `price-change ${isPositive ? 'positive' : 'negative'}`;
    }
}

// Update Indicators Display
function updateIndicators(indicators) {
    if (!indicators) return;

    if (elements.rsiValue) elements.rsiValue.textContent = indicators.rsi || '--';
    if (elements.macdValue) elements.macdValue.textContent = indicators.macd?.toFixed(2) || '--';

    if (elements.emaTrend) {
        const isBullish = indicators.ema_short > indicators.ema_medium;
        elements.emaTrend.textContent = isBullish ? 'Bullish ↑' : 'Bearish ↓';
        elements.emaTrend.style.color = isBullish ? '#3fb950' : '#f85149';
    }

    if (elements.volumeStatus) elements.volumeStatus.textContent = 'Normal';
}

// Load Signal
async function loadSignal() {
    try {
        const response = await fetch(`/api/signal/${currentSymbol}`);
        const data = await response.json();

        console.log('Signal data:', data);

        if (data.success) {
            updateSignalDisplay(data);
        }
    } catch (error) {
        console.error('Error loading signal:', error);
    }
}

// Update Signal Display
function updateSignalDisplay(data) {
    if (elements.signalDisplay) {
        const signalType = elements.signalDisplay.querySelector('.signal-type');
        if (signalType) {
            signalType.textContent = data.signal_type;
            signalType.className = `signal-type ${data.signal_type.toLowerCase()}`;
        }
    }

    if (elements.signalScore) {
        elements.signalScore.textContent = `${data.score}%`;
    }
}

// Run Backtest
async function runBacktest() {
    if (!elements.runBacktest) return;

    elements.runBacktest.disabled = true;
    elements.runBacktest.textContent = 'Running...';

    try {
        const response = await fetch('/api/backtest', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                symbol: currentSymbol,
                timeframe: currentTimeframe,
                days: parseInt(elements.backtestDays?.value || 90)
            })
        });

        const data = await response.json();
        console.log('Backtest result:', data);

        if (data.success) {
            displayBacktestResults(data);
        } else {
            alert('Backtest failed: ' + data.error);
        }
    } catch (error) {
        console.error('Backtest error:', error);
        alert('Backtest failed: ' + error.message);
    } finally {
        elements.runBacktest.disabled = false;
        elements.runBacktest.textContent = 'Run Backtest';
    }
}

// Display Backtest Results
function displayBacktestResults(data) {
    const results = data.results;

    // Update backtest stats
    const btWinRate = document.getElementById('btWinRate');
    const btReturn = document.getElementById('btReturn');
    const btDrawdown = document.getElementById('btDrawdown');
    const btProfitFactor = document.getElementById('btProfitFactor');

    if (btWinRate) btWinRate.textContent = `${results.win_rate}%`;
    if (btReturn) btReturn.textContent = `${results.total_return > 0 ? '+' : ''}${results.total_return}%`;
    if (btDrawdown) btDrawdown.textContent = `${results.max_drawdown}%`;
    if (btProfitFactor) btProfitFactor.textContent = results.profit_factor;

    // Update performance stats
    if (elements.totalTrades) elements.totalTrades.textContent = results.total_trades;
    if (elements.winRate) elements.winRate.textContent = `${results.win_rate}%`;
    if (elements.totalPnl) elements.totalPnl.textContent = `$${(results.final_capital - results.initial_capital).toFixed(2)}`;
    if (elements.balance) elements.balance.textContent = `$${results.final_capital.toLocaleString()}`;

    // Show results
    if (elements.backtestResults) {
        elements.backtestResults.classList.remove('hidden');
    }

    // Update trades table
    updateTradesTable(data.trades);
}

// Update Trades Table
function updateTradesTable(trades) {
    if (!elements.tradesBody) return;

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
    if (elements.lastUpdate) {
        elements.lastUpdate.textContent = new Date().toLocaleTimeString();
    }
}

// Setup Event Listeners
function setupEventListeners() {
    if (elements.symbolSelect) {
        elements.symbolSelect.addEventListener('change', (e) => {
            currentSymbol = e.target.value;
            loadPriceData();
            loadSignal();
        });
    }

    if (elements.timeframeSelect) {
        elements.timeframeSelect.addEventListener('change', (e) => {
            currentTimeframe = e.target.value;
            loadPriceData();
        });
    }

    if (elements.startBtn) {
        elements.startBtn.addEventListener('click', startBot);
    }

    if (elements.stopBtn) {
        elements.stopBtn.addEventListener('click', stopBot);
    }

    if (elements.runBacktest) {
        elements.runBacktest.addEventListener('click', runBacktest);
    }

    // Auto-refresh every 30 seconds
    setInterval(() => {
        loadPriceData();
        loadSignal();
    }, 30000);
}

// Start Bot
function startBot() {
    if (elements.botStatus) elements.botStatus.classList.add('online');
    if (elements.statusText) elements.statusText.textContent = `Bot Running - ${currentSymbol}`;
    if (elements.startBtn) elements.startBtn.disabled = true;
    if (elements.stopBtn) elements.stopBtn.disabled = false;
}

// Stop Bot
function stopBot() {
    if (elements.botStatus) elements.botStatus.classList.remove('online');
    if (elements.statusText) elements.statusText.textContent = 'Bot Offline';
    if (elements.startBtn) elements.startBtn.disabled = false;
    if (elements.stopBtn) elements.stopBtn.disabled = true;
}
