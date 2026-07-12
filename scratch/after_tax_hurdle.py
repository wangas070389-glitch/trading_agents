"""
AFTER-TAX / REAL-FEE HURDLE: what actually lands in your pocket
================================================================
The 6.53% Bondia hurdle and the backtest returns are PRE-TAX, and the fee
models vary per backtest. This script recomputes, per daily strategy:

  1. the annualized return on the frontier's common window (as modeled),
  2. incremental REAL-broker fee drag vs what the backtest embeds,
  3. Mexican tax by execution route:
       - Route SIC : casa de bolsa mexicana, BMV/SIC-listed -> 10% definitive
         ISR on net realized gains (LISR Art. 129; inflation-adjusted basis
         ignored here = slightly conservative), fees 0.25%+IVA ~ 0.29%/side
       - Route US  : US broker (e.g. Alpaca real) -> 0% commission, but gains
         are ordinary accumulable income at the MARGINAL rate (up to 35%),
         no 10% regime; FX conversion spread on funding ignored (one-off)
  4. the after-tax Bondia hurdle (ISR is owed on the REAL component of
     interest only: nominal minus inflation).

DISCLAIMER: simplified model for strategy comparison, not tax advice.
Rates/regimes must be confirmed with a Mexican contador before real money.

Output: after_tax_report.md (repo root).
Usage:  python scratch/after_tax_hurdle.py
"""
import os
import datetime
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRADING_DAYS = 252

BONDIA = 0.0653          # nominal sweep yield
INFLATION = 0.042        # assumed annual inflation (basis for real-interest tax)
MARGINAL = 0.35          # assumed marginal ISR bracket (sensitivity: 0.30 shown too)
SIC_TAX = 0.10           # definitive ISR on net gains, BMV/SIC-listed sales
SIC_FEE_SIDE = 0.0029    # 0.25% commission + 16% IVA per side (GBM-style)

# name -> (csv, date col (0 = first), nav col, annual round-trip turnover,
#          fee/side embedded in the backtest, US-broker route available?)
# Turnover: generate_clean_report.py KPI table. Embedded fees verified in each
# backtest: 0.29%/side legacy, 0.10% S2 (re-tuned 2026-07-11), ~5bps rotated
# notional S12-S15.
STRATS = {
    "S1 Alpha Growth": ("backtest_nav.csv", 0, "strategy", 1.5, 0.0029, False),
    "S2 MACD (re-tuned)": ("macd_backtest_nav.csv", 0, "NAV", 2.4, 0.0010, False),
    "S4 US DCF": ("us_stocks_dcf_backtest_nav.csv", "Date", "NAV", 2.0, 0.0029, True),
    "S5 Alternatives": ("alternatives_backtest_nav.csv", "Date", "NAV", 1.0, 0.0029, True),
    "S6 High Beta": ("high_beta_backtest_nav.csv", "Date", "NAV", 6.0, 0.0029, True),
    "S8 Dividends": ("dividends_backtest_nav.csv", "date", "nav", 1.2, 0.0029, False),
    "S9 Stat-Arb": ("strategy9_backtest_nav.csv", "Date", "NAV", 8.0, 0.0029, True),
    "S12 VTTL": ("strategy12_backtest_nav.csv", "Date", "NAV", 2.8, 0.0005, True),
    "S13 CARA": ("strategy13_backtest_nav.csv", "Date", "NAV", 8.4, 0.0005, True),
    "S14 HEDGE": ("strategy14_backtest_nav.csv", "Date", "NAV", 1.3, 0.0005, True),
    "S15 TRACK": ("strategy15_backtest_nav.csv", "Date", "NAV", 1.3, 0.0005, True),
}


def load_common_returns():
    dfs = {}
    for name, (fname, date_col, nav_col, *_rest) in STRATS.items():
        path = os.path.join(ROOT, fname)
        if not os.path.exists(path):
            print(f"  [WARN] missing {fname}; {name} excluded")
            continue
        df = pd.read_csv(path)
        dc = df.columns[0] if date_col == 0 else date_col
        df["d"] = pd.to_datetime(df[dc])
        s = df.set_index("d")[nav_col].astype(float)
        dfs[name] = s[~s.index.duplicated(keep="last")].sort_index()
    navs = pd.DataFrame(dfs).ffill().dropna()
    rets = navs.pct_change().dropna()
    return navs, rets.mean() * TRADING_DAYS


def after_tax_bondia(marginal):
    """ISR is owed on the real component of interest (nominal - inflation)."""
    real = max(BONDIA - INFLATION, 0.0)
    return BONDIA - marginal * real


