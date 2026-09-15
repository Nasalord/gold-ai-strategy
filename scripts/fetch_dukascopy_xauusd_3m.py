from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

from fetch_dukascopy_xauusd import (
    is_regular_xau_trading_hour,
    month_rows,
    month_starts,
    parse_date,
)


BAR_MS = 3 * 60 * 1000
HOUR_MS = 60 * 60 * 1000


@dataclass
class Bar:
    timestamp_ms: int
    open: float
    high: float
    low: float
    close: float
    source_rows: int = 1

    def update(self, o: float, h: float, l: float, c: float) -> None:
        self.high = max(self.high, h)
        self.low = min(self.low, l)
        self.close = c
        self.source_rows += 1

    @property
    def flat(self) -> bool:
        return self.open == self.high == self.low == self.close


def _synthetic_flat_hours(bars: list[Bar]) -> set[int]:
    """Find entire regular-session hours that are completely flat.

    The public monthly dataset can forward-fill holiday closures. We remove an
    hour only when every 3-minute bar inside that hour is flat and every bar is
    at the same price. Individual flat 3-minute bars inside an otherwise active
    hour remain in the series.
    """
    groups: dict[int, list[Bar]] = {}
    for bar in bars:
        hour = bar.timestamp_ms - (bar.timestamp_ms % HOUR_MS)
        groups.setdefault(hour, []).append(bar)

    closed: set[int] = set()
    for hour, group in groups.items():
        if not group or not all(bar.flat for bar in group):
            continue
        prices = {bar.close for bar in group}
        if len(prices) == 1:
            closed.add(hour)
    return closed


def aggregate_3m(
    *,
    start: date,
    end: date,
    side: str,
    trading_session_only: bool,
    drop_flat_hours: bool,
) -> tuple[list[Bar], dict[str, object]]:
    start_ms = int(datetime(start.year, start.month, start.day, tzinfo=timezone.utc).timestamp() * 1000)
    end_ms = int(datetime(end.year, end.month, end.day, tzinfo=timezone.utc).timestamp() * 1000)

    bars: list[Bar] = []
    current: Bar | None = None
    source_rows = 0
    months = 0

    for month in month_starts(start, end):
        months += 1
        for ts, (o, h, l, c) in month_rows(month, side):
            if ts < start_ms or ts >= end_ms:
                continue
            source_rows += 1
            bucket = ts - (ts % BAR_MS)
            if current is None or bucket != current.timestamp_ms:
                if current is not None:
                    bars.append(current)
                current = Bar(bucket, o, h, l, c)
            else:
                current.update(o, h, l, c)

    if current is not None:
        bars.append(current)

    raw_bars = len(bars)
    dropped_schedule = 0
    dropped_flat_hours = 0

    if trading_session_only:
        regular = [bar for bar in bars if is_regular_xau_trading_hour(bar.timestamp_ms)]
        dropped_schedule = len(bars) - len(regular)
        bars = regular

        if drop_flat_hours:
            closed_hours = _synthetic_flat_hours(bars)
            before = len(bars)
            bars = [
                bar
                for bar in bars
                if (bar.timestamp_ms - (bar.timestamp_ms % HOUR_MS)) not in closed_hours
            ]
            dropped_flat_hours = before - len(bars)

    summary = {
        "instrument": "XAUUSD",
        "provider": "Dukascopy via kevingtlin/Market-Data-Lab",
        "price_side": side,
        "source_timeframe": "1m",
        "output_timeframe": "3m UTC-aligned",
        "start_inclusive": start.isoformat(),
        "end_exclusive": end.isoformat(),
        "months_requested": months,
        "source_rows": source_rows,
        "raw_3m_bars": raw_bars,
        "trading_session_only": trading_session_only,
        "drop_flat_hours": drop_flat_hours,
        "dropped_closed_schedule_3m_bars": dropped_schedule,
        "dropped_flat_hour_3m_bars": dropped_flat_hours,
        "bars": len(bars),
    }
    return bars, summary


def write_csv(path: Path, bars: list[Bar]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["timestamp", "open", "high", "low", "close"])
        for bar in bars:
            ts = datetime.fromtimestamp(bar.timestamp_ms / 1000, tz=timezone.utc)
            writer.writerow(
                [
                    ts.isoformat().replace("+00:00", "Z"),
                    f"{bar.open:.10f}",
                    f"{bar.high:.10f}",
                    f"{bar.low:.10f}",
                    f"{bar.close:.10f}",
                ]
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch Dukascopy XAUUSD M1 history and resample to 3m")
    parser.add_argument("--start", type=parse_date, required=True)
    parser.add_argument("--end", type=parse_date, required=True)
    parser.add_argument("--side", choices=["bid", "ask", "mid"], required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path)
    parser.add_argument("--trading-session-only", action="store_true")
    parser.add_argument("--drop-flat-hours", action="store_true")
    args = parser.parse_args()

    if args.start >= args.end:
        raise ValueError("--start must be before --end")
    if args.drop_flat_hours and not args.trading_session_only:
        raise ValueError("--drop-flat-hours requires --trading-session-only")

    bars, summary = aggregate_3m(
        start=args.start,
        end=args.end,
        side=args.side,
        trading_session_only=args.trading_session_only,
        drop_flat_hours=args.drop_flat_hours,
    )
    if not bars:
        raise RuntimeError("no bars produced")

    write_csv(args.output, bars)
    if args.summary is not None:
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
