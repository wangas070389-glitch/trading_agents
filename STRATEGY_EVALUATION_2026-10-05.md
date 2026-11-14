# Strategy evaluation and repair record — 5 October 2026

## Scope and conclusion

Reviewed the online repository at commit `fd7461011259e175777f7c21695e5abfc696f829`, not just the older local reports. Local `main` was initially 36 commits behind; the differences were generated artifacts, with no differences in the reviewed Python implementations or S32 research snapshot. The repairs are proposed on `codex/strategy-validation` for review, not deployed to online main. No broker orders, schedule changes, or fabricated reconciliation entries were made.

The repository is a substantial research collection, but it is not yet a validated portfolio of deployable strategies. Its main weaknesses are inconsistent accounting, stale performance references, insufficiently independent validation, and highly overlapping risk exposures. More strategies do not automatically create more diversification.

My research priorities are S12 and one representative of S14/S15. S8 is a useful accounting-reconstruction candidate, not a demonstrated performance winner. S2/S30 merit reassessment after their repairs. Several complicated leveraged variants have not justified their complexity against their own benchmarks. No strategy is approved for real-money deployment by this evaluation.

## What the online operational evidence actually says

- The pinned graduation report marks all 27 non-composite candidates BLOCKED. Waiting for more calendar days does not resolve the accounting blocks.
- Of 28 registered books, the reconciliation artifact contains 23 MISMATCH, four UNRESOLVED, and one VERIFIED result. S8 has the verified current cash/position snapshot, but its historical return series remains unverified.
- Mismatches vary in severity. S12's reported cash difference is only MXN 0.09, with matching holdings. Some exact MXN 200,000 differences are opening-funding/schema problems. These are not evidence that those amounts were lost.
- S3 is materially different: the watchdog reports negative USD cash and broker/ledger position discrepancies. Broker statements, fills, account ownership, and verified opening balances are required to resolve them. This repair did not submit orders or invent ledger adjustments.
- The apparent absence of critical watchdog alerts was not reassuring: its scheduler-source regex failed because the scheduler imports the registry instead of defining a literal list. Active strategies were therefore downgraded to inactive warnings.
- S7/current multi-strategy reporting, S18, and the shadow frontier are derived views. They must not be counted as additional independent deployable capital or independent alpha.

