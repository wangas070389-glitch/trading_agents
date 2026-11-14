import os
import json
import math
import datetime
import pandas as pd
from backtest_review import backtest_block

# Historical Backtest KPIs
STRATEGY_KPIS = {
    "S1: Adaptive Value": {
        "asset": "S&P/BMV IPC Value Basket",
        "window": 4.0,
        "cagr": 0.2007,
        "max_dd": -0.2818,
        "sharpe": 0.82,
        "turnover": "~1.5x",
        "currency": "MXN",
        "is_live": True,
        "inception": "2026-06-03"
    },
    "S2: 1d MACD Systematic": {
        "asset": "Multi-Asset Universe",
        "window": 5.0,
        "cagr": 0.1310,
        "max_dd": -0.1094,
        "sharpe": 1.27,
        "turnover": "~2.4x",
        "currency": "MXN",
        "is_live": True,
        "inception": "2026-06-03"
    },
    "S3: US Stock Momentum": {
        "asset": "QQQ/SPY Tech Leaders",
        "window": 5.0,
        "cagr": 0.2540,
        "max_dd": -0.1820,
        "sharpe": 1.15,
        "turnover": "~4.0x",
        "currency": "USD",
        "is_live": True,
        "inception": "2026-06-23"
    },
    "S4: US DCS Value-Growth": {
        "asset": "US Large Cap Value",
        "window": 4.0,
        "cagr": 0.2193,
        "max_dd": -0.1219,
        "sharpe": 1.14,
        "turnover": "~2.0x",
        "currency": "USD",
        "is_live": True,
        "inception": "2026-06-23"
    },
    "S5: Alternative Assets": {
        "asset": "BTC, Gold, Real Estate",
        "window": 4.0,
        "cagr": 0.1840,
        "max_dd": -0.1520,
        "sharpe": 0.95,
        "turnover": "~1.0x",
        "currency": "USD",
        "is_live": True,
        "inception": "2026-06-23"
    },
    "S6: High-Beta Momentum": {
        "asset": "High-Beta Watch Equity",
        "window": 4.0,
        "cagr": 0.2210,
        "max_dd": -0.1950,
        "sharpe": 1.05,
        "turnover": "~6.0x",
        "currency": "USD",
        "is_live": True,
        "inception": "2026-06-23"
    },
    "S8: Dividend Quality": {
        "asset": "High-Dividend MXN Stocks",
        "window": 5.0,
        "cagr": 0.1450,
        "max_dd": -0.1120,
        "sharpe": 1.12,
        "turnover": "~1.2x",
        "currency": "MXN",
        "is_live": True,
        "inception": "2026-06-25"
    },
    "S9: AI Regime Stat-Arb": {
        "asset": "Statistical Arbitrage Pairs",
        "window": 2.0,
        "cagr": 0.2680,
        "max_dd": -0.0750,
        "sharpe": 1.45,
        "turnover": "~8.0x",
        "currency": "MXN",
        "is_live": True,
        "inception": "2026-06-30"
    },
    "S10: AI Intraday VWAP": {
        "asset": "Leveraged Index ETFs (TQQQ)",
        "window": 60.0 / 365.0, # 60 days
        "cagr": 0.5325,
        "max_dd": -0.0414,
        "sharpe": 2.73,
        "turnover": "Intraday",
        "currency": "MXN",
        "is_live": True,
        "inception": "2026-07-02"
    },
    "S11: AI Intraday CCI-ADX": {
        "asset": "Leveraged Index ETFs (TQQQ)",
        "window": 60.0 / 365.0, # 60 days
        "cagr": 0.1188,
        "max_dd": -0.1631,
        "sharpe": 0.10,
        "turnover": "Intraday",
        "currency": "MXN",
        "is_live": True,
        "inception": "2026-07-02"
    },
    "S12: Vol-Targeted Trend (VTTL)": {
        "asset": "TQQQ Volatility Trend-Carry",
        "window": 22.5,
        "cagr": 0.1713,
        "max_dd": -0.2134,
        "sharpe": 0.46,
        "turnover": "~2.8x",
        "currency": "MXN",
        "is_live": True,
        "inception": "2026-07-06"
    },
    "S13: Risk Appetite (CARA)": {
        "asset": "QQQ Trend / Treasury Bonds",
        "window": 19.2,
        "cagr": 0.1595,
        "max_dd": -0.2502,
        "sharpe": 0.45,
        "turnover": "~8.4x",
        "currency": "MXN",
        "is_live": False,  # retired standalone
        "inception": "2026-07-06"
    },
    "S14: Aggregator (HEDGE)": {
        "asset": "Online Expert Aggregation",
        "window": 19.2,
        "cagr": 0.1517,
        "max_dd": -0.1519,
        "sharpe": 0.53,
        "turnover": "~1.3x",
        "currency": "MXN",
        "is_live": True,
        "inception": "2026-07-06"
    },
    "S15: Tracker (TRACK)": {
        "asset": "Fixed-Share Expert Tracking",
        "window": 19.2,
        "cagr": 0.1505,
        "max_dd": -0.1473,
        "sharpe": 0.53,
        "turnover": "~1.3x",
        "currency": "MXN",
        "is_live": True,
        "inception": "2026-07-06"
    },
    "S16: HMM Intraday Router": {
        "asset": "Multi-Asset Index Universe",
        "window": 60.0 / 365.0,
        "cagr": -0.1129,
        "max_dd": -0.1829,
        "sharpe": -1.27,
        "turnover": "Intraday",
        "currency": "MXN",
        "is_live": True,
        "inception": "2026-07-07"
    },
    "S17: FIBRAs Dynamic": {
        "asset": "BMV FIBRAs Basket",
        "window": 4.0,
        "cagr": 0.0746,
        "max_dd": -0.1693,
        "sharpe": 0.08,
        "turnover": "Quarterly",
        "currency": "MXN",
        "is_live": True,
        "inception": "2026-07-12"
    },
    "S18: Efficient Frontier": {
        "asset": "Risk Parity (12 strategies)",
        "window": 4.0,
        "cagr": 0.1366,
        "max_dd": -0.0329,
        "sharpe": 1.16,
        "turnover": "Monthly Rebalancing",
        "currency": "USD",
        "is_live": True,
        "inception": "2026-07-12"
    },
    "S19: Particle Filter QQQ/TQQQ/SQQQ": {
        "asset": "QQQ, TQQQ, SQQQ",
        "window": 16.41,
        "cagr": 0.2192,
        "max_dd": -0.5178,
        "sharpe": 0.31,
        "turnover": "~9 trades/year",
        "currency": "MXN",
        "is_live": True,
        "inception": "2026-07-13"
    },
    "S20: Hurst Exponent Dynamic": {
        "asset": "QQQ, TQQQ, SQQQ",
        "window": 16.41,
        "cagr": 0.2429,
        "max_dd": -0.6371,
        "sharpe": 0.34,
        "turnover": "~4.4 trades/year",
        "currency": "MXN",
        "is_live": True,
        "inception": "2026-07-13"
    },
    "S21: Shannon Entropy Dynamic": {
        "asset": "QQQ, TQQQ, SQQQ",
        "window": 16.41,
        "cagr": 0.1085,
        "max_dd": -0.7025,
        "sharpe": 0.03,
        "turnover": "~5.2 trades/year",
        "currency": "MXN",
        "is_live": True,
        "inception": "2026-07-13"
    },
    "S22: Walk-Forward ML Classifier": {
        "asset": "QQQ, TQQQ, SQQQ",
        "window": 16.42,
        "cagr": 0.2113,
        "max_dd": -0.5866,
        "sharpe": 0.26,
        "turnover": "~12.2 trades/year",
        "currency": "MXN",
        "is_live": True,
        "inception": "2026-07-14"
    },
    "S23: Calculus S&R & RSI Systematic": {
        "asset": "QQQ, TQQQ, SQQQ",
        "window": 16.0,
        "cagr": 0.3082,
        "max_dd": -0.7053,
        "sharpe": 0.42,
        "turnover": "~15 trades/year",
        "currency": "MXN",
        "is_live": True,
        "inception": "2026-07-15"
    },
    "S24: 30m Random Forest Classifier": {
        "asset": "Leveraged Index ETFs",
        "window": 0.24,
        "cagr": 0.3737,
        "max_dd": -0.1192,
        "sharpe": 0.59,
        "turnover": "Intraday",
        "currency": "MXN",
        "is_live": True,
        "inception": "2026-07-15"
    },
    "S25: Golden MACD BMV": {
        "asset": "BMV Stocks",
        "window": 16.0,
        "cagr": 0.2086,
        "max_dd": -0.1869,
        "sharpe": 0.45,
        "turnover": "~4.0x",
        "currency": "MXN",
        "is_live": True,
        "inception": "2026-07-15"
    },
    "S27: Golden Hurst": {
        "asset": "QQQ Index",
        "window": 16.0,
        "cagr": 0.0540,
        "max_dd": -0.4381,
        "sharpe": 0.48,
        "turnover": "~5.0x",
        "currency": "MXN",
        "is_live": True,
        "inception": "2026-07-15"
    },
    "S29: Golden Stat-Arb": {
        "asset": "Statistical Arbitrage Pairs",
        "window": 5.0,
        "cagr": 2.5345,
        "max_dd": -0.0001,
        "sharpe": 5.0354,
        "turnover": "~12 trades/year",
        "currency": "MXN",
        "is_live": True,
        "inception": "2026-07-15"
    },
    "S30: Golden MACD US Stocks": {
        "asset": "US Large Cap Equity",
        "window": 16.0,
        "cagr": 0.1520,
        "max_dd": -0.1800,
        "sharpe": 0.55,
        "turnover": "~3.5x",
        "currency": "USD",
        "is_live": True,
        "inception": "2026-07-15"
    },
    "S31: Fibonacci S&R": {
        "asset": "TQQQ & Cash",
        "window": 16.51,
        "cagr": 0.1356,
        "max_dd": -0.4960,
        "sharpe": 0.15,
        "turnover": "~8.0 trades/year",
        "currency": "MXN",
        "is_live": True,
        "inception": "2026-07-15"
    },
    "S7: Core Hybrid Portfolio": {
        "asset": "Consolidated Multi-Asset",
        "window": 4.0,
        "cagr": 0.1563,
        "max_dd": -0.1049,
        "sharpe": 1.07,
        "turnover": "Dynamic Rebalancing",
        "currency": "USD",
        "is_live": True,
        "inception": "2026-07-02"
    }
}

