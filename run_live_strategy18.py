"""
STRATEGY 18: EFFICIENT FRONTIER ALLOCATION PORTFOLIO
=====================================================
This strategy acts as a live tracking portfolio representing the optimal Risk Parity
(hurdle-filtered) portfolio across all 12 parent strategies, including the new S17 FIBRAs strategy.

S18 Starting Capital: $100,000.00 USD virtual book.
Rebalances: Monthly, on the first mark of each month, back to target weights.
Sleeve returns are chain-linked net of cash contributions/deposits.
"""
import datetime
import json
import math
import os

DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = "portfolio_strategy18.json"
REPORT_FILE = "strategy18_report_live.md"
LEDGER_FILE = "transactions_strategy18.md"

INITIAL_CAPITAL_USD = 100000.0
BONDIA_HURDLE = 0.0653
MIN_SAMPLES_FOR_STATS = 10
MIN_SAMPLES_FOR_CORR = 15
SUSPICIOUS_MOVE = 0.15
STALE_DAYS = 4

WEIGHTS_VERSION = "Risk Parity, S17-inclusive (S18 Core)"

# Target weights from the S17-inclusive optimization run
SLEEVES = {
    "core":         dict(short="S1", label="S1 Alpha Growth", weight=0.045,
                         ms_key="s1_nav_usd", ledger="transactions.md", ledger_ccy="MXN"),
    "macd":         dict(short="S2", label="S2 MACD Systematic", weight=0.042,
                         ms_key=None, ledger="transactions_macd.md", ledger_ccy="MXN"),
    "us_dcs":       dict(short="S4", label="S4 US DCF Value-Growth", weight=0.039,
                         ms_key="s4_nav_usd", ledger="transactions_us_dcs.md", ledger_ccy="USD"),
    "alternatives": dict(short="S5", label="S5 Alternatives", weight=0.250,
                         ms_key="s5_nav_usd", ledger="transactions_alternatives.md", ledger_ccy="USD"),
    "high_beta":    dict(short="S6", label="S6 High-Beta Momentum", weight=0.117,
                         ms_key="s6_nav_usd", ledger="transactions_high_beta.md", ledger_ccy="USD"),
    "dividends":    dict(short="S8", label="S8 Dividend Quality", weight=0.094,
                         ms_key=None, ledger="transactions_dividends.md", ledger_ccy="MXN"),
    "strategy9":    dict(short="S9", label="S9 AI Regime Stat-Arb", weight=0.074,
                         ms_key=None, ledger="transactions_strategy9.md", ledger_ccy="MXN"),
    "strategy12":   dict(short="S12", label="S12 VTTL Trend+Vol", weight=0.047,
                         ms_key=None, ledger="transactions_strategy12.md", ledger_ccy="MXN"),
    "strategy13":   dict(short="S13", label="S13 CARA Cross-Asset", weight=0.052,
                         ms_key=None, ledger="transactions_strategy13.md", ledger_ccy="MXN"),
    "strategy14":   dict(short="S14", label="S14 HEDGE Aggregator", weight=0.064,
                         ms_key=None, ledger="transactions_strategy14.md", ledger_ccy="MXN"),
    "strategy15":   dict(short="S15", label="S15 TRACK Tracker", weight=0.066,
                         ms_key=None, ledger="transactions_strategy15.md", ledger_ccy="MXN"),
    "strategy17":   dict(short="S17", label="S17 FIBRAs Dynamic", weight=0.110,
                         ms_key=None, ledger="transactions_strategy17.md", ledger_ccy="MXN"),
}

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

def latest_ms_mark(ms_history, ms_key):
    for row in reversed(ms_history):
        v = row.get(ms_key)
        if finite(v) and float(v) > 0:
            return row.get("date"), float(v)
    return None

def latest_wd_mark(wd_history, key, usd_mxn_rate):
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

def deposits_between(ledger, after_date, upto_date):
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

def update_sleeve(st, mark, deposits_usd):
    if mark is None:
        return False, None
    mark_date, mark_nav = mark
    if not mark_date or mark_date <= st["last_date"]:
        return False, None
    if not finite(mark_nav) or mark_nav <= 0 or st["last_nav"] <= 0:
        return False, f"mark invalido ({mark_nav}) el {mark_date}; sleeve congeleado"
    growth = (mark_nav - deposits_usd) / st["last_nav"]
    if not finite(growth) or growth <= 0:
        return False, f"growth factor invalido ({growth:.4f}) el {mark_date}"
    warning = None
    if abs(growth - 1.0) > SUSPICIOUS_MOVE:
        warning = f"movimiento sospechoso de {(growth - 1.0) * 100:+.1f}% el {mark_date}"
    st["alloc_usd"] *= growth
    st["tr_index"] *= growth
    st["last_nav"] = mark_nav
    st["last_date"] = mark_date
    return True, warning

def should_rebalance(prev_date, new_date):
    return bool(prev_date) and prev_date[:7] != new_date[:7]

