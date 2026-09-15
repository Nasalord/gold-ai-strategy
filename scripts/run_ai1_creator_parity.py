from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from ai_investing_lab.strategies.ai1_btc import AI1Backtester, AI1Config, Candle

UTC = timezone.utc
TRADE_START = datetime(2020, 3, 1, tzinfo=UTC)
TRADE_END = datetime(2024, 3, 1, tzinfo=UTC)


def parse_iso(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def load_csv(path: Path) -> list[Candle]:
    out: list[Candle] = []
    with path.open("r", newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            out.append(Candle(
                time=parse_iso(row["timestamp"]),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row.get("volume") or 0.0),
            ))
    return sorted(out, key=lambda c: c.time)


def summarize(result):
    closed = [t for t in result.trades if t.closed]
    counts: dict[str, int] = {}
    longs = 0
    shorts = 0
    for t in closed:
        longs += t.side.value == "long"
        shorts += t.side.value == "short"
        if t.exit_reason:
            counts[t.exit_reason.value] = counts.get(t.exit_reason.value, 0) + 1
    return {
        "metrics": asdict(result.metrics),
        "exit_counts": counts,
        "long_trades": longs,
        "short_trades": shorts,
        "open_at_end": len([t for t in result.trades if not t.closed]),
    }


def run_variant(candles: list[Candle], name: str, exact_start: bool = False):
    cfg = AI1Config.creator_10m()
    data = [c for c in candles if c.time >= TRADE_START] if exact_start else candles
    result = AI1Backtester(cfg).run(data, trade_start=TRADE_START, trade_end=TRADE_END)
    return {"name": name, **summarize(result)}


def main() -> None:
    ap = argparse.ArgumentParser(description="AI1 creator-window parity")
    ap.add_argument("csv_path", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    candles = load_csv(args.csv_path)
    if not candles:
        raise RuntimeError("no candles loaded")

    payload = {
        "benchmark": {
            "asset": "BTCUSDT",
            "timeframe": "10m",
            "start": "2020-03-01",
            "end": "2024-03-01",
            "trades": 455,
            "net_profit_pct": 1863.0,
            "profit_factor": 1.59,
            "win_rate_pct": 34.07,
            "max_drawdown_pct": 24.42,
            "position_notional_usd": 100000.0,
            "initial_capital_usd": 10000.0,
            "commission_pct_per_side": 0.1,
            "slippage_ticks": 2,
        },
        "source_settings": asdict(AI1Config.creator_10m()),
        "data": {
            "bars": len(candles),
            "first": candles[0].time.isoformat(),
            "last": candles[-1].time.isoformat(),
        },
        "variants": {
            "prehistory_warmup": run_variant(candles, "prehistory_warmup", exact_start=False),
            "calculation_starts_2020_03_01": run_variant(candles, "calculation_starts_2020_03_01", exact_start=True),
        },
        "principle": "No strategy parameter is optimized. The only first-pass platform control is whether recursive calculations include prehistory before the creator test window.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, allow_nan=True), encoding="utf-8")
    print(json.dumps(payload["variants"], indent=2, allow_nan=True))


if __name__ == "__main__":
    main()
