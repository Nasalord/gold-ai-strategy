from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from ai_investing_lab.strategies.ai58_usdjpy import (
    AI58Config,
    VideoBenchmark,
    VideoOOSBenchmark,
    evaluate_video_parity,
)
from ai_investing_lab.strategies.ai58_usdjpy.csv_runner import load_candles_csv, trade_dict
from ai_investing_lab.strategies.ai58_usdjpy.source_fidelity import SourceFaithfulAI58Backtester


IS_START = datetime(2021, 9, 1, tzinfo=timezone.utc)
IS_END = datetime(2025, 9, 1, tzinfo=timezone.utc)
OOS_START = IS_END
OOS_END = datetime(2026, 3, 15, tzinfo=timezone.utc)  # includes Mar 14 calendar day


def subset(candles, start, end):
    return [c for c in candles if start <= c.time < end]


def metrics_dict(metrics):
    return asdict(metrics)


def oos_compare(metrics):
    b = VideoOOSBenchmark()
    return {
        "observed": metrics_dict(metrics),
        "benchmark": asdict(b),
        "deltas": {
            "trades": metrics.trades - b.trades,
            "net_profit_pct": metrics.net_profit_pct - b.net_profit_pct,
            "profit_factor": metrics.profit_factor - b.profit_factor,
            "win_rate_pct": metrics.win_rate_pct - b.win_rate_pct,
            "max_drawdown_pct": metrics.max_drawdown_pct - b.max_drawdown_pct,
        },
    }


def run_variant(candles, *, stop_mult, tp_rr, label):
    cfg = AI58Config.optimized_15m(stop_mult=stop_mult, tp_rr=tp_rr)
    bt = SourceFaithfulAI58Backtester(cfg)

    is_result = bt.run(subset(candles, IS_START, IS_END))
    oos_result = bt.run(subset(candles, OOS_START, OOS_END))

    return {
        "label": label,
        "fixed_exit_hypothesis": {
            "stop_mult": stop_mult,
            "tp_rr": tp_rr,
        },
        "engine_semantics": "uploaded Pine flat requirement enforced on range pre-arm",
        "config": {
            "timezone": cfg.timezone,
            "range_start": cfg.range_start.isoformat(timespec="minutes"),
            "range_end": cfg.range_end.isoformat(timespec="minutes"),
            "direction": cfg.direction.value,
            "use_tdfi": cfg.use_tdfi,
            "tdfi_lookback": cfg.tdfi_lookback,
            "tdfi_high": cfg.tdfi_filter_high,
            "tdfi_low": cfg.tdfi_filter_low,
            "use_trailing_atr": cfg.use_trailing_atr,
            "atr_length": cfg.trailing_atr_length,
            "atr_multiplier": cfg.trailing_atr_multiplier,
            "slippage_ticks": cfg.slippage_ticks,
            "min_tick": cfg.min_tick,
            "commission_per_standard_lot_per_side_usd": cfg.commission_usd_per_standard_lot_per_side,
            "fixed_notional_usd": cfg.fixed_notional_usd,
        },
        "in_sample": {
            "window": "2021-09-01 to 2025-09-01 (end exclusive)",
            "metrics": metrics_dict(is_result.metrics),
            "video_parity": evaluate_video_parity(is_result.metrics),
            "trade_log": [trade_dict(t) for t in is_result.trades],
        },
        "out_of_sample": {
            "window": "2025-09-01 to 2026-03-15 (includes Mar 14)",
            "metrics": metrics_dict(oos_result.metrics),
            "video_comparison": oos_compare(oos_result.metrics),
            "trade_log": [trade_dict(t) for t in oos_result.trades],
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    candles = load_candles_csv(args.csv_path)
    if not candles:
        raise RuntimeError("no candles loaded")

    variants = [
        run_variant(candles, stop_mult=100.0, tp_rr=100.0, label="asr_100_100_trailing_only_hypothesis"),
        run_variant(candles, stop_mult=1.0, tp_rr=1.0, label="literal_asr_1_1_control"),
    ]

    summary = {
        "source_file": str(args.csv_path),
        "bars_loaded": len(candles),
        "first_bar": candles[0].time.isoformat(),
        "last_bar": candles[-1].time.isoformat(),
        "creator_video_in_sample_benchmark": asdict(VideoBenchmark()),
        "creator_video_oos_benchmark": asdict(VideoOOSBenchmark()),
        "important_limitations": [
            "Creator used IC Markets; this run uses an independent feed.",
            "Creator enabled TradingView Bar Magnifier; this first-pass engine evaluates 15m OHLC without lower-timeframe magnifier data.",
            "TradingView max drawdown can use intrabar mark-to-market logic; current engine reports closed-trade equity drawdown.",
            "100/100 fixed exits are a transcript-ASR resolution hypothesis, not screenshot-verified inputs.",
        ],
        "variants": variants,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, allow_nan=True), encoding="utf-8")

    concise = {
        "source_file": summary["source_file"],
        "bars_loaded": summary["bars_loaded"],
        "variants": [
            {
                "label": v["label"],
                "in_sample_metrics": v["in_sample"]["metrics"],
                "in_sample_parity": v["in_sample"]["video_parity"],
                "oos_metrics": v["out_of_sample"]["metrics"],
                "oos_comparison": v["out_of_sample"]["video_comparison"],
            }
            for v in variants
        ],
    }
    print(json.dumps(concise, indent=2, allow_nan=True))


if __name__ == "__main__":
    main()
