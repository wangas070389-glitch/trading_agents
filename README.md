# Trading Agents — Paper-Trading Research Platform

A multi-strategy paper-trading and research platform for Mexican and US
equities, ETFs, alternatives, and portfolio allocation. It is not an order
execution system and must not be treated as investment advice.

---

## 1. System Architecture

The project separates stateless computational calculations (Skills Layer) from analytical reasoning (Agents Layer) to prevent model hallucinations:

```
[Live Data Ingestion] (yfinance / broker APIs → BMV, US equities, ETFs)
          │
          ▼
[Skills Layer (Python Compute)]
  ├── Liquidity Gatekeeper (ADTV filter)
  ├── Ratio Calculator (PE, PB, EV/EBITDA)
  └── DCF Valuation Engine (Multi-stage FCFF)
          │
          ▼
[Strategy Layer]
  ├── Fundamental, momentum, technical, statistical-arbitrage, and ML sleeves
  ├── Independent paper portfolios and transaction ledgers
  └── Multi-strategy and efficient-frontier aggregation
          │
          ▼
[Monitoring & Governance]
  ├── Paper-trading transaction blotters and portfolio snapshots
  ├── Watchdog, broker reconciliation, graduation reports, and kill criteria
  └── Local dashboard
```

---

## 2. Directory Structure

```
trading_agents/
├── .github/workflows/
│   └── monitor.yml            # GitHub Actions: automated daily pipeline
├── skills/                    # Stateless compute modules
│   ├── liquidity_gatekeeper.py
│   ├── fundamental_ratio_calculator.py
│   └── dcf_valuation_engine.py
├── agents/                    # Agent templates and orchestration logic
│   └── agents.py
├── connectors/                # Data ingestion modules
│   └── mock_data_connector.py
├── strategy_registry.py       # Canonical scheduled-runner registry
├── scheduler.py               # Local scheduler with a fail-closed run lock
├── run.py                     # Simulated prototype entrypoint
├── ingest_live_bmv.py         # Live S&P/BMV IPC ingestion & evaluation
├── monitor_portfolio.py       # Tracks P/L and triggers sell flags
├── app.py                     # Dashboard backend (Flask)
├── index.html / .css / .js    # Glassmorphic dashboard frontend
├── portfolio*.json            # Per-strategy paper portfolio snapshots
├── portfolio_status.md        # Auto-generated monitoring report
├── transactions.md            # Paper trading ledger
├── agents_config.md           # Agent system configurations
└── requirements.txt           # Python dependencies
```

---

## 3. How to Run

### Installation

```bash
pip install -r requirements.txt
```

### 1. Run Simulated Prototype
Runs mock filings data to test filter and value-trap rejections:
```bash
python run.py
```
**Output:** `mexican_value_equity_report.md`

### 2. Run an individual BMV strategy
Fetches the S&P/BMV IPC components in real-time, filters, stress-tests, and outputs target shares + sell triggers:
```bash
python ingest_live_bmv.py
```
**Output:** `mexican_value_equity_report_live.md`

### 3. Track the core paper portfolio
Loads holdings from `portfolio.json`, updates prices, calculates unrealized P/L, and flags take-profit or scale-out targets:
```bash
python monitor_portfolio.py
```
**Output:** `portfolio_status.md`

### 4. Launch Dashboard (Local)
Serves a glassmorphic real-time dashboard on `http://localhost:5001`:
```bash
python app.py
```

---

## 4. Automated GitHub Actions Pipeline

The workflow in `.github/workflows/monitor.yml` queues market-hour runs rather
than allowing overlap. It installs dependencies, runs the full test suite, and
then runs the paper-trading pipeline.

1. **Portfolio and strategy runners** — update paper state and reports
2. **Comparison, graduation, and watchdog reports** — check evidence and books
3. **Generated-artifact commit** — only after tests pass; source changes stay human-reviewed

You can also trigger it manually from the **Actions** tab.

---

## 5. Key Sizing and Exit Rules

| Rule | Value |
|------|-------|
| **Concentration Limit** | Max 40% weight per stock |
| **Opening Target** | ≥30% capital allocation, rest in cash |
| **Take-Profit Exit** | GTC limit sell at 100% of Intrinsic Value |
| **Scale-Out Exit** | Sell 50% at 90% of Intrinsic Value |
| **Stop-Loss Trigger** | Liquidate if recalculated IV < acquisition cost |

---

## 6. Operating Safely

`KILL_CRITERIA.md` is the binding policy for allocations and demotions.
`watchdog.py` is audit-only: a critical finding must be investigated and a
human must create or clear a `HALT_<strategy>.flag` before an affected runner
is resumed. The pipeline lock is intentionally not self-healing; if it remains
after an interruption, inspect the previous run before removing it.

---

## 7. Current Design Limits

- State remains file-backed; the JSON and Markdown artifacts are operational
  records, not a transactional broker ledger.
- Strategies have varied levels of out-of-sample and live-paper evidence.
  `graduation_report.md` is the authoritative readiness view.
- The dashboard binds locally by default. Do not expose it to a network without
  authentication and a proper production server.
