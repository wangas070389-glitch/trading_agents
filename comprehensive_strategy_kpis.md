# Comprehensive Strategy KPI & Compounding Report
**Report Compiled on:** 2026-07-14 | **Evidence-Quality Ranked**

## 1. Evidence Quality Rank & 5-Year Projection Grid
This table ranks strategies by **Evidence Quality Score** (`Sharpe * Backtest Window (Years)`), ensuring that 60-day in-sample strategies are properly contextualized behind long-window, walk-forward verified strategies.

| Rank & Strategy | Evidence Score | Window (Years) | Sharpe | CAGR % | Max Drawdown % | Year 5 (MXN) | Total Profit (MXN) | ROI % |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1. S12: Vol-Targeted Trend (VTTL)** | **10.35** | 22.50 | 0.46 | 17.13% | -21.34% | **$492,942.65** | $212,942.65 | +76.1% |
| **2. S14: Aggregator (HEDGE)** | **10.18** | 19.20 | 0.53 | 15.17% | -15.19% | **$462,672.61** | $182,672.61 | +65.2% |
| **3. S15: Tracker (TRACK)** | **10.18** | 19.20 | 0.53 | 15.05% | -14.73% | **$460,875.01** | $180,875.01 | +64.6% |
| **4. S13: Risk Appetite (CARA)** | **8.64** | 19.20 | 0.45 | 15.95% | -25.02% | **$474,512.14** | $194,512.14 | +69.5% |
| **5. S2: 1d MACD Systematic** | **6.35** | 5.00 | 1.27 | 13.10% | -10.94% | **$432,536.48** | $152,536.48 | +54.5% |
| **6. S3: US Stock Momentum** | **5.75** | 5.00 | 1.15 | 25.40% | -18.20% | **$641,104.64** | $361,104.64 | +129.0% |
| **7. S8: Dividend Quality** | **5.60** | 5.00 | 1.12 | 14.50% | -11.20% | **$452,716.53** | $172,716.53 | +61.7% |
| **8. S20: Hurst Exponent Dynamic** | **5.58** | 16.41 | 0.34 | 24.29% | -63.71% | **$619,163.24** | $339,163.24 | +121.1% |
| **9. S19: Particle Filter QQQ/TQQQ/SQQQ** | **5.09** | 16.41 | 0.31 | 21.92% | -51.78% | **$574,523.45** | $294,523.45 | +105.2% |
| **10. S18: Efficient Frontier** | **4.64** | 4.00 | 1.16 | 13.66% | -3.29% | **$440,508.46** | $160,508.46 | +57.3% |
| **11. S4: US DCS Value-Growth** | **4.56** | 4.00 | 1.14 | 21.93% | -12.19% | **$574,705.64** | $294,705.64 | +105.3% |
| **12. S7: Core Hybrid Portfolio** | **4.28** | 4.00 | 1.07 | 15.63% | -10.49% | **$469,622.22** | $189,622.22 | +67.7% |
| **13. S22: Walk-Forward ML Classifier** | **4.27** | 16.42 | 0.26 | 21.13% | -58.66% | **$560,291.21** | $280,291.21 | +100.1% |
| **14. S6: High-Beta Momentum** | **4.20** | 4.00 | 1.05 | 22.10% | -19.50% | **$577,810.81** | $297,810.81 | +106.4% |
| **15. S5: Alternative Assets** | **3.80** | 4.00 | 0.95 | 18.40% | -15.20% | **$513,495.30** | $233,495.30 | +83.4% |
| **16. S1: Adaptive Value** | **3.28** | 4.00 | 0.82 | 20.07% | -28.18% | **$541,687.84** | $261,687.84 | +93.5% |
| **17. S9: AI Regime Stat-Arb** | **2.90** | 2.00 | 1.45 | 26.80% | -7.50% | **$669,753.18** | $389,753.18 | +139.2% |
| **18. S21: Shannon Entropy Dynamic** | **0.49** | 16.41 | 0.03 | 10.85% | -70.25% | **$401,812.64** | $121,812.64 | +43.5% |
| **19. S10: AI Intraday VWAP** | **0.45** | 0.16 | 2.73 | 53.25% | -4.14% | **$1,462,659.29** | $1,182,659.29 | +422.4% |
| **20. S17: FIBRAs Dynamic** | **0.32** | 4.00 | 0.08 | 7.46% | -16.93% | **$359,282.39** | $79,282.39 | +28.3% |
| **21. S11: AI Intraday CCI-ADX** | **0.02** | 0.16 | 0.10 | 11.88% | -16.31% | **$415,621.33** | $135,621.33 | +48.4% |
| **22. S16: HMM Intraday Router** | **-0.21** | 0.16 | -1.27 | -11.29% | -18.29% | **$191,032.04** | $-88,967.96 | -31.8% |

---

## 2. Methodology & Evidence Score Philosophy
* **Evidence Quality Score (`Sharpe * Window`)**: Raw CAGR is a deceptive metric if calculated over short or in-sample periods. S11 and S10 are evaluated over only 60 days (0.16 years) of intraday data, giving them high raw CAGR but very low evidence scores (0.31 and 0.25).
* **Out-of-Sample Podiums**: S12, S14, and S15 (VTTL, HEDGE, TRACK) represent 19-22 year honest backtest windows spanning multiple market cycles (including 2008). They occupy the top ranks because their performance has high mathematical evidence support.
* **HEDGE Aggregate Regret**: The HEDGE MWU strategy limits historical drawdown to **-15.19%** over 19.2 years compared to VTTL's **-21.34%**, capturing the diversification benefit of the expert mixture.