"""
EFFICIENT FRONTIER v2: graduation-day target allocation
========================================================
Builds the target portfolio for the day strategies graduate to live money.

Improvements over scratch/efficient_frontier.py (v1):
- Full daily-strategy roster (11 strategies vs 6): adds S9, S12-S15.
- Weight cap (25%) so the optimizer can't concentrate into one backtest.
- Adds Equal-Risk-Contribution (risk parity) portfolio, which needs no
  expected-return estimates -- the weakest input in mean-variance work.
- Intraday sleeves (S10/S11/S16) are explicitly EXCLUDED from the frontier:
  their backtest NAVs cover only ~60 in-sample days, and the walk-forward
  validation (walkforward_report.md) showed near-zero/negative out-of-sample
  edge. They are treated as capped satellites in the recommendation.
- Hurdle/Sharpe use Bondia 6.53% (the live do-nothing alternative), matching
  graduation_report.py.

Output: efficient_frontier_report.md (repo root).
Usage:  python scratch/efficient_frontier_v2.py
"""
import os
import datetime
import numpy as np
import pandas as pd
from scipy.optimize import minimize

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RF = 0.0653          # Bondia sweep -- the live hurdle
W_CAP = 0.25         # max weight per strategy
TRADING_DAYS = 252

# name -> (csv, date column, nav column)
SERIES = {
    "S1 Alpha Growth": ("backtest_nav.csv", 0, "strategy"),
    "S2 MACD": ("macd_backtest_nav.csv", 0, "NAV"),
    "S4 US DCF": ("us_stocks_dcf_backtest_nav.csv", "Date", "NAV"),
    "S5 Alternatives": ("alternatives_backtest_nav.csv", "Date", "NAV"),
    "S6 High Beta": ("high_beta_backtest_nav.csv", "Date", "NAV"),
    "S8 Dividends": ("dividends_backtest_nav.csv", "date", "nav"),
    "S9 Stat-Arb": ("strategy9_backtest_nav.csv", "Date", "NAV"),
    "S12 VTTL": ("strategy12_backtest_nav.csv", "Date", "NAV"),
    "S13 CARA": ("strategy13_backtest_nav.csv", "Date", "NAV"),
    "S14 HEDGE": ("strategy14_backtest_nav.csv", "Date", "NAV"),
    "S15 TRACK": ("strategy15_backtest_nav.csv", "Date", "NAV"),
}

# Current S7 target weights (run_live_multi_strategy.py) restricted to the
# daily strategies and renormalized, for comparison on the same window.
CURRENT_TARGETS = {
    "S1 Alpha Growth": 0.10, "S2 MACD": 0.00, "S4 US DCF": 0.15,
    "S5 Alternatives": 0.05, "S6 High Beta": 0.05, "S8 Dividends": 0.10,
    "S9 Stat-Arb": 0.15, "S12 VTTL": 0.05, "S13 CARA": 0.05,
    "S14 HEDGE": 0.05, "S15 TRACK": 0.05,
}


def load_series():
    dfs = {}
    for name, (fname, date_col, nav_col) in SERIES.items():
        path = os.path.join(ROOT, fname)
        if not os.path.exists(path):
            print(f"  [WARN] missing {fname}; {name} excluded")
            continue
        df = pd.read_csv(path)
        dc = df.columns[0] if date_col == 0 else date_col
        df["d"] = pd.to_datetime(df[dc])
        s = df.set_index("d")[nav_col].astype(float)
        s = s[~s.index.duplicated(keep="last")].sort_index()
        dfs[name] = s
    return pd.DataFrame(dfs).ffill().dropna()


def stats(w, mu, cov):
    w = np.asarray(w)
    r = float(w @ mu)
    v = float(np.sqrt(w @ cov @ w))
    return r, v, (r - RF) / v if v > 0 else 0.0


def max_dd_of(weights, rets):
    port = (rets @ weights).add(1.0).cumprod()
    return float((port / port.cummax() - 1.0).min())


