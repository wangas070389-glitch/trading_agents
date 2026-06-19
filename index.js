// index.js

let allocationChartInstance = null;

// Formatter helpers
const formatCurrency = (val) => {
    return new Intl.NumberFormat('es-MX', {
        style: 'decimal',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(val);
};

// Fetch data and build dashboard
// Fetch data and build dashboard
async function loadDashboard() {
    try {
        const response = await fetch('/api/portfolio');
        if (!response.ok) {
            throw new Error(`Failed to load data: ${response.statusText}`);
        }
        const data = await response.json();
        
        let dcsThreshold = 0.15; // default fallback
        try {
            const paramsResponse = await fetch('/learned_params.json');
            if (paramsResponse.ok) {
                const params = await paramsResponse.json();
                if (params.dcs_threshold !== undefined) {
                    dcsThreshold = params.dcs_threshold;
                }
            }
        } catch (e) {
            console.log("Could not load learned_params.json, using default threshold:", e);
        }
        
        renderDashboard(data, dcsThreshold);
    } catch (err) {
        console.error("Dashboard Load Error:", err);
        alert(`Error loading portfolio: ${err.message}`);
    }
}

function renderDashboard(portfolio, dcsThreshold) {
    const cash = portfolio.cash_balance;
    const originalCapital = portfolio.total_capital;
    const holdings = portfolio.holdings;

    // 1. Calculate values
    let totalStockValue = 0;
    let totalPL = 0;
    
    holdings.forEach(h => {
        totalStockValue += h.shares * h.last_price;
    });

    const totalPortfolioValue = totalStockValue + cash;
    totalPL = totalPortfolioValue - originalCapital;
    const plPercentage = (totalPL / originalCapital) * 100;

    // 2. Update KPI metrics cards
    document.getElementById('total-val').innerHTML = `${formatCurrency(totalPortfolioValue)} <span class="currency">MXN</span>`;
    
    const plElement = document.getElementById('total-pl');
    const plSign = totalPL >= 0 ? '+' : '';
    plElement.textContent = `${plSign}${formatCurrency(totalPL)} MXN (${plSign}${plPercentage.toFixed(2)}%)`;
    if (totalPL >= 0) {
        plElement.className = 'kpi-change positive';
    } else {
        plElement.className = 'kpi-change negative';
    }

    document.getElementById('deployed-val').innerHTML = `${formatCurrency(totalStockValue)} <span class="currency">MXN</span>`;
    document.getElementById('deployed-pct').textContent = `${((totalStockValue / totalPortfolioValue) * 100).toFixed(1)}% allocation`;

    document.getElementById('cash-val').innerHTML = `${formatCurrency(cash)} <span class="currency">MXN</span>`;
    document.getElementById('cash-pct').textContent = `${((cash / totalPortfolioValue) * 100).toFixed(1)}% cash reserve`;

    const slippageSavings = portfolio.slippage_savings !== undefined ? portfolio.slippage_savings : 0.0;
    document.getElementById('dqn-savings').innerHTML = `$${formatCurrency(slippageSavings)} <span class="currency">MXN</span>`;

    // 3. Render Positions Table
    const tbody = document.getElementById('portfolio-body');
    tbody.innerHTML = '';

    holdings.forEach(h => {
        const tr = document.createElement('tr');
        
        const mktVal = h.shares * h.last_price;
        const pl = mktVal - (h.shares * h.buy_price);
        const plPct = ((h.last_price / h.buy_price) - 1) * 100;
        
        const plSign = pl >= 0 ? '+' : '';
        const plClass = pl >= 0 ? 'positive' : 'negative';

        // V4 Specific Metrics
        const targetWeightVal = h.target_weight !== undefined ? h.target_weight : 0.0;
        const dcsVal = h.dcs !== undefined ? h.dcs : 0.0;
        const zgVal = h.zg_t !== undefined ? h.zg_t : 0.0;
        const hmmStateVal = h.hmm_state !== undefined ? h.hmm_state : 0;
        
        const targetWeightPct = (targetWeightVal * 100).toFixed(1) + '%';
        const dcsStr = dcsVal.toFixed(4);
        const zgStr = (zgVal >= 0 ? '+' : '') + zgVal.toFixed(2);
        const zgClass = zgVal >= 1.5 ? 'positive' : (zgVal <= -1.5 ? 'negative' : 'neutral');
        
        let hmmStateStr = 'Sideways (0)';
        let hmmClass = 'neutral';
        if (hmmStateVal === 1) {
            hmmStateStr = 'Bull (1)';
            hmmClass = 'positive';
        } else if (hmmStateVal === -1) {
            hmmStateStr = 'Bear (-1)';
            hmmClass = 'negative';
        }
        
        const dcsClass = dcsVal >= dcsThreshold ? 'positive' : 'negative';

        tr.innerHTML = `
            <td><strong>${h.ticker}</strong></td>
            <td>${h.shares.toLocaleString()}</td>
            <td>$${formatCurrency(h.buy_price)}</td>
            <td>$${formatCurrency(h.last_price)}</td>
            <td>$${formatCurrency(mktVal)}</td>
            <td class="${plClass}">${plSign}$${formatCurrency(pl)}</td>
            <td class="${plClass}">${plSign}${plPct.toFixed(2)}%</td>
            <td><strong>${targetWeightPct}</strong></td>
            <td class="${dcsClass}">${dcsStr}</td>
            <td class="${zgClass}">${zgStr}</td>
            <td><span class="hmm-state-badge ${hmmClass}">${hmmStateStr}</span></td>
        `;
        tbody.appendChild(tr);
    });

    // 4. Update Rebalancing Alerts
    const alertsContainer = document.getElementById('alerts-list');
    alertsContainer.innerHTML = '';
    let alertsCount = 0;

    holdings.forEach(h => {
        const hmmStateVal = h.hmm_state !== undefined ? h.hmm_state : 0;
        const dcsVal = h.dcs !== undefined ? h.dcs : 0.0;

        if (hmmStateVal === -1) {
            alertsCount++;
            const div = document.createElement('div');
            div.className = 'alert-item alert-danger';
            div.innerHTML = `
                <span class="alert-icon">🚨</span>
                <div class="alert-text">
                    <strong>[BEAR REGIME ALERT]</strong> ${h.ticker} has transitioned into a Bearish HMM market regime. The model suggests reducing exposure.
                </div>
            `;
            alertsContainer.appendChild(div);
        } else if (dcsVal < dcsThreshold) {
            alertsCount++;
            const div = document.createElement('div');
            div.className = 'alert-item alert-warning';
            div.innerHTML = `
                <span class="alert-icon">⚠️</span>
                <div class="alert-text">
                    <strong>[SIGNAL WEAKNESS]</strong> ${h.ticker} Differential Quantitative Signal is weak (DCS v2: <strong>${dcsVal.toFixed(4)}</strong> &lt; ${dcsThreshold.toFixed(2)}). Target weight is capped.
                </div>
            `;
            alertsContainer.appendChild(div);
        }
    });

    // Always append Bondia status
    const bondiaDiv = document.createElement('div');
    bondiaDiv.className = 'alert-item alert-info';
    bondiaDiv.innerHTML = `
        <span class="alert-icon">💸</span>
        <div class="alert-text">
            <strong>[BONDIA CASH ROUTING]</strong> Cash reserves are parked at 11% APR. Nightly interest accrues automatically.
        </div>
    `;
    alertsContainer.appendChild(bondiaDiv);

    // 5. Render Allocation Donut Chart
    renderChart(cash, holdings);
}

function renderChart(cash, holdings) {
    const ctx = document.getElementById('allocationChart').getContext('2d');
    
    // Destroy previous instance to prevent rendering duplicates
    if (allocationChartInstance) {
        allocationChartInstance.destroy();
    }

    const labels = ['Cash'];
    const data = [cash];
    const backgroundColors = ['rgba(255, 255, 255, 0.08)'];
    const borderColors = ['rgba(255, 255, 255, 0.15)'];

    // Distinct vibrant border/slice colors for assets
    const assetColors = [
        { fill: 'rgba(99, 102, 241, 0.5)', border: '#6366f1' },  // Indigo
        { fill: 'rgba(16, 185, 129, 0.5)', border: '#10b981' }, // Emerald
        { fill: 'rgba(14, 165, 233, 0.5)', border: '#0ea5e9' }   // Cyan
    ];

    holdings.forEach((h, idx) => {
        labels.push(h.ticker);
        data.push(h.shares * h.last_price);
        const col = assetColors[idx % assetColors.length];
        backgroundColors.push(col.fill);
        borderColors.push(col.border);
    });

    allocationChartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: backgroundColors,
                borderColor: borderColors,
                borderWidth: 1.5
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        color: '#8f9cae',
                        font: {
                            family: 'Outfit',
                            size: 11
                        },
                        padding: 15
                    }
                }
            },
            cutout: '70%'
        }
    });
}

