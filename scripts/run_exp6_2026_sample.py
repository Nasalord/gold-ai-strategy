from __future__ import annotations

import argparse
import csv
import io
import json
import urllib.request
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from ai_investing_lab.strategies.triple_macd_nq.config import TripleMACDNQConfig
from ai_investing_lab.strategies.triple_macd_nq.engine import Candle, TripleMACDNQBacktester
from scripts.run_exp6_public_nq_parity import metric_dict, write_trades

UTC = timezone.utc
URL = "https://raw.githubusercontent.com/getdata-finance/nq-1m-ohlcv-stocks-historical-data/main/NQ_1m.csv"


def parse_dt(value: str) -> datetime:
    s = value.strip().replace("Z", "+00:00")
    for candidate in (s, s.replace(" ", "T", 1)):
        try:
            d = datetime.fromisoformat(candidate)
            return d.replace(tzinfo=UTC) if d.tzinfo is None else d.astimezone(UTC)
        except ValueError:
            pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=UTC)
        except ValueError:
            pass
    raise ValueError(f"unsupported datetime: {value!r}")


def download_rows() -> tuple[list[tuple[datetime,float,float,float,float,float]], list[str]]:
    req = urllib.request.Request(URL, headers={"User-Agent": "ai-investing-lab-exp6"})
    with urllib.request.urlopen(req, timeout=60) as r:
        text = r.read().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    headers = [h.strip() for h in (reader.fieldnames or [])]
    norm = {h.lower().strip(): h for h in headers}
    dt_col = next((norm[k] for k in ("datetime", "timestamp", "time", "date") if k in norm), None)
    needed = {k: norm.get(k) for k in ("open", "high", "low", "close", "volume")}
    if dt_col is None or any(v is None for v in needed.values()):
        raise RuntimeError(f"unexpected columns: {headers}")
    rows = []
    for row in reader:
        try:
            rows.append((
                parse_dt(row[dt_col]),
                float(row[needed["open"]]), float(row[needed["high"]]),
                float(row[needed["low"]]), float(row[needed["close"]]),
                float(row[needed["volume"]]),
            ))
        except (ValueError, TypeError, KeyError):
            continue
    rows.sort(key=lambda x: x[0])
    return rows, headers


def resample(rows):
    buckets = {}
    for t,o,h,l,c,v in rows:
        ts = int(t.timestamp())
        bts = ts - ts % 600
        if bts not in buckets:
            buckets[bts] = [o,h,l,c,v]
        else:
            b = buckets[bts]
            b[1] = max(b[1], h); b[2] = min(b[2], l); b[3] = c; b[4] += v
    return [Candle(datetime.fromtimestamp(ts, tz=UTC), *vals) for ts, vals in sorted(buckets.items())]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trade-start", default="2026-04-01")
    ap.add_argument("--trade-end", default="2026-09-03")
    ap.add_argument("--out-dir", default="exp6_2026_sample")
    args = ap.parse_args()
    out = Path(args.out_dir); out.mkdir(parents=True, exist_ok=True)

    rows, headers = download_rows()
    candles = resample(rows)
    start = datetime.fromisoformat(args.trade_start).replace(tzinfo=UTC)
    end = datetime.fromisoformat(args.trade_end).replace(tzinfo=UTC)
    base = TripleMACDNQConfig.creator_nq_10m()
    cases = {
        "creator_8_5m": base,
        "four_million": replace(base, order_cash_usd=4_000_000.0),
        "one_million_normalized": replace(base, order_cash_usd=1_000_000.0),
        "creator_8_5m_2x_costs": replace(base, commission_usd_per_contract_per_order=5.0, slippage_ticks=10),
    }
    results = {}
    for name,cfg in cases.items():
        r = TripleMACDNQBacktester(cfg).run(candles, trade_start=start, trade_end=end, close_at_end=False)
        results[name] = r
        m = metric_dict(r)
        print(f"{name:26s} trades={m['trades']:3d} net={m['net_profit_pct']:8.3f}% PF={m['profit_factor']:.4f} win={m['win_rate_pct']:.2f}% DD={m['max_closed_trade_drawdown_pct']:.2f}%")
        write_trades(out / f"trades_{name}.csv", r)

    metrics = {k: metric_dict(v) for k,v in results.items()}
    report = {
        "experiment": "EXP6 Triple MACD NQ 10m",
        "status": "INDEPENDENT 2026 PUBLIC-SAMPLE OOS — PARAMETERS FROZEN",
        "source": {
            "repository": "getdata-finance/nq-1m-ohlcv-stocks-historical-data",
            "url": URL,
            "headers": headers,
            "minute_rows": len(rows),
            "ten_minute_bars": len(candles),
            "first_minute": rows[0][0].isoformat() if rows else None,
            "last_minute": rows[-1][0].isoformat() if rows else None,
        },
        "window": {"start": args.trade_start, "end": args.trade_end},
        "metrics": metrics,
        "notes": [
            "This dataset is independent from both TradingView and the 2022-2025 public dataset used in earlier EXP6 diagnostics.",
            "No strategy parameters were changed after observing 2025 OOS.",
            "Results are research/paper-only and are not live-trade instructions.",
        ],
    }
    (out / "exp6_2026_sample.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = ["# Experiment 6 — independent 2026 NQ sample", "", "Parameters frozen before this window.", "", "| Case | Trades | Win % | Net % | PF | Closed DD % |", "|---|---:|---:|---:|---:|---:|"]
    for name,m in metrics.items():
        lines.append(f"| {name} | {m['trades']} | {m['win_rate_pct']:.2f} | {m['net_profit_pct']:.3f} | {m['profit_factor']:.3f} | {m['max_closed_trade_drawdown_pct']:.2f} |")
    (out / "EXP6_2026_SAMPLE.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
