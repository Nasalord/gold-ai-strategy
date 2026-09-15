from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai_investing_lab.strategies.ai65_gold import (
    AI65Backtester,
    AI65Config,
    ExecutionMode,
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
    parser = argparse.ArgumentParser(
        description="Run the reusable AI65 engine under the OANDA/video working hypothesis"
    )
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    candles = load_candles_csv(args.csv_path)

    configs = {
        "video_oanda_replica_cutoff": AI65Config.video_oanda_1h(),
        # Compare a hard 22:00 pending-order cutoff because the video describes
        # a forced end-of-day exit while the uploaded base source leaves an
        # unfilled pending order alive. This is a diagnostic comparison, not
        # parameter optimization.
        "video_oanda_hard_cutoff": AI65Config.video_oanda_1h(
            execution_mode=ExecutionMode.GUARDED
        ),
        "video_oanda_zero_costs": AI65Config.video_oanda_1h(
            slippage_ticks=0,
            commission_per_contract_per_side=0.0,
        ),
    }

    payload = {"benchmark": BENCHMARK, "engine": {}}
    for name, cfg in configs.items():
        result = AI65Backtester(cfg).run(candles)
        payload["engine"][name] = metrics_dict(result)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
