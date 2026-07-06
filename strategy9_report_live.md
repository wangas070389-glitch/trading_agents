# Strategy 9: AI-Regime Adaptive Statistical Arbitrage Execution Report
**Execution Date:** 2026-07-05 23:41:55 | **Strategy Version:** Upgraded Live V1

## 1. Portfolio Summary
* **Total Portfolio NAV:** $196,951.91 MXN
* **Total Cash Balance:** $196,951.91 MXN (Parked compounding in Bondia sweep at 6.53% APR)
* **Equity Exposure:** 0.0%
* **Active Regime:** State 2 (Range-bound chop, mean-reversion detected on SPY)

## 2. Current Holdings
| Ticker | Type | Shares/Qty Y | Shares/Qty X | Buy Price/Alloc | Last Price | Market Value (MXN) |
| :--- | :---: | :---: | :---: | :---: | :---: | ---: |

## 3. Today's Execution Logs
* **[INTEREST ACCRUED]** Cash reserves earned $$0.3427 MXN sweep interest.
* SOLD 13.0000 shares of SPY due to regime rotation.

## 4. Asset Evaluation Diagnostics (Regime & Arbitrage checks)
* **Regime Signal Classifier (HMM on SPY):**
  * Current Decoded Regime: HMM State 0 -> **Regime 2 (Range-bound chop, mean-reversion detected on SPY)**

### Statistical Arbitrage Pairs Cointegration Telemetry:
| Pair | Cointegrated? | Current Z-Score | Hedge Ratio (Beta) | Decision |
| :--- | :---: | :---: | :---: | :--- |
| BTC-USD/ETH-USD | NO | 0.000 | 1.000 | No signal |
| EURUSD=X/GBPUSD=X | NO | 0.000 | 1.000 | No signal |
