"""S34 causal research primitives. No network, broker, or filesystem mutation.

Inputs are provider-neutral, reviewed point-in-time records. Adjusted price-index
units are synthetic total-return units, not executable broker share lots.
"""
from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass
import math

import numpy as np
import pandas as pd

PARAMS = dict(momentum_sessions=126, skip_sessions=5, risk_sessions=20,
              revision_sessions=21, event_max_days=45, estimate_max_days=45,
              eps_floor=.25, min_surprise=.05, min_price=5., min_adv=5_000_000.,
              max_names=20, name_weight=.05, sector_cap=.25, vol_target=.20,
              max_participation=.01)
MODELS = ("combined", "earnings_only", "momentum_only", "momentum_covered", "qqq_vol")
TABLES = ("sessions", "securities", "prices", "universes", "actuals", "estimates")


class DataError(ValueError):
    """Do not calculate performance from an incomplete or ambiguous history."""


def timestamp(value):
    try:
        result = pd.Timestamp(value)
    except (ValueError, TypeError) as exc:
        raise DataError("Invalid timestamp") from exc
    if pd.isna(result) or result.tzinfo is None:
        raise DataError("Explicit UTC-offset timestamps are required, not dates alone")
    return result.tz_convert("UTC")


def finite(value, label, minimum=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise DataError(f"Finite numeric {label} required")
    if minimum is not None and value < minimum:
        raise DataError(f"Invalid {label}")
    return float(value)


def required(row, fields):
    if not isinstance(row, dict) or any(k not in row for k in fields):
        raise DataError(f"Missing record fields: {fields}")


@dataclass
class Dataset:
    """Preindexed immutable-history view; row timestamps are normalized to UTC."""
    bundle: dict

    def __post_init__(self):
        b = self.bundle
        if not isinstance(b, dict) or b.get("schema_version") != 1 or any(not isinstance(b.get(t), list) or not b[t] for t in TABLES):
            raise DataError("Nonempty version-1 tables required")
        self.sessions, self.securities, self.prices = [], {}, {}
        self.actuals, self.estimates, self.histories = defaultdict(list), defaultdict(list), defaultdict(list)
        self.universes = []
        dates = set()
        for row in b["sessions"]:
            required(row, ("date", "close_at", "decision_at"))
            close, decision = timestamp(row["close_at"]), timestamp(row["decision_at"])
            if row["date"] != close.date().isoformat() or decision <= close or row["date"] in dates:
                raise DataError("Unique sessions with decision strictly after close required")
            if self.sessions and close <= self.sessions[-1]["decision_at"]:
                raise DataError("Sessions must be chronological and nonoverlapping")
            self.sessions.append(dict(date=row["date"], close_at=close, decision_at=decision))
            dates.add(row["date"])
        self.date_index = {r["date"]: i for i, r in enumerate(self.sessions)}
        for row in b["securities"]:
            required(row, ("sid", "kind", "currency", "label"))
            if not row["sid"] or row["sid"] in self.securities or row["currency"] != "USD" or row["kind"] not in {"common_stock", "benchmark"}:
                raise DataError("Unique stable USD security IDs and supported security kinds required")
            self.securities[row["sid"]] = dict(row)
        if "QQQ" not in self.securities or self.securities["QQQ"]["kind"] != "benchmark":
            raise DataError("QQQ benchmark series required")
        terminals = {}
        for source in b["prices"]:
            required(source, ("sid", "date", "available_at", "tr_index", "raw_close", "dollar_volume", "tradable", "terminal"))
            r = dict(source)
            if r["sid"] not in self.securities or r["date"] not in dates or (r["date"], r["sid"]) in self.prices:
                raise DataError("Unknown or duplicate security/session price")
            r["available_at"] = timestamp(r["available_at"])
            session = self.sessions[self.date_index[r["date"]]]
            if r["available_at"] < session["close_at"]:
                raise DataError("A closing price cannot be available before its close")
            for field in ("tr_index", "raw_close", "dollar_volume"):
                finite(r[field], field, 0)
            if type(r["tradable"]) is not bool or type(r["terminal"]) is not bool:
                raise DataError("Explicit tradability and terminal flags required")
            if r["terminal"]:
                if r["tradable"] or r["sid"] in terminals:
                    raise DataError("One nontradable terminal settlement per security required")
                terminals[r["sid"]] = r["date"]
            elif r["tr_index"] <= 0 or r["raw_close"] <= 0:
                raise DataError("Nonterminal prices must be positive")
            self.prices[(r["date"], r["sid"])] = r
            self.histories[r["sid"]].append(r)
        for sid, history in self.histories.items():
            history.sort(key=lambda r: r["date"])
            if sid in terminals and history[-1]["date"] != terminals[sid]:
                raise DataError("Price history continues after terminal settlement")
        self.terminals = terminals
        for session in self.sessions:
            quote = self.prices.get((session["date"], "QQQ"))
            if quote is None or quote["terminal"] or quote["available_at"] > session["decision_at"]:
                raise DataError("Complete, timely QQQ benchmark history required")
        seen_universes = set()
        for source in b["universes"]:
            required(source, ("asof_at", "available_at", "members", "source_ref"))
            r = dict(source, asof_at=timestamp(source["asof_at"]), available_at=timestamp(source["available_at"]))
            if r["asof_at"] > r["available_at"] or not r["source_ref"] or not isinstance(r["members"], list):
                raise DataError("Invalid point-in-time universe record")
            key = (r["asof_at"], r["available_at"])
            if key in seen_universes:
                raise DataError("Ambiguous duplicate universe vintage")
            seen_universes.add(key)
            ids = set()
            for member in r["members"]:
                required(member, ("sid", "sector"))
                if member["sid"] in ids or self.securities.get(member["sid"], {}).get("kind") != "common_stock" or not member["sector"]:
                    raise DataError("Unique common-stock members with historical sectors required")
                ids.add(member["sid"])
            self.universes.append(r)
        self.universes.sort(key=lambda r: (r["asof_at"], r["available_at"]))
        event_versions, initial_periods = set(), set()
        for source in b["actuals"]:
            required(source, ("sid", "event_id", "period_end", "announced_at", "available_at", "eps", "basis_id", "currency", "version", "source_ref"))
            r = dict(source, announced_at=timestamp(source["announced_at"]), available_at=timestamp(source["available_at"]))
            self._fundamental(r)
            if r["announced_at"] > r["available_at"] or pd.Timestamp(r["period_end"]).date() > r["announced_at"].date():
                raise DataError("Actual EPS must follow the fiscal period and announcement")
            if type(r["version"]) is not int or r["version"] < 0 or not r["event_id"]:
                raise DataError("Explicit actual-EPS version required")
            key = (r["sid"], r["event_id"], r["version"])
            if key in event_versions:
                raise DataError("Duplicate actual-EPS version")
            event_versions.add(key)
            if r["version"] == 0:
                period_key = (r["sid"], r["period_end"])
                if period_key in initial_periods:
                    raise DataError("More than one initial earnings event for a fiscal quarter")
                initial_periods.add(period_key)
            self.actuals[r["sid"]].append(r)
        estimate_keys = set()
        for source in b["estimates"]:
            required(source, ("sid", "period_end", "period_type", "asof_at", "available_at", "eps", "basis_id", "currency", "source_ref"))
            r = dict(source, asof_at=timestamp(source["asof_at"]), available_at=timestamp(source["available_at"]))
            self._fundamental(r)
            if r["asof_at"] > r["available_at"] or r["period_type"] not in {"quarter", "annual"}:
                raise DataError("Invalid historical estimate vintage")
            key = tuple(r[k] for k in ("sid", "period_end", "period_type", "asof_at", "available_at", "basis_id"))
            if key in estimate_keys:
                raise DataError("Ambiguous duplicate estimate vintage")
            estimate_keys.add(key)
            self.estimates[r["sid"]].append(r)

    def _fundamental(self, row):
        if self.securities.get(row["sid"], {}).get("kind") != "common_stock" or row["currency"] != "USD" or not row["basis_id"] or not row["source_ref"]:
            raise DataError("Stable stock ID, USD EPS, basis and source required")
        finite(row["eps"], "EPS")
        if pd.isna(pd.to_datetime(row["period_end"], format="%Y-%m-%d", errors="coerce")):
            raise DataError("Exact fiscal period_end date required")

    def universe(self, at):
        eligible = [r for r in self.universes if r["asof_at"] <= at and r["available_at"] <= at]
        if not eligible:
            raise DataError("No historical universe available at decision time")
        row = max(eligible, key=lambda r: (r["asof_at"], r["available_at"]))
        if at - row["asof_at"] > pd.Timedelta(days=35):
            raise DataError("Historical universe snapshot is stale")
        return row["members"]

    def window(self, sid, index, count):
        at = self.sessions[index]["decision_at"]
        dates = [s["date"] for s in self.sessions[index-count+1:index+1]]
        rows = [self.prices.get((d, sid)) for d in dates]
        if len(rows) != count or any(r is None or r["available_at"] > at or r["terminal"] for r in rows):
            return None  # Never backfill absent, terminal or not-yet-known history.
        return rows

    def earnings(self, sid, index):
        p, at = PARAMS, self.sessions[index]["decision_at"]
        actuals = [r for r in self.actuals[sid] if r["version"] == 0 and r["available_at"] <= at
                   and pd.Timedelta(0) <= at-r["announced_at"] <= pd.Timedelta(days=p["event_max_days"])]
        if not actuals:
            return None
        actual = max(actuals, key=lambda r: (r["announced_at"], r["event_id"]))
        estimates = self.estimates[sid]
        # Strictly pre-announcement availability, not merely a backdated as-of date.
        consensus = [r for r in estimates if r["period_type"] == "quarter" and r["period_end"] == actual["period_end"]
                     and r["basis_id"] == actual["basis_id"] and r["available_at"] < actual["announced_at"]
                     and actual["announced_at"]-r["asof_at"] <= pd.Timedelta(days=p["estimate_max_days"])]
        if not consensus or index < p["revision_sessions"]:
            return None
        expected = max(consensus, key=lambda r: (r["asof_at"], r["available_at"]))
        surprise = (actual["eps"]-expected["eps"])/max(abs(expected["eps"]), p["eps_floor"])
        cutoff = self.sessions[index-p["revision_sessions"]]["decision_at"]
        forwards = [r for r in estimates if r["period_type"] == "annual" and r["available_at"] <= at
                    and pd.Timestamp(r["period_end"]).date() > at.date() and at-r["asof_at"] <= pd.Timedelta(days=p["estimate_max_days"])]
        if not forwards:
            return None
        period = min(r["period_end"] for r in forwards)
        current = max((r for r in forwards if r["period_end"] == period), key=lambda r: (r["asof_at"], r["available_at"]))
        previous = [r for r in estimates if r["period_type"] == "annual" and r["period_end"] == period
                    and r["basis_id"] == current["basis_id"] and r["available_at"] <= cutoff
                    and cutoff-r["asof_at"] <= pd.Timedelta(days=p["estimate_max_days"])]
        if not previous:
            return None
        baseline = max(previous, key=lambda r: (r["asof_at"], r["available_at"]))
        revision = (current["eps"]-baseline["eps"])/max(abs(baseline["eps"]), p["eps_floor"])
        return dict(surprise=float(np.clip(surprise, -2, 2)), revision=float(np.clip(revision, -2, 2)),
                    event_id=actual["event_id"], actual_available_at=actual["available_at"].isoformat(),
                    consensus_available_at=expected["available_at"].isoformat(),
                    forward_current_available_at=current["available_at"].isoformat(),
                    forward_baseline_available_at=baseline["available_at"].isoformat())


def select(data, index, mode="combined"):
    if mode not in MODELS:
        raise ValueError("Unknown research model")
    p, rows, returns = PARAMS, [], {}
    if index < max(p["momentum_sessions"], p["risk_sessions"], p["revision_sessions"]):
        return {}, []
    members = [{"sid": "QQQ", "sector": "benchmark"}] if mode == "qqq_vol" else data.universe(data.sessions[index]["decision_at"])
    for member in members:
        sid = member["sid"]
        history = data.window(sid, index, p["momentum_sessions"]+1)
        if history is None or not history[-1]["tradable"]:
            continue
        tri = np.array([r["tr_index"] for r in history])
        daily = tri[-p["risk_sessions"]:] / tri[-p["risk_sessions"]-1:-1] - 1
        adv = float(np.mean([r["dollar_volume"] for r in history[-20:]]))
        momentum = tri[-p["skip_sessions"]-1]/tri[0]-1
        confirmation = tri[-1]/tri[-p["skip_sessions"]-1]-1
        if history[-1]["raw_close"] < p["min_price"] or adv < p["min_adv"]:
            continue
        if mode in {"combined", "momentum_only", "momentum_covered"} and (momentum <= 0 or confirmation <= 0):
            continue
        evidence = data.earnings(sid, index) if mode in {"combined", "earnings_only", "momentum_covered"} else {}
        if evidence is None or (mode in {"combined", "earnings_only"} and
                                (evidence["surprise"] < p["min_surprise"] or evidence["revision"] <= 0)):
            continue
        rows.append(dict(sid=sid, sector=member["sector"], momentum=float(momentum), adv=adv, **evidence))
        returns[sid] = daily
    if not rows:
        return {}, []
    frame = pd.DataFrame(rows).set_index("sid")
    features = ["momentum"] if mode in {"momentum_only", "momentum_covered", "qqq_vol"} else ["surprise", "revision"]
    if mode == "combined":
        features += ["momentum"]
    frame["score"] = frame[features].rank(pct=True, method="average").mean(axis=1)
    # Stable-ID tie break, never current ticker alphabet or future performance.
    ordered = sorted(frame.index, key=lambda sid: (-frame.loc[sid, "score"], sid))
    weights, sectors, audit = {}, defaultdict(float), []
    for sid in ordered:
        if len(weights) >= p["max_names"]:
            break
        row = frame.loc[sid]
        weight = 1. if mode == "qqq_vol" else p["name_weight"]
        if mode != "qqq_vol" and sectors[row.sector]+weight > p["sector_cap"]+1e-10:
            continue
        weights[sid] = weight
        sectors[row.sector] += weight
        audit.append(dict(sid=sid, decision_at=data.sessions[index]["decision_at"].isoformat(), **row.to_dict()))
    if not weights:
        return {}, []
    portfolio_returns = sum(returns[sid]*weight for sid, weight in weights.items())
    vol = float(np.std(portfolio_returns, ddof=1)*np.sqrt(252))
    scale = min(1., p["vol_target"]/vol) if vol > 1e-12 else 1.
    return {sid: float(w*scale) for sid, w in weights.items()}, audit


def funded_allocation(values, weights, nav, cost):
    ids = sorted(set(values) | set(weights))
    if (not 0 <= cost < 1 or not math.isfinite(nav) or nav <= 0 or
            any(not math.isfinite(w) or w < 0 for w in weights.values()) or sum(weights.values()) > 1+1e-10 or
            any(not math.isfinite(v) or v < 0 for v in values.values()) or sum(values.values()) > nav+1e-7):
        raise ValueError("Invalid funded target")
    low, high = 0., nav
    for _ in range(55):
        middle = (low+high)/2
        fees = cost*sum(abs(middle*weights.get(sid, 0)-values.get(sid, 0)) for sid in ids)
        if middle+fees > nav:
            high = middle
        else:
            low = middle
    targets = {sid: low*weights.get(sid, 0.) for sid in ids}
    trades = {sid: targets[sid]-values.get(sid, 0.) for sid in ids}
    fees = cost*sum(abs(v) for v in trades.values())
    return targets, float(nav-fees-sum(targets.values())), trades, fees


def simulate(data, mode="combined", *, cost=.003, lag=1, seed=100000.):
    if mode not in MODELS or lag not in (1, 2) or not 0 <= cost < 1 or not math.isfinite(seed) or seed <= 0:
        raise ValueError("Invalid simulation assumptions")
    cash, units, pending = float(seed), {}, None
    ledger, rows, signals, rejections = [], [], [], []
    warmup = PARAMS["momentum_sessions"]
    if len(data.sessions) <= warmup+lag+1:
        raise DataError("Insufficient signal warmup and evaluation history")
    for i in range(warmup, len(data.sessions)):
        session = data.sessions[i]
        date, at = session["date"], session["decision_at"]
        # Missing marks are fatal; never erase a disappeared/delisted position.
        for sid in list(units):
            price = data.prices.get((date, sid))
            if price is None or price["available_at"] > at:
                raise DataError(f"Missing/not-yet-known held mark for {sid} on {date}")
            if price["terminal"]:
                settlement = units.pop(sid)*price["tr_index"]
                cash += settlement
                ledger.append(dict(date=date, sid=sid, action="TERMINAL", cash_delta=float(settlement), fee=0.))
        values = {sid: qty*data.prices[(date, sid)]["tr_index"] for sid, qty in units.items()}
        nav, fee_total, traded_total = float(cash+sum(values.values())), 0., 0.
        if nav <= 0 or not math.isfinite(nav):
            raise DataError("Portfolio exhausted or invalid; no fabricated recovery")
        if pending is not None and pending["due"] == i:
            target, cash_after, trades, fees = funded_allocation(values, pending["weights"], nav, cost)
            unavailable = []
            for sid, trade in trades.items():
                if abs(trade) <= 1e-8:
                    continue
                price = data.prices.get((date, sid))
                capacity = pending["adv"].get(sid, 0.)*PARAMS["max_participation"]
                if price is None or price["available_at"] > at or not price["tradable"] or price["terminal"] or abs(trade) > capacity:
                    unavailable.append(sid)
            # Conservative batch model: any unfillable leg cancels all legs.
            # In particular, failed/untradable sells never finance fresh buys.
            if unavailable:
                rejections.append(dict(date=date, reason="UNFILLABLE_BATCH", securities=unavailable))
            else:
                for sid, trade in trades.items():
                    if abs(trade) > 1e-8:
                        ledger.append(dict(date=date, decision_at=pending["at"], sid=sid,
                                           action="BUY" if trade > 0 else "SELL",
                                           notional=float(abs(trade)), fee=float(abs(trade)*cost),
                                           cash_delta=float(-trade-abs(trade)*cost)))
                units = {sid: value/data.prices[(date, sid)]["tr_index"] for sid, value in target.items() if value > 1e-8}
                cash, fee_total, traded_total = cash_after, fees, sum(abs(v) for v in trades.values())
            pending = None
        nav = float(cash+sum(qty*data.prices[(date, sid)]["tr_index"] for sid, qty in units.items()))
        if cash < -1e-7 or any(q < 0 for q in units.values()):
            raise AssertionError("Unfunded portfolio")
        rows.append(dict(date=date, nav=nav, cash=cash, fees=fee_total, traded=traded_total,
                         exposure=(nav-cash)/nav, holdings=len(units)))
        previous = data.sessions[i-1]["date"]
        new_week = pd.Timestamp(date).to_period("W-SUN") != pd.Timestamp(previous).to_period("W-SUN")
        if (i == warmup or new_week) and i+lag < len(data.sessions):
            weights, selected = select(data, i, mode)
            adv = {r["sid"]: r["adv"] for r in selected}
            for sid in units:
                history = data.window(sid, i, 20)
                if history:
                    adv[sid] = float(np.mean([r["dollar_volume"] for r in history]))
            pending = dict(due=i+lag, weights=weights, at=at.isoformat(), adv=adv)
            signals.extend(selected)
    frame = pd.DataFrame(rows).set_index("date")
    frame.index = pd.to_datetime(frame.index)
    frame.attrs["seed"] = seed
    return frame, ledger, signals, rejections


def metrics(frame, start=None, end=None):
    part = frame.loc[start:end]
    if len(part) < 2:
        return None
    before = frame.loc[frame.index < part.index[0]]
    initial = float(before.nav.iloc[-1]) if len(before) else frame.attrs["seed"]
    initial_date = before.index[-1] if len(before) else part.index[0]
    values = np.r_[initial, part.nav.to_numpy()]
    returns = values[1:]/values[:-1]-1
    years = (part.index[-1]-initial_date).days/365.25
    volatility = float(returns.std(ddof=1)*np.sqrt(252))
    sharpe = float(returns.mean()*252/volatility) if volatility > 1e-12 else 0.
    return dict(cagr=float((values[-1]/initial)**(1/years)-1), years=years,
                total_return=float(values[-1]/initial-1), sharpe_zero_rf=sharpe,
                evidence_score=sharpe*years, volatility=volatility,
                max_dd=float((values/np.maximum.accumulate(values)-1).min()),
                turnover=float((part.traded/part.nav).sum()/years),
                average_exposure=float(part.exposure.mean()), fees=float(part.fees.sum()))
