from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from math import inf
from pathlib import Path
from statistics import median

from ai_investing_lab.strategies.ai58_usdjpy import AI58Config
from ai_investing_lab.strategies.ai58_usdjpy.csv_runner import load_candles_csv
from ai_investing_lab.strategies.ai58_usdjpy.source_fidelity import SourceFaithfulAI58Backtester

WARMUP_START = datetime(2011, 3, 18, tzinfo=timezone.utc)
ANALYSIS_START = datetime(2011, 4, 1, tzinfo=timezone.utc)
REFERENCE_END = datetime(2026, 3, 15, tzinfo=timezone.utc)
ANALYSIS_END = datetime(2026, 9, 14, tzinfo=timezone.utc)
INITIAL_CAPITAL = 10_000.0


def add_months(dt: datetime, months: int) -> datetime:
    idx = dt.year * 12 + dt.month - 1 + months
    year, month0 = divmod(idx, 12)
    # All rolling endpoints use day 14, which exists in every month.
    return datetime(year, month0 + 1, dt.day, tzinfo=timezone.utc)


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    values = sorted(values)
    if len(values) == 1:
        return values[0]
    pos = (len(values) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(values) - 1)
    frac = pos - lo
    return values[lo] * (1 - frac) + values[hi] * frac


def percentile_rank(values: list[float], target: float) -> float | None:
    if not values:
        return None
    return 100.0 * sum(v <= target for v in values) / len(values)


def trade_metrics(trades, initial_capital: float = INITIAL_CAPITAL) -> dict[str, float | int]:
    closed = [t for t in trades if t.closed]
    wins = [t for t in closed if t.net_pnl_usd > 0]
    losses = [t for t in closed if t.net_pnl_usd <= 0]
    gp = sum(t.net_pnl_usd for t in wins)
    gl = abs(sum(t.net_pnl_usd for t in losses))
    net = sum(t.net_pnl_usd for t in closed)
    return {
        "trades": len(closed),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_pct": 100.0 * len(wins) / len(closed) if closed else 0.0,
        "net_profit_usd": net,
        "net_profit_pct": 100.0 * net / initial_capital,
        "profit_factor": gp / gl if gl else (inf if gp else 0.0),
    }


def trades_in_window(trades, start: datetime, end: datetime):
    return [t for t in trades if t.closed and start <= t.entry_time < end]


def window_metrics(trades, start: datetime, end: datetime) -> dict[str, object]:
    out = trade_metrics(trades_in_window(trades, start, end))
    out["start"] = start.isoformat()
    out["end_exclusive"] = end.isoformat()
    return out


def losing_streaks(trades):
    closed = sorted((t for t in trades if t.closed), key=lambda t: t.exit_time or t.entry_time)
    streaks = []
    current = []
    for t in closed:
        if t.net_pnl_usd <= 0:
            current.append(t)
        else:
            if current:
                streaks.append(current)
                current = []
    if current:
        streaks.append(current)
    return streaks


def streak_record(streak) -> dict[str, object]:
    return {
        "length": len(streak),
        "start": streak[0].entry_time.isoformat(),
        "end": (streak[-1].exit_time or streak[-1].entry_time).isoformat(),
        "net_pnl_usd": sum(t.net_pnl_usd for t in streak),
    }


