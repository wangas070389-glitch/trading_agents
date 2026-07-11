# Kill Criteria — When Money Comes OUT

**Adopted:** 2026-07-10 | **Status:** Binding policy, versioned in git
**Companion to:** `graduation_report.md` (when money goes in) and `efficient_frontier_report.md` (how much)

These rules are written **before** any real money is at risk, precisely so that
no decision has to be made mid-drawdown. The entire value of this document is
that it is mechanical: if a trigger fires, the action executes. There are no
overrides. An override you would make under stress is exactly the decision
this document exists to prevent.

---

## 1. Triggers for LIVE-MONEY strategies

| ID | Trigger | Measurement | Action | Timing |
|:---|:---|:---|:---|:---|
| **K1 — Distribution breach** | Live drawdown from peak exceeds **1.25× backtest MaxDD** (same bound as watchdog W5) | Live NAV history vs `*_backtest_nav.csv` MaxDD | **Liquidate to Bondia cash, same day.** The live strategy is outside the distribution that justified funding it; its parameters are invalidated. | Immediate, no review |
| **K2 — Hurdle failure** | Trailing 6-month money-weighted return (annualized, net of fees) below **Bondia 6.53%** | Monthly review, first business day | 1st consecutive fail: note it. **2nd: cut allocation 50%** (proceeds to Bondia). **4th: full demotion to paper.** | Monthly cadence |
| **K3 — Books cannot be trusted** | Broker reconciliation gap > **1% of NAV**, negative/NaN cash, or no runs for 2+ business days (watchdog W1/W4/W6) | Watchdog report | **Suspend trading immediately** (manual HALT flag). Do NOT liquidate on corrupted books — reconcile first, then decide with clean numbers. | Immediate |
| **K4 — Behavior drift** | Realized 60-day vol > **2× backtest vol**, or zero trades for 20+ business days on a strategy that should trade weekly | Monthly review | **Cut allocation 50%** and investigate. The strategy is not behaving like the one that was validated. | Monthly cadence |
| **K5 — Portfolio circuit breaker** | Total live portfolio drawdown > **15%** from peak | Any run | **De-risk every strategy by 50%** into Bondia, regardless of individual status. Restore only via §3. | Immediate |

## 2. Triggers for PAPER strategies (roster hygiene)

| ID | Trigger | Action |
|:---|:---|:---|
| **P1** | 180 live-paper days with annualized return below Bondia | Flag as **retire candidate**; stop counting it toward future allocation plans |
| **P2** | Live-paper drawdown breaches 1.25× backtest MaxDD | Parameters invalidated → **back to research** (walk-forward re-validation required before the graduation clock may restart) |
| **P3** | Any parameter change while live | **Graduation clock resets to zero.** A re-tuned strategy is a new strategy (lesson of the July 2026 optimization: in-sample tuning looks like alpha until walk-forwarded) |

## 3. Re-entry after a kill

A killed or demoted strategy must **re-qualify from zero** through the full
pipeline: walk-forward validation of the (possibly re-tuned) parameters →
90-day live-paper record → all graduation criteria → funded again at the
starter slice (10–20% of its target weight), not its previous size.

No fast-track. The urge to "get back in because it's recovering" is the same
psychology K-rules exist to contain.

## 4. Standing behavioral rules

1. **No overrides.** If a rule produces a bad outcome, change the rule in git
   *after* complying with it — never instead of complying with it.
2. **No parameter changes on live strategies.** Re-tune in research, then
   re-qualify (P3).
3. **Reviews are calendar-driven** (first business day of the month), not
   triggered by P&L anxiety. K1/K3/K5 are the only intra-month actions.
4. **Every kill/demotion gets one paragraph in git** (what fired, what was
   done, NAV before/after). The ledger is the memory that prevents repeating
   the trade.

## 5. Current parameter values

| Parameter | Value | Source |
|:---|:---|:---|
| DD bound | 1.25× backtest MaxDD | watchdog `DD_BREAKER_FACTOR` |
| Hurdle | 6.53% annual (Bondia) | `BONDIA_YIELD` in live runners |
| K2 window | 126 trading days (~6 months) | this policy |
| Portfolio breaker | −15% from peak | ≈2× worst frontier-portfolio MaxDD (−5.6%), ≈1.7× historical portfolio MaxDD (−8.8%) |
| Starter slice on (re-)entry | 10–20% of target weight | graduation policy |

*Automated monitoring: `graduation_report.py` prints a Kill-Criteria Watch
table every pipeline cycle flagging K1/K2-equivalent breaches on the live
paper record. The watchdog (audit-only) covers K3 signals.*
