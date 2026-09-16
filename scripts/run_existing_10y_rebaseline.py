from __future__ import annotations

import argparse
import json
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path

from ai_investing_lab.strategies.ai8_btc import AI8Config
from ai_investing_lab.strategies.ai2_eth import AI2Config
from ai_investing_lab.strategies.ai38_gbpusd import AI38Config
from ai_investing_lab.strategies.ai58_usdjpy import AI58Config
from ai_investing_lab.strategies.ai58_usdjpy.csv_runner import load_candles_csv as load_ai58
from ai_investing_lab.strategies.ai58_usdjpy.source_fidelity import SourceFaithfulAI58Backtester
from scripts.run_ai8_full_validation import load_csv as load_ai8, run_window as run_ai8, result_summary as summary_ai8
from scripts.run_ai2_full_validation import load_csv as load_ai2, run_window as run_ai2, metric_dict as summary_ai2
from scripts.run_ai38_full_validation import load_csv as load_ai38, metrics_for as summary_ai38
from scripts.run_ai58_deep_history import window_metrics as summary_ai58

UTC = timezone.utc
TARGET_START = datetime(2016, 1, 1, tzinfo=UTC)

CREATOR_WINDOWS = {
    "AI8": (datetime(2020, 3, 1, tzinfo=UTC), datetime(2024, 3, 1, tzinfo=UTC)),
    "AI2": (datetime(2020, 3, 1, tzinfo=UTC), datetime(2024, 3, 1, tzinfo=UTC)),
    "AI38": (datetime(2020, 3, 1, tzinfo=UTC), datetime(2024, 3, 1, tzinfo=UTC)),
    "AI58": (datetime(2021, 9, 1, tzinfo=UTC), datetime(2025, 9, 1, tzinfo=UTC)),
}


def dt(value: str) -> datetime:
    x = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return x if x.tzinfo else x.replace(tzinfo=UTC)


def month_shift(value: datetime, months: int) -> datetime:
    index = value.year * 12 + value.month - 1 + months
    year, month0 = divmod(index, 12)
    day = min(value.day, 28)
    return datetime(year, month0 + 1, day, tzinfo=UTC)


def usable_start(first_bar: datetime, target: datetime = TARGET_START) -> datetime:
    # If the provider starts after 2016, use its earliest trustworthy bar. The
    # strategy engine still must warm its indicators before a trade can occur.
    return max(target, first_bar)


def years_between(start: datetime, end: datetime):
    for year in range(start.year, end.year + 1):
        a = max(start, datetime(year, 1, 1, tzinfo=UTC))
        b = min(end, datetime(year + 1, 1, 1, tzinfo=UTC))
        if a < b:
            yield str(year), a, b


def build_ai8(candles, end: datetime) -> dict:
    start = usable_start(candles[0].time)
    cfg = AI8Config.creator_fixed_cash()
    cost_cfg = AI8Config.creator_fixed_cash(commission_pct_per_side=0.20, slippage_ticks=4)
    creator_start, creator_end = CREATOR_WINDOWS["AI8"]

    def run(a, b, config=cfg):
        return summary_ai8(run_ai8(candles, config, a, b))

    rolling = {}
    for months in (6, 12, 24, 36, 60):
        a = max(start, month_shift(end, -months))
        rolling[str(months)] = run(a, end)

    yearly = {year: run(a, b) for year, a, b in years_between(start, end)}
    return {
        "strategy": "AI8 BTCUSDT 2H",
        "requested_start": TARGET_START.date().isoformat(),
        "available_start": candles[0].time.isoformat(),
        "scored_start": start.isoformat(),
        "end_exclusive": end.isoformat(),
        "coverage_years": (end - start).total_seconds() / (365.25 * 86400),
        "full_history": run(start, end),
        "full_history_2x_costs": run(start, end, cost_cfg),
        "pre_creator": run(start, creator_start),
        "creator_window": run(creator_start, creator_end),
        "post_creator_oos": run(creator_end, end),
        "latest_rolling_months": rolling,
        "calendar_years": yearly,
        "frozen_config": asdict(cfg),
        "note": "Binance Spot BTCUSDT does not provide a 2016 history in this project; the rebaseline starts at the earliest downloaded Binance bar instead.",
    }


def build_ai2(candles, end: datetime) -> dict:
    start = usable_start(candles[0].time)
    cfg = AI2Config.creator_15m()
    cost_cfg = replace(cfg, commission_pct_per_side=0.20, slippage_ticks=4)
    creator_start, creator_end = CREATOR_WINDOWS["AI2"]

    def run(a, b, config=cfg):
        return summary_ai2(run_ai2(candles, config, a, b))

    rolling = {}
    for months in (6, 12, 24, 36, 60):
        a = max(start, month_shift(end, -months))
        rolling[str(months)] = run(a, end)

    yearly = {year: run(a, b) for year, a, b in years_between(start, end)}
    return {
        "strategy": "AI2 ETHUSDT 15m",
        "requested_start": TARGET_START.date().isoformat(),
        "available_start": candles[0].time.isoformat(),
        "scored_start": start.isoformat(),
        "end_exclusive": end.isoformat(),
        "coverage_years": (end - start).total_seconds() / (365.25 * 86400),
        "full_history": run(start, end),
        "full_history_2x_costs": run(start, end, cost_cfg),
        "pre_creator": run(start, creator_start),
        "creator_window": run(creator_start, creator_end),
        "post_creator_oos": run(creator_end, end),
        "latest_rolling_months": rolling,
        "calendar_years": yearly,
        "frozen_config": asdict(cfg),
        "note": "Binance Spot ETHUSDT begins after 2016; the rebaseline therefore uses the earliest available Binance history rather than fabricating earlier data.",
    }


