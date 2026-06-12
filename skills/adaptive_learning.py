"""
Adaptive learning layer for the V3 pipeline.

Three components, each with a deliberately limited job:

1. SignalPerformanceTracker
   Records every signal the system acts on (DCS, HMM state, vol, weight) and,
   once enough time has passed, the realized forward return. From that history
   it computes an empirical-Bayes confidence multiplier per signal bucket:
   buckets that have historically delivered positive expectancy get sized up
   (capped), buckets that lose money get sized down. With few observations the
   multiplier shrinks to 1.0 (no opinion) — the system only "trusts" what it
   has evidence for.

2. DrawdownGovernor
   Tracks the strategy's own equity curve and scales gross exposure down as
   drawdown deepens. This is the single most reliable "profitability" lever:
   it does not predict returns, it caps how much a bad model can lose while
   the tracker accumulates evidence.

3. Walk-forward threshold optimization (see learn_parameters.py)
   The entry thresholds (DCS >= x, relative volume >= y) were hardcoded
   guesses. They are now learned on a training window and validated on
   held-out data, with a robustness penalty so we pick stable parameters,
   not the luckiest backtest.

Honesty note: none of this guarantees profit. It makes the system update on
evidence and lose less when it is wrong, which is the only defensible meaning
of "learning to be profitable" with this little capital and history.
"""

import os
import json
import math
import datetime

SIGNAL_HISTORY_FILE = "signal_history.json"
EQUITY_CURVE_FILE = "equity_curve.json"
LEARNED_PARAMS_FILE = "learned_params.json"

# Forward horizon (business days) over which a signal is judged.
# Matches the rebalance cadence so each decision is scored against
# what happened until the next decision.
OUTCOME_HORIZON_DAYS = 15


def _load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return default
    return default


def _save_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)


def load_learned_params(dir_path):
    """
    Returns learned thresholds, falling back to the original hardcoded
    values when learn_parameters.py has not been run yet.
    """
    defaults = {
        "dcs_threshold": 0.25,
        "vr_threshold": 1.2,
        "trained_on": None,
        "validation_sharpe": None,
    }
    params = _load_json(os.path.join(dir_path, LEARNED_PARAMS_FILE), defaults)
    # Never accept absurd values from a corrupted file
    if not (0.0 <= params.get("dcs_threshold", 0.25) <= 0.9):
        params["dcs_threshold"] = 0.25
    if not (0.5 <= params.get("vr_threshold", 1.2) <= 3.0):
        params["vr_threshold"] = 1.2
    return params


