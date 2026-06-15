import os
import sys
import json
import datetime
import time
import numpy as np
import pandas as pd
import yfinance as yf


# Add current directory to path to enable local imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

_RETRY_DELAYS = [5, 15, 30]  # seconds between attempts


def _strip_tz(df: pd.DataFrame) -> pd.DataFrame:
    """Remove timezone from a DataFrame's DatetimeIndex regardless of its current state and normalize to midnight."""
    if df.index.tz is not None:
        df.index = df.index.tz_convert("UTC").tz_localize(None)
    df.index = df.index.normalize()
    return df


def _fetch_ticker_history(ticker_symbol: str, period: str = "5y", max_retries: int = 3) -> pd.DataFrame:
    """
    Download historical OHLCV data from yfinance with retry/backoff.
    Returns an empty DataFrame on permanent failure instead of raising.
    """
    last_exc = None
    for attempt, delay in enumerate((_RETRY_DELAYS + [None])[:max_retries], start=1):
        try:
            hist = yf.Ticker(ticker_symbol).history(period=period, timeout=30)
            if not hist.empty:
                return hist
            # Empty result is not an exception but still a failure worth retrying
            raise ValueError(f"yfinance returned empty history for {ticker_symbol}")
        except Exception as exc:
            last_exc = exc
            if delay is not None:
                print(f"  [WARN] Attempt {attempt}/{max_retries} failed for {ticker_symbol}: {exc}. Retrying in {delay}s...")
                time.sleep(delay)
    print(f"  [ERROR] All {max_retries} attempts failed for {ticker_symbol}: {last_exc}")
    return pd.DataFrame()
from skills.liquidity_gatekeeper import calculate_adtv, passes_liquidity_gate
from skills.adaptive_learning import (
    SignalPerformanceTracker, DrawdownGovernor, load_learned_params,
)
from skills.index_constituents import get_spx_tickers
from skills.prefilter import prefilter_us_universe
from agents.agents import FundamentalScreener, MacroRiskAnalyst, PortfolioReconciler


def estimate_portfolio_value(dir_path):
    """Current total value (cash + marked holdings) for affordability cuts."""
    p = load_portfolio(dir_path)
    return p["cash_balance"] + sum(h["shares"] * h["last_price"] for h in p["holdings"])

# Major S&P/BMV IPC components to query
BMV_TICKERS = [
    "AMXB.MX",       # América Móvil
    "FEMSAUBD.MX",   # FEMSA
    "WALMEX.MX",     # Walmart de México
    "GFNORTEO.MX",   # Banorte
    "GMEXICOB.MX",   # Grupo México
    "CEMEXCPO.MX",   # Cemex
    "BIMBOA.MX",     # Grupo Bimbo
    "GAPB.MX",       # Grupo Aeroportuario del Pacífico
    "ASURB.MX",      # Grupo Aeroportuario del Sureste
    "OMAB.MX",       # Grupo Aeroportuario del Centro Norte
    "GRUMAB.MX",     # Gruma
    "ALFAA.MX",      # Alfa
    "KIMBERA.MX",    # Kimberly-Clark de México
    "AC.MX",         # Arca Continental
    "ORBIA.MX",      # Orbia Advance Corporation
    "PE&OLES.MX",    # Industrias Peñoles
    "PINFRA.MX",     # Pinfra
    "BBAJIOO.MX",    # Banco del Bajío
    "GENTERA.MX",    # Gentera
    "CUERVO.MX",     # Jose Cuervo
    "GCC.MX",        # Cementos de Chihuahua
    "VESTA.MX"       # Vesta (Industrial Real Estate warehouses)
]

# Major US components to query
US_TICKERS = [
    "NVDA",
    "AAPL",
    "MSFT",
    "AMZN",
    "GOOGL"
]

def fetch_historical_exogenous() -> tuple[pd.DataFrame, pd.Series]:
    """
    Downloads 5 years of historical closing prices for SPY and USD/MXN (MXN=X).
    Computes daily log returns and returns a cleaned DataFrame plus raw USD/MXN rate.
    """
    print("Fetching historical exogenous regressors (SPY and USD/MXN)...")
    spy = yf.Ticker("SPY").history(period="5y")
    usdmxn = yf.Ticker("MXN=X").history(period="5y")
    
    if spy.empty or usdmxn.empty:
        raise ValueError("Failed to fetch exogenous data from Yahoo Finance.")
        
    spy.index = spy.index.tz_localize(None)
    usdmxn.index = usdmxn.index.tz_localize(None)
    
    spy_ret = np.log(spy["Close"] / spy["Close"].shift(1))
    usdmxn_ret = np.log(usdmxn["Close"] / usdmxn["Close"].shift(1))
    
    df = pd.DataFrame({
        "SPY_Ret": spy_ret,
        "USDMXN_Ret": usdmxn_ret
    }).dropna()
    
    # Raw exchange rate (aligned index)
    raw_rate = usdmxn["Close"].rename("USDMXN_Rate")
    return df, raw_rate

