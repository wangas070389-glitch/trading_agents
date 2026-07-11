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

MODO AUDITORIA: el watchdog NO escribe HALT flags ni detiene estrategias;
solo reporta. Los halts (HALT_<estrategia>.flag) se crean y borran a mano.

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
SUSPENDED_STRATEGIES = set()  # us_stocks (S3) reactivada 2026-07-10 por el usuario


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


def calculate_portfolio_nav(p, name):
    # For S9-S16, total_capital is the correct, dynamically-updated NAV
    if name in ("strategy9", "strategy10", "strategy11", "strategy12", "strategy13", "strategy14", "strategy15", "strategy16"):
        return p.get("total_capital") or p.get("total_portfolio_value") or p.get("cash_balance", 0.0)

    # For other strategies, we compute NAV = Cash + sum(shares * last_price)
    cash = p.get("cash_balance") or 0.0
    holdings_val = 0.0
    for h in p.get("holdings", []):
        shares = float(h.get("shares", 0.0))
        price = float(h.get("last_price", h.get("buy_price", h.get("current_price", 0.0))))
        holdings_val += shares * price
    return cash + holdings_val


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
    tx_path = os.path.join(dir_path, "transactions.md" if name == "core" else f"transactions_{name}.md")
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
    nav = calculate_portfolio_nav(p, name)
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
    bt_csv = os.path.join(dir_path, f"{name}_backtest_nav.csv")
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
        nav_txt = f"NAV ${nav:,.2f}" if isinstance(nav, (int, float)) else "NAV n/d"
        findings.append(Finding("OK", name, "-", f"{nav_txt} | sin anomalias"))
    return findings, nav_hist



