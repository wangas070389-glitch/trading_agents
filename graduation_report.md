# Strategy Graduation Report — Paper to Live Money
**Generated:** 2026-11-13 21:13:27 | Hurdle: Bondia **6.53%** | Min live history: **90 days** | DD bound: **1.25× backtest MaxDD**

| Strategy | Verdict | Live days | ROI to date | Ann. return | vs 6.53% hurdle | Live Sharpe | Live MaxDD | DD bound (1.25×BT) | Evidence score | BT Sharpe (window) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| S12 VTTL Trend+Vol | **BLOCKED** | 130 | n/a | n/a | n/a | n/a | n/a | -26.7% | 10.35 | 0.46 (22.5y) |
| S14 HEDGE Aggregator | **BLOCKED** | 130 | n/a | n/a | n/a | n/a | n/a | -19.0% | 10.18 | 0.53 (19.2y) |
| S15 TRACK Tracker | **BLOCKED** | 130 | n/a | n/a | n/a | n/a | n/a | -18.4% | 10.18 | 0.53 (19.2y) |
| S2 MACD Systematic | **BLOCKED** | 125 | n/a | n/a | n/a | n/a | n/a | -11.9% | 8.78 | 1.76 (5.0y) |
| S8 Dividend Quality | **BLOCKED** | 141 | n/a | n/a | n/a | n/a | n/a | -14.2% | 5.60 | 1.12 (5.0y) |
| S4 US DCF Value-Growth | **BLOCKED** | 143 | n/a | n/a | n/a | n/a | n/a | -15.2% | 4.56 | 1.14 (4.0y) |

## Verdict Detail

**S12 VTTL Trend+Vol** — BLOCKED
- C5 operations: historical NAV marks need ledger/flow validation

**S14 HEDGE Aggregator** — BLOCKED
- C5 operations: historical NAV marks need ledger/flow validation

**S15 TRACK Tracker** — BLOCKED
- C5 operations: historical NAV marks need ledger/flow validation

**S2 MACD Systematic** — BLOCKED
- C5 operations: historical NAV marks need ledger/flow validation
- Re-tuned 2026-07-11; graduation clock restarted (P3)

**S8 Dividend Quality** — BLOCKED
- C5 operations: historical NAV marks need ledger/flow validation

**S4 US DCF Value-Growth** — BLOCKED
- C5 operations: cash/position evidence incomplete, mismatched, or changed since audit; reconcile before graduation

## Kill-Criteria Watch (KILL_CRITERIA.md)
| Strategy | Status | Detail |
| :--- | :---: | :--- |
| S12 VTTL Trend+Vol | BLOCKED | Accounting evidence unresolved; risk conclusions withheld |
| S14 HEDGE Aggregator | BLOCKED | Accounting evidence unresolved; risk conclusions withheld |
| S15 TRACK Tracker | BLOCKED | Accounting evidence unresolved; risk conclusions withheld |
| S2 MACD Systematic | BLOCKED | Accounting evidence unresolved; risk conclusions withheld |
| S8 Dividend Quality | BLOCKED | Accounting evidence unresolved; risk conclusions withheld |
| S4 US DCF Value-Growth | BLOCKED | Accounting evidence unresolved; risk conclusions withheld |

## Criteria
- **C1 History:** ≥ 90 calendar days of live paper record
- **C2 Hurdle:** annualized live return (money-weighted approximation, deposits excluded from profit) > Bondia 6.53% — the do-nothing alternative. Judged only after 30 live days
- **C3 Risk:** live max drawdown within 1.25× backtest MaxDD (watchdog W5 bound)
- **C4 Quality:** live Sharpe > 0, judged only after 30 live days and 8 daily samples
- **C5 Operations:** no unresolved operational blocks

## Caveats — read before moving money
- **Evidence score = backtest Sharpe × backtest window (years).** S10/S11/S16 were re-optimized in July 2026 on the same 60 days they were backtested on; their backtests are in-sample ceilings, not forecasts. Their live record is the first true out-of-sample test.
- Native-currency histories exclude external flows using an interval-end convention. Legacy marks require reconstruction before graduation; blocked strategies show no performance claims.
- Annualized returns from a few weeks of data swing wildly; C2 only becomes meaningful alongside C1.
- Monthly DCA deposits are subtracted from profit but still smooth the NAV series slightly.
- Paper trading cannot simulate slippage or your own psychology. Graduate with a 10–20% slice first and scale only after live money matches paper.

*Audit-only: this report never trades, halts, or rebalances anything.*
