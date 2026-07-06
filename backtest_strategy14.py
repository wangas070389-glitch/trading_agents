"""
Strategy 14: HEDGE - Online Expert Aggregation (Multiplicative Weights)
=======================================================================
Freund & Schapire (1997). N expertos = reglas de asignacion causales.
Peso del experto i en t:   w_i(t) ~ exp(eta * G_i(t-1))
donde G_i = retorno log acumulado del experto i hasta t-1 (recortado).

GARANTIA (teorema, no backtest): para toda secuencia de retornos,
   G_best - G_hedge  <=  ln(N)/eta + eta * T * R^2 / 8
con R = rango del retorno diario recortado. El agregador queda cerca del
mejor experto EN RETROSPECTIVA sin saber por adelantado cual es.

Expertos (todos causales, todos en MXN, senal t -> retorno t+1):
  E1 CASH_MXN   Bondia
  E2 QQQ_BH     buy & hold QQQ
  E3 VTTL       trend SMA200 + vol targeting (Strategy 12)
  E4 CARA       score cross-asset VIXts/credito/trend (Strategy 13)
  E5 TSMOM      momentum 12-1 con vol targeting
  E6 CASH_USD   dolar (hedge estructural del peso)

El portafolio final mezcla las POSICIONES de los expertos (w_tqqq, f_usd)
con los pesos del agregador -> ejecutable con los mismos instrumentos.

Uso:
  python backtest_strategy14.py             # datos reales (desde 2007)
  python backtest_strategy14.py --selftest  # sintetico: valida logica
"""
import os
import sys
import argparse
import numpy as np
import pandas as pd
from scipy import stats

PARAMS = {
    # agregador
    "eta": None,               # None -> tasa teorica sqrt(8 ln N / T); o fija (p.ej. 4.0)
    "clip_daily": 0.10,        # recorte del retorno diario del experto (acota R)
    "rebalance_band": 0.15,
    # expertos VTTL / CARA / TSMOM
    "sma_trend_vttl": 200, "sma_trend_cara": 100, "credit_sma": 60,
    "tsmom_lookback": 252, "tsmom_skip": 21,
    "vol_window": 20, "vol_target": 0.20, "max_exposure": 1.5,
    "leverage_etf": 3.0, "hedge_usd_frac_cara": 0.35,
    # costos / tasas
    "cost_bps_etf": 5.0, "cost_bps_fx": 2.0,
    "tqqq_expense": 0.0095, "usd_financing": 0.045,
    "mxn_cash_yield": 0.0653, "usd_cash_yield": 0.045, "rf_mxn": 0.095,
    "n_trials": 1,
}
TRADING_DAYS = 252
EXPERT_NAMES = ["CASH_MXN", "QQQ_BH", "VTTL", "CARA", "TSMOM", "CASH_USD"]


# ---------------- Metricas ----------------
def psr(returns, sr_b):
    r = pd.Series(returns).dropna().values
    n = len(r)
    if n < 30:
        return np.nan
    sr = r.mean() / r.std(ddof=1)
    g3, g4 = stats.skew(r), stats.kurtosis(r, fisher=False)
    d = np.sqrt(max(1e-12, 1 - g3 * sr + (g4 - 1) / 4 * sr ** 2))
    return float(stats.norm.cdf((sr - sr_b) * np.sqrt(n - 1) / d))


def dsr(returns, n_trials):
    r = pd.Series(returns).dropna().values
    n = len(r)
    sr = r.mean() / r.std(ddof=1)
    g3, g4 = stats.skew(r), stats.kurtosis(r, fisher=False)
    v = max((1 - g3 * sr + (g4 - 1) / 4 * sr ** 2) / (n - 1), 1e-12)
    eu = 0.5772156649015329
    N = max(int(n_trials), 1)
    s = 0.0 if N == 1 else np.sqrt(v) * ((1 - eu) * stats.norm.ppf(1 - 1 / N) + eu * stats.norm.ppf(1 - 1 / (N * np.e)))
    return {"sr_star": s, "dsr": psr(returns, s)}


