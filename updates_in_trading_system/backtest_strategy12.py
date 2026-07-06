"""
Strategy 12: Vol-Targeted Trend Leverage + MXN Carry (VTTL)
============================================================
Diseno con cero parametros ajustados in-sample. Todos los parametros se
declaran a priori (bloque PARAMS) y la rejilla de robustez reporta TODAS
las combinaciones vecinas sin seleccion.

Fuentes de retorno:
  1. Trend filter (SMA 200 QQQ): exposicion solo sobre tendencia.
  2. Vol targeting (Moreira & Muir 2017): peso = vol_target / vol_realizada.
  3. Carry estructural MXN: exposicion via TQQQ a peso/3; el capital libre
     (~2/3) rinde tasa MXN (Bondia). El costo implicito del 3x es tasa USD.

Sin SQQQ. Sin HMM. Sin look-ahead: senal en cierre t -> retorno t+1.
Contabilidad 100% en MXN (incluye USDMXN).

Uso:
  python backtest_strategy12.py            # datos reales via yfinance
  python backtest_strategy12.py --selftest # datos sinteticos (verificacion logica)
"""
import os
import sys
import argparse
import numpy as np
import pandas as pd
from scipy import stats

# ============================================================
# PARAMETROS DECLARADOS A PRIORI (no optimizados)
# ============================================================
PARAMS = {
    "sma_window": 200,        # filtro de tendencia sobre QQQ
    "vol_window": 20,         # ventana de vol realizada (dias)
    "vol_target": 0.20,       # 20% anualizado sobre la exposicion QQQ efectiva
    "max_exposure": 1.5,      # exposicion QQQ efectiva maxima (1.5x)
    "rebalance_band": 0.20,   # rebalancea solo si |w_actual/w_objetivo - 1| > 20%
    "leverage_etf": 3.0,      # TQQQ
    "cost_bps": 5.0,          # costo por rebalanceo (spread+slippage) en bps del notional rotado
    "tqqq_expense": 0.0095,   # expense ratio anual TQQQ
    "mxn_cash_yield": 0.0653, # Bondia (usa tu tasa vigente)
    "usd_financing": 0.045,   # costo de fondeo USD implicito del 3x (aprox SOFR+spread)
    "rf_mxn": 0.095,          # tasa libre de riesgo MXN para Sharpe/DSR
    "n_trials": 1,            # trials de ESTE diseno; suma los de tu overfitting_ledger al evaluar DSR
}

TRADING_DAYS = 252


# ============================================================
# Metricas: PSR / DSR (Bailey & Lopez de Prado)
# ============================================================
def probabilistic_sharpe_ratio(returns: pd.Series, sr_benchmark: float) -> float:
    r = returns.dropna().values
    n = len(r)
    if n < 30:
        return np.nan
    sr = r.mean() / r.std(ddof=1)  # SR por-periodo (no anualizado)
    g3 = stats.skew(r)
    g4 = stats.kurtosis(r, fisher=False)
    denom = np.sqrt(max(1e-12, 1.0 - g3 * sr + (g4 - 1.0) / 4.0 * sr ** 2))
    z = (sr - sr_benchmark) * np.sqrt(n - 1) / denom
    return float(stats.norm.cdf(z))


def deflated_sharpe_ratio(returns: pd.Series, n_trials: int) -> dict:
    r = returns.dropna().values
    n = len(r)
    sr = r.mean() / r.std(ddof=1)
    # Varianza del estimador de SR entre trials ~ aproximada con la del propio track
    g3 = stats.skew(r)
    g4 = stats.kurtosis(r, fisher=False)
    var_sr = (1.0 - g3 * sr + (g4 - 1.0) / 4.0 * sr ** 2) / (n - 1)
    var_sr = max(var_sr, 1e-12)
    euler = 0.5772156649015329
    N = max(int(n_trials), 1)
    if N == 1:
        sr_star = 0.0
    else:
        sr_star = np.sqrt(var_sr) * (
            (1.0 - euler) * stats.norm.ppf(1.0 - 1.0 / N)
            + euler * stats.norm.ppf(1.0 - 1.0 / (N * np.e))
        )
    dsr = probabilistic_sharpe_ratio(returns, sr_star)
    return {"sr_period": float(sr), "sr_star": float(sr_star), "dsr": float(dsr)}


