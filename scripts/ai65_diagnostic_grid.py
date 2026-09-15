from __future__ import annotations

import argparse
import json
import sys
from datetime import time
from pathlib import Path

# Allow direct execution as `python scripts/ai65_diagnostic_grid.py ...`
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai_investing_lab.strategies.ai65_gold import (
    AI65Backtester,
    AI65Config,
    TDFIGating,
)
from ai_investing_lab.strategies.ai65_gold.csv_runner import load_candles_csv


BENCHMARK = {
    "trades": 670,
    "net_profit_pct": 552.94,
    "profit_factor": 1.667,
    "win_rate_pct": 52.69,
    "max_drawdown_pct": 25.73,
}


def metrics_dict(result):
    m = result.metrics
    return {
        "trades": m.trades,
        "net_profit_pct": m.net_profit_pct,
        "profit_factor": m.profit_factor,
        "win_rate_pct": m.win_rate_pct,
        "max_drawdown_pct": m.max_drawdown_pct,
        "ambiguous_trades": m.ambiguous_trades,
        "trade_count_diff": m.trades - BENCHMARK["trades"],
        "win_rate_diff_pp": m.win_rate_pct - BENCHMARK["win_rate_pct"],
        "profit_factor_diff": m.profit_factor - BENCHMARK["profit_factor"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="AI65 source-semantics diagnostic grid")
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    candles = load_candles_csv(args.csv_path)

    variants: list[tuple[str, dict]] = [
        ("baseline_ny_arm_tdfi", {}),
        ("tdfi_entry_time_plus_arm", {"tdfi_gating": TDFIGating.ENTRY_TIME}),
        ("tdfi_off", {"use_tdfi": False}),
        ("tdfi_threshold_-0.10", {"tdfi_long_threshold": -0.10}),
        ("tdfi_threshold_-0.075", {"tdfi_long_threshold": -0.075}),
        ("tdfi_threshold_-0.025", {"tdfi_long_threshold": -0.025}),
        ("tdfi_threshold_0.00", {"tdfi_long_threshold": 0.0}),
        ("range_10_12_ny", {"range_start": time(10, 0), "range_end": time(12, 0)}),
        ("range_12_14_ny", {"range_start": time(12, 0), "range_end": time(14, 0)}),
        ("force_exit_21_ny", {"force_exit": time(21, 0)}),
        ("force_exit_23_ny", {"force_exit": time(23, 0)}),
        ("fixed_utc_minus4", {"timezone": "Etc/GMT+4"}),
        ("fixed_utc_minus5", {"timezone": "Etc/GMT+5"}),
        ("pine_literal_target_12.54x", {"target_mult": 3.8 * 3.3}),
        ("zero_costs", {"slippage_ticks": 0, "commission_per_contract_per_side": 0.0}),
    ]

    output = {"benchmark": BENCHMARK, "variants": {}}
    for name, overrides in variants:
        cfg = AI65Config.creator_1h(**overrides)
        result = AI65Backtester(cfg).run(candles)
        output["variants"][name] = metrics_dict(result)
        print(name, json.dumps(output["variants"][name], sort_keys=True))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
