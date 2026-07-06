"""
Strategy 14 LIVE: HEDGE - Online Expert Aggregation
Estado de aprendizaje (G acumulado por experto) persistido en el JSON del
portafolio. Cada dia habil:
  1. Actualiza G_i con el retorno realizado de cada experto (cierre->cierre).
  2. Recalcula pesos multiplicativos w_i ~ exp(eta*G_i).
  3. Mezcla las posiciones objetivo de los expertos y rebalancea con banda.
Sin look-ahead posible: los pesos de hoy usan retornos hasta ayer.
"""
import os
import sys
import json
import datetime
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
import yfinance as yf

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

PORTFOLIO_FILE = "portfolio_strategy14.json"
TRANSACTIONS_FILE = "transactions_strategy14.md"
REPORT_FILE = "strategy14_report_live.md"

EXPERTS = ["CASH_MXN", "QQQ_BH", "VTTL", "CARA", "TSMOM", "CASH_USD"]
PARAMS = {
    "eta": 0.055, "clip_daily": 0.10, "rebalance_band": 0.15,
    "sma_trend_vttl": 200, "sma_trend_cara": 100, "credit_sma": 60,
    "tsmom_lookback": 252, "tsmom_skip": 21,
    "vol_window": 20, "vol_target": 0.20, "max_exposure": 1.5,
    "leverage_etf": 3.0, "hedge_usd_frac_cara": 0.35,
}
MONTHLY_CONTRIBUTION = 2000.0
BONDIA_YIELD = 0.0653
USD_CASH_YIELD = 0.045
TRADING_DAYS = 252


