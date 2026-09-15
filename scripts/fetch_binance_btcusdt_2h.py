from __future__ import annotations

import argparse
import csv
import io
import json
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASES = {
    "spot": "https://data.binance.vision/data/spot",
    "usdm": "https://data.binance.vision/data/futures/um",
}
SYMBOL = "BTCUSDT"
INTERVAL = "2h"


def parse_date(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def month_start(dt: datetime) -> datetime:
    return datetime(dt.year, dt.month, 1, tzinfo=timezone.utc)


def next_month(dt: datetime) -> datetime:
    if dt.month == 12:
        return datetime(dt.year + 1, 1, 1, tzinfo=timezone.utc)
    return datetime(dt.year, dt.month + 1, 1, tzinfo=timezone.utc)


def download(url: str) -> bytes | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ai-investing-lab/1.0"})
        with urllib.request.urlopen(req, timeout=45) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def decode_zip(payload: bytes) -> list[list[str]]:
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = [n for n in archive.namelist() if n.lower().endswith(".csv")]
        if len(names) != 1:
            raise RuntimeError(f"expected one CSV in Binance archive, got {names!r}")
        text = archive.read(names[0]).decode("utf-8")
    return list(csv.reader(io.StringIO(text)))


def timestamp_ms(raw: str) -> int:
    value = int(raw)
    # Binance Vision began using microsecond timestamps in some newer archives.
    return value // 1000 if value > 10**14 else value


def rows_from_archive(rows: list[list[str]], start: datetime, end: datetime):
    start_ms = int(start.timestamp() * 1000)
    end_ms = int(end.timestamp() * 1000)
    for row in rows:
        if not row or not row[0].isdigit() or len(row) < 6:
            continue
        open_ms = timestamp_ms(row[0])
        if start_ms <= open_ms < end_ms:
            yield {
                "timestamp": datetime.fromtimestamp(open_ms / 1000, tz=timezone.utc).isoformat(),
                "open": float(row[1]),
                "high": float(row[2]),
                "low": float(row[3]),
                "close": float(row[4]),
                "volume": float(row[5]),
            }


def fetch_month(dt: datetime, base: str) -> bytes | None:
    name = f"{SYMBOL}-{INTERVAL}-{dt:%Y-%m}.zip"
    return download(f"{base}/monthly/klines/{SYMBOL}/{INTERVAL}/{name}")


def fetch_day(dt: datetime, base: str) -> bytes | None:
    name = f"{SYMBOL}-{INTERVAL}-{dt:%Y-%m-%d}.zip"
    return download(f"{base}/daily/klines/{SYMBOL}/{INTERVAL}/{name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch official Binance Vision BTCUSDT 2h klines")
    parser.add_argument("--start", type=parse_date, required=True)
    parser.add_argument("--end", type=parse_date, required=True)
    parser.add_argument("--market", choices=sorted(BASES), default="spot")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.start >= args.end:
        raise ValueError("--start must be before --end")

    base = BASES[args.market]
    collected: dict[str, dict[str, object]] = {}
    month = month_start(args.start)
    months_attempted = 0
    monthly_archives = 0
    daily_archives = 0

    while month < args.end:
        months_attempted += 1
        payload = fetch_month(month, base)
        if payload is not None:
            monthly_archives += 1
            for item in rows_from_archive(decode_zip(payload), args.start, args.end):
                collected[str(item["timestamp"])] = item
        else:
            day = max(month, args.start)
            month_end = min(next_month(month), args.end)
            while day < month_end:
                daily = fetch_day(day, base)
                if daily is not None:
                    daily_archives += 1
                    for item in rows_from_archive(decode_zip(daily), args.start, args.end):
                        collected[str(item["timestamp"])] = item
                day += timedelta(days=1)
        month = next_month(month)

    rows = [collected[key] for key in sorted(collected)]
    if not rows:
        raise RuntimeError(f"no Binance BTCUSDT {args.market} bars were downloaded")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["timestamp", "open", "high", "low", "close", "volume"])
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "provider": "Binance Vision spot klines" if args.market == "spot" else "Binance Vision USD-M perpetual klines",
        "market": args.market,
        "symbol": SYMBOL,
        "interval": INTERVAL,
        "start_inclusive": args.start.isoformat(),
        "end_exclusive": args.end.isoformat(),
        "rows": len(rows),
        "first": rows[0]["timestamp"],
        "last": rows[-1]["timestamp"],
        "months_attempted": months_attempted,
        "monthly_archives": monthly_archives,
        "daily_archives": daily_archives,
    }
    args.output.with_suffix(".summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
