from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai_investing_lab.strategies.ai65_gold import (
    AI65Backtester,
    AI65Config,
    Candle,
    ExecutionMode,
)
from ai_investing_lab.strategies.ai65_gold.csv_runner import load_candles_csv


def load_tradingview_oanda_csv(
    path: Path,
    *,
    end_exclusive: datetime,
) -> list[Candle]:
    """Load the public TradingView OANDA:XAUUSD H1 export.

    The dataset carries a Unix-epoch ``timestamp`` column and a human-readable
    UTC ``datetime`` column. The epoch is treated as authoritative so timezone
    interpretation is unambiguous.
    """
    candles: list[Candle] = []
    with path.open("r", newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            ts = datetime.fromtimestamp(int(row["timestamp"]), tz=timezone.utc)
            if ts >= end_exclusive:
                break
            candles.append(
                Candle(
                    time=ts,
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                )
            )
    return candles


def metrics_dict(result) -> dict[str, float | int]:
    m = result.metrics
    return {
        "trades": m.trades,
        "net_profit_pct": m.net_profit_pct,
        "profit_factor": m.profit_factor,
        "win_rate_pct": m.win_rate_pct,
        "max_drawdown_pct": m.max_drawdown_pct,
        "ambiguous_trades": m.ambiguous_trades,
    }


def run_mode(candles: list[Candle], mode: ExecutionMode):
    config = AI65Config.video_oanda_1h(execution_mode=mode)
    return AI65Backtester(config).run(candles)


def session_set(result) -> set[str]:
    return {trade.session_date.isoformat() for trade in result.trades}


def compare_sessions(a, b) -> dict[str, object]:
    sa = session_set(a)
    sb = session_set(b)
    union = sa | sb
    return {
        "intersection": len(sa & sb),
        "oanda_only": len(sa - sb),
        "dukascopy_only": len(sb - sa),
        "union": len(union),
        "jaccard": (len(sa & sb) / len(union)) if union else 1.0,
        "oanda_only_dates": sorted(sa - sb),
        "dukascopy_only_dates": sorted(sb - sa),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare AI65 on TradingView OANDA:XAUUSD and Dukascopy overlap"
    )
    parser.add_argument("--oanda-csv", type=Path, required=True)
    parser.add_argument("--dukascopy-csv", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--end", default="2026-03-01T00:00:00+00:00")
    args = parser.parse_args()

    end = datetime.fromisoformat(args.end)
    if end.tzinfo is None:
        raise ValueError("--end must include a UTC offset")

    oanda = load_tradingview_oanda_csv(args.oanda_csv, end_exclusive=end)
    dukascopy = [c for c in load_candles_csv(args.dukascopy_csv) if c.time < end]

    if not oanda or not dukascopy:
        raise ValueError("both feeds must contain candles")

    report: dict[str, object] = {
        "window": {
            "oanda_first_bar": oanda[0].time.isoformat(),
            "oanda_last_bar": oanda[-1].time.isoformat(),
            "dukascopy_first_bar": dukascopy[0].time.isoformat(),
            "dukascopy_last_bar": dukascopy[-1].time.isoformat(),
            "end_exclusive": end.isoformat(),
        },
        "bars": {"oanda": len(oanda), "dukascopy": len(dukascopy)},
        "modes": {},
    }

    for label, mode in (
        ("source_pending_until_next_session", ExecutionMode.REPLICA),
        ("cancel_pending_at_22_ny", ExecutionMode.GUARDED),
    ):
        oanda_result = run_mode(oanda, mode)
        dukascopy_result = run_mode(dukascopy, mode)
        report["modes"][label] = {
            "oanda": metrics_dict(oanda_result),
            "dukascopy": metrics_dict(dukascopy_result),
            "trade_session_overlap": compare_sessions(oanda_result, dukascopy_result),
        }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=True), encoding="utf-8")
    print(json.dumps(report, indent=2, allow_nan=True))


if __name__ == "__main__":
    main()