def load_portfolio(dir_path):
    p_path = os.path.join(dir_path, PORTFOLIO_FILE)
    if not os.path.exists(p_path):
        return {"total_capital": 200000.0, "cash_balance_mxn": 200000.0, "cash_balance_usd": 0.0,
                "holdings": [], "last_signal_date": "",
                "expert_G": {e: 0.0 for e in EXPERTS},
                "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    with open(p_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_portfolio(dir_path, p):
    p["last_updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(os.path.join(dir_path, PORTFOLIO_FILE), "w", encoding="utf-8") as f:
        json.dump(p, f, indent=2)


def log_transaction(dir_path, date_str, ticker, action, qty, price, note):
    t_path = os.path.join(dir_path, TRANSACTIONS_FILE)
    if not os.path.exists(t_path):
        with open(t_path, "w", encoding="utf-8") as f:
            f.write("# Transaction Ledger (Strategy 14: HEDGE)\n\n"
                    "| Date | Ticker | Action | Qty | Price | Note |\n"
                    "| :--- | :--- | :--- | ---: | ---: | :--- |\n---\n")
    with open(t_path, "r", encoding="utf-8") as f:
        lines = f.read().split("\n")
    row = f"| {date_str} | {ticker} | {action} | {qty:.4f} | ${price:.4f} | {note} |"
    idx = next((i for i, l in enumerate(lines) if l.strip() == "---"), None)
    lines.insert(idx, row) if idx is not None else lines.append(row)
    with open(t_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def fetch(t, period):
    df = yf.download(t, period=period, interval="1d", progress=False, auto_adjust=True)
    if df.empty:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    s = df["Close"]
    if s.index.tz is not None:
        s.index = s.index.tz_localize(None)
    return s


def expert_targets_and_returns(qqq, vix, vix3m, hyg, ief, fx, p):
    """Con cierres completados: posicion objetivo (w_tqqq, f_usd) de cada experto
    HOY, y el retorno MXN realizado de cada experto en el ultimo cierre->cierre."""
    r_qqq = qqq.pct_change()
    rvol = float(r_qqq.rolling(p["vol_window"]).std(ddof=1).iloc[-1] * np.sqrt(TRADING_DAYS))
    base = min(p["vol_target"] / rvol, p["max_exposure"]) if rvol > 0 else 0.0
    L = p["leverage_etf"]

    def cara_state(idx):
        ratio = (hyg / ief.reindex(hyg.index)).dropna()
        s = (int(float(vix3m.iloc[idx]) > float(vix.iloc[idx]))
             + int(float(ratio.iloc[idx]) > float(ratio.rolling(p["credit_sma"]).mean().iloc[idx]))
             + int(float(qqq.iloc[idx]) > float(qqq.rolling(p["sma_trend_cara"]).mean().iloc[idx])))
        return s

    def targets(idx):
        trend_v = float(qqq.iloc[idx]) > float(qqq.rolling(p["sma_trend_vttl"]).mean().iloc[idx])
        s = cara_state(idx)
        exp_cara = base if s == 3 else (base * 0.5 if s == 2 else 0.0)
        mom = float(qqq.iloc[idx - p["tsmom_skip"]]) / float(qqq.iloc[idx - p["tsmom_lookback"]]) - 1
        low3 = all(cara_state(idx - k) <= 1 for k in range(3))
        return {
            "CASH_MXN": (0.0, 0.0),
            "QQQ_BH":   (1.0 / L, 0.0),
            "VTTL":     ((base if trend_v else 0.0) / L, 0.0),
            "CARA":     (exp_cara / L, p["hedge_usd_frac_cara"] if low3 else 0.0),
            "TSMOM":    ((base if mom > 0 else 0.0) / L, 0.0),
            "CASH_USD": (0.0, 1.0),
        }

    tgt_today = targets(-1)      # posicion a mantener desde hoy
    tgt_prev = targets(-2)       # posicion que cada experto tenia ayer

    # retorno realizado de cada experto en el ultimo cierre->cierre (en MXN)
    r_fx_last = float(fx.pct_change().iloc[-1]) if len(fx) > 1 else 0.0
    r_q_last = float(r_qqq.iloc[-1])
    drag = (L - 1) * 0.045 / TRADING_DAYS + 0.0095 / TRADING_DAYS
    r_tqqq_usd = L * r_q_last - drag
    r_tqqq_mxn = (1 + r_tqqq_usd) * (1 + r_fx_last) - 1
    mxn_d = BONDIA_YIELD / TRADING_DAYS
    r_usd_mxn = (1 + USD_CASH_YIELD / TRADING_DAYS) * (1 + r_fx_last) - 1

    r_experts = {}
    for e in EXPERTS:
        w, f = tgt_prev[e]
        r_experts[e] = w * r_tqqq_mxn + (1 - w) * ((1 - f) * mxn_d + f * r_usd_mxn)
    return tgt_today, r_experts, base, rvol


def main():
    dir_path = os.path.dirname(os.path.abspath(__file__))
    now_et = datetime.datetime.now(ZoneInfo("America/New_York"))
    today_str = now_et.strftime("%Y-%m-%d")
    now_local = datetime.datetime.now()
    p = PARAMS

    print("=" * 80)
    print(f"LIVE EXECUTION: STRATEGY 14 HEDGE ({today_str} ET)")
    print("=" * 80)

    portfolio = load_portfolio(dir_path)
    cash_mxn = portfolio.get("cash_balance_mxn", 200000.0)
    cash_usd = portfolio.get("cash_balance_usd", 0.0)

    # interes ambos sleeves + DCA (mismo patron que S13)
    last_str = portfolio.get("last_updated", today_str + " 00:00:00")
    fmt = "%Y-%m-%d %H:%M:%S" if " " in last_str else "%Y-%m-%d"
    last_dt = datetime.datetime.strptime(last_str, fmt)
    days = max((now_local - last_dt).total_seconds() / 86400.0, 0.0)
    if days > 0:
        i_m = cash_mxn * (BONDIA_YIELD / 365.25) * days
        i_u = cash_usd * (USD_CASH_YIELD / 365.25) * days
        cash_mxn = round(cash_mxn + i_m, 2)
        cash_usd = round(cash_usd + i_u, 4)
        if i_m > 0:
            log_transaction(dir_path, today_str, "BONDIA", "INTEREST", 1, i_m, "MXN sweep")
        if i_u > 0:
            log_transaction(dir_path, today_str, "USD-MMF", "INTEREST", 1, i_u, "USD sweep")
    if now_local.year > last_dt.year or (now_local.year == last_dt.year and now_local.month > last_dt.month):
        cash_mxn += MONTHLY_CONTRIBUTION
        log_transaction(dir_path, today_str, "CASH", "DEPOSIT", 1, MONTHLY_CONTRIBUTION, "Monthly DCA")

    # datos
    try:
        qqq = fetch("QQQ", "3y"); vix = fetch("^VIX", "1y"); vix3m = fetch("^VIX3M", "1y")
        hyg = fetch("HYG", "1y"); ief = fetch("IEF", "1y"); tqqq = fetch("TQQQ", "5d")
        fx_s = fetch("MXN=X", "1mo")
        if any(s is None or len(s) == 0 for s in (qqq, vix, vix3m, hyg, ief, tqqq, fx_s)):
            print("CRITICAL: feed incompleto. Halt.")
            portfolio["cash_balance_mxn"], portfolio["cash_balance_usd"] = cash_mxn, cash_usd
            save_portfolio(dir_path, portfolio)
            return
    except Exception as e:
        print(f"CRITICAL: fallo de datos ({e}). Halt.")
        save_portfolio(dir_path, portfolio)
        return

    fx_rate = float(fx_s.iloc[-1])
    tqqq_mxn = float(tqqq.iloc[-1]) * fx_rate

    def completed(s):
        return s[s.index.strftime("%Y-%m-%d") < today_str] if now_et.time() < datetime.time(16, 0) else s
    qqq_c, vix_c, vix3m_c = completed(qqq), completed(vix), completed(vix3m)
    hyg_c, ief_c, fx_c = completed(hyg), completed(ief), completed(fx_s)

    if len(qqq_c) < p["tsmom_lookback"] + 10:
        print("CRITICAL: historial insuficiente. Halt.")
        save_portfolio(dir_path, portfolio)
        return

    signal_date = str(qqq_c.index[-1].date())
    already = portfolio.get("last_signal_date") == signal_date

    tgt, r_experts, base, rvol = expert_targets_and_returns(qqq_c, vix_c, vix3m_c, hyg_c, ief_c, fx_c, p)

    # 1) actualizar aprendizaje (solo una vez por senal)
    G = portfolio.get("expert_G", {e: 0.0 for e in EXPERTS})
    if not already:
        for e in EXPERTS:
            G[e] = G.get(e, 0.0) + float(np.log1p(np.clip(r_experts[e], -p["clip_daily"], p["clip_daily"])))
        portfolio["expert_G"] = G

    # 2) pesos multiplicativos
    g = np.array([G[e] for e in EXPERTS])
    z = p["eta"] * (g - g.max())
    wk = np.exp(z); wk /= wk.sum()
    agg = {e: float(wk[i]) for i, e in enumerate(EXPERTS)}

    # 3) posicion mezclada
    tgt_w = sum(agg[e] * tgt[e][0] for e in EXPERTS)
    tgt_f = sum(agg[e] * tgt[e][1] for e in EXPERTS)

    holdings = portfolio["holdings"]
    pos = holdings[0] if holdings else None
    pos_value = pos["shares"] * tqqq_mxn if pos else 0.0
    nav = cash_mxn + cash_usd * fx_rate + pos_value
    cur_w = pos_value / nav if nav > 0 else 0.0

    print(f"Senal ({signal_date}) | vol20d={rvol*100:.1f}% base={base:.2f}x")
    print("Pesos agregador: " + "  ".join(f"{e}={agg[e]*100:.1f}%" for e in EXPERTS))
    print(f"Objetivo mezclado: w_TQQQ={tgt_w:.3f} f_USD={tgt_f:.3f} | actual w={cur_w:.3f}")

    actions = []
    if not already:
        if abs(tgt_w - cur_w) > p["rebalance_band"] * max(abs(tgt_w), 0.05):
            delta = nav * tgt_w - pos_value
            if delta > 0 and cash_mxn > 0:
                buy = min(delta, cash_mxn); sh = buy / tqqq_mxn
                cash_mxn -= buy
                if pos:
                    pos["shares"] += sh
                else:
                    holdings.append({"ticker": "TQQQ", "side": "long", "shares": sh,
                                     "buy_price": tqqq_mxn, "last_price": tqqq_mxn})
                    pos = holdings[0]
                log_transaction(dir_path, today_str, "TQQQ", "BUY", sh, tqqq_mxn, f"HEDGE mix w={tgt_w:.3f}")
                actions.append(f"BUY {sh:.4f} TQQQ")
            elif delta < 0 and pos:
                sell = min(-delta, pos_value); sh = sell / tqqq_mxn
                pos["shares"] -= sh; cash_mxn += sell
                log_transaction(dir_path, today_str, "TQQQ", "SELL", sh, tqqq_mxn, f"HEDGE mix w={tgt_w:.3f}")
                actions.append(f"SELL {sh:.4f} TQQQ")
                if pos["shares"] < 1e-6:
                    portfolio["holdings"] = []; pos = None; pos_value = 0.0
        total_cash = cash_mxn + cash_usd * fx_rate
        tgt_usd_mxn = total_cash * tgt_f
        d_usd = tgt_usd_mxn - cash_usd * fx_rate
        if abs(d_usd) > total_cash * 0.02:
            if d_usd > 0:
                mv = min(d_usd, cash_mxn); cash_mxn -= mv; cash_usd += mv / fx_rate
                log_transaction(dir_path, today_str, "USDMXN", "BUY_USD", mv / fx_rate, fx_rate, f"mix f={tgt_f:.2f}")
                actions.append(f"USD +{mv/fx_rate:,.2f}")
            else:
                mv = min(-d_usd, cash_usd * fx_rate); cash_usd -= mv / fx_rate; cash_mxn += mv
                log_transaction(dir_path, today_str, "USDMXN", "SELL_USD", mv / fx_rate, fx_rate, f"mix f={tgt_f:.2f}")
                actions.append(f"USD -{mv/fx_rate:,.2f}")
        portfolio["last_signal_date"] = signal_date
        if not actions:
            actions.append("Dentro de bandas; sin operacion.")
    else:
        actions.append("Senal ya procesada; solo valuacion.")

    pos_value = pos["shares"] * tqqq_mxn if pos else 0.0
    if pos:
        pos["last_price"] = tqqq_mxn
    nav = cash_mxn + cash_usd * fx_rate + pos_value
    portfolio["cash_balance_mxn"] = round(cash_mxn, 2)
    portfolio["cash_balance_usd"] = round(cash_usd, 4)
    portfolio["total_capital"] = round(nav, 2)
    save_portfolio(dir_path, portfolio)

    ranked = sorted(EXPERTS, key=lambda e: -G.get(e, 0.0))
    report = f"""# Strategy 14: HEDGE Live Report
**Execution:** {now_local.strftime('%Y-%m-%d %H:%M:%S')} | **Signal date:** {signal_date}

* **NAV:** ${nav:,.2f} MXN | Cash MXN ${cash_mxn:,.2f} | Cash USD ${cash_usd:,.2f} | TQQQ ${pos_value:,.2f}
* **Objetivo mezclado:** w_TQQQ={tgt_w:.3f}, f_USD={tgt_f:.3f}

## Pesos del agregador (confianza aprendida)
{chr(10).join(f'* {e}: **{agg[e]*100:.1f}%** (G={G.get(e,0.0):+.4f})' for e in ranked)}

## Acciones
{chr(10).join(f'* {a}' for a in actions)}
"""
    with open(os.path.join(dir_path, REPORT_FILE), "w", encoding="utf-8") as f:
        f.write(report)
    print(f"NAV: ${nav:,.2f} MXN. Reporte escrito.")
    print("=" * 80)


if __name__ == "__main__":
    main()
