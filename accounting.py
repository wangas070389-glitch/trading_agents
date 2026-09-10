"""Shared valuation rules. Currency-specific cash supersedes legacy cash."""
import math


def finite_number(value):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("Non-finite accounting value")
    return result


def cash_value(portfolio, currency, fx):
    if fx <= 0:
        raise ValueError("FX must be positive")
    if "cash_balance_mxn" in portfolio or "cash_balance_usd" in portfolio:
        mxn = finite_number(portfolio.get("cash_balance_mxn", 0))
        usd = finite_number(portfolio.get("cash_balance_usd", 0))
        return mxn + usd * fx if currency == "MXN" else usd + mxn / fx
    return finite_number(portfolio.get("cash_balance", 0))


def nav_value(portfolio, currency, fx):
    cash = cash_value(portfolio, currency, fx)
    value = cash
    for holding in portfolio.get("holdings", []):
        quantity = finite_number(holding["shares"])
        if not quantity:
            continue
        price = valuation_price(holding)
        if not price:
            raise ValueError("Holding has no usable price")
        value += quantity * price
    return value, cash


def valuation_price(holding):
    """Fallback prices are estimates; ledger verification does not certify marks."""
    for key in ("last_price", "current_price", "buy_price"):
        try:
            value = finite_number(holding.get(key))
            if value > 0:
                return value
        except (TypeError, ValueError):
            continue
    return 0.0
