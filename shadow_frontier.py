"""
SHADOW FRONTIER: live track record for the allocation layer itself
===================================================================
The efficient-frontier weights (efficient_frontier_report.md, Risk Parity
hurdle-filtered) are themselves an untested strategy: the covariances and
correlations behind them come from backtests. This runner paper-trades the
allocation: a virtual $100,000 USD book holds each strategy at its target
weight and is marked every cycle from the NAVs the pipeline already collects.
When strategies graduate, this book says whether the BLEND behaved as promised
(vol 6.66%, Sharpe 1.22, MaxDD -4.10%) -- not just the parts.

Mechanics
- Marks: per-strategy USD NAVs from portfolio_multi_strategy.json history;
  S2 (not tracked there) from watchdog_nav_history.json (MXN / usd_mxn_rate).
- Deposit adjustment: S4/S5/S6 receive monthly cash contributions; sleeve
  returns are chain-linked NET of ledger DEPOSIT rows so contributions never
  count as performance.
- Stale/NaN marks freeze the sleeve at its last value (no NaN propagation,
  same policy as the 2026-07 data guards).
- Rebalance: back to target weights on the first mark of each calendar month.
- Weights are FROZEN at inception (2026-07-11). Changing them is a new
  allocation config: reset the state file and note it, per KILL_CRITERIA P3.

Runs every cycle (scheduler.py / monitor.yml) after graduation_report.py.
Output: shadow_frontier_report.md + portfolio_shadow_frontier.json (state).
"""
import datetime
import json
import math
import os

DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = "portfolio_shadow_frontier.json"
REPORT_FILE = "shadow_frontier_report.md"

INITIAL_CAPITAL_USD = 100000.0
BONDIA_HURDLE = 0.0653           # same hurdle as graduation_report.py
MIN_SAMPLES_FOR_STATS = 10       # daily points before Sharpe/DD are quoted
MIN_SAMPLES_FOR_CORR = 15        # return observations before correlations
SUSPICIOUS_MOVE = 0.15           # single-mark sleeve move worth flagging
STALE_DAYS = 4                   # calendar days without a mark worth flagging

WEIGHTS_VERSION = ("efficient_frontier_report.md 2026-07-11 -- "
                   "Risk Parity, hurdle-filtered (RECOMMENDED)")
# What the frontier promised for this portfolio (annualized, common window).
PROMISE = dict(ann_ret=0.1467, ann_vol=0.0666, sharpe=1.22, max_dd=-0.0410)

