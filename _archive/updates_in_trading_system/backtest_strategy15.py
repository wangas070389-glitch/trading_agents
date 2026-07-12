"""
Strategy 15: TRACK - Fixed-Share Expert Tracking (Herbster & Warmuth 1998)
==========================================================================
Upgrade de Strategy 14 (HEDGE). Un solo cambio en la actualizacion:

    v_i   = w_i * exp(eta * r_i)                (multiplicative weights)
    w'_i  = (1 - alpha) * v_i / sum(v) + alpha/N   (fixed share)

El termino alpha impide el colapso de pesos: ningun experto queda nunca
"demasiado atras" para recuperar liderazgo. Consecuencia teorica:

  HEDGE garantiza:  cercania al mejor experto ESTATICO de toda la historia.
  TRACK garantiza:  cercania a la mejor SECUENCIA de expertos con k cambios
                    (tracking regret ~ [(k+1) ln N + k ln(T/k)] / eta + eta*T*R^2/8)

alpha = tasa esperada de cambios de liderazgo. Declarado a priori: 1/252
(~1 cambio de regimen tolerado por anio). Rejilla completa incluida.

Reusa expertos, datos y metricas de backtest_strategy14 (mismo directorio).

Uso:
  python backtest_strategy15.py             # datos reales
  python backtest_strategy15.py --selftest  # QUIEBRE ESTRUCTURAL sintetico:
                                            # demuestra TRACK vs HEDGE
"""
import os
import sys
import argparse
import numpy as np
import pandas as pd

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from backtest_strategy14 import (  # noqa: E402
    PARAMS as P14, EXPERT_NAMES, TRADING_DAYS,
    load_real_data, build_tqqq_returns, expert_allocations,
    psr, dsr, perf,
)

PARAMS = dict(P14)
PARAMS.update({
    "alpha": 1.0 / 252.0,   # fixed-share: ~1 cambio de liderazgo tolerado/anio
    "n_trials": 1,
})


# ---------------- Sintetico con QUIEBRE ESTRUCTURAL ----------------
def load_regime_break_data(seed=15):
    """Era 1 (anios 0-9): bull tendencial fuerte -> ganan QQQ_BH/VTTL.
    Era 2 (anios 9-18): lateral volatil con drift ~0 en USD y peso fuerte
    -> gana CASH_MXN. El mejor experto ESTATICO es distinto del mejor
    experto EN CADA ERA: el escenario exacto donde HEDGE sufre y TRACK no."""
    rng = np.random.default_rng(seed)
    n = 18 * TRADING_DAYS
    half = n // 2
    idx = pd.bdate_range("2007-04-11", periods=n)
    vol = np.empty(n); vol[0] = 0.16
    for i in range(1, n):
        target_v = 0.15 if i < half else 0.30
        vol[i] = np.clip(vol[i-1] + 0.03 * (target_v - vol[i-1]) + 0.015 * rng.standard_normal(), 0.07, 1.0)
    drift = np.where(np.arange(n) < half, 0.16 / TRADING_DAYS, -0.02 / TRADING_DAYS)
    r_q = drift + vol / np.sqrt(TRADING_DAYS) * rng.standard_normal(n)
    qqq = 100 * np.exp(np.cumsum(r_q))
    vix = vol * 100 * (1 + 0.05 * rng.standard_normal(n))
    vix3m = pd.Series(vix, index=idx).rolling(40, min_periods=1).mean().values * 1.05
    r_h = 0.05 / TRADING_DAYS - 0.5 * (vol - 0.18) / TRADING_DAYS + 0.05 / np.sqrt(TRADING_DAYS) * rng.standard_normal(n)
    hyg = 100 * np.exp(np.cumsum(r_h))
    ief = 100 * np.exp(np.cumsum(0.03 / TRADING_DAYS + 0.06 / np.sqrt(TRADING_DAYS) * rng.standard_normal(n)))
    fx_drift = np.where(np.arange(n) < half, 0.01 / TRADING_DAYS, -0.02 / TRADING_DAYS)
    r_fx = fx_drift - 0.30 * (r_q - drift) + 0.07 / np.sqrt(TRADING_DAYS) * rng.standard_normal(n)
    fx = 11 * np.exp(np.cumsum(r_fx))
    return pd.DataFrame({"qqq": qqq, "tqqq": np.nan, "vix": vix, "vix3m": vix3m,
                         "hyg": hyg, "ief": ief, "fx": fx}, index=idx), idx[half]


