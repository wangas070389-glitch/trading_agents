# Strategy Graduation Report — Paper to Live Money
**Generated:** 2026-07-11 20:52:58 | Hurdle: Bondia **6.53%** | Min live history: **90 days** | DD bound: **1.25× backtest MaxDD**

| Strategy | Verdict | Live days | ROI to date | Ann. return | vs 6.53% hurdle | Live Sharpe | Live MaxDD | DD bound (1.25×BT) | Evidence score | BT Sharpe (window) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| S12 VTTL Trend+Vol | **ON TRACK** | 5 | +1.0% | +75.0% | pending | n/a | n/a | -26.7% | 10.35 | 0.46 (22.5y) |
| S14 HEDGE Aggregator | **ON TRACK** | 5 | +0.8% | +60.3% | pending | n/a | n/a | -19.0% | 10.18 | 0.53 (19.2y) |
| S15 TRACK Tracker | **ON TRACK** | 5 | +0.8% | +60.1% | pending | n/a | n/a | -18.4% | 10.18 | 0.53 (19.2y) |
| S2 MACD Systematic | **ON TRACK** | 0 | -0.0% | -14.4% | pending | n/a | n/a | -11.9% | 8.78 | 1.76 (5.0y) |
| S13 CARA Cross-Asset | **ON TRACK** | 5 | +1.0% | +75.1% | pending | n/a | n/a | -31.3% | 8.64 | 0.45 (19.2y) |
| S8 Dividend Quality | **ON TRACK** | 16 | -1.9% | -42.2% | pending | -8.62 | -2.3% | -14.2% | 5.60 | 1.12 (5.0y) |
| S4 US DCF Value-Growth | **ON TRACK** | 18 | +1.2% | +24.4% | pending | 3.58 | -1.0% | -15.2% | 4.56 | 1.14 (4.0y) |
| S6 High-Beta Momentum | **ON TRACK** | 18 | +0.7% | +14.2% | pending | 4.71 | -0.1% | -24.4% | 4.20 | 1.05 (4.0y) |
| S5 Alternatives | **ON TRACK** | 18 | +0.4% | +7.3% | pending | 4.29 | -0.1% | -19.0% | 3.80 | 0.95 (4.0y) |
| S1 Adaptive Value (BMV) | **ON TRACK** | 38 | +3.7% | +36.0% | PASS | 0.59 | -3.3% | -35.2% | 3.28 | 0.82 (4.0y) |
| S9 AI Regime Stat-Arb | **ON TRACK** | 0 | +0.0% | +0.0% | pending | -15.66 | -2.2% | -7.5% | 2.35 | 0.47 (5.0y) |
| S10 Intraday VWAP | **ON TRACK** | 9 | +0.1% | +5.7% | pending | -2.04 | -0.6% | -4.0% | 0.52 | 3.27 (0.2y) |
| S16 MACD-HMM Router | **ON TRACK** | 4 | +0.1% | +6.6% | pending | n/a | n/a | -13.4% | 0.16 | 0.99 (0.2y) |
| S11 Intraday CCI-ADX | **ON TRACK** | 9 | +1.0% | +39.3% | pending | 3.72 | -0.3% | -8.4% | 0.06 | 0.35 (0.2y) |
| S3 US Stock Momentum | **BLOCKED** | 18 | +99.2% | +2011.6% | pending | n/a | n/a | -22.7% | 5.75 | 1.15 (5.0y) |

## Verdict Detail

**S12 VTTL Trend+Vol** — ON TRACK
- needs 85 more live days (C1: 5/90)
- return/Sharpe judged from day 30 (now 5); current figures are informational
- risk stats pending (6 daily samples, need 8) [multi-strategy daily USD]

**S14 HEDGE Aggregator** — ON TRACK
- needs 85 more live days (C1: 5/90)
- return/Sharpe judged from day 30 (now 5); current figures are informational
- risk stats pending (6 daily samples, need 8) [multi-strategy daily USD]

**S15 TRACK Tracker** — ON TRACK
- needs 85 more live days (C1: 5/90)
- return/Sharpe judged from day 30 (now 5); current figures are informational
- risk stats pending (6 daily samples, need 8) [multi-strategy daily USD]

**S2 MACD Systematic** — ON TRACK
- needs 90 more live days (C1: 0/90)
- return/Sharpe judged from day 30 (now 0); current figures are informational
- risk stats pending (6 daily samples, need 8) [watchdog snapshots (local ccy)]
- Re-tuned 2026-07-11; graduation clock restarted (P3)

**S13 CARA Cross-Asset** — ON TRACK
- needs 85 more live days (C1: 5/90)
- return/Sharpe judged from day 30 (now 5); current figures are informational
- risk stats pending (6 daily samples, need 8) [multi-strategy daily USD]
- Retired standalone; survives as expert sleeve in S14/S15

**S8 Dividend Quality** — ON TRACK
- needs 74 more live days (C1: 16/90)
- return/Sharpe judged from day 30 (now 16); current figures are informational

**S4 US DCF Value-Growth** — ON TRACK
- needs 72 more live days (C1: 18/90)
- return/Sharpe judged from day 30 (now 18); current figures are informational

**S6 High-Beta Momentum** — ON TRACK
- needs 72 more live days (C1: 18/90)
- return/Sharpe judged from day 30 (now 18); current figures are informational

**S5 Alternatives** — ON TRACK
- needs 72 more live days (C1: 18/90)
- return/Sharpe judged from day 30 (now 18); current figures are informational

**S1 Adaptive Value (BMV)** — ON TRACK
- needs 52 more live days (C1: 38/90)
- BMV data quality degraded; see Known Issues

**S9 AI Regime Stat-Arb** — ON TRACK
- needs 90 more live days (C1: 0/90)
- return/Sharpe judged from day 30 (now 0); current figures are informational
- Re-tuned 2026-07-11 (consensus filter); graduation clock restarted (P3)

**S10 Intraday VWAP** — ON TRACK
- needs 81 more live days (C1: 9/90)
- return/Sharpe judged from day 30 (now 9); current figures are informational
- 60d in-sample backtest; params tuned July 2026 -- treat backtest as ceiling

**S16 MACD-HMM Router** — ON TRACK
- needs 86 more live days (C1: 4/90)
- return/Sharpe judged from day 30 (now 4); current figures are informational
- risk stats pending (5 daily samples, need 8) [watchdog snapshots (local ccy)]
- 60d in-sample backtest; params tuned July 2026 -- treat backtest as ceiling

**S11 Intraday CCI-ADX** — ON TRACK
- needs 81 more live days (C1: 9/90)
- return/Sharpe judged from day 30 (now 9); current figures are informational
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
