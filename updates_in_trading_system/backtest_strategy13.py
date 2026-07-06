"""
Strategy 13: CARA - Cross-Asset Risk Appetite
=============================================
Regimen por votacion de 3 mercados (informacion ortogonal al precio de QQQ):
  1. VIX term structure:  VIX3M > VIX  (contango = apetito de riesgo)
  2. Credito:             HYG/IEF > SMA(60) del ratio (high yield firme)
  3. Tendencia:           QQQ > SMA(100)

Exposicion escalonada con vol targeting (via TQQQ a peso/3, resto en cash):
  score 3 -> exposicion completa   min(vol_target/vol20d, cap)
  score 2 -> media exposicion
  score<=1 -> 0 equity + HEDGE FX: 35% del cash rota a USD (tasa USD + USDMXN),
              el activo que historicamente sube en la cola izquierda del peso.

Sin modelos ajustados. Senal en cierre t -> retorno t+1. Contabilidad en MXN.

Uso:
  python backtest_strategy13.py             # datos reales (desde 2007, incluye GFC)
  python backtest_strategy13.py --selftest  # sintetico: solo valida logica
"""
import os
import sys
import argparse
import numpy as np
import pandas as pd
from scipy import stats

PARAMS = {
    "credit_sma": 60,
    "trend_sma": 100,
    "vol_window": 20,
    "vol_target": 0.20,
    "max_exposure": 1.5,
    "rebalance_band": 0.20,
    "leverage_etf": 3.0,
    "hedge_usd_frac": 0.35,    # fraccion del cash rotada a USD cuando score<=1
    "cost_bps_etf": 5.0,
    "cost_bps_fx": 2.0,
    "tqqq_expense": 0.0095,
    "usd_financing": 0.045,
    "mxn_cash_yield": 0.0653,
    "usd_cash_yield": 0.045,
    "rf_mxn": 0.095,
    "n_trials": 1,             # sumar el conteo real del overfitting_ledger
}
TRADING_DAYS = 252


# ---------------- Metricas (identicas a Strategy 12) ----------------
def probabilistic_sharpe_ratio(returns, sr_benchmark):
    r = pd.Series(returns).dropna().values
    n = len(r)
    if n < 30:
        return np.nan
    sr = r.mean() / r.std(ddof=1)
    g3, g4 = stats.skew(r), stats.kurtosis(r, fisher=False)
    denom = np.sqrt(max(1e-12, 1.0 - g3 * sr + (g4 - 1.0) / 4.0 * sr ** 2))
    return float(stats.norm.cdf((sr - sr_benchmark) * np.sqrt(n - 1) / denom))


def deflated_sharpe_ratio(returns, n_trials):
    r = pd.Series(returns).dropna().values
    n = len(r)
    sr = r.mean() / r.std(ddof=1)
    g3, g4 = stats.skew(r), stats.kurtosis(r, fisher=False)
    var_sr = max((1.0 - g3 * sr + (g4 - 1.0) / 4.0 * sr ** 2) / (n - 1), 1e-12)
    euler = 0.5772156649015329
    N = max(int(n_trials), 1)
    sr_star = 0.0 if N == 1 else np.sqrt(var_sr) * (
        (1 - euler) * stats.norm.ppf(1 - 1.0 / N) + euler * stats.norm.ppf(1 - 1.0 / (N * np.e)))
    return {"sr_star": float(sr_star), "dsr": probabilistic_sharpe_ratio(returns, sr_star)}


def perf_metrics(nav, rf_annual):
    rets = nav.pct_change().dropna()
    yrs = max((nav.index[-1] - nav.index[0]).days / 365.25, 1e-6)
    cagr = (nav.iloc[-1] / nav.iloc[0]) ** (1 / yrs) - 1
    vol = rets.std(ddof=1) * np.sqrt(TRADING_DAYS)
    return {"cagr": cagr, "vol": vol,
            "sharpe": (cagr - rf_annual) / vol if vol > 0 else np.nan,
            "max_dd": float((nav / nav.cummax() - 1).min())}