def perf(nav, rf):
    r = nav.pct_change().dropna()
    yrs = max((nav.index[-1] - nav.index[0]).days / 365.25, 1e-6)
    cagr = (nav.iloc[-1] / nav.iloc[0]) ** (1 / yrs) - 1
    vol = r.std(ddof=1) * np.sqrt(TRADING_DAYS)
    return {"cagr": cagr, "vol": vol, "sharpe": (cagr - rf) / vol if vol > 0 else np.nan,
            "max_dd": float((nav / nav.cummax() - 1).min())}


# ---------------- Datos (mismas fuentes que S13) ----------------
def load_real_data():
    import yfinance as yf
    def dl(t, start):
        df = yf.download(t, start=start, progress=False, auto_adjust=True)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]
        return df["Close"]
    qqq = dl("QQQ", "2006-01-01")
    data = pd.DataFrame({
        "qqq": qqq,
        "tqqq": dl("TQQQ", "2010-02-11").reindex(qqq.index),
        "vix": dl("^VIX", "2006-01-01").reindex(qqq.index).ffill(),
        "vix3m": dl("^VIX3M", "2006-01-01").reindex(qqq.index).ffill(),
        "hyg": dl("HYG", "2007-04-11").reindex(qqq.index),
        "ief": dl("IEF", "2006-01-01").reindex(qqq.index),
        "fx": dl("MXN=X", "2006-01-01").reindex(qqq.index).ffill(),
    })
    return data.dropna(subset=["qqq", "vix", "vix3m", "hyg", "ief", "fx"])


def load_synthetic_data(seed=13):
    rng = np.random.default_rng(seed)
    n = 19 * TRADING_DAYS
    idx = pd.bdate_range("2007-04-11", periods=n)
    vol = np.empty(n); vol[0] = 0.20
    for i in range(1, n):
        vol[i] = np.clip(vol[i-1] + 0.03 * (0.20 - vol[i-1]) + 0.02 * rng.standard_normal(), 0.08, 1.0)
    r_q = 0.10 / TRADING_DAYS + vol / np.sqrt(TRADING_DAYS) * rng.standard_normal(n)
    qqq = 100 * np.exp(np.cumsum(r_q))
    vix = vol * 100 * (1 + 0.05 * rng.standard_normal(n))
    vix3m = pd.Series(vix, index=idx).rolling(40, min_periods=1).mean().values * 1.05
    r_h = 0.05 / TRADING_DAYS - 0.5 * (vol - 0.20) / TRADING_DAYS + 0.05 / np.sqrt(TRADING_DAYS) * rng.standard_normal(n)
    hyg = 100 * np.exp(np.cumsum(r_h))
    ief = 100 * np.exp(np.cumsum(0.03 / TRADING_DAYS + 0.06 / np.sqrt(TRADING_DAYS) * rng.standard_normal(n)))
    r_fx = 0.03 / TRADING_DAYS - 0.35 * r_q + 0.08 / np.sqrt(TRADING_DAYS) * rng.standard_normal(n)
    fx = 11 * np.exp(np.cumsum(r_fx))
    return pd.DataFrame({"qqq": qqq, "tqqq": np.nan, "vix": vix, "vix3m": vix3m,
                         "hyg": hyg, "ief": ief, "fx": fx}, index=idx)


def build_tqqq_returns(data, p):
    r = data["qqq"].pct_change()
    drag = (p["leverage_etf"] - 1) * p["usd_financing"] / TRADING_DAYS + p["tqqq_expense"] / TRADING_DAYS
    synth = p["leverage_etf"] * r - drag
    if data["tqqq"].notna().sum() > TRADING_DAYS:
        real = data["tqqq"].pct_change()
        return real.where(real.notna(), synth)
    return synth


