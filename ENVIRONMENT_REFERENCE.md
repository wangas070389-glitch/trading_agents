# Trading Agents Suite — Complete Environment Reference

**Version:** July 2026 | **Platform:** Windows (PowerShell) | **Language:** Python 3.11
**Repository:** `wangas070389-glitch/trading_agents` (GitHub)
**Local path:** `c:\Users\wanga\OneDrive\Escritorio\Antigravity-projects\trading_agents`

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture Diagram](#2-architecture-diagram)
3. [Strategy Catalog](#3-strategy-catalog)
4. [Infrastructure Layer](#4-infrastructure-layer)
5. [Live Execution Pipeline](#5-live-execution-pipeline)
6. [Dashboard](#6-dashboard)
7. [Risk & Safety Systems](#7-risk--safety-systems)
8. [Portfolio State (Current)](#8-portfolio-state-current)
9. [Dependencies & Environment Setup](#9-dependencies--environment-setup)
10. [File Reference Map](#10-file-reference-map)
11. [Optimization History](#11-optimization-history)
12. [Known Issues & Operational Notes](#12-known-issues--operational-notes)
13. [CI/CD & Git Workflow](#13-cicd--git-workflow)

---

## 1. System Overview

The Trading Agents Suite is a **paper-trading simulation and research platform** that manages a diversified portfolio of algorithmic trading strategies operating across Mexican and U.S. equity markets. All positions are simulated in **Mexican Pesos (MXN)** via a USD/MXN conversion layer.

### Core Purpose
- Simulate a real multi-strategy portfolio with $200,000 MXN per sub-strategy
- Run live data ingestion and signal generation every 30 minutes during market hours
- Maintain full audit logs, transaction ledgers, and performance reports
- Provide a real-time web dashboard for monitoring

### Key Design Constraints
- **No real broker connection** for most strategies — pure paper trading via `yfinance` data
- **Exception:** Strategies S3/S4 use Alpaca paper trading API for realistic execution
- All strategies are denominated in **MXN**, with USD positions converted via live USD/MXN rate
- **Bondia yield** (Mexican overnight sweep rate, **6.53% APR** — `BONDIA_YIELD = 0.0653` in every live runner) is accrued on idle cash. Note: backtests use 9.5% only as the *risk-free rate for Sharpe calculations* (`rf_annual = 0.095`); do not confuse the two.

---

## 2. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                     TRADING AGENTS SUITE                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────┐    Every 30 min (Mon-Fri 08:30-15:00 CT)          │
│  │ scheduler.py│──► run_live_*.py scripts (16 strategies)          │
│  └─────────────┘         │                                         │
│                           ▼                                         │
│  ┌──────────────────────────────────────────────────────────┐      │
│  │              DATA LAYER (yfinance / Alpaca API)           │      │
│  │  SPY, QQQ, TQQQ, SQQQ, GLD, BTC, ETH, FX, BMV tickers  │      │
│  └──────────────────────────┬───────────────────────────────┘      │
│                              ▼                                      │
│  ┌──────────────────────────────────────────────────────────┐      │
│  │              SIGNAL & REGIME LAYER                        │      │
│  │  GaussianHMM (3-state) │ MACD │ CCI │ ADX │ VWAP │ SMA  │      │
│  └──────────────────────────┬───────────────────────────────┘      │
│                              ▼                                      │
│  ┌──────────────────────────────────────────────────────────┐      │
│  │              PORTFOLIO STATE LAYER                        │      │
│  │  portfolio_*.json files (one per strategy)               │      │
│  │  transactions_*.md (full audit ledger)                   │      │
│  │  *_report_live.md (narrative performance report)         │      │
│  └──────────────────────────┬───────────────────────────────┘      │
│                              ▼                                      │
│  ┌──────────────────────────────────────────────────────────┐      │
│  │              MONITORING & SAFETY LAYER                    │      │
│  │  watchdog.py (W1-W5 checks) │ halt_gate.py               │      │
│  │  HALT_*.flag (emergency kill-switch per strategy)        │      │
│  └──────────────────────────┬───────────────────────────────┘      │
│                              ▼                                      │
│  ┌──────────────────────────────────────────────────────────┐      │
│  │              REPORTING & DASHBOARD LAYER                  │      │
│  │  compare_strategies.py │ generate_clean_report.py        │      │
│  │  app.py (Dash web dashboard) @ localhost:8050            │      │
│  │  index.html (static dashboard alternative)               │      │
│  └──────────────────────────────────────────────────────────┘      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Strategy Catalog

### Active Intraday Strategies (optimized July 2026)

| ID | Name | Runner | Backtest | Timeframe | Signal | HMM | Assets | Cap (MXN) | Status |
|:---|:---|:---|:---|:---:|:---|:---:|:---|:---:|:---:|
| **S10** | VWAP Channel Breakout | `run_live_strategy10.py` | `backtest_strategy10.py` | **1h** | VWAP±1.0 ATR | ✅ 60d | TQQQ/SQQQ | 200k | ✅ Live |
| **S11** | CCI-ADX Mean Reversion | `run_live_strategy11.py` | `backtest_strategy11.py` | **1h** | CCI+ADX | ✅ 60d | TQQQ/SQQQ | 200k | ✅ Live |
| **S16** | MACD-HMM Swing Router | `run_live_strategy16.py` | `backtest_strategy16.py` | **1h** | MACD crossover | ✅ 60d | QQQ/SPY/SOXX/IWM 3x pairs | 200k | ✅ Live |

**Optimized July 2026:** All three moved from 30m → 1h bars, lookback fixed to 60 trading days (~420 1h bars), hybrid trailing stop (3.0→1.5 ATR after 1.5 ATR profit).

---

### Daily Regime Strategies

| ID | Name | Runner | Backtest | Timeframe | Signal | HMM | Assets | Cap (MXN) | Status |
|:---|:---|:---|:---|:---:|:---|:---:|:---|:---:|:---:|
| **S9** | AI Regime Stat-Arb | `run_live_strategy9.py` | `backtest_strategy9.py` | 1d | Bull/Bear/Chop routing | ✅ Full 5y | SPY/GLD/BTC/ETH/FX | 200k | ✅ Live |
| **S2/MACD** | MACD Systematic | `ingest_live_macd.py` | `backtest_macd.py` | 1d | MACD+SMA50 | ✅ Full 5y | 20-asset US universe | 200k | ✅ Live |
| **S12** | VTTL Trend+Vol | `run_live_strategy12.py` | `backtest_strategy12.py` | 1d | SMA200+vol targeting | ❌ | TQQQ | 200k | ✅ Live |
| **S13** | CARA Cross-Asset | `run_live_strategy13.py` | `backtest_strategy13.py` | 1d | VIX/credit/trend macro | ❌ | TQQQ | 200k | ✅ Live |
| **S14** | HEDGE Expert Aggregation | `run_live_strategy14.py` | `backtest_strategy14.py` | 1d | Multiplicative weights | ❌ | TQQQ/USD | 200k | ✅ Live |
| **S15** | TRACK Expert Tracking | `run_live_strategy15.py` | `backtest_strategy15.py` | 1d | Fixed-share weights | ❌ | TQQQ/USD | 200k | ✅ Live |

---

### Legacy / Long-Term Strategies

| ID | Name | Runner | Signal | Assets | Status |
|:---|:---|:---|:---|:---|:---:|
| **S1** | Alpha Growth (MXN Value) | `run_live_alpha_growth.py` | DCF+fundamental | BMV equities | ✅ Live |
| **S4/US-DCF** | US Stocks DCF | `run_live_alpaca_us_stocks_dcf.py` | DCF screening | US equities (Alpaca) | ✅ Live |
| **S5/ALT** | Alternatives | `run_live_alternatives.py` | Multi-asset allocation | Crypto/commodities/bonds | ✅ Live |
| **S6/HIGH-BETA** | High Beta | `run_live_high_beta.py` | Beta momentum | High-beta US ETFs | ✅ Live |
| **S8/DIV** | Dividend Quality | `run_live_dividends.py` | Dividend yield+growth | US dividend ETFs | ✅ Live |
| **S3** | Alpaca US Stocks | `run_live_alpaca_us_stocks.py` | Signal isolation | US stocks (Alpaca) | ⚠️ **SUSPENDED** |

> **S3 Note:** Suspended pending reconciliation of −$44,000 MXN margin discrepancy vs Alpaca paper account. Do not re-enable until investigation is complete.

---

### Strategy Performance Summary (as of 2026-07-08)

| Strategy | NAV (USD) | Return vs 200k MXN inception | Notes |
|:---|:---:|:---:|:---|
| S4 US-DCF | $101,483 | +0.1% | Near flat — stable |
| S5 Alternatives | $101,246 | +0.1% | Stable |
| S6 High Beta | $101,158 | +0.1% | Slight positive |
| S12 VTTL | $11,380 | Flat | Small allocation |
| S13 CARA | $11,380 | Flat | Small allocation |
| S14 HEDGE | $11,392 | Flat | Small allocation |
| S15 TRACK | $11,391 | Flat | Small allocation |
| S10 VWAP | $11,393 | Flat | Recently optimized |
| S11 CCI-ADX | $11,505 | Flat | Recently optimized |
| S9 Stat-Arb | $11,124 | −2% | Normal swing |
| S8 Dividends | $11,301 | Flat | |
| **Portfolio Total** | **$395,934** | **CAGR 24.4%** | **Sharpe 1.41** |

---

## 4. Infrastructure Layer

### 4.1 Scheduler (`scheduler.py`)

Controls live execution timing. Runs as a **background process**.

```
Schedule:  Mon–Fri, 08:30–15:00 machine LOCAL time (intended as Central Time;
           note CDMX is UTC-6 year-round vs US Central UTC-5 in summer)
Interval:  Every 30 minutes (aligns to :00 and :30 marks)
Timeout:   600 seconds per script (kills if hung)
Logging:   scheduler.log + scheduler_logs/<script>_<timestamp>.log
```

**Pipeline execution order (every 30-min cycle):**
1. `monitor_portfolio.py` — portfolio health check
2. `run_live_alpha_growth.py` — S1
3. `ingest_live_macd.py` — S2/MACD
4. ~~`run_live_alpaca_us_stocks.py`~~ — S3 (SUSPENDED)
5. `run_live_alpaca_us_stocks_dcf.py` — S4
6. `run_live_alternatives.py` — S5
7. `run_live_high_beta.py` — S6
8. `run_live_dividends.py` — S8
9. `run_live_strategy9.py` — S9
10. `run_live_strategy10.py` — S10
11. `run_live_strategy11.py` — S11
12. `run_live_strategy12.py` — S12
13. `run_live_strategy13.py` — S13
14. `run_live_strategy14.py` — S14
15. `run_live_strategy15.py` — S15
16. `run_live_strategy16.py` — S16
17. `run_live_multi_strategy.py` — Cross-strategy aggregator
18. `compare_strategies.py` — Generates comparison reports
19. `generate_clean_report.py` — Builds executive summary
20. `graduation_report.py` — Paper→live readiness scorecard
21. `watchdog.py` — Final safety audit

**To run the scheduler:**
```powershell
cd c:\Users\wanga\OneDrive\Escritorio\Antigravity-projects\trading_agents
python scheduler.py
# For immediate test run (all scripts once):
python scheduler.py --test
```

---

### 4.2 Watchdog (`watchdog.py`)

Audits all portfolios at the end of every scheduler cycle. **Audit-only:** the watchdog reports findings but does NOT write HALT flags or stop any strategy. Checks 5 failure modes:

| Code | Check | Trigger | Severity |
|:---:|:---|:---|:---:|
| **W1** | Staleness | `last_updated` ≥ 2 business days old | CRITICAL |
| **W2** | Zero-Trade | Strategy live ≥10 business days with 0 non-interest trades | CRITICAL (WARNING during 10-day grace) |
| **W3** | NAV Jump | Day-over-day NAV move above a dynamic cap based on actual exposure (`max(exposure × 3 × 12%, 3%)` per day) | CRITICAL |
| **W4** | Negative/NaN | Cash < 0, shares < 0, or NaN in JSON | CRITICAL |
| **W5** | DD Breaker | Live drawdown > 1.25× backtest MaxDD | CRITICAL |

Findings on inactive strategies (e.g. suspended S3) are downgraded to WARNING.

**Output:** `watchdog_report.md` + exit code 1 on CRITICAL (triggers GitHub Actions red build). No automatic halts.

---

### 4.3 Halt Gate (`halt_gate.py`)

**Manual** emergency kill-switch. HALT flags are created and removed by hand — the watchdog never writes them (audit-only). To halt a strategy, create `HALT_<strategy>.flag` in the repo root.

```python
# Pattern in runners that honor the flag:
from halt_gate import halted
if halted(dir_path, "strategy12"):
    return
```

**Coverage:** the flag is honored by S3, S4, S5, S6, S9, and S12–S15. The runners for **S1, S2 (ingest_live_macd), S8, S10, S11, S16, and the multi-strategy aggregator do NOT check halt flags** — to stop those, comment them out in `scheduler.py` / `.github/workflows/monitor.yml` (as was done for S3).

**Current active halts:** `HALT_us_stocks.flag` (S3 suspended — also commented out of the scheduler and workflow)

**To clear a halt:** Delete the `.flag` file after investigating the root cause.

---

### 4.4 Portfolio State Files

Each strategy maintains its own isolated portfolio JSON:

| File | Strategy | Key Fields |
|:---|:---|:---|
| `portfolio_strategy9.json` | S9 | cash_balance, holdings, last_updated |
| `portfolio_strategy10.json` | S10 | cash_balance, holdings, last_updated |
| `portfolio_strategy11.json` | S11 | cash_balance, holdings, last_updated |
| `portfolio_strategy12.json` | S12 | cash_balance, holdings, last_updated |
| `portfolio_strategy13.json` | S13 | cash_balance, holdings, last_updated |
| `portfolio_strategy14.json` | S14 | cash_balance, holdings, last_updated |
| `portfolio_strategy15.json` | S15 | cash_balance, holdings, last_updated |
| `portfolio_strategy16.json` | S16 | cash_balance, holdings, last_updated |
| `portfolio_multi_strategy.json` | Aggregate | Cross-strategy NAV history + weights |
| `portfolio_macd.json` | S2/MACD | cash_balance, holdings |
| `portfolio.json` | S1 Alpha Growth | cash_balance, holdings |
| `portfolio_us_stocks.json` | S3 (suspended) | cash_balance, holdings |
| `portfolio_us_dcs.json` | S4 US-DCF | cash_balance, holdings (note the `dcs` filename) |
| `portfolio_alternatives.json` | S5 | cash_balance, holdings |
| `portfolio_high_beta.json` | S6 | cash_balance, holdings |
| `portfolio_dividends.json` | S8 | cash_balance, holdings |

---

## 5. Live Execution Pipeline

### How each `run_live_*.py` works

Every strategy runner follows the same lifecycle:

```
1. Check halt_gate → abort if HALT flag exists (S3-S6, S9, S12-S15 only)
2. Load portfolio JSON → get current cash + holdings
3. Accrue Bondia overnight yield on idle cash (6.53% APR / 365.25 days)
4. Check monthly DCA deposit (2,000 MXN/month contribution)
5. Download market data (yfinance, interval varies per strategy)
   → NaN/invalid prices are rejected: cached last_price is kept and
     trading aborts rather than executing on bad data
6. Compute HMM regime (if applicable)
7. Compute indicators (MACD / CCI+ADX / VWAP / etc.)
8. Generate buy/sell signals
9. Execute paper trades → update holdings, cash
10. Update portfolio JSON
11. Append transaction to transactions_*.md ledger
12. Write narrative report to *_report_live.md
```

### Critical parameters by strategy type

**Intraday strategies (S10, S11, S16):**
- Data: 1h bars — S10/S11 download QQQ with `period="150d"` and TQQQ/SQQQ with 10-15d; S16 downloads base assets with `period="730d"` for HMM training and 10d for trading data
- HMM training: trailing 60 trading days of 1h bars (~420 bars)
- HMM: `GaussianHMM(n_components=3, covariance_type="diag", n_iter=100)`
- Stop: Hybrid — 3.0 ATR entry wide → tightens to 1.5 ATR once +1.5 ATR in profit
- Hold: Overnight (not liquidated at EOD)
- Commission: **0%** (`TRANSACTION_FEE_RATE = 0.0000`, Alpaca-free model)

**Daily regime strategies (S9, S2/MACD):**
- Data: `yfinance.download("SPY", period="5y", interval="1d")`
- HMM training: full 5-year daily history (~1,254 bars)
- HMM: `GaussianHMM(n_components=3, covariance_type="full", n_iter=100)`

**Daily systematic strategies (S12–S15):**
- No HMM
- Signal computed fresh daily on closing prices
- Daily rebalancing

---

## 6. Dashboard

### Web Dashboard (`app.py`)

Built with **Python Dash** (Plotly). Runs at `http://localhost:8050`.

**To start:**
```powershell
python run_dashboard.py
# or directly:
python app.py
```

**Tabs and views:**
- **Overview** — Consolidated NAV across all strategies
- **Strategy Details** — Per-strategy equity curve, drawdown, trades
- **Heatmap Matrix** — Performance heatmap (strategy × date)
- **Transaction Ledger** — Full trade history with filters
- **Watchdog Report** — Live W1-W5 safety audit results

### Static Dashboard (`index.html` + `app.js` + `index.css`)

Standalone HTML/JS alternative — can be opened directly in browser without running a server. Uses pre-computed JSON data files.

---

## 7. Risk & Safety Systems

### Capital Limits

| Protection | Value | Enforced By |
|:---|:---:|:---|
| Per-strategy starting capital | 200,000 MXN | Initial portfolio JSON |
| Monthly DCA contribution | 2,000 MXN | Each `run_live_*.py` |
| Max single trade size | Configurable (usually 100% of available cash) | Per-strategy logic |
| Commission rate | 0.29%/side for BMV/legacy strategies; **0% for S3, S4, S10, S11, S16** (Alpaca-free model) | Coded in each runner |

### Bondia Yield Accrual

All idle cash earns the Mexican overnight sweep rate:
```
BONDIA_YIELD = 0.0653   # 6.53% annual
Daily rate = 0.0653 / 365.25
```
Applied every time the runner detects time has elapsed since last update.

### Data Sanity Guards (added 2026-07-09)

All price ingestion points reject NaN / non-positive prices (yfinance returns
NaN closes for BMV tickers while the market is closed):
- Mark-to-market loops keep the cached `last_price` instead of overwriting with NaN
- Trading runners (S9, S12–S15) abort the cycle without trading if the fresh price or FX rate is invalid
- Report generators (`compare_strategies.py`, `generate_clean_report.py`, `run_live_multi_strategy.py`) fall back to `buy_price` when `last_price` is invalid

### Capital Exit Rules

`KILL_CRITERIA.md` defines the binding, mechanical rules for removing money
from a strategy (DD breach, sustained hurdle failure, untrusted books,
behavior drift, portfolio circuit breaker). `graduation_report.py` evaluates
the paper-record equivalents every cycle in its Kill-Criteria Watch table.

### Emergency Kill-Switch Protocol (manual)

1. Watchdog detects CRITICAL → `watchdog_report.md` + GitHub Actions CI run marked RED (audit-only; no flags written)
2. Human investigates → if a stop is needed, manually create `HALT_<strategy>.flag` (honored by S3-S6, S9, S12-S15) or comment the runner out of `scheduler.py` and `.github/workflows/monitor.yml`
3. After fixing the root cause → delete the flag / restore the runner

---

## 8. Portfolio State (Current)

**As of 2026-07-08 22:09 UTC:**

| Metric | Value |
|:---|:---:|
| Total Portfolio NAV | **$395,934 USD** |
| Total Cash (idle) | $273,591 USD |
| USD/MXN Rate | 17.57 |
| Portfolio CAGR | **24.4%** |
| Portfolio Max Drawdown | **-8.8%** |
| Portfolio Sharpe | **1.41** |

**Strategy Weights vs Targets:**

| Strategy | NAV USD | Current Weight | Target Weight | Deviation |
|:---|:---:|:---:|:---:|:---:|
| S4 US-DCF | $101,483 | 25.6% | 15.0% | **+10.6%** (overweight) |
| S6 High-Beta | $101,158 | 25.5% | 5.0% | **+20.5%** (overweight) |
| S5 Alternatives | $101,246 | 25.6% | 5.0% | **+20.6%** (overweight) |
| S9 Stat-Arb | $11,124 | 2.8% | 15.0% | -12.2% (underweight) |
| S10 VWAP | $11,393 | 2.9% | 10.0% | -7.1% (underweight) |
| S11 CCI-ADX | $11,505 | 2.9% | 10.0% | -7.1% (underweight) |
| S1 Alpha Growth | $1,181 | 0.3% | 10.0% | -9.7% (underweight) |
| S8 Dividends | $11,301 | 2.9% | 10.0% | -7.1% (underweight) |
| S12 VTTL | $11,380 | 2.9% | 5.0% | -2.1% |
| S13 CARA | $11,380 | 2.9% | 5.0% | -2.1% |
| S14 HEDGE | $11,392 | 2.9% | 5.0% | -2.1% |
| S15 TRACK | $11,391 | 2.9% | 5.0% | -2.1% |

> **Note:** S4, S5, S6 are significantly overweight vs targets. This reflects the original legacy strategies having higher absolute NAV from early DCA contributions. Rebalancing would require selling from overweight and funding underweight strategies.

---

## 9. Dependencies & Environment Setup

### Python Requirements (`requirements.txt`)

```
yfinance>=0.2.31        # Market data
requests>=2.31.0        # HTTP
arch>=6.0.0             # GARCH volatility models
hmmlearn>=0.3.0         # Gaussian HMM
scikit-learn            # ML utilities
scipy                   # Stats
numpy>=1.26             # Numerical
pandas>=2.0             # DataFrames
pytest>=8.0.0           # Testing
```

**Additional (not in requirements.txt):**
- `dash` / `plotly` — Dashboard
- `statsmodels` — OLS for stat-arb pairs (S9)
- `alpaca-trade-api` — Alpaca paper trading (S3/S4)

**Install:**
```powershell
pip install -r requirements.txt
pip install dash plotly statsmodels alpaca-trade-api
```

### Alpaca API (S3/S4 only)

S4 (US-DCF) and S3 (Suspended) use the Alpaca Paper Trading API.
Credentials are read from environment variables only (never hardcode them):
- `APCA_API_KEY_ID`
- `APCA_API_SECRET_KEY`
- Endpoint: `https://paper-api.alpaca.markets`

### Python Version

**Python 3.11** (confirmed — in `C:\Users\wanga\AppData\Local\Programs\Python\Python311\`)

---

## 10. File Reference Map

### Core Infrastructure

| File | Purpose |
|:---|:---|
| `scheduler.py` | Main cron loop — runs all scripts every 30 min during market hours |
| `watchdog.py` | Safety auditor — W1-W5 checks at end of each cycle |
| `halt_gate.py` | Kill-switch mechanism — `halted()` and `raise_halt()` |
| `monitor_portfolio.py` | Portfolio health monitor |
| `pipeline_orchestrator.py` | Alternative orchestration utility |
| `compare_strategies.py` | Cross-strategy performance comparison generator |
| `generate_clean_report.py` | Executive summary report builder |
| `graduation_report.py` | Paper→live readiness scorecard (`graduation_report.md`): 90-day history, Bondia 6.53% hurdle, 1.25× DD bound, Sharpe > 0; includes the Kill-Criteria Watch |
| `KILL_CRITERIA.md` | **Binding policy** for taking money out: K1 DD breach → liquidate, K2 hurdle failure → staged demotion, K3 bad books → suspend, K5 portfolio −15% breaker; no overrides, re-entry from zero |
| `app.py` | Dash web dashboard backend |
| `run_dashboard.py` | Dashboard launch script |
| `run.py` | Utility launcher |

### Strategy Backtests

| File | Strategy | Key Signal |
|:---|:---|:---|
| `backtest_strategy9.py` | S9 Stat-Arb | HMM(SPY 5y daily) → regime-based allocation |
| `backtest_strategy10.py` | S10 VWAP | VWAP ± 1.0 ATR channel on 1h bars, 60d HMM |
| `backtest_strategy11.py` | S11 CCI-ADX | CCI oversold+ADX trend, 1h bars, 60d HMM |
| `backtest_strategy12.py` | S12 VTTL | SMA200 + vol targeting, daily |
| `backtest_strategy13.py` | S13 CARA | VIX/credit/SMA macro vote, daily |
| `backtest_strategy14.py` | S14 HEDGE | Multiplicative expert weights, daily |
| `backtest_strategy15.py` | S15 TRACK | Fixed-share expert tracking, daily |
| `backtest_strategy16.py` | S16 MACD-HMM | MACD crossover + HMM gate, 1h bars, 60d HMM |
| `backtest_macd.py` | S2/MACD | MACD+SMA50 on 20 US assets, daily |
| `backtest_alpha_growth.py` | S1 | DCF + fundamental screening, BMV |

### Portfolio State Files

| File | Content |
|:---|:---|
| `portfolio_strategy*.json` | Per-strategy: cash, holdings, last_updated |
| `portfolio_multi_strategy.json` | Consolidated cross-strategy NAV history + allocations |
| `portfolio_macd.json` | S2/MACD portfolio |
| `portfolio.json` | S1 Alpha Growth portfolio |
| `watchdog_nav_history.json` | Historical NAV snapshots for W3/W5 checks |
| `HALT_*.flag` | Active halt flags (delete to re-enable strategy) |

### Research & Optimization

| File | Content |
|:---|:---|
| `optimization_master_journey.md` | **Master reference** — complete optimization history |
| `strategy_optimization_comparison.md` | Before/after table for S10/S11/S16 + S9/S2 grid |
| `optimization_conclusions.md` | 4 universal optimization rules |
| `walkforward_report.md` | Walk-forward validation of S10/S11/S16 frozen configs (10 OOS windows; verdict: July backtests were in-sample fits) |
| `efficient_frontier_report.md` | Graduation-day target allocation: hurdle-filtered risk parity recommended (generated by `scratch/efficient_frontier_v2.py`) |
| `after_tax_report.md` | After-tax/real-fee hurdle (5.71% net at 35% ISR); SIC 10% regime vs US-broker marginal-rate comparison (generated by `scratch/after_tax_hurdle.py`) |
| `strategy10_optimization_journey.md` | S10 detailed journey |
| `strategy11_optimization_journey.md` | S11 detailed journey |
| `strategy16_optimization_journey.md` | S16 detailed journey |
| `scratch/grid_s9_s2_full.py` | 5×4 grid search for S9+S2 |

### Transaction Ledgers (Audit Trail)

| File | Covers |
|:---|:---|
| `transactions_strategy*.md` | Full trade ledger per strategy (buy/sell/interest) |
| `transactions_macd.md` | S2/MACD trades |
| `transactions.md` | S1 Alpha Growth trades |

### NAV History CSVs

Each strategy has a `*_backtest_nav.csv` and some have `*_backtest_report.md`:
- `strategy9_backtest_nav.csv` — CAGR 15.92%, Sharpe 0.47, MaxDD -6.00%
- `strategy10_backtest_nav.csv` — Return +9.91%, Sharpe 3.27 (optimized)
- `strategy11_backtest_nav.csv` — Return +16.17%, Sharpe 0.35 (optimized)
- `strategy16_backtest_nav.csv` — Return +59.00%, Sharpe 0.99 (optimized)

---

## 11. Optimization History

### Summary of July 2026 Optimization Session

**Root cause discovered:** Intraday strategies on 30m bars suffered from:
1. **Noise whipsaws** — 30m microstructure noise triggering false HMM transitions
2. **Stale HMM** — Too few/too many training bars causing misclassification
3. **Premature stop-outs** — Fixed trailing stops exiting winners too early

**Universal formula applied to S10, S11, S16:**
- Timeframe: 30m → **1h bars**
- HMM lookback: Short/Full → **60 trading days of 1h bars (~420 bars)**
- Stop: Fixed 1.5 ATR → **Hybrid 3.0→1.5 ATR** (profit-tightening)

**Results:**

| Strategy | Before | After |
|:---|:---:|:---:|
| S16 MACD-HMM | -35.81%, Sharpe -0.89 | **+59.00%, Sharpe +0.99** |
| S11 CCI-ADX | +1.11%, Sharpe -0.34 | **+16.17%, Sharpe +0.35** |
| S10 VWAP | +5.36%, Sharpe -0.43 | **+9.91%, Sharpe +3.27** |

**Extended grid search:** S9 and S2/MACD tested across 5 timeframes × 4 lookbacks → confirmed current `1d/ALL` configs are optimal. Shorter timeframes destroy HMM regime quality (0% Bear detection, 100% transition rate).

**See:** [`optimization_master_journey.md`](optimization_master_journey.md)

---

## 12. Known Issues & Operational Notes

### ⚠️ S3 / Alpaca reconciliation (in progress 2026-07-11)
- **Root cause found:** S3's runner traded in mock mode without the broker following (phantom fills), and **S3 and S4 share ONE Alpaca paper account**, so neither book alone matches the broker
- Real broker state discovered 2026-07-11: cash **−$62,477 USD**, orphan DBA 733 position claimed by no book, S3 phantom NVDA/META book entries
- De-leverage sells queued (TSLA 47, JPM 59, DBA 733, AVGO 10 ≈ $63k) → fill Monday 2026-07-13 open → then `reconcile_s3.py` + manual AVGO split (S3 38 / S4 65)
- **Structural note:** with a shared account, each book's `cash_balance` is its own simulation; the broker's cash is the only shared truth. Watchdog W6 compares the broker against the *combined* ledgers — that is the check that matters

### ⚠️ S1 Alpha Growth Underperforming
- NAV has declined to ~$1,181 USD (from ~$11,000 starting capital equivalent)
- BMV data access issues and illiquid BMV equities have degraded signal quality
- Consider reviewing BMV data pipeline

### ⚠️ Portfolio Allocation Drift
- S4, S5, S6 are significantly overweight (25% each vs 5-15% target)
- No auto-rebalancing is implemented — manual review needed
- Cash is parked ($273,591 USD idle — 69% of portfolio)

### yfinance Data Limits
| Interval | Max History | Notes |
|:---:|:---:|:---|
| 30m | ~60 calendar days | Only for diagnostics |
| 1h (60m) | ~730 days | Used by S10/S11/S16 |
| 1d | ~33 years | Used by S9/S2/S12-S15 |
| 4h | Not available via yfinance | Use 1h+resample |

### HMM Convergence Warnings
`hmmlearn` emits `Model is not converging` and `zero-sum transmat_` warnings when:
- Training window is too short (<200 bars for 3-state model)
- Market data is too uniform (e.g., low-volatility period with no regime changes)
- These are expected in research/diagnostic scripts. Production covariance types: intraday runners (S10/S11/S16) use `covariance_type="diag"`; daily runners (S9, S2) use `covariance_type="full"`

### Commission Rates
- **0% commission (Alpaca-free model):** S3, S4, S10, S11, S16
- **0.29% per side (GBM/SIC broker assumption):** S1, S2, S5, S6, S8, S9 and daily systematic strategies

### NaN Price Incident (2026-07-09, resolved)
- The 06:15 UTC GitHub Actions run executed while BMV was closed; yfinance returned NaN closes for `.MX` tickers and the runners overwrote `last_price` with NaN in `portfolio.json` (S1), `portfolio_macd.json` (S2), and `portfolio_dividends.json` (S8), which propagated NaN into the consolidated NAV, its history/CSV, and `comparison_report.md`
- Fixed on 2026-07-09: NaN guards added at every price-ingestion point, corrupted state repaired from the 2026-07-08 close, reports regenerated clean
- `comparison_report.md` is written by `compare_strategies.py` and then **overwritten** by `generate_clean_report.py` later in the same pipeline cycle — the final content always comes from `generate_clean_report.py`

---

## 13. CI/CD & Git Workflow

### Repository Structure
```
trading_agents/
├── .github/            # GitHub Actions workflows
├── _archive/           # Stale snapshots (formerly files/ and
│                       #   updates_in_trading_system/) — never edit or run
├── agents/             # Agent skill definitions
├── connectors/         # MCP data connectors
├── scratch/            # Research scripts (not production)
├── scheduler_logs/     # Per-run script logs
├── skills/             # Python skill modules
├── tests/              # pytest test suite (incl. test_data_guards.py
│                       #   regression tests for the NaN/W6 guards)
├── correction_files/   # Manual correction utilities
└── update_v2/, update_v3/  # Version migration files
```

> **Canonical source:** the scripts in the **repo root** are production — they are what `scheduler.py` and the GitHub Actions workflow execute. Everything under `_archive/` is a drifted historical snapshot (archived 2026-07-11); never edit or run it.

### Auto-Commit Workflow
The scheduler or a GitHub Action auto-commits after each pipeline run:
```
Auto-update: Multi-strategy concentrated paper trading [YYYY-MM-DD HH:MM:SS UTC]
```
These appear in `git log` every 30–60 minutes.

### Manual Commit Convention
```
feat:  new strategy or major feature
fix:   bug fix
docs:  documentation update
test:  test changes
optim: optimization changes (e.g. strategy parameters)
```

### Branch Strategy
- **`main`** — only branch; all changes committed directly
- No feature branches currently in use

### To push changes:
```powershell
git add <files>
git commit -m "type: description"
git push origin main
```

---

*This document is the master operational reference for the Trading Agents Suite.
Last updated: 2026-07-09 (verified against production code; NaN-guard hardening + audit-only watchdog).*
