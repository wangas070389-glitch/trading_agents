import os
import numpy as np
import pandas as pd
from scipy.optimize import minimize

def main():
    dir_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 1. Load NAV series
    files = {
        "S1_Alpha_Growth": ("backtest_alpha_growth_nav.csv", "Unnamed: 0", "strategy"),
        "S2_MACD_Trend": ("backtest_macd_nav.csv", "Unnamed: 0", "strategy"),
        "S4_US_DCS": ("us_stocks_dcf_backtest_nav.csv", "Date", "NAV"),
        "S5_Alternatives": ("alternatives_backtest_nav.csv", "Date", "NAV"),
        "S6_High_Beta": ("high_beta_backtest_nav.csv", "Date", "NAV"),
        "S8_Dividends": ("dividends_backtest_nav.csv", "date", "nav")
    }
    
    dfs = {}
    for name, (fname, date_col, nav_col) in files.items():
        fpath = os.path.join(dir_path, fname)
        if os.path.exists(fpath):
            df = pd.read_csv(fpath)
            # Ensure the date column is parsed correctly
            df["parsed_date"] = pd.to_datetime(df[date_col])
            df = df.set_index("parsed_date")
            dfs[name] = df[nav_col].astype(float)
        else:
            print(f"Warning: File {fpath} not found.")

    if len(dfs) < 2:
        print("Error: Not enough NAV files found to run optimization.")
        return
        
    # Merge into a single dataframe
    m_df = pd.DataFrame(dfs).ffill().dropna()
    print(f"Data merged successfully. Total overlapping trading days: {len(m_df)}")
    print(f"Period: {m_df.index[0].date()} to {m_df.index[-1].date()}")
    
    # Calculate daily returns
    rets = m_df.pct_change().dropna()
    
    # Annualized statistics
    ann_rets = rets.mean() * 252
    ann_cov = rets.cov() * 252
    ann_stds = rets.std() * np.sqrt(252)
    corrs = rets.corr()
    
    # Risk-free rate baseline (9.50% Mbonos)
    rf = 0.095
    
    num_assets = len(ann_rets)
    asset_names = ann_rets.index.tolist()
    
    # Functions for optimization
    def portfolio_stats(weights):
        weights = np.array(weights)
        p_ret = np.sum(ann_rets * weights)
        p_vol = np.sqrt(np.dot(weights.T, np.dot(ann_cov, weights)))
        p_sharpe = (p_ret - rf) / p_vol if p_vol > 0 else 0.0
        return p_ret, p_vol, p_sharpe

    def min_vol_func(weights):
        return portfolio_stats(weights)[1]

    def neg_sharpe_func(weights):
        return -portfolio_stats(weights)[2]

    # Bounds and constraints (weights sum to 1, no short selling)
    bounds = tuple((0.0, 1.0) for _ in range(num_assets))
    constraints = ({'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0})
    
    # Find MSR Portfolio
    init_weights = [1.0 / num_assets] * num_assets
    opt_sharpe = minimize(neg_sharpe_func, init_weights, method='SLSQP', bounds=bounds, constraints=constraints)
    msr_weights = opt_sharpe.x
    msr_ret, msr_vol, msr_sharpe = portfolio_stats(msr_weights)
    
    # Find GMV Portfolio
    opt_vol = minimize(min_vol_func, init_weights, method='SLSQP', bounds=bounds, constraints=constraints)
    gmv_weights = opt_vol.x
    gmv_ret, gmv_vol, gmv_sharpe = portfolio_stats(gmv_weights)
    
    # Find our current target portfolio
    # S1 (MXN Value/Alpha Growth): 25%, S4 (US DCS): 30%, S8 (Dividends): 20%, S6 (High Beta): 15%, S5 (Alternatives): 10%, S2 (MACD): 0%
    target_dict = {
        "S1_Alpha_Growth": 0.25,
        "S2_MACD_Trend": 0.0,
        "S4_US_DCS": 0.30,
        "S5_Alternatives": 0.10,
        "S6_High_Beta": 0.15,
        "S8_Dividends": 0.20
    }
    tgt_weights = []
    for name in asset_names:
        tgt_weights.append(target_dict.get(name, 0.0))
        
    tgt_weights = np.array(tgt_weights)
    tgt_weights = tgt_weights / np.sum(tgt_weights) # Re-normalize just in case
    tgt_ret, tgt_vol, tgt_sharpe = portfolio_stats(tgt_weights)
    
    # Draw the frontier curve
    min_ret = gmv_ret
    max_ret = np.max(ann_rets)
    target_returns = np.linspace(min_ret, max_ret, 15)
    frontier_vols = []
    
    for r in target_returns:
        cons = (
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0},
            {'type': 'eq', 'fun': lambda w: np.sum(ann_rets * w) - r}
        )
        res = minimize(min_vol_func, init_weights, method='SLSQP', bounds=bounds, constraints=cons)
        frontier_vols.append(res.fun)
        
    # Write report
    report = []
    report.append("# Strategy Portfolio Efficient Frontier Optimization Report\n")
    report.append(f"**Period Evaluated:** {m_df.index[0].date()} to {m_df.index[-1].date()}\n")
    
    report.append("## 1. Individual Strategy Annualized Metrics")
    report.append("| Strategy Component | Annualized Return | Annualized Volatility | Sharpe Ratio (Rf=9.5%) |")
    report.append("| :--- | :---: | :---: | :---: |")
    for name in asset_names:
        r = ann_rets[name]
        vol = ann_stds[name]
        sh = (r - rf) / vol
        report.append(f"| {name.replace('_', ' ')} | {r*100:.2f}% | {vol*100:.2f}% | {sh:.2f} |")
    
    report.append("\n## 2. Correlation Matrix")
    report.append("| | " + " | ".join([n.replace('_', ' ') for n in asset_names]) + " |")
    report.append("| :--- | " + " | ".join([":---:" for _ in asset_names]) + " |")
    for idx, row_name in enumerate(asset_names):
        cells = [row_name.replace('_', ' ')]
        for col_name in asset_names:
            cells.append(f"{corrs.loc[row_name, col_name]:.3f}")
        report.append("| " + " | ".join(cells) + " |")
        
    report.append("\n## 3. Key Optimized Portfolios")
    report.append("| Portfolio | Annualized Return | Annualized Volatility | Sharpe Ratio | Description |")
    report.append("| :--- | :---: | :---: | :---: | :--- |")
    report.append(f"| **Maximum Sharpe (MSR)** | {msr_ret*100:.2f}% | {msr_vol*100:.2f}% | **{msr_sharpe:.2f}** | Portfolio that maximizes return-to-risk |")
    report.append(f"| **Global Minimum Variance (GMV)** | {gmv_ret*100:.2f}% | {gmv_vol*100:.2f}% | {gmv_sharpe:.2f} | Portfolio with the absolute lowest risk |")
    report.append(f"| **Current Target Allocation (S7)** | {tgt_ret*100:.2f}% | {tgt_vol*100:.2f}% | {tgt_sharpe:.2f} | S4=30%, S1=25%, S8=20%, S6=15%, S5=10% |")
    
    report.append("\n## 4. Portfolio Allocation Comparison")
    headers = ["Asset Strategy", "Current Target Weight %", "Max Sharpe (MSR) %", "Min Variance (GMV) %"]
    report.append("| " + " | ".join(headers) + " |")
    report.append("| :--- | :---: | :---: | :---: |")
    for idx, name in enumerate(asset_names):
        tgt_w = tgt_weights[idx]
        msr_w = msr_weights[idx]
        gmv_w = gmv_weights[idx]
        report.append(f"| {name.replace('_', ' ')} | {tgt_w*100:.1f}% | {msr_w*100:.1f}% | {gmv_w*100:.1f}% |")

    # 5. Render ASCII Efficient Frontier
    report.append("\n## 5. Efficient Frontier Visual Mapping (ASCII Plot)\n")
    report.append("```text")
    report.append("   Annualized Return")
    report.append("     ^")
    
    x_min = min(frontier_vols + [tgt_vol]) * 0.9
    x_max = max(frontier_vols + [tgt_vol]) * 1.1
    y_min = min(target_returns.tolist() + [tgt_ret]) * 0.9
    y_max = max(target_returns.tolist() + [tgt_ret]) * 1.1
    
    grid = [[" " for _ in range(60)] for _ in range(16)]
    
    def get_coords(x, y):
        x_col = int((x - x_min) / (x_max - x_min) * 58)
        y_row = 15 - int((y - y_min) / (y_max - y_min) * 15)
        x_col = max(0, min(59, x_col))
        y_row = max(0, min(15, y_row))
        return x_col, y_row

    for r, v in zip(target_returns, frontier_vols):
        col, row = get_coords(v, r)
        grid[row][col] = "o"
        
    col, row = get_coords(msr_vol, msr_ret)
    grid[row][col] = "*" 
    
    col, row = get_coords(gmv_vol, gmv_ret)
    grid[row][col] = "#" 
    
    col, row = get_coords(tgt_vol, tgt_ret)
    grid[row][col] = "X" 
    
    for row_idx in range(16):
        val = y_min + (15 - row_idx)/15 * (y_max - y_min)
        row_str = "".join(grid[row_idx])
        report.append(f" {val*100:5.1f}% | {row_str}")
        
    report.append("        +" + "-"*60)
    report.append(f"         {x_min*100:.1f}%" + " " * 45 + f"{x_max*100:.1f}%   Annualized Volatility")
    report.append("```\n")
    report.append("### Legend:")
    report.append("* **`o`** : Efficient Frontier boundary (minimum risk portfolios for any target return)")
    report.append("* **`*`** : **Max Sharpe Ratio (MSR)** Portfolio")
    report.append("* **`#`** : **Global Minimum Variance (GMV)** Portfolio")
    report.append("* **`X`** : **Current Target Allocation (S7)** Portfolio")
    
    report_path = os.path.join(dir_path, "efficient_frontier_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report))
    print(f"Efficient frontier report written successfully to {report_path}")

if __name__ == "__main__":
    main()