Sources: [pinned graduation report](https://github.com/wangas070389-glitch/trading_agents/blob/fd7461011259e175777f7c21695e5abfc696f829/graduation_report.md), [reconciliation artifact](https://github.com/wangas070389-glitch/trading_agents/blob/fd7461011259e175777f7c21695e5abfc696f829/nav_reconciliation.json), [watchdog report](https://github.com/wangas070389-glitch/trading_agents/blob/fd7461011259e175777f7c21695e5abfc696f829/watchdog_report.md), and `ACCOUNTING_REVIEW_FOLLOWUP.md`.

## Repairs implemented in this working copy

| Component | Confirmed defect | Repair and remaining limitation |
|---|---|---|
| S1 Alpha Growth | TWR linked pre-trade NAV to the previous post-trade NAV, omitting each day's trading fees from returns. | Link the post-flow trading subperiod as well; include the initial loss when computing return/drawdown. Historical reports need regeneration. |
| S2 MACD portfolio engine | Same fee omission. A flat-price synthetic example reported +0.1677% while actual NAV lost 0.3328%. | TWR now agrees with NAV in the no-flow regression, including the MXN 500 fee. Contributions remain excluded from returns. Multiple S2 versions still need a single canonical configuration. |
| S8 dividends | Deposits counted as profit; drawdown calculated on contribution-inflated NAV; adjusted prices plus explicit dividends; missing fundamentals replaced with passing values. | Record external flows, calculate net flow-adjusted returns and TWR drawdown, request unadjusted prices, and exclude missing quality data. Current fundamentals remain a historical approximation, explicitly disclosed. |
| S8 API | Raw NAV growth called return, cash transfers called trade P&L, deposits counted as trades, fixed 100% win rate, missing fee fields. | Serve TWR returns, exclude contributions from total P&L, record fees, match benchmark flows, and mark unavailable closed-lot P&L/win rate as null. |
| S25 Golden MACD BMV | Applied USD/MXN returns to prices already denominated in MXN. | Native-MXN prices only; reject non-BMV tickers. An irrelevant FX column cannot alter the curve. |
| S25/S30 backtests | Stop-arming expression divided a price by itself, so it could never reach +15%. | Shared tested simulator tracks the actual entry fill and peak. Signals from the previous completed close fill at the next close; no pre-fill return is earned. Stops are signals, not guaranteed execution prices. |
| S25/S30 paper runners | Purchase check covered notional but not fees. | Require enough cash for notional plus fees. The runners were not executed. |
| S24 parameter search | Selected hyperparameters on the same period subsequently called out-of-sample. | Search only the first 75% of observations; reserve the last 25% from selection. Reject insufficient data or failed searches. Online model refitting uses past observations; historical knowledge still makes this a retrospective experiment. |
| Watchdog | All-active-to-inactive parsing error; critical findings returned success; dry run wrote files. | Read `StrategySpec.active` directly, return exit status 1 on critical findings, and suppress report/history writes during dry runs. Audit-only: this does not automatically halt broker execution. |
| KPI/graduation reporting | Invalid historical figures could retain high ranks and support promotion/projections after code changes. | Central reviewed-evidence blocks suppress affected rankings and graduation. Remove five-year compounding forecasts. Remaining archival numbers are labeled research references, not independently certified returns. |

These repairs correct specific implementation defects. They do not repair every economic-model assumption, prove profitability, or validate old histories. The old generated reports and portfolios are deliberately preserved; they are not silently replaced with purportedly corrected performance.

## Strategy-by-strategy assessment

All figures below describe the **pre-repair archived evidence**, not verified live results or new post-repair backtests. CAGR and maximum drawdown are percentages; Sharpe definitions, currencies, samples, and financing conventions differ across engines. A row with invalid evidence must not be used as an investment ranking.

| Strategy | Archived evidence and principal concern | Research decision |
|---|---|---|
| S1 Adaptive Value / Alpha Growth | Current Alpha report: 21.93% CAGR, Sharpe 1.14, DD -12.19%; equal-weight 20.83%, Sharpe 1.21. Roughly four years, static cash carry, and fee omission. KPI references a different original variant. | Repair completed for TWR; reassess after point-in-time inputs, costs, and version alignment. No demonstrated benchmark-adjusted advantage yet. |
| S2 MACD Systematic | MXN portfolio report: 13.10% versus equal-weight 16.88%, DD -10.94%. A separate USD engine reports 23.98% with DD -37.65%. These are not interchangeable records. Closed-trade win rate excludes open losers. | Retain as a simple testable hypothesis; choose one canonical runner and regenerate net-of-cost evidence. |
| S3 US Stock Momentum | Reported 33.85%, Sharpe 1.36, DD -25.14% over about 5.2 years. Fixed universe includes major subsequent winners; saved terminal NAV differs from report. Serious broker/ledger discrepancies. | Operational reconciliation first; then survivor-aware and sector/risk-matched testing. Strong historical-looking numbers are not enough. |
| S4 US DCF Value-Growth | Reported 31.32%, Sharpe 1.19, DD -32.04%. Historical decisions call a static fundamental database without an as-of date; headline KPI uses another strategy's figures. | Historical fundamental edge is unproven. Require point-in-time statements with publication lags. |
| S5 Alternative Assets | Own report: 3.42% TWR CAGR versus benchmark 9.10%, not the headline 18.4%. Crypto/equity calendars and external flows require consistent treatment. | Low priority until accounting, calendars, and benchmark provenance agree. |
| S6 High-Beta Momentum | Three-position concentration; scratch backtest uses static DCF data and unadjusted-for-flow daily NAV returns. Dividing terminal value by total contributions is not TWR. | Do not trust the headline 22.1%. Compare with a leverage/risk-matched equity baseline after rebuilding returns. |
| S7 historical Hybrid | Historical 15.63%, Sharpe 1.07, DD -10.49%, versus equal-weight 20.83%, Sharpe 1.21. The current similarly labeled component is a reporting consolidator. | Separate historical strategy identity from current accounting aggregation. |
| S8 Dividend Quality | Advertised 26.74% comes from a deposit-contaminated curve; dividend treatment and current-fundamental screens also invalidate the historical claim. | Rebuild first. Current snapshot reconciliation makes it a useful repair starting point, not the best-performing strategy. |
| S9 AI Regime Stat-Arb | Reported 15.92%, Sharpe 0.47, DD -6.00%, but HMM fitted on the full sample; contributions included in growth and crypto-calendar days annualized as trading days. | Current statistical evidence invalid. Needs chronological fitting and signed, funded pair accounting. |
| S10 Intraday VWAP | Recent sample: Sharpe 3.27 over about 60 sessions. Ten earlier windows: only three positive, mean return +1.23%, median -1.51%. | Do not annualize the short optimized sample into a forecast. Require broader chronological validation and realistic execution costs. |
| S11 Intraday CCI-ADX | Recent sample Sharpe 4.00; earlier-window mean return -3.19%, worst return -17.59%, worst DD -22.87%. | Retire the current performance claim; unstable across windows. |
| S12 VTTL Trend + Volatility | 22.6-year record: 17.13%, Sharpe 0.46, DD -21.34%, versus QQQ 17.25%, Sharpe 0.36, DD -41.21%. Much of the appeal is risk control, not higher raw return. | Highest-priority hypothesis. Validate pre-inception synthetic TQQQ, historical financing/cash rates, and executable signal timing. |
| S13 CARA Cross-Asset | 19.2-year record: 15.95%, Sharpe 0.45, DD -25.02%, versus QQQ 19.35%, Sharpe 0.44, DD -41.21%. Live VIX3M fallback changes the signal's meaning. | Evaluate as a sleeve, not a separate winner. Record when proxy signals are used. |
| S14 HEDGE Aggregator | 15.17%, Sharpe 0.53, DD -15.19% over 19.2 years. Experts overlap; a sleeve labeled QQQ_BH is actually one-third TQQQ plus cash. | Worth further research as a risk-control portfolio, with corrected sleeve names and common costs. |
| S15 TRACK Tracker | 15.05%, Sharpe 0.53, DD -14.73%. Saved daily-return correlation with S14 is 0.99989 over 4,837 observations. | Use one S14/S15 representative unless genuine incremental benefit is demonstrated. Do not count both as diversification. |
| S16 HMM Intraday Router | Recent 59% gain annualized to 616.81%, Sharpe 12.09, on a short sample. Earlier windows include -38.79% return and -48.37% DD. | Current leveraged configuration is not robust. Reject extrapolation of recent results. |
| S17 FIBRAs Dynamic | Stored no-deposit curve grows about 10.32% annually with DD -16.93%; different summaries show different figures. Current debt data reused historically; incomplete historical payout evidence. | Income hypothesis only. Require point-in-time payout/debt data, distribution treatment, and liquidity costs. |
| S18 Efficient Frontier | Published 13.66%, Sharpe 1.16, DD -3.29% depends on underlying strategy histories, overlapping exposures, and currency/calendar normalization. | Reconstruct components before optimizing weights. Not an independent strategy-validation result. |
| S19 Particle Filter | 21.92%, Sharpe 0.31, DD -51.78%, versus QQQ 21.96%, Sharpe 0.57, DD -41.21%. | Deprioritize: reported return is essentially matched by the simpler benchmark with better risk statistics. |
| S20 Hurst Dynamic | 24.29%, Sharpe 0.34, DD -63.71%, versus QQQ 21.96%, Sharpe 0.57, DD -41.21%. | Extra return comes with materially worse tail risk. Require risk-matched comparisons before claiming alpha. |
| S21 Entropy Dynamic | 10.85%, Sharpe 0.03, DD -70.25%, versus QQQ 21.96%, Sharpe 0.57, DD -41.21%. | Retire current research variant unless a materially new, prespecified hypothesis is proposed. |
| S22 Walk-Forward ML | 21.13%, Sharpe 0.26, DD -58.66%, versus QQQ 21.79%, Sharpe 0.56, DD -41.21%. Training uses past slices, but added complexity has not improved reported risk-adjusted outcomes. | Deprioritize; model sophistication is not evidence of an edge. |
| S23 Calculus S&R | Actual report/curve: 25.01%, Sharpe 0.30, DD -77.36%; 2022-onward validation DD -72.11%. Headline table is stale. | Current leverage/tail risk fails a reasonable research screen. Report the actual parameter-search count. |
| S24 30m Random Forest | About 780 bars; reported holdout was used for hyperparameter selection. Selected sample also trailed its benchmark. | Split repaired, but no new market-data validation run. Keep blocked; do not retune against the same known holdout. |
| S25 Golden MACD BMV | Saved pre-repair curve: about 2.06% CAGR and -10.19% DD, not headline 20.86%. FX and stop defects invalidate either as a clean strategy result. | Engine repaired; rerun with a frozen BMV snapshot and matching benchmark before judgment. |
| S27 Golden Hurst | Saved curve: 4.26%, DD -49.14%, negative reported Sharpe; headline table disagrees. Current long cash-only stretch is not itself proof of broken logic. | Deprioritize current variant; validate signal availability and inactivity expectations. |
| S29 Golden Stat-Arb | Headline 253.45%/Sharpe 5.04 conflicts with saved curve about -7.26%/DD -52.18%. Full-sample HMM, inconsistent pair valuation, same-date timing, and live/backtest behavior mismatch. | Quarantine the current evidence. No ranking or promotion; the trading/accounting model requires redesign, not cosmetic parameter tuning. |
| S30 Golden MACD US | Pre-repair 12.35%, reported Sharpe 0.67, DD -23.07%, not headline 15.20%. Broken stop and a selected five-stock universe. | Engine repaired; compare against the same universe and currency with identical costs before selecting it. |
| S31 Fibonacci S&R | Own report: 8.18%, Sharpe -0.10, DD -27.24%, versus QQQ 21.39%, Sharpe 0.55, DD -41.21%. Headline differs. | Low priority: reduced drawdown alone does not establish a useful risk-adjusted improvement. |
| S32 frozen challenger | Reproduced 2020–2025 MXN holdout: 5.48%, Sharpe 0.56, DD -22.26%; equal-weight 10.07%, 0.65, -25.78%; SPY 14.07%, 0.67, -28.92%. Double costs reduce trend CAGR to 4.75%. | Keep the honest rejection. Best reproducibility discipline, not the best strategy. Not registered for trading. |

No implemented S26 or S28 was found in the current registry. Shadow-frontier output is another derived allocation view, subject to the same source-data limitations as S18.

## Evidence ranking and portfolio interpretation

Apply an integrity gate before the repository's prescribed score, **Sharpe × backtest window years**. Multiplying an invalid Sharpe by a long window does not make it credible. Using the archived declared windows, the leading uninvalidated research references are:

| Research reference | Nominal score | Interpretation |
|---|---:|---|
| S12 | 10.35 | Long sample and plausible trend/volatility mechanism; synthetic leverage and carry remain assumptions. |
| S14 | 10.18 | Lower historical DD with less return; portfolio-level validation still required. |
| S15 | 10.18 | Near-duplicate of S14, not an independent confirmation. |
| S13 | 8.64 | Potential sleeve; modest reported risk-adjusted distinction from its benchmark. |

These scores are not confidence levels and do not adjust for multiple testing, nonstationarity, leverage, or different Sharpe conventions. S30's nominal score could be high too, but its old curve cannot pass the integrity gate after the stop repair. S29's former first-place ranking is unsupported.

S12/S14 saved daily-return correlation is also high, approximately 0.908. S12–S16 and S19–S24 frequently express versions of US growth-equity/leveraged-ETF risk. S3/S4/S6/S30 overlap in large US equities. A genuinely diversified portfolio needs measured common-date, common-currency, net-of-flow returns and exposure aggregation—not a count of strategy names.

## Initial repair verification and limits

- 28 offline unittest regressions pass. They cover fee and flow accounting, S8 download/API behavior, funded fills, entry-relative stops, future-price invariance, native-MXN returns, holdout isolation, report quarantine, and watchdog behavior.
- Syntax parsing passed for all 16 changed/new Python files; `git diff --check` found no whitespace errors.
- S32's saved trend/equal-weight/SPY/cash holdout metrics and double-cost sensitivity were independently replayed. Its paper cash, units, and NAV reconcile. Six additional synthetic invariant groups passed.
- The S32 recorded SHA256 matches CRLF-formatted CSV bytes; Git stores LF bytes with a different hash. The values are unchanged. Cross-platform fingerprinting should explicitly normalize line endings.
- The complete pytest suite and market-data backtests were not run: this runtime lacks pytest, yfinance, scipy/sklearn, hmmlearn, and torch. S24 tests verify the selection boundary using a deterministic simulator substitute; they do not certify a new trained Random Forest's performance. S1's pure metrics were tested without importing its optional news/ML stack.
- No broker endpoint or live runner was invoked. No historical portfolio/ledger/report was rewritten, no graduation block was cleared, and no profitability claim was inferred from passing tests.

Run the focused suite in a Python environment with numpy and pandas:

```powershell
python -B -m unittest tests.test_strategy_repair_regressions -v
```

To reproduce the pinned evidence inspection (not execute current strategies):

```powershell
python -B scratch/evaluate_strategy_evidence.py --ref fd7461011259e175777f7c21695e5abfc696f829 --offline-checks
```

## What is still required

1. Reconstruct canonical opening balances, fills, corporate actions, transfers, distributions, fees, and daily native-currency NAV. Broker discrepancies require evidence, not fabricated balancing entries.
2. Freeze data snapshots and attach code, parameter, universe, currency, flow convention, and data fingerprints to every regenerated backtest. Do not publish the old KPIs as results of these repairs.
3. Supply point-in-time fundamentals for S4/S6/S8/S17; redesign chronological regime training and funded pair valuation for S9/S29. These cannot be repaired by inventing missing data.
4. Rerun corrected S1/S2/S8/S25/S30 with the same deposit/cost assumptions as their benchmarks. Evaluate S12 and one S14/S15 representative on the same return engine, with historical-rate and synthetic-leverage sensitivity analyses.
5. Test independent time periods, parameter neighborhoods, doubled costs, realistic turnover/slippage, and lagged fills. Keep fixed hypotheses when examining previously reserved data; repeated holdout tuning creates a new selection sample.
6. Only then start or continue a versioned prospective paper record. The active graduation code requires 90 days; workspace guidance mentions 30. Resolve that inconsistency explicitly rather than silently lowering the implemented requirement. Neither duration substitutes for valid accounting or robust risk evidence.

The yfinance default-adjustment behavior underlying the S8 defect is documented in the [upstream history implementation](https://github.com/ranaroussi/yfinance/blob/main/yfinance/scrapers/history.py). The general distinction between training/parameter selection and held-out evaluation is described in [scikit-learn's cross-validation documentation](https://scikit-learn.org/stable/modules/cross_validation.html). The strategy-specific conclusions above come from this repository's code, saved curves, and reports—not from those general references.

## Follow-up validation completed

The initial dependency limitation above is now resolved in an isolated Python
3.12 environment. **207 tests and six subtests pass, with no failures or skips.**
The JUnit record and exact installed versions are in
`research/validation/2026-10-05/`. External network access is denied during tests;
live-feed tests now use deterministic fixtures, and cache/report writes use
temporary directories. S24's actual Random Forest also passes future-price
invariance on synthetic data. This does not certify its profitability or execution model.

Frozen S25/S30 price snapshots cover 2010-02-11 through 2026-10-05. Their hashes,
native-currency matched-basket curves, assumptions, base/zero-carry/double-cost
scenarios and implementation fingerprints are preserved in the validation folder.
S25's corrected base CAGR is **1.71% versus 10.88%** for its basket; S30's is
**10.51% versus 35.22%**. S30 reduces drawdown (-24.22% versus -48.14%) but also
trails the basket's zero-risk-free Sharpe (1.02 versus 1.16). These retrospective,
selected-universe sleeve simulations do not establish an investable edge or
full shared-cash live parity. All promotion blocks remain.

Offline ledger reconstruction reproduces 23 mismatches, four unresolved books,
and the one matching S8 snapshot. No original operating book was modified.
S32's holdout metrics, doubled-cost case, paper ledger and six synthetic invariant
groups were independently replayed again; the rejection stands.

The workflow now persists the trading cycle's ledgers before propagating a
critical watchdog failure. This avoids losing the cycle's records merely because
the repaired auditor returns a nonzero exit status.

Per the workspace's negative-cash safety rule, `HALT_us_stocks.flag` is included
on the repair branch. It blocks S3 before broker access in checkouts using the
branch; it is not a broker-wide stop and does not cancel or close any positions.
It does not affect the separately scheduled online main branch until adopted.
Do not remove it until manual, strategy-specific broker reconciliation is reviewed.

Reproduction commands and remaining evidence requirements are in
`research/validation/2026-10-05/README.md`; detailed results are in `report.md`.