# key -> sleeve config. weight = frozen target; ms_key = column in
# portfolio_multi_strategy.json history (None -> watchdog snapshots, MXN);
# ledger parsed for DEPOSIT rows in ledger_ccy.
SLEEVES = {
    "core":         dict(short="S1", label="S1 Adaptive Value (BMV)", weight=0.054,
                         ms_key="s1_nav_usd", ledger="transactions.md", ledger_ccy="MXN"),
    "macd":         dict(short="S2", label="S2 MACD Systematic", weight=0.049,
                         ms_key=None, ledger="transactions_macd.md", ledger_ccy="MXN"),
    "us_dcs":       dict(short="S4", label="S4 US DCF Value-Growth", weight=0.045,
                         ms_key="s4_nav_usd", ledger="transactions_us_dcs.md", ledger_ccy="USD"),
    "alternatives": dict(short="S5", label="S5 Alternatives", weight=0.250,
                         ms_key="s5_nav_usd", ledger="transactions_alternatives.md", ledger_ccy="USD"),
    "high_beta":    dict(short="S6", label="S6 High-Beta Momentum", weight=0.135,
                         ms_key="s6_nav_usd", ledger="transactions_high_beta.md", ledger_ccy="USD"),
    "dividends":    dict(short="S8", label="S8 Dividend Quality", weight=0.118,
                         ms_key="s8_nav_usd", ledger="transactions_dividends.md", ledger_ccy="MXN"),
    "strategy9":    dict(short="S9", label="S9 AI Regime Stat-Arb", weight=0.086,
                         ms_key="s9_nav_usd", ledger="transactions_strategy9.md", ledger_ccy="MXN"),
    "strategy12":   dict(short="S12", label="S12 VTTL Trend+Vol", weight=0.053,
                         ms_key="s12_nav_usd", ledger="transactions_strategy12.md", ledger_ccy="MXN"),
    "strategy13":   dict(short="S13", label="S13 CARA Cross-Asset", weight=0.060,
                         ms_key="s13_nav_usd", ledger="transactions_strategy13.md", ledger_ccy="MXN"),
    "strategy14":   dict(short="S14", label="S14 HEDGE Aggregator", weight=0.074,
                         ms_key="s14_nav_usd", ledger="transactions_strategy14.md", ledger_ccy="MXN"),
    "strategy15":   dict(short="S15", label="S15 TRACK Tracker", weight=0.076,
                         ms_key="s15_nav_usd", ledger="transactions_strategy15.md", ledger_ccy="MXN"),
    "strategy17":   dict(short="S17", label="S17 FIBRAs Dynamic", weight=0.000,
                         ms_key="s17_nav_usd", ledger="transactions_strategy17.md", ledger_ccy="MXN"),
    "strategy19":   dict(short="S19", label="S19 Particle Filter QQQ", weight=0.000,
                         ms_key="s19_nav_usd", ledger="transactions_strategy19.md", ledger_ccy="MXN"),
    "strategy20":   dict(short="S20", label="S20 Hurst Exponent Dynamic", weight=0.000,
                         ms_key="s20_nav_usd", ledger="transactions_strategy20.md", ledger_ccy="MXN"),
    "strategy21":   dict(short="S21", label="S21 Golden Entropy", weight=0.000,
                         ms_key="s21_nav_usd", ledger="transactions_strategy21.md", ledger_ccy="MXN"),
    "strategy22":   dict(short="S22", label="S22 Walk-Forward ML", weight=0.000,
                         ms_key="s22_nav_usd", ledger="transactions_strategy22.md", ledger_ccy="MXN"),
    "strategy23":   dict(short="S23", label="S23 Calculus S&R", weight=0.000,
                         ms_key="s23_nav_usd", ledger="transactions_strategy23.md", ledger_ccy="MXN"),
    "strategy24":   dict(short="S24", label="S24 ML Classifier", weight=0.000,
                         ms_key="s24_nav_usd", ledger="transactions_strategy24.md", ledger_ccy="MXN"),
    "strategy25":   dict(short="S25", label="S25 Golden MACD BMV", weight=0.000,
                         ms_key="s25_nav_usd", ledger="transactions_strategy25.md", ledger_ccy="MXN"),
    "strategy27":   dict(short="S27", label="S27 Golden Hurst", weight=0.000,
                         ms_key="s27_nav_usd", ledger="transactions_strategy27.md", ledger_ccy="MXN"),
    "strategy29":   dict(short="S29", label="S29 Golden Stat-Arb", weight=0.000,
                         ms_key="s29_nav_usd", ledger="transactions_strategy29.md", ledger_ccy="MXN"),
    "strategy30":   dict(short="S30", label="S30 Golden MACD US", weight=0.000,
                         ms_key="s30_nav_usd", ledger="transactions_strategy30.md", ledger_ccy="USD"),
}

