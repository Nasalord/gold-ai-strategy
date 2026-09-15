from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from math import ceil, floor
from pathlib import Path

from ai_investing_lab.strategies.ai38_gbpusd import AI38Backtester, AI38Config, Candle

UTC = timezone.utc
TRADE_START = datetime(2020, 3, 1, tzinfo=UTC)
REFERENCE_START = datetime(2020, 3, 15, tzinfo=UTC)
REFERENCE_END = datetime(2026, 3, 15, tzinfo=UTC)
INITIAL_CAPITAL = 10_000.0
NORMALIZED_FIXED_UNITS = 10_000.0


def parse_date(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=UTC)


def parse_iso(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def load_csv(path: Path) -> list[Candle]:
    out: list[Candle] = []
    with path.open("r", newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            out.append(
                Candle(
                    time=parse_iso(row["timestamp"]),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                )
            )
    return sorted(out, key=lambda c: c.time)


def shift_months(dt: datetime, delta: int) -> datetime:
    total = dt.year * 12 + (dt.month - 1) + delta
    year, month0 = divmod(total, 12)
    return datetime(year, month0 + 1, dt.day, tzinfo=UTC)


def window_metrics(
    candles: list[Candle],
    cfg: AI38Config,
    start: datetime,
    end: datetime,
) -> dict[str, float | int]:
    """Use the exact isolated-window semantics used by AI38 full validation."""
    result = AI38Backtester(cfg).run(candles, trade_start=start, trade_end=end)
    m = result.metrics
    return {
        "trades": m.trades,
        "wins": m.wins,
        "losses": m.losses,
        "win_rate_pct": m.win_rate_pct,
        "net_profit_usd": m.net_profit_usd,
        "net_profit_pct": m.net_profit_pct,
        "profit_factor": m.profit_factor,
        "max_closed_trade_drawdown_pct": m.max_closed_trade_drawdown_pct,
    }


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    vals = sorted(float(v) for v in values)
    if len(vals) == 1:
        return vals[0]
    pos = (len(vals) - 1) * q
    lo = floor(pos)
    hi = ceil(pos)
    if lo == hi:
        return vals[lo]
    weight = pos - lo
    return vals[lo] * (1.0 - weight) + vals[hi] * weight


def percentile_rank(values: list[float], current: float) -> float:
    if not values:
        return 0.0
    return 100.0 * sum(float(v) <= current for v in values) / len(values)


def rolling_reference(
    candles: list[Candle], cfg: AI38Config, months: int
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    end = shift_months(REFERENCE_START, months)
    while end <= REFERENCE_END:
        start = shift_months(end, -months)
        rows.append(
            {
                "start": start.date().isoformat(),
                "end": end.date().isoformat(),
                **window_metrics(candles, cfg, start, end),
            }
        )
        end = shift_months(end, 1)
    return rows


def losing_streaks(trades, end: datetime) -> tuple[list[int], int]:
    closed = [
        t for t in trades if t.closed and t.exit_time is not None and t.exit_time < end
    ]
    closed.sort(key=lambda t: (t.exit_time, t.entry_time))
    streaks: list[int] = []
    current = 0
    for trade in closed:
        if trade.net_pnl_usd <= 0:
            current += 1
        elif current:
            streaks.append(current)
            current = 0
    if current:
        streaks.append(current)
    return streaks, current


def drawdown_episodes(trades, end: datetime) -> tuple[list[dict[str, float]], dict[str, float]]:
    closed = [
        t for t in trades if t.closed and t.exit_time is not None and t.exit_time < end
    ]
    closed.sort(key=lambda t: (t.exit_time, t.entry_time))

    equity = INITIAL_CAPITAL
    peak = equity
    peak_time = TRADE_START
    active = False
    max_depth = 0.0
    episodes: list[dict[str, float]] = []

    for trade in closed:
        equity += trade.net_pnl_usd
        if equity >= peak:
            if active and trade.exit_time is not None:
                episodes.append(
                    {
                        "max_drawdown_pct": max_depth,
                        "duration_days": (trade.exit_time - peak_time).total_seconds() / 86400.0,
                    }
                )
            peak = equity
            peak_time = trade.exit_time or peak_time
            active = False
            max_depth = 0.0
        elif peak > 0:
            active = True
            max_depth = max(max_depth, 100.0 * (peak - equity) / peak)

    current_depth = 100.0 * (peak - equity) / peak if peak > 0 else 0.0
    current = {
        "max_drawdown_pct": current_depth,
        "duration_days": (end - peak_time).total_seconds() / 86400.0 if active else 0.0,
    }
    return episodes, current


def main() -> None:
    parser = argparse.ArgumentParser(description="Run frozen AI38 regime health monitor")
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--analysis-end", type=parse_date, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.analysis_end <= REFERENCE_END:
        raise ValueError("--analysis-end must be after frozen reference cutoff 2026-03-15")

    candles = load_csv(args.csv_path)
    if not candles:
        raise RuntimeError("no GBPUSD candles loaded")

    cfg = AI38Config.creator_4h(fixed_units=NORMALIZED_FIXED_UNITS)

    # Rolling return/PF health must use the exact same boundary semantics as the
    # approved AI38 full-validation study. Each window starts with no open trade.
    ref6 = rolling_reference(candles, cfg, 6)
    ref12 = rolling_reference(candles, cfg, 12)
    ref24 = rolling_reference(candles, cfg, 24)

    latest6 = window_metrics(candles, cfg, shift_months(args.analysis_end, -6), args.analysis_end)
    latest12 = window_metrics(candles, cfg, shift_months(args.analysis_end, -12), args.analysis_end)
    latest24 = window_metrics(candles, cfg, shift_months(args.analysis_end, -24), args.analysis_end)

    # Drawdown duration and ending streak are path-dependent, so they use one
    # continuous frozen-strategy simulation rather than reset rolling windows.
    continuous = AI38Backtester(cfg).run(
        candles,
        trade_start=TRADE_START,
        trade_end=args.analysis_end,
        close_at_end=False,
    )
    trades = continuous.trades

    ref_streaks, _ = losing_streaks(trades, REFERENCE_END)
    _, ending_streak = losing_streaks(trades, args.analysis_end)

    ref_dd_episodes, ref_unrecovered = drawdown_episodes(trades, REFERENCE_END)
    _, current_dd = drawdown_episodes(trades, args.analysis_end)
    ref_depths = [row["max_drawdown_pct"] for row in ref_dd_episodes]
    ref_durations = [row["duration_days"] for row in ref_dd_episodes]
    if ref_unrecovered["duration_days"] > 0:
        ref_depths.append(ref_unrecovered["max_drawdown_pct"])
        ref_durations.append(ref_unrecovered["duration_days"])

    thresholds = {
        "reference_start": REFERENCE_START.isoformat(),
        "reference_end": REFERENCE_END.isoformat(),
        "drawdown_depth_p95_pct": percentile(ref_depths, 0.95),
        "drawdown_duration_p95_days": percentile(ref_durations, 0.95),
        "losing_streak_length_p95": percentile([float(x) for x in ref_streaks], 0.95),
        "max_losing_streak": max(ref_streaks) if ref_streaks else 0,
        "rolling_6m_return_p10_pct": percentile(
            [float(row["net_profit_pct"]) for row in ref6], 0.10
        ),
        "rolling_12m_return_p10_pct": percentile(
            [float(row["net_profit_pct"]) for row in ref12], 0.10
        ),
    }

    pct = {
        "latest_6m_return_percentile": percentile_rank(
            [float(row["net_profit_pct"]) for row in ref6], float(latest6["net_profit_pct"])
        ),
        "latest_12m_return_percentile": percentile_rank(
            [float(row["net_profit_pct"]) for row in ref12], float(latest12["net_profit_pct"])
        ),
        "latest_24m_return_percentile": percentile_rank(
            [float(row["net_profit_pct"]) for row in ref24], float(latest24["net_profit_pct"])
        ),
        "latest_6m_pf_percentile": percentile_rank(
            [float(row["profit_factor"]) for row in ref6], float(latest6["profit_factor"])
        ),
        "latest_12m_pf_percentile": percentile_rank(
            [float(row["profit_factor"]) for row in ref12], float(latest12["profit_factor"])
        ),
        "latest_24m_pf_percentile": percentile_rank(
            [float(row["profit_factor"]) for row in ref24], float(latest24["profit_factor"])
        ),
    }

    signals = {
        "weak_6m": latest6["net_profit_pct"] <= 0 or latest6["profit_factor"] < 1.0,
        "weak_12m": latest12["net_profit_pct"] <= 0 or latest12["profit_factor"] < 1.0,
        "weak_24m": latest24["net_profit_pct"] <= 0 or latest24["profit_factor"] < 1.0,
        "6m_return_below_reference_p10": pct["latest_6m_return_percentile"] <= 10.0,
        "12m_return_below_reference_p10": pct["latest_12m_return_percentile"] <= 10.0,
        "drawdown_depth_over_reference_p95": (
            current_dd["max_drawdown_pct"] >= thresholds["drawdown_depth_p95_pct"]
            and current_dd["max_drawdown_pct"] > 0
        ),
        "drawdown_duration_over_reference_p95": (
            current_dd["duration_days"] >= thresholds["drawdown_duration_p95_days"]
            and current_dd["duration_days"] > 0
        ),
        "losing_streak_over_reference_p95": ending_streak
        >= max(1, ceil(thresholds["losing_streak_length_p95"])),
    }

    risk_breaches = sum(
        bool(signals[key])
        for key in (
            "drawdown_depth_over_reference_p95",
            "drawdown_duration_over_reference_p95",
            "losing_streak_over_reference_p95",
        )
    )

    if (
        risk_breaches >= 2
        or (
            signals["weak_24m"]
            and signals["weak_12m"]
            and (signals["weak_6m"] or risk_breaches >= 1)
        )
    ):
        classification = "structural_concern"
    elif (signals["weak_6m"] and signals["weak_12m"]) or risk_breaches >= 1:
        classification = "high_risk_dormant"
    elif (
        signals["weak_6m"]
        or signals["weak_12m"]
        or signals["6m_return_below_reference_p10"]
        or signals["12m_return_below_reference_p10"]
    ):
        classification = "weak_but_within_historical_tolerance"
    else:
        classification = "historically_normal"

    stale_hours = (args.analysis_end - candles[-1].time).total_seconds() / 3600.0
    payload = {
        "strategy": "AI38 Double EMA + Momentum GBPUSD 4H",
        "method": (
            "Frozen AI38 signal/regime monitor. Rolling return/PF windows use the exact "
            "isolated-window semantics of run_ai38_full_validation.py; continuous history is "
            "used only for drawdown-duration and losing-streak state. All indicator/execution "
            "parameters remain unchanged. Position size is normalized to 10,000 GBP units for "
            "research drawdown health. Reference thresholds are frozen before the observed weak "
            "post-2026-03 regime. The failed 2005-2020 backlog remains a permanent caveat."
        ),
        "data": {
            "source": "Dukascopy midpoint GBPUSD, 4H UTC+2 alignment",
            "analysis_end_exclusive": args.analysis_end.isoformat(),
            "reference_history_start": REFERENCE_START.isoformat(),
            "reference_history_end": REFERENCE_END.isoformat(),
            "first_bar": candles[0].time.isoformat(),
            "last_bar": candles[-1].time.isoformat(),
            "bars": len(candles),
            "data_age_hours_at_analysis_end": stale_hours,
            "data_stale": stale_hours > 36.0,
        },
        "monitor_sizing": {
            "initial_capital_usd": INITIAL_CAPITAL,
            "fixed_units": NORMALIZED_FIXED_UNITS,
            "creator_fixed_units": 100_000.0,
            "note": (
                "Research normalization only. Signal timing, stop/target logic, costs, win rate, "
                "profit factor and all indicator parameters are unchanged."
            ),
        },
        "reference_thresholds": thresholds,
        "current_percentiles_vs_reference": pct,
        "current_regime": {
            "classification": classification,
            "latest_6m": latest6,
            "latest_12m": latest12,
            "latest_24m": latest24,
            "current_unrecovered_drawdown": current_dd,
            "current_ending_losing_streak": {
                "length": ending_streak,
                "reference_max": thresholds["max_losing_streak"],
            },
            "signals": signals,
        },
        "reference_sample": {
            "rolling_6m_windows": len(ref6),
            "rolling_12m_windows": len(ref12),
            "rolling_24m_windows": len(ref24),
            "drawdown_episodes": len(ref_depths),
            "losing_streaks": len(ref_streaks),
        },
        "permanent_caveat": (
            "AI38's 2005-2020 pre-optimization backlog failed. This monitor evaluates whether "
            "the more recent validated regime persists; it does not erase or repair that failure."
        ),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, allow_nan=True), encoding="utf-8")
    print(
        json.dumps(
            {
                "classification": classification,
                "latest_6m": latest6,
                "latest_12m": latest12,
                "latest_24m": latest24,
                "drawdown": current_dd,
                "ending_losing_streak": ending_streak,
                "signals": signals,
                "data_stale": payload["data"]["data_stale"],
            },
            indent=2,
            allow_nan=True,
        )
    )


if __name__ == "__main__":
    main()