class SignalPerformanceTracker:
    """
    Persistent log of (signal -> realized forward return) pairs.

    Buckets are pooled across tickers: (hmm_state, dcs_bin). With a 15-day
    horizon a single ticker would need years to accumulate a usable sample;
    pooling across the ~25-name universe gets there ~25x faster, at the cost
    of assuming the signal means roughly the same thing for every name.
    """

    DCS_BIN_WIDTH = 0.25  # bins: [0,0.25), [0.25,0.5), [0.5,0.75), [0.75,1.0]
    MIN_SAMPLES_FULL_TRUST = 30   # shrinkage prior weight
    MULT_FLOOR = 0.4
    MULT_CAP = 1.4

    def __init__(self, dir_path):
        self.path = os.path.join(dir_path, SIGNAL_HISTORY_FILE)
        self.records = _load_json(self.path, [])

    # ------------------------------------------------------------------ #
    @staticmethod
    def _bucket(hmm_state, dcs):
        b = min(int(max(dcs, 0.0) / SignalPerformanceTracker.DCS_BIN_WIDTH), 3)
        return f"state{hmm_state}_dcs{b}"

    def record_signals(self, execution_date, adjusted_metrics, weights):
        """Log today's acted-on signals (weight > 0) as pending outcomes."""
        added = 0
        for ticker, w in weights.items():
            if w <= 0.0 or ticker not in adjusted_metrics:
                continue
            met = adjusted_metrics[ticker]
            self.records.append({
                "date": execution_date,
                "ticker": ticker,
                "dcs": round(met["dcs_adjusted"], 4),
                "hmm_state": met["hmm_state"],
                "weight": round(w, 4),
                "entry_price": met["current_price"],
                "exit_price": None,
                "fwd_return": None,
                "resolved": False,
            })
            added += 1
        _save_json(self.path, self.records)
        return added

    def update_outcomes(self, execution_date, price_lookup):
        """
        Resolve pending signals older than OUTCOME_HORIZON_DAYS business days
        (approximated as horizon * 7/5 calendar days) using today's prices.
        """
        today = datetime.date.fromisoformat(execution_date)
        min_age = datetime.timedelta(days=int(OUTCOME_HORIZON_DAYS * 7 / 5))
        resolved = 0
        for rec in self.records:
            if rec["resolved"]:
                continue
            rec_date = datetime.date.fromisoformat(rec["date"])
            if today - rec_date < min_age:
                continue
            price_now = price_lookup.get(rec["ticker"])
            if price_now is None or rec["entry_price"] <= 0:
                continue  # stays pending until we see the ticker again
            rec["exit_price"] = price_now
            rec["fwd_return"] = price_now / rec["entry_price"] - 1.0
            rec["resolved"] = True
            resolved += 1
        if resolved:
            _save_json(self.path, self.records)
        return resolved

    def bucket_stats(self):
        """Mean forward return and count per signal bucket (resolved only)."""
        stats = {}
        for rec in self.records:
            if not rec["resolved"]:
                continue
            key = self._bucket(rec["hmm_state"], rec["dcs"])
            stats.setdefault(key, []).append(rec["fwd_return"])
        return {
            k: {"n": len(v), "mean_fwd_return": sum(v) / len(v)}
            for k, v in stats.items()
        }

    def confidence_multiplier(self, hmm_state, dcs):
        """
        Empirical-Bayes multiplier on position weight for this signal bucket.

        shrunk_mean = (n * sample_mean + k * 0) / (n + k), prior mean 0
        multiplier  = clip(1 + shrunk_mean / scale, FLOOR, CAP)

        scale = 0.05 means a bucket with a proven +5% mean 15-day return
        (after full sample) gets ~2x conviction before capping; in practice
        the cap binds long before that. With n=0 the multiplier is exactly 1.
        """
        stats = self.bucket_stats().get(self._bucket(hmm_state, dcs))
        if not stats:
            return 1.0
        n = stats["n"]
        k = self.MIN_SAMPLES_FULL_TRUST
        shrunk = (n * stats["mean_fwd_return"]) / (n + k)
        mult = 1.0 + shrunk / 0.05
        return max(self.MULT_FLOOR, min(self.MULT_CAP, mult))


class DrawdownGovernor:
    """
    Scales gross exposure by the strategy's own drawdown.

    exposure = 1.0                     while drawdown < soft_limit (5%)
    linear interpolation to floor      between soft (5%) and hard (15%)
    exposure = floor (0.30)            at/beyond hard limit

    Recovery is symmetric: as the equity curve climbs back, exposure
    re-expands automatically. State lives in equity_curve.json.
    """

    SOFT_DD = 0.05
    HARD_DD = 0.15
    FLOOR = 0.30

    def __init__(self, dir_path):
        self.path = os.path.join(dir_path, EQUITY_CURVE_FILE)
        self.curve = _load_json(self.path, [])

    def record_value(self, execution_date, total_value):
        # One point per date (re-runs on the same day overwrite)
        self.curve = [p for p in self.curve if p["date"] != execution_date]
        self.curve.append({"date": execution_date, "value": round(total_value, 2)})
        self.curve.sort(key=lambda p: p["date"])
        _save_json(self.path, self.curve)

    def current_drawdown(self):
        if not self.curve:
            return 0.0
        # drawdown *now* relative to all-time peak:
        last = self.curve[-1]["value"]
        peak = max(p["value"] for p in self.curve)
        return last / peak - 1.0

    def exposure_scalar(self):
        dd = -self.current_drawdown()  # positive number
        if dd <= self.SOFT_DD:
            return 1.0
        if dd >= self.HARD_DD:
            return self.FLOOR
        frac = (dd - self.SOFT_DD) / (self.HARD_DD - self.SOFT_DD)
        return 1.0 - frac * (1.0 - self.FLOOR)
