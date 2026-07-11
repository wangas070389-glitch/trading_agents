"""
GRADUATION REPORT: which strategies have earned live money?
============================================================
Ranks every paper-trading strategy against explicit go-live criteria and
writes graduation_report.md. Audit-only: reports, never acts.

Criteria (a strategy is READY only when ALL pass):
  C1 HISTORY   >= MIN_LIVE_DAYS calendar days of live paper record
  C2 HURDLE    annualized live return (money-weighted approx, net of the
               fees already modeled in the ledgers) > Bondia 6.53% -- the
               do-nothing alternative
  C3 RISK      live max drawdown within 1.25x backtest MaxDD (same bound
               as watchdog W5): live is inside the validated distribution
  C4 QUALITY   live Sharpe > 0 once enough daily samples exist
  C5 OPS       no operational blocks (e.g. unreconciled broker gap)

Verdicts:
  READY     all criteria pass
  ON TRACK  no current breach, but not enough live history yet (C1)
  NOT READY currently failing C2/C3/C4 -- fix or wait
  BLOCKED   operational issue must be resolved first (C5)

Usage: python graduation_report.py
"""
import os
import json
import math
import datetime

DIR = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(DIR, "graduation_report.md")

MIN_LIVE_DAYS = 90
EVAL_MIN_DAYS = 30              # C2/C4 are only judged after this many days --
                                # annualizing a few days of returns is noise
BONDIA_HURDLE = 0.0653          # annual, the risk-free MXN sweep alternative
DD_BREAKER = 1.25               # same tolerance as watchdog W5
MIN_SAMPLES_FOR_STATS = 8       # daily NAV points needed for Sharpe/DD

