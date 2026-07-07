const STRATEGY_METADATA = {
    "S1": { name: "Adaptive Value", file: "portfolio.json", currency: "MXN", active: true, assets: "BMV IPC Leaders", cagr: "20.07%", sharpe: "0.82", maxdd: "-28.18%" },
    "S2": { name: "1d MACD Systematic", file: "portfolio_macd.json", currency: "MXN", active: true, assets: "BMV Leaders + SIC", cagr: "13.10%", sharpe: "1.27", maxdd: "-10.94%" },
    "S3": { name: "US Stock Momentum", file: "portfolio_us_stocks.json", currency: "USD", active: false, assets: "US Large Cap Tech", cagr: "25.40%", sharpe: "1.15", maxdd: "-18.20%" },
    "S4": { name: "US DCS Value-Growth", file: "portfolio_us_dcs.json", currency: "USD", active: true, assets: "US Growth Leaders", cagr: "21.93%", sharpe: "1.14", maxdd: "-12.19%" },
    "S5": { name: "Alternative Assets", file: "portfolio_alternatives.json", currency: "USD", active: true, assets: "BTC, ETH, Gold, USO", cagr: "18.40%", sharpe: "0.95", maxdd: "-15.20%" },
    "S6": { name: "High-Beta Momentum", file: "portfolio_high_beta.json", currency: "USD", active: true, assets: "High Beta Tech Stocks", cagr: "22.10%", sharpe: "1.05", maxdd: "-19.50%" },
    "S8": { name: "Dividend Quality & Yield", file: "portfolio_dividends.json", currency: "MXN", active: true, assets: "FIBRAS + MX Dividends", cagr: "14.50%", sharpe: "1.12", maxdd: "-11.20%" },
    "S9": { name: "AI Regime Stat-Arb", file: "portfolio_strategy9.json", currency: "MXN", active: true, assets: "BMV Cointegrated Pairs", cagr: "26.80%", sharpe: "1.45", maxdd: "-7.50%" },
    "S10": { name: "AI Intraday VWAP", file: "portfolio_strategy10.json", currency: "MXN", active: true, assets: "TQQQ, SQQQ, QQQ", cagr: "53.25%", sharpe: "2.73", maxdd: "-4.14%" },
    "S11": { name: "AI Intraday CCI-ADX", file: "portfolio_strategy11.json", currency: "MXN", active: true, assets: "TQQQ, SQQQ, QQQ", cagr: "11.88%", sharpe: "0.10", maxdd: "-16.31%" },
    "S12": { name: "Vol-Targeted Trend (VTTL)", file: "portfolio_strategy12.json", currency: "MXN", active: true, assets: "TQQQ + BONDIA", cagr: "17.13%", sharpe: "0.46", maxdd: "-21.34%" },
    "S13": { name: "Risk Appetite (CARA)", file: "portfolio_strategy13.json", currency: "MXN", active: false, assets: "TQQQ + BONDIA", cagr: "15.95%", sharpe: "0.45", maxdd: "-25.02%" },
    "S14": { name: "Aggregator (HEDGE)", file: "portfolio_strategy14.json", currency: "MXN", active: true, assets: "S12, S13 + BONDIA", cagr: "15.17%", sharpe: "0.53", maxdd: "-15.19%" },
    "S15": { name: "Tracker (TRACK)", file: "portfolio_strategy15.json", currency: "MXN", active: true, assets: "S12, S13 + BONDIA", cagr: "15.05%", sharpe: "0.53", maxdd: "-14.73%" }
};

// Fixed simulated FX rate for consolidated calculations
const FX_RATE = 20.0; 

let navChartInstance = null;
let allocChartInstance = null;

// Initialize Dashboard
document.addEventListener("DOMContentLoaded", () => {
    loadDashboardData();
    checkHaltStatus();
});

// Check if circuit breaker flag exists
function checkHaltStatus() {
    fetch("HALT_us_stocks.flag")
        .then(response => {
            const haltBadge = document.getElementById("halt-status");
            const haltText = document.getElementById("halt-text");
            if (response.ok) {
                haltBadge.className = "status-badge halt";
                haltText.textContent = "ALERTA: HALT ACTIVO (S3)";
            } else {
                haltBadge.className = "status-badge secure";
                haltText.textContent = "Sistema Seguro (Normal)";
            }
        })
        .catch(() => {
            // Safe fallback if flag is not present
            const haltBadge = document.getElementById("halt-status");
            const haltText = document.getElementById("halt-text");
            haltBadge.className = "status-badge secure";
            haltText.textContent = "Sistema Seguro (Normal)";
        });
}