def check_broker_reconciliation(dir_path, now, active_strats=None):
    """W6: reconciliacion contra Alpaca. Los libros locales pueden mentir
    (fills fantasma); el broker es la verdad. Requiere APCA_API_KEY_ID y
    APCA_API_SECRET_KEY en el entorno; si faltan, se omite con WARNING."""
    if active_strats is None:
        active_strats = set()
    import glob as _glob
    key = os.environ.get("APCA_API_KEY_ID")
    sec = os.environ.get("APCA_API_SECRET_KEY")
    base = os.environ.get("APCA_API_BASE_URL", "https://paper-api.alpaca.markets")
    if not key or not sec:
        return [Finding("WARNING", "broker", "W6", "Sin credenciales Alpaca en env; reconciliacion omitida")]
    try:
        import requests
        hdr = {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": sec}
        acct = requests.get(f"{base}/v2/account", headers=hdr, timeout=15).json()
        positions = requests.get(f"{base}/v2/positions", headers=hdr, timeout=15).json()
    except Exception as e:
        return [Finding("WARNING", "broker", "W6", f"Alpaca inaccesible: {e}")]

    findings = []
    cash = float(acct.get("cash", 0.0))
    if cash < -0.01:
        level = "CRITICAL" if "us_stocks" in active_strats else "WARNING"
        prefix = "" if level == "CRITICAL" else "[INACTIVE STRATEGY] "
        findings.append(Finding(level, "broker", "W6",
                        f"{prefix}Cash de Alpaca NEGATIVO: ${cash:,.2f} (margen no intencional; probable fill fantasma previo)"))

    # holdings locales agregados de todos los portafolios (tickers US) y mapeo de ticker -> lista de estrategias
    local = {}
    ticker_to_strats = {}
    for p_path in _glob.glob(os.path.join(dir_path, "portfolio_*.json")):
        try:
            name = os.path.basename(p_path).replace("portfolio_", "").replace("portfolio", "core").replace(".json", "") or "core"
            with open(p_path, "r", encoding="utf-8") as f:
                pj = json.load(f)
            for h in pj.get("holdings", []):
                t = str(h.get("ticker", "")).upper()
                if t and ".MX" not in t:
                    local[t] = local.get(t, 0.0) + float(h.get("shares", 0.0))
                    if t not in ticker_to_strats:
                        ticker_to_strats[t] = set()
                    ticker_to_strats[t].add(name)
        except Exception:
            continue

    for pos in positions if isinstance(positions, list) else []:
        sym = str(pos.get("symbol", "")).upper()
        qty_b = float(pos.get("qty", 0.0))
        qty_l = local.get(sym, 0.0)
        if qty_b - qty_l > max(0.02 * max(qty_b, 1.0), 0.5):
            strats_for_ticker = ticker_to_strats.get(sym, set())
            is_active_mismatch = any(s in active_strats for s in strats_for_ticker) or ("us_stocks" in active_strats)
            
            level = "CRITICAL" if is_active_mismatch else "WARNING"
            prefix = "" if level == "CRITICAL" else "[INACTIVE STRATEGY] "
            
            findings.append(Finding(level, "broker", "W6",
                            f"{prefix}HUERFANO en Alpaca: {sym} broker={qty_b:g} vs ledgers={qty_l:g} "
                            f"(firma de SELL fantasma: el broker aun lo tiene)"))
    if not findings:
        findings.append(Finding("OK", "broker", "W6", f"Reconciliado: cash ${cash:,.2f}, {len(positions) if isinstance(positions, list) else 0} posiciones"))
    return findings

def get_active_strategies(dir_path):
    active_map = {
        "run_live_alpha_growth.py": "core",
        "ingest_live_macd.py": "macd",
        "run_live_alpaca_us_stocks.py": "us_stocks",
        "run_live_alpaca_us_stocks_dcf.py": "us_dcs",
        "run_live_alternatives.py": "alternatives",
        "run_live_high_beta.py": "high_beta",
        "run_live_dividends.py": "dividends",
        "run_live_strategy9.py": "strategy9",
        "run_live_strategy10.py": "strategy10",
        "run_live_strategy11.py": "strategy11",
        "run_live_strategy12.py": "strategy12",
        "run_live_strategy13.py": "strategy13",
        "run_live_strategy14.py": "strategy14",
        "run_live_strategy15.py": "strategy15",
        "run_live_strategy16.py": "strategy16",
    }
    scheduler_path = os.path.join(dir_path, "scheduler.py")
    if not os.path.exists(scheduler_path):
        return set(active_map.values())
    
    active_strats = set()
    try:
        with open(scheduler_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        match = re.search(r"STRATEGY_SCRIPTS\s*=\s*\[(.*?)\]", content, re.DOTALL)
        if match:
            list_block = match.group(1)
            for line in list_block.split("\n"):
                line_strip = line.strip()
                if not line_strip or line_strip.startswith("#"):
                    continue
                if "#" in line_strip:
                    line_strip = line_strip.split("#")[0].strip()
                m_str = re.search(r"['\"](.*?)['\"]", line_strip)
                if m_str:
                    script = m_str.group(1)
                    if script in active_map:
                        active_strats.add(active_map[script])
    except Exception as e:
        print(f"Error parsing active strategies from scheduler.py: {e}")
        return set(active_map.values())
    return active_strats

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

    active_strats = get_active_strategies(dir_path) - SUSPENDED_STRATEGIES
    print(f"DEBUG: active_strats = {active_strats}")

    all_findings = []
    paths = sorted(glob.glob(os.path.join(dir_path, "portfolio_*.json")))
    core = os.path.join(dir_path, "portfolio.json")
    if os.path.exists(core):
        paths.insert(0, core)
    for p_path in paths:
        if os.path.basename(p_path) == "watchdog_nav_history.json":
            continue
        name = os.path.basename(p_path).replace("portfolio_", "").replace("portfolio", "core").replace(".json", "") or "core"
        f, nav_hist = check_strategy(name, p_path, dir_path, nav_hist, now)
        
        if name not in active_strats:
            for finding in f:
                if finding.level == "CRITICAL":
                    finding.level = "WARNING"
                    finding.msg = f"[INACTIVE STRATEGY] {finding.msg}"
        all_findings.extend(f)

    with open(hist_path, "w", encoding="utf-8") as f:
        json.dump(nav_hist, f, indent=1)

    all_findings.extend(check_broker_reconciliation(dir_path, now, active_strats))

    # AUDIT-ONLY: el watchdog reporta hallazgos (watchdog_report.md + exit 1
    # en CRITICAL para poner Actions en rojo) pero NO escribe HALT flags ni
    # detiene estrategias. Los halts se gestionan manualmente creando o
    # borrando HALT_<estrategia>.flag.
    n_crit_flags = sum(1 for f in all_findings if f.level == "CRITICAL" and f.strategy not in ("broker",))
    if n_crit_flags:
        print(f"AUDIT-ONLY: {n_crit_flags} CRITICAL detectados; no se escriben HALT flags (revision manual).")

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