# Backtest references. window = backtest years, sharpe/cagr/max_dd from the
# strategy's own backtest. Sources: generate_clean_report.STRATEGY_KPIS,
# ENVIRONMENT_REFERENCE.md section 10, optimization_master_journey.md
# (S10/S11/S16 post-optimization figures).
STRATS = [
    # key, label, portfolio file, ledger file, initial, ccy, inception,
    #   ms_key (per-strategy column in portfolio_multi_strategy history),
    #   bt {window, sharpe, cagr, max_dd}, block reason or None
    dict(key="core", label="S1 Adaptive Value (BMV)", pf="portfolio.json",
         ledger="transactions.md", initial=20000.0, ccy="MXN", inception="2026-06-03",
         ms_key="s1_nav_usd", bt=dict(window=4.0, sharpe=0.82, cagr=0.2007, max_dd=-0.2818),
         block=None, note="BMV data quality degraded; see Known Issues"),
    dict(key="macd", label="S2 MACD Systematic", pf="portfolio_macd.json",
         ledger="transactions_macd.md", initial=20000.0, ccy="MXN", inception="2026-06-03",
         ms_key=None, bt=dict(window=5.0, sharpe=1.27, cagr=0.1310, max_dd=-0.1094),
         block=None, note=""),
    dict(key="us_stocks", label="S3 US Stock Momentum", pf="portfolio_us_stocks.json",
         ledger="transactions_us_stocks.md", initial=100000.0, ccy="USD", inception="2026-06-23",
         ms_key=None, bt=dict(window=5.0, sharpe=1.15, cagr=0.2540, max_dd=-0.1820),
         block="Reactivated 2026-07-10 but broker reconciliation still pending: books were re-based in mock mode; run reconcile_s3.py with Alpaca keys before trusting its P&L", note=""),
    dict(key="us_dcs", label="S4 US DCF Value-Growth", pf="portfolio_us_dcs.json",
         ledger="transactions_us_dcs.md", initial=100000.0, ccy="USD", inception="2026-06-23",
         ms_key="s4_nav_usd", bt=dict(window=4.0, sharpe=1.14, cagr=0.2193, max_dd=-0.1219),
         block=None, note=""),
    dict(key="alternatives", label="S5 Alternatives", pf="portfolio_alternatives.json",
         ledger="transactions_alternatives.md", initial=100000.0, ccy="USD", inception="2026-06-23",
         ms_key="s5_nav_usd", bt=dict(window=4.0, sharpe=0.95, cagr=0.1840, max_dd=-0.1520),
         block=None, note=""),
    dict(key="high_beta", label="S6 High-Beta Momentum", pf="portfolio_high_beta.json",
         ledger="transactions_high_beta.md", initial=100000.0, ccy="USD", inception="2026-06-23",
         ms_key="s6_nav_usd", bt=dict(window=4.0, sharpe=1.05, cagr=0.2210, max_dd=-0.1950),
         block=None, note=""),
    dict(key="dividends", label="S8 Dividend Quality", pf="portfolio_dividends.json",
         ledger="transactions_dividends.md", initial=200000.0, ccy="MXN", inception="2026-06-25",
         ms_key="s8_nav_usd", bt=dict(window=5.0, sharpe=1.12, cagr=0.1450, max_dd=-0.1120),
         block=None, note=""),
    dict(key="strategy9", label="S9 AI Regime Stat-Arb", pf="portfolio_strategy9.json",
         ledger="transactions_strategy9.md", initial=200000.0, ccy="MXN", inception="2026-06-30",
         ms_key="s9_nav_usd", bt=dict(window=5.0, sharpe=0.47, cagr=0.1592, max_dd=-0.0600),
         block=None, note=""),
    dict(key="strategy10", label="S10 Intraday VWAP", pf="portfolio_strategy10.json",
         ledger="transactions_strategy10.md", initial=200000.0, ccy="MXN", inception="2026-07-02",
         ms_key="s10_nav_usd", bt=dict(window=0.16, sharpe=3.27, cagr=0.5325, max_dd=-0.0414),
         block=None, note="60d in-sample backtest; params tuned July 2026 -- treat backtest as ceiling"),
    dict(key="strategy11", label="S11 Intraday CCI-ADX", pf="portfolio_strategy11.json",
         ledger="transactions_strategy11.md", initial=200000.0, ccy="MXN", inception="2026-07-02",
         ms_key="s11_nav_usd", bt=dict(window=0.16, sharpe=0.35, cagr=0.1188, max_dd=-0.1631),
         block=None, note="60d in-sample backtest; params tuned July 2026 -- treat backtest as ceiling"),
    dict(key="strategy12", label="S12 VTTL Trend+Vol", pf="portfolio_strategy12.json",
         ledger="transactions_strategy12.md", initial=200000.0, ccy="MXN", inception="2026-07-06",
         ms_key="s12_nav_usd", bt=dict(window=22.5, sharpe=0.46, cagr=0.1713, max_dd=-0.2134),
         block=None, note=""),
    dict(key="strategy13", label="S13 CARA Cross-Asset", pf="portfolio_strategy13.json",
         ledger="transactions_strategy13.md", initial=200000.0, ccy="MXN", inception="2026-07-06",
         ms_key="s13_nav_usd", bt=dict(window=19.2, sharpe=0.45, cagr=0.1595, max_dd=-0.2502),
         block=None, note="Retired standalone; survives as expert sleeve in S14/S15"),
    dict(key="strategy14", label="S14 HEDGE Aggregator", pf="portfolio_strategy14.json",
         ledger="transactions_strategy14.md", initial=200000.0, ccy="MXN", inception="2026-07-06",
         ms_key="s14_nav_usd", bt=dict(window=19.2, sharpe=0.53, cagr=0.1517, max_dd=-0.1519),
         block=None, note=""),
    dict(key="strategy15", label="S15 TRACK Tracker", pf="portfolio_strategy15.json",
         ledger="transactions_strategy15.md", initial=200000.0, ccy="MXN", inception="2026-07-06",
         ms_key="s15_nav_usd", bt=dict(window=19.2, sharpe=0.53, cagr=0.1505, max_dd=-0.1473),
         block=None, note=""),
    dict(key="strategy16", label="S16 MACD-HMM Router", pf="portfolio_strategy16.json",
         ledger="transactions_strategy16.md", initial=200000.0, ccy="MXN", inception="2026-07-07",
         ms_key=None, bt=dict(window=0.16, sharpe=0.99, cagr=0.5900, max_dd=-0.1070),
         block=None, note="60d in-sample backtest; params tuned July 2026 -- treat backtest as ceiling"),
]


def finite(x):
    try:
        return math.isfinite(float(x))
    except (TypeError, ValueError):
        return False


def valuation_price(h):
    for key in ("last_price", "buy_price"):
        px = h.get(key, 0.0)
        if finite(px) and float(px) > 0:
            return float(px)
    return 0.0


def load_json(path):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None