# ---------------- Datos ----------------
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


def load_synthetic_data(seed=11):
    """Series correlacionadas con estructura riesgo-on/riesgo-off. SOLO valida logica."""
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
    # credito: cae con vol alta; fx: sube (peso deprecia) en riesgo-off
    r_hyg = 0.05 / TRADING_DAYS - 0.5 * (vol - 0.20) / TRADING_DAYS + 0.05 / np.sqrt(TRADING_DAYS) * rng.standard_normal(n)
    hyg = 100 * np.exp(np.cumsum(r_hyg))
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


# ---------------- Motor ----------------
def compute_signals(data, p):
    ratio = data["hyg"] / data["ief"]
    s_vix = (data["vix3m"] > data["vix"]).astype(int)
    s_credit = (ratio > ratio.rolling(p["credit_sma"]).mean()).astype(int)
    s_trend = (data["qqq"] > data["qqq"].rolling(p["trend_sma"]).mean()).astype(int)
    score = s_vix + s_credit + s_trend
    rvol = data["qqq"].pct_change().rolling(p["vol_window"]).std(ddof=1) * np.sqrt(TRADING_DAYS)
    base = (p["vol_target"] / rvol).clip(upper=p["max_exposure"])
    exposure = base.where(score == 3, base * 0.5)
    exposure = exposure.where(score >= 2, 0.0)
    # Hedge FX con confirmacion: requiere score<=1 durante 3 dias consecutivos
    # (evita churn por parpadeo del score alrededor del umbral; declarado a priori)
    hedge_on = (score.rolling(3).max() <= 1).astype(float)
    return score, exposure.fillna(0.0), hedge_on


def run_backtest(data, p, initial_nav=200000.0):
    r_tqqq = build_tqqq_returns(data, p).values
    r_fx = data["fx"].pct_change().fillna(0.0).values
    score, exposure, hedge_on = compute_signals(data, p)

    # SIN LOOK-AHEAD
    tgt_w = (exposure / p["leverage_etf"]).shift(1).fillna(0.0).values
    tgt_h = hedge_on.shift(1).fillna(0.0).values

    mxn_d = p["mxn_cash_yield"] / TRADING_DAYS
    usd_d = p["usd_cash_yield"] / TRADING_DAYS

    n = len(data)
    nav = np.empty(n); nav[0] = initial_nav
    w, f_usd = 0.0, 0.0
    weights = np.zeros(n); hedges = np.zeros(n)
    turn_etf = turn_fx = 0.0

    for i in range(1, n):
        # rebalanceo equity con banda
        wt = tgt_w[i]
        if wt <= 0:
            des_w = 0.0
        elif w <= 0 or abs(w / wt - 1) > p["rebalance_band"]:
            des_w = wt
        else:
            des_w = w
        d_w = abs(des_w - w); w = des_w
        # hedge FX: toggle completo con la senal
        des_f = p["hedge_usd_frac"] if tgt_h[i] > 0 else 0.0
        d_f_notional = abs(des_f - f_usd) * (1.0 - w)
        f_usd = des_f

        cost = d_w * p["cost_bps_etf"] / 1e4 + d_f_notional * p["cost_bps_fx"] / 1e4
        turn_etf += d_w; turn_fx += d_f_notional

        rt = r_tqqq[i] if np.isfinite(r_tqqq[i]) else 0.0
        rt_mxn = (1 + rt) * (1 + r_fx[i]) - 1
        r_usd_cash_mxn = (1 + usd_d) * (1 + r_fx[i]) - 1
        cash_ret = (1 - f_usd) * mxn_d + f_usd * r_usd_cash_mxn

        r_day = w * rt_mxn + (1 - w) * cash_ret - cost
        nav[i] = nav[i - 1] * (1 + r_day)
        if w > 0:
            w = w * (1 + rt_mxn) / (1 + r_day)
        weights[i] = w; hedges[i] = f_usd

    nav_s = pd.Series(nav, index=data.index, name="NAV")
    r_qqq_mxn = ((1 + data["qqq"].pct_change()) * (1 + pd.Series(r_fx, index=data.index)) - 1).fillna(0.0)
    yrs = max((data.index[-1] - data.index[0]).days / 365.25, 1e-6)
    return {"nav": nav_s,
            "bh_qqq": initial_nav * (1 + r_qqq_mxn).cumprod(),
            "bondia": pd.Series(initial_nav * (1 + mxn_d) ** np.arange(n), index=data.index),
            "weights": pd.Series(weights, index=data.index),
            "hedge": pd.Series(hedges, index=data.index),
            "score": score,
            "turnover": (turn_etf + turn_fx) / yrs,
            "pct_full": float((score.shift(1) == 3).mean()),
            "pct_half": float((score.shift(1) == 2).mean()),
            "pct_out": float((score.shift(1) <= 1).mean())}