def perf_metrics(nav: pd.Series, rf_annual: float) -> dict:
    rets = nav.pct_change().dropna()
    n_years = max((nav.index[-1] - nav.index[0]).days / 365.25, 1e-6)
    cagr = (nav.iloc[-1] / nav.iloc[0]) ** (1.0 / n_years) - 1.0
    vol = rets.std(ddof=1) * np.sqrt(TRADING_DAYS)
    sharpe = (cagr - rf_annual) / vol if vol > 0 else np.nan
    dd = (nav / nav.cummax() - 1.0).min()
    return {"cagr": cagr, "vol": vol, "sharpe": sharpe, "max_dd": float(dd),
            "final": float(nav.iloc[-1]), "rets": rets}


# ============================================================
# Datos
# ============================================================
def load_real_data() -> pd.DataFrame:
    import yfinance as yf
    qqq = yf.download("QQQ", start="1999-03-10", progress=False, auto_adjust=True)
    tqqq = yf.download("TQQQ", start="2010-02-11", progress=False, auto_adjust=True)
    fx = yf.download("MXN=X", start="1999-03-10", progress=False, auto_adjust=True)
    for df in (qqq, tqqq, fx):
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]
    out = pd.DataFrame({
        "qqq": qqq["Close"],
        "tqqq": tqqq["Close"].reindex(qqq.index),
        "fx": fx["Close"].reindex(qqq.index).ffill(),
    }).dropna(subset=["qqq", "fx"])
    return out


def load_synthetic_data(seed: int = 7) -> pd.DataFrame:
    """GBM con vol clusterizada. Solo para verificar la logica, NO para evaluar la estrategia."""
    rng = np.random.default_rng(seed)
    n = 26 * TRADING_DAYS
    idx = pd.bdate_range("2000-01-03", periods=n)
    vol = np.empty(n)
    vol[0] = 0.20
    for i in range(1, n):
        vol[i] = np.clip(vol[i - 1] + 0.02 * (0.22 - vol[i - 1]) + 0.015 * rng.standard_normal(), 0.08, 0.90)
    r = 0.10 / TRADING_DAYS + vol / np.sqrt(TRADING_DAYS) * rng.standard_normal(n)
    qqq = 100 * np.exp(np.cumsum(r))
    fx = 10 * np.exp(np.cumsum(0.03 / TRADING_DAYS + 0.10 / np.sqrt(TRADING_DAYS) * rng.standard_normal(n)))
    return pd.DataFrame({"qqq": qqq, "tqqq": np.nan, "fx": fx}, index=idx)


def build_tqqq_returns(data: pd.DataFrame, p: dict) -> pd.Series:
    """TQQQ real donde existe; pre-2010 sintetico: 3x diario - financiamiento - expense."""
    r_qqq = data["qqq"].pct_change()
    daily_drag = (p["leverage_etf"] - 1.0) * p["usd_financing"] / TRADING_DAYS + p["tqqq_expense"] / TRADING_DAYS
    synth = p["leverage_etf"] * r_qqq - daily_drag
    if data["tqqq"].notna().sum() > TRADING_DAYS:
        real = data["tqqq"].pct_change()
        return real.where(real.notna(), synth)
    return synth