# ---------------- Posiciones objetivo de cada experto ----------------
def expert_allocations(data, p):
    """Devuelve por experto: (w_tqqq, f_usd_del_cash), series causales SIN shift.
    El shift(1) se aplica una sola vez en el motor."""
    r_qqq = data["qqq"].pct_change()
    rvol = r_qqq.rolling(p["vol_window"]).std(ddof=1) * np.sqrt(TRADING_DAYS)
    base = (p["vol_target"] / rvol).clip(upper=p["max_exposure"])
    zeros = pd.Series(0.0, index=data.index)

    # E3 VTTL
    trend200 = data["qqq"] > data["qqq"].rolling(p["sma_trend_vttl"]).mean()
    w_vttl = (base * trend200).fillna(0.0) / p["leverage_etf"]

    # E4 CARA
    ratio = data["hyg"] / data["ief"]
    score = ((data["vix3m"] > data["vix"]).astype(int)
             + (ratio > ratio.rolling(p["credit_sma"]).mean()).astype(int)
             + (data["qqq"] > data["qqq"].rolling(p["sma_trend_cara"]).mean()).astype(int))
    exp_cara = base.where(score == 3, base * 0.5).where(score >= 2, 0.0).fillna(0.0)
    w_cara = exp_cara / p["leverage_etf"]
    f_cara = (score.rolling(3).max() <= 1).astype(float) * p["hedge_usd_frac_cara"]

    # E5 TSMOM 12-1
    mom = data["qqq"].shift(p["tsmom_skip"]) / data["qqq"].shift(p["tsmom_lookback"]) - 1
    w_tsm = (base * (mom > 0)).fillna(0.0) / p["leverage_etf"]

    # E2 QQQ_BH: exposicion 1.0 sin apalancar -> w_tqqq = 1/3
    w_bh = pd.Series(1.0 / p["leverage_etf"], index=data.index)

    return {
        "CASH_MXN": (zeros, zeros),
        "QQQ_BH":   (w_bh, zeros),
        "VTTL":     (w_vttl, zeros),
        "CARA":     (w_cara, f_cara.fillna(0.0)),
        "TSMOM":    (w_tsm, zeros),
        "CASH_USD": (zeros, pd.Series(1.0, index=data.index)),
    }


