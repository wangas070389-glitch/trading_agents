"""
S&P 500 constituent universe with a three-source fallback chain.

Source priority (first to pass validation wins):
  1. GitHub open dataset (datasets/s-and-p-500-companies) — plain CSV over
     raw.githubusercontent.com; auto-maintained, no rate limits, no auth.
  2. Wikipedia constituents table — stable for 15+ years, HTML scrape.
  3. TradingView scanner endpoint — undocumented/unofficial; convenient but
     can change or block without notice. Last resort only.

Every fetched list must pass a VALIDATION GATE before it replaces the cache:
plausible size (480-510 tickers) and presence of sentinel mega-caps. A list
that fails validation is discarded and the previous cached list is used —
a stale-but-valid universe is always safer than a corrupted one for a system
trading unattended. The S&P changes composition only a handful of times per
quarter, so a cache up to CACHE_MAX_AGE_DAYS old costs essentially nothing.

The cache (spx_constituents.json) is committed to the repo by the Action so
every run — and every backtest — sees the same universe.

Known limitation (by design): all three sources return TODAY's members, so
any backtest over this universe carries survivorship bias. Treat expanded-
universe backtest numbers accordingly.
"""

import os
import io
import json
import datetime

import requests

CACHE_FILE = "spx_constituents.json"
CACHE_MAX_AGE_DAYS = 7

# Validation gate
MIN_PLAUSIBLE = 480
MAX_PLAUSIBLE = 510
SENTINELS = {"AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "JPM", "XOM"}

GITHUB_CSV_URL = ("https://raw.githubusercontent.com/datasets/"
                  "s-and-p-500-companies/main/data/constituents.csv")
WIKIPEDIA_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
TRADINGVIEW_SCAN_URL = "https://scanner.tradingview.com/america/scan"

REQUEST_TIMEOUT = 20
USER_AGENT = {"User-Agent": "Mozilla/5.0 (portfolio-research; contact: repo issues)"}


def _normalize(ticker: str) -> str:
    """Class shares: BRK.B -> BRK-B (Yahoo Finance convention)."""
    return ticker.strip().upper().replace(".", "-")


def _validate(tickers: list) -> bool:
    s = set(tickers)
    if not (MIN_PLAUSIBLE <= len(s) <= MAX_PLAUSIBLE):
        return False
    return SENTINELS.issubset(s)


# --------------------------------------------------------------------------- #
# Sources
# --------------------------------------------------------------------------- #
def _fetch_github_csv() -> list:
    resp = requests.get(GITHUB_CSV_URL, timeout=REQUEST_TIMEOUT, headers=USER_AGENT)
    resp.raise_for_status()
    import csv
    rows = list(csv.DictReader(io.StringIO(resp.text)))
    col = "Symbol" if rows and "Symbol" in rows[0] else "symbol"
    return [_normalize(r[col]) for r in rows if r.get(col)]


def _fetch_wikipedia() -> list:
    resp = requests.get(WIKIPEDIA_URL, timeout=REQUEST_TIMEOUT, headers=USER_AGENT)
    resp.raise_for_status()
    # The constituents table is the first wikitable with id="constituents".
    # Parse without pandas.read_html to avoid an lxml hard dependency.
    import re
    table_match = re.search(r'id="constituents".*?</table>', resp.text, re.S)
    if not table_match:
        raise ValueError("Wikipedia constituents table not found")
    # First <td> of each row holds the ticker (linked or plain)
    tickers = re.findall(r"<tr>\s*<td[^>]*>(?:<a[^>]*>)?([A-Z][A-Z0-9.\-]{0,6})(?:</a>)?\s*</td>",
                         table_match.group(0))
    return [_normalize(t) for t in tickers]


def _fetch_tradingview() -> list:
    payload = {
        "filter": [{"left": "index", "operation": "has", "right": ["SP:SPX"]}],
        "columns": ["name"],
        "range": [0, 600],
    }
    resp = requests.post(TRADINGVIEW_SCAN_URL, json=payload,
                         timeout=REQUEST_TIMEOUT, headers=USER_AGENT)
    resp.raise_for_status()
    data = resp.json().get("data", [])
    out = []
    for row in data:
        # symbol arrives as "NASDAQ:AAPL"
        sym = row.get("s", "")
        if ":" in sym:
            out.append(_normalize(sym.split(":", 1)[1]))
    return out


SOURCES = [
    ("github_dataset", _fetch_github_csv),
    ("wikipedia", _fetch_wikipedia),
    ("tradingview_scanner", _fetch_tradingview),
]


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def get_spx_tickers(dir_path: str, force_refresh: bool = False) -> list:
    """
    Returns the cached S&P 500 ticker list, refreshing it through the
    fallback chain when the cache is older than CACHE_MAX_AGE_DAYS.
    Never returns an unvalidated list; never deletes a valid cache on
    a failed refresh.
    """
    cache_path = os.path.join(dir_path, CACHE_FILE)
    cache = None
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cache = json.load(f)
        except (json.JSONDecodeError, OSError):
            cache = None

    if cache and not force_refresh:
        age = (datetime.date.today()
               - datetime.date.fromisoformat(cache["fetched_on"])).days
        if age <= CACHE_MAX_AGE_DAYS and _validate(cache["tickers"]):
            return cache["tickers"]

    for name, fetch in SOURCES:
        try:
            tickers = sorted(set(fetch()))
            if _validate(tickers):
                with open(cache_path, "w", encoding="utf-8") as f:
                    json.dump({
                        "fetched_on": datetime.date.today().isoformat(),
                        "source": name,
                        "count": len(tickers),
                        "tickers": tickers,
                    }, f, indent=1)
                print(f"  |-- [Constituents] {len(tickers)} SPX tickers via {name}.")
                return tickers
            print(f"  |-- [Constituents] {name} returned {len(set(tickers))} "
                  f"tickers — failed validation gate, trying next source.")
        except Exception as e:
            print(f"  |-- [Constituents] {name} failed: {e}")

    if cache and _validate(cache.get("tickers", [])):
        print(f"  |-- [Constituents] All sources failed. Using stale cache "
              f"from {cache['fetched_on']} ({cache['count']} tickers).")
        return cache["tickers"]

    raise RuntimeError(
        "No SPX constituent source available and no valid cache on disk. "
        "Run once with network access to seed spx_constituents.json."
    )
