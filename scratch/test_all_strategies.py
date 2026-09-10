import subprocess
import sys
import os

scripts = [
    'monitor_portfolio.py',
    'run_live_alpha_growth.py',
    'ingest_live_macd.py',
    'run_live_alpaca_us_stocks.py',
    'run_live_alpaca_us_stocks_dcf.py',
    'run_live_alternatives.py',
    'run_live_high_beta.py',
    'run_live_dividends.py',
    'run_live_strategy9.py',
    'run_live_strategy10.py',
    'run_live_strategy11.py',
    'run_live_strategy12.py',
    'run_live_strategy13.py',
    'run_live_strategy14.py',
    'run_live_strategy15.py',
    'run_live_strategy16.py',
    'run_live_strategy17.py',
    'run_live_strategy19.py',
    'run_live_strategy20.py',
    'run_live_strategy21.py',
    'run_live_strategy22.py',
    'run_live_strategy23.py',
    'run_live_strategy24.py',
    'run_live_strategy25.py',
    'run_live_strategy27.py',
    'run_live_strategy29.py',
    'run_live_strategy30.py',
    'run_live_strategy31.py',
    'run_live_multi_strategy.py',
    'shadow_frontier.py',
    'run_live_strategy18.py',
    'compare_strategies.py',
    'generate_clean_report.py',
    'graduation_report.py',
    'watchdog.py'
]

python_exe = sys.executable

results = {}
failures = {}

print(f"Running full verification test on {len(scripts)} scripts...")
print("=" * 80)

for script in scripts:
    print(f"Testing {script}...", end=" ", flush=True)
    res = subprocess.run([python_exe, script], capture_output=True, text=True)
    if res.returncode == 0:
        print("OK")
        results[script] = "OK"
    else:
        print("FAILED!")
        results[script] = "FAILED"
        failures[script] = res.stderr or res.stdout

print("=" * 80)
print("SUMMARY OF RESULTS:")
for script, status in results.items():
    print(f"  {script:<35}: {status}")

if failures:
    print("\n" + "=" * 80)
    print("FAILURE DETAILS:")
    for script, err in failures.items():
        print(f"\n--- {script} ---")
        print(err[-1000:] if len(err) > 1000 else err)
    sys.exit(1)
else:
    print("\nALL STRATEGY SCRIPTS PASSED SUCCESSFULLY!")
    sys.exit(0)
