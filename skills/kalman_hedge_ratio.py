"""
Kalman Filter Dynamic Hedge Ratio Module

Provides online, recursive 2D Kalman filtering to estimate time-varying 
hedge ratios (beta) and intercepts (alpha) between cointegrated asset pairs.
Used for statistical arbitrage (S9, S29).
"""

import numpy as np


class KalmanHedgeTracker:
    """
    2D Online Kalman Filter for time-varying linear relationship y_t = alpha_t + beta_t * x_t + e_t.
    """

    def __init__(self, delta: float = 1e-4, R: float = 1e-3):
        """
        delta: State transition variance scale (process noise).
        R: Observation noise variance.
        """
        self.delta = delta
        self.R = R
        self.P = np.zeros((2, 2))
        self.theta = np.zeros(2)  # [alpha, beta]
        self.initialized = False

    def initialize(self, initial_alpha: float = 0.0, initial_beta: float = 1.0):
        self.theta = np.array([initial_alpha, initial_beta], dtype=np.float64)
        self.P = np.eye(2, dtype=np.float64) * 1.0
        self.initialized = True

    def update(self, y: float, x: float) -> dict:
        """
        Updates the state estimate with observation (y, x).
        Returns current state estimate (alpha, beta, spread, std_error).
        """
        if not self.initialized:
            self.initialize(0.0, y / x if x != 0 else 1.0)

        # Observation matrix H = [1, x]
        H = np.array([1.0, x], dtype=np.float64)

        # Process noise covariance Q
        Q = self.delta / (1.0 - self.delta) * np.eye(2)

        # State prediction covariance
        P_pred = self.P + Q

        # Innovation / residual
        y_hat = float(np.dot(H, self.theta))
        e = y - y_hat

        # Innovation covariance
        S = float(np.dot(H, np.dot(P_pred, H.T)) + self.R)

        # Kalman Gain K
        K = np.dot(P_pred, H.T) / S

        # State update
        self.theta = self.theta + K * e

        # Covariance update
        self.P = P_pred - np.outer(K, np.dot(H, P_pred))

        return {
            "alpha": float(self.theta[0]),
            "beta": float(self.theta[1]),
            "residual": float(e),
            "std_error": float(np.sqrt(S))
        }


def calculate_kalman_hedge_ratio(y_series: np.ndarray, x_series: np.ndarray, delta: float = 1e-4) -> dict:
    """
    Computes time-series of Kalman Filter state estimates across historical price arrays.
    
    y_series, x_series: 1D numpy arrays of log-prices.
    returns: dict containing betas, alphas, and z-score spread series.
    """
    n = len(y_series)
    if n < 5 or n != len(x_series):
        return {"beta": 1.0, "alpha": 0.0, "current_zscore": 0.0}

    tracker = KalmanHedgeTracker(delta=delta)
    betas = np.zeros(n)
    alphas = np.zeros(n)
    spreads = np.zeros(n)

    for i in range(n):
        res = tracker.update(y_series[i], x_series[i])
        alphas[i] = res["alpha"]
        betas[i] = res["beta"]
        spreads[i] = res["residual"]

    # Calculate rolling Z-score of residual spread over last 30 periods
    window = min(n, 30)
    recent_spreads = spreads[-window:]
    mean_s = np.mean(recent_spreads)
    std_s = np.std(recent_spreads)

    zscore = float((spreads[-1] - mean_s) / std_s) if std_s > 1e-8 else 0.0

    return {
        "beta": float(betas[-1]),
        "alpha": float(alphas[-1]),
        "current_zscore": zscore,
        "historical_betas": betas,
        "spreads": spreads
    }
