import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import pandas as pd
import backtest_strategy22 as s

def main():
    data = s.load_data()
    results = []
    
    # Grid of probability thresholds
    for thresh in np.arange(0.33, 0.51, 0.02):
        # We temporarily redefine s.run_simulation logic internally or check
        df_out, n_trades, fees = s.run_simulation(data, thresh=thresh)
        
        initial_nav = df_out["nav"].iloc[0]
        final_nav = df_out["nav"].iloc[-1]
        total_ret = final_nav / initial_nav - 1.0
        
        days = (df_out.index[-1] - df_out.index[0]).days
        years = days / 365.25
        cagr = (final_nav / initial_nav) ** (1.0 / years) - 1.0
        
        daily_rets = df_out["nav"].pct_change().dropna()
        ann_vol = daily_rets.std() * np.sqrt(252)
        sharpe = (cagr - 0.095) / ann_vol if ann_vol > 0 else np.nan
        
        roll_max = df_out["nav"].cummax()
        max_dd = float(((df_out["nav"] - roll_max) / roll_max).min())
        
        results.append({
            "threshold": thresh,
            "final_nav": final_nav,
            "cagr": cagr,
            "sharpe": sharpe,
            "max_dd": max_dd,
            "n_trades": n_trades,
            "fees": fees
        })
        
    df_res = pd.DataFrame(results)
    print(df_res.to_string(index=False))

if __name__ == "__main__":
    main()
