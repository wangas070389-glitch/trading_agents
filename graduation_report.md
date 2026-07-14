# Strategy Graduation Report — Paper to Live Money
**Generated:** 2026-07-14 17:43:03 | Hurdle: Bondia **6.53%** | Min live history: **90 days** | DD bound: **1.25× backtest MaxDD**

| Strategy | Verdict | Live days | ROI to date | Ann. return | vs 6.53% hurdle | Live Sharpe | Live MaxDD | DD bound (1.25×BT) | Evidence score | BT Sharpe (window) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| S12 VTTL Trend+Vol | **ON TRACK** | 8 | +0.6% | +29.2% | pending | -3.57 | -1.6% | -26.7% | 10.35 | 0.46 (22.5y) |
| S14 HEDGE Aggregator | **ON TRACK** | 8 | +0.5% | +22.4% | pending | -3.67 | -1.3% | -19.0% | 10.18 | 0.53 (19.2y) |
| S15 TRACK Tracker | **ON TRACK** | 8 | +0.5% | +22.5% | pending | -3.68 | -1.3% | -18.4% | 10.18 | 0.53 (19.2y) |
| S2 MACD Systematic | **ON TRACK** | 3 | +0.2% | +22.3% | pending | 5.59 | -2.1% | -11.9% | 8.78 | 1.76 (5.0y) |
| S13 CARA Cross-Asset | **ON TRACK** | 8 | +0.6% | +29.2% | pending | -3.57 | -1.6% | -31.3% | 8.64 | 0.45 (19.2y) |
| S8 Dividend Quality | **ON TRACK** | 19 | -1.2% | -23.6% | pending | -6.66 | -2.3% | -14.2% | 5.60 | 1.12 (5.0y) |
| S4 US DCF Value-Growth | **ON TRACK** | 21 | +0.8% | +13.4% | pending | 1.16 | -1.1% | -15.2% | 4.56 | 1.14 (4.0y) |
| S6 High-Beta Momentum | **ON TRACK** | 21 | +0.4% | +6.6% | pending | 1.16 | -0.8% | -24.4% | 4.20 | 1.05 (4.0y) |
| S5 Alternatives | **ON TRACK** | 21 | +0.3% | +4.5% | pending | 2.99 | -0.1% | -19.0% | 3.80 | 0.95 (4.0y) |
| S1 Adaptive Value (BMV) | **ON TRACK** | 41 | +0.9% | +7.6% | PASS | 3.65 | -3.3% | -35.2% | 3.28 | 0.82 (4.0y) |
| S9 AI Regime Stat-Arb | **ON TRACK** | 3 | -0.9% | -115.0% | pending | -15.90 | -3.2% | -7.5% | 2.35 | 0.47 (5.0y) |
| S10 Intraday VWAP | **ON TRACK** | 12 | +0.2% | +6.4% | pending | -2.59 | -0.6% | -4.0% | 0.52 | 3.27 (0.2y) |
| S16 MACD-HMM Router | **ON TRACK** | 7 | +0.1% | +7.4% | pending | -54.61 | +0.0% | -13.4% | 0.16 | 0.99 (0.2y) |
| S11 Intraday CCI-ADX | **ON TRACK** | 12 | +2.1% | +62.7% | pending | 4.54 | -0.3% | -8.4% | 0.06 | 0.35 (0.2y) |
| S3 US Stock Momentum | **BLOCKED** | 21 | +9.8% | +171.0% | pending | n/a | n/a | -22.7% | 5.75 | 1.15 (5.0y) |

## Verdict Detail

**S12 VTTL Trend+Vol** — ON TRACK
- needs 82 more live days (C1: 8/90)
- return/Sharpe judged from day 30 (now 8); current figures are informational

**S14 HEDGE Aggregator** — ON TRACK
- needs 82 more live days (C1: 8/90)
- return/Sharpe judged from day 30 (now 8); current figures are informational

**S15 TRACK Tracker** — ON TRACK
- needs 82 more live days (C1: 8/90)
- return/Sharpe judged from day 30 (now 8); current figures are informational

**S2 MACD Systematic** — ON TRACK
- needs 87 more live days (C1: 3/90)
- return/Sharpe judged from day 30 (now 3); current figures are informational
- Re-tuned 2026-07-11; graduation clock restarted (P3)

**S13 CARA Cross-Asset** — ON TRACK
- needs 82 more live days (C1: 8/90)
- return/Sharpe judged from day 30 (now 8); current figures are informational
- Retired standalone; survives as expert sleeve in S14/S15

