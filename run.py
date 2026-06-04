import os
from pipeline_orchestrator import run_valuation_pipeline

def main():
    # Execution Date
    execution_date = "2026-06-03"
    
    # Run the DAG pipeline
    report = run_valuation_pipeline(execution_date)
    
    # Save the output report
    output_filename = "mexican_value_equity_report.md"
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), output_filename)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)
        
    print(f"\n[Export] Saved final markdown report to: {output_path}")
    print("\n--- REPORT OUTPUT ---")
    print(report)

if __name__ == "__main__":
    main()
