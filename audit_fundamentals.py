"""
Audits yfinance fundamentals coverage across the live BMV/US universe.

For each ticker, checks whether the fields required by the DCF engine and
fundamental ratio calculator are populated and reasonable. Writes a Markdown
table to audit_fundamentals_report.md and prints a summary to stdout.

This is a diagnostic: if a large fraction of tickers have missing or
nonsensical fundamentals, the DCF pipeline cannot be trusted without
swapping to a paid data source.
"""

import os
import sys
import time
import math
import yfinance as yf

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ingest_live_bmv import BMV_TICKERS, US_TICKERS


# Fields the DCF engine and ratio calculator need.
# Each entry: (display_name, info_key, fallback_keys, must_be_positive)
DCF_FIELDS = [
    ("shares_outstanding", "sharesOutstanding", ["impliedSharesOutstanding"], True),
    ("market_cap",         "marketCap",        [],                            True),
    ("ttm_net_income",     "netIncomeToCommon",["trailingEps"],               False),  # can be negative
    ("ttm_ebitda",         "ebitda",           [],                            False),
    ("total_debt",         "totalDebt",        [],                            False),  # can be zero
    ("cash",               "totalCash",        [],                            False),
    ("book_value",         "bookValue",        [],                            False),  # per-share, can be negative
    ("beta",               "beta",             [],                            False),
    ("dividend_rate",      "dividendRate",     [],                            False),
    ("trailing_pe",        "trailingPE",       [],                            False),
]


def fetch_info(ticker_symbol: str, retries: int = 2) -> dict:
    """Pull .info from yfinance with one retry. Returns {} on permanent failure."""
    for attempt in range(retries):
        try:
            info = yf.Ticker(ticker_symbol).info or {}
            if info:
                return info
        except Exception as exc:
            if attempt == retries - 1:
                print(f"  [ERROR] {ticker_symbol}: {exc}")
            else:
                time.sleep(2)
    return {}


def get_field(info: dict, primary_key: str, fallback_keys: list) -> object:
    """Look up a field by primary key, then fallbacks. Returns None if all missing."""
    for key in [primary_key] + fallback_keys:
        if key in info and info[key] is not None:
            value = info[key]
            if isinstance(value, float) and math.isnan(value):
                continue
            return value
    return None


def audit_ticker(ticker_symbol: str) -> dict:
    """Audit a single ticker. Returns a dict with field-by-field status."""
    info = fetch_info(ticker_symbol)
    if not info:
        return {"ticker": ticker_symbol, "fetchable": False, "fields": {}, "usable": False, "issues": ["info fetch failed"]}

    fields = {}
    issues = []
    for display_name, info_key, fallback_keys, must_be_positive in DCF_FIELDS:
        value = get_field(info, info_key, fallback_keys)
        if value is None:
            fields[display_name] = None
            issues.append(f"missing {display_name}")
        elif must_be_positive and (not isinstance(value, (int, float)) or value <= 0):
            fields[display_name] = value
            issues.append(f"{display_name} not positive ({value})")
        else:
            fields[display_name] = value

    # DCF-usable means we have the critical inputs: shares, debt, cash, EBITDA, net income
    critical_keys = ["shares_outstanding", "ttm_ebitda", "ttm_net_income", "total_debt", "cash"]
    usable = all(fields.get(k) is not None for k in critical_keys)

    return {
        "ticker": ticker_symbol,
        "fetchable": True,
        "fields": fields,
        "usable": usable,
        "issues": issues,
    }


def format_value(value) -> str:
    if value is None:
        return "—"
    if isinstance(value, (int, float)):
        if abs(value) > 1e9:
            return f"{value/1e9:.2f}B"
        if abs(value) > 1e6:
            return f"{value/1e6:.2f}M"
        if abs(value) > 1e3:
            return f"{value/1e3:.2f}K"
        return f"{value:.2f}"
    return str(value)