**S8 Dividend Quality** — ON TRACK
- needs 71 more live days (C1: 19/90)
- return/Sharpe judged from day 30 (now 19); current figures are informational

**S4 US DCF Value-Growth** — ON TRACK
- needs 69 more live days (C1: 21/90)
- return/Sharpe judged from day 30 (now 21); current figures are informational

**S6 High-Beta Momentum** — ON TRACK
- needs 69 more live days (C1: 21/90)
- return/Sharpe judged from day 30 (now 21); current figures are informational

**S5 Alternatives** — ON TRACK
- needs 69 more live days (C1: 21/90)
- return/Sharpe judged from day 30 (now 21); current figures are informational

**S1 Adaptive Value (BMV)** — ON TRACK
- needs 49 more live days (C1: 41/90)
- BMV data quality degraded; see Known Issues

**S9 AI Regime Stat-Arb** — ON TRACK
- needs 87 more live days (C1: 3/90)
- return/Sharpe judged from day 30 (now 3); current figures are informational
- Re-tuned 2026-07-11 (consensus filter); graduation clock restarted (P3)

**S10 Intraday VWAP** — ON TRACK
- needs 78 more live days (C1: 12/90)
- return/Sharpe judged from day 30 (now 12); current figures are informational
- 60d in-sample backtest; params tuned July 2026 -- treat backtest as ceiling

**S16 MACD-HMM Router** — ON TRACK
- needs 83 more live days (C1: 7/90)
- return/Sharpe judged from day 30 (now 7); current figures are informational
- 60d in-sample backtest; params tuned July 2026 -- treat backtest as ceiling

**S11 Intraday CCI-ADX** — ON TRACK
- needs 78 more live days (C1: 12/90)
- return/Sharpe judged from day 30 (now 12); current figures are informational
- 60d in-sample backtest; params tuned July 2026 -- treat backtest as ceiling

**S3 US Stock Momentum** — BLOCKED
- Reconciliation in progress: de-leverage sells (TSLA 47, JPM 59, DBA 733, AVGO 10) queued 2026-07-11, fill at Monday open; then run reconcile_s3.py and split AVGO claim with S4 (shared Alpaca account)

## Kill-Criteria Watch (KILL_CRITERIA.md)
| Strategy | Status | Detail |
| :--- | :---: | :--- |
| S12 VTTL Trend+Vol | OK | no kill triggers active |
| S14 HEDGE Aggregator | OK | no kill triggers active |
| S15 TRACK Tracker | OK | no kill triggers active |
| S2 MACD Systematic | OK | no kill triggers active |
| S13 CARA Cross-Asset | OK | no kill triggers active |
| S8 Dividend Quality | OK | no kill triggers active |
| S4 US DCF Value-Growth | OK | no kill triggers active |
| S6 High-Beta Momentum | OK | no kill triggers active |
| S5 Alternatives | OK | no kill triggers active |
| S1 Adaptive Value (BMV) | OK | no kill triggers active |
| S9 AI Regime Stat-Arb | OK | no kill triggers active |
| S10 Intraday VWAP | OK | no kill triggers active |
| S16 MACD-HMM Router | OK | no kill triggers active |
| S11 Intraday CCI-ADX | OK | no kill triggers active |
| S3 US Stock Momentum | OK | no kill triggers active |

## Criteria
- **C1 History:** ≥ 90 calendar days of live paper record
- **C2 Hurdle:** annualized live return (money-weighted approximation, deposits excluded from profit) > Bondia 6.53% — the do-nothing alternative. Judged only after 30 live days
- **C3 Risk:** live max drawdown within 1.25× backtest MaxDD (watchdog W5 bound)
- **C4 Quality:** live Sharpe > 0, judged only after 30 live days and 8 daily samples
- **C5 Operations:** no unresolved operational blocks

## Caveats — read before moving money
- **Evidence score = backtest Sharpe × backtest window (years).** S10/S11/S16 were re-optimized in July 2026 on the same 60 days they were backtested on; their backtests are in-sample ceilings, not forecasts. Their live record is the first true out-of-sample test.
- Live Sharpe/DD for most strategies use the multi-strategy **USD** series, so MXN strategies include USD/MXN moves; short windows make these stats noisy.
- Annualized returns from a few weeks of data swing wildly; C2 only becomes meaningful alongside C1.
- Monthly DCA deposits are subtracted from profit but still smooth the NAV series slightly.
- Paper trading cannot simulate slippage or your own psychology. Graduate with a 10–20% slice first and scale only after live money matches paper.

*Audit-only: this report never trades, halts, or rebalances anything.*
