"""Known-invalid historical evidence: repair code, then independently revalidate.

Removing a block requires regenerated artifacts with matching code/data/parameter
provenance and a reviewed validation result. Merely repairing code is insufficient.
This module changes reporting/graduation, not scheduling or brokerage positions.
"""
import re


BACKTEST_BLOCKS = {
    1: "Fee-excluding TWR repaired; archived metrics require regeneration.",
    2: "Fee-excluding TWR repaired; multiple strategy versions require reconciliation.",
    3: "Saved curve and reported metrics differ; fixed-universe selection needs validation.",
    4: "Static present-day fundamentals used historically; KPI source mismatched.",
    5: "Headline KPIs disagree with the strategy backtest report.",
    6: "Static fundamentals and contribution-contaminated performance statistics.",
    7: "Historical hybrid is not the current reporting-only composite.",
    8: "Deposit/dividend accounting repaired; point-in-time fundamentals still missing.",
    9: "Full-sample HMM training, external-flow and calendar errors.",
    10: "Short tuned sample; earlier-window results do not establish robust performance.",
    11: "Short tuned sample and unstable earlier-window validation.",
    16: "Short tuned sample and severe earlier-window instability.",
    17: "Present-day debt screens lack historical point-in-time evidence.",
    18: "Composite inherits unverified underlying strategy histories.",
    23: "Headline KPIs disagree with saved results; selection-adjusted validation required.",
    24: "Holdout-selection leakage repaired; new independent validation required.",
    25: "Native-currency and trailing-stop simulation repaired; old results invalidated.",
    27: "Headline KPIs disagree with saved results.",
    29: "Headline KPIs contradicted by saved NAV; HMM leakage and live/backtest mismatch.",
    30: "Trailing-stop simulation repaired; old results invalidated.",
    31: "Headline KPIs disagree with the strategy backtest report.",
}


def backtest_block(label):
    match = re.match(r"S(\d+)\b", label)
    return BACKTEST_BLOCKS.get(int(match.group(1))) if match else None