def valuation_price(h):
    """Best available price for valuing a holding: last_price when it is a
    finite positive number, otherwise fall back to buy_price. Protects the
    report from NaN last_price values written while markets were closed."""
    for key in ("last_price", "buy_price"):
        try:
            px = float(h.get(key, 0.0))
            if math.isfinite(px) and px > 0:
                return px
        except (TypeError, ValueError):
            continue
    return 0.0

def get_nav(portfolio_data):
    if not portfolio_data:
        return 0.0, 0.0, 0.0
    if "total_portfolio_value_usd" in portfolio_data and "sleeves" in portfolio_data:
        # Strategy 18 (Efficient Frontier)
        nav = float(portfolio_data["total_portfolio_value_usd"])
        return nav, 0.0, nav
    cash_mxn = float(portfolio_data.get("cash_balance_mxn", 0.0))
    cash_usd = float(portfolio_data.get("cash_balance_usd", 0.0))
    cash = float(portfolio_data.get("cash_balance", 0.0)) + cash_mxn

    holdings_val = 0.0
    for h in portfolio_data.get("holdings", []):
        if "shares" in h:
            holdings_val += float(h["shares"]) * valuation_price(h)
        elif "last_price" in h:
            holdings_val += valuation_price(h)

    return (cash + holdings_val), cash, cash_usd

