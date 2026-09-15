from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from ai_investing_lab.strategies.triple_macd_nq import (
    Candle,
    TripleMACDNQBacktester,
    TripleMACDNQConfig,
)


def _parse_time(raw: str) -> datetime:
    value = raw.strip()
    try:
        number = float(value)
    except ValueError:
        number = None
    if number is not None:
        # Accept epoch seconds, milliseconds, microseconds, or nanoseconds.
        mag = abs(number)
        if mag > 1e17:
            number /= 1e9
        elif mag > 1e14:
            number /= 1e6
        elif mag > 1e11:
            number /= 1e3
        return datetime.fromtimestamp(number, tz=timezone.utc).replace(tzinfo=None)
    text = value.replace("Z", "+00:00")
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def load_csv(path: Path) -> list[Candle]:
    aliases = {
        "time": ("time", "timestamp", "datetime", "date", "window_start"),
        "open": ("open", "o"),
        "high": ("high", "h"),
        "low": ("low", "l"),
        "close": ("close", "c"),
        "volume": ("volume", "v"),
    }
    with path.open("r", newline="", encoding="utf-8-sig") as fh:
        rows = csv.DictReader(fh)
        if rows.fieldnames is None:
            raise ValueError("CSV requires a header row")
        lookup = {name.lower().strip(): name for name in rows.fieldnames}

        def col(key: str, *, required: bool = True) -> str | None:
            for candidate in aliases[key]:
                if candidate in lookup:
                    return lookup[candidate]
            if required:
                raise ValueError(f"missing {key} column; found {rows.fieldnames}")
            return None

        time_col = col("time")
        open_col = col("open")
        high_col = col("high")
        low_col = col("low")
        close_col = col("close")
        volume_col = col("volume", required=False)
        out: list[Candle] = []
        for row in rows:
            out.append(
                Candle(
                    time=_parse_time(row[time_col]),
                    open=float(row[open_col]),
                    high=float(row[high_col]),
                    low=float(row[low_col]),
                    close=float(row[close_col]),
                    volume=float(row[volume_col]) if volume_col and row.get(volume_col) else 0.0,
                )
            )
    return sorted(out, key=lambda x: x.time)


def parse_dt(value: str | None) -> datetime | None:
    return _parse_time(value) if value else None


def main() -> None:
    ap = argparse.ArgumentParser(description="Paper-only Triple MACD NQ1! 10m validation")
    ap.add_argument("csv", type=Path, help="10-minute continuous NQ OHLCV CSV")
    ap.add_argument("--start", help="trade-window start; earlier bars remain available for warmup")
    ap.add_argument("--end", help="exclusive trade-window end")
    ap.add_argument("--order-cash", type=float, default=8_500_000.0)
    ap.add_argument("--initial-capital", type=float, default=1_000_000.0)
    ap.add_argument("--fractional-contracts", action="store_true")
    ap.add_argument("--close-at-end", action="store_true")
    args = ap.parse_args()

    candles = load_csv(args.csv)
    cfg = TripleMACDNQConfig.creator_nq_10m(
        order_cash_usd=args.order_cash,
        initial_capital_usd=args.initial_capital,
        allow_fractional_contracts=args.fractional_contracts,
    )
    result = TripleMACDNQBacktester(cfg).run(
        candles,
        trade_start=parse_dt(args.start),
        trade_end=parse_dt(args.end),
        close_at_end=args.close_at_end,
    )
    m = result.metrics
    print(json.dumps({
        "status": "RESEARCH_ONLY",
        "bars": len(candles),
        "first_bar": candles[0].time.isoformat() if candles else None,
        "last_bar": candles[-1].time.isoformat() if candles else None,
        "trades": m.trades,
        "wins": m.wins,
        "losses": m.losses,
        "win_rate_pct": m.win_rate_pct,
        "net_profit_usd": m.net_profit_usd,
        "net_profit_pct": m.net_profit_pct,
        "profit_factor": m.profit_factor,
        "max_closed_trade_drawdown_pct": m.max_closed_trade_drawdown_pct,
        "note": "Do not promote until creator-period parity and continuous-futures roll parity are resolved.",
    }, indent=2, allow_nan=True))


if __name__ == "__main__":
    main()
