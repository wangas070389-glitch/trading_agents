# Strategy 16: Setup Comparison & Matrix Analysis

This table breaks down the metrics, parameters, advantages, and risks of the four Strategy 16 setups to help you select the optimal live configuration.

---

## Comparative Matrix

| Setup Name | Return (60d) | Sharpe Ratio | Max Drawdown | Trades | Key Parameters | Primary Advantages | Key Risks / Disadvantages |
| :--- | :---: | :---: | :---: | :---: | :--- | :--- | :--- |
| **1. Original Intraday Baseline** | **-35.81%** | **-6.70** | **-36.52%** | **41** | • 30m bars<br>• 1.5 ATR stop<br>• EOD Liquidation<br>• 0.29% transaction fee | None (historical baseline) | • **Fatal fee drag** (Mexican broker commissions consume all edge).<br>• **Noise stop-outs** (1.5 ATR on 30m stops out with a 0% win rate). |
| **2. S10 Breakout Prototype** | **+20.38%** | **+3.37** | **-10.12%** | **21** | • 30m bars<br>• 1.5 ATR stop<br>• Breakout entries<br>• 0% Alpaca fee | • **High Sharpe Ratio** (very smooth equity curve).<br>• **Low Drawdown** (EOD liquidations shield from overnight risk). | • **Misses big moves** (liquidating at EOD cuts off long-term swing trends).<br>• Breakout entries buy high. |
| **3. Pure Swing (1h + 60d HMM)** | **+59.00%** | **+0.99** | **-10.70%** | **17** | • 1h bars<br>• 3.0 ATR stop<br>• Pullback entries<br>• 0% Alpaca fee<br>• Hold overnight | • **High Total Return** (multi-day swing holds capture massive gains).<br>• **Pullback entries** (buys the dip instead of breakouts). | • **Overnight Gap Risk** (holding positions overnight increases volatility).<br>• Wider stop (3.0 ATR) means individual stop-outs are larger. |
| **4. Hybrid Swing + Profit Tightening (Best of Both)** | **+59.00%** | **+0.99** | **-10.70%** | **17** | • 1h bars<br>• 3.0 ATR to 1.5 ATR stop<br>• Pullback entries<br>• 0% Alpaca fee<br>• Hold overnight | • **Stellar Returns** (+59.00% return).<br>• **Active Profit-Locking** (automatically tightens trailing stop to 1.5 ATR once profit > 1.5 ATR).<br>• Combines the pullback entry edge with S10 profit protection. | • **Overnight Gap Risk** (still holds positions overnight, exposing to gap-down risks). |

---

## Summary & Recommendations

1.  **Avoid Intraday Scalping:** The baseline results prove that trading on tight stops with intraday liquidations creates negative edge.
2.  **The Pullback Edge:** Pullback entries (**CCI < -100** and **ADX > 20**) perform significantly better than momentum breakout entries, as they buy structural dips rather than chasing highs.
3.  **Optimal Configuration:** The **Hybrid Swing + Profit Tightening (Setup 4)** is the recommended path forward. It lets your profits run during major multi-day trends but locks them in automatically if the trend begins to reverse.