def portfolio_nav(pf, usd_mxn_rate):
    """NAV in the strategy's local currency from its portfolio JSON.
    USD cash sleeves (S13-S15 hold cash_balance_usd) are converted to MXN."""
    data = load_json(os.path.join(DIR, pf))
    if not data:
        return None
    cash = float(data.get("cash_balance", 0.0)) + float(data.get("cash_balance_mxn", 0.0))
    cash += float(data.get("cash_balance_usd", 0.0)) * usd_mxn_rate
    hv = 0.0
    for h in data.get("holdings", []):
        if "shares" in h:
            hv += float(h["shares"]) * valuation_price(h)
    return cash + hv


def deposits_from_ledger(ledger):
    """Sum of DEPOSIT rows (shares * price) in a transactions_*.md ledger."""
    path = os.path.join(DIR, ledger)
    if not os.path.exists(path):
        return 0.0
    total = 0.0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if "| DEPOSIT |" not in line:
                continue
            cells = [c.strip() for c in line.split("|")]
            try:
                i = cells.index("DEPOSIT")
                shares = float(cells[i + 1].replace(",", "").replace("$", ""))
                price = float(cells[i + 2].replace(",", "").replace("$", ""))
                total += shares * price
            except (ValueError, IndexError):
                continue
    return total


def daily_series(strat, ms_history, wd_history):
    """Daily NAV series: multi-strategy USD history if tracked, else the
    watchdog snapshots (local currency) collapsed to one point per day."""
    if strat["ms_key"]:
        pts = [(row["date"], row.get(strat["ms_key"]))
               for row in ms_history if finite(row.get(strat["ms_key"]))]
        if len(pts) >= 2:
            return [v for _, v in pts], "multi-strategy daily USD"
    snaps = wd_history.get(strat["key"], [])
    by_day = {}
    for s in snaps:
        if finite(s.get("nav")):
            by_day[s["ts"][:10]] = float(s["nav"])
    vals = [by_day[d] for d in sorted(by_day)]
    return vals, "watchdog snapshots (local ccy)"


def series_stats(vals):
    """(annualized sharpe, max drawdown) from a daily NAV series."""
    if len(vals) < MIN_SAMPLES_FOR_STATS:
        return None, None
    rets = [vals[i] / vals[i - 1] - 1.0 for i in range(1, len(vals)) if vals[i - 1] > 0]
    if len(rets) < MIN_SAMPLES_FOR_STATS - 1:
        return None, None
    rf_d = BONDIA_HURDLE / 252.0
    mean = sum(r - rf_d for r in rets) / len(rets)
    var = sum((r - rf_d - mean) ** 2 for r in rets) / max(len(rets) - 1, 1)
    std = math.sqrt(var)
    sharpe = (mean / std) * math.sqrt(252.0) if std > 0 else 0.0
    peak, max_dd = vals[0], 0.0
    for v in vals:
        peak = max(peak, v)
        if peak > 0:
            max_dd = min(max_dd, v / peak - 1.0)
    return sharpe, max_dd


def backtest_max_dd(strat):
    """MaxDD from {key}_backtest_nav.csv when present (watchdog W5 source),
    else the reference table value."""
    path = os.path.join(DIR, f"{strat['key']}_backtest_nav.csv")
    if os.path.exists(path):
        try:
            navs = []
            with open(path, "r", encoding="utf-8") as f:
                header = f.readline().split(",")
                col = header.index("NAV") if "NAV" in [h.strip() for h in header] else 1
                for line in f:
                    parts = line.split(",")
                    if len(parts) > col and finite(parts[col]):
                        navs.append(float(parts[col]))
            if len(navs) > 5:
                peak, dd = navs[0], 0.0
                for v in navs:
                    peak = max(peak, v)
                    if peak > 0:
                        dd = min(dd, v / peak - 1.0)
                return dd
        except Exception:
            pass
    return strat["bt"]["max_dd"]