def drawdown_episodes(trades, initial_capital: float = INITIAL_CAPITAL):
    closed = sorted((t for t in trades if t.closed), key=lambda t: t.exit_time or t.entry_time)
    equity = initial_capital
    peak_equity = equity
    peak_time = ANALYSIS_START
    active = None
    episodes = []

    for t in closed:
        when = t.exit_time or t.entry_time
        equity += t.net_pnl_usd

        if equity >= peak_equity:
            if active is not None:
                active["recovery_time"] = when
                active["recovered"] = True
                active["duration_days"] = (when - active["peak_time"]).total_seconds() / 86400.0
                active["recovery_from_trough_days"] = (when - active["trough_time"]).total_seconds() / 86400.0
                episodes.append(active)
                active = None
            peak_equity = equity
            peak_time = when
            continue

        dd = (peak_equity - equity) / peak_equity if peak_equity > 0 else 0.0
        if active is None:
            active = {
                "peak_time": peak_time,
                "peak_equity_usd": peak_equity,
                "trough_time": when,
                "trough_equity_usd": equity,
                "max_drawdown_pct": 100.0 * dd,
                "trades_underwater": 1,
                "recovered": False,
                "recovery_time": None,
                "duration_days": None,
                "recovery_from_trough_days": None,
            }
        else:
            active["trades_underwater"] += 1
            if dd > active["max_drawdown_pct"] / 100.0:
                active["max_drawdown_pct"] = 100.0 * dd
                active["trough_time"] = when
                active["trough_equity_usd"] = equity

    if active is not None:
        last_time = (closed[-1].exit_time or closed[-1].entry_time) if closed else ANALYSIS_END
        active["duration_days"] = (last_time - active["peak_time"]).total_seconds() / 86400.0
        active["recovery_from_trough_days"] = None
        episodes.append(active)

    def serializable(ep):
        out = dict(ep)
        for key in ("peak_time", "trough_time", "recovery_time"):
            if out.get(key) is not None:
                out[key] = out[key].isoformat()
        return out

    return episodes, [serializable(ep) for ep in episodes]


def rolling_windows(trades, months: int):
    rows = []
    end = datetime(2011, 10, 14, tzinfo=timezone.utc)
    while end <= ANALYSIS_END:
        start = add_months(end, -months)
        if start >= ANALYSIS_START:
            rows.append(window_metrics(trades, start, end))
        end = add_months(end, 1)
    return rows


