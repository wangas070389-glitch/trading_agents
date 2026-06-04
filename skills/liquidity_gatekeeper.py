def calculate_adtv(prices: list[float], volumes: list[float]) -> float:
    """
    Calculates the Average Daily Traded Volume (ADTV) in MXN.
    ADTV = (1 / N) * sum(Price_t * Volume_t)
    Usually N = 30.
    """
    if not prices or not volumes:
        return 0.0
    
    n = min(len(prices), len(volumes), 30)
    if n == 0:
        return 0.0
        
    # Get last n days of data
    recent_prices = prices[-n:]
    recent_volumes = volumes[-n:]
    
    total_value = sum(p * v for p, v in zip(recent_prices, recent_volumes))
    return total_value / n

def passes_liquidity_gate(adtv: float, threshold: float = 5000000.0) -> bool:
    """
    Determines if the ADTV meets the critical threshold (default 5M MXN).
    """
    return adtv >= threshold