// Bind button action
document.getElementById('refresh-btn').addEventListener('click', async () => {
    const btn = document.getElementById('refresh-btn');
    btn.disabled = true;
    btn.classList.add('loading');
    btn.innerHTML = `<span class="btn-icon">⏳</span> Fetching Live Data...`;

    try {
        const response = await fetch('/api/refresh', {
            method: 'POST'
        });
        
        if (!response.ok) {
            throw new Error(`Failed to refresh prices: ${response.statusText}`);
        }
        
        const resData = await response.json();
        if (resData.status === 'success') {
            renderDashboard(resData.data);
        } else {
            throw new Error(resData.message || "Unknown error during refresh");
        }
    } catch (err) {
        console.error("Refresh Error:", err);
        alert(`Failed to update live prices: ${err.message}`);
    } finally {
        btn.disabled = false;
        btn.classList.remove('loading');
        btn.innerHTML = `<span class="btn-icon">🔄</span> Refresh Live Prices`;
    }
});

let backtestChartInstance = null;
let currentStrategy = 'value_equity';

function renderBacktestChart(dates, strategy, cash, benchmark) {
    const ctx = document.getElementById('backtestChart').getContext('2d');
    if (backtestChartInstance) {
        backtestChartInstance.destroy();
    }
    
    const tickerVal = document.getElementById('macd-ticker').value;
    const valVariant = document.getElementById('val-variant').value;
    const stratLabel = currentStrategy === 'macd_trend' 
        ? (tickerVal === 'ALL' ? 'MACD Multi-Asset Strategy' : 'MACD Systematic Strategy') 
        : `V5 Active Strategy (${valVariant === 'adaptive' ? 'Adaptive' : (valVariant === 'aggressive' ? 'Aggressive' : 'Standard')})`;
    const benchLabel = currentStrategy === 'macd_trend' 
        ? (tickerVal === 'ALL' ? 'SPY Buy & Hold' : `${tickerVal} Buy & Hold`) 
        : 'SPY Buy & Hold';
    const stratColor = currentStrategy === 'macd_trend' ? '#6366f1' : '#10b981';
    const stratBg = currentStrategy === 'macd_trend' ? 'rgba(99, 102, 241, 0.05)' : 'rgba(16, 185, 129, 0.05)';
    
    backtestChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: dates,
            datasets: [
                {
                    label: stratLabel,
                    data: strategy,
                    borderColor: stratColor,
                    backgroundColor: stratBg,
                    borderWidth: 2,
                    pointRadius: 1,
                    tension: 0.1,
                    fill: true
                },
                {
                    label: 'Bondia Cash (11% APR)',
                    data: cash,
                    borderColor: '#0ea5e9',
                    backgroundColor: 'transparent',
                    borderWidth: 1.5,
                    pointRadius: 0,
                    borderDash: [4, 4],
                    tension: 0.1
                },
                {
                    label: benchLabel,
                    data: benchmark,
                    borderColor: '#a855f7',
                    backgroundColor: 'transparent',
                    borderWidth: 1.5,
                    pointRadius: 0,
                    tension: 0.1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        color: '#8f9cae',
                        font: { family: 'Outfit', size: 10 }
                    }
                }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.03)' },
                    ticks: {
                        color: '#8f9cae',
                        font: { family: 'Outfit', size: 9 },
                        maxTicksLimit: 8
                    }
                },
                y: {
                    grid: { color: 'rgba(255, 255, 255, 0.03)' },
                    ticks: {
                        color: '#8f9cae',
                        font: { family: 'Outfit', size: 9 },
                        callback: function(value) { return '$' + value.toLocaleString(); }
                    }
                }
            }
        }
    });
}

