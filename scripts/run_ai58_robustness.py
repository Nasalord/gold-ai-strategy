from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime, time, timezone
from pathlib import Path

from ai_investing_lab.strategies.ai58_usdjpy import AI58Config
from ai_investing_lab.strategies.ai58_usdjpy.csv_runner import load_candles_csv
from ai_investing_lab.strategies.ai58_usdjpy.source_fidelity import SourceFaithfulAI58Backtester

IS_START = datetime(2021, 9, 1, tzinfo=timezone.utc)
IS_END = datetime(2025, 9, 1, tzinfo=timezone.utc)
VIDEO_OOS_END = datetime(2026, 3, 15, tzinfo=timezone.utc)
FRESH_OOS_END = datetime(2026, 9, 14, tzinfo=timezone.utc)


def subset(candles, start, end):
    return [c for c in candles if start <= c.time < end]


def metrics_dict(result):
    return asdict(result.metrics)


def json_safe_overrides(overrides):
    out = {}
    for key, value in overrides.items():
        if isinstance(value, time):
            out[key] = value.isoformat(timespec="minutes")
        else:
            out[key] = value
    return out


def run(candles, cfg):
    return SourceFaithfulAI58Backtester(cfg).run(candles)


def evaluate_variant(candles, label: str, **overrides):
    cfg = AI58Config.optimized_15m(**overrides)
    is_result = run(subset(candles, IS_START, IS_END), cfg)
    video_oos = run(subset(candles, IS_END, VIDEO_OOS_END), cfg)
    fresh_oos = run(subset(candles, VIDEO_OOS_END, FRESH_OOS_END), cfg)
    full_oos = run(subset(candles, IS_END, FRESH_OOS_END), cfg)
    return {
        "label": label,
        "overrides": json_safe_overrides(overrides),
        "in_sample": metrics_dict(is_result),
        "video_oos": metrics_dict(video_oos),
        "fresh_post_video_oos": metrics_dict(fresh_oos),
        "full_oos_since_2025_09_01": metrics_dict(full_oos),
    }


def calendar_years(candles):
    cfg = AI58Config.optimized_15m()
    out = {}
    for year in range(2022, 2027):
        start = datetime(year, 1, 1, tzinfo=timezone.utc)
        end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        if year == 2026:
            end = FRESH_OOS_END
        result = run(subset(candles, start, end), cfg)
        out[str(year)] = metrics_dict(result)
    return out


def main():
    parser = argparse.ArgumentParser(description="AI58 predeclared robustness matrix")
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    candles = load_candles_csv(args.csv_path)
    if not candles:
        raise RuntimeError("no candles loaded")

    # This matrix is fixed in advance. It is not an optimizer and no best row
    # is selected. Every row is reported.
    variants = [
        evaluate_variant(candles, "baseline"),
        evaluate_variant(candles, "slippage_18_ticks", slippage_ticks=18),
        evaluate_variant(candles, "slippage_24_ticks", slippage_ticks=24),
        evaluate_variant(candles, "commission_1p5x", commission_usd_per_standard_lot_per_side=5.25),
        evaluate_variant(candles, "commission_2x", commission_usd_per_standard_lot_per_side=7.00),
        evaluate_variant(candles, "costs_2x", slippage_ticks=24, commission_usd_per_standard_lot_per_side=7.00),
        evaluate_variant(candles, "tdfi_lookback_40", tdfi_lookback=40),
        evaluate_variant(candles, "tdfi_lookback_60", tdfi_lookback=60),
        evaluate_variant(candles, "atr_length_400", trailing_atr_length=400),
        evaluate_variant(candles, "atr_length_500", trailing_atr_length=500),
        evaluate_variant(candles, "atr_multiplier_9", trailing_atr_multiplier=9.0),
        evaluate_variant(candles, "atr_multiplier_13", trailing_atr_multiplier=13.0),
        evaluate_variant(candles, "range_15m_earlier", range_start=time(5, 45), range_end=time(8, 0)),
        evaluate_variant(candles, "range_15m_later", range_start=time(6, 15), range_end=time(8, 30)),
        # Fixed $10k notional on a $10k account: a non-leveraged paper-sim
        # comparison using identical signals/cost assumptions.
        evaluate_variant(candles, "paper_fixed_10k_notional", fixed_notional_usd=10_000.0),
    ]

    baseline = next(v for v in variants if v["label"] == "baseline")
    stressed = next(v for v in variants if v["label"] == "costs_2x")
    fresh = baseline["fresh_post_video_oos"]

    gates = {
        "baseline_video_oos_positive": baseline["video_oos"]["net_profit_pct"] > 0,
        "fresh_post_video_oos_positive": fresh["net_profit_pct"] > 0,
        "fresh_post_video_oos_pf_above_1": fresh["profit_factor"] > 1.0,
        "double_costs_in_sample_positive": stressed["in_sample"]["net_profit_pct"] > 0,
        "double_costs_in_sample_pf_above_1": stressed["in_sample"]["profit_factor"] > 1.0,
        "all_parameter_neighbors_in_sample_positive": all(
            v["in_sample"]["net_profit_pct"] > 0
            for v in variants
            if v["label"] in {
                "tdfi_lookback_40",
                "tdfi_lookback_60",
                "atr_length_400",
                "atr_length_500",
                "atr_multiplier_9",
                "atr_multiplier_13",
                "range_15m_earlier",
                "range_15m_later",
            }
        ),
    }

    payload = {
        "method": "Predeclared symmetric robustness checks; no parameter selection or optimization.",
        "data": {
            "source_file": str(args.csv_path),
            "bars": len(candles),
            "first_bar": candles[0].time.isoformat(),
            "last_bar": candles[-1].time.isoformat(),
        },
        "windows": {
            "in_sample": "2021-09-01 to 2025-09-01",
            "creator_video_oos": "2025-09-01 to 2026-03-15",
            "fresh_post_video_oos": "2026-03-15 to 2026-09-14 (end exclusive)",
        },
        "baseline_year_by_year": calendar_years(candles),
        "gates": gates,
        "all_gates_pass": all(gates.values()),
        "variants": variants,
        "notes": [
            "Creator feed was IC Markets; this robustness run uses independent Dukascopy midpoint OHLC.",
            "The 100/100 fixed-exit disable interpretation is retained from the passing parity run.",
            "No variant is selected as a replacement parameter set; the matrix only measures sensitivity.",
            "The paper_fixed_10k_notional row is fixed-notional paper normalization, not a recommendation or live-trading configuration.",
        ],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, allow_nan=True), encoding="utf-8")
    print(json.dumps({
        "all_gates_pass": payload["all_gates_pass"],
        "gates": gates,
        "baseline": baseline,
        "double_costs": stressed,
        "year_by_year": payload["baseline_year_by_year"],
    }, indent=2, allow_nan=True))


if __name__ == "__main__":
    main()