# Backtest correlation matrix from efficient_frontier_report.md (2026-07-11),
# for the realized-vs-promised divergence check.
BT_CORR_ORDER = ["S1", "S2", "S4", "S5", "S6", "S8", "S9", "S12", "S13", "S14", "S15"]
BT_CORR_ROWS = [
    [1.00, 0.24, 0.23, 0.13, 0.08, 0.29, 0.15, 0.17, 0.15, 0.20, 0.20],
    [0.24, 1.00, 0.70, -0.01, 0.30, 0.23, 0.27, 0.59, 0.65, 0.74, 0.74],
    [0.23, 0.70, 1.00, 0.04, 0.55, 0.18, 0.37, 0.59, 0.64, 0.67, 0.67],
    [0.13, -0.01, 0.04, 1.00, 0.09, 0.10, 0.10, 0.04, 0.05, 0.03, 0.03],
    [0.08, 0.30, 0.55, 0.09, 1.00, 0.09, 0.18, 0.36, 0.37, 0.36, 0.36],
    [0.29, 0.23, 0.18, 0.10, 0.09, 1.00, 0.24, 0.09, 0.12, 0.20, 0.21],
    [0.15, 0.27, 0.37, 0.10, 0.18, 0.24, 1.00, 0.26, 0.26, 0.29, 0.29],
    [0.17, 0.59, 0.59, 0.04, 0.36, 0.09, 0.26, 1.00, 0.89, 0.93, 0.93],
    [0.15, 0.65, 0.64, 0.05, 0.37, 0.12, 0.26, 0.89, 1.00, 0.92, 0.92],
    [0.20, 0.74, 0.67, 0.03, 0.36, 0.20, 0.29, 0.93, 0.92, 1.00, 1.00],
    [0.20, 0.74, 0.67, 0.03, 0.36, 0.21, 0.29, 0.93, 0.92, 1.00, 1.00],
]
BT_CORR = {(a, b): BT_CORR_ROWS[i][j]
           for i, a in enumerate(BT_CORR_ORDER)
           for j, b in enumerate(BT_CORR_ORDER)}


def finite(x):
    try:
        return math.isfinite(float(x))
    except (TypeError, ValueError):
        return False


def load_json(path):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None


def normalized_weights():
    total = sum(cfg["weight"] for cfg in SLEEVES.values())
    return {k: cfg["weight"] / total for k, cfg in SLEEVES.items()}


# ---------------------------------------------------------------------------
# Marks
# ---------------------------------------------------------------------------
def latest_ms_mark(ms_history, ms_key):
    """(date, nav_usd) of the last finite entry for ms_key, else None."""
    for row in reversed(ms_history):
        v = row.get(ms_key)
        if finite(v) and float(v) > 0:
            return row.get("date"), float(v)
    return None


def latest_wd_mark(wd_history, key, usd_mxn_rate):
    """(date, nav_usd) from the newest finite watchdog snapshot (MXN)."""
    snaps = wd_history.get(key, [])
    for s in reversed(snaps):
        v = s.get("nav")
        if finite(v) and float(v) > 0:
            return s.get("ts", "")[:10], float(v) / usd_mxn_rate
    return None


def collect_marks(ms_history, wd_history, usd_mxn_rate):
    marks = {}
    for key, cfg in SLEEVES.items():
        if cfg["ms_key"]:
            marks[key] = latest_ms_mark(ms_history, cfg["ms_key"])
        else:
            marks[key] = latest_wd_mark(wd_history, key, usd_mxn_rate)
    return marks


# ---------------------------------------------------------------------------
# Deposits: contributions must not count as sleeve performance
# ---------------------------------------------------------------------------
def deposits_between(ledger, after_date, upto_date):
    """Sum of DEPOSIT amounts (ledger local ccy) with after_date < date <= upto_date."""
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
                d = cells[1]
                i = cells.index("DEPOSIT")
                shares = float(cells[i + 1].replace(",", "").replace("$", ""))
                price = float(cells[i + 2].replace(",", "").replace("$", ""))
            except (ValueError, IndexError):
                continue
            if after_date < d <= upto_date:
                total += shares * price
    return total


