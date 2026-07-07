const STRATEGY_METADATA = {
    "S1": { name: "Adaptive Value", file: "portfolio.json", tx_file: "transactions.md", currency: "MXN", active: true, assets: "BMV IPC Leaders", cagr: "20.07%", sharpe: "0.82", maxdd: "-28.18%" },
    "S2": { name: "1d MACD Systematic", file: "portfolio_macd.json", tx_file: "transactions_macd.md", currency: "MXN", active: true, assets: "BMV Leaders + SIC", cagr: "13.10%", sharpe: "1.27", maxdd: "-10.94%" },
    "S3": { name: "US Stock Momentum", file: "portfolio_us_stocks.json", tx_file: "transactions_us_stocks.md", currency: "USD", active: false, assets: "US Large Cap Tech", cagr: "25.40%", sharpe: "1.15", maxdd: "-18.20%" },
    "S4": { name: "US DCS Value-Growth", file: "portfolio_us_dcs.json", tx_file: "transactions_us_dcs.md", currency: "USD", active: true, assets: "US Growth Leaders", cagr: "21.93%", sharpe: "1.14", maxdd: "-12.19%" },
    "S5": { name: "Alternative Assets", file: "portfolio_alternatives.json", tx_file: "transactions_alternatives.md", currency: "USD", active: true, assets: "BTC, ETH, Gold, USO", cagr: "18.40%", sharpe: "0.95", maxdd: "-15.20%" },
    "S6": { name: "High-Beta Momentum", file: "portfolio_high_beta.json", tx_file: "transactions_high_beta.md", currency: "USD", active: true, assets: "High Beta Tech Stocks", cagr: "22.10%", sharpe: "1.05", maxdd: "-19.50%" },
    "S8": { name: "Dividend Quality & Yield", file: "portfolio_dividends.json", tx_file: "transactions_dividends.md", currency: "MXN", active: true, assets: "FIBRAS + MX Dividends", cagr: "14.50%", sharpe: "1.12", maxdd: "-11.20%" },
    "S9": { name: "AI Regime Stat-Arb", file: "portfolio_strategy9.json", tx_file: "transactions_strategy9.md", currency: "MXN", active: true, assets: "BMV Cointegrated Pairs", cagr: "26.80%", sharpe: "1.45", maxdd: "-7.50%" },
    "S10": { name: "AI Intraday VWAP", file: "portfolio_strategy10.json", tx_file: "transactions_strategy10.md", currency: "MXN", active: true, assets: "TQQQ, SQQQ, QQQ", cagr: "53.25%", sharpe: "2.73", maxdd: "-4.14%" },
    "S11": { name: "AI Intraday CCI-ADX", file: "portfolio_strategy11.json", tx_file: "transactions_strategy11.md", currency: "MXN", active: true, assets: "TQQQ, SQQQ, QQQ", cagr: "11.88%", sharpe: "0.10", maxdd: "-16.31%" },
    "S12": { name: "Vol-Targeted Trend (VTTL)", file: "portfolio_strategy12.json", tx_file: "transactions_strategy12.md", currency: "MXN", active: true, assets: "TQQQ + BONDIA", cagr: "17.13%", sharpe: "0.46", maxdd: "-21.34%" },
    "S13": { name: "Risk Appetite (CARA)", file: "portfolio_strategy13.json", tx_file: "transactions_strategy13.md", currency: "MXN", active: false, assets: "TQQQ + BONDIA", cagr: "15.95%", sharpe: "0.45", maxdd: "-25.02%" },
    "S14": { name: "Aggregator (HEDGE)", file: "portfolio_strategy14.json", tx_file: "transactions_strategy14.md", currency: "MXN", active: true, assets: "S12, S13 + BONDIA", cagr: "15.17%", sharpe: "0.53", maxdd: "-15.19%" },
    "S15": { name: "Tracker (TRACK)", file: "portfolio_strategy15.json", tx_file: "transactions_strategy15.md", currency: "MXN", active: true, assets: "S12, S13 + BONDIA", cagr: "15.05%", sharpe: "0.53", maxdd: "-14.73%" }
};

const FX_RATE = 20.0;
let cachedPortfolios = {};
let cachedHistory = null;
let parsedTransactions = [];

let navChartInstance = null;
let allocChartInstance = null;
let txNavChartInstance = null;

document.addEventListener("DOMContentLoaded", () => {
    initializeNavigation();
    loadDashboardData();
    checkHaltStatus();
});

