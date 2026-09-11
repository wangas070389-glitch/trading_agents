# Workspace Rules: Trading Agents & Execution Safety

## 1. Broker API & Execution Circuit Breakers
- **Order Execution Validation:** NEVER execute dependent `BUY` orders if a preceding `SELL` order fails, is rejected, or returns an HTTP error code (e.g., 403 Forbidden, 429 Rate Limit, 500 Server Error).
- **Cash & Margin Safety:** Before submitting market `BUY` orders, verify that `available_cash >= order_value`. Prohibit non-intentional margin debt.
- **Broker Mismatch Reconciliation:** If an orphan position or negative cash balance is detected, trigger an emergency halt (Watchdog W4/W6) and run `reconcile_s3.py` after manual position closure.

## 2. Strategy Audit & Performance Benchmark Standard
- **Evidence Quality Ranking:** When reviewing portfolio strategies, rank by Evidence Quality Score (`Sharpe * Backtest Window Years`) rather than short-term CAGR.
- **Graduation Benchmark:** Require $\ge 30$ calendar days of live paper history, positive live Sharpe, and live annualized return > BONDIA 6.53% APR before marking any strategy as PASSING for live money deployment.

## 3. Fundamental Dividend & FIBRA Screening Guardrails
- **Payout Ratio & Cash Flow Cap:** Exclude any dividend stock or FIBRA where Free Cash Flow (FCF) or EPS payout ratio exceeds 100% to prevent value traps.
- **Trend & Balance Sheet Gates:** Require $Close > \text{SMA 200}$ (bullish trend filter) and $\text{Debt/Equity} \le 1.5$ before initiating or holding income assets.
- **Yield Floors:** Require annual yield $\ge 2.5\%$ for dividend stocks and $\ge 4.0\%$ for FIBRAs.

## 4. HMM & Intraday Quantitative Architecture Standards
- **Timeframe & Noise Filtering:** Prefer 1-hour bars over 30-minute bars for intraday HMM/trend strategies to minimize noise and broker fee drag.
- **HMM Lookback Window:** Require $\approx 60$ trading days ($\sim 420$ bars on 1h timeframe) for 3-state Gaussian HMM model training to ensure state convergence.
- **Regime Stability Filter:** Apply a 3-day rolling consensus filter (majority vote) on daily HMM regime outputs to eliminate state flips and fee bleed.
- **Intraday ML Protection:** Enforce a minimum holding period ($\ge 26$ bars / 2 days) and single Golden Ratio feature scale ($\approx 35$ bars) for rolling ML classifiers.