def load_json(path):
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return None

def build_kpi_report(today_str):
    """Report archival research without presenting invalid results as forecasts."""
    candidates, blocked = [], []
    for name, kpi in STRATEGY_KPIS.items():
        reason = backtest_block(name)
        if reason:
            blocked.append((name, reason))
        else:
            candidates.append((name, kpi))
    candidates.sort(key=lambda item: item[1]["window"] * item[1]["sharpe"], reverse=True)
    lines = [
        "# Strategy Research Evidence Review",
        f"**Report compiled:** {today_str}",
        "",
        "These are archival backtest references, not current live returns or verified forecasts.",
        "Code repairs invalidate old results; they do not certify replacement performance.",
        "The score is a research-prioritization heuristic, not statistical confidence.",
        "No strategy is approved for deployment by this report.",
        "",
        "## Research references not invalidated by this review",
        "",
        "| Strategy | Nominal Sharpe × years | Years | Archived Sharpe | Archived CAGR | Archived MaxDD |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name, kpi in candidates:
        score = kpi["window"] * kpi["sharpe"]
        lines.append(f"| {name} | {score:.2f} | {kpi['window']:.2f} | {kpi['sharpe']:.2f} | {kpi['cagr']:.2%} | {kpi['max_dd']:.2%} |")
    lines += [
        "",
        "S12–S15 still need synthetic-leverage, timing, carry, and accounting validation.",
        "S14/S15 are near-duplicate return streams, not independent diversification.",
        "Being listed here does not establish out-of-sample success or an investable edge.",
        "",
        "## Invalidated or insufficient evidence — excluded from ranking",
        "",
        "| Strategy | Required repair or validation |",
        "|---|---|",
    ]
    lines.extend(f"| {name} | {reason} |" for name, reason in blocked)
    lines += [
        "",
        "Five-year compounding projections have been withdrawn: disputed or short-sample",
        "backtest CAGRs must not be presented as expected future investment outcomes.",
        "See STRATEGY_EVALUATION_2026-10-05.md and ACCOUNTING_REVIEW_FOLLOWUP.md.",
    ]
    return "\n".join(lines) + "\n"


def main():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "comprehensive_strategy_kpis.md")
    with open(path, "w", encoding="utf-8") as report:
        report.write(build_kpi_report(datetime.date.today().isoformat()))
    print(f"Research evidence review written to {path}")


if __name__ == "__main__":
    main()