// Setup tab navigation and filter dropdown listeners
function initializeNavigation() {
    const tabDashboard = document.getElementById("tab-dashboard");
    const tabTransactions = document.getElementById("tab-transactions");
    const dashboardView = document.getElementById("dashboard-view");
    const transactionsView = document.getElementById("transactions-view");

    tabDashboard.addEventListener("click", () => {
        tabDashboard.classList.add("active");
        tabTransactions.classList.remove("active");
        dashboardView.classList.remove("hidden");
        transactionsView.classList.add("hidden");
    });

    tabTransactions.addEventListener("click", () => {
        tabTransactions.classList.add("active");
        tabDashboard.classList.remove("active");
        transactionsView.classList.remove("hidden");
        dashboardView.classList.add("hidden");
        loadTransactionsData();
    });

    const strategySelect = document.getElementById("strategy-select");
    strategySelect.addEventListener("change", () => {
        const selected = strategySelect.value;
        updateUIForSelectedStrategy(selected);
        if (!transactionsView.classList.contains("hidden")) {
            loadTransactionsData();
        }
    });

    const searchInput = document.getElementById("tx-search");
    searchInput.addEventListener("input", () => {
        filterTransactionsTable(searchInput.value.toLowerCase());
    });
}

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
            if (!res.ok) throw new Error("Not found");
            const data = await res.json();
            return { key, data, success: true };
        } catch (e) {
            return { key, success: false };
        }
    });

    const results = await Promise.all(promises);
    results.forEach(res => {
        if (res.success) {
            cachedPortfolios[res.key] = res.data;
        }
    });

    // Load history once
    try {
        const historyRes = await fetch("watchdog_nav_history.json");
        if (historyRes.ok) {
            cachedHistory = await historyRes.json();
        }
    } catch (e) {
        console.error("Failed history fetch:", e);
    }

    // Default: update UI with ALL consolidated
    updateUIForSelectedStrategy("ALL");
}