// Load and aggregate data
async function loadDashboardData() {
    const promises = Object.keys(STRATEGY_METADATA).map(async (key) => {
        const metadata = STRATEGY_METADATA[key];
        try {
            const res = await fetch(metadata.file);
            if (!res.ok) throw new Error(`Not found`);
            const data = await res.json();
            return { key, data, success: true };
        } catch (e) {
            return { key, success: false };
        }
    });

    const results = await Promise.all(promises);
    
    let totalNavMxn = 0;
    let totalCashMxn = 0;
    let totalInvestedMxn = 0;
    const combinedPositions = [];
    const allocationClasses = {
        "US Equity": 0,
        "MXN Equity": 0,
        "Crypto": 0,
        "Commodities": 0,
        "Cash/Sweep": 0
    };

    const strategiesGrid = document.getElementById("strategies-card-grid");
    strategiesGrid.innerHTML = "";

    results.forEach(result => {
        const key = result.key;
        const metadata = STRATEGY_METADATA[key];
        
        let nav = 0;
        let cash = 0;
        let invested = 0;
        let roi = "0.00%";
        let statusClass = metadata.active ? "active" : "suspended";
        let lastUpdated = "Inactivo";

        if (result.success) {
            const data = result.data;
            cash = data.cash_balance || 0;
            nav = data.total_capital || data.total_portfolio_value || cash;
            invested = nav - cash;
            lastUpdated = data.last_updated || "Hoy";

            // Aggregate values
            const rate = metadata.currency === "USD" ? FX_RATE : 1.0;
            totalNavMxn += nav * rate;
            totalCashMxn += cash * rate;
            totalInvestedMxn += invested * rate;

            // Classify Cash
            allocationClasses["Cash/Sweep"] += cash * rate;

            // Process Positions
            if (data.holdings && data.holdings.length > 0) {
                data.holdings.forEach(pos => {
                    const shares = pos.shares || 0;
                    const buyPrice = pos.buy_price || pos.average_price || 0;
                    const lastPrice = pos.last_price || pos.current_price || buyPrice;
                    const value = shares * lastPrice;
                    const valueMxn = value * rate;

                    // Classify asset class
                    const assetClass = classifyAsset(pos.ticker, metadata.currency);
                    allocationClasses[assetClass] += valueMxn;

                    const cost = shares * buyPrice;
                    const profitPct = cost > 0 ? ((value - cost) / cost) * 100 : 0;

                    combinedPositions.push({
                        ticker: pos.ticker,
                        strategy: key,
                        shares: shares,
                        buyPrice: buyPrice,
                        lastPrice: lastPrice,
                        value: value,
                        profitPct: profitPct,
                        currency: metadata.currency
                    });
                });
            }

            // Calculate ROI
            const initial = metadata.currency === "USD" ? 100000.0 : 200000.0;
            const profit = nav - initial;
            roi = `${profit >= 0 ? "+" : ""}${((profit / initial) * 100).toFixed(2)}%`;
        }

        // Render Strategy Card
        const card = document.createElement("div");
        card.className = `glass-card strategy-card ${statusClass}`;
        card.innerHTML = `
            <div class="strategy-header">
                <div>
                    <div class="strategy-name">${key}: ${metadata.name}</div>
                    <div style="font-size:0.75rem; color:var(--text-secondary)">${metadata.assets}</div>
                </div>
                <div class="strategy-status-dot" style="background-color: ${metadata.active ? 'var(--accent-green)' : 'var(--accent-red)'}"></div>
            </div>
            <div class="strategy-metrics">
                <div class="metric-box">
                    <span class="metric-label">NAV actual</span>
                    <span class="metric-value">${nav > 0 ? formatCurrency(nav, metadata.currency) : "N/D"}</span>
                </div>
                <div class="metric-box">
                    <span class="metric-label">ROI en vivo</span>
                    <span class="metric-value ${roi.startsWith('-') ? 'value-down' : 'value-up'}">${roi}</span>
                </div>
                <div class="metric-box" style="margin-top:0.5rem">
                    <span class="metric-label">CAGR Est.</span>
                    <span class="metric-value" style="color:var(--accent-blue)">${metadata.cagr}</span>
                </div>
                <div class="metric-box" style="margin-top:0.5rem">
                    <span class="metric-label">Sharpe Est.</span>
                    <span class="metric-value">${metadata.sharpe}</span>
                </div>
            </div>
            <div class="strategy-footer">
                <span class="strategy-assets">MaxDD: ${metadata.maxdd}</span>
                <span style="color:var(--text-secondary)">Act: ${lastUpdated.split(' ')[0]}</span>
            </div>
        `;
        strategiesGrid.appendChild(card);
    });

    // Populate Top Metrics
    document.getElementById("metric-net-val").textContent = `$${totalNavMxn.toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} MXN`;
    document.getElementById("metric-net-val-usd").textContent = `$${(totalNavMxn / FX_RATE).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} USD`;
    
    document.getElementById("metric-cash").textContent = `$${totalCashMxn.toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} MXN`;
    const cashPct = totalNavMxn > 0 ? (totalCashMxn / totalNavMxn) * 100 : 0;
    document.getElementById("metric-cash-pct").textContent = `${cashPct.toFixed(1)}% del valor total (BONDIA)`;

    document.getElementById("metric-invested").textContent = `$${totalInvestedMxn.toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} MXN`;
    const investedPct = totalNavMxn > 0 ? (totalInvestedMxn / totalNavMxn) * 100 : 0;
    document.getElementById("metric-invested-pct").textContent = `${investedPct.toFixed(1)}% del valor total`;

    document.getElementById("metric-twr").textContent = "+15.63%"; // Core S7 performance

    // Populate Positions Table
    const tableBody = document.getElementById("positions-table-body");
    tableBody.innerHTML = "";
    
    if (combinedPositions.length === 0) {
        tableBody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-secondary);">No hay posiciones de activos en cartera en este momento.</td></tr>`;
    } else {
        combinedPositions.forEach(pos => {
            const tr = document.createElement("tr");
            const profitClass = pos.profitPct >= 0 ? "value-up" : "value-down";
            tr.innerHTML = `
                <td><strong>${pos.ticker}</strong></td>
                <td><span class="badge badge-strat">${pos.strategy}</span></td>
                <td>${pos.shares.toFixed(4)}</td>
                <td>${formatCurrency(pos.buyPrice, pos.currency)}</td>
                <td>${formatCurrency(pos.lastPrice, pos.currency)}</td>
                <td><strong>${formatCurrency(pos.shares * pos.lastPrice, pos.currency)}</strong></td>
                <td class="${profitClass}">${pos.profitPct >= 0 ? "+" : ""}${pos.profitPct.toFixed(2)}%</td>
            `;
            tableBody.appendChild(tr);
        });
    }

    // Render Allocation Donut Chart
    renderAllocationChart(allocationClasses);

    // Fetch and Render Nav Line Chart
    loadNavChartData();
}

