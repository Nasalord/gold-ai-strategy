from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from ai_investing_lab.strategies.ai8_btc import (
    AI8Backtester,
    AI8Config,
    Candle,
    evaluate_creator_parity,
)


def parse_iso(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def load_csv(path: Path) -> list[Candle]:
    out: list[Candle] = []
    with path.open("r", newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            out.append(
                Candle(
                    time=parse_iso(row["timestamp"]),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                )
            )
    return out


def metrics_dict(result) -> dict[str, object]:
    m = result.metrics
    return {
        "trades": m.trades,
        "wins": m.wins,
        "losses": m.losses,
        "win_rate_pct": m.win_rate_pct,
        "net_profit_usd": m.net_profit_usd,
        "net_profit_pct": m.net_profit_pct,
        "profit_factor": m.profit_factor,
        "max_closed_trade_drawdown_pct": m.max_closed_trade_drawdown_pct,
        "max_intrabar_drawdown_pct": m.max_intrabar_drawdown_pct,
        "ambiguous_trades": m.ambiguous_trades,
    }


def exit_counts(result) -> dict[str, int]:
    counts: dict[str, int] = {}
    for trade in result.trades:
        if trade.exit_reason is None:
            continue
        key = trade.exit_reason.value
        counts[key] = counts.get(key, 0) + 1
    return counts


def trade_rows(result) -> list[dict[str, object]]:
    rows = []
    for t in result.trades:
        rows.append(
            {
                "signal_time": t.signal_time.isoformat(),
                "entry_time": t.entry_time.isoformat(),
                "entry_price": t.entry_price,
                "quantity_btc": t.quantity_btc,
                "entry_notional_usd": t.entry_notional_usd,
                "equity_at_signal_usd": t.equity_at_signal_usd,
                "stop_price": t.stop_price,
                "target_price": t.target_price,
                "entry_commission_usd": t.entry_commission_usd,
                "exit_time": t.exit_time.isoformat() if t.exit_time else None,
                "exit_price": t.exit_price,
                "exit_reason": t.exit_reason.value if t.exit_reason else None,
                "exit_commission_usd": t.exit_commission_usd,
                "gross_pnl_usd": t.gross_pnl_usd,
                "net_pnl_usd": t.net_pnl_usd,
                "ambiguous_same_bar": t.ambiguous_same_bar,
            }
        )
    return rows


def run_variant(candles, config, start, end):
    result = AI8Backtester(config).run(
        candles,
        trade_start=start,
        trade_end=end,
        close_at_end=False,
    )
    return {
        "config": asdict(config),
        "metrics": metrics_dict(result),
        "exit_counts": exit_counts(result),
        "creator_parity": evaluate_creator_parity(result.metrics),
        "trades": trade_rows(result),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="AI8 independent Binance creator-parity test")
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    candles = load_csv(args.csv_path)
    start = datetime(2020, 3, 1, tzinfo=timezone.utc)

    boundaries = {
        "end_exclusive_2024_03_01": datetime(2024, 3, 1, tzinfo=timezone.utc),
        "include_2024_03_01": datetime(2024, 3, 2, tzinfo=timezone.utc),
    }

    variants = {}
    for boundary_name, end in boundaries.items():
        variants[f"video_verified_fixed_80k_pyr7__{boundary_name}"] = run_variant(
            candles, AI8Config.creator_video(), start, end
        )
        variants[f"percent_equity_80_pyr7_control__{boundary_name}"] = run_variant(
            candles, AI8Config.creator_percent_equity(), start, end
        )
        variants[f"pine_default_15pct_pyr1_control__{boundary_name}"] = run_variant(
            candles, AI8Config.pine_source_default(), start, end
        )

    payload = {
        "method": (
            "Exact creator-linked Pine signal inputs plus creator-video-verified TradingView Properties: "
            "$100k initial capital, fixed $80k cash per entry, pyramiding 7, 0.1% commission on each "
            "entry and exit, 2 ticks slippage, long only. For strategy.cash, quantity is derived from "
            "the signal-bar close and percentage commission is applied to actual filled transaction value. "
            "Independent Binance Vision BTCUSDT 2h bars. No indicator or execution parameter search."
        ),
        "creator_benchmark": {
            "asset": "BTCUSDT",
            "timeframe": "2h",
            "backtest_interval": "2020-03-01 to 2024-03-01",
            "trades": 319,
            "net_profit_pct": 637.97,
            "profit_factor": 1.969,
            "win_rate_pct": 44.51,
            "max_drawdown_pct": 27.87,
            "initial_capital_usd": 100000,
            "fixed_cash_per_entry_usd": 80000,
            "pyramiding": 7,
            "commission_pct_each_entry_exit": 0.1,
            "slippage_ticks": 2,
        },
        "variants": variants,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, allow_nan=True), encoding="utf-8")

    compact = {
        name: {
            "metrics": item["metrics"],
            "parity_pass": item["creator_parity"]["passed"],
            "parity_checks": item["creator_parity"]["checks"],
            "exit_counts": item["exit_counts"],
        }
        for name, item in variants.items()
    }
    print(json.dumps(compact, indent=2, allow_nan=True))


if __name__ == "__main__":
    main()
