from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ai_investing_lab.strategies.ai8_btc import AI8Backtester, AI8Config, Candle


def parse_iso(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


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
            ))
    return out


def m(result) -> dict[str, float | int]:
    x = result.metrics
    return {
        "trades": x.trades,
        "wins": x.wins,
        "losses": x.losses,
        "win_rate_pct": x.win_rate_pct,
        "net_profit_pct": x.net_profit_pct,
        "profit_factor": x.profit_factor,
        "closed_trade_drawdown_pct": x.max_closed_trade_drawdown_pct,
        "intrabar_drawdown_pct": x.max_intrabar_drawdown_pct,
        "ambiguous_trades": x.ambiguous_trades,
    }


def run(candles: list[Candle], warmup_days: int | None, percent_equity: bool = False) -> dict[str, object]:
    start = datetime(2020, 3, 1, tzinfo=timezone.utc)
    end = datetime(2024, 3, 1, tzinfo=timezone.utc)
    calc_start = candles[0].time if warmup_days is None else start - timedelta(days=warmup_days)
    subset = [c for c in candles if calc_start <= c.time < end]
    cfg = AI8Config.creator_percent_equity() if percent_equity else AI8Config.creator_fixed_cash()
    result = AI8Backtester(cfg).run(subset, trade_start=start, trade_end=end, close_at_end=False)
    return {
        "calculation_start": calc_start.isoformat(),
        "bars_supplied": len(subset),
        "sizing": "80% equity control" if percent_equity else "fixed $80K creator-video interpretation",
        "metrics": m(result),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_path", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    candles = load_csv(args.csv_path)

    variants = {
        "deep_backtest_exact_start_0d": run(candles, 0),
        "warmup_30d": run(candles, 30),
        "warmup_60d": run(candles, 60),
        "warmup_90d": run(candles, 90),
        "warmup_180d": run(candles, 180),
        "warmup_365d": run(candles, 365),
        "all_available_prehistory": run(candles, None),
        "deep_start_80pct_equity_control": run(candles, 0, percent_equity=True),
        "365d_80pct_equity_control": run(candles, 365, percent_equity=True),
    }
    payload = {
        "benchmark": {"trades": 319, "net_profit_pct": 637.97, "profit_factor": 1.969, "win_rate_pct": 44.51, "max_drawdown_pct": 27.87},
        "platform_note": "TradingView documents that custom Deep Backtesting calculations start at the beginning of the selected date range; recursive EMA/RMA values may differ from regular chart backtests.",
        "variants": variants,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, allow_nan=True), encoding="utf-8")
    print(json.dumps({k: v["metrics"] for k, v in variants.items()}, indent=2, allow_nan=True))


if __name__ == "__main__":
    main()