def solve(objective, n, bounds, extra_cons=()):
    cons = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}, *extra_cons]
    best = None
    for seed in (np.full(n, 1.0 / n), np.random.default_rng(42).dirichlet(np.ones(n))):
        res = minimize(objective, seed, method="SLSQP", bounds=bounds,
                       constraints=cons, options={"maxiter": 500})
        if res.success and (best is None or res.fun < best.fun):
            best = res
    return best.x if best is not None else np.full(n, 1.0 / n)


def main():
    print("Loading NAV series...")
    navs = load_series()
    names = list(navs.columns)
    n = len(names)
    print(f"  {n} strategies, {len(navs)} overlapping days "
          f"({navs.index[0].date()} .. {navs.index[-1].date()})")

    rets = navs.pct_change().dropna()
    mu = rets.mean().values * TRADING_DAYS
    cov = rets.cov().values * TRADING_DAYS
    vols = rets.std().values * np.sqrt(TRADING_DAYS)
    corr = rets.corr()

    bounds = tuple((0.0, W_CAP) for _ in range(n))

    # Max Sharpe (capped)
    w_msr = solve(lambda w: -stats(w, mu, cov)[2], n, bounds)
    # Global minimum variance (capped)
    w_gmv = solve(lambda w: stats(w, mu, cov)[1], n, bounds)

    # Equal risk contribution (risk parity)
    def erc_obj(w):
        w = np.asarray(w)
        port_var = w @ cov @ w
        rc = w * (cov @ w)
        target = port_var / n
        return float(np.sum((rc - target) ** 2)) * 1e6
    w_erc = solve(erc_obj, n, tuple((0.001, W_CAP) for _ in range(n)))

    # Hurdle-filtered risk parity (RECOMMENDED): risk parity rewards low
    # volatility even when a strategy loses to cash (e.g. a 2%-vol strategy
    # returning less than Bondia gets a huge weight). Drop anything whose
    # common-window return is below the hurdle, re-solve ERC on the rest --
    # the dropped slice is better held in Bondia directly.
    keep = [i for i in range(n) if mu[i] > RF]
    dropped = [names[i] for i in range(n) if i not in keep]
    cov_k = cov[np.ix_(keep, keep)]
    nk = len(keep)

    def erc_obj_k(w):
        w = np.asarray(w)
        port_var = w @ cov_k @ w
        rc = w * (cov_k @ w)
        return float(np.sum((rc - port_var / nk) ** 2)) * 1e6

    cons_k = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
    res_k = minimize(erc_obj_k, np.full(nk, 1.0 / nk), method="SLSQP",
                     bounds=tuple((0.001, W_CAP) for _ in range(nk)),
                     constraints=cons_k, options={"maxiter": 500})
    w_ercf = np.zeros(n)
    for j, i in enumerate(keep):
        w_ercf[i] = res_k.x[j]

    # Current S7 targets, renormalized over these names
    w_cur = np.array([CURRENT_TARGETS.get(nm, 0.0) for nm in names])
    w_cur = w_cur / w_cur.sum()

    ports = {
        "Risk Parity, hurdle-filtered (RECOMMENDED)": w_ercf,
        "Risk Parity (all)": w_erc,
        "Max Sharpe (25% cap)": w_msr,
        "Min Variance (25% cap)": w_gmv,
        "Current S7 targets": w_cur,
    }

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    L = [
        "# Efficient Frontier v2 — Graduation-Day Target Allocation",
        f"**Generated:** {now} | Window: {navs.index[0].date()} → {navs.index[-1].date()} "
        f"({len(rets)} overlapping trading days) | Hurdle/Rf: Bondia {RF*100:.2f}% | Cap: {W_CAP*100:.0f}%/strategy",
        "",
        "Covariances and returns come from each strategy's own backtest NAV series over",
        "the common window. **Intraday sleeves (S10/S11/S16) are excluded**: only ~60",
        "in-sample days of NAV exist, and the walk-forward validation showed",
        "near-zero/negative out-of-sample edge — see the satellite policy below.",
        "",
        "## 1. Individual Strategy Metrics (common window)",
        "| Strategy | Ann. return | Ann. vol | Sharpe (Rf 6.53%) | Max DD |",
        "| :--- | ---: | ---: | ---: | ---: |",
    ]
    for i, nm in enumerate(names):
        e = np.zeros(n); e[i] = 1.0
        L.append(f"| {nm} | {mu[i]*100:+.2f}% | {vols[i]*100:.2f}% | "
                 f"{(mu[i]-RF)/vols[i]:+.2f} | {max_dd_of(e, rets)*100:.2f}% |")

    L += ["", "## 2. Correlation Matrix",
          "| | " + " | ".join(nm.split()[0] for nm in names) + " |",
          "| :--- |" + " ---: |" * n]
    for nm in names:
        L.append("| " + nm.split()[0] + " | " +
                 " | ".join(f"{corr.loc[nm, c]:.2f}" for c in names) + " |")

    L += ["", "## 3. Candidate Portfolios",
          "| Portfolio | Ann. return | Ann. vol | Sharpe | Max DD |",
          "| :--- | ---: | ---: | ---: | ---: |"]
    for label, w in ports.items():
        r, v, s = stats(w, mu, cov)
        L.append(f"| **{label}** | {r*100:+.2f}% | {v*100:.2f}% | {s:+.2f} | "
                 f"{max_dd_of(w, rets)*100:.2f}% |")

    L += ["", "## 4. Weights",
          "| Strategy | **RP hurdle-filtered** | RP (all) | Max Sharpe | Min Variance | Current S7 |",
          "| :--- | ---: | ---: | ---: | ---: | ---: |"]
    for i, nm in enumerate(names):
        L.append(f"| {nm} | **{w_ercf[i]*100:.1f}%** | {w_erc[i]*100:.1f}% | "
                 f"{w_msr[i]*100:.1f}% | {w_gmv[i]*100:.1f}% | {w_cur[i]*100:.1f}% |")
    if dropped:
        L.append("")
        L.append(f"*Hurdle filter dropped (return < Bondia {RF*100:.2f}% on this window): "
                 f"{', '.join(dropped)} — their slice belongs in Bondia cash, not in a "
                 f"strategy that underperforms it.*")

    L += [
        "",
        "## 5. Satellite policy for the intraday sleeves (from walk-forward evidence)",
        "- **S10 VWAP:** out-of-sample mean +1.2%/60d, contained drawdowns → optional",
        "  satellite, **max 5%** of the live portfolio, and only after its 90-day live",
        "  record confirms the walk-forward.",
        "- **S11 CCI-ADX:** out-of-sample mean −3.2%/60d → **0%** until a live record",
        "  contradicts the walk-forward.",
        "- **S16 Router:** out-of-sample mean +0.9%/60d with a −48% drawdown window →",
        "  **0%**; research project, not an allocation.",
        "",
        "## 6. How to use this",
        "- **Hurdle-filtered risk parity is the recommended core**: risk contributions are",
        "  equalized (no dependence on noisy expected-return estimates) but only across",
        "  strategies that actually beat Bondia on the common window.",
        "- Max Sharpe shows what historical means would suggest — treat it as an upper",
        "  bound on concentration, not a target; backtest means are noisy.",
        "- Strategies only receive their weight once they reach **READY** in",
        "  graduation_report.md; until then their slice stays in Bondia cash.",
        "- Caveats: MXN and USD series are mixed (FX exposure differs by sleeve); the",
        "  common window (2022→) is mostly one market era; S13 is retired standalone",
        "  and its weight should be folded into S14/S15 at implementation.",
    ]

    out = os.path.join(ROOT, "efficient_frontier_report.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print(f"Report written to {out}\n")

    for label, w in ports.items():
        r, v, s = stats(w, mu, cov)
        print(f"{label:<24} ret {r*100:+6.2f}%  vol {v*100:5.2f}%  sharpe {s:+5.2f}  "
              f"dd {max_dd_of(w, rets)*100:6.2f}%")


if __name__ == "__main__":
    main()
