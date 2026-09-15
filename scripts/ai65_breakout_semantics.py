from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai_investing_lab.strategies.ai65_gold import compute_tdfi
from ai_investing_lab.strategies.ai65_gold.csv_runner import load_candles_csv

NY = ZoneInfo("America/New_York")
BENCHMARK = {
    "trades": 670,
    "net_profit_pct": 552.94,
    "profit_factor": 1.667,
    "win_rate_pct": 52.69,
    "max_drawdown_pct": 25.73,
}


@dataclass
class Position:
    entry: float
    stop: float
    target: float
    qty: float
    session_date: date


@dataclass
class Session:
    key: date
    high: float | None = None
    low: float | None = None
    pending: bool = False
    traded: bool = False
    invalidated: bool = False


def _session_key(local_dt: datetime) -> date:
    clock = local_dt.timetz().replace(tzinfo=None)
    return local_dt.date() if clock >= time(11, 0) else local_dt.date() - timedelta(days=1)


def _metrics(pnls: list[float]) -> dict[str, float | int]:
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    gp = sum(wins)
    gl = abs(sum(losses))
    equity = 10_000.0
    peak = equity
    max_dd = 0.0
    for pnl in pnls:
        equity += pnl
        peak = max(peak, equity)
        if peak > 0:
            max_dd = max(max_dd, (peak - equity) / peak)
    n = len(pnls)
    return {
        "trades": n,
        "net_profit_pct": 100.0 * sum(pnls) / 10_000.0,
        "profit_factor": gp / gl if gl else (math.inf if gp else 0.0),
        "win_rate_pct": 100.0 * len(wins) / n if n else 0.0,
        "max_drawdown_pct": 100.0 * max_dd,
    }


def _distance(metrics: dict[str, float | int]) -> dict[str, float]:
    return {
        "trade_count_abs_diff": abs(float(metrics["trades"]) - BENCHMARK["trades"]),
        "win_rate_abs_diff_pct_points": abs(float(metrics["win_rate_pct"]) - BENCHMARK["win_rate_pct"]),
        "profit_factor_abs_diff": abs(float(metrics["profit_factor"]) - BENCHMARK["profit_factor"]),
        "net_profit_abs_diff_pct_points": abs(float(metrics["net_profit_pct"]) - BENCHMARK["net_profit_pct"]),
        "max_drawdown_abs_diff_pct_points": abs(float(metrics["max_drawdown_pct"]) - BENCHMARK["max_drawdown_pct"]),
    }


def run_variant(candles, tdfi, *, variant: str) -> dict[str, object]:
    """Test source-plausible meanings of 'price breaks above the range and TDFI agrees'.

    This is diagnostic-only. All strategy parameters, costs, timezone, stop/target,
    force exit and one-trade-per-session rules are held fixed.
    """
    min_tick = 0.001
    slippage = 100 * min_tick
    commission = 0.04

    session: Session | None = None
    position: Position | None = None
    force_exit_next_bar = False
    prev_local: datetime | None = None
    prev_high: float | None = None
    prev_close: float | None = None
    pnls: list[float] = []
    traded_sessions: list[str] = []

    def close(pos: Position, price: float) -> None:
        pnl = pos.qty * (price - pos.entry) - 2.0 * pos.qty * commission
        pnls.append(pnl)

    for i, candle in enumerate(candles):
        local = candle.time.astimezone(NY)
        key = _session_key(local)
        clock = local.timetz().replace(tzinfo=None)

        if force_exit_next_bar and position is not None:
            close(position, max(0.0, candle.open - slippage))
            position = None
            force_exit_next_bar = False

        if session is None or session.key != key:
            session = Session(key=key)

        range_start = datetime.combine(key, time(11, 0), NY)
        range_end = datetime.combine(key, time(13, 0), NY)
        in_range = range_start <= local < range_end

        if (
            position is None
            and session.pending
            and not session.traded
            and not session.invalidated
            and not in_range
            and session.high is not None
            and session.low is not None
        ):
            h = session.high
            tdfi_ok = tdfi[i] is not None and tdfi[i] > -0.05
            touched = candle.high >= h

            if variant == "any_above":
                breakout = touched
            elif variant == "previous_high_below":
                breakout = prev_high is not None and prev_high < h and touched
            elif variant == "previous_close_below":
                breakout = prev_close is not None and prev_close <= h and touched
            elif variant == "open_below":
                breakout = candle.open <= h and touched
            elif variant == "close_cross":
                breakout = prev_close is not None and prev_close <= h and candle.close > h
            elif variant in {"first_touch_only", "first_close_only"}:
                breakout = touched if variant == "first_touch_only" else candle.close > h
                if breakout and not tdfi_ok:
                    # The first breakout occurred without confirmation, so the
                    # session receives no second chance unless price forms a new
                    # opening range the next day.
                    session.invalidated = True
                    session.pending = False
            else:
                raise ValueError(f"unknown variant: {variant}")

            if breakout and tdfi_ok:
                raw_fill = max(h, candle.open)
                entry = raw_fill + slippage
                base_distance = max(entry - session.low, min_tick)
                stop = entry - base_distance * 3.8
                target = entry + base_distance * 3.3
                qty = 70_000.0 / entry
                position = Position(entry, stop, target, qty, session.key)
                session.traded = True
                session.pending = False
                traded_sessions.append(session.key.isoformat())

                # Conservative historical same-bar ordering.
                if candle.low <= stop:
                    close(position, max(0.0, stop - slippage))
                    position = None
                elif candle.high >= target:
                    close(position, target)
                    position = None

        elif position is not None:
            if candle.low <= position.stop:
                close(position, max(0.0, position.stop - slippage))
                position = None
            elif candle.high >= position.target:
                close(position, position.target)
                position = None

        if in_range:
            session.high = candle.high if session.high is None else max(session.high, candle.high)
            session.low = candle.low if session.low is None else min(session.low, candle.low)
            bar_close_local = (candle.time + timedelta(hours=1)).astimezone(NY)
            if bar_close_local >= range_end and session.high > session.low:
                session.pending = True

        crossed_force_exit = (
            clock >= time(22, 0)
            and (
                prev_local is None
                or prev_local.date() != local.date()
                or prev_local.timetz().replace(tzinfo=None) < time(22, 0)
            )
        )
        if crossed_force_exit and position is not None:
            force_exit_next_bar = True

        prev_local = local
        prev_high = candle.high
        prev_close = candle.close

    if position is not None:
        last = candles[-1]
        close(position, max(0.0, last.close - slippage))

    metrics = _metrics(pnls)
    return {
        "metrics": metrics,
        "benchmark_distance": _distance(metrics),
        "traded_session_count": len(set(traded_sessions)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="AI65 fresh-breakout semantics diagnostic")
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    candles = load_candles_csv(args.csv_path)
    tdfi = compute_tdfi([c.close for c in candles], 5)
    variants = [
        "any_above",
        "previous_high_below",
        "previous_close_below",
        "open_below",
        "close_cross",
        "first_touch_only",
        "first_close_only",
    ]
    results = {
        "benchmark": BENCHMARK,
        "interpretation": "Diagnostic only; no parameter optimization.",
        "variants": {name: run_variant(candles, tdfi, variant=name) for name in variants},
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2, allow_nan=True), encoding="utf-8")
    print(json.dumps(results, indent=2, allow_nan=True))


if __name__ == "__main__":
    main()