# ============================================================
# Motor de backtest
# ============================================================
def run_backtest(data: pd.DataFrame, p: dict, initial_nav: float = 200000.0):
    r_qqq_usd = data["qqq"].pct_change()
    r_tqqq_usd = build_tqqq_returns(data, p)
    r_fx = data["fx"].pct_change().fillna(0.0)

    sma = data["qqq"].rolling(p["sma_window"]).mean()
    realized_vol = r_qqq_usd.rolling(p["vol_window"]).std(ddof=1) * np.sqrt(TRADING_DAYS)

    trend_on = (data["qqq"] > sma)
    raw_w = (p["vol_target"] / realized_vol).clip(upper=p["max_exposure"])
    target_exposure = (raw_w * trend_on).fillna(0.0)          # exposicion QQQ efectiva deseada
    target_w_tqqq = target_exposure / p["leverage_etf"]        # peso en TQQQ

    # SIN LOOK-AHEAD: senal del cierre t gobierna el retorno de t+1
    target_w_tqqq = target_w_tqqq.shift(1).fillna(0.0)

    cash_daily_mxn = p["mxn_cash_yield"] / TRADING_DAYS
    r_tqqq_mxn = (1.0 + r_tqqq_usd) * (1.0 + r_fx) - 1.0

    nav = np.empty(len(data))
    nav[0] = initial_nav
    w_held = 0.0
    turnover_total = 0.0
    n_rebalances = 0
    weights = np.zeros(len(data))

    tw = target_w_tqqq.values
    rt = r_tqqq_mxn.values
    for i in range(1, len(data)):
        # Rebalanceo con banda (evaluado con la senal vigente, precios de cierre previos)
        wt = tw[i]
        if wt <= 0.0:
            desired = 0.0
        elif w_held <= 0.0:
            desired = wt
        elif abs(w_held / wt - 1.0) > p["rebalance_band"]:
            desired = wt
        else:
            desired = w_held
        traded = abs(desired - w_held)
        cost = traded * p["cost_bps"] / 10000.0
        if traded > 1e-9:
            n_rebalances += 1
            turnover_total += traded
        w_held = desired

        r_day = w_held * (rt[i] if np.isfinite(rt[i]) else 0.0) + (1.0 - w_held) * cash_daily_mxn - cost
        nav[i] = nav[i - 1] * (1.0 + r_day)

        # deriva del peso con el movimiento del dia
        if w_held > 0.0 and np.isfinite(rt[i]):
            w_held = w_held * (1.0 + rt[i]) / (1.0 + r_day)
        weights[i] = w_held

    nav_s = pd.Series(nav, index=data.index, name="NAV")

    # Benchmarks en MXN
    r_qqq_mxn = ((1.0 + r_qqq_usd) * (1.0 + r_fx) - 1.0).fillna(0.0)
    bh_qqq = initial_nav * (1.0 + r_qqq_mxn).cumprod()
    bondia = initial_nav * (1.0 + cash_daily_mxn) ** np.arange(len(data))
    bondia = pd.Series(bondia, index=data.index)

    return {
        "nav": nav_s, "bh_qqq": bh_qqq, "bondia": bondia,
        "weights": pd.Series(weights, index=data.index),
        "turnover_annual": turnover_total / max((data.index[-1] - data.index[0]).days / 365.25, 1e-6),
        "n_rebalances": n_rebalances,
    }


