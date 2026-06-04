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
async function loadDashboard() {
    try {
        const response = await fetch('/api/portfolio');
        if (!response.ok) {
            throw new Error(`Failed to load data: ${response.statusText}`);
        }
        const data = await response.json();
        renderDashboard(data);
    } catch (err) {
        console.error("Dashboard Load Error:", err);
        alert(`Error loading portfolio: ${err.message}`);
    }
}

function renderDashboard(portfolio) {
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

        // Calculate exit target progress
        // BuyPrice (0%) to IntrinsicValue (100%)
        let progress = 0;
        if (h.intrinsic_value > h.buy_price) {
            progress = ((h.last_price - h.buy_price) / (h.intrinsic_value - h.buy_price)) * 100;
            progress = Math.min(100, Math.max(0, progress)); // Constrain between 0% and 100%
        }

        tr.innerHTML = `
            <td><strong>${h.ticker}</strong></td>
            <td>${h.shares.toLocaleString()}</td>
            <td>$${formatCurrency(h.buy_price)}</td>
            <td>$${formatCurrency(h.last_price)}</td>
            <td>$${formatCurrency(mktVal)}</td>
            <td class="${plClass}">${plSign}$${formatCurrency(pl)}</td>
            <td class="${plClass}">${plSign}${plPct.toFixed(2)}%</td>
            <td>
                <div class="progress-bar-container">
                    <div class="progress-labels">
                        <span>Buy</span>
                        <span><strong>${progress.toFixed(0)}%</strong></span>
                        <span>Target</span>
                    </div>
                    <div class="progress-track">
                        <div class="progress-fill" style="width: ${progress}%"></div>
                    </div>
                </div>
            </td>
        `;
        tbody.appendChild(tr);
    });

    // 4. Update Rebalancing Alerts
    const alertsContainer = document.getElementById('alerts-list');
    alertsContainer.innerHTML = '';
    let alertsCount = 0;

    holdings.forEach(h => {
        if (h.last_price >= h.intrinsic_value) {
            alertsCount++;
            const div = document.createElement('div');
            div.className = 'alert-item alert-danger';
            div.innerHTML = `
                <span class="alert-icon">🚨</span>
                <div class="alert-text">
                    <strong>[SELL TRIGGER: TAKE PROFIT]</strong> ${h.ticker} has reached fair intrinsic value of <strong>$${h.intrinsic_value.toFixed(2)} MXN</strong> (Current: $${h.last_price.toFixed(2)}). Sell 100% to capitalize profit!
                </div>
            `;
            alertsContainer.appendChild(div);
        } else if (h.last_price >= h.scale_out_price) {
            alertsCount++;
            const div = document.createElement('div');
            div.className = 'alert-item alert-warning';
            div.innerHTML = `
                <span class="alert-icon">⚠️</span>
                <div class="alert-text">
                    <strong>[SELL TRIGGER: SCALE OUT]</strong> ${h.ticker} has reached the 90% scale-out limit of <strong>$${h.scale_out_price.toFixed(2)} MXN</strong> (Current: $${h.last_price.toFixed(2)}). Sell 50% to secure profits!
                </div>
            `;
            alertsContainer.appendChild(div);
        }
    });

    if (alertsCount === 0) {
        alertsContainer.innerHTML = `
            <div class="alert-item empty-state">
                <span class="alert-icon">✨</span>
                <p>No active sell triggers hit. Open positions are moving within target boundaries.</p>
            </div>
        `;
    }

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

// Load on DOM ready
document.addEventListener('DOMContentLoaded', loadDashboard);
