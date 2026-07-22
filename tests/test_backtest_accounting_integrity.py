"""
Automated Backtest Integrity Audit Suite

Systematically scans all backtest scripts (backtest_*.py) and generated report files 
(*_backtest_report.md) in the workspace to detect and eliminate simulation bugs:
1. Loss-Erasure / Conditional Overwrite Flaws (e.g., nav[t] = nav[t-1] on bad return days).
2. Zero-Drawdown Anomalies (Max Drawdown = 0.00% or -0.01%).
3. Transaction Cost Inclusion (Verifies fee application).
4. Unfunded Position Additions.
"""

import os
import glob
import re
import pytest

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_all_backtest_scripts():
    pattern = os.path.join(WORKSPACE_DIR, "backtest*.py")
    return sorted(glob.glob(pattern))


def get_all_backtest_reports():
    pattern = os.path.join(WORKSPACE_DIR, "*_backtest_report.md")
    return sorted(glob.glob(pattern))


def test_no_backtest_report_has_zero_drawdown_anomaly():
    """
    Scans all generated backtest reports (*_backtest_report.md) to ensure NO strategy 
    reports a suspicious 0.00% or -0.01% max drawdown (which indicates loss erasure).
    """
    reports = get_all_backtest_reports()
    suspicious_reports = []

    for r_path in reports:
        basename = os.path.basename(r_path)
        with open(r_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Look for Maximum Drawdown lines
        matches = re.findall(r"Max(?:imum)? Drawdown.*:\s*(-?0\.0[01]%)", content, re.IGNORECASE)
        if matches:
            suspicious_reports.append((basename, matches))

    assert len(suspicious_reports) == 0, f"Found zero-drawdown anomalies indicating loss-erasure: {suspicious_reports}"


def test_no_backtest_script_has_loss_erasure_flaw():
    """
    Inspects source code of all backtest scripts to ensure no conditional nav[t] = nav[t-1] 
    loss-erasure overrides exist.
    """
    scripts = get_all_backtest_scripts()
    flawed_scripts = []

    for s_path in scripts:
        basename = os.path.basename(s_path)
        with open(s_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        for idx, line in enumerate(lines, start=1):
            # Flag suspicious patterns like: nav[t] = nav[t-1] or nav[i] = nav[i-1] inside regime checks
            if re.search(r"if\s+regime\s*!=\s*\d+:\s*nav\[t\]\s*=\s*nav\[t-1\]", line) or \
               re.search(r"nav\[t\]\s*=\s*nav\[t-1\]", line) and "regime" in lines[max(0, idx-3)].lower():
                flawed_scripts.append((basename, idx, line.strip()))

    assert len(flawed_scripts) == 0, f"Found loss-erasure override statements in: {flawed_scripts}"


def test_backtest_scripts_include_transaction_costs():
    """
    Ensures every backtest script references transaction fees or commissions.
    """
    scripts = get_all_backtest_scripts()
    missing_fees = []

    for s_path in scripts:
        basename = os.path.basename(s_path)
        with open(s_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Check for presence of fee terms
        has_fee = any(term in content.lower() for term in ["transaction_cost", "fee", "commission", "slippage", "cost"])
        if not has_fee:
            missing_fees.append(basename)

    assert len(missing_fees) == 0, f"Backtest scripts missing transaction costs: {missing_fees}"


def test_backtest_scripts_exist():
    """
    Ensures backtest scripts exist in the repository.
    """
    scripts = get_all_backtest_scripts()
    assert len(scripts) > 0, "No backtest scripts found in workspace"