function updateUIForSelectedStrategy(selected) {
    let navMxn = 0;
    let cashMxn = 0;
    let investedMxn = 0;
    
    const combinedPositions = [];
    const allocationClasses = {
        "US Equity": 0,
        "MXN Equity": 0,
        "Crypto": 0,
        "Commodities": 0,
        "Cash/Sweep": 0
    };

    const strategiesGrid = document.getElementById("strategies-card-grid");
    
    // UI Label Overrides
    const kpiNavLabel = document.getElementById("kpi-nav-label");
    const kpiCashLabel = document.getElementById("kpi-cash-label");
    const kpiInvestedLabel = document.getElementById("kpi-invested-label");
    const kpiTwrLabel = document.getElementById("kpi-twr-label");

    if (selected === "ALL") {
        kpiNavLabel.textContent = "Valor Neto Consolidado";
        kpiCashLabel.textContent = "Efectivo Sweep";
        kpiInvestedLabel.textContent = "Capital Invertido";
        kpiTwrLabel.textContent = "Retorno Compuesto (TWR)";
        document.getElementById("metric-twr").textContent = "+15.63%";
        document.getElementById("metric-twr-sub").textContent = "Ponderación S7";
        strategiesGrid.parentNode.style.display = "block"; // Show detail grid
    } else {
        const meta = STRATEGY_METADATA[selected];
        kpiNavLabel.textContent = `NAV actual de ${selected}`;
        kpiCashLabel.textContent = `Efectivo en ${selected}`;
        kpiInvestedLabel.textContent = `Capital Invertido ${selected}`;
        kpiTwrLabel.textContent = "Rendimiento Estimado (CAGR)";
        document.getElementById("metric-twr").textContent = meta.cagr;
        document.getElementById("metric-twr-sub").textContent = `Riesgo (Sharpe: ${meta.sharpe})`;
        strategiesGrid.parentNode.style.display = "none"; // Hide detail grid when focused
    }

    const targetStrategies = selected === "ALL" ? Object.keys(STRATEGY_METADATA) : [selected];

    targetStrategies.forEach(key => {
        const metadata = STRATEGY_METADATA[key];
        const data = cachedPortfolios[key];
        if (!data) return;

        const rate = metadata.currency === "USD" ? FX_RATE : 1.0;
        const cashVal = data.cash_balance || 0;
        const navVal = data.total_capital || data.total_portfolio_value || cashVal;
        const investedVal = navVal - cashVal;

        navMxn += navVal * rate;
        cashMxn += cashVal * rate;
        investedMxn += investedVal * rate;

        allocationClasses["Cash/Sweep"] += cashVal * rate;

        if (data.holdings) {
            data.holdings.forEach(pos => {
                const shares = pos.shares || 0;
                const buyPrice = pos.buy_price || pos.average_price || 0;
                const lastPrice = pos.last_price || pos.current_price || buyPrice;
                const value = shares * lastPrice;
                const valueMxn = value * rate;

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
    });

    // Update top labels
    document.getElementById("metric-net-val").textContent = `$${navMxn.toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} MXN`;
    document.getElementById("metric-net-val-usd").textContent = `$${(navMxn / FX_RATE).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} USD`;
    
    document.getElementById("metric-cash").textContent = `$${cashMxn.toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} MXN`;
    const cashPct = navMxn > 0 ? (cashMxn / navMxn) * 100 : 0;
    document.getElementById("metric-cash-pct").textContent = `${cashPct.toFixed(1)}% del valor total (${selected === "ALL" ? 'BONDIA/USD' : STRATEGY_METADATA[selected].currency === "USD" ? 'USD Cash' : 'BONDIA'})`;

    document.getElementById("metric-invested").textContent = `$${investedMxn.toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} MXN`;
    const investedPct = navMxn > 0 ? (investedMxn / navMxn) * 100 : 0;
    document.getElementById("metric-invested-pct").textContent = `${investedPct.toFixed(1)}% del valor total`;

    // Render Holdings
    const tableBody = document.getElementById("positions-table-body");
    tableBody.innerHTML = "";
    if (combinedPositions.length === 0) {
        tableBody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-secondary);">No hay posiciones activas en la estrategia seleccionada.</td></tr>`;
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

    if (selected === "ALL") {
        renderStrategiesGrid();
    }

    renderAllocationChart(allocationClasses);
    renderNAVChart(selected);
}

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

function renderStrategiesGrid() {
    const strategiesGrid = document.getElementById("strategies-card-grid");
    strategiesGrid.innerHTML = "";

    Object.keys(STRATEGY_METADATA).forEach(key => {
        const metadata = STRATEGY_METADATA[key];
        const data = cachedPortfolios[key];
        
        let nav = 0;
        let roi = "0.00%";
        let lastUpdated = "Inactivo";
        let statusClass = metadata.active ? "active" : "suspended";

        if (data) {
            const cash = data.cash_balance || 0;
            nav = data.total_capital || data.total_portfolio_value || cash;
            lastUpdated = data.last_updated || "Hoy";

            const initial = metadata.currency === "USD" ? 100000.0 : 200000.0;
            const profit = nav - initial;
            roi = `${profit >= 0 ? "+" : ""}${((profit / initial) * 100).toFixed(2)}%`;
        }

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
}

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
                    '#38bdf8', // US Equity
                    '#10b981', // MXN Equity
                    '#a855f7', // Crypto
                    '#f59e0b', // Commodities
                    '#64748b'  // Cash
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
                    labels: { color: '#94a3b8', font: { family: 'Outfit', size: 11 } }
                }
            },
            cutout: '70%'
        }
    });
}

