# 🇲🇽 Mexican Value Stock Evaluation Pipeline (DAG)

A deterministic, pipeline-driven Directed Acyclic Graph (DAG) for deep-value investment analysis and portfolio tracking within the Mexican equity market (Bolsa Mexicana de Valores - BMV).

---

## 1. System Architecture

The project separates stateless computational calculations (Skills Layer) from analytical reasoning (Agents Layer) to prevent model hallucinations:

```
[Live Data Ingestion] (yfinance → S&P/BMV IPC)
          │
          ▼
[Skills Layer (Python Compute)]
  ├── Liquidity Gatekeeper (ADTV filter)
  ├── Ratio Calculator (PE, PB, EV/EBITDA)
  └── DCF Valuation Engine (Multi-stage FCFF)
          │
          ▼
[Agents Layer (Deterministic DAG Orchestration)]
  ├── 1. Fundamental Screener (Anonymized Blind Screen)
  ├── 2. Macro Risk Analyst (Sector-based Risk Discounting)
  └── 3. Portfolio Reconciler (De-anonymization & Position Sizing)
          │
          ▼
[Execution & Monitoring]
  ├── Execution Order Blotter
  ├── Exit & Take-Profit Triggers
  └── Live Portfolio Tracker
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
├── pipeline_orchestrator.py   # Sequential DAG driver
├── run.py                     # Simulated prototype entrypoint
├── ingest_live_bmv.py         # Live S&P/BMV IPC ingestion & evaluation
├── monitor_portfolio.py       # Tracks P/L and triggers sell flags
├── app.py                     # Dashboard backend (Flask)
├── index.html / .css / .js    # Glassmorphic dashboard frontend
├── portfolio.json             # Current holdings (20K MXN paper trading)
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

### 2. Ingest & Analyze Live BMV Index
Fetches the S&P/BMV IPC components in real-time, filters, stress-tests, and outputs target shares + sell triggers:
```bash
python ingest_live_bmv.py
```
**Output:** `mexican_value_equity_report_live.md`

### 3. Track Active Portfolio Positions
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

The workflow in `.github/workflows/monitor.yml` runs **Monday–Friday at 4:30 PM Mexico City time** (22:30 UTC):

1. **Portfolio Monitor** — updates P/L, checks exit triggers
2. **Live BMV Screener** — re-evaluates all IPC components for new opportunities
3. **Auto-commit** — pushes updated reports back to this repo

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

## 6. Paper Trading Portfolio

Currently paper trading with **20,000 MXN**. See `portfolio.json` for live holdings and `transactions.md` for the full ledger.

---

*Built with an agentic DAG architecture — no LLM hallucinations in the math layer.*