# ---------------------------------------------------------------------------
# Sleeve update: chain-linked total return, deposit-adjusted
# ---------------------------------------------------------------------------
def update_sleeve(st, mark, deposits_usd):
    """Apply a new mark to a sleeve state dict.
    Returns (updated: bool, warning: str|None). Stale, missing, or invalid
    marks leave the sleeve frozen at its last value."""
    if mark is None:
        return False, None
    mark_date, mark_nav = mark
    if not mark_date or mark_date <= st["last_date"]:
        return False, None
    if not finite(mark_nav) or mark_nav <= 0 or st["last_nav"] <= 0:
        return False, f"mark invalido ({mark_nav}) el {mark_date}; sleeve congelado"
    growth = (mark_nav - deposits_usd) / st["last_nav"]
    if not finite(growth) or growth <= 0:
        return False, (f"factor de crecimiento invalido ({growth:.4f}) el "
                       f"{mark_date}; sleeve congelado")
    warning = None
    if abs(growth - 1.0) > SUSPICIOUS_MOVE:
        warning = (f"movimiento de {(growth - 1.0) * 100:+.1f}% en una sola marca "
                   f"({st['last_date']} -> {mark_date}); revisar fuente de datos")
    st["alloc_usd"] *= growth
    st["tr_index"] *= growth
    st["last_nav"] = mark_nav
    st["last_date"] = mark_date
    return True, warning


def should_rebalance(prev_date, new_date):
    """Rebalance on the first mark of a new calendar month."""
    return bool(prev_date) and prev_date[:7] != new_date[:7]


def apply_rebalance(state, today):
    weights = normalized_weights()
    total = sum(s["alloc_usd"] for s in state["sleeves"].values())
    drift = max(abs(s["alloc_usd"] / total - weights[k])
                for k, s in state["sleeves"].items()) if total > 0 else 0.0
    for k, s in state["sleeves"].items():
        s["alloc_usd"] = weights[k] * total
    state["rebalances"].append(dict(date=today, nav_usd=round(total, 2),
                                    max_drift=round(drift, 4)))


# ---------------------------------------------------------------------------
# Stats (same math as graduation_report.series_stats)
# ---------------------------------------------------------------------------
def series_stats(vals):
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


def ann_vol(vals):
    if len(vals) < MIN_SAMPLES_FOR_STATS:
        return None
    rets = [vals[i] / vals[i - 1] - 1.0 for i in range(1, len(vals)) if vals[i - 1] > 0]
    if len(rets) < 2:
        return None
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
    return math.sqrt(var) * math.sqrt(252.0)


def pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx <= 0 or syy <= 0:
        return None
    return sxy / math.sqrt(sxx * syy)


