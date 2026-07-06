"""
WATCHDOG: auditor de fallo silencioso para todos los portafolios del repo.
==========================================================================
Escanea portfolio_strategy*.json + transactions_strategy*.md y verifica:

  W1  STALENESS       last_updated con mas de MAX_STALE_HOURS de antiguedad
                      en dia habil -> el cron esta muerto o el script crashea.
  W2  ZERO-TRADE      estrategia viva >= MIN_DAYS_FOR_TRADE dias habiles con
                      cero transacciones no-interes -> logica de entrada
                      posiblemente muerta (esto habria detectado S10/S11 en
                      su primera semana).
  W3  NAV-JUMP        salto de NAV dia-a-dia imposible dada la exposicion
                      (holdings 3x acotan el movimiento plausible) -> bug de
                      contabilidad (esto habria detectado el P&L invertido
                      de SQQQ en su primer trade).
  W4  NEGATIVE/NAN    cash negativo, shares negativos, NaN en el JSON.
  W5  DD-BREAKER      drawdown live > tolerancia sobre el MaxDD del backtest
                      (si existe strategyN_backtest_nav.csv) -> el live esta
                      fuera de la distribucion que validaste.

Salida: watchdog_report.md + exit code 1 si hay CRITICAL -> GitHub Actions
marca la corrida EN ROJO. El fallo deja de ser silencioso.

Uso:  python watchdog.py            (auditar y fallar en critico)
      python watchdog.py --dry-run  (auditar sin exit code)
Integracion en workflow (paso final, despues de los runners):
      - run: python watchdog.py
"""
import os
import re
import sys
import json
import glob
import argparse
import datetime

import numpy as np
import pandas as pd

MAX_STALE_HOURS = 30          # > 1 dia habil sin actualizar = cron muerto
MIN_DAYS_FOR_TRADE = 10       # dias habiles de gracia antes de exigir 1 trade
NAV_JUMP_TOLERANCE = 0.35     # |dNAV| diario maximo plausible (3x ETF ~ +-25% extremo)
DD_BREAKER_FACTOR = 1.25      # live DD no debe exceder 1.25x el MaxDD del backtest
NAV_HISTORY_FILE = "watchdog_nav_history.json"


class Finding:
    def __init__(self, level, strategy, code, msg):
        self.level, self.strategy, self.code, self.msg = level, strategy, code, msg

    def row(self):
        icon = {"CRITICAL": "[CRIT]", "WARNING": "[WARN]", "OK": "[ OK ]"}[self.level]
        return f"| {icon} | {self.strategy} | {self.code} | {self.msg} |"


def business_days_between(d0, d1):
    return int(np.busday_count(d0.date(), d1.date()))