function renderNAVChart(selected) {
    if (!cachedHistory) return;
    const ctx = document.getElementById("navChart").getContext("2d");
    if (navChartInstance) navChartInstance.destroy();

    const chartTitle = document.getElementById("chart-nav-title");
    
    if (selected === "ALL") {
        chartTitle.textContent = "Evolución del NAV Consolidado General (MXN)";
        const dateNavs = {};
        Object.keys(cachedHistory).forEach(stratKey => {
            const points = cachedHistory[stratKey];
            const isUsd = ["us_dcs", "us_stocks", "alternatives", "high_beta"].includes(stratKey);
            const rate = isUsd ? FX_RATE : 1.0;
            points.forEach(pt => {
                const date = pt.ts.split(" ")[0];
                if (!dateNavs[date]) dateNavs[date] = 0;
                dateNavs[date] += pt.nav * rate;
            });
        });

        const sortedDates = Object.keys(dateNavs).sort();
        const values = sortedDates.map(d => dateNavs[d]);

        navChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: sortedDates,
                datasets: [{
                    label: 'NAV Total Consolidado (MXN)',
                    data: values,
                    borderColor: '#10b981',
                    borderWidth: 2,
                    backgroundColor: 'rgba(16, 185, 129, 0.05)',
                    fill: true,
                    tension: 0.35,
                    pointRadius: 2
                }]
            },
            options: getChartOptions(selected)
        });
    } else {
        chartTitle.textContent = `Evolución del NAV de ${selected} vs. S14 (HEDGE)`;
        const mapKeyMap = {
            "S1": "core",
            "S2": "macd",
            "S3": "us_stocks",
            "S4": "us_dcs",
            "S5": "alternatives",
            "S6": "high_beta",
            "S8": "dividends",
            "S9": "strategy9",
            "S10": "strategy10",
            "S11": "strategy11",
            "S12": "strategy12",
            "S13": "strategy13",
            "S14": "strategy14",
            "S15": "strategy15"
        };
        const mappedKey = mapKeyMap[selected] || selected.toLowerCase();
        const selectedPoints = cachedHistory[mappedKey] || [];
        const hedgePoints = cachedHistory["strategy14"] || [];

        const dateNavSelected = {};
        selectedPoints.forEach(pt => {
            const date = pt.ts.split(" ")[0];
            dateNavSelected[date] = pt.nav;
        });

        const dateNavHedge = {};
        hedgePoints.forEach(pt => {
            const date = pt.ts.split(" ")[0];
            dateNavHedge[date] = pt.nav;
        });

        const allDatesSet = new Set([...Object.keys(dateNavSelected), ...Object.keys(dateNavHedge)]);
        const sortedDates = Array.from(allDatesSet).sort();

        const selectedValues = sortedDates.map(d => dateNavSelected[d] || null);
        const hedgeValues = sortedDates.map(d => dateNavHedge[d] || null);

        const currency = STRATEGY_METADATA[selected].currency;

        navChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: sortedDates,
                datasets: [
                    {
                        label: `${selected} NAV (${currency})`,
                        data: selectedValues,
                        borderColor: '#0ea5e9',
                        borderWidth: 2,
                        fill: false,
                        tension: 0.35,
                        pointRadius: 3
                    },
                    {
                        label: `S14: HEDGE (MXN)`,
                        data: hedgeValues,
                        borderColor: '#64748b',
                        borderWidth: 1.5,
                        borderDash: [5, 5],
                        fill: false,
                        tension: 0.35,
                        pointRadius: 0
                    }
                ]
            },
            options: getChartOptions(selected)
        });
    }
}

function getChartOptions(selected) {
    const currency = selected === "ALL" ? "MXN" : STRATEGY_METADATA[selected].currency;
    return {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { 
                display: true, 
                position: 'top',
                labels: { color: '#94a3b8', font: { family: 'Outfit', size: 11 } }
            }
        },
        scales: {
            x: {
                grid: { display: false },
                ticks: { color: '#64748b', font: { family: 'Outfit', size: 10 } }
            },
            y: {
                grid: { color: 'rgba(255, 255, 255, 0.03)' },
                ticks: { 
                    color: '#64748b', 
                    font: { family: 'Outfit', size: 10 },
                    callback: function(value) {
                        return value >= 1000 ? '$' + (value/1000).toFixed(0) + 'k ' + currency : '$' + value + ' ' + currency;
                    }
                }
            }
        }
    };
}

// Transactions Ledger parser
async function loadTransactionsData() {
    const selected = document.getElementById("strategy-select").value;
    const tableBody = document.getElementById("transactions-table-body");
    tableBody.innerHTML = `<tr><td colspan="10" style="text-align: center; color: var(--text-secondary);">Descargando bitácora de transacciones...</td></tr>`;

    const targetStrategies = selected === "ALL" ? Object.keys(STRATEGY_METADATA) : [selected];
    parsedTransactions = [];

    const promises = targetStrategies.map(async (key) => {
        const metadata = STRATEGY_METADATA[key];
        try {
            const res = await fetch(metadata.tx_file);
            if (!res.ok) return;
            const text = await res.text();
            
            const lines = text.split("\n");
            lines.forEach(line => {
                if (line.trim().startsWith("|") && !line.includes("Action") && !line.includes("---")) {
                    const cols = line.split("|").map(col => col.trim());
                    if (cols.length >= 10 && cols[1] && cols[1] !== "") {
                        parsedTransactions.push({
                            date: cols[1],
                            ticker: cols[2],
                            strategy: key,
                            action: cols[3],
                            shares: cols[4],
                            price: cols[5],
                            netImpact: cols[6],
                            orderType: cols[7],
                            status: cols[8],
                            note: cols[9] || "-"
                        });
                    }
                }
            });
        } catch (e) {
            console.error(`Failed transaction load for ${key}:`, e);
        }
    });

    await Promise.all(promises);

    parsedTransactions.sort((a, b) => b.date.localeCompare(a.date));

    // Render Table and Interactive Execution Point Chart
    renderTransactionsTable(parsedTransactions);
    renderTxNavChart(selected);
}

