import os
import sys
import time
import datetime
import subprocess
import logging
import argparse

# Set up directory paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "scheduler_logs")
os.makedirs(LOG_DIR, exist_ok=True)

# Configure logging
log_format = "%(asctime)s [%(levelname)s] %(message)s"
logging.basicConfig(
    level=logging.INFO,
    format=log_format,
    handlers=[
        logging.FileHandler(os.path.join(BASE_DIR, "scheduler.log"), encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

# List of scripts to run in sequence
STRATEGY_SCRIPTS = [
    "monitor_portfolio.py",
    "run_live_alpha_growth.py",
    "ingest_live_macd.py",
    "run_live_alpaca_us_stocks.py",
    "run_live_alpaca_us_stocks_dcf.py",
    "run_live_alternatives.py",
    "run_live_high_beta.py",
    "run_live_dividends.py",
    "run_live_strategy9.py",
    "run_live_strategy10.py",
    "run_live_strategy11.py",
    "run_live_strategy12.py",
    "run_live_strategy13.py",
    "run_live_strategy14.py",
    "run_live_strategy15.py",
    "run_live_multi_strategy.py",
    "compare_strategies.py",
    "watchdog.py"
]

def run_script(script_name):
    script_path = os.path.join(BASE_DIR, script_name)
    if not os.path.exists(script_path):
        logging.error(f"Script not found: {script_path}")
        return False
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file_name = f"{os.path.splitext(script_name)[0]}_{timestamp}.log"
    log_file_path = os.path.join(LOG_DIR, log_file_name)
    
    logging.info(f"Running {script_name}...")
    try:
        # Run script and redirect stdout/stderr to a timestamped log file
        with open(log_file_path, "w", encoding="utf-8") as log_file:
            result = subprocess.run(
                [sys.executable, script_path],
                stdout=log_file,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=BASE_DIR,
                timeout=600 # 10 minutes timeout per script
            )
        
        if result.returncode == 0:
            logging.info(f"Successfully completed {script_name}. Log saved to: scheduler_logs/{log_file_name}")
            return True
        else:
            logging.error(f"Error executing {script_name} (Exit code: {result.returncode}). Log saved to: scheduler_logs/{log_file_name}")
            return False
            
    except subprocess.TimeoutExpired:
        logging.error(f"Timeout expired while executing {script_name} after 10 minutes.")
        return False
    except Exception as e:
        logging.error(f"Unexpected error running {script_name}: {e}")
        return False

def run_all_strategies():
    logging.info("=" * 60)
    logging.info("STARTING SCHEDULED PORTFOLIO UPDATE SEQUENCE")
    logging.info("=" * 60)
    
    success_count = 0
    for script in STRATEGY_SCRIPTS:
        success = run_script(script)
        if success:
            success_count += 1
            
    logging.info("=" * 60)
    logging.info(f"SEQUENCE COMPLETED: {success_count}/{len(STRATEGY_SCRIPTS)} scripts completed successfully.")
    logging.info("=" * 60)

def is_market_hours(now):
    # Weekday check (Monday=0, Sunday=6)
    if now.weekday() > 4:
        return False
        
    # Time check (8:30 AM to 3:00 PM Central Time)
    start_time = datetime.time(8, 30)
    end_time = datetime.time(15, 0)
    current_time = now.time()
    
    return start_time <= current_time <= end_time

def main():
    parser = argparse.ArgumentParser(description="Trading Agents 30-Minute Live Scheduler")
    parser.add_argument("--test", action="store_true", help="Run the entire pipeline once immediately for testing, then exit.")
    args = parser.parse_args()

    logging.info("Trading Agents Scheduler Initialized.")
    logging.info("Target Hours: Mon-Fri 8:30 AM - 3:00 PM (Local Time)")
    logging.info(f"Scripts in pipeline: {', '.join(STRATEGY_SCRIPTS)}")
    
    if args.test:
        logging.info("--- RUNNING IN TEST MODE (IMMEDIATE EXECUTION) ---")
        run_all_strategies()
        logging.info("Test run complete. Exiting scheduler.")
        sys.exit(0)
        
    last_run_interval = None
    last_heartbeat = None
    
    while True:
        try:
            now = datetime.datetime.now()
            current_interval = (now.year, now.month, now.day, now.hour, now.minute // 30)
            
            # Print heartbeat to console/log every 30 minutes to show active status
            if last_heartbeat is None or (now - last_heartbeat).total_seconds() >= 1800:
                logging.info(f"Heartbeat: Scheduler is active. Current local time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
                last_heartbeat = now
                
            if is_market_hours(now):
                if current_interval != last_run_interval:
                    logging.info(f"Detected new 30-minute interval window: {now.hour:02d}:{now.minute // 30 * 30:02d}")
                    run_all_strategies()
                    last_run_interval = current_interval
            else:
                # If we transition outside market hours, reset the last run interval to allow running
                # immediately on the next market open interval.
                if last_run_interval is not None:
                    logging.info("Market is closed. Standing by for next market session.")
                    last_run_interval = None
                    
            # Check every 10 seconds
            time.sleep(10)
            
        except KeyboardInterrupt:
            logging.info("Scheduler stopped by user.")
            break
        except Exception as e:
            logging.error(f"Error in scheduler loop: {e}")
            time.sleep(30)  # Sleep longer on error to avoid hot loops

if __name__ == "__main__":
    main()
