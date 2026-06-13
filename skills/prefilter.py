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
