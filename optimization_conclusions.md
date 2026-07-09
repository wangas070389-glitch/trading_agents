# S11 & S16 Optimization Conclusions

The optimization journey for Strategy 11 and Strategy 16 has yielded four generalizable rules for algorithmic trading systems trading leveraged equity ETFs:

### 1. Higher Frequency carries Negative Edge
Trading on 30-minute intervals resulted in high trading frequency, stop-out whipsaws, and commission drag. Shifting to **1-hour intervals** act as an automatic low-pass filter, reducing transaction costs and improving entry win rates without changing indicator parameters.

### 2. EOD Liquidations act as a Tax on Swing Profits
Enforcing mandatory end-of-day liquidations to avoid overnight risk significantly degrades performance. Transitioning to **overnight swing holds** allows models to capture multi-day trends. 

### 3. HMM Training Data Balance (The 60-Day Rule)
The stability of a Gaussian HMM regime predictor is sensitive to training lookback:
* **Too short (<30 days):** Causes overfitting and state instability (constant flips between bull/bear/chop).
* **Too long (>90 days):** Dilutes recent volatility shifts, rendering the model slow to adapt.
* **The Sweet Spot (60 days of 1h bars):** ~420 samples provides sufficient statistical significance for convergence while maintaining high responsiveness to new market regimes.

### 4. Hybrid Stops act as High-Performance Capital Protectors
Wider trailing stops (**3.0 ATR**) are necessary at position entry to prevent premature stop-outs from local pullback noise. However, once a trade moves in-favor by **1.5 ATR**, tightening the stop to **1.5 ATR** secures accrued profits. This hybrid model provides the maximum benefit of both wide breathing room and tight profit-locking.
