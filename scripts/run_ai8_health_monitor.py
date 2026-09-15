from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from math import ceil, floor, inf
from pathlib import Path

from ai_investing_lab.strategies.ai8_btc import AI8Backtester, AI8Config, Candle

UTC = timezone.utc
DATA_START = datetime(2017, 8, 17, tzinfo=UTC)
BACKLOG_START = datetime(2018, 3, 1, tzinfo=UTC)
REFERENCE_END = datetime(2025, 9, 1, tzinfo=UTC)
INITIAL_CAPITAL = 100_000.0
# Preserve AI8's exact signals/pyramiding but normalize each of seven possible
# stacked entries so maximum requested gross notional is about 1x capital.
NORMALIZED_LEG_CASH = INITIAL_CAPITAL / 7.0


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


def summarize(trades, start: datetime, end: datetime) -> dict[str, float | int]:
    closed = [
        t for t in trades
        if t.closed and t.exit_time is not None and start <= t.exit_time < end
    ]
    closed.sort(key=lambda t: (t.exit_time, t.entry_time))
    wins = [t for t in closed if t.net_pnl_usd > 0]
    losses = [t for t in closed if t.net_pnl_usd <= 0]
    gp = sum(t.net_pnl_usd for t in wins)
    gl = abs(sum(t.net_pnl_usd for t in losses))
    net = sum(t.net_pnl_usd for t in closed)
    pf = gp / gl if gl else (inf if gp else 0.0)
    equity = INITIAL_CAPITAL
    peak = equity
    max_dd = 0.0
    for trade in closed:
        equity += trade.net_pnl_usd
        peak = max(peak, equity)
        if peak > 0:
            max_dd = max(max_dd, 100.0 * (peak - equity) / peak)
    n = len(closed)
    return {
        "trades": n,
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_pct": 100.0 * len(wins) / n if n else 0.0,
        "net_profit_usd": net,
        "net_profit_pct": 100.0 * net / INITIAL_CAPITAL,
        "profit_factor": pf,
        "max_closed_trade_drawdown_pct": max_dd,
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


def rolling_reference(trades, months: int) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    end = shift_months(BACKLOG_START, months)
    while end <= REFERENCE_END:
        start = shift_months(end, -months)
        rows.append({
            "start": start.date().isoformat(),
            "end": end.date().isoformat(),
            **summarize(trades, start, end),
        })
        end = shift_months(end, 1)
    return rows


def losing_streaks(trades, end: datetime) -> tuple[list[int], int]:
    closed = [t for t in trades if t.closed and t.exit_time is not None and t.exit_time < end]
    closed.sort(key=lambda t: (t.exit_time, t.entry_time))
    streaks: list[int] = []
    current = 0
    for t in closed:
        if t.net_pnl_usd <= 0:
            current += 1
        elif current:
            streaks.append(current)
            current = 0
    if current:
        streaks.append(current)
    return streaks, current


def drawdown_episodes(trades, end: datetime) -> tuple[list[dict[str, float]], dict[str, float]]:
    closed = [t for t in trades if t.closed and t.exit_time is not None and t.exit_time < end]
    closed.sort(key=lambda t: (t.exit_time, t.entry_time))
    equity = INITIAL_CAPITAL
    peak = equity
    peak_time = BACKLOG_START
    active = False
    max_depth = 0.0
    episodes: list[dict[str, float]] = []

    for t in closed:
        equity += t.net_pnl_usd
        if equity >= peak:
            if active and t.exit_time is not None:
                episodes.append({
                    "max_drawdown_pct": max_depth,
                    "duration_days": (t.exit_time - peak_time).total_seconds() / 86400.0,
                })
            peak = equity
            peak_time = t.exit_time or peak_time
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
    parser = argparse.ArgumentParser(description="Run frozen AI8 regime health monitor")
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--analysis-end", type=parse_date, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.analysis_end <= REFERENCE_END:
        raise ValueError("--analysis-end must be after frozen reference cutoff 2025-09-01")

    candles = load_csv(args.csv_path)
    if not candles:
        raise RuntimeError("no BTCUSDT candles loaded")

    cfg = AI8Config.creator_fixed_cash(fixed_cash_usd=NORMALIZED_LEG_CASH)
    result = AI8Backtester(cfg).run(
        candles,
        trade_start=BACKLOG_START,
        trade_end=args.analysis_end,
        close_at_end=False,
    )
    trades = result.trades

    ref6 = rolling_reference(trades, 6)
    ref12 = rolling_reference(trades, 12)
    ref24 = rolling_reference(trades, 24)

    latest6 = summarize(trades, shift_months(args.analysis_end, -6), args.analysis_end)
    latest12 = summarize(trades, shift_months(args.analysis_end, -12), args.analysis_end)
    latest24 = summarize(trades, shift_months(args.analysis_end, -24), args.analysis_end)

    ref_streaks, _ = losing_streaks(trades, REFERENCE_END)
    _, ending_streak = losing_streaks(trades, args.analysis_end)

    ref_dd_episodes, ref_unrecovered = drawdown_episodes(trades, REFERENCE_END)
    current_dd_episodes, current_dd = drawdown_episodes(trades, args.analysis_end)
    ref_depths = [x["max_drawdown_pct"] for x in ref_dd_episodes]
    ref_durations = [x["duration_days"] for x in ref_dd_episodes]
    if ref_unrecovered["duration_days"] > 0:
        ref_depths.append(ref_unrecovered["max_drawdown_pct"])
        ref_durations.append(ref_unrecovered["duration_days"])

    thresholds = {
        "reference_end": REFERENCE_END.isoformat(),
        "drawdown_depth_p95_pct": percentile(ref_depths, 0.95),
        "drawdown_duration_p95_days": percentile(ref_durations, 0.95),
        "losing_streak_length_p95": percentile([float(x) for x in ref_streaks], 0.95),
        "max_losing_streak": max(ref_streaks) if ref_streaks else 0,
        "rolling_6m_return_p10_pct": percentile([float(r["net_profit_pct"]) for r in ref6], 0.10),
        "rolling_12m_return_p10_pct": percentile([float(r["net_profit_pct"]) for r in ref12], 0.10),
    }

    pct = {
        "latest_6m_return_percentile": percentile_rank([float(r["net_profit_pct"]) for r in ref6], float(latest6["net_profit_pct"])),
        "latest_12m_return_percentile": percentile_rank([float(r["net_profit_pct"]) for r in ref12], float(latest12["net_profit_pct"])),
        "latest_24m_return_percentile": percentile_rank([float(r["net_profit_pct"]) for r in ref24], float(latest24["net_profit_pct"])),
        "latest_6m_pf_percentile": percentile_rank([float(r["profit_factor"]) for r in ref6], float(latest6["profit_factor"])),
        "latest_12m_pf_percentile": percentile_rank([float(r["profit_factor"]) for r in ref12], float(latest12["profit_factor"])),
        "latest_24m_pf_percentile": percentile_rank([float(r["profit_factor"]) for r in ref24], float(latest24["profit_factor"])),
    }

    signals = {
        "weak_6m": latest6["net_profit_pct"] <= 0 or latest6["profit_factor"] < 1.0,
        "weak_12m": latest12["net_profit_pct"] <= 0 or latest12["profit_factor"] < 1.0,
        "weak_24m": latest24["net_profit_pct"] <= 0 or latest24["profit_factor"] < 1.0,
        "6m_return_below_reference_p10": pct["latest_6m_return_percentile"] <= 10.0,
        "12m_return_below_reference_p10": pct["latest_12m_return_percentile"] <= 10.0,
        "drawdown_depth_over_reference_p95": current_dd["max_drawdown_pct"] >= thresholds["drawdown_depth_p95_pct"] and current_dd["max_drawdown_pct"] > 0,
        "drawdown_duration_over_reference_p95": current_dd["duration_days"] >= thresholds["drawdown_duration_p95_days"] and current_dd["duration_days"] > 0,
        "losing_streak_over_reference_p95": ending_streak >= max(1, ceil(thresholds["losing_streak_length_p95"])),
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
        or (signals["weak_24m"] and signals["weak_12m"] and (signals["weak_6m"] or risk_breaches >= 1))
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
        "method": (
            "Frozen AI8 signal/regime monitor. Strategy inputs and pyramiding are unchanged; "
            "position notional is normalized to 1/7 of $100k per leg so seven stacked legs "
            "represent roughly 1x requested gross exposure. Reference thresholds are frozen "
            "using history ending 2025-09-01, before the known weak 12-month regime."
        ),
        "data": {
            "source": "Official Binance Vision spot BTCUSDT 2h klines",
            "analysis_end_exclusive": args.analysis_end.isoformat(),
            "reference_history_end": REFERENCE_END.isoformat(),
            "first_bar": candles[0].time.isoformat(),
            "last_bar": candles[-1].time.isoformat(),
            "bars": len(candles),
            "data_age_hours_at_analysis_end": stale_hours,
            "data_stale": stale_hours > 30.0,
        },
        "monitor_sizing": {
            "initial_capital_usd": INITIAL_CAPITAL,
            "fixed_cash_per_leg_usd": NORMALIZED_LEG_CASH,
            "pyramiding": 7,
            "max_requested_gross_if_full_stack_usd": NORMALIZED_LEG_CASH * 7,
            "note": "Research normalization only. It does not recommend live position sizing.",
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
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, allow_nan=True), encoding="utf-8")
    print(json.dumps({
        "classification": classification,
        "latest_6m": latest6,
        "latest_12m": latest12,
        "latest_24m": latest24,
        "drawdown": current_dd,
        "ending_losing_streak": ending_streak,
        "signals": signals,
        "data_stale": payload["data"]["data_stale"],
    }, indent=2, allow_nan=True))


if __name__ == "__main__":
    main()
