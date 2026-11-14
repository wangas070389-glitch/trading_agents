"""Small, offline performance-accounting primitives (no broker or file I/O)."""
import math


def flow_adjusted_return(opening_nav, closing_nav, external_flow=0.0, *, timing="start"):
    """Return net of all modeled costs, excluding deposits/withdrawals.

    Use start for a flow before the period's investment return; use end for a
    flow after it. Dividends and interest are investment income, not flows.
    """
    if not all(math.isfinite(v) for v in (opening_nav, closing_nav, external_flow)):
        raise ValueError("Finite NAV and external flows required")
    if timing == "start":
        denominator, numerator = opening_nav + external_flow, closing_nav
    elif timing == "end":
        denominator, numerator = opening_nav, closing_nav - external_flow
    else:
        raise ValueError("Flow timing must be start or end")
    if denominator <= 0 or numerator < 0:
        raise ValueError("Positive invested capital and nonnegative NAV required")
    return numerator / denominator - 1.0
