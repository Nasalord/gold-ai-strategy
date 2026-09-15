from __future__ import annotations

import argparse
import csv
import io
import json
import urllib.error
import urllib.request
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://data.binance.vision/data/spot"
SYMBOL = "BTCUSDT"
SOURCE_INTERVAL = "5m"
TARGET_MS = 10 * 60 * 1000


def parse_date(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def month_start(dt: datetime) -> datetime:
    return datetime(dt.year, dt.month, 1, tzinfo=timezone.utc)


def next_month(dt: datetime) -> datetime:
    year = dt.year + (1 if dt.month == 12 else 0)
    month = 1 if dt.month == 12 else dt.month + 1
    return datetime(year, month, 1, tzinfo=timezone.utc)


def download(url: str) -> bytes | None:
    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def archive_rows(payload: bytes):
    with zipfile.ZipFile(io.BytesIO(payload)) as zf:
        names = [n for n in zf.namelist() if n.endswith(".csv")]
        if not names:
            return
        with zf.open(names[0]) as handle:
            text = io.TextIOWrapper(handle, encoding="utf-8")
            for row in csv.reader(text):
                if not row or not row[0].isdigit():
                    continue
                yield row


def timestamp_ms(raw: str) -> int:
    """Normalize Binance archive timestamps to milliseconds.

    Binance Spot historical archives changed newer kline timestamps from
    milliseconds to microseconds. Millisecond Unix timestamps are ~1e12 while
    microseconds are ~1e15, so the unit is unambiguous for this dataset.
    """
    value = int(raw)
    if value >= 100_000_000_000_000:
        value //= 1000
    return value


def main() -> None:
    ap = argparse.ArgumentParser(description="Fetch official Binance Spot BTCUSDT 5m archives and aggregate to 10m")
    ap.add_argument("--start", type=parse_date, required=True)
    ap.add_argument("--end", type=parse_date, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    if args.start >= args.end:
        raise ValueError("--start must be before --end")

    groups: dict[int, list[list[str]]] = defaultdict(list)
    month = month_start(args.start)
    archives = 0
    while month < args.end:
        name = f"{SYMBOL}-{SOURCE_INTERVAL}-{month:%Y-%m}.zip"
        url = f"{BASE}/monthly/klines/{SYMBOL}/{SOURCE_INTERVAL}/{name}"
        payload = download(url)
        if payload is not None:
            archives += 1
            for row in archive_rows(payload):
                ts = timestamp_ms(row[0])
                dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
                if not (args.start <= dt < args.end):
                    continue
                normalized = list(row)
                normalized[0] = str(ts)
                bucket = (ts // TARGET_MS) * TARGET_MS
                groups[bucket].append(normalized)
        month = next_month(month)

    if not groups:
        raise RuntimeError("no Binance BTCUSDT 5m data downloaded")

    out_rows = []
    for bucket in sorted(groups):
        rows = sorted(groups[bucket], key=lambda r: int(r[0]))
        # Require both constituent 5m bars for a complete 10m candle.
        if len(rows) != 2:
            continue
        out_rows.append({
            "timestamp": datetime.fromtimestamp(bucket / 1000, tz=timezone.utc).isoformat(),
            "open": float(rows[0][1]),
            "high": max(float(r[2]) for r in rows),
            "low": min(float(r[3]) for r in rows),
            "close": float(rows[-1][4]),
            "volume": sum(float(r[5]) for r in rows),
        })

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["timestamp", "open", "high", "low", "close", "volume"])
        writer.writeheader()
        writer.writerows(out_rows)

    summary = {
        "provider": "Binance Vision Spot 5m aggregated to 10m",
        "symbol": SYMBOL,
        "source_interval": SOURCE_INTERVAL,
        "target_interval": "10m",
        "start_inclusive": args.start.isoformat(),
        "end_exclusive": args.end.isoformat(),
        "monthly_archives": archives,
        "rows": len(out_rows),
        "first": out_rows[0]["timestamp"],
        "last": out_rows[-1]["timestamp"],
    }
    args.output.with_suffix(".summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
