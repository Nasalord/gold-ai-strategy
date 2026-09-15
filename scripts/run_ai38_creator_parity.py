from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from ai_investing_lab.strategies.ai38_gbpusd import AI38Backtester, AI38Config, Candle

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
            ))
    return sorted(out, key=lambda c: c.time)


def summarize(result):
    closed = [t for t in result.trades if t.closed]
    return {
        "metrics": asdict(result.metrics),
        "long_trades": sum(t.side.value == "long" for t in closed),
        "short_trades": sum(t.side.value == "short" for t in closed),
        "stop_exits": sum(t.exit_reason and t.exit_reason.value == "stop" for t in closed),
        "target_exits": sum(t.exit_reason and t.exit_reason.value == "target" for t in closed),
        "open_at_end": sum(not t.closed for t in result.trades),
    }


def parity_score(metrics: dict) -> float:
    # Predeclared comparison score only for diagnosing feed/alignment; it does
    # not alter strategy parameters.
    return (
        abs(metrics["trades"] - 94) / 94.0
        + abs(metrics["net_profit_pct"] - 217.06) / 217.06
        + abs(metrics["profit_factor"] - 1.845) / 1.845
        + abs(metrics["win_rate_pct"] - 39.36) / 39.36
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="AI38 GBPUSD creator-window parity matrix")
    ap.add_argument("data_dir", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    variants = {}
    for side in ("bid", "ask", "mid"):
        for offset in range(4):
            path = args.data_dir / f"gbpusd_{side}_4h_offset{offset}.csv"
            candles = load_csv(path)
            for exact_start in (False, True):
                name = f"{side}_offset{offset}_{'exact_start' if exact_start else 'warmup'}"
                data = [c for c in candles if c.time >= TRADE_START] if exact_start else candles
                result = AI38Backtester(AI38Config.creator_4h()).run(
                    data,
                    trade_start=TRADE_START,
                    trade_end=TRADE_END,
                )
                summary = summarize(result)
                summary["parity_score"] = parity_score(summary["metrics"])
                summary["bars"] = len(data)
                variants[name] = summary

    ranked = sorted(variants, key=lambda k: variants[k]["parity_score"])
    payload = {
        "benchmark": {
            "asset": "GBPUSD",
            "timeframe": "4H",
            "start": "2020-03-01",
            "end": "2024-03-01",
            "trades": 94,
            "net_profit_pct": 217.06,
            "profit_factor": 1.845,
            "win_rate_pct": 39.36,
            "max_drawdown_pct": 19.56,
            "initial_capital_usd": 10000.0,
            "fixed_units": 100000.0,
            "commission_usd_per_contract_per_side": 0.00005,
            "slippage_ticks": 20,
        },
        "source_settings": asdict(AI38Config.creator_4h()),
        "variants": variants,
        "ranked_alignment_feed_diagnostics": ranked,
        "best_diagnostic_match": ranked[0] if ranked else None,
        "principle": "All strategy parameters are frozen. Only independent feed side, legitimate UTC 4H bar alignment, and calculation warmup are varied as predeclared platform diagnostics.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, allow_nan=True), encoding="utf-8")
    if ranked:
        print("Best diagnostic match:", ranked[0])
        print(json.dumps(variants[ranked[0]], indent=2, allow_nan=True))
    print("Top 8:")
    for name in ranked[:8]:
        m = variants[name]["metrics"]
        print(name, "score=", round(variants[name]["parity_score"], 4), "trades=", m["trades"], "net=", round(m["net_profit_pct"], 3), "pf=", round(m["profit_factor"], 4), "win=", round(m["win_rate_pct"], 3), "dd=", round(m["max_closed_trade_drawdown_pct"], 3))


if __name__ == "__main__":
    main()