def main():
    today = datetime.date.today()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ms = load_json(os.path.join(DIR, "portfolio_multi_strategy.json")) or {}
    ms_history = ms.get("history", [])
    wd_history = load_json(os.path.join(DIR, "watchdog_nav_history.json")) or {}
    usd_mxn_rate = ms.get("usd_mxn_rate", 17.5)
    if not finite(usd_mxn_rate) or usd_mxn_rate <= 0:
        usd_mxn_rate = 17.5

    rows = []
    for s in STRATS:
        inception = datetime.datetime.strptime(s["inception"], "%Y-%m-%d").date()
        live_days = (today - inception).days
        nav = portfolio_nav(s["pf"], usd_mxn_rate)
        deposits = deposits_from_ledger(s["ledger"])
        capital_base = s["initial"] + deposits
        profit = (nav - capital_base) if nav is not None else None
        roi = (profit / capital_base) if profit is not None else None
        ann_ret = roi * (365.0 / max(live_days, 1)) if roi is not None else None

        vals, src = daily_series(s, ms_history, wd_history)
        live_sharpe, live_dd = series_stats(vals)
        bt_dd = backtest_max_dd(s)
        dd_bound = bt_dd * DD_BREAKER
        evidence = s["bt"]["window"] * s["bt"]["sharpe"]

        # criteria -- C2/C4 are only judged after EVAL_MIN_DAYS: annualizing a
        # handful of days produces meaningless triple-digit figures
        judge = live_days >= EVAL_MIN_DAYS
        c1 = live_days >= MIN_LIVE_DAYS
        c2 = None if (ann_ret is None or not judge) else (ann_ret > BONDIA_HURDLE)
        c3 = None if live_dd is None else (live_dd >= dd_bound)  # dd negative: inside bound
        c4 = None if (live_sharpe is None or not judge) else (live_sharpe > 0)
        c5 = s["block"] is None

        reasons = []
        if not c5:
            verdict = "BLOCKED"
            reasons.append(s["block"])
        else:
            hard_fail = (c2 is False) or (c3 is False) or (c4 is False)
            if c1 and c2 and (c3 is not False) and (c4 is not False):
                verdict = "READY"
            elif hard_fail:
                verdict = "NOT READY"
            else:
                verdict = "ON TRACK"
            if not c1:
                reasons.append(f"needs {MIN_LIVE_DAYS - live_days} more live days (C1: {live_days}/{MIN_LIVE_DAYS})")
            if c2 is False:
                reasons.append(f"annualized live return {ann_ret*100:+.1f}% below Bondia hurdle {BONDIA_HURDLE*100:.2f}% (C2)")
            if c3 is False:
                reasons.append(f"live DD {live_dd*100:.1f}% breaches {DD_BREAKER}x backtest bound {dd_bound*100:.1f}% (C3)")
            if c4 is False:
                reasons.append(f"live Sharpe {live_sharpe:.2f} <= 0 (C4)")
            if not judge:
                reasons.append(f"return/Sharpe judged from day {EVAL_MIN_DAYS} (now {live_days}); current figures are informational")
            if c3 is None:
                reasons.append(f"risk stats pending ({len(vals)} daily samples, need {MIN_SAMPLES_FOR_STATS}) [{src}]")
        if s["note"]:
            reasons.append(s["note"])

        rows.append(dict(s=s, live_days=live_days, nav=nav, deposits=deposits,
                         roi=roi, ann_ret=ann_ret, live_sharpe=live_sharpe, live_dd=live_dd,
                         bt_dd=bt_dd, dd_bound=dd_bound, evidence=evidence,
                         verdict=verdict, reasons=reasons, src=src, samples=len(vals)))

    order = {"READY": 0, "ON TRACK": 1, "NOT READY": 2, "BLOCKED": 3}
    rows.sort(key=lambda r: (order[r["verdict"]], -r["evidence"]))

    def fmt_pct(x):
        return f"{x*100:+.1f}%" if x is not None else "n/a"

    def fmt_num(x):
        return f"{x:.2f}" if x is not None else "n/a"

    lines = [
        "# Strategy Graduation Report — Paper to Live Money",
        f"**Generated:** {now_str} | Hurdle: Bondia **{BONDIA_HURDLE*100:.2f}%** | "
        f"Min live history: **{MIN_LIVE_DAYS} days** | DD bound: **{DD_BREAKER}× backtest MaxDD**",
        "",
        "| Strategy | Verdict | Live days | ROI to date | Ann. return | vs 6.53% hurdle | Live Sharpe | Live MaxDD | DD bound (1.25×BT) | Evidence score | BT Sharpe (window) |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]
    for r in rows:
        s = r["s"]
        if r["ann_ret"] is None:
            hurdle = "n/a"
        elif r["live_days"] < EVAL_MIN_DAYS:
            hurdle = "pending"
        else:
            hurdle = "PASS" if r["ann_ret"] > BONDIA_HURDLE else "FAIL"
        lines.append(
            f"| {s['label']} | **{r['verdict']}** | {r['live_days']} | {fmt_pct(r['roi'])} | {fmt_pct(r['ann_ret'])} | {hurdle} | "
            f"{fmt_num(r['live_sharpe'])} | {fmt_pct(r['live_dd'])} | {fmt_pct(r['dd_bound'])} | "
            f"{r['evidence']:.2f} | {s['bt']['sharpe']:.2f} ({s['bt']['window']:.1f}y) |")

    lines += ["", "## Verdict Detail", ""]
    for r in rows:
        lines.append(f"**{r['s']['label']}** — {r['verdict']}")
        for reason in r["reasons"]:
            lines.append(f"- {reason}")
        if not r["reasons"]:
            lines.append("- all criteria pass")
        lines.append("")

    # Kill-Criteria Watch (see KILL_CRITERIA.md): the reverse of graduation.
    # P2/K1: live DD breaches 1.25x backtest MaxDD -> parameters invalidated.
    # P1/K2: sustained sub-hurdle returns -> retire candidate / demotion watch.
    lines += ["## Kill-Criteria Watch (KILL_CRITERIA.md)",
              "| Strategy | Status | Detail |",
              "| :--- | :---: | :--- |"]
    for r in rows:
        s = r["s"]
        if r["live_dd"] is not None and r["live_dd"] < r["dd_bound"]:
            status, detail = "**BREACH (P2/K1)**", (
                f"live DD {r['live_dd']*100:.1f}% exceeds 1.25× backtest bound "
                f"{r['dd_bound']*100:.1f}% — parameters invalidated, back to research")
        elif (r["ann_ret"] is not None and r["live_days"] >= 180
              and r["ann_ret"] < BONDIA_HURDLE):
            status, detail = "**RETIRE CANDIDATE (P1)**", (
                f"{r['live_days']}d live and {r['ann_ret']*100:+.1f}% annualized "
                f"< Bondia {BONDIA_HURDLE*100:.2f}%")
        elif (r["ann_ret"] is not None and r["live_days"] >= EVAL_MIN_DAYS
              and r["ann_ret"] < BONDIA_HURDLE):
            status, detail = "WATCH (K2)", (
                f"below hurdle ({r['ann_ret']*100:+.1f}% ann.); "
                f"P1 review at day 180 ({r['live_days']}/180)")
        else:
            status, detail = "OK", "no kill triggers active"
        lines.append(f"| {s['label']} | {status} | {detail} |")
    lines.append("")

    lines += [
        "## Criteria",
        f"- **C1 History:** ≥ {MIN_LIVE_DAYS} calendar days of live paper record",
        f"- **C2 Hurdle:** annualized live return (money-weighted approximation, deposits excluded from profit) > Bondia {BONDIA_HURDLE*100:.2f}% — the do-nothing alternative. Judged only after {EVAL_MIN_DAYS} live days",
        f"- **C3 Risk:** live max drawdown within {DD_BREAKER}× backtest MaxDD (watchdog W5 bound)",
        f"- **C4 Quality:** live Sharpe > 0, judged only after {EVAL_MIN_DAYS} live days and {MIN_SAMPLES_FOR_STATS} daily samples",
        "- **C5 Operations:** no unresolved operational blocks",
        "",
        "## Caveats — read before moving money",
        "- **Evidence score = backtest Sharpe × backtest window (years).** S10/S11/S16 were re-optimized in July 2026 on the same 60 days they were backtested on; their backtests are in-sample ceilings, not forecasts. Their live record is the first true out-of-sample test.",
        "- Live Sharpe/DD for most strategies use the multi-strategy **USD** series, so MXN strategies include USD/MXN moves; short windows make these stats noisy.",
        "- Annualized returns from a few weeks of data swing wildly; C2 only becomes meaningful alongside C1.",
        "- Monthly DCA deposits are subtracted from profit but still smooth the NAV series slightly.",
        "- Paper trading cannot simulate slippage or your own psychology. Graduate with a 10–20% slice first and scale only after live money matches paper.",
        "",
        "*Audit-only: this report never trades, halts, or rebalances anything.*",
    ]

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Graduation report written to {OUT}")
    for r in rows:
        print(f"  {r['verdict']:<9} {r['s']['label']}")


if __name__ == "__main__":
    main()
