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

from ai_investing_lab.strategies.ai65_gold import AI65Backtester, AI65Config, compute_tdfi
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
class VideoTrade:
    entry_price: float
    quantity: float
    stop_price: float
    target_price: float
    entry_time: datetime
    exit_time: datetime | None = None
    exit_price: float | None = None
    net_pnl: float = 0.0


@dataclass
class Session:
    key: date
    high: float | None = None
    low: float | None = None
    pending: bool = False
    traded: bool = False


def _session_key(local_dt: datetime) -> date:
    clock = local_dt.timetz().replace(tzinfo=None)
    return local_dt.date() if clock >= time(11, 0) else local_dt.date() - timedelta(days=1)


def _metrics(trades: list[VideoTrade], initial_capital: float = 10_000.0) -> dict[str, float | int]:
    wins = [t for t in trades if t.net_pnl > 0]
    losses = [t for t in trades if t.net_pnl <= 0]
    gross_profit = sum(t.net_pnl for t in wins)
    gross_loss = abs(sum(t.net_pnl for t in losses))
    net = sum(t.net_pnl for t in trades)
    equity = initial_capital
    peak = equity
    max_dd = 0.0
    for trade in trades:
        equity += trade.net_pnl
        peak = max(peak, equity)
        if peak > 0:
            max_dd = max(max_dd, (peak - equity) / peak)
    n = len(trades)
    return {
        "trades": n,
        "net_profit_pct": 100.0 * net / initial_capital,
        "profit_factor": gross_profit / gross_loss if gross_loss else (math.inf if gross_profit else 0.0),
        "win_rate_pct": 100.0 * len(wins) / n if n else 0.0,
        "max_drawdown_pct": 100.0 * max_dd,
    }


def run_video_breakout_tdfi(
    candles,
    *,
    min_tick: float,
    slippage_ticks: int,
    commission_per_unit_per_side: float,
    block_entries_at_force_exit: bool = True,
) -> dict[str, float | int]:
    """Literal-video diagnostic: TDFI must agree when price is breaking the OR high.

    This is intentionally separate from the uploaded Pine source's arm-time filter.
    It is a research diagnostic, not a replacement baseline.
    """
    tdfi = compute_tdfi([c.close for c in candles], 5)
    slippage = slippage_ticks * min_tick
    trades: list[VideoTrade] = []
    session: Session | None = None
    position: VideoTrade | None = None
    force_exit_next_bar = False
    prev_local: datetime | None = None

    def close_position(trade: VideoTrade, candle, price: float) -> None:
        trade.exit_time = candle.time
        trade.exit_price = price
        trade.net_pnl = trade.quantity * (price - trade.entry_price)
        trade.net_pnl -= 2.0 * trade.quantity * commission_per_unit_per_side
        trades.append(trade)

    for i, candle in enumerate(candles):
        local = candle.time.astimezone(NY)
        key = _session_key(local)
        clock = local.timetz().replace(tzinfo=None)

        if force_exit_next_bar and position is not None:
            close_position(position, candle, max(0.0, candle.open - slippage))
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
            and not in_range
            and session.high is not None
            and session.low is not None
            and candle.high >= session.high
            and (not block_entries_at_force_exit or clock < time(22, 0))
        ):
            filter_ok = tdfi[i] is not None and tdfi[i] > -0.05
            if filter_ok:
                raw_fill = max(session.high, candle.open)
                entry = raw_fill + slippage
                base_distance = max(entry - session.low, min_tick)
                stop = entry - base_distance * 3.8
                target = entry + base_distance * 3.3
                qty = 70_000.0 / entry
                position = VideoTrade(entry, qty, stop, target, candle.time)
                session.traded = True
                session.pending = False

                stop_hit = candle.low <= stop
                target_hit = candle.high >= target
                if stop_hit:
                    close_position(position, candle, max(0.0, stop - slippage))
                    position = None
                elif target_hit:
                    close_position(position, candle, target)
                    position = None

        elif position is not None:
            stop_hit = candle.low <= position.stop_price
            target_hit = candle.high >= position.target_price
            if stop_hit:
                close_position(position, candle, max(0.0, position.stop_price - slippage))
                position = None
            elif target_hit:
                close_position(position, candle, position.target_price)
                position = None

        if in_range:
            session.high = candle.high if session.high is None else max(session.high, candle.high)
            session.low = candle.low if session.low is None else min(session.low, candle.low)
            bar_close_local = (candle.time + timedelta(hours=1)).astimezone(NY)
            if bar_close_local >= range_end and session.high > session.low:
                # Video interpretation: once the range is complete, wait for a
                # breakout whose contemporaneous TDFI agrees.
                session.pending = True

        crossed_force = (
            clock >= time(22, 0)
            and (
                prev_local is None
                or prev_local.date() != local.date()
                or prev_local.timetz().replace(tzinfo=None) < time(22, 0)
            )
        )
        if crossed_force and position is not None:
            force_exit_next_bar = True

        prev_local = local

    if position is not None:
        last = candles[-1]
        close_position(position, last, max(0.0, last.close - slippage))

    return _metrics(trades)


def run_source_arm_time(candles, *, min_tick: float, slippage_ticks: int, commission: float):
    cfg = AI65Config.creator_1h(
        min_tick=min_tick,
        slippage_ticks=slippage_ticks,
        commission_per_contract_per_side=commission,
    )
    m = AI65Backtester(cfg).run(candles).metrics
    return {
        "trades": m.trades,
        "net_profit_pct": m.net_profit_pct,
        "profit_factor": m.profit_factor,
        "win_rate_pct": m.win_rate_pct,
        "max_drawdown_pct": m.max_drawdown_pct,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="AI65 video-vs-source semantics and tick-size diagnostic")
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    candles = load_candles_csv(args.csv_path)
    cases = [
        ("0.01", 0.01, 100, 0.04),
        ("0.001", 0.001, 100, 0.04),
        ("0.0001", 0.0001, 100, 0.04),
        ("zero_slippage", 0.001, 0, 0.04),
        ("zero_costs", 0.001, 0, 0.0),
    ]

    results = {"benchmark": BENCHMARK, "source_arm_time": {}, "video_breakout_time": {}}
    for label, min_tick, slippage_ticks, commission in cases:
        results["source_arm_time"][label] = run_source_arm_time(
            candles,
            min_tick=min_tick,
            slippage_ticks=slippage_ticks,
            commission=commission,
        )
        results["video_breakout_time"][label] = run_video_breakout_tdfi(
            candles,
            min_tick=min_tick,
            slippage_ticks=slippage_ticks,
            commission_per_unit_per_side=commission,
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