# ---------------- Motor con actualizacion recursiva de pesos ----------------
def run_backtest(data, p, alpha, initial_nav=200000.0, eta_override=None):
    n = len(data)
    K = len(EXPERT_NAMES)
    r_tqqq = build_tqqq_returns(data, p).values
    r_fx = data["fx"].pct_change().fillna(0.0).values
    mxn_d = p["mxn_cash_yield"] / TRADING_DAYS
    usd_d = p["usd_cash_yield"] / TRADING_DAYS

    allocs = expert_allocations(data, p)
    W = np.stack([allocs[e][0].shift(1).fillna(0.0).values for e in EXPERT_NAMES])
    F = np.stack([allocs[e][1].shift(1).fillna(0.0).values for e in EXPERT_NAMES])

    eta = eta_override if eta_override is not None else np.sqrt(8.0 * np.log(K) / n)
    clip = p["clip_daily"]

    wk = np.full(K, 1.0 / K)          # pesos recursivos (fixed-share necesita estado)
    G_real = np.zeros(K)
    r_expert_hist = np.zeros((n, K))
    nav = np.empty(n); nav[0] = initial_nav
    w_held, f_held = 0.0, 0.0
    weights_hist = np.zeros((n, K)); weights_hist[0] = wk
    agg_logret_clipped = 0.0
    turn = 0.0

    for i in range(1, n):
        tgt_w = float(wk @ W[:, i])
        tgt_f = float(wk @ F[:, i])
        if abs(tgt_w - w_held) > p["rebalance_band"] * max(abs(tgt_w), 0.05):
            turn += abs(tgt_w - w_held); w_new = tgt_w
        else:
            w_new = w_held
        d_f = abs(tgt_f - f_held) * (1 - w_new)
        cost = abs(w_new - w_held) * p["cost_bps_etf"] / 1e4 + d_f * p["cost_bps_fx"] / 1e4
        w_held, f_held = w_new, tgt_f

        rt = r_tqqq[i] if np.isfinite(r_tqqq[i]) else 0.0
        rt_mxn = (1 + rt) * (1 + r_fx[i]) - 1
        r_usd_mxn = (1 + usd_d) * (1 + r_fx[i]) - 1
        cash_ret = (1 - f_held) * mxn_d + f_held * r_usd_mxn
        r_day = w_held * rt_mxn + (1 - w_held) * cash_ret - cost
        nav[i] = nav[i - 1] * (1 + r_day)
        agg_logret_clipped += np.log1p(np.clip(r_day, -clip, clip))
        if w_held != 0:
            w_held = w_held * (1 + rt_mxn) / (1 + r_day)

        # retornos realizados de expertos + actualizacion HEDGE + FIXED-SHARE
        g_i = np.empty(K)
        for k in range(K):
            r_k = W[k, i] * rt_mxn + (1 - W[k, i]) * ((1 - F[k, i]) * mxn_d + F[k, i] * r_usd_mxn)
            r_expert_hist[i, k] = np.log1p(np.clip(r_k, -clip, clip))
            g_i[k] = r_expert_hist[i, k]
            G_real[k] += np.log1p(r_k)
        v = wk * np.exp(eta * (g_i - g_i.max()))
        v /= v.sum()
        wk = (1.0 - alpha) * v + alpha / K
        weights_hist[i] = wk

    nav_s = pd.Series(nav, index=data.index, name="NAV")

    # comparadores de regret:
    cum = r_expert_hist.cumsum(axis=0)
    static_best = float(cum[-1].max())
    # mejor secuencia por anio calendario (comparador de tracking, k = #anios-1)
    years = data.index.year
    piecewise_best = 0.0
    k_switches = -1
    prev_best = None
    for y in np.unique(years):
        mask = years == y
        seg = r_expert_hist[mask].sum(axis=0)
        b = int(np.argmax(seg))
        piecewise_best += float(seg[b])
        if prev_best is not None and b != prev_best:
            k_switches += 1 if k_switches >= 0 else 0
        if prev_best is None:
            k_switches = 0
        elif b != prev_best:
            k_switches += 1
        prev_best = b

    return {"nav": nav_s, "eta": eta,
            "weights": pd.DataFrame(weights_hist, index=data.index, columns=EXPERT_NAMES),
            "G_experts": dict(zip(EXPERT_NAMES, G_real)),
            "regret_static": static_best - agg_logret_clipped,
            "regret_tracking": piecewise_best - agg_logret_clipped,
            "k_switches": int(k_switches),
            "turnover": turn / max((data.index[-1] - data.index[0]).days / 365.25, 1e-6)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    dir_path = os.path.dirname(os.path.abspath(__file__))
    p = PARAMS

    print("=" * 80)
    print("STRATEGY 15: TRACK - FIXED-SHARE EXPERT TRACKING")
    print("=" * 80)

    if args.selftest:
        print("[SELF-TEST] Mundo sintetico con QUIEBRE ESTRUCTURAL a mitad de periodo.")
        data, break_date = load_regime_break_data()
        print(f"Datos: {data.index[0].date()} -> {data.index[-1].date()} | quiebre: {break_date.date()}")
    else:
        data = load_real_data()
        break_date = None
        print(f"Datos: {data.index[0].date()} -> {data.index[-1].date()} ({len(data)} dias)")

    # TRACK (fixed-share) vs HEDGE (alpha=0) sobre los MISMOS datos
    res_t = run_backtest(data, p, alpha=p["alpha"])
    res_h = run_backtest(data, p, alpha=0.0)
    m_t, m_h = perf(res_t["nav"], p["rf_mxn"]), perf(res_h["nav"], p["rf_mxn"])

    print(f"\n--- TRACK (alpha=1/252) vs HEDGE (alpha=0) | eta={res_t['eta']:.3f} ---")
    print(f"  TRACK: CAGR {m_t['cagr']*100:6.2f}%  Sharpe {m_t['sharpe']:5.2f}  MaxDD {m_t['max_dd']*100:7.2f}%")
    print(f"  HEDGE: CAGR {m_h['cagr']*100:6.2f}%  Sharpe {m_h['sharpe']:5.2f}  MaxDD {m_h['max_dd']*100:7.2f}%")

    print(f"\n--- Regret contra dos comparadores (log-riqueza recortada) ---")
    print(f"  vs mejor experto ESTATICO:            TRACK {res_t['regret_static']:7.3f} | HEDGE {res_h['regret_static']:7.3f}")
    print(f"  vs mejor SECUENCIA anual (k={res_t['k_switches']} cambios): TRACK {res_t['regret_tracking']:7.3f} | HEDGE {res_h['regret_tracking']:7.3f}")
    print("  (TRACK debe ganar en el segundo comparador; ese es el teorema.)")

    if args.selftest and break_date is not None:
        # La ventaja de fixed-share solo existe cuando los pesos SE CONCENTRAN.
        # Con eta teorica (pequena) los pesos quedan casi uniformes y ambos
        # algoritmos coinciden. Repetimos en regimen de concentracion (eta=3):
        print(f"\n--- DEMO en regimen de CONCENTRACION (eta=3.0) ---")
        rt3 = run_backtest(data, p, alpha=p["alpha"], eta_override=3.0)
        rh3 = run_backtest(data, p, alpha=0.0, eta_override=3.0)
        mt3, mh3 = perf(rt3["nav"], p["rf_mxn"]), perf(rh3["nav"], p["rf_mxn"])
        print(f"  TRACK: CAGR {mt3['cagr']*100:6.2f}%  Sharpe {mt3['sharpe']:5.2f}  regret_track {rt3['regret_tracking']:7.3f}")
        print(f"  HEDGE: CAGR {mh3['cagr']*100:6.2f}%  Sharpe {mh3['sharpe']:5.2f}  regret_track {rh3['regret_tracking']:7.3f}")
        for name, res in (("TRACK", rt3), ("HEDGE", rh3)):
            era1 = res["weights"].loc[:break_date]
            champ = era1.iloc[-1].idxmax()
            w_break = float(era1.iloc[-1][champ])
            w_after = res["weights"].loc[break_date:][champ]
            below = w_after[w_after < w_break / 2.0]
            dias = (below.index[0] - break_date).days if len(below) else None
            print(f"  {name}: campeon era-1 '{champ}' con peso {w_break*100:.0f}% al quiebre; "
                  f"tarda {dias if dias is not None else 'INF (nunca)'} dias en caer a la mitad")

    mxn_d = p["mxn_cash_yield"] / TRADING_DAYS
    bondia = pd.Series(200000.0 * (1 + mxn_d) ** np.arange(len(data)), index=data.index)
    excess = (res_t["nav"].pct_change() - bondia.pct_change()).dropna()
    d = dsr(excess, p["n_trials"])
    print(f"\n  PSR: {psr(excess, 0.0):.4f} | DSR (N={p['n_trials']}): {d['dsr']:.4f} | Rotacion: {res_t['turnover']:.2f}x")

    print("\n--- Sensibilidad a alpha (rejilla completa) ---")
    for a in (0.0, 1/1260, 1/504, 1/252, 1/126, 1/63):
        r2 = run_backtest(data, p, alpha=a)
        m2 = perf(r2["nav"], p["rf_mxn"])
        label = "HEDGE" if a == 0 else f"1/{int(round(1/a))}"
        print(f"  alpha={label:7s}: CAGR {m2['cagr']*100:6.2f}%  Sharpe {m2['sharpe']:5.2f}  "
              f"regret_track {r2['regret_tracking']:7.3f}")

    pd.concat([res_t["nav"], res_t["weights"]], axis=1).to_csv(
        os.path.join(dir_path, "strategy15_backtest_nav.csv"))

    w_final = res_t["weights"].iloc[-1]
    report = f"""# Strategy 15: TRACK - Fixed-Share Expert Tracking
**Periodo:** {data.index[0].date()} a {data.index[-1].date()} | **Modo:** {'SELF-TEST (quiebre estructural)' if args.selftest else 'Datos reales'}
**alpha:** 1/252 | **eta:** {res_t['eta']:.3f}

## TRACK vs HEDGE (mismos datos, mismos expertos)
| Metrica | TRACK | HEDGE (S14) |
| :--- | ---: | ---: |
| CAGR | {m_t['cagr']*100:.2f}% | {m_h['cagr']*100:.2f}% |
| Sharpe | {m_t['sharpe']:.2f} | {m_h['sharpe']:.2f} |
| MaxDD | {m_t['max_dd']*100:.2f}% | {m_h['max_dd']*100:.2f}% |
| Regret vs mejor estatico | {res_t['regret_static']:.3f} | {res_h['regret_static']:.3f} |
| Regret vs mejor secuencia anual | {res_t['regret_tracking']:.3f} | {res_h['regret_tracking']:.3f} |

## Pesos finales
{chr(10).join(f'* {e}: {w_final[e]*100:.1f}%' for e in EXPERT_NAMES)}

## Nota honesta
TRACK paga una prima pequena y permanente (el alpha redistribuido) a cambio de
adaptabilidad ante cambios de regimen. En un mundo SIN cambios de liderazgo,
HEDGE gana por esa prima. La eleccion entre S14 y S15 es una apuesta sobre la
frecuencia de rotacion de regimen, no sobre cual es "mejor" en abstracto.
"""
    with open(os.path.join(dir_path, "strategy15_backtest_report.md"), "w", encoding="utf-8") as f:
        f.write(report)
    print("\nNAV+pesos -> strategy15_backtest_nav.csv | Reporte -> strategy15_backtest_report.md")
    print("=" * 80)


if __name__ == "__main__":
    main()
