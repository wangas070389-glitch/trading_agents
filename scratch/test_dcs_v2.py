import sys
import os
import numpy as np

# Ensure path includes root directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.agents import FundamentalScreener

def generate_regime_data(n_days, transition_matrix, means, vols):
    state = 1  # start in sideways
    states = []
    for _ in range(n_days):
        states.append(state)
        state = np.random.choice([0, 1, 2], p=transition_matrix[state])
    
    rets = np.array([np.random.normal(means[s], vols[s]) for s in states])
    return rets, np.array(states)

def run_tests():
    print("====================================================")
    print("RUNNING DCS V2 PROPERTIES UNIT TESTS (10-ASSET UNIVERSE)")
    print("====================================================")
    
    screener = FundamentalScreener()
    
    np.random.seed(42)
    n_days = 250
    
    # 3-state parameters: 0: Bear, 1: Sideways, 2: Bull
    P = np.array([
        [0.85, 0.10, 0.05],
        [0.10, 0.80, 0.10],
        [0.05, 0.10, 0.85]
    ])
    means = [-0.015, 0.0, 0.015]
    vols = [0.02, 0.01, 0.015]
    
    # Generate exog
    ret_spy, _ = generate_regime_data(n_days, P, [0.0001, 0.0003, 0.0008], [0.01, 0.008, 0.012])
    ret_mxn, _ = generate_regime_data(n_days, P, [0.0002, 0.0, -0.0002], [0.008, 0.007, 0.009])
    exog = np.column_stack([ret_spy, ret_mxn])
    
    # Generate 10 assets: 4 bullish, 4 bearish, 2 sideways
    universe = {}
    for i in range(10):
        ret, _ = generate_regime_data(n_days, P, means, vols)
        if i < 4:
            # Bullish
            ret += 0.008
            name = f"BULL_{i}.MX"
        elif i < 8:
            # Bearish
            ret -= 0.008
            name = f"BEAR_{i}.MX"
        else:
            # Sideways
            name = f"SIDE_{i}.MX"
            
        prices = 100.0 * np.exp(np.cumsum(ret))
        vol = np.random.normal(1e6, 1e5, n_days)
        universe[name] = {
            "prices": prices,
            "volumes": vol,
            "exogenous": exog
        }
        
    results = screener.screen(universe)
    
    # Test 1: Bounded in [-1, 1]
    print("\n--- TEST 1: Bounding ---")
    for ticker, res in results.items():
        dcs = res["dcs"]
        print(f"  {ticker}: DCS = {dcs:.4f}")
        assert -1.0 <= dcs <= 1.0, f"Error: {ticker} DCS {dcs} out of bounds [-1, 1]"
    print("  => PASS: All DCS v2 scores are strictly within [-1, 1].")
    
    # Test 2: No Saturation
    print("\n--- TEST 2: No Saturation ---")
    for ticker, res in results.items():
        dcs = res["dcs"]
        assert abs(dcs) < 1.0, f"Error: {ticker} DCS is fully saturated at {dcs}"
    print("  => PASS: No DCS v2 score saturated at exactly -1.0 or 1.0.")
    
    # Test 3: Standard deviation across the universe is > 0.15
    print("\n--- TEST 3: Universe DCS Variance ---")
    dcs_values = [res["dcs"] for res in results.values()]
    std_dcs = np.std(dcs_values)
    print(f"  Standard deviation of DCS v2 across universe: {std_dcs:.4f}")
    assert std_dcs > 0.15, f"Error: Universe DCS v2 standard deviation is too small ({std_dcs:.4f} <= 0.15)"
    print("  => PASS: Universe DCS standard deviation is greater than 0.15.")
    
    # Test 4: HMM State and DCS Sign alignment
    print("\n--- TEST 4: HMM State and DCS Sign Consensus ---")
    for ticker, res in results.items():
        state = res["hmm_state"]
        dcs = res["dcs"]
        print(f"  {ticker}: State = {state} | DCS = {dcs:.4f}")
        if state == 1:
            assert dcs > -0.1, f"Error: Bull state ({state}) has highly negative DCS ({dcs})"
        elif state == -1:
            assert dcs < 0.1, f"Error: Bear state ({state}) has highly positive DCS ({dcs})"
    print("  => PASS: State labels and DCS scores do not contradict.")
    
    print("\nALL DCS V2 UNIT TESTS PASSED SUCCESSFULLY!")
    print("====================================================")

if __name__ == "__main__":
    run_tests()
