import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from statsmodels.tsa.stattools import coint

def compute_hedge_ratio(prices_a, prices_b):
    """
    Fits a linear regression price_a = alpha + beta * price_b
    to find the statistical hedge ratio (beta) and the spread series.
    """
    x = np.array(prices_b).reshape(-1, 1)
    y = np.array(prices_a)
    model = LinearRegression().fit(x, y)
    beta = model.coef_[0]
    alpha = model.intercept_
    spread = y - (alpha + beta * np.array(prices_b))
    return float(beta), float(alpha), spread

def test_cointegration(prices_a, prices_b):
    """
    Performs the Engle-Granger two-step cointegration test.
    Returns the p-value. Cointegrated if p_value < 0.05.
    """
    if len(prices_a) < 50 or len(prices_b) < 50:
        return 1.0
    # coint returns: (adf_stat, p_value, critical_values)
    _, p_value, _ = coint(prices_a, prices_b)
    return float(p_value)

class StatisticalArbitrageEngine:
    def __init__(self, p_value_threshold=0.05):
        self.p_value_threshold = p_value_threshold
        # Cache of identified active cointegrated pairs: (asset_a, asset_b) -> metadata
        self.active_pairs = {}

    def update_cointegration_graph(self, universe_prices_dict):
        """
        Scans a dictionary of ticker -> historical price array to find cointegrated pairs.
        To keep execution fast, we limit the search to a sub-universe of liquid assets.
        """
        self.active_pairs = {}
        tickers = list(universe_prices_dict.keys())
        # Sort tickers to limit scan if universe is large (limit to top 12 for speed)
        tickers = sorted(tickers)[:12]
        
        for i in range(len(tickers)):
            for j in range(i + 1, len(tickers)):
                t_a = tickers[i]
                t_b = tickers[j]
                
                prices_a = universe_prices_dict[t_a]
                prices_b = universe_prices_dict[t_b]
                
                # Align lengths
                min_len = min(len(prices_a), len(prices_b))
                p_a = prices_a[-min_len:]
                p_b = prices_b[-min_len:]
                
                p_val = test_cointegration(p_a, p_b)
                if p_val < self.p_value_threshold:
                    beta, alpha, spread = compute_hedge_ratio(p_a, p_b)
                    spread_std = float(np.std(spread))
                    current_spread_val = float(spread[-1])
                    
                    self.active_pairs[(t_a, t_b)] = {
                        "p_value": p_val,
                        "beta": beta,
                        "alpha": alpha,
                        "spread_std": spread_std,
                        "current_spread": current_spread_val,
                        # Normalized spread (Z-score)
                        "z_score": current_spread_val / max(1e-4, spread_std)
                    }
        return self.active_pairs

    def apply_regime_arbitrage(self, base_weights, active_regimes):
        """
        Adjusts target weights based on cointegration spread and regime divergence.
        If Asset A and Asset B are cointegrated, but:
          - HMM(A) is Bull (state 1) and HMM(B) is Bear/Sideways (state -1/0)
          - The normalized spread (A - beta * B) is high (Z-score > 1.5)
        Then B is statistically lagging (undervalued relative to A).
        We dynamically shift 5% weight from A to B to capture the convergence.
        """
        adjusted_weights = base_weights.copy()
        shifts_applied = []

        for (t_a, t_b), meta in self.active_pairs.items():
            # Check if both are in base weights
            w_a = base_weights.get(t_a, 0.0)
            w_b = base_weights.get(t_b, 0.0)
            
            reg_a = active_regimes.get(t_a, 0)
            reg_b = active_regimes.get(t_b, 0)
            
            z_score = meta["z_score"]
            
            # Scenario 1: A is Bull (reg=1), B is lagging (reg<=0), Spread is high (Z > 1.0)
            if reg_a == 1 and reg_b <= 0 and z_score > 1.0:
                if w_a > 0.05:
                    shift = 0.05
                    adjusted_weights[t_a] = w_a - shift
                    # If B is not in long weights, add it with the shifted weight
                    adjusted_weights[t_b] = w_b + shift
                    shifts_applied.append(
                        f"Regime Arbitrage: Shifted {shift:.0%} from {t_a} (Bull, leading) to {t_b} (Lagging, undervalued spread Z={z_score:.2f})"
                    )
                    
            # Scenario 2: B is Bull (reg=1), A is lagging (reg<=0), Spread is low (Z < -1.0)
            elif reg_b == 1 and reg_a <= 0 and z_score < -1.0:
                if w_b > 0.05:
                    shift = 0.05
                    adjusted_weights[t_b] = w_b - shift
                    adjusted_weights[t_a] = w_a + shift
                    shifts_applied.append(
                        f"Regime Arbitrage: Shifted {shift:.0%} from {t_b} (Bull, leading) to {t_a} (Lagging, undervalued spread Z={z_score:.2f})"
                    )

        # Normalize weights to sum to <= 1.0
        total_w = sum(adjusted_weights.values())
        if total_w > 1.0:
            for k in adjusted_weights:
                adjusted_weights[k] = adjusted_weights[k] / total_w
                
        return adjusted_weights, shifts_applied

if __name__ == "__main__":
    print("Testing Engle-Granger Cointegration and Regime Arbitrage Engine...")
    np.random.seed(42)
    # Generate cointegrated series
    steps = 100
    x = np.cumsum(np.random.randn(steps))
    y = 0.8 * x + np.random.randn(steps) * 0.5 # Cointegrated
    z = np.cumsum(np.random.randn(steps)) # Random walk (not cointegrated)
    
    universe_prices = {
        "WALMEX.MX": y,
        "FEMSAUBD.MX": x,
        "AMXB.MX": z
    }
    
    engine = StatisticalArbitrageEngine()
    pairs = engine.update_cointegration_graph(universe_prices)
    
    print("\nIdentified Cointegrated Pairs:")
    for (t_a, t_b), meta in pairs.items():
        print(f"  |-- {t_a} vs {t_b}: p-value = {meta['p_value']:.4f} | Beta = {meta['beta']:.2f} | Z-Score = {meta['z_score']:.2f}")
        
    base_w = {"WALMEX.MX": 0.40, "FEMSAUBD.MX": 0.40}
    regimes = {"FEMSAUBD.MX": 1, "WALMEX.MX": 0} # FEMSA leading, WALMEX lagging
    
    adj_w, reports = engine.apply_regime_arbitrage(base_w, regimes)
    print("\nWeight Adjustments:")
    for r in reports:
        print(f"  |-- {r}")
    print(f"Adjusted weights: {adj_w}")