// Setup Strategy Toggles
document.getElementById('strat-val-btn').addEventListener('click', () => {
    if (currentStrategy === 'value_equity') return;
    currentStrategy = 'value_equity';
    
    // UI states
    document.getElementById('strat-val-btn').style.background = 'rgba(16, 185, 129, 0.2)';
    document.getElementById('strat-val-btn').style.borderColor = '#10b981';
    document.getElementById('strat-val-btn').style.color = 'white';
    
    document.getElementById('strat-macd-btn').style.background = 'transparent';
    document.getElementById('strat-macd-btn').style.borderColor = 'transparent';
    document.getElementById('strat-macd-btn').style.color = '#8f9cae';
    
    document.getElementById('macd-ticker-container').style.display = 'none';
    document.getElementById('val-variant-container').style.display = 'flex';
    
    // Update labels
    document.getElementById('label-strat-ret').textContent = 'V5 Strategy Return:';
    document.getElementById('label-cash-ret').textContent = 'Bondia Cash Yield (11%):';
    document.getElementById('label-spy-ret').textContent = 'SPY Index Return:';
    document.getElementById('label-fees-paid').textContent = 'Total Trading Fees Paid:';
    
    resetBacktestUI();
});

document.getElementById('strat-macd-btn').addEventListener('click', () => {
    if (currentStrategy === 'macd_trend') return;
    currentStrategy = 'macd_trend';
    
    // UI states
    document.getElementById('strat-macd-btn').style.background = 'rgba(99, 102, 241, 0.2)';
    document.getElementById('strat-macd-btn').style.borderColor = '#6366f1';
    document.getElementById('strat-macd-btn').style.color = 'white';
    
    document.getElementById('strat-val-btn').style.background = 'transparent';
    document.getElementById('strat-val-btn').style.borderColor = 'transparent';
    document.getElementById('strat-val-btn').style.color = '#8f9cae';
    
    document.getElementById('macd-ticker-container').style.display = 'flex';
    document.getElementById('val-variant-container').style.display = 'none';
    
    // Update labels
    document.getElementById('label-strat-ret').textContent = 'MACD Strategy Return:';
    document.getElementById('label-cash-ret').textContent = 'Bondia Cash Yield (11%):';
    const ticker = document.getElementById('macd-ticker').value;
    const displayTicker = ticker === 'ALL' ? 'SPY' : ticker;
    document.getElementById('label-spy-ret').textContent = `${displayTicker} Index Return:`;
    document.getElementById('label-fees-paid').textContent = 'Total Trans. Cost (Est):';
    
    resetBacktestUI();
});