def main():
    parser = argparse.ArgumentParser(description="AI58 drawdown, losing-streak and regime-risk analysis")
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    candles = load_candles_csv(args.csv_path)
    selected = [c for c in candles if WARMUP_START <= c.time < ANALYSIS_END]
    if not selected:
        raise RuntimeError("no candles in analysis range")

    cfg = AI58Config.optimized_15m()
    result = SourceFaithfulAI58Backtester(cfg).run(selected)
    trades = [t for t in result.trades if t.closed and t.entry_time >= ANALYSIS_START]

    reference_trades = [t for t in trades if t.entry_time < REFERENCE_END]
    current_trades = [t for t in trades if REFERENCE_END <= t.entry_time < ANALYSIS_END]

    all_streaks = losing_streaks(trades)
    ref_streaks = [s for s in losing_streaks(reference_trades) if (s[-1].exit_time or s[-1].entry_time) < REFERENCE_END]
    current_end_streak = all_streaks[-1] if all_streaks and all_streaks[-1][-1] == trades[-1] else []

    dd_internal, dd_serial = drawdown_episodes(trades)
    ref_dd = [ep for ep in dd_internal if ep["recovered"] and ep["recovery_time"] < REFERENCE_END]
    current_dd = dd_internal[-1] if dd_internal and not dd_internal[-1]["recovered"] else None

    ref_dd_depths = [float(ep["max_drawdown_pct"]) for ep in ref_dd]
    ref_dd_durations = [float(ep["duration_days"]) for ep in ref_dd if ep["duration_days"] is not None]
    ref_streak_lengths = [len(s) for s in ref_streaks]

    rolling_6m = rolling_windows(trades, 6)
    rolling_12m = rolling_windows(trades, 12)
    rolling_24m = rolling_windows(trades, 24)

    ref6 = [w for w in rolling_6m if datetime.fromisoformat(w["end_exclusive"]) <= REFERENCE_END]
    ref12 = [w for w in rolling_12m if datetime.fromisoformat(w["end_exclusive"]) <= REFERENCE_END]
    ref24 = [w for w in rolling_24m if datetime.fromisoformat(w["end_exclusive"]) <= REFERENCE_END]

    latest_6m = window_metrics(trades, add_months(ANALYSIS_END, -6), ANALYSIS_END)
    latest_12m = window_metrics(trades, add_months(ANALYSIS_END, -12), ANALYSIS_END)
    latest_24m = window_metrics(trades, add_months(ANALYSIS_END, -24), ANALYSIS_END)

    p95_dd_depth = percentile(ref_dd_depths, 0.95)
    p95_dd_duration = percentile(ref_dd_durations, 0.95)
    p95_loss_streak = percentile([float(x) for x in ref_streak_lengths], 0.95)

    current_dd_depth = float(current_dd["max_drawdown_pct"]) if current_dd else 0.0
    current_dd_duration = float(current_dd["duration_days"]) if current_dd and current_dd["duration_days"] is not None else 0.0
    current_streak_len = len(current_end_streak)

    # Thresholds are set exclusively from history available before the fresh
    # post-video period. They are diagnostics, not trading instructions.
    latest6_weak = latest_6m["net_profit_pct"] <= 0 or latest_6m["profit_factor"] <= 1.0
    latest12_weak = latest_12m["net_profit_pct"] <= 0 or latest_12m["profit_factor"] <= 1.0
    latest24_weak = latest_24m["net_profit_pct"] <= 0 or latest_24m["profit_factor"] <= 1.0
    dd_extreme = p95_dd_depth is not None and current_dd_depth > p95_dd_depth
    duration_extreme = p95_dd_duration is not None and current_dd_duration > p95_dd_duration
    streak_extreme = p95_loss_streak is not None and current_streak_len > p95_loss_streak

    if latest24_weak and dd_extreme and duration_extreme:
        regime = "structural_concern"
    elif latest12_weak or dd_extreme or duration_extreme or streak_extreme:
        regime = "high_risk_dormant"
    elif latest6_weak:
        regime = "weak_but_within_historical_tolerance"
    else:
        regime = "historically_normal"

    def window_distribution(rows):
        returns = [float(w["net_profit_pct"]) for w in rows]
        pfs = [float(w["profit_factor"]) for w in rows if w["trades"] > 0 and w["profit_factor"] != inf]
        return {
            "windows": len(rows),
            "profitable_pct": 100.0 * sum(x > 0 for x in returns) / len(returns) if returns else None,
            "median_return_pct": median(returns) if returns else None,
            "return_p10_pct": percentile(returns, 0.10),
            "return_p90_pct": percentile(returns, 0.90),
            "pf_median": median(pfs) if pfs else None,
            "pf_p10": percentile(pfs, 0.10),
        }

    payload = {
        "method": "Frozen AI58 creator-video parameters; regime thresholds derived only from history ending 2026-03-15.",
        "data": {
            "source_file": str(args.csv_path),
            "provider": "Dukascopy midpoint proxy",
            "analysis_start": ANALYSIS_START.isoformat(),
            "reference_history_end": REFERENCE_END.isoformat(),
            "analysis_end_exclusive": ANALYSIS_END.isoformat(),
            "bars": len(selected),
            "trades": len(trades),
        },
        "frozen_config": asdict(cfg),
        "current_regime": {
            "classification": regime,
            "latest_6m": latest_6m,
            "latest_12m": latest_12m,
            "latest_24m": latest_24m,
            "current_unrecovered_drawdown": None if current_dd is None else {
                **{k: v for k, v in current_dd.items() if k not in {"peak_time", "trough_time", "recovery_time"}},
                "peak_time": current_dd["peak_time"].isoformat(),
                "trough_time": current_dd["trough_time"].isoformat(),
                "recovery_time": None,
            },
            "current_ending_losing_streak": streak_record(current_end_streak) if current_end_streak else None,
            "signals": {
                "latest_6m_weak": latest6_weak,
                "latest_12m_weak": latest12_weak,
                "latest_24m_weak": latest24_weak,
                "drawdown_depth_above_reference_p95": dd_extreme,
                "drawdown_duration_above_reference_p95": duration_extreme,
                "ending_losing_streak_above_reference_p95": streak_extreme,
            },
        },
        "reference_thresholds": {
            "completed_drawdown_episodes": len(ref_dd),
            "drawdown_depth_p50_pct": percentile(ref_dd_depths, 0.50),
            "drawdown_depth_p90_pct": percentile(ref_dd_depths, 0.90),
            "drawdown_depth_p95_pct": p95_dd_depth,
            "drawdown_duration_p50_days": percentile(ref_dd_durations, 0.50),
            "drawdown_duration_p90_days": percentile(ref_dd_durations, 0.90),
            "drawdown_duration_p95_days": p95_dd_duration,
            "max_completed_drawdown_duration_days": max(ref_dd_durations) if ref_dd_durations else None,
            "max_completed_drawdown_depth_pct": max(ref_dd_depths) if ref_dd_depths else None,
            "losing_streaks": len(ref_streaks),
            "losing_streak_length_p50": percentile([float(x) for x in ref_streak_lengths], 0.50),
            "losing_streak_length_p90": percentile([float(x) for x in ref_streak_lengths], 0.90),
            "losing_streak_length_p95": p95_loss_streak,
            "max_losing_streak": max(ref_streak_lengths) if ref_streak_lengths else 0,
        },
        "current_percentiles_vs_reference": {
            "current_drawdown_depth_percentile": percentile_rank(ref_dd_depths, current_dd_depth),
            "current_drawdown_duration_percentile": percentile_rank(ref_dd_durations, current_dd_duration),
            "current_ending_losing_streak_percentile": percentile_rank([float(x) for x in ref_streak_lengths], float(current_streak_len)),
            "latest_6m_return_percentile": percentile_rank([float(w["net_profit_pct"]) for w in ref6], float(latest_6m["net_profit_pct"])),
            "latest_12m_return_percentile": percentile_rank([float(w["net_profit_pct"]) for w in ref12], float(latest_12m["net_profit_pct"])),
            "latest_24m_return_percentile": percentile_rank([float(w["net_profit_pct"]) for w in ref24], float(latest_24m["net_profit_pct"])),
        },
        "rolling_window_reference": {
            "six_month": window_distribution(ref6),
            "twelve_month": window_distribution(ref12),
            "twenty_four_month": window_distribution(ref24),
        },
        "all_drawdown_episodes": dd_serial,
        "reference_losing_streaks": [streak_record(s) for s in ref_streaks],
        "fresh_post_video_metrics": trade_metrics(current_trades),
        "interpretation_rules": {
            "historically_normal": "Latest six-month return and PF are positive/above 1 and no historical-risk threshold is breached.",
            "weak_but_within_historical_tolerance": "Latest six months are weak, but 12/24-month behavior and drawdown/streak risk remain inside reference-history limits.",
            "high_risk_dormant": "12-month performance is weak or a drawdown/streak exceeds the pre-fresh-period 95th-percentile threshold.",
            "structural_concern": "24-month performance is weak while both drawdown depth and duration exceed their pre-fresh-period 95th-percentile thresholds.",
        },
        "notes": [
            "This is a research regime classifier, not a live-trading rule or recommendation.",
            "Drawdown duration/depth use closed-trade equity because the current research engine does not retain full bar-level mark-to-market equity.",
            "The reference thresholds end on 2026-03-15, before the fresh post-video period being classified.",
            "No strategy parameter is changed based on the 2026 result.",
        ],
    }

    def json_default(obj):
        if hasattr(obj, "isoformat"):
            return obj.isoformat()
        if hasattr(obj, "value"):
            return obj.value
        raise TypeError(type(obj).__name__)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, allow_nan=True, default=json_default), encoding="utf-8")
    print(json.dumps({
        "classification": regime,
        "current_regime": payload["current_regime"],
        "reference_thresholds": payload["reference_thresholds"],
        "current_percentiles_vs_reference": payload["current_percentiles_vs_reference"],
        "rolling_window_reference": payload["rolling_window_reference"],
    }, indent=2, allow_nan=True, default=json_default))


if __name__ == "__main__":
    main()