def realized_correlations(history):
    """Per-sleeve daily returns from the tr_index columns of history rows."""
    if len(history) < MIN_SAMPLES_FOR_CORR + 1:
        return None
    keys = list(SLEEVES.keys())
    rets = {k: [] for k in keys}
    for prev, cur in zip(history, history[1:]):
        for k in keys:
            a, b = prev.get("idx", {}).get(k), cur.get("idx", {}).get(k)
            rets[k].append(b / a - 1.0 if finite(a) and finite(b) and a > 0 else 0.0)
    out = {}
    for i, ka in enumerate(keys):
        for kb in keys[i + 1:]:
            c = pearson(rets[ka], rets[kb])
            if c is not None:
                out[(SLEEVES[ka]["short"], SLEEVES[kb]["short"])] = c
    return out or None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    today = datetime.date.today().isoformat()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    ms = load_json(os.path.join(DIR, "portfolio_multi_strategy.json")) or {}
    ms_history = ms.get("history", [])
    wd_history = load_json(os.path.join(DIR, "watchdog_nav_history.json")) or {}
    usd_mxn_rate = ms.get("usd_mxn_rate", 17.5)
    if not finite(usd_mxn_rate) or usd_mxn_rate <= 0:
        usd_mxn_rate = 17.5

    marks = collect_marks(ms_history, wd_history, usd_mxn_rate)
    weights = normalized_weights()
    warnings = []

    state = load_json(os.path.join(DIR, STATE_FILE))
    if state is None:
        missing = [k for k, m in marks.items() if m is None]
        if missing:
            raise SystemExit(f"[shadow_frontier] sin marca inicial para: {missing}; "
                             "no se puede inicializar el libro sombra")
        state = dict(
            inception=today,
            initial_capital_usd=INITIAL_CAPITAL_USD,
            weights_version=WEIGHTS_VERSION,
            weights={k: round(w, 4) for k, w in weights.items()},
            sleeves={k: dict(alloc_usd=weights[k] * INITIAL_CAPITAL_USD,
                             last_nav=marks[k][1], last_date=marks[k][0],
                             tr_index=1.0)
                     for k in SLEEVES},
            history=[], rebalances=[],
        )
        print(f"[shadow_frontier] libro sombra inicializado ({today}, "
              f"${INITIAL_CAPITAL_USD:,.0f} USD virtuales)")

    prev_hist_date = state["history"][-1]["date"] if state["history"] else None

    for key, st in state["sleeves"].items():
        cfg = SLEEVES[key]
        mark = marks.get(key)
        dep_local = 0.0
        if mark is not None and mark[0] and mark[0] > st["last_date"]:
            dep_local = deposits_between(cfg["ledger"], st["last_date"], mark[0])
        dep_usd = dep_local if cfg["ledger_ccy"] == "USD" else dep_local / usd_mxn_rate
        _, warn = update_sleeve(st, mark, dep_usd)
        if warn:
            warnings.append(f"{cfg['label']}: {warn}")
        if dep_usd > 0:
            print(f"[shadow_frontier] {cfg['label']}: deposito de "
                  f"${dep_usd:,.2f} USD excluido del retorno")

    if prev_hist_date and should_rebalance(prev_hist_date, today):
        apply_rebalance(state, today)
        print(f"[shadow_frontier] rebalanceo mensual aplicado ({today})")

    nav = sum(s["alloc_usd"] for s in state["sleeves"].values())
    row = dict(date=today, nav_usd=round(nav, 2),
               idx={k: round(s["tr_index"], 6) for k, s in state["sleeves"].items()})
    if state["history"] and state["history"][-1]["date"] == today:
        state["history"][-1] = row
    else:
        state["history"].append(row)
    state["last_updated"] = now_str

    with open(os.path.join(DIR, STATE_FILE), "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

    write_report(state, nav, usd_mxn_rate, warnings, now_str, today)
    print(f"[shadow_frontier] NAV ${nav:,.2f} USD | reporte -> {REPORT_FILE}")


def write_report(state, nav, usd_mxn_rate, warnings, now_str, today):
    navs = [r["nav_usd"] for r in state["history"] if finite(r.get("nav_usd"))]
    sharpe, max_dd = series_stats(navs)
    vol = ann_vol(navs)
    roi = nav / state["initial_capital_usd"] - 1.0
    inception = datetime.date.fromisoformat(state["inception"])
    live_days = (datetime.date.fromisoformat(today) - inception).days

    def pct(x, digits=2):
        return f"{x * 100:+.{digits}f}%" if x is not None else "--"

    L = [
        "# Shadow Frontier — Live Track Record of the Allocation Layer",
        f"**Generated:** {now_str} | Inception: {state['inception']} "
        f"({live_days} calendar days) | Virtual capital: "
        f"${state['initial_capital_usd']:,.0f} USD",
        f"**Weights (frozen):** {state['weights_version']}",
        "",
        "This book paper-trades the recommended frontier allocation itself, marked",
        "from the same NAVs the pipeline already collects. It answers: does the",
        "*blend* behave as the backtest covariances promised? Sleeve returns are",
        "chain-linked **net of deposits**; stale/NaN marks freeze a sleeve rather",
        "than corrupt it; rebalanced to targets on the first mark of each month.",
        "",
        "## 1. Promise vs. Realized",
        "| Metric | Backtest promise | Realized (live) |",
        "| :--- | ---: | ---: |",
        f"| NAV | -- | ${nav:,.2f} USD |",
        f"| Return since inception | -- | {pct(roi)} |",
        f"| Ann. return | {pct(PROMISE['ann_ret'])} | "
        f"{pct(roi * 365.0 / live_days) if live_days >= 30 else '-- (<30d)'} |",
        f"| Ann. volatility | {PROMISE['ann_vol'] * 100:.2f}% | "
        f"{f'{vol * 100:.2f}%' if vol is not None else '-- (<' + str(MIN_SAMPLES_FOR_STATS) + ' marks)'} |",
        f"| Sharpe (Rf {BONDIA_HURDLE * 100:.2f}%) | {PROMISE['sharpe']:+.2f} | "
        f"{f'{sharpe:+.2f}' if sharpe is not None else '--'} |",
        f"| Max drawdown | {PROMISE['max_dd'] * 100:.2f}% | "
        f"{f'{max_dd * 100:.2f}%' if max_dd is not None else '--'} |",
        "",
        "## 2. Sleeves",
        "| Sleeve | Target w | Current w | TR since inception | Last mark | Source |",
        "| :--- | ---: | ---: | ---: | :--- | :--- |",
    ]
    for key, cfg in SLEEVES.items():
        st = state["sleeves"][key]
        cur_w = st["alloc_usd"] / nav if nav > 0 else 0.0
        src = "multi-strategy USD" if cfg["ms_key"] else "watchdog MXN/USD"
        stale = ""
        try:
            age = (datetime.date.fromisoformat(today)
                   - datetime.date.fromisoformat(st["last_date"])).days
            if age >= STALE_DAYS:
                stale = f" (stale {age}d)"
        except ValueError:
            pass
        L.append(f"| {cfg['label']} | {state['weights'][key] * 100:.1f}% | "
                 f"{cur_w * 100:.1f}% | {pct(st['tr_index'] - 1.0)} | "
                 f"{st['last_date']}{stale} | {src} |")

    L += ["", "## 3. Correlation check (realized vs. backtest)"]
    corr = realized_correlations(state["history"])
    if corr is None:
        L.append(f"*Needs >= {MIN_SAMPLES_FOR_CORR} daily return observations; "
                 f"have {max(len(state['history']) - 1, 0)}.*")
    else:
        divs = sorted(((abs(c - BT_CORR.get((a, b), 0.0)), a, b, c)
                       for (a, b), c in corr.items()), reverse=True)[:10]
        L += ["Largest divergences from the backtest correlation matrix "
              "(the frontier's key input):",
              "", "| Pair | Backtest | Realized | Divergence |",
              "| :--- | ---: | ---: | ---: |"]
        for d, a, b, c in divs:
            L.append(f"| {a}-{b} | {BT_CORR.get((a, b), 0.0):.2f} | {c:.2f} | {d:.2f} |")

    L += ["", "## 4. Rebalances"]
    if state["rebalances"]:
        L += ["| Date | NAV | Max weight drift |", "| :--- | ---: | ---: |"]
        for rb in state["rebalances"]:
            L.append(f"| {rb['date']} | ${rb['nav_usd']:,.2f} | "
                     f"{rb['max_drift'] * 100:.1f}pp |")
    else:
        L.append("*None yet (monthly, first mark of each month).*")

    L += ["", "## 5. Warnings"]
    if warnings:
        L += [f"- {w}" for w in warnings]
    else:
        L.append("*None this cycle.*")

    L += [
        "",
        "## 6. Method notes",
        f"- USD-denominated; MXN sleeves converted at usd_mxn_rate "
        f"({usd_mxn_rate:.4f}), so they carry FX exposure — same caveat as the "
        "frontier report.",
        "- S2 is marked from watchdog snapshots (it has no multi-strategy NAV "
        "column), so its marks can lag the others by one cycle.",
        "- A weight change is a new allocation config (KILL_CRITERIA P3): delete "
        "portfolio_shadow_frontier.json to restart the clock, and say so here.",
        "- This is evidence for the ALLOCATION layer only; individual strategies "
        "still graduate (or die) via graduation_report.md / KILL_CRITERIA.md.",
    ]

    with open(os.path.join(DIR, REPORT_FILE), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