# ---------------- Motor ----------------
def run_backtest(data, p, initial_nav=200000.0, eta_override=None):
    n = len(data)
    r_tqqq = build_tqqq_returns(data, p).values
    r_fx = data["fx"].pct_change().fillna(0.0).values
    mxn_d = p["mxn_cash_yield"] / TRADING_DAYS
    usd_d = p["usd_cash_yield"] / TRADING_DAYS

    allocs = expert_allocations(data, p)
    K = len(EXPERT_NAMES)
    W = np.stack([allocs[e][0].shift(1).fillna(0.0).values for e in EXPERT_NAMES])   # K x n
    F = np.stack([allocs[e][1].shift(1).fillna(0.0).values for e in EXPERT_NAMES])

    eta = eta_override if eta_override is not None else (
        p["eta"] if p["eta"] is not None else np.sqrt(8.0 * np.log(K) / n))
    clip = p["clip_daily"]

    G = np.zeros(K)                      # log-retorno acumulado (recortado) por experto
    G_real = np.zeros(K)                 # sin recorte, para reporte
    agg_logret = 0.0
    nav = np.empty(n); nav[0] = initial_nav
    w_held, f_held = 0.0, 0.0
    weights_hist = np.zeros((n, K)); weights_hist[0] = 1.0 / K
    turn = 0.0

    for i in range(1, n):
        # pesos del agregador con informacion hasta t-1 (multiplicative weights)
        z = eta * (G - G.max())
        wk = np.exp(z); wk /= wk.sum()
        weights_hist[i] = wk

        # posicion mezclada
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
        agg_logret += np.log1p(np.clip(r_day, -clip, clip))
        if w_held != 0:
            w_held = w_held * (1 + rt_mxn) / (1 + r_day)

        # actualizar G de cada experto con SU retorno realizado del dia
        for k in range(K):
            r_k = W[k, i] * rt_mxn + (1 - W[k, i]) * ((1 - F[k, i]) * mxn_d + F[k, i] * r_usd_mxn)
            G[k] += np.log1p(np.clip(r_k, -clip, clip))
            G_real[k] += np.log1p(r_k)

    nav_s = pd.Series(nav, index=data.index, name="NAV")
    yrs = max((data.index[-1] - data.index[0]).days / 365.25, 1e-6)
    # regret empirico vs cota teorica (en log-riqueza recortada)
    regret_emp = float(G.max() - agg_logret)
    bound = np.log(K) / eta + eta * n * (2 * clip) ** 2 / 8.0
    return {"nav": nav_s, "eta": eta, "weights": pd.DataFrame(weights_hist, index=data.index, columns=EXPERT_NAMES),
            "G_experts": dict(zip(EXPERT_NAMES, G_real)), "regret_emp": regret_emp,
            "regret_bound": float(bound), "turnover": turn / yrs,
            "best_expert": EXPERT_NAMES[int(np.argmax(G))]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    dir_path = os.path.dirname(os.path.abspath(__file__))
    p = PARAMS

    print("=" * 80)
    print("STRATEGY 14: HEDGE - ONLINE EXPERT AGGREGATION (MULTIPLICATIVE WEIGHTS)")
    print("=" * 80)
    if args.selftest:
        print("[SELF-TEST] Sintetico: valida logica y el TEOREMA, no evalua la estrategia.")
        data = load_synthetic_data()
    else:
        data = load_real_data()
    print(f"Datos: {data.index[0].date()} -> {data.index[-1].date()} ({len(data)} dias)")

    res = run_backtest(data, p)
    m = perf(res["nav"], p["rf_mxn"])
    mxn_d = p["mxn_cash_yield"] / TRADING_DAYS
    bondia = pd.Series(200000.0 * (1 + mxn_d) ** np.arange(len(data)), index=data.index)
    excess = (res["nav"].pct_change() - bondia.pct_change()).dropna()
    d = dsr(excess, p["n_trials"])

    print(f"\n--- HEDGE agregado (MXN) | eta={res['eta']:.3f} ---")
    print(f"  CAGR {m['cagr']*100:7.2f}%  Vol {m['vol']*100:6.2f}%  Sharpe {m['sharpe']:5.2f}  MaxDD {m['max_dd']*100:7.2f}%")
    print("\n--- Log-riqueza final por experto (CAGR aprox) ---")
    yrs = (data.index[-1] - data.index[0]).days / 365.25
    for e, g in sorted(res["G_experts"].items(), key=lambda kv: -kv[1]):
        print(f"  {e:9s}: {(np.exp(g / yrs) - 1)*100:7.2f}%/anio")
    print(f"\n--- VERIFICACION DEL TEOREMA ---")
    print(f"  Mejor experto en retrospectiva: {res['best_expert']}")
    print(f"  Regret empirico:  {res['regret_emp']:8.4f}  (log-riqueza)")
    print(f"  Cota teorica:     {res['regret_bound']:8.4f}")
    ok = res["regret_emp"] <= res["regret_bound"] + 1e-9
    print(f"  {'TEOREMA VERIFICADO: regret <= cota' if ok else 'VIOLACION: revisar implementacion'}")
    print(f"\n  Rotacion anual: {res['turnover']:.2f}x | PSR: {psr(excess, 0.0):.4f} | DSR (N={p['n_trials']}): {d['dsr']:.4f}")

    # sensibilidad a eta (el unico parametro del agregador)
    print("\n--- Sensibilidad a eta (rejilla completa) ---")
    for e_try in (0.5, 1.0, 2.0, 4.0, 8.0):
        r2 = run_backtest(data, p, eta_override=e_try)
        m2 = perf(r2["nav"], p["rf_mxn"])
        print(f"  eta={e_try:4.1f}: CAGR {m2['cagr']*100:6.2f}%  Sharpe {m2['sharpe']:5.2f}  "
              f"MaxDD {m2['max_dd']*100:7.2f}%  regret {r2['regret_emp']:.3f} <= {r2['regret_bound']:.3f}")

    out = pd.concat([res["nav"], res["weights"]], axis=1)
    out.to_csv(os.path.join(dir_path, "strategy14_backtest_nav.csv"))

    w_final = res["weights"].iloc[-1]
    report = f"""# Strategy 14: HEDGE - Online Expert Aggregation
**Periodo:** {data.index[0].date()} a {data.index[-1].date()} | **Modo:** {'SELF-TEST' if args.selftest else 'Datos reales'} | **eta:** {res['eta']:.3f}

## Resultado agregado (MXN)
CAGR {m['cagr']*100:.2f}% | Vol {m['vol']*100:.2f}% | Sharpe {m['sharpe']:.2f} | MaxDD {m['max_dd']*100:.2f}%

## Garantia verificada
* Mejor experto retrospectivo: **{res['best_expert']}**
* Regret empirico **{res['regret_emp']:.4f}** <= cota teorica **{res['regret_bound']:.4f}** {'(OK)' if ok else '(VIOLADA)'}

## Pesos finales del agregador
{chr(10).join(f'* {e}: {w_final[e]*100:.1f}%' for e in EXPERT_NAMES)}

## Nota honesta
La garantia es RELATIVA: cercania al mejor experto en retrospectiva. Si todos
los expertos son malos, HEDGE sera casi tan malo como el menos malo. Su valor
es eliminar el riesgo de eleccion, no crear alpha.
"""
    with open(os.path.join(dir_path, "strategy14_backtest_report.md"), "w", encoding="utf-8") as f:
        f.write(report)
    print("\nNAV+pesos -> strategy14_backtest_nav.csv | Reporte -> strategy14_backtest_report.md")
    print("=" * 80)


if __name__ == "__main__":
    main()


def run_strategy14_backtest_for_api():
    p = PARAMS
    data = load_real_data()
    res = run_backtest(data, p)
    m = perf(res["nav"], p["rf_mxn"])
    
    initial_nav = float(res["nav"].iloc[0])
    
    dates = [d.strftime("%Y-%m-%d") for d in res["nav"].index]
    strategy_vals = [float(x) for x in res["nav"].values]
    
    r_qqq_mxn = ((1.0 + data["qqq"].pct_change()) * (1.0 + data["fx"].pct_change()) - 1.0).fillna(0.0)
    bench_vals = [float(x) for x in (initial_nav * (1.0 + r_qqq_mxn).cumprod()).values]
    
    mxn_d = p["mxn_cash_yield"] / TRADING_DAYS
    cash_vals = [float(x) for x in (initial_nav * (1.0 + mxn_d) ** np.arange(len(data)))]
    
    return {
        "dates": dates,
        "strategy": strategy_vals,
        "cash": cash_vals,
        "benchmark": bench_vals,
        "trade_log": [],
        "metrics": {
            "strategy_return": float((res["nav"].iloc[-1] / initial_nav - 1.0) * 100),
            "strategy_cagr": float(m["cagr"] * 100),
            "cash_return": float((cash_vals[-1] / initial_nav - 1.0) * 100),
            "benchmark_return": float((bench_vals[-1] / initial_nav - 1.0) * 100),
            "benchmark_cagr": float(perf(pd.Series(bench_vals, index=res["nav"].index), p["rf_mxn"])["cagr"] * 100),
            "sharpe": float(m["sharpe"]) if not pd.isna(m["sharpe"]) else 0.0,
            "drawdown": float(m["max_dd"] * 100),
            "n_trades": int(res["n_rebalances"]),
            "win_rate": 100.0,
            "total_fees": 0.0,
            "total_pnl": float(res["nav"].iloc[-1] - initial_nav)
        }
    }