function renderTransactionsTable(txs) {
    const tableBody = document.getElementById("transactions-table-body");
    tableBody.innerHTML = "";

    if (txs.length === 0) {
        tableBody.innerHTML = `<tr><td colspan="10" style="text-align: center; color: var(--text-secondary);">No se encontraron transacciones registradas para este filtro.</td></tr>`;
        return;
    }

    txs.forEach(tx => {
        const tr = document.createElement("tr");
        let opClass = "badge-usd";
        if (tx.action === "BUY") opClass = "badge-strat";
        else if (tx.action === "SELL") opClass = "badge";

        tr.innerHTML = `
            <td>${tx.date}</td>
            <td><strong>${tx.ticker}</strong></td>
            <td><span class="badge badge-strat">${tx.strategy}</span></td>
            <td><span class="badge ${opClass}">${tx.action}</span></td>
            <td>${tx.shares}</td>
            <td>${tx.price}</td>
            <td><strong>${tx.netImpact}</strong></td>
            <td>${tx.orderType}</td>
            <td><span class="value-up">${tx.status}</span></td>
            <td style="font-size:0.8rem; color:var(--text-secondary); max-width:250px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${tx.note}">${tx.note}</td>
        `;
        tableBody.appendChild(tr);
    });
}

function filterTransactionsTable(query) {
    if (!query) {
        renderTransactionsTable(parsedTransactions);
        return;
    }

    const filtered = parsedTransactions.filter(tx => {
        return tx.ticker.toLowerCase().includes(query) || 
               tx.action.toLowerCase().includes(query) ||
               tx.strategy.toLowerCase().includes(query) ||
               tx.note.toLowerCase().includes(query) ||
               tx.date.includes(query);
    });

    renderTransactionsTable(filtered);
}