def build_ai38(candles, end: datetime) -> dict:
    start = TARGET_START
    cfg = AI38Config.creator_4h()
    cost_cfg = AI38Config.creator_4h(commission_usd_per_contract_per_side=0.00010, slippage_ticks=40)
    creator_start, creator_end = CREATOR_WINDOWS["AI38"]

    def run(a, b, config=cfg):
        return summary_ai38(candles, config, a, b)

    rolling = {}
    for months in (6, 12, 24, 36, 60):
        rolling[str(months)] = run(month_shift(end, -months), end)

    yearly = {year: run(a, b) for year, a, b in years_between(start, end)}
    return {
        "strategy": "AI38 GBPUSD 4H",
        "requested_start": TARGET_START.date().isoformat(),
        "available_start": candles[0].time.isoformat(),
        "scored_start": start.isoformat(),
        "end_exclusive": end.isoformat(),
        "coverage_years": (end - start).total_seconds() / (365.25 * 86400),
        "full_history": run(start, end),
        "full_history_2x_costs": run(start, end, cost_cfg),
        "pre_creator": run(start, creator_start),
        "creator_window": run(creator_start, creator_end),
        "post_creator_oos": run(creator_end, end),
        "latest_rolling_months": rolling,
        "calendar_years": yearly,
        "frozen_config": asdict(cfg),
        "note": "The repository retains older 2005+ AI38 evidence separately; this standardized comparison scores 2016 onward.",
    }


def build_ai58(candles, end: datetime) -> dict:
    # Feed a full warmup year before the standardized 2016 score boundary.
    selected = [c for c in candles if c.time < end]
    cfg = AI58Config.optimized_15m()
    baseline = SourceFaithfulAI58Backtester(cfg).run(selected)
    cost_cfg = AI58Config.optimized_15m(
        slippage_ticks=24,
        commission_usd_per_standard_lot_per_side=7.0,
    )
    cost_result = SourceFaithfulAI58Backtester(cost_cfg).run(selected)
    creator_start, creator_end = CREATOR_WINDOWS["AI58"]

    def run(trades, a, b):
        return summary_ai58(trades, a, b)

    rolling = {}
    for months in (6, 12, 24, 36, 60):
        rolling[str(months)] = run(baseline.trades, month_shift(end, -months), end)

    yearly = {
        year: run(baseline.trades, a, b)
        for year, a, b in years_between(TARGET_START, end)
    }
    return {
        "strategy": "AI58 USDJPY 15m ORB",
        "requested_start": TARGET_START.date().isoformat(),
        "available_start": candles[0].time.isoformat(),
        "scored_start": TARGET_START.isoformat(),
        "end_exclusive": end.isoformat(),
        "coverage_years": (end - TARGET_START).total_seconds() / (365.25 * 86400),
        "full_history": run(baseline.trades, TARGET_START, end),
        "full_history_2x_costs": run(cost_result.trades, TARGET_START, end),
        "pre_creator": run(baseline.trades, TARGET_START, creator_start),
        "creator_window": run(baseline.trades, creator_start, creator_end),
        "post_creator_oos": run(baseline.trades, creator_end, end),
        "latest_rolling_months": rolling,
        "calendar_years": yearly,
        "frozen_config": asdict(cfg),
        "note": "The repository also has independent AI58 history back to 2011; 2016 onward is used here for the standardized cross-strategy comparison.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Standardize previously validated strategies on the 2016-or-earliest long-history rule")
    ap.add_argument("--btc", type=Path, required=True)
    ap.add_argument("--eth", type=Path, required=True)
    ap.add_argument("--gbp", type=Path, required=True)
    ap.add_argument("--jpy", type=Path, required=True)
    ap.add_argument("--end", required=True, help="exclusive UTC ISO date")
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    end = dt(args.end)
    ai8 = build_ai8(load_ai8(args.btc), end)
    ai2 = build_ai2(load_ai2(str(args.eth)), end)
    ai38 = build_ai38(load_ai38(args.gbp), end)
    ai58 = build_ai58(load_ai58(args.jpy), end)

    report = {
        "rule": "Score from 2016-01-01 to latest where trustworthy history exists; when the provider begins later, use its earliest available history and disclose the limitation. Earlier validated history is retained as additional evidence.",
        "end_exclusive": end.isoformat(),
        "strategies": {"AI8": ai8, "AI2": ai2, "AI38": ai38, "AI58": ai58},
        "EXP6": {
            "status": "coverage limitation",
            "earliest_current_public_continuous_sample": "2023-01-01",
            "note": "EXP6 cannot satisfy the 2016 rule with the currently validated public NQ datasets. Its existing 2023-2025 public history and separate 2026 sample are rerun in the same workflow rather than being stitched into a false continuous series.",
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=True, default=str), encoding="utf-8")

    print("10-year / earliest-available rebaseline")
    for key, row in report["strategies"].items():
        m = row["full_history"]
        c = row["full_history_2x_costs"]
        print(
            f"{key}: {row['scored_start']} -> {row['end_exclusive']} | "
            f"trades={m['trades']} net={m['net_profit_pct']:.2f}% PF={m['profit_factor']:.3f} "
            f"DD={m.get('max_closed_trade_drawdown_pct', m.get('max_drawdown_pct_closed_trade')):.2f}% | "
            f"2x costs net={c['net_profit_pct']:.2f}% PF={c['profit_factor']:.3f}"
        )
    print("EXP6: current trustworthy public coverage starts 2023; long-history gate remains unmet.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