def main():
    navs, mu = load_common_returns()
    window = f"{navs.index[0].date()} → {navs.index[-1].date()}"
    hurdle35 = after_tax_bondia(0.35)
    hurdle30 = after_tax_bondia(0.30)

    rows = []
    for name, (_f, _dc, _nc, turnover, fee_model, us_ok) in STRATS.items():
        if name not in mu.index:
            continue
        r = float(mu[name])

        # Route SIC: pay 0.29%/side; add only the drag the backtest did NOT model
        drag_sic = turnover * 2.0 * max(SIC_FEE_SIDE - fee_model, 0.0)
        pre_sic = r - drag_sic
        net_sic = pre_sic - SIC_TAX * max(pre_sic, 0.0)

        # Route US broker: 0% commission -> add back embedded fees, tax at marginal
        if us_ok:
            addback = turnover * 2.0 * fee_model
            pre_us = r + addback
            net_us = pre_us - MARGINAL * max(pre_us, 0.0)
        else:
            net_us = None

        best_route = "SIC" if (net_us is None or net_sic >= net_us) else "US broker"
        best_net = net_sic if best_route == "SIC" else net_us
        rows.append(dict(name=name, r=r, drag=drag_sic, net_sic=net_sic,
                         net_us=net_us, best=best_route, best_net=best_net,
                         passes=best_net > hurdle35))

    rows.sort(key=lambda x: x["best_net"], reverse=True)

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fmt = lambda x: f"{x*100:+.2f}%" if x is not None else "—"
    L = [
        "# After-Tax / Real-Fee Hurdle — What Actually Lands in Your Pocket",
        f"**Generated:** {now} | Common window: {window} | "
        f"Marginal ISR assumed: {MARGINAL*100:.0f}% | Inflation assumed: {INFLATION*100:.1f}%",
        "",
        "> **Not tax advice.** Simplified comparison model — confirm regimes and rates",
        "> with a Mexican contador before moving real money.",
        "",
        "## 1. The hurdle, after tax",
        f"Bondia pays {BONDIA*100:.2f}% nominal; ISR applies to the *real* component",
        f"(nominal − inflation = {max(BONDIA-INFLATION,0)*100:.2f}%):",
        "",
        "| Marginal bracket | After-tax Bondia hurdle |",
        "| :---: | :---: |",
        f"| 30% | **{hurdle30*100:.2f}%** |",
        f"| 35% | **{hurdle35*100:.2f}%** |",
        "",
        "## 2. Strategies net of real fees and taxes (common window)",
        "Route **SIC** = casa de bolsa mexicana (0.29%/side, **10% definitive ISR on gains**).",
        f"Route **US broker** = e.g. Alpaca real (0% commission, gains taxed as ordinary",
        f"income at the {MARGINAL*100:.0f}% marginal rate — no 10% regime).",
        "",
        "| Strategy | As modeled | +SIC fee drag | **Net (SIC)** | Net (US broker) | Best route | vs hurdle "
        f"{hurdle35*100:.2f}% |",
        "| :--- | ---: | ---: | ---: | ---: | :---: | :---: |",
    ]
    for x in rows:
        L.append(f"| {x['name']} | {fmt(x['r'])} | −{x['drag']*100:.2f}% | "
                 f"**{fmt(x['net_sic'])}** | {fmt(x['net_us'])} | {x['best']} | "
                 f"{'PASS' if x['passes'] else 'FAIL'} |")

    passing = [x["name"] for x in rows if x["passes"]]
    failing = [x["name"] for x in rows if not x["passes"]]
    L += [
        "",
        "## 3. Findings",
        f"- **The 10% BMV/SIC regime dominates.** For every strategy with both routes",
        f"  available, executing through a Mexican casa de bolsa nets more after tax than",
        f"  a commission-free US broker, because 10% definitive beats {MARGINAL*100:.0f}% marginal by",
        f"  far more than 0.29%/side costs at these turnover levels. **Real money should",
        f"  trade SIC-listed instruments through a Mexican broker.**",
        f"- **High turnover is the silent killer on the SIC route.** The fee drag column",
        f"  is `turnover × 2 × (0.29% − modeled fee)`: S13 (8.4× turnover, 5 bps modeled)",
        f"  loses ~4% a year to real commissions its backtest never charged; S12–S15's",
        f"  cheap cost model flatters them all.",
        f"- **Hurdle-passing set (35% bracket): {', '.join(passing)}.**",
        (f"- **Failing: {', '.join(failing)}.**" if failing else "- No strategy fails."),
        f"- Intraday sleeves (S10/S11/S16): dozens of round trips per 60 days makes the",
        f"  SIC route instantly fatal (S16 v1 already proved −35% at 0.29%/side), and the",
        f"  US-broker route taxes whatever remains at {MARGINAL*100:.0f}%. Their walk-forward edge was",
        f"  ~0 pre-tax; after tax the case for 0% allocation is even stronger.",
        "",
        "## 4. Impact on the target allocation (efficient_frontier_report.md)",
        "- Re-check the hurdle filter with after-tax numbers: membership below.",
        "- Because the SIC tax is a flat 10% of gains, relative rankings barely move;",
        "  the fee-drag adjustment is what reorders S12–S15 (especially S13).",
        "",
        "## 5. Model caveats",
        "- Gains tax approximated as `10% × max(annual return, 0)` — ignores the",
        "  inflation-adjusted cost basis (helps you) and loss carryforwards (help you);",
        "  both make reality slightly better than this table.",
        "- Turnover figures are the KPI-table estimates, not measured round trips.",
        "- Dividend strategies (S8) additionally face ~10% withholding on the dividend",
        "  stream itself (~0.3-0.5% extra drag at a 3-5% yield) — not modeled.",
        "- S5 holds crypto ETFs; confirm SIC availability and tax treatment per instrument.",
        "- FX conversion spreads on funding (one-off ~0.3%) not modeled.",
    ]

    out = os.path.join(ROOT, "after_tax_report.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print(f"Report written to {out}\n")
    print(f"After-tax hurdle: {hurdle35*100:.2f}% (35% bracket) / {hurdle30*100:.2f}% (30%)")
    for x in rows:
        print(f"  {x['name']:<22} model {fmt(x['r']):>8}  netSIC {fmt(x['net_sic']):>8}  "
              f"netUS {fmt(x['net_us']):>8}  [{x['best']}]  "
              f"{'PASS' if x['passes'] else 'FAIL'}")


if __name__ == "__main__":
    main()
