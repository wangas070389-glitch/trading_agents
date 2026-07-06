"""
Strategy 12 LIVE: Vol-Targeted Trend Leverage + MXN Carry (VTTL)
Semantica identica a backtest_strategy12.py:
  - Senal calculada SOLO con cierres diarios COMPLETADOS (hasta ayer).
  - Ejecucion al precio actual (equivale a t+1 del backtest).
  - Solo TQQQ + cash Bondia. Sin SQQQ, sin HMM, sin intradia.
Cadencia: una decision por dia habil. Corridas adicionales solo acumulan interes.
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

PORTFOLIO_FILE = "portfolio_strategy12.json"
TRANSACTIONS_FILE = "transactions_strategy12.md"
REPORT_FILE = "strategy12_report_live.md"

PARAMS = {
    "sma_window": 200,
    "vol_window": 20,
    "vol_target": 0.20,
    "max_exposure": 1.5,
    "rebalance_band": 0.20,
    "leverage_etf": 3.0,
}
MONTHLY_CONTRIBUTION = 2000.0
BONDIA_YIELD = 0.0653
TRADING_DAYS = 252


def load_portfolio(dir_path):
    p_path = os.path.join(dir_path, PORTFOLIO_FILE)
    if not os.path.exists(p_path):
        return {"total_capital": 200000.0, "cash_balance": 200000.0, "holdings": [],
                "last_signal_date": "", 
                "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    with open(p_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_portfolio(dir_path, portfolio):
    portfolio["last_updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(os.path.join(dir_path, PORTFOLIO_FILE), "w", encoding="utf-8") as f:
        json.dump(portfolio, f, indent=2)


def log_transaction(dir_path, date_str, ticker, action, shares, price, note, fee=0.0):
    t_path = os.path.join(dir_path, TRANSACTIONS_FILE)
    if not os.path.exists(t_path):
        with open(t_path, "w", encoding="utf-8") as f:
            f.write("# Transaction Ledger (Strategy 12: VTTL)\n\n"
                    "| Date | Ticker | Action | Shares | Price | Fee | Note |\n"
                    "| :--- | :--- | :--- | ---: | ---: | ---: | :--- |\n---\n")
    with open(t_path, "r", encoding="utf-8") as f:
        lines = f.read().split("\n")
    row = f"| {date_str} | {ticker} | {action} | {shares:.4f} | ${price:.4f} | ${fee:.2f} | {note} |"
    idx = next((i for i, l in enumerate(lines) if l.strip() == "---"), None)
    lines.insert(idx, row) if idx is not None else lines.append(row)
    with open(t_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    dir_path = os.path.dirname(os.path.abspath(__file__))
    now_et = datetime.datetime.now(ZoneInfo("America/New_York"))
    today_str = now_et.strftime("%Y-%m-%d")
    now_local = datetime.datetime.now()

    print("=" * 80)
    print(f"LIVE EXECUTION: STRATEGY 12 VTTL ({today_str} ET)")
    print("=" * 80)

    portfolio = load_portfolio(dir_path)
    cash = portfolio["cash_balance"]

    # --- Interes Bondia (identico patron al resto del repo) ---
    last_str = portfolio.get("last_updated", today_str + " 00:00:00")
    fmt = "%Y-%m-%d %H:%M:%S" if " " in last_str else "%Y-%m-%d"
    last_dt = datetime.datetime.strptime(last_str, fmt)
    days = max((now_local - last_dt).total_seconds() / 86400.0, 0.0)
    if days > 0:
        interest = cash * (BONDIA_YIELD / 365.25) * days
        cash = round(cash + interest, 2)
        portfolio["cash_balance"] = cash
        log_transaction(dir_path, today_str, "BONDIA", "INTEREST", 1, interest, "Sweep interest", 0.0)
        print(f"[Sweep] +${interest:,.4f} MXN")

    # --- DCA mensual ---
    if now_local.year > last_dt.year or (now_local.year == last_dt.year and now_local.month > last_dt.month):
        cash += MONTHLY_CONTRIBUTION
        portfolio["cash_balance"] = cash
        log_transaction(dir_path, today_str, "CASH", "DEPOSIT", 1, MONTHLY_CONTRIBUTION, "Monthly DCA", 0.0)
        print(f"[DCA] +${MONTHLY_CONTRIBUTION:,.2f} MXN")

    # --- Datos: SOLO cierres diarios completados para la senal ---
    try:
        qqq = yf.download("QQQ", period="2y", interval="1d", progress=False, auto_adjust=True)
        tqqq_now = yf.download("TQQQ", period="5d", interval="1d", progress=False, auto_adjust=True)
        fx_hist = yf.Ticker("MXN=X").history(period="5d")
        if qqq.empty or tqqq_now.empty or fx_hist.empty:
            print("CRITICAL: feed vacio. Halt sin tocar portafolio.")
            save_portfolio(dir_path, portfolio)
            return
        if isinstance(qqq.columns, pd.MultiIndex):
            qqq.columns = [c[0] for c in qqq.columns]
        if isinstance(tqqq_now.columns, pd.MultiIndex):
            tqqq_now.columns = [c[0] for c in tqqq_now.columns]
    except Exception as e:
        print(f"CRITICAL: fallo de datos ({e}). Halt sin tocar portafolio.")
        save_portfolio(dir_path, portfolio)
        return

    fx_rate = float(fx_hist["Close"].iloc[-1])
    tqqq_price_mxn = float(tqqq_now["Close"].iloc[-1]) * fx_rate

    # Excluir la barra de hoy si el mercado sigue abierto (senal = cierres completados)
    qqq_idx_dates = qqq.index.tz_localize(None) if qqq.index.tz is not None else qqq.index
    completed = qqq[qqq_idx_dates.strftime("%Y-%m-%d") < today_str] if now_et.time() < datetime.time(16, 0) else qqq
    if len(completed) < PARAMS["sma_window"] + 5:
        print("CRITICAL: historial insuficiente para SMA200. Halt.")
        save_portfolio(dir_path, portfolio)
        return

    signal_date = str(qqq_idx_dates[len(completed) - 1].date())
    if portfolio.get("last_signal_date") == signal_date:
        print(f"Senal de {signal_date} ya procesada hoy. Solo valuacion.")
        rebalance_allowed = False
    else:
        rebalance_allowed = True

    close = completed["Close"]
    sma = float(close.rolling(PARAMS["sma_window"]).mean().iloc[-1])
    rvol = float(close.pct_change().rolling(PARAMS["vol_window"]).std(ddof=1).iloc[-1] * np.sqrt(TRADING_DAYS))
    last_close = float(close.iloc[-1])

    trend_on = last_close > sma
    exposure = min(PARAMS["vol_target"] / rvol, PARAMS["max_exposure"]) if (trend_on and rvol > 0) else 0.0
    target_w = exposure / PARAMS["leverage_etf"]

    # --- Estado actual ---
    holdings = portfolio["holdings"]
    pos = holdings[0] if holdings else None
    pos_value = pos["shares"] * tqqq_price_mxn if pos else 0.0
    nav = cash + pos_value
    current_w = pos_value / nav if nav > 0 else 0.0

    print(f"Senal ({signal_date}): trend={'ON' if trend_on else 'OFF'} | vol20d={rvol*100:.1f}% "
          f"| exposicion objetivo={exposure:.2f}x QQQ | w_TQQQ objetivo={target_w:.3f} | w actual={current_w:.3f}")

    actions = []
    needs_rebalance = rebalance_allowed and (
        (target_w <= 0 and current_w > 0)
        or (target_w > 0 and current_w <= 0)
        or (target_w > 0 and current_w > 0 and abs(current_w / target_w - 1.0) > PARAMS["rebalance_band"])
    )

    if needs_rebalance:
        target_value = nav * target_w
        delta_mxn = target_value - pos_value
        if delta_mxn > 0 and cash > 0:
            buy_mxn = min(delta_mxn, cash)
            sh = buy_mxn / tqqq_price_mxn
            cash -= buy_mxn
            if pos:
                pos["shares"] += sh
            else:
                holdings.append({"ticker": "TQQQ", "side": "long", "shares": sh,
                                 "buy_price": tqqq_price_mxn, "last_price": tqqq_price_mxn})
                pos = holdings[0]
            log_transaction(dir_path, today_str, "TQQQ", "BUY", sh, tqqq_price_mxn,
                            f"Rebalanceo a w={target_w:.3f}", 0.0)
            actions.append(f"BUY {sh:.4f} TQQQ @ ${tqqq_price_mxn:,.2f} MXN -> w={target_w:.3f}")
        elif delta_mxn < 0 and pos:
            sell_mxn = min(-delta_mxn, pos_value)
            sh = sell_mxn / tqqq_price_mxn
            pos["shares"] -= sh
            cash += sell_mxn
            log_transaction(dir_path, today_str, "TQQQ", "SELL", sh, tqqq_price_mxn,
                            f"Rebalanceo a w={target_w:.3f}", 0.0)
            actions.append(f"SELL {sh:.4f} TQQQ @ ${tqqq_price_mxn:,.2f} MXN -> w={target_w:.3f}")
            if pos["shares"] < 1e-6:
                portfolio["holdings"] = []
                pos = None
        portfolio["last_signal_date"] = signal_date
    elif rebalance_allowed:
        portfolio["last_signal_date"] = signal_date
        actions.append(f"Dentro de banda ({PARAMS['rebalance_band']:.0%}); sin operacion.")

    # --- Valuacion final ---
    pos_value = pos["shares"] * tqqq_price_mxn if pos else 0.0
    if pos:
        pos["last_price"] = tqqq_price_mxn
    nav = cash + pos_value
    portfolio["cash_balance"] = round(cash, 2)
    portfolio["total_capital"] = round(nav, 2)
    save_portfolio(dir_path, portfolio)

    report = f"""# Strategy 12: VTTL Live Report
**Execution:** {now_local.strftime('%Y-%m-%d %H:%M:%S')} | **Signal date:** {signal_date}

* **NAV:** ${nav:,.2f} MXN | **Cash (Bondia):** ${cash:,.2f} MXN | **TQQQ:** ${pos_value:,.2f} MXN
* **Trend (QQQ>SMA200):** {'ON' if trend_on else 'OFF'} | **Vol 20d:** {rvol*100:.1f}% | **Exposicion objetivo:** {exposure:.2f}x
* **w_TQQQ:** actual {current_w:.3f} -> objetivo {target_w:.3f}

## Acciones
"""
    report += "".join(f"* {a}\n" for a in actions) if actions else "* Sin cambios.\n"
    with open(os.path.join(dir_path, REPORT_FILE), "w", encoding="utf-8") as f:
        f.write(report)
    print("Reporte escrito. NAV: $%s MXN" % f"{nav:,.2f}")
    print("=" * 80)


if __name__ == "__main__":
    main()
