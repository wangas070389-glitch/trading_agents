import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import pandas as pd
import backtest_strategy22 as s

def main():
    data = s.load_data()
    n_days = len(data)
    
    # 1. Feature Engineering
    r_qqq = data["qqq"].pct_change().fillna(0.0)
    r_fx = data["fx"].pct_change().fillna(0.0)
    
    r_tqqq_real = data["tqqq"].pct_change().fillna(0.0)
    r_sqqq_real = data["sqqq"].pct_change().fillna(0.0)
    
    tqqq_drag = (2.0 * 0.045 + 0.0095) / 252
    sqqq_drag = (2.0 * 0.055 + 0.0095) / 252
    
    r_tqqq = np.where(data["tqqq"].notna() & (r_tqqq_real != 0.0), r_tqqq_real, 3.0 * r_qqq - tqqq_drag)
    r_sqqq = np.where(data["sqqq"].notna() & (r_sqqq_real != 0.0), r_sqqq_real, -3.0 * r_qqq - sqqq_drag)
    
    r_qqq_mxn = ((1.0 + r_qqq) * (1.0 + r_fx) - 1.0).values
    r_tqqq_mxn = ((1.0 + r_tqqq) * (1.0 + r_fx) - 1.0).values
    r_sqqq_mxn = ((1.0 + r_sqqq) * (1.0 + r_fx) - 1.0).values
    
    daily_cash_sweep = s.BONDIA_YIELD / 252
    
    print("Running feature engineering...")
    features = pd.DataFrame(index=data.index)
    features["ret_1d"] = r_qqq
    features["ret_5d"] = data["qqq"].pct_change(5).fillna(0.0)
    features["ret_10d"] = data["qqq"].pct_change(10).fillna(0.0)
    features["ret_20d"] = data["qqq"].pct_change(20).fillna(0.0)
    features["ret_60d"] = data["qqq"].pct_change(60).fillna(0.0)
    features["vol_5d"] = r_qqq.rolling(5).std().fillna(0.0)
    features["vol_20d"] = r_qqq.rolling(20).std().fillna(0.0)
    sma_50 = data["qqq"].rolling(50).mean()
    sma_120 = data["qqq"].rolling(120).mean()
    features["dist_sma50"] = (data["qqq"] / sma_50 - 1.0).fillna(0.0)
    features["dist_sma120"] = (data["qqq"] / sma_120 - 1.0).fillna(0.0)
    
    log_closes = np.log(data["qqq"].values)
    features["hurst"] = s.calculate_hurst_exponent_rolling(log_closes)
    features["entropy"] = s.calculate_shannon_entropy_rolling(r_qqq.values)
    
    forward_returns = (data["qqq"].shift(-5) / data["qqq"] - 1.0).fillna(0.0)
    labels = np.full(n_days, 1)
    labels[forward_returns > 0.015] = 2
    labels[forward_returns < -0.015] = 0
    
    X = features.values
    y = labels
    
    print("Generating out-of-sample prediction probabilities (once)...")
    all_probs = []
    # default probabilities to cash
    for t in range(n_days):
        all_probs.append(np.array([0.0, 1.0, 0.0])) # 100% Cash default
        
    clf = None
    train_window = 500
    retrace_days = 5
    for t in range(train_window, n_days):
        if (t - train_window) % retrace_days == 0:
            X_train = X[t - train_window : t - 5]
            y_train = y[t - train_window : t - 5]
            from sklearn.ensemble import RandomForestClassifier
            clf = RandomForestClassifier(n_estimators=50, max_depth=3, min_samples_leaf=10, random_state=42, n_jobs=None)
            clf.fit(X_train, y_train)
        
        if clf is not None:
            feat_today = X[t-1].reshape(1, -1)
            all_probs[t] = clf.predict_proba(feat_today)[0]
            
    print("Evaluating grid search thresholds...")
    results = []
    for thresh in np.arange(0.33, 0.51, 0.02):
        nav = np.zeros(n_days)
        nav[0] = 200000.0
        positions = np.zeros(n_days, dtype=int)
        current_asset = 0
        n_trades = 0
        total_fees_paid = 0.0
        
        for t in range(1, n_days):
            probs = all_probs[t]
            pred = np.argmax(probs)
            asset_map = {0: 3, 1: 0, 2: 2}
            proposed_asset = asset_map[pred]
            
            if probs[pred] > thresh:
                target_asset = proposed_asset
            else:
                target_asset = current_asset
                
            positions[t] = target_asset
            
            if target_asset == 0:
                ret = daily_cash_sweep
            elif target_asset == 2:
                ret = r_tqqq_mxn[t]
            elif target_asset == 3:
                ret = r_sqqq_mxn[t]
                
            fee = 0.0
            if target_asset != current_asset:
                n_trades += 1
                fee = nav[t-1] * s.TRANSACTION_COST
                total_fees_paid += fee
                
            nav[t] = nav[t-1] * (1.0 + ret) - fee
            current_asset = target_asset
            
        final_nav = nav[-1]
        years = n_days / 252.0
        cagr = (final_nav / 200000.0) ** (1.0 / (years)) - 1.0
        results.append({
            "threshold": thresh,
            "final_nav": final_nav,
            "cagr": cagr,
            "n_trades": n_trades,
            "fees": total_fees_paid
        })
        
    df_res = pd.DataFrame(results)
    print("\n" + df_res.to_string(index=False))

if __name__ == "__main__":
    main()