def log_rebalance(dir_path, date_str, total_nav, drift):
    l_path = os.path.join(dir_path, LEDGER_FILE)
    row = f"| {date_str} | PORTFOLIO | REBALANCE | 1.00 | ${total_nav:,.2f} | ${total_nav:,.2f} | Rebalance | FILLED | Max drift: {drift*100:.2f}pp |"
    
    if os.path.exists(l_path):
        with open(l_path, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        content = f"# Strategy 18: Efficient Frontier Allocation Ledger\n\n| Date | Ticker | Action | Shares | Price | Net Capital Impact | Order Type | Status | Note |\n| :--- | :--- | :---: | :---: | :---: | :--- | :--- | :--- | :--- |\n---\n"
        
    lines = content.split("\n")
    insert_idx = None
    for i, line in enumerate(lines):
        if line.strip() == "---":
            insert_idx = i
            break
    if insert_idx is not None:
        lines.insert(insert_idx, row)
    else:
        lines.append(row)
    with open(l_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

def apply_rebalance(state, today):
    weights = normalized_weights()
    total = sum(s["alloc_usd"] for s in state["sleeves"].values())
    drift = max(abs(s["alloc_usd"] / total - weights[k])
                for k, s in state["sleeves"].items()) if total > 0 else 0.0
    for k, s in state["sleeves"].items():
        s["alloc_usd"] = weights[k] * total
    state["rebalances"].append(dict(date=today, nav_usd=round(total, 2), max_drift=round(drift, 4)))
    log_rebalance(DIR, today, total, drift)

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
            raise SystemExit(f"[strategy18] sin marca inicial para: {missing}; no se puede inicializar")
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
        log_rebalance(DIR, today, INITIAL_CAPITAL_USD, 0.0)
        print(f"[strategy18] portafolio inicializado (${INITIAL_CAPITAL_USD:,.0f} USD)")

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

    if prev_hist_date and should_rebalance(prev_hist_date, today):
        apply_rebalance(state, today)

    nav = sum(s["alloc_usd"] for s in state["sleeves"].values())
    row = dict(date=today, nav_usd=round(nav, 2),
               idx={k: round(s["tr_index"], 6) for k, s in state["sleeves"].items()})
    
    if state["history"] and state["history"][-1]["date"] == today:
        state["history"][-1] = row
    else:
        state["history"].append(row)
    state["last_updated"] = now_str
    state["total_portfolio_value_usd"] = nav  # standard key for watchdog

    with open(os.path.join(DIR, STATE_FILE), "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

    write_report(state, nav, usd_mxn_rate, warnings, now_str, today)
    print(f"Strategy 18 NAV: ${nav:,.2f} USD")

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
        "# Strategy 18: Efficient Frontier Allocation Execution Report",
        f"**Execution Date:** {now_str} | **Strategy Version:** Live V1",
        f"* **Total Portfolio NAV:** ${nav:,.2f} USD",
        f"* **Inception Date:** {state['inception']} ({live_days} calendar days elapsed)",
        f"* **Virtual Capital Base:** ${state['initial_capital_usd']:,.2f} USD",
        f"* **USD/MXN Rate:** {usd_mxn_rate:.4f}",
        "",
        "## 1. Portfolio Performance Summary",
        "| Metric | Realized (live) |",
        "| :--- | ---: |",
        f"| Return since inception | {pct(roi)} |",
        f"| Sharpe (Rf {BONDIA_HURDLE * 100:.2f}%) | {f'{sharpe:+.2f}' if sharpe is not None else '--'} |",
        f"| Realized Volatility (Ann.) | {f'{vol * 100:.2f}%' if vol is not None else '--'} |",
        f"| Max drawdown | {f'{max_dd * 100:.2f}%' if max_dd is not None else '--'} |",
        "",
        "## 2. Current Allocations & Sleeves",
        "| Sleeve | Target weight | Current weight | TR since inception | Last mark date |",
        "| :--- | ---: | ---: | ---: | :--- |",
    ]
    for key, cfg in SLEEVES.items():
        st = state["sleeves"][key]
        cur_w = st["alloc_usd"] / nav if nav > 0 else 0.0
        L.append(f"| {cfg['label']} ({cfg['short']}) | {state['weights'][key] * 100:.1f}% | "
                 f"{cur_w * 100:.1f}% | {pct(st['tr_index'] - 1.0)} | {st['last_date']} |")

    L += ["", "## 3. Rebalances"]
    if state["rebalances"]:
        L += ["| Date | NAV | Max weight drift |", "| :--- | ---: | ---: |"]
        for rb in state["rebalances"]:
            L.append(f"| {rb['date']} | ${rb['nav_usd']:,.2f} | {rb['max_drift'] * 100:.1f}pp |")
    else:
        L.append("*None yet (monthly, first mark of each month).*")

    L += ["", "## 4. Warnings"]
    if warnings:
        L += [f"- {w}" for w in warnings]
    else:
        L.append("*None this cycle.*")

    with open(os.path.join(DIR, REPORT_FILE), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")

if __name__ == "__main__":
    main()