// Update label-spy-ret when dropdown changes
document.getElementById('macd-ticker').addEventListener('change', () => {
    const ticker = document.getElementById('macd-ticker').value;
    const displayTicker = ticker === 'ALL' ? 'SPY' : ticker;
    document.getElementById('label-spy-ret').textContent = `${displayTicker} Index Return:`;
    resetBacktestUI();
});

// Update backtest UI when Value Strategy profile changes
document.getElementById('val-variant').addEventListener('change', () => {
    resetBacktestUI();
});

function resetBacktestUI() {
    document.getElementById('bt-strat-ret').textContent = '--';
    document.getElementById('bt-cash-ret').textContent = '--';
    document.getElementById('bt-spy-ret').textContent = '--';
    document.getElementById('bt-sharpe').textContent = '--';
    document.getElementById('bt-drawdown').textContent = '--';
    document.getElementById('bt-fees').textContent = '--';
    if (backtestChartInstance) {
        backtestChartInstance.destroy();
        backtestChartInstance = null;
    }
}

// Bind backtest button action
document.getElementById('backtest-btn').addEventListener('click', async () => {
    const btn = document.getElementById('backtest-btn');
    btn.disabled = true;
    btn.innerHTML = `<span class="btn-icon">⏳</span> Running simulation...`;
    
    try {
        let response;
        if (currentStrategy === 'value_equity') {
            const variant = document.getElementById('val-variant').value;
            response = await fetch('/api/backtest', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ strategy_type: variant })
            });
        } else {
            const ticker = document.getElementById('macd-ticker').value;
            response = await fetch('/api/backtest_macd', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ ticker: ticker })
            });
        }
        
        if (!response.ok) {
            throw new Error(`Simulation failed: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        // Update Metrics Panel
        const metrics = data.metrics;
        document.getElementById('bt-strat-ret').textContent = `${metrics.strategy_return >= 0 ? '+' : ''}${metrics.strategy_return.toFixed(2)}%`;
        document.getElementById('bt-cash-ret').textContent = `+${metrics.cash_return.toFixed(2)}%`;
        document.getElementById('bt-spy-ret').textContent = `${metrics.benchmark_return >= 0 ? '+' : ''}${metrics.benchmark_return.toFixed(2)}%`;
        document.getElementById('bt-sharpe').textContent = metrics.sharpe.toFixed(2);
        document.getElementById('bt-drawdown').textContent = `${metrics.drawdown.toFixed(2)}%`;
        
        const isMACD = currentStrategy === 'macd_trend';
        const feeCurrency = isMACD ? 'USD' : 'MXN';
        document.getElementById('bt-fees').textContent = `$${formatCurrency(metrics.fees)} ${feeCurrency}`;
        
        // Render Chart
        renderBacktestChart(data.dates, data.strategy, data.cash, data.benchmark);
        
    } catch (err) {
        console.error("Backtest Error:", err);
        alert(`Backtest execution error: ${err.message}`);
    } finally {
        btn.disabled = false;
        btn.innerHTML = `<span class="btn-icon">📈</span> Run Backtest Simulation`;
    }
});

// Load on DOM ready
document.addEventListener('DOMContentLoaded', loadDashboard);
