from __future__ import annotations

import argparse
import csv
import io
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


RAW_BASE = "https://raw.githubusercontent.com/kevingtlin/Market-Data-Lab/main/xauusd"
NY = ZoneInfo("America/New_York")


@dataclass
class HourBar:
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


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def month_starts(start: date, end: date):
    cur = date(start.year, start.month, 1)
    while cur < end:
        yield cur
        if cur.month == 12:
            cur = date(cur.year + 1, 1, 1)
        else:
            cur = date(cur.year, cur.month + 1, 1)


def _url(side: str, month: date) -> str:
    filename = f"xauusd_{side}_m1_{month.year:04d}_{month.month:02d}.csv"
    return f"{RAW_BASE}/{side}/m1/{filename}"


def fetch_text(url: str, *, retries: int = 5) -> str:
    last_error: Exception | None = None
    for attempt in range(retries):
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "ai-investing-lab-ai65-parity/1.0",
                "Accept": "text/csv,text/plain,*/*",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                body = response.read()
            if not body:
                raise RuntimeError(f"empty response from {url}")
            return body.decode("utf-8-sig")
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, RuntimeError) as exc:
            last_error = exc
            if attempt + 1 == retries:
                break
            time.sleep(min(20, 2**attempt))
    raise RuntimeError(f"failed to download {url}: {last_error}")


def parse_rows(text: str) -> dict[int, tuple[float, float, float, float]]:
    rows: dict[int, tuple[float, float, float, float]] = {}
    reader = csv.DictReader(io.StringIO(text))
    required = {"timestamp", "open", "high", "low", "close"}
    if not required.issubset(reader.fieldnames or []):
        raise ValueError(f"unexpected CSV columns: {reader.fieldnames}")

    for row in reader:
        ts = int(row["timestamp"])
        rows[ts] = (
            float(row["open"]),
            float(row["high"]),
            float(row["low"]),
            float(row["close"]),
        )
    return rows


def month_rows(month: date, side: str):
    if side in {"bid", "ask"}:
        rows = parse_rows(fetch_text(_url(side, month)))
        for ts in sorted(rows):
            yield ts, rows[ts]
        return

    if side != "mid":
        raise ValueError(f"unsupported price side: {side}")

    bid = parse_rows(fetch_text(_url("bid", month)))
    ask = parse_rows(fetch_text(_url("ask", month)))
    common = sorted(set(bid).intersection(ask))
    if not common:
        raise RuntimeError(f"no overlapping bid/ask rows for {month:%Y-%m}")

    for ts in common:
        b = bid[ts]
        a = ask[ts]
        yield ts, tuple((x + y) / 2.0 for x, y in zip(b, a))


def is_regular_xau_trading_hour(timestamp_ms: int) -> bool:
    """Return whether an H1 bar-open is inside Dukascopy's normal XAU/USD week.

    Dukascopy's published XAU/USD schedule maps cleanly to New York local time:
    the regular daily settlement break is 17:00-18:00 NY, the weekend closes
    Friday at 17:00 NY, and Gold resumes after the Sunday settlement hour at
    18:00 NY. Using America/New_York makes the UTC shift DST-aware.

    US-holiday extended closures are handled separately by optionally dropping
    fully flat H1 bars after this regular-session filter.
    """
    local = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).astimezone(NY)
    weekday = local.weekday()  # Monday=0, Sunday=6
    hour = local.hour

    if weekday == 5:  # Saturday
        return False
    if weekday == 6:  # Sunday: Gold resumes after settlement break
        return hour >= 18
    if weekday == 4:  # Friday: closed from 17:00 NY onward
        return hour < 17

    # Monday-Thursday daily settlement break.
    return hour != 17


def filter_trading_hours(
    bars: list[HourBar], *, drop_flat_hours: bool
) -> tuple[list[HourBar], dict[str, int]]:
    regular = [bar for bar in bars if is_regular_xau_trading_hour(bar.timestamp_ms)]
    dropped_schedule = len(bars) - len(regular)

    if drop_flat_hours:
        active = [bar for bar in regular if not bar.flat]
    else:
        active = regular

    return active, {
        "dropped_closed_schedule_hours": dropped_schedule,
        "dropped_flat_hours_inside_schedule": len(regular) - len(active),
    }


def aggregate_hourly(
    *,
    start: date,
    end: date,
    side: str,
    trading_session_only: bool = False,
    drop_flat_hours: bool = False,
) -> tuple[list[HourBar], dict[str, object]]:
    start_ms = int(
        datetime(start.year, start.month, start.day, tzinfo=timezone.utc).timestamp()
        * 1000
    )
    end_ms = int(
        datetime(end.year, end.month, end.day, tzinfo=timezone.utc).timestamp()
        * 1000
    )

    bars: list[HourBar] = []
    current: HourBar | None = None
    source_rows = 0
    months = 0

    for month in month_starts(start, end):
        months += 1
        for ts, (o, h, l, c) in month_rows(month, side):
            if ts < start_ms or ts >= end_ms:
                continue
            source_rows += 1
            hour_ts = ts - (ts % 3_600_000)
            if current is None or hour_ts != current.timestamp_ms:
                if current is not None:
                    bars.append(current)
                current = HourBar(hour_ts, o, h, l, c)
            else:
                current.update(o, h, l, c)

    if current is not None:
        bars.append(current)

    raw_hourly_bars = len(bars)
    filter_summary = {
        "dropped_closed_schedule_hours": 0,
        "dropped_flat_hours_inside_schedule": 0,
    }
    if trading_session_only:
        bars, filter_summary = filter_trading_hours(
            bars, drop_flat_hours=drop_flat_hours
        )

    summary = {
        "instrument": "XAUUSD",
        "provider": "Dukascopy via kevingtlin/Market-Data-Lab",
        "price_side": side,
        "source_timeframe": "1m",
        "output_timeframe": "1h UTC-aligned",
        "start_inclusive": start.isoformat(),
        "end_exclusive": end.isoformat(),
        "months_requested": months,
        "source_rows": source_rows,
        "raw_hourly_bars": raw_hourly_bars,
        "trading_session_only": trading_session_only,
        "drop_flat_hours": drop_flat_hours,
        **filter_summary,
        "hourly_bars": len(bars),
    }
    return bars, summary


def write_csv(path: Path, bars: list[HourBar]) -> None:
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
    parser = argparse.ArgumentParser(
        description="Fetch public Dukascopy XAUUSD M1 history and resample to H1"
    )
    parser.add_argument("--start", type=parse_date, required=True)
    parser.add_argument("--end", type=parse_date, required=True)
    parser.add_argument("--side", choices=["bid", "ask", "mid"], required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path)
    parser.add_argument(
        "--trading-session-only",
        action="store_true",
        help="Remove regular weekend and daily XAU/USD settlement-break hours.",
    )
    parser.add_argument(
        "--drop-flat-hours",
        action="store_true",
        help="Also remove fully flat H1 bars inside the regular schedule (holiday closures).",
    )
    args = parser.parse_args()

    if args.start >= args.end:
        raise ValueError("--start must be before --end")
    if args.drop_flat_hours and not args.trading_session_only:
        raise ValueError("--drop-flat-hours requires --trading-session-only")

    bars, summary = aggregate_hourly(
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