def robustness_grid(data, p):
    rows = []
    for cs in (40, 60, 80):
        for ts in (75, 100, 125):
            m = perf_metrics(run_backtest(data, dict(p, credit_sma=cs, trend_sma=ts))["nav"], p["rf_mxn"])
            rows.append({"CreditSMA": cs, "TrendSMA": ts, "CAGR": m["cagr"],
                         "Sharpe": m["sharpe"], "MaxDD": m["max_dd"]})
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    dir_path = os.path.dirname(os.path.abspath(__file__))
    p = PARAMS

    print("=" * 80)
    print("STRATEGY 13: CARA - CROSS-ASSET RISK APPETITE")
    print("=" * 80)
    if args.selftest:
        print("[SELF-TEST] Sintetico: valida logica, NO evalua la estrategia.")
        data = load_synthetic_data()
    else:
        data = load_real_data()
    print(f"Datos: {data.index[0].date()} -> {data.index[-1].date()} ({len(data)} dias)")

    res = run_backtest(data, p)
    m = perf_metrics(res["nav"], p["rf_mxn"])
    m_bh = perf_metrics(res["bh_qqq"], p["rf_mxn"])
    excess = (res["nav"].pct_change() - res["bondia"].pct_change()).dropna()
    dsr = deflated_sharpe_ratio(excess, p["n_trials"])
    psr0 = probabilistic_sharpe_ratio(excess, 0.0)

    print("\n--- CARA (MXN) ---")
    print(f"  CAGR {m['cagr']*100:7.2f}%  Vol {m['vol']*100:6.2f}%  Sharpe {m['sharpe']:5.2f}  MaxDD {m['max_dd']*100:7.2f}%")
    print("--- QQQ Buy&Hold (MXN) ---")
    print(f"  CAGR {m_bh['cagr']*100:7.2f}%  Vol {m_bh['vol']*100:6.2f}%  Sharpe {m_bh['sharpe']:5.2f}  MaxDD {m_bh['max_dd']*100:7.2f}%")
    print(f"\n  Tiempo en score 3/2/<=1: {res['pct_full']*100:.0f}% / {res['pct_half']*100:.0f}% / {res['pct_out']*100:.0f}%")
    print(f"  Rotacion anual (ETF+FX): {res['turnover']:.2f}x")
    print(f"  PSR: {psr0:.4f} | DSR (N={p['n_trials']}): {dsr['dsr']:.4f}")
    print("  >>> Ajusta n_trials con tu overfitting_ledger. <<<")

    # Comparacion opcional contra Strategy 12 si existe su NAV
    s12_path = os.path.join(dir_path, "strategy12_backtest_nav.csv")
    if os.path.exists(s12_path) and not args.selftest:
        s12 = pd.read_csv(s12_path, index_col=0, parse_dates=True)["NAV"]
        common = res["nav"].index.intersection(s12.index)
        if len(common) > TRADING_DAYS:
            m12 = perf_metrics(s12.loc[common], p["rf_mxn"])
            m13c = perf_metrics(res["nav"].loc[common], p["rf_mxn"])
            print(f"\n--- vs Strategy 12 (periodo comun {common[0].date()}->{common[-1].date()}) ---")
            print(f"  CARA:  Sharpe {m13c['sharpe']:.2f}  MaxDD {m13c['max_dd']*100:.1f}%")
            print(f"  VTTL:  Sharpe {m12['sharpe']:.2f}  MaxDD {m12['max_dd']*100:.1f}%")

    grid = robustness_grid(data, p)
    print("\n--- Rejilla de robustez (completa, sin cherry-pick) ---")
    print(grid.to_string(index=False, formatters={
        "CAGR": lambda x: f"{x*100:6.2f}%", "Sharpe": lambda x: f"{x:5.2f}", "MaxDD": lambda x: f"{x*100:7.2f}%"}))
    disp = grid["Sharpe"].max() - grid["Sharpe"].min()
    print(f"\n  Dispersion de Sharpe: {disp:.2f} "
          f"{'(estable)' if disp < 0.35 else '(ALTA: sensibilidad a parametros)'}")

    pd.DataFrame({"NAV": res["nav"], "QQQ_BH_MXN": res["bh_qqq"], "BONDIA": res["bondia"],
                  "W_TQQQ": res["weights"], "HEDGE_USD": res["hedge"],
                  "SCORE": res["score"]}).to_csv(os.path.join(dir_path, "strategy13_backtest_nav.csv"))

    report = f"""# Strategy 13: CARA - Cross-Asset Risk Appetite
**Periodo:** {data.index[0].date()} a {data.index[-1].date()} | **Modo:** {'SELF-TEST' if args.selftest else 'Datos reales'}

## Resultados (MXN)
| Metrica | CARA | QQQ B&H |
| :--- | ---: | ---: |
| CAGR | {m['cagr']*100:.2f}% | {m_bh['cagr']*100:.2f}% |
| Vol anual | {m['vol']*100:.2f}% | {m_bh['vol']*100:.2f}% |
| Sharpe (rf {p['rf_mxn']*100:.1f}% MXN) | {m['sharpe']:.2f} | {m_bh['sharpe']:.2f} |
| Max Drawdown | {m['max_dd']*100:.2f}% | {m_bh['max_dd']*100:.2f}% |

## Validacion
* PSR: **{psr0:.4f}** | DSR (N={p['n_trials']}): **{dsr['dsr']:.4f}** | Rotacion: {res['turnover']:.2f}x/anio
* Tiempo score 3 / 2 / <=1: {res['pct_full']*100:.0f}% / {res['pct_half']*100:.0f}% / {res['pct_out']*100:.0f}%

## Reglas
1. Voto 1: VIX3M > VIX (contango). Voto 2: HYG/IEF > SMA({p['credit_sma']}). Voto 3: QQQ > SMA({p['trend_sma']}).
2. Score 3 -> min({p['vol_target']:.0%}/vol20d, {p['max_exposure']}x) via TQQQ/3. Score 2 -> mitad. Score <=1 -> 0 equity.
3. Score <=1 activa hedge: {p['hedge_usd_frac']:.0%} del cash a USD (tasa USD + USDMXN).
4. Senal cierre t -> retorno t+1. Banda de rebalanceo {p['rebalance_band']:.0%}. Costos {p['cost_bps_etf']:.0f}/{p['cost_bps_fx']:.0f} bps.
"""
    with open(os.path.join(dir_path, "strategy13_backtest_report.md"), "w", encoding="utf-8") as f:
        f.write(report)
    print("\nNAV -> strategy13_backtest_nav.csv | Reporte -> strategy13_backtest_report.md")
    print("=" * 80)


if __name__ == "__main__":
    main()
