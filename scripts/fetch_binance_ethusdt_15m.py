from __future__ import annotations

import argparse
import csv
import io
import json
import urllib.error
import urllib.request
import zipfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path


BASE = "https://data.binance.vision/data/spot"
SYMBOL = "ETHUSDT"
INTERVAL = "15m"


def _download_zip(url: str) -> bytes | None:
    req = urllib.request.Request(url, headers={"User-Agent": "ai-investing-lab/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def _timestamp_to_dt(raw: str) -> datetime:
    value = int(raw)
    divisor = 1_000_000 if value >= 100_000_000_000_000 else 1_000
    return datetime.fromtimestamp(value / divisor, tz=timezone.utc)


def _parse_zip(blob: bytes) -> list[tuple[datetime, float, float, float, float, float]]:
    rows: list[tuple[datetime, float, float, float, float, float]] = []
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not names:
            raise RuntimeError("archive contains no CSV")
        with zf.open(names[0]) as raw:
            text = io.TextIOWrapper(raw, encoding="utf-8")
            for row in csv.reader(text):
                if not row:
                    continue
                try:
                    t = _timestamp_to_dt(row[0])
                    o, h, l, c, v = map(float, row[1:6])
                except (ValueError, IndexError):
                    continue
                rows.append((t, o, h, l, c, v))
    return rows


def _month_starts(start: date, end: date):
    cur = date(start.year, start.month, 1)
    while cur < end:
        yield cur
        if cur.month == 12:
            cur = date(cur.year + 1, 1, 1)
        else:
            cur = date(cur.year, cur.month + 1, 1)


def _next_month(d: date) -> date:
    return date(d.year + (d.month == 12), 1 if d.month == 12 else d.month + 1, 1)


def _daily_dates(start: date, end: date):
    cur = start
    while cur < end:
        yield cur
        cur += timedelta(days=1)


def fetch(start: datetime, end: datetime):
    collected: dict[datetime, tuple[datetime, float, float, float, float, float]] = {}
    today = datetime.now(timezone.utc).date()
    this_month = date(today.year, today.month, 1)

    for month in _month_starts(start.date(), end.date() + timedelta(days=1)):
        month_end = _next_month(month)
        chunk_start = max(start.date(), month)
        chunk_end = min(end.date() + timedelta(days=1), month_end)

        use_monthly = month < this_month
        monthly_ok = False
        if use_monthly:
            url = f"{BASE}/monthly/klines/{SYMBOL}/{INTERVAL}/{SYMBOL}-{INTERVAL}-{month:%Y-%m}.zip"
            blob = _download_zip(url)
            if blob is not None:
                for row in _parse_zip(blob):
                    if start <= row[0] < end:
                        collected[row[0]] = row
                monthly_ok = True
                print(f"monthly ok {month:%Y-%m}")

        if not monthly_ok:
            for d in _daily_dates(chunk_start, chunk_end):
                if d >= today:
                    continue
                url = f"{BASE}/daily/klines/{SYMBOL}/{INTERVAL}/{SYMBOL}-{INTERVAL}-{d:%Y-%m-%d}.zip"
                blob = _download_zip(url)
                if blob is None:
                    print(f"daily missing {d}")
                    continue
                for row in _parse_zip(blob):
                    if start <= row[0] < end:
                        collected[row[0]] = row
                print(f"daily ok {d}")

    return [collected[k] for k in sorted(collected)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2017-08-17")
    ap.add_argument("--end", required=True, help="exclusive UTC date")
    ap.add_argument("--output", required=True)
    ap.add_argument("--summary", required=True)
    args = ap.parse_args()

    start = datetime.fromisoformat(args.start).replace(tzinfo=timezone.utc)
    end = datetime.fromisoformat(args.end).replace(tzinfo=timezone.utc)
    rows = fetch(start, end)
    if not rows:
        raise SystemExit("no ETHUSDT bars downloaded")

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["time", "open", "high", "low", "close", "volume"])
        for t, o, h, l, c, v in rows:
            w.writerow([t.isoformat(), o, h, l, c, v])

    expected_seconds = 15 * 60
    gaps = []
    for a, b in zip(rows, rows[1:]):
        delta = (b[0] - a[0]).total_seconds()
        if delta > expected_seconds:
            gaps.append({"from": a[0].isoformat(), "to": b[0].isoformat(), "minutes": delta / 60})

    summary = {
        "symbol": SYMBOL,
        "interval": INTERVAL,
        "rows": len(rows),
        "first": rows[0][0].isoformat(),
        "last": rows[-1][0].isoformat(),
        "gaps_over_15m": len(gaps),
        "largest_gaps": sorted(gaps, key=lambda x: x["minutes"], reverse=True)[:20],
    }
    Path(args.summary).write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
