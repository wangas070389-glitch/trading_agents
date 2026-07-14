import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import pandas as pd
import backtest_strategy21 as s

def main():
    data = s.load_data()
    results = []
    
    # Grid of thresholds
    for entry in np.arange(0.80, 0.91, 0.01):
        for exit in np.arange(entry + 0.01, entry + 0.05, 0.01):
            df_out, n_trades, fees = s.run_simulation(data, entry_thresh=entry, exit_thresh=exit)
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
            
            # Position breakdown
            cash_days = (df_out["position"] == 0).sum()
            tqqq_days = (df_out["position"] == 2).sum()
            sqqq_days = (df_out["position"] == 3).sum()
            
            results.append({
                "entry": entry,
                "exit": exit,
                "final_nav": final_nav,
                "cagr": cagr,
                "sharpe": sharpe,
                "max_dd": max_dd,
                "n_trades": n_trades,
                "fees": fees,
                "cash_pct": cash_days / len(df_out) * 100.0
            })
            
    df_res = pd.DataFrame(results)
    df_res = df_res.sort_values(by="final_nav", ascending=False)
    print(df_res.head(15).to_string(index=False))

if __name__ == "__main__":
    main()