// Asset classifier
function classifyAsset(ticker, currency) {
    if (ticker.includes("BTC") || ticker.includes("ETH")) return "Crypto";
    if (["GLD", "SLV", "USO", "DBA"].includes(ticker)) return "Commodities";
    if (currency === "USD") return "US Equity";
    return "MXN Equity";
}

function formatCurrency(val, currency) {
    return currency === "USD" 
        ? `$${val.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} USD`
        : `$${val.toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} MXN`;
}

// Chart Renderings
function renderAllocationChart(allocData) {
    const ctx = document.getElementById("allocationChart").getContext("2d");
    if (allocChartInstance) allocChartInstance.destroy();

    const labels = Object.keys(allocData).filter(key => allocData[key] > 0);
    const data = labels.map(key => allocData[key]);

    allocChartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: [
                    '#38bdf8', // US Equity (Blue)
                    '#10b981', // MXN Equity (Green)
                    '#a855f7', // Crypto (Purple)
                    '#f59e0b', // Commodities (Orange)
                    '#64748b'  // Cash/Sweep (Slate Gray)
                ],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: '#94a3b8', font: { family: 'Outfit', size: 12 } }
                }
            },
            cutout: '70%'
        }
    });
}

// Fetch historical NAV values from watchdog_nav_history.json
async function loadNavChartData() {
    try {
        const res = await fetch("watchdog_nav_history.json");
        if (!res.ok) return;
        const history = await res.json();

        // Aggregate NAV by date
        const dateNavs = {};
        Object.keys(history).forEach(stratKey => {
            const points = history[stratKey];
            const rate = ["strategy4", "alternatives", "high_beta", "portfolio_us_dcs", "portfolio_alternatives", "portfolio_high_beta"].includes(stratKey) ? FX_RATE : 1.0;
            points.forEach(pt => {
                const date = pt.ts.split(" ")[0]; // YYYY-MM-DD
                if (!dateNavs[date]) dateNavs[date] = 0;
                dateNavs[date] += pt.nav * rate;
            });
        });

        const sortedDates = Object.keys(dateNavs).sort();
        const chartData = sortedDates.map(d => dateNavs[d]);

        const ctx = document.getElementById("navChart").getContext("2d");
        if (navChartInstance) navChartInstance.destroy();

        navChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: sortedDates,
                datasets: [{
                    label: 'Consolidated Portfolio NAV (MXN)',
                    data: chartData,
                    borderColor: '#10b981',
                    borderWidth: 2.5,
                    backgroundColor: 'rgba(16, 185, 129, 0.05)',
                    fill: true,
                    tension: 0.35,
                    pointRadius: 3,
                    pointHoverRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: { color: '#64748b', font: { family: 'Outfit' } }
                    },
                    y: {
                        grid: { color: 'rgba(255, 255, 255, 0.03)' },
                        ticks: { 
                            color: '#64748b', 
                            font: { family: 'Outfit' },
                            callback: function(value) {
                                return '$' + (value/1000) + 'k';
                            }
                        }
                    }
                }
            }
        });
    } catch (e) {
        console.error("Could not render NAV chart:", e);
    }
}