def parse_last_updated(p):
    s = p.get("last_updated", "")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def count_real_trades(tx_path):
    """Transacciones que NO son interes/deposito (BUY/SELL/BUY_USD/etc)."""
    if not os.path.exists(tx_path):
        return None, None
    trades, first_date = 0, None
    with open(tx_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.startswith("|") or line.startswith("| Date") or line.startswith("| :"):
                continue
            cols = [c.strip() for c in line.split("|")]
            if len(cols) < 5:
                continue
            date_s, action = cols[1], cols[3].upper()
            m = re.match(r"\d{4}-\d{2}-\d{2}", date_s)
            if m and first_date is None:
                first_date = datetime.datetime.strptime(m.group(0), "%Y-%m-%d")
            if action not in ("INTEREST", "DEPOSIT"):
                trades += 1
    return trades, first_date


def total_exposure_ratio(p):
    """Valor de holdings / NAV -> acota el movimiento diario plausible."""
    nav = p.get("total_capital", 0.0) or 0.0
    if nav <= 0:
        return 0.0
    hv = sum(abs(h.get("shares", 0.0) * h.get("last_price", 0.0)) for h in p.get("holdings", []))
    return hv / nav


def check_strategy(name, p_path, dir_path, nav_hist, now):
    findings = []
    try:
        with open(p_path, "r", encoding="utf-8") as f:
            p = json.load(f)
    except Exception as e:
        return [Finding("CRITICAL", name, "W4", f"JSON ilegible: {e}")], nav_hist

    # W4: sanidad basica
    cash_fields = [v for k, v in p.items() if k.startswith("cash_balance") and isinstance(v, (int, float))]
    if any((not np.isfinite(v)) for v in cash_fields) or not np.isfinite(p.get("total_capital", 0.0)):
        findings.append(Finding("CRITICAL", name, "W4", "NaN/inf en cash o total_capital"))
    if any(v < -0.01 for v in cash_fields):
        findings.append(Finding("CRITICAL", name, "W4", f"Cash negativo: {cash_fields}"))
    for h in p.get("holdings", []):
        if h.get("shares", 0) < -1e-9:
            findings.append(Finding("CRITICAL", name, "W4", f"Shares negativos en {h.get('ticker')}"))

    # W1: staleness (solo si hoy es dia habil)
    lu = parse_last_updated(p)
    if lu is None:
        findings.append(Finding("WARNING", name, "W1", "last_updated ilegible"))
    else:
        stale_busdays = business_days_between(lu, now)
        # Viernes -> lunes madrugada = 1 dia habil transcurrido: normal.
        # 2+ dias habiles sin update con cron diario = muerto.
        if stale_busdays >= 2:
            findings.append(Finding("CRITICAL", name, "W1",
                            f"Sin actualizar desde {lu} ({stale_busdays} dias habiles): cron muerto o script crasheando"))

    # W2: zero-trade
    num = name.replace("strategy", "")
    tx_path = os.path.join(dir_path, f"transactions_strategy{num}.md")
    trades, first_date = count_real_trades(tx_path)
    if trades is not None and first_date is not None:
        age = business_days_between(first_date, now)
        if trades == 0 and age >= MIN_DAYS_FOR_TRADE:
            findings.append(Finding("CRITICAL", name, "W2",
                            f"{age} dias habiles vivos y CERO trades (solo interes): logica de entrada muerta?"))
        elif trades == 0:
            findings.append(Finding("WARNING", name, "W2",
                            f"Sin trades aun ({age}/{MIN_DAYS_FOR_TRADE} dias de gracia)"))

    # W3: salto de NAV vs historia propia del watchdog
    nav = p.get("total_capital", None)
    hist = nav_hist.get(name, [])
    if nav is not None and hist:
        prev_nav = hist[-1]["nav"]
        prev_dt = datetime.datetime.strptime(hist[-1]["ts"], "%Y-%m-%d %H:%M:%S")
        days = max(business_days_between(prev_dt, now), 1)
        if prev_nav > 0:
            move = abs(nav / prev_nav - 1.0)
            exposure = total_exposure_ratio(p)
            # tope plausible: exposicion * 3x * 12% diario extremo * dias; min 3%/dia para cash-only
            cap = max(exposure * 3.0 * 0.12, 0.03) * days
            if move > max(cap, 0.03) and move > 0.05:
                findings.append(Finding("CRITICAL", name, "W3",
                                f"NAV salto {move*100:.1f}% en {days}d con exposicion {exposure*100:.0f}%: "
                                f"posible bug de contabilidad (tope plausible {cap*100:.1f}%)"))
    if nav is not None:
        hist.append({"ts": now.strftime("%Y-%m-%d %H:%M:%S"), "nav": float(nav)})
        nav_hist[name] = hist[-500:]

    # W5: drawdown breaker vs backtest
    bt_csv = os.path.join(dir_path, f"strategy{num}_backtest_nav.csv")
    if os.path.exists(bt_csv) and len(hist) > 5:
        try:
            bt_nav = pd.read_csv(bt_csv, index_col=0)["NAV"]
            bt_dd = float((bt_nav / bt_nav.cummax() - 1.0).min())
            navs = pd.Series([h["nav"] for h in hist])
            live_dd = float((navs / navs.cummax() - 1.0).min())
            if bt_dd < -0.01 and live_dd < bt_dd * DD_BREAKER_FACTOR:
                findings.append(Finding("CRITICAL", name, "W5",
                                f"DD live {live_dd*100:.1f}% excede {DD_BREAKER_FACTOR}x el MaxDD del backtest "
                                f"({bt_dd*100:.1f}%): fuera de distribucion validada"))
        except Exception:
            pass

    if not findings:
        findings.append(Finding("OK", name, "-", f"NAV ${nav:,.2f} | sin anomalias"))
    return findings, nav_hist


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    dir_path = os.path.dirname(os.path.abspath(__file__))
    now = datetime.datetime.now()

    hist_path = os.path.join(dir_path, NAV_HISTORY_FILE)
    nav_hist = {}
    if os.path.exists(hist_path):
        try:
            with open(hist_path, "r", encoding="utf-8") as f:
                nav_hist = json.load(f)
        except Exception:
            nav_hist = {}

    all_findings = []
    for p_path in sorted(glob.glob(os.path.join(dir_path, "portfolio_strategy*.json"))):
        name = os.path.basename(p_path).replace("portfolio_", "").replace(".json", "")
        f, nav_hist = check_strategy(name, p_path, dir_path, nav_hist, now)
        all_findings.extend(f)

    with open(hist_path, "w", encoding="utf-8") as f:
        json.dump(nav_hist, f, indent=1)

    n_crit = sum(1 for f in all_findings if f.level == "CRITICAL")
    n_warn = sum(1 for f in all_findings if f.level == "WARNING")

    lines = [f"# Watchdog Report - {now.strftime('%Y-%m-%d %H:%M:%S')}",
             "", f"**CRITICAL: {n_crit} | WARNING: {n_warn}**", "",
             "| Nivel | Estrategia | Check | Detalle |", "| :--- | :--- | :--- | :--- |"]
    lines += [f.row() for f in all_findings]
    report = "\n".join(lines) + "\n"
    with open(os.path.join(dir_path, "watchdog_report.md"), "w", encoding="utf-8") as f:
        f.write(report)
    print(report)

    if n_crit > 0 and not args.dry_run:
        print(f"WATCHDOG: {n_crit} hallazgos CRITICOS -> exit 1 (Actions en rojo)")
        sys.exit(1)
    print("WATCHDOG: sin criticos." if n_crit == 0 else "WATCHDOG: criticos (dry-run, exit 0).")


if __name__ == "__main__":
    main()
