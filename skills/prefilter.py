"""
Cheap pre-filter funnel for the expanded S&P 500 universe.

Why this exists: GARCH + HMM per ticker costs seconds each. 500 tickers
would push the daily Action past 30 minutes and the Saturday training job
into hours. This stage cuts ~500 names to MAX_DEEP_CANDIDATES using one
BATCHED yfinance download and vectorized pandas — no model fitting.

The funnel, in order:

1. DATA COMPLETENESS — at least MIN_HISTORY_DAYS of prices in the batch
   window; dead/halted/just-listed tickers drop out.
2. AFFORDABILITY — share price in MXN must be <= MAX_PRICE_FRACTION of
   current portfolio value. This is the binding constraint of a ~20,000 MXN
   account: a stock you can only buy 0 or 1 shares of cannot be weighted,
   and the screener must never nominate positions the reconciler cannot
   open. At 20% and today's portfolio (~20,300 MXN) the cut is ~4,060 MXN
   (~225 USD)/share — at least 2 shares fit under the 40% concentration cap,
   which is the minimum granularity for weights to mean anything.
3. LIQUIDITY — 30-day ADTV in MXN through the existing gatekeeper
   (trivially passed by SPX names; kept for symmetry with BMV).
4. CHEAP RANKING — survivors ranked by 60-day risk-adjusted momentum
   (mean daily return / daily vol). The top MAX_DEEP_CANDIDATES advance to
   the expensive GARCH/HMM stage. This is a coarse pre-screen, NOT the
   signal: its only job is to ensure the deep stage spends its budget on
   names that are at least trending and tradable.

Honest caveat: any pre-filter discards information. A strong DCS name with
flat 60-day momentum can be cut at stage 4 before the HMM ever sees it.
That is the deliberate price of a bounded runtime; widen
MAX_DEEP_CANDIDATES if the Action budget allows.
"""

import numpy as np
import pandas as pd

MIN_HISTORY_DAYS = 100        # within the ~6-month batch window
MAX_PRICE_FRACTION = 0.20     # of portfolio value, per share
MAX_DEEP_CANDIDATES = 35      # US names forwarded to GARCH/HMM stage
MOMENTUM_WINDOW = 60
ADTV_THRESHOLD_MXN = 5_000_000.0


def prefilter_us_universe(batch_close: pd.DataFrame,
                          batch_volume: pd.DataFrame,
                          usdmxn_rate: float,
                          portfolio_value_mxn: float,
                          max_candidates: int = MAX_DEEP_CANDIDATES) -> dict:
    """
    batch_close / batch_volume: wide DataFrames (dates x tickers) from a
    single yf.download(tickers, period="6mo") call.
    Returns {ticker: diagnostics} for the selected candidates, ranked.
    """
    max_price_mxn = portfolio_value_mxn * MAX_PRICE_FRACTION
    rows = []
    rejects = {"history": 0, "affordability": 0, "liquidity": 0}

    for ticker in batch_close.columns:
        px = batch_close[ticker].dropna()
        if len(px) < MIN_HISTORY_DAYS:
            rejects["history"] += 1
            continue

        last_usd = float(px.iloc[-1])
        price_mxn = last_usd * usdmxn_rate
        if price_mxn > max_price_mxn:
            rejects["affordability"] += 1
            continue

        vol = batch_volume[ticker].reindex(px.index).fillna(0.0)
        adtv_mxn = float((px.iloc[-30:] * vol.iloc[-30:]).mean()) * usdmxn_rate
        if adtv_mxn < ADTV_THRESHOLD_MXN:
            rejects["liquidity"] += 1
            continue

        rets = np.log(px / px.shift(1)).dropna().iloc[-MOMENTUM_WINDOW:]
        sd = float(rets.std())
        momentum_score = float(rets.mean()) / sd if sd > 1e-10 else 0.0

        rows.append({
            "ticker": ticker,
            "price_usd": last_usd,
            "price_mxn": round(price_mxn, 2),
            "adtv_mxn": round(adtv_mxn, 0),
            "momentum_score": round(momentum_score, 5),
        })

    rows.sort(key=lambda r: r["momentum_score"], reverse=True)
    selected = rows[:max_candidates]

    print(f"  |-- [Pre-filter] {len(batch_close.columns)} SPX tickers -> "
          f"{len(rows)} tradable (rejected: {rejects['history']} history, "
          f"{rejects['affordability']} affordability @ <= {max_price_mxn:,.0f} MXN/share, "
          f"{rejects['liquidity']} liquidity) -> top {len(selected)} by "
          f"{MOMENTUM_WINDOW}d risk-adjusted momentum advance to deep screening.")

    return {r["ticker"]: r for r in selected}