def fetch_historical_asset(ticker_symbol: str) -> pd.DataFrame:
    """
    Downloads 5 years of historical daily price and volume data for an asset.
    """
    print(f"Fetching historical data for {ticker_symbol} from Yahoo Finance...")
    ticker = yf.Ticker(ticker_symbol)
    hist = ticker.history(period="5y")
    return hist

def load_portfolio(dir_path):
    """Load portfolio.json from project root."""
    portfolio_path = os.path.join(dir_path, "portfolio.json")
    if os.path.exists(portfolio_path):
        with open(portfolio_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def save_portfolio(dir_path, portfolio):
    """Save portfolio.json."""
    portfolio_path = os.path.join(dir_path, "portfolio.json")
    with open(portfolio_path, "w", encoding="utf-8") as f:
        json.dump(portfolio, f, indent=2)

def log_transaction(dir_path, date_str, ticker, action, shares, price, note, fee=0.0):
    """Append a transaction row to transactions.md. Net capital impact includes fees."""
    transactions_path = os.path.join(dir_path, "transactions.md")
    gross = shares * price
    if action == "BUY":
        cash_flow_str = f"-{gross + fee:,.2f}"
    else:
        cash_flow_str = f"+{gross - fee:,.2f}"

    row = f"| {date_str} | {ticker} | {action} | {shares} | {price:.2f} | {cash_flow_str} | Market | FILLED | {note} |"

    if os.path.exists(transactions_path):
        with open(transactions_path, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        # Create default table header if file missing
        content = "# Transaction Ledger\n\n| Date | Ticker | Action | Shares | Price | Net Capital Impact | Order Type | Status | Note |\n| :--- | :--- | :---: | :---: | :---: | :--- | :--- | :--- | :--- |\n---\n"

    lines = content.split("\n")
    insert_idx = None
    for i, line in enumerate(lines):
        if line.strip() == "---":
            insert_idx = i
            break

    if insert_idx is not None:
        lines.insert(insert_idx, row)
    else:
        lines.append(row)

    with open(transactions_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

def update_capital_reconciliation(dir_path, portfolio):
    """Update the capital reconciliation section in transactions.md."""
    transactions_path = os.path.join(dir_path, "transactions.md")
    if not os.path.exists(transactions_path):
        return
        
    with open(transactions_path, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.split("\n")
    recon_start = None
    for i, line in enumerate(lines):
        if "## Portfolio Capital Reconciliation" in line:
            recon_start = i
            break

    total_capital = portfolio["total_capital"]
    cash = portfolio["cash_balance"]
    invested = sum(h["shares"] * h["buy_price"] for h in portfolio["holdings"])
    total_value = cash + sum(h["shares"] * h.get("last_price", h["buy_price"]) for h in portfolio["holdings"])

    recon_lines = [
        "## Portfolio Capital Reconciliation",
        "",
        f"* **Initial Starting Capital (2026-06-03)**: {total_capital:,.2f} MXN",
        f"* **Total Deployed Capital**: {invested:,.2f} MXN ({invested/total_value*100:.1f}% invested)",
        f"* **Unallocated Cash Reserves**: {cash:,.2f} MXN ({cash/total_value*100:.1f}% cash)",
        f"* **Current Portfolio Market Value**: {total_value:,.2f} MXN (including cash)",
        ""
    ]

    if recon_start is not None:
        lines = lines[:recon_start] + recon_lines
    else:
        lines.extend(["", "---", ""] + recon_lines)

    with open(transactions_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

def append_evaluation_history(dir_path, execution_date, adjusted_metrics, pesos_asignados):
    """Append this run's quantitative metrics to evaluation_history.md."""
    history_path = os.path.join(dir_path, "evaluation_history.md")

    entry_lines = []
    entry_lines.append(f"\n## Run: {execution_date} @ {datetime.datetime.now().strftime('%H:%M:%S')} (V3 Quantitative Model)")
    entry_lines.append("")
    entry_lines.append("| Ticker | DCS v2 | GARCH Vol | Relative Vol | HMM State | Target Weight | Price |")
    entry_lines.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: |")
    
    sorted_tickers = sorted(adjusted_metrics.keys(), key=lambda x: adjusted_metrics[x]["dcs_adjusted"], reverse=True)
    for t in sorted_tickers:
        met = adjusted_metrics[t]
        state_str = "Bull" if met["hmm_state"] == 1 else ("Bear" if met["hmm_state"] == -1 else "Sideways")
        weight_str = f"{pesos_asignados.get(t, 0.0):.1%}"
        entry_lines.append(f"| {t} | {met['dcs_adjusted']:.4f} | {met['garch_vol_adjusted']:.4f} | {met['relative_vol']:.2f} | {state_str} | {weight_str} | {met['current_price']:.2f} |")

    entry_lines.append("")
    entry_lines.append("---")

    if not os.path.exists(history_path):
        header = "# Evaluation History Log\n\nRolling record of every DAG pipeline evaluation run (Hedge Fund Method V3).\n\n---\n"
        with open(history_path, "w", encoding="utf-8") as f:
            f.write(header + "\n".join(entry_lines))
    else:
        with open(history_path, "a", encoding="utf-8") as f:
            f.write("\n".join(entry_lines))

    print(f"[History] Appended V3 evaluation record to: {history_path}")

def main():
    dir_path = os.path.dirname(os.path.abspath(__file__))
    execution_date = datetime.date.today().strftime("%Y-%m-%d")
    print("=" * 80)
    print(f"STARTING LIVE S&P/BMV IPC V3 QUANTITATIVE EVALUATION PIPELINE | DATE: {execution_date}")
    print("=" * 80)

    # 1. Fetch exogenous regressors (SPY and USD/MXN exchange rate)
    try:
        df_exog, raw_rate = fetch_historical_exogenous()
    except Exception as e:
        print(f"Critical error fetching exogenous regressors: {e}")
        return

    # 2. Gather historical data for BMV universe and US stocks, and align indices
    universe_data = {}
    
    print("\n--- PHASE 1: HISTORICAL DATA INGESTION & ALIGNMENT ---")
    
    # Process BMV (Mexican) stocks
    for ticker in BMV_TICKERS:
        try:
            # Download asset data
            hist = fetch_historical_asset(ticker)
            if len(hist) < 30:
                print(f"  |-- {ticker}: Skipping (insufficient data: {len(hist)} days)")
                continue
                
            hist.index = hist.index.tz_localize(None)
                
            # Filter through liquidity gatekeeper first (using 30-day ADTV)
            prices_30 = hist["Close"].iloc[-30:].tolist()
            volumes_30 = hist["Volume"].iloc[-30:].tolist()
            adtv = calculate_adtv(prices_30, volumes_30)
            
            if not passes_liquidity_gate(adtv, threshold=5000000.0):
                print(f"  +-- [REJECTED] {ticker} failed liquidity gate (ADTV: {adtv:,.2f} MXN < 5M)")
                continue
                
            # Calculate returns
            asset_ret = np.log(hist["Close"] / hist["Close"].shift(1)).fillna(0.0)
            
            # Combine returns, prices, volumes, and join with exogenous
            df_asset = pd.DataFrame({
                "Asset_Price": hist["Close"],
                "Asset_Vol": hist["Volume"],
                "Asset_Ret": asset_ret
            })
            
            # Inner join to synchronize dates with SPY & USDMXN returns
            df_aligned = df_asset.join(df_exog, how="inner").fillna(0.0)
            
            if len(df_aligned) < 60:
                print(f"  |-- {ticker}: Skipping (insufficient aligned dates: {len(df_aligned)})")
                continue
                
            universe_data[ticker] = {
                "prices": df_aligned["Asset_Price"].values,
                "volumes": df_aligned["Asset_Vol"].values,
                "exogenous": df_aligned[["SPY_Ret", "USDMXN_Ret"]].values
            }
            print(f"  +-- Ingested & aligned {ticker} ({len(df_aligned)} synchronous business days)")
            
        except Exception as e:
            print(f"  +-- [ERROR] Failed to ingest {ticker}: {e}")
            continue

    # Process US stocks (converting to MXN)
    # SPX EXPANSION: the static 5-ticker US list is replaced by the full
    # S&P 500 universe, funneled through a cheap pre-filter so the expensive
    # GARCH/HMM stage only sees affordable, liquid, trending candidates.
    us_candidates = list(US_TICKERS)  # static list = last-resort fallback
    try:
        spx_tickers = get_spx_tickers(dir_path)
        portfolio_value_est = estimate_portfolio_value(dir_path)
        current_fx = float(raw_rate.iloc[-1])
        print(f"  |-- [Pre-filter] Batch-downloading 6mo history for "
              f"{len(spx_tickers)} SPX tickers (single request)...")
        batch = yf.download(spx_tickers, period="6mo", progress=False,
                            auto_adjust=True, group_by="column", threads=True)
        candidates = prefilter_us_universe(
            batch["Close"], batch["Volume"],
            usdmxn_rate=current_fx,
            portfolio_value_mxn=portfolio_value_est,
        )
        if candidates:
            # Held US positions must ALWAYS reach the deep stage, even if the
            # momentum funnel would cut them — otherwise the reconciler loses
            # signal coverage on open positions (carry-warning territory).
            held_us = {h["ticker"] for h in load_portfolio(dir_path)["holdings"]
                       if not h["ticker"].endswith(".MX")}
            us_candidates = list(dict.fromkeys(list(candidates) + sorted(held_us)))
    except Exception as e:
        print(f"  |-- [Pre-filter] SPX funnel failed ({e}). "
              f"Falling back to static US ticker list.")

    for ticker in us_candidates:
        try:
            # Download asset data
            hist = fetch_historical_asset(ticker)
            if len(hist) < 30:
                print(f"  |-- {ticker}: Skipping (insufficient data: {len(hist)} days)")
                continue
                
            hist.index = hist.index.tz_localize(None)
            
            # Align with raw exchange rate to convert to MXN
            df_usd = pd.DataFrame({
                "Close_USD": hist["Close"],
                "Volume": hist["Volume"]
            }).join(raw_rate, how="inner")
            
            if df_usd.empty:
                print(f"  |-- {ticker}: Skipping (failed to align with exchange rate history)")
                continue
                
            df_usd["Close_MXN"] = df_usd["Close_USD"] * df_usd["USDMXN_Rate"]
            
            # Filter through liquidity gatekeeper first (using 30-day ADTV in MXN)
            prices_mxn_30 = df_usd["Close_MXN"].iloc[-30:].tolist()
            volumes_30 = df_usd["Volume"].iloc[-30:].tolist()
            adtv = calculate_adtv(prices_mxn_30, volumes_30)
            
            if not passes_liquidity_gate(adtv, threshold=5000000.0):
                print(f"  +-- [REJECTED] {ticker} failed liquidity gate (ADTV: {adtv:,.2f} MXN < 5M)")
                continue
                
            # Calculate returns in MXN
            asset_ret_mxn = np.log(df_usd["Close_MXN"] / df_usd["Close_MXN"].shift(1)).fillna(0.0)
            
            # Combine returns, prices in MXN, volumes, and join with exogenous returns
            df_asset = pd.DataFrame({
                "Asset_Price": df_usd["Close_MXN"],
                "Asset_Vol": df_usd["Volume"],
                "Asset_Ret": asset_ret_mxn
            })
            
            # Inner join to synchronize dates with SPY & USDMXN returns
            df_aligned = df_asset.join(df_exog, how="inner").fillna(0.0)
            
            if len(df_aligned) < 60:
                print(f"  |-- {ticker}: Skipping (insufficient aligned dates: {len(df_aligned)})")
                continue
                
            universe_data[ticker] = {
                "prices": df_aligned["Asset_Price"].values,
                "volumes": df_aligned["Asset_Vol"].values,
                "exogenous": df_aligned[["SPY_Ret", "USDMXN_Ret"]].values
            }
            print(f"  +-- Ingested & aligned US stock {ticker} (Converted to MXN: {len(df_aligned)} business days)")
            
        except Exception as e:
            print(f"  +-- [ERROR] Failed to ingest US stock {ticker}: {e}")
            continue

    if not universe_data:
        print("No candidates survived Phase 1. Exiting.")
        return

    # 3. Phase 2: Quantitative Screening (Agent 1)
    print("\n--- PHASE 2: AGENT QUANTITATIVE SCREENING ---")
    screener = FundamentalScreener()
    raw_metrics = screener.screen(universe_data)

    # 4. Phase 3: Qualitative Macro Adjustment (Agent 2)
    print("\n--- PHASE 3: AGENT MACRO RISK ANALYSIS ---")
    analyst = MacroRiskAnalyst()
    adjusted_metrics = analyst.stress_test(raw_metrics, {})

    # 5. Phase 4: Portfolio Optimization & Rebalancing (Agent 3)
    print("\n--- PHASE 4: PORTFOLIO RECONCILIATION & REBALANCING ---")
    portfolio = load_portfolio(dir_path)
    if portfolio is None:
        # Initialize default portfolio if not found
        portfolio = {
            "total_capital": 20000.0,
            "cash_balance": 20000.0,
            "holdings": [],
            "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        print("  |-- portfolio.json missing. Initialized default empty portfolio with $20,000.00 MXN.")

    # 5b. Adaptive learning context: resolve past signal outcomes, compute
    # confidence multipliers, load learned thresholds, apply drawdown brake.
    print("\n--- PHASE 4b: ADAPTIVE LEARNING CONTEXT ---")
    tracker = SignalPerformanceTracker(dir_path)
    price_lookup = {t: m["current_price"] for t, m in adjusted_metrics.items()}
    resolved = tracker.update_outcomes(execution_date, price_lookup)
    print(f"  |-- Resolved {resolved} pending signal outcome(s). "
          f"Bucket stats: {tracker.bucket_stats() or 'no resolved samples yet'}")

    learned = load_learned_params(dir_path)
    if learned.get("trained_on"):
        print(f"  |-- Learned thresholds in use (trained {learned['trained_on']}, "
              f"val Sharpe {learned.get('validation_sharpe')}): "
              f"DCS>={learned['dcs_threshold']}, VR>={learned['vr_threshold']}")
    else:
        print("  |-- No learned_params.json found. Using default thresholds "
              "(run learn_parameters.py to train).")

    governor = DrawdownGovernor(dir_path)
    exposure = governor.exposure_scalar()

    confidence = {
        t: tracker.confidence_multiplier(m["hmm_state"], m["dcs_adjusted"])
        for t, m in adjusted_metrics.items()
    }

    learning_context = {
        "dcs_threshold": learned["dcs_threshold"],
        "vr_threshold": learned["vr_threshold"],
        "confidence": confidence,
        "exposure_scalar": exposure,
    }

    reconciler = PortfolioReconciler()
    universe_prices_dict = {t: data["prices"] for t, data in universe_data.items()}
    updated_portfolio, report_markdown, rebalancing_trades = reconciler.reconcile(
        adjusted_metrics, portfolio, execution_date, learning_context, universe_prices_dict
    )

    # 6. Execute paper trades & write logs
    print("\n--- PHASE 5: EXECUTING REBALANCING LOGS ---")
    
    # Extract optimal weights dictionary
    pesos_asignados = {h["ticker"]: h["target_weight"] for h in updated_portfolio["holdings"]}
    for t in adjusted_metrics:
        if t not in pesos_asignados:
            pesos_asignados[t] = 0.0

    # BUGFIX: previously trades were re-derived here by diffing old vs new holdings,
    # ignoring fees — so transactions.md never reconciled with portfolio.json cash.
    # Now we log the exact blotter the reconciler executed, fees included.
    trades_executed = len(rebalancing_trades)
    for trade in rebalancing_trades:
        log_transaction(
            dir_path, execution_date,
            trade["ticker"], trade["action"], trade["shares"],
            trade["price"], trade["note"], fee=trade["fee"]
        )

    # Save new portfolio.json
    save_portfolio(dir_path, updated_portfolio)
    update_capital_reconciliation(dir_path, updated_portfolio)

    # 6b. Feed the learning loop: log today's acted-on signals as pending
    # outcomes, and append today's total value to the equity curve so the
    # drawdown governor sees it on the next run.
    logged = tracker.record_signals(execution_date, adjusted_metrics, pesos_asignados)
    total_value_now = updated_portfolio["cash_balance"] + sum(
        h["shares"] * h["last_price"] for h in updated_portfolio["holdings"]
    )
    governor.record_value(execution_date, total_value_now)
    print(f"  |-- [Learning] Logged {logged} signal(s) for future scoring. "
          f"Equity curve point: {total_value_now:,.2f} MXN "
          f"(drawdown {governor.current_drawdown():+.2%}, next-run exposure {governor.exposure_scalar():.0%}).")

    if trades_executed > 0:
        print(f"  |-- Processed and logged {trades_executed} transaction(s) in transactions.md.")
    else:
        print("  |-- Holdings already matched targets. No new trades written.")

    # 7. Append signal history
    append_evaluation_history(dir_path, execution_date, adjusted_metrics, pesos_asignados)

    # 8. Save technical execution report
    output_filename = "mexican_value_equity_report_live.md"
    output_path = os.path.join(dir_path, output_filename)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_markdown)
    print(f"  |-- Saved V3 live report to: {output_path}")

    # 9. Print final report
    print("\n" + "=" * 80)
    print("LIVE V3 MODEL REPORT OUTPUT:")
    print("=" * 80)
    print(report_markdown)
    print("=" * 80)

if __name__ == "__main__":
    main()