def main():
    all_tickers = BMV_TICKERS + US_TICKERS
    print("=" * 80)
    print(f"FUNDAMENTALS AUDIT — {len(all_tickers)} tickers ({len(BMV_TICKERS)} BMV + {len(US_TICKERS)} US)")
    print("=" * 80)

    results = []
    for i, ticker in enumerate(all_tickers, 1):
        print(f"[{i}/{len(all_tickers)}] {ticker}...", end=" ", flush=True)
        result = audit_ticker(ticker)
        results.append(result)
        if not result["fetchable"]:
            print("FAILED (no info)")
        elif result["usable"]:
            print("OK")
        else:
            print(f"INCOMPLETE ({len(result['issues'])} issues)")

    # Summary
    n_fetchable = sum(1 for r in results if r["fetchable"])
    n_usable = sum(1 for r in results if r["usable"])
    n_bmv_usable = sum(1 for r in results if r["usable"] and r["ticker"] in BMV_TICKERS)
    n_us_usable = sum(1 for r in results if r["usable"] and r["ticker"] in US_TICKERS)

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"  Fetchable:        {n_fetchable}/{len(all_tickers)}")
    print(f"  DCF-usable:       {n_usable}/{len(all_tickers)} ({100*n_usable/len(all_tickers):.0f}%)")
    print(f"    BMV usable:     {n_bmv_usable}/{len(BMV_TICKERS)} ({100*n_bmv_usable/max(1,len(BMV_TICKERS)):.0f}%)")
    print(f"    US usable:      {n_us_usable}/{len(US_TICKERS)} ({100*n_us_usable/max(1,len(US_TICKERS)):.0f}%)")

    # Write report
    report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audit_fundamentals_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# yfinance Fundamentals Coverage Audit\n\n")
        f.write(f"**Universe:** {len(all_tickers)} tickers ({len(BMV_TICKERS)} BMV + {len(US_TICKERS)} US)\n\n")
        f.write("## Summary\n\n")
        f.write(f"- Fetchable: {n_fetchable}/{len(all_tickers)}\n")
        f.write(f"- DCF-usable: {n_usable}/{len(all_tickers)} ({100*n_usable/len(all_tickers):.0f}%)\n")
        f.write(f"- BMV usable: {n_bmv_usable}/{len(BMV_TICKERS)} ({100*n_bmv_usable/max(1,len(BMV_TICKERS)):.0f}%)\n")
        f.write(f"- US usable: {n_us_usable}/{len(US_TICKERS)} ({100*n_us_usable/max(1,len(US_TICKERS)):.0f}%)\n\n")
        f.write("A ticker is **DCF-usable** when shares outstanding, EBITDA, net income, debt, ")
        f.write("and cash are all present and shares are positive. Without these the DCF engine ")
        f.write("produces meaningless intrinsic values.\n\n")
        f.write("## Per-Ticker Detail\n\n")
        f.write("| Ticker | Usable | Shares | Mkt Cap | NetInc TTM | EBITDA | Debt | Cash | Beta | Issues |\n")
        f.write("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |\n")
        for r in results:
            fields = r["fields"]
            status = "OK" if r["usable"] else ("FAIL" if not r["fetchable"] else "PARTIAL")
            f.write(
                f"| {r['ticker']} | {status} "
                f"| {format_value(fields.get('shares_outstanding'))} "
                f"| {format_value(fields.get('market_cap'))} "
                f"| {format_value(fields.get('ttm_net_income'))} "
                f"| {format_value(fields.get('ttm_ebitda'))} "
                f"| {format_value(fields.get('total_debt'))} "
                f"| {format_value(fields.get('cash'))} "
                f"| {format_value(fields.get('beta'))} "
                f"| {'; '.join(r['issues'][:3]) if r['issues'] else '—'} |\n"
            )

    print(f"\nReport written to: {report_path}")

    # Honest verdict
    print("\n" + "=" * 80)
    print("VERDICT")
    print("=" * 80)
    pct_usable = 100 * n_usable / len(all_tickers)
    if pct_usable >= 90:
        print(f"  yfinance fundamentals look usable ({pct_usable:.0f}% complete).")
        print("  DCF pipeline can run on live data with this source.")
    elif pct_usable >= 60:
        print(f"  Mixed quality ({pct_usable:.0f}% complete).")
        print("  DCF will skip a meaningful fraction of the universe. Acceptable for")
        print("  a screen, not for a portfolio that needs to be fully invested.")
    else:
        print(f"  Insufficient coverage ({pct_usable:.0f}% complete).")
        print("  DCF cannot be trusted on this data source. Either swap to a paid")
        print("  fundamentals provider (FMP, Tiingo, IEX Cloud, Bloomberg) or drop")
        print("  the DCF leg from the strategy.")


if __name__ == "__main__":
    main()
