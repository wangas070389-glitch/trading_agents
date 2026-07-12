"""
Strategy 13 LIVE: CARA - Cross-Asset Risk Appetite
Semantica identica a backtest_strategy13.py:
  - Senal SOLO con cierres diarios completados (VIX, VIX3M, HYG/IEF, QQQ).
  - Ejecucion al precio actual (= t+1 del backtest).
  - Sleeve USD: cash del portafolio puede rotar 35% a USD cuando score<=1 (3 dias).
Cadencia: una decision por dia habil.
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

PORTFOLIO_FILE = "portfolio_strategy13.json"
TRANSACTIONS_FILE = "transactions_strategy13.md"
REPORT_FILE = "strategy13_report_live.md"

PARAMS = {
    "credit_sma": 60, "trend_sma": 100, "vol_window": 20,
    "vol_target": 0.20, "max_exposure": 1.5, "rebalance_band": 0.20,
    "leverage_etf": 3.0, "hedge_usd_frac": 0.35, "hedge_confirm_days": 3,
}
MONTHLY_CONTRIBUTION = 2000.0
BONDIA_YIELD = 0.0653
USD_CASH_YIELD = 0.045
TRADING_DAYS = 252


def load_portfolio(dir_path):
    p_path = os.path.join(dir_path, PORTFOLIO_FILE)
    if not os.path.exists(p_path):
        return {"total_capital": 200000.0, "cash_balance_mxn": 200000.0,
                "cash_balance_usd": 0.0, "holdings": [], "last_signal_date": "",
                "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    with open(p_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_portfolio(dir_path, portfolio):
    portfolio["last_updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(os.path.join(dir_path, PORTFOLIO_FILE), "w", encoding="utf-8") as f:
        json.dump(portfolio, f, indent=2)


def log_transaction(dir_path, date_str, ticker, action, shares, price, note):
    t_path = os.path.join(dir_path, TRANSACTIONS_FILE)
    if not os.path.exists(t_path):
        with open(t_path, "w", encoding="utf-8") as f:
            f.write("# Transaction Ledger (Strategy 13: CARA)\n\n"
                    "| Date | Ticker | Action | Qty | Price | Note |\n"
                    "| :--- | :--- | :--- | ---: | ---: | :--- |\n---\n")
    with open(t_path, "r", encoding="utf-8") as f:
        lines = f.read().split("\n")
    row = f"| {date_str} | {ticker} | {action} | {shares:.4f} | ${price:.4f} | {note} |"
    idx = next((i for i, l in enumerate(lines) if l.strip() == "---"), None)
    lines.insert(idx, row) if idx is not None else lines.append(row)
    with open(t_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def fetch_series(ticker, period="1y"):
    df = yf.download(ticker, period=period, interval="1d", progress=False, auto_adjust=True)
    if df.empty:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    s = df["Close"]
    if s.index.tz is not None:
        s.index = s.index.tz_localize(None)
    return s


def main():
    dir_path = os.path.dirname(os.path.abspath(__file__))
    from halt_gate import halted
    if halted(dir_path, "strategy13"):
        return
    now_et = datetime.datetime.now(ZoneInfo("America/New_York"))
    today_str = now_et.strftime("%Y-%m-%d")
    now_local = datetime.datetime.now()

    print("=" * 80)
    print(f"LIVE EXECUTION: STRATEGY 13 CARA ({today_str} ET)")
    print("=" * 80)

    portfolio = load_portfolio(dir_path)
    cash_mxn = portfolio.get("cash_balance_mxn", portfolio.get("cash_balance", 200000.0))
    cash_usd = portfolio.get("cash_balance_usd", 0.0)

    # Interes en ambos sleeves
    last_str = portfolio.get("last_updated", today_str + " 00:00:00")
    fmt = "%Y-%m-%d %H:%M:%S" if " " in last_str else "%Y-%m-%d"
    last_dt = datetime.datetime.strptime(last_str, fmt)
    days = max((now_local - last_dt).total_seconds() / 86400.0, 0.0)
    if days > 0:
        i_mxn = cash_mxn * (BONDIA_YIELD / 365.25) * days
        i_usd = cash_usd * (USD_CASH_YIELD / 365.25) * days
        cash_mxn = round(cash_mxn + i_mxn, 2)
        cash_usd = round(cash_usd + i_usd, 4)
        if i_mxn > 0:
            log_transaction(dir_path, today_str, "BONDIA", "INTEREST", 1, i_mxn, "MXN sweep")
        if i_usd > 0:
            log_transaction(dir_path, today_str, "USD-MMF", "INTEREST", 1, i_usd, "USD sweep")
        print(f"[Sweep] +${i_mxn:,.4f} MXN | +${i_usd:,.4f} USD")

    # DCA mensual (entra al sleeve MXN)
    if now_local.year > last_dt.year or (now_local.year == last_dt.year and now_local.month > last_dt.month):
        cash_mxn += MONTHLY_CONTRIBUTION
        log_transaction(dir_path, today_str, "CASH", "DEPOSIT", 1, MONTHLY_CONTRIBUTION, "Monthly DCA")
        print(f"[DCA] +${MONTHLY_CONTRIBUTION:,.2f} MXN")

    # --- Datos ---
    try:
        qqq = fetch_series("QQQ", "1y")
        vix = fetch_series("^VIX", "6mo")
        vix3m = fetch_series("^VIX3M", "6mo")
        hyg = fetch_series("HYG", "1y")
        ief = fetch_series("IEF", "1y")
        tqqq = fetch_series("TQQQ", "5d")
        fx_hist = yf.Ticker("MXN=X").history(period="5d")
        if any(s is None or len(s) == 0 for s in (qqq, vix, vix3m, hyg, ief, tqqq)) or fx_hist.empty:
            print("CRITICAL: feed incompleto. Halt sin tocar portafolio.")
            portfolio["cash_balance_mxn"] = cash_mxn
            portfolio["cash_balance_usd"] = cash_usd
            save_portfolio(dir_path, portfolio)
            return
    except Exception as e:
        print(f"CRITICAL: fallo de datos ({e}). Halt.")
        save_portfolio(dir_path, portfolio)
        return

    fx_rate = float(fx_hist["Close"].iloc[-1])
    tqqq_mxn = float(tqqq.iloc[-1]) * fx_rate

    # Solo cierres completados (excluir hoy si el mercado sigue abierto)
    def completed(s):
        return s[s.index.strftime("%Y-%m-%d") < today_str] if now_et.time() < datetime.time(16, 0) else s
    qqq_c, vix_c, vix3m_c = completed(qqq), completed(vix), completed(vix3m)
    hyg_c, ief_c = completed(hyg), completed(ief)

    if len(qqq_c) < PARAMS["trend_sma"] + 5 or len(hyg_c) < PARAMS["credit_sma"] + 5:
        print("CRITICAL: historial insuficiente. Halt.")
        save_portfolio(dir_path, portfolio)
        return

    signal_date = str(qqq_c.index[-1].date())
    rebalance_allowed = portfolio.get("last_signal_date") != signal_date

    # --- Score CARA (3 votos, ultimo dia completado) ---
    v1 = int(float(vix3m_c.iloc[-1]) > float(vix_c.iloc[-1]))
    ratio = (hyg_c / ief_c.reindex(hyg_c.index)).dropna()
    v2 = int(float(ratio.iloc[-1]) > float(ratio.rolling(PARAMS["credit_sma"]).mean().iloc[-1]))
    v3 = int(float(qqq_c.iloc[-1]) > float(qqq_c.rolling(PARAMS["trend_sma"]).mean().iloc[-1]))
    score = v1 + v2 + v3

    rvol = float(qqq_c.pct_change().rolling(PARAMS["vol_window"]).std(ddof=1).iloc[-1] * np.sqrt(TRADING_DAYS))
    base = min(PARAMS["vol_target"] / rvol, PARAMS["max_exposure"]) if rvol > 0 else 0.0
    exposure = base if score == 3 else (base * 0.5 if score == 2 else 0.0)
    target_w = exposure / PARAMS["leverage_etf"]

    # Confirmacion de hedge: contador persistido de dias consecutivos con score<=1
    streak = portfolio.get("low_score_streak", 0)
    if rebalance_allowed:
        streak = streak + 1 if score <= 1 else 0
        portfolio["low_score_streak"] = streak
    hedge_active = streak >= PARAMS["hedge_confirm_days"]

    # --- Estado y valuacion ---
    holdings = portfolio["holdings"]
    pos = holdings[0] if holdings else None
    pos_value = pos["shares"] * tqqq_mxn if pos else 0.0
    nav = cash_mxn + cash_usd * fx_rate + pos_value
    current_w = pos_value / nav if nav > 0 else 0.0

    print(f"Senal ({signal_date}): VIXts={v1} Credito={v2} Trend={v3} -> SCORE {score} | "
          f"vol20d={rvol*100:.1f}% | w objetivo={target_w:.3f} | w actual={current_w:.3f} | "
          f"hedge={'ON' if hedge_active else 'OFF'} (streak={streak})")

    actions = []
    if rebalance_allowed:
        # 1) Equity con banda
        needs = ((target_w <= 0 and current_w > 0) or (target_w > 0 and current_w <= 0)
                 or (target_w > 0 and current_w > 0 and abs(current_w / target_w - 1) > PARAMS["rebalance_band"]))
        if needs:
            delta = nav * target_w - pos_value
            if delta > 0 and cash_mxn > 0:
                buy = min(delta, cash_mxn)
                sh = buy / tqqq_mxn
                cash_mxn -= buy
                if pos:
                    pos["shares"] += sh
                else:
                    holdings.append({"ticker": "TQQQ", "side": "long", "shares": sh,
                                     "buy_price": tqqq_mxn, "last_price": tqqq_mxn})
                    pos = holdings[0]
                log_transaction(dir_path, today_str, "TQQQ", "BUY", sh, tqqq_mxn, f"Score {score} -> w={target_w:.3f}")
                actions.append(f"BUY {sh:.4f} TQQQ (score {score})")
            elif delta < 0 and pos:
                sell = min(-delta, pos_value)
                sh = sell / tqqq_mxn
                pos["shares"] -= sh
                cash_mxn += sell
                log_transaction(dir_path, today_str, "TQQQ", "SELL", sh, tqqq_mxn, f"Score {score} -> w={target_w:.3f}")
                actions.append(f"SELL {sh:.4f} TQQQ (score {score})")
                if pos["shares"] < 1e-6:
                    portfolio["holdings"] = []
                    pos = None
                    pos_value = 0.0
        # 2) Hedge FX sobre el cash total
        total_cash_mxn_eq = cash_mxn + cash_usd * fx_rate
        target_usd_mxn_eq = total_cash_mxn_eq * (PARAMS["hedge_usd_frac"] if hedge_active else 0.0)
        delta_usd_mxn = target_usd_mxn_eq - cash_usd * fx_rate
        if abs(delta_usd_mxn) > total_cash_mxn_eq * 0.02:  # umbral minimo 2% para operar FX
            if delta_usd_mxn > 0:
                mv = min(delta_usd_mxn, cash_mxn)
                cash_mxn -= mv
                cash_usd += mv / fx_rate
                log_transaction(dir_path, today_str, "USDMXN", "BUY_USD", mv / fx_rate, fx_rate, "Hedge riesgo-off ON")
                actions.append(f"HEDGE ON: {mv/fx_rate:,.2f} USD @ {fx_rate:.4f}")
            else:
                mv = min(-delta_usd_mxn, cash_usd * fx_rate)
                cash_usd -= mv / fx_rate
                cash_mxn += mv
                log_transaction(dir_path, today_str, "USDMXN", "SELL_USD", mv / fx_rate, fx_rate, "Hedge riesgo-off OFF")
                actions.append(f"HEDGE OFF: {mv/fx_rate:,.2f} USD @ {fx_rate:.4f}")
        portfolio["last_signal_date"] = signal_date
        if not actions:
            actions.append("Dentro de bandas; sin operacion.")
    else:
        actions.append(f"Senal de {signal_date} ya procesada; solo valuacion.")

    pos_value = pos["shares"] * tqqq_mxn if pos else 0.0
    if pos:
        pos["last_price"] = tqqq_mxn
    nav = cash_mxn + cash_usd * fx_rate + pos_value
    portfolio["cash_balance_mxn"] = round(cash_mxn, 2)
    portfolio["cash_balance_usd"] = round(cash_usd, 4)
    portfolio["total_capital"] = round(nav, 2)
    save_portfolio(dir_path, portfolio)

    report = f"""# Strategy 13: CARA Live Report
**Execution:** {now_local.strftime('%Y-%m-%d %H:%M:%S')} | **Signal date:** {signal_date}

* **NAV:** ${nav:,.2f} MXN
* **Cash MXN (Bondia):** ${cash_mxn:,.2f} | **Cash USD:** ${cash_usd:,.2f} (${cash_usd*fx_rate:,.2f} MXN) | **TQQQ:** ${pos_value:,.2f} MXN
* **Score CARA:** {score}/3 (VIXts={v1}, Credito={v2}, Trend={v3}) | **Vol 20d:** {rvol*100:.1f}%
* **w_TQQQ:** actual {current_w:.3f} -> objetivo {target_w:.3f} | **Hedge USD:** {'ACTIVO' if hedge_active else 'inactivo'} (streak {streak}/{PARAMS['hedge_confirm_days']})

## Acciones
"""
    report += "".join(f"* {a}\n" for a in actions)
    with open(os.path.join(dir_path, REPORT_FILE), "w", encoding="utf-8") as f:
        f.write(report)
    print(f"NAV: ${nav:,.2f} MXN. Reporte escrito.")
    print("=" * 80)


if __name__ == "__main__":
    main()