# ============================================================
# Rejilla de robustez (se reporta COMPLETA, sin seleccion)
# ============================================================
def robustness_grid(data: pd.DataFrame, p: dict) -> pd.DataFrame:
    rows = []
    for sma_w in (150, 200, 250):
        for vt in (0.15, 0.20, 0.25):
            q = dict(p, sma_window=sma_w, vol_target=vt)
            res = run_backtest(data, q)
            m = perf_metrics(res["nav"], p["rf_mxn"])
            rows.append({"SMA": sma_w, "VolTarget": vt, "CAGR": m["cagr"],
                         "Sharpe": m["sharpe"], "MaxDD": m["max_dd"]})
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true", help="datos sinteticos para verificar logica")
    args = ap.parse_args()

    dir_path = os.path.dirname(os.path.abspath(__file__))
    p = PARAMS

    print("=" * 80)
    print("STRATEGY 12: VOL-TARGETED TREND LEVERAGE + MXN CARRY (VTTL)")
    print("=" * 80)

    if args.selftest:
        print("[SELF-TEST] Datos sinteticos: valida logica, NO evalua la estrategia.")
        data = load_synthetic_data()
    else:
        data = load_real_data()
    print(f"Datos: {data.index[0].date()} -> {data.index[-1].date()} ({len(data)} dias)")

    res = run_backtest(data, p)
    m = perf_metrics(res["nav"], p["rf_mxn"])
    m_bh = perf_metrics(res["bh_qqq"], p["rf_mxn"])
    m_cash = perf_metrics(res["bondia"], p["rf_mxn"])

    excess = (res["nav"].pct_change() - res["bondia"].pct_change()).dropna()
    dsr = deflated_sharpe_ratio(excess, p["n_trials"])
    psr0 = probabilistic_sharpe_ratio(excess, 0.0)

    print("\n--- VTTL (MXN) ---")
    print(f"  CAGR {m['cagr']*100:7.2f}%  Vol {m['vol']*100:6.2f}%  Sharpe(rf MXN) {m['sharpe']:5.2f}  MaxDD {m['max_dd']*100:7.2f}%")
    print("--- QQQ Buy&Hold (MXN) ---")
    print(f"  CAGR {m_bh['cagr']*100:7.2f}%  Vol {m_bh['vol']*100:6.2f}%  Sharpe(rf MXN) {m_bh['sharpe']:5.2f}  MaxDD {m_bh['max_dd']*100:7.2f}%")
    print("--- Bondia (MXN) ---")
    print(f"  CAGR {m_cash['cagr']*100:7.2f}%")
    print(f"\n  Rotacion anual media: {res['turnover_annual']:.2f}x  |  Rebalanceos: {res['n_rebalances']}")
    print(f"  PSR (SR*>0): {psr0:.4f}  |  DSR (N={p['n_trials']} trials): {dsr['dsr']:.4f}  (SR*={dsr['sr_star']:.4f}/periodo)")
    print("  >>> Ajusta n_trials con el conteo real de tu overfitting_ledger antes de creer el DSR. <<<")

    grid = robustness_grid(data, p)
    print("\n--- Rejilla de robustez (todas las celdas, sin cherry-pick) ---")
    print(grid.to_string(index=False, formatters={
        "CAGR": lambda x: f"{x*100:6.2f}%", "Sharpe": lambda x: f"{x:5.2f}", "MaxDD": lambda x: f"{x*100:7.2f}%"}))
    disp = grid["Sharpe"].max() - grid["Sharpe"].min()
    print(f"\n  Dispersion de Sharpe en la rejilla: {disp:.2f} "
          f"{'(estable: el edge no depende de una celda)' if disp < 0.35 else '(ALTA: sospecha de sensibilidad a parametros)'}")

    # Persistir NAV y reporte
    out_csv = os.path.join(dir_path, "strategy12_backtest_nav.csv")
    pd.DataFrame({"NAV": res["nav"], "QQQ_BH_MXN": res["bh_qqq"],
                  "BONDIA": res["bondia"], "W_TQQQ": res["weights"]}).to_csv(out_csv)

    report = f"""# Strategy 12: Vol-Targeted Trend Leverage + MXN Carry (VTTL)
**Periodo:** {data.index[0].date()} a {data.index[-1].date()} | **Modo:** {'SELF-TEST SINTETICO' if args.selftest else 'Datos reales'}

## Resultados (MXN)
| Metrica | VTTL | QQQ B&H | Bondia |
| :--- | ---: | ---: | ---: |
| CAGR | {m['cagr']*100:.2f}% | {m_bh['cagr']*100:.2f}% | {m_cash['cagr']*100:.2f}% |
| Vol anual | {m['vol']*100:.2f}% | {m_bh['vol']*100:.2f}% | ~0% |
| Sharpe (rf MXN {p['rf_mxn']*100:.1f}%) | {m['sharpe']:.2f} | {m_bh['sharpe']:.2f} | - |
| Max Drawdown | {m['max_dd']*100:.2f}% | {m_bh['max_dd']*100:.2f}% | 0% |

## Validacion estadistica
* PSR (SR*>0): **{psr0:.4f}** | DSR (N={p['n_trials']}): **{dsr['dsr']:.4f}**
* Rotacion anual: {res['turnover_annual']:.2f}x | Costos: {p['cost_bps']:.0f} bps por notional rotado
* Parametros declarados a priori; rejilla de robustez completa en consola.

## Reglas
1. Trend: exposicion solo si QQQ > SMA({p['sma_window']}); si no, 100% Bondia.
2. Vol targeting: exposicion efectiva = min({p['vol_target']:.0%}/vol_20d, {p['max_exposure']}x).
3. Implementacion: TQQQ a exposicion/3; capital libre en Bondia (carry MXN).
4. Senal en cierre t aplica al retorno t+1. Banda de rebalanceo {p['rebalance_band']:.0%}.
5. Sin SQQQ, sin HMM, sin parametros ajustados.
"""
    with open(os.path.join(dir_path, "strategy12_backtest_report.md"), "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\nNAV -> strategy12_backtest_nav.csv | Reporte -> strategy12_backtest_report.md")
    print("=" * 80)


if __name__ == "__main__":
    main()