// Render the new trades execution-point NAV chart in the transactions view with continuous daily dates and fluctuations
function renderTxNavChart(selected) {
    if (!cachedHistory) return;
    const ctx = document.getElementById("txNavChart").getContext("2d");
    if (txNavChartInstance) txNavChartInstance.destroy();

    const txChartTitle = document.getElementById("tx-chart-title");
    
    // Group transactions by date for point annotations
    const dateTxs = {};
    parsedTransactions.forEach(tx => {
        const date = tx.date;
        if (!dateTxs[date]) dateTxs[date] = [];
        dateTxs[date].push(tx);
    });

    const dateNavsMap = {};
    const currency = selected === "ALL" ? "MXN" : STRATEGY_METADATA[selected].currency;

    if (selected === "ALL") {
        const dateNavs = {};
        Object.keys(cachedHistory).forEach(stratKey => {
            const points = cachedHistory[stratKey];
            const isUsd = ["us_dcs", "us_stocks", "alternatives", "high_beta"].includes(stratKey);
            const rate = isUsd ? FX_RATE : 1.0;
            points.forEach(pt => {
                const date = pt.ts.split(" ")[0];
                if (!dateNavs[date]) dateNavs[date] = 0;
                dateNavs[date] += pt.nav * rate;
            });
        });
        Object.assign(dateNavsMap, dateNavs);
    } else {
        const mapKeyMap = {
            "S1": "core", "S2": "macd", "S3": "us_stocks", "S4": "us_dcs",
            "S5": "alternatives", "S6": "high_beta", "S8": "dividends",
            "S9": "strategy9", "S10": "strategy10", "S11": "strategy11", "S12": "strategy12",
            "S13": "strategy13", "S14": "strategy14", "S15": "strategy15"
        };
        const mappedKey = mapKeyMap[selected] || selected.toLowerCase();
        const selectedPoints = cachedHistory[mappedKey] || [];
        selectedPoints.forEach(pt => {
            const date = pt.ts.split(" ")[0];
            dateNavsMap[date] = pt.nav;
        });
    }

    const rawDates = Object.keys(dateNavsMap).sort();
    if (rawDates.length === 0) return;

    // Generate continuous date range
    const minDateStr = rawDates[0];
    const maxDateStr = rawDates[rawDates.length - 1];
    
    function generateDateRange(minD, maxD) {
        const dates = [];
        let curr = new Date(minD + "T00:00:00");
        const end = new Date(maxD + "T00:00:00");
        while (curr <= end) {
            dates.push(curr.toISOString().split("T")[0]);
            curr.setDate(curr.getDate() + 1);
        }
        return dates;
    }
    const allDates = generateDateRange(minDateStr, maxDateStr);

    // Forward fill NAV values for missing dates (e.g. weekends)
    let lastKnownNav = 0;
    const continuousNavs = [];
    const dailyChanges = [];

    allDates.forEach((date, index) => {
        if (dateNavsMap[date] !== undefined) {
            lastKnownNav = dateNavsMap[date];
        }
        continuousNavs.push(lastKnownNav);
        
        if (index === 0) {
            dailyChanges.push(0);
        } else {
            dailyChanges.push(continuousNavs[index] - continuousNavs[index - 1]);
        }
    });

    // Color definitions for bars
    const barColors = dailyChanges.map(change => change >= 0 ? 'rgba(16, 185, 129, 0.25)' : 'rgba(239, 68, 68, 0.25)');
    const barBorderColors = dailyChanges.map(change => change >= 0 ? '#10b981' : '#ef4444');

    // Build transaction highlights
    const pointRadii = [];
    const pointColors = [];
    const pointStyles = [];

    allDates.forEach(date => {
        const dayTxs = dateTxs[date];
        if (dayTxs && dayTxs.length > 0) {
            pointRadii.push(7);
            const hasBuy = dayTxs.some(t => t.action === "BUY");
            const hasSell = dayTxs.some(t => t.action === "SELL");

            if (hasBuy && hasSell) {
                pointColors.push('#f59e0b');
                pointStyles.push('rectRot');
            } else if (hasBuy) {
                pointColors.push('#10b981');
                pointStyles.push('triangle');
            } else if (hasSell) {
                pointColors.push('#ef4444');
                pointStyles.push('rectRot');
            } else {
                pointColors.push('#0ea5e9');
                pointStyles.push('circle');
            }
        } else {
            pointRadii.push(0);
            pointColors.push('transparent');
            pointStyles.push('circle');
        }
    });

    if (selected === "ALL") {
        txChartTitle.textContent = "Historial Consolidado: NAV General y Puntos de Ejecución (Trades)";
    } else {
        txChartTitle.textContent = `Evolución de ${selected} y Puntos de Ejecución (Trades)`;
    }

    txNavChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: allDates,
            datasets: [
                {
                    type: 'line',
                    label: `NAV de Cartera (${currency})`,
                    data: continuousNavs,
                    borderColor: '#38bdf8',
                    borderWidth: 2,
                    fill: false,
                    tension: 0.25,
                    pointRadius: pointRadii,
                    pointBackgroundColor: pointColors,
                    pointBorderColor: pointColors,
                    pointStyle: pointStyles,
                    pointHoverRadius: 9,
                    yAxisID: 'y'
                },
                {
                    type: 'bar',
                    label: `Cambio Diario (${currency})`,
                    data: dailyChanges,
                    backgroundColor: barColors,
                    borderColor: barBorderColors,
                    borderWidth: 1,
                    yAxisID: 'yChange'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { 
                    display: true,
                    position: 'top',
                    labels: { color: '#94a3b8', font: { family: 'Outfit', size: 11 } }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const index = context.dataIndex;
                            const date = context.chart.data.labels[index];
                            const datasetIndex = context.datasetIndex;
                            
                            if (datasetIndex === 0) {
                                const nav = context.raw;
                                let label = `NAV: $${nav.toLocaleString("es-MX", {minimumFractionDigits: 2})} ${currency}`;
                                if (dateTxs[date]) {
                                    const list = dateTxs[date].map(t => `${t.action} ${t.ticker} (${t.shares} shrs)`).join(' | ');
                                    label += ` [Trades: ${list}]`;
                                }
                                return label;
                            } else {
                                const change = context.raw;
                                return `Cambio Diario: ${change >= 0 ? '+' : ''}$${change.toLocaleString("es-MX", {minimumFractionDigits: 2})} ${currency}`;
                            }
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { color: '#64748b', font: { family: 'Outfit', size: 10 } }
                },
                y: {
                    type: 'linear',
                    position: 'left',
                    grid: { color: 'rgba(255, 255, 255, 0.03)' },
                    ticks: { color: '#38bdf8', font: { family: 'Outfit', size: 10 } }
                },
                yChange: {
                    type: 'linear',
                    position: 'right',
                    grid: { drawOnChartArea: false },
                    ticks: { color: '#10b981', font: { family: 'Outfit', size: 10 } }
                }
            }
        }
    });
}


