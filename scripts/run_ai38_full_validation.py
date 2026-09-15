from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from ai_investing_lab.strategies.ai38_gbpusd import AI38Backtester, AI38Config, Candle

UTC = timezone.utc
BACKLOG_START = datetime(2005, 1, 1, tzinfo=UTC)
CREATOR_START = datetime(2020, 3, 1, tzinfo=UTC)
CREATOR_END = datetime(2024, 3, 1, tzinfo=UTC)
OOS_END = datetime(2026, 9, 15, tzinfo=UTC)

WINDOWS = {
    "backlog_2005_to_creator": (BACKLOG_START, CREATOR_START),
    "creator_2020_03_to_2024_03": (CREATOR_START, CREATOR_END),
    "oos_2024_03_to_2026_09": (CREATOR_END, OOS_END),
    "oos_year1_2024_03_to_2025_03": (CREATOR_END, datetime(2025, 3, 1, tzinfo=UTC)),
    "oos_year2_2025_03_to_2026_03": (datetime(2025, 3, 1, tzinfo=UTC), datetime(2026, 3, 1, tzinfo=UTC)),
    "recent_2026_03_to_2026_09": (datetime(2026, 3, 1, tzinfo=UTC), OOS_END),
    "rolling_6m": (datetime(2026, 3, 15, tzinfo=UTC), OOS_END),
    "rolling_12m": (datetime(2025, 9, 15, tzinfo=UTC), OOS_END),
    "rolling_24m": (datetime(2024, 9, 15, tzinfo=UTC), OOS_END),
    "full_2005_to_2026": (BACKLOG_START, OOS_END),
}


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


def metrics_for(candles: list[Candle], cfg: AI38Config, start: datetime, end: datetime) -> dict:
    result = AI38Backtester(cfg).run(candles, trade_start=start, trade_end=end)
    closed = [t for t in result.trades if t.closed]
    return {
        **asdict(result.metrics),
        "long_trades": sum(t.side.value == "long" for t in closed),
        "short_trades": sum(t.side.value == "short" for t in closed),
        "stop_exits": sum(t.exit_reason and t.exit_reason.value == "stop" for t in closed),
        "target_exits": sum(t.exit_reason and t.exit_reason.value == "target" for t in closed),
    }


def run_windows(candles: list[Candle], cfg: AI38Config) -> dict:
    return {name: metrics_for(candles, cfg, start, end) for name, (start, end) in WINDOWS.items()}


def main() -> None:
    ap = argparse.ArgumentParser(description="AI38 frozen long-history, OOS, and robustness validation")
    ap.add_argument("data_dir", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    primary_path = args.data_dir / "gbpusd_mid_4h_offset2.csv"
    candles = load_csv(primary_path)
    if not candles:
        raise RuntimeError("no primary GBPUSD candles")

    baseline_cfg = AI38Config.creator_4h()
    baseline = run_windows(candles, baseline_cfg)

    cost_variants = {
        "commission_1_5x": {"commission_usd_per_contract_per_side": 0.000075},
        "commission_2x": {"commission_usd_per_contract_per_side": 0.00010},
        "slippage_30_ticks": {"slippage_ticks": 30},
        "slippage_40_ticks": {"slippage_ticks": 40},
        "combined_2x_costs": {"commission_usd_per_contract_per_side": 0.00010, "slippage_ticks": 40},
    }
    neighbor_variants = {
        "ema_fast_18": {"ema_fast_length": 18},
        "ema_fast_24": {"ema_fast_length": 24},
        "ema_slow_45": {"ema_slow_length": 45},
        "ema_slow_55": {"ema_slow_length": 55},
        "momentum_a_100": {"momentum_a_length": 100},
        "momentum_a_120": {"momentum_a_length": 120},
        "momentum_b_25": {"momentum_b_length": 25},
        "momentum_b_35": {"momentum_b_length": 35},
        "rr_2_0": {"risk_reward_ratio": 2.0},
        "rr_2_8": {"risk_reward_ratio": 2.8},
        "candle_lookback_2": {"candle_lookback": 2},
        "candle_lookback_4": {"candle_lookback": 4},
        "fast_growth_25pct": {"ema_fast_growth_percent": 25.0},
        "fast_growth_35pct": {"ema_fast_growth_percent": 35.0},
        "slow_growth_30pct": {"ema_slow_growth_percent": 30.0},
        "slow_growth_40pct": {"ema_slow_growth_percent": 40.0},
        "fast_growth_lookback_18": {"ema_fast_lookback": 18},
        "fast_growth_lookback_24": {"ema_fast_lookback": 24},
        "slow_growth_lookback_5": {"ema_slow_lookback": 5},
        "slow_growth_lookback_7": {"ema_slow_lookback": 7},
    }

    costs = {name: run_windows(candles, AI38Config.creator_4h(**overrides)) for name, overrides in cost_variants.items()}
    neighbors = {name: run_windows(candles, AI38Config.creator_4h(**overrides)) for name, overrides in neighbor_variants.items()}
    normalized_1x = run_windows(candles, AI38Config.creator_4h(fixed_units=10_000.0))

    # Feed/alignment sensitivity is kept separate from the chosen neutral
    # midpoint UTC+2 primary. No best row is selected from these diagnostics.
    feed_alignment = {}
    for side in ("bid", "ask", "mid"):
        for offset in range(4):
            key = f"{side}_offset{offset}"
            alt = load_csv(args.data_dir / f"gbpusd_{side}_4h_offset{offset}.csv")
            feed_alignment[key] = {
                "backlog": metrics_for(alt, baseline_cfg, BACKLOG_START, CREATOR_START),
                "creator": metrics_for(alt, baseline_cfg, CREATOR_START, CREATOR_END),
                "oos": metrics_for(alt, baseline_cfg, CREATOR_END, OOS_END),
            }

    years = {}
    for year in range(2005, 2027):
        start = datetime(year, 1, 1, tzinfo=UTC)
        end = min(datetime(year + 1, 1, 1, tzinfo=UTC), OOS_END)
        if start >= OOS_END:
            break
        years[str(year)] = metrics_for(candles, baseline_cfg, start, end)

    oos = baseline["oos_2024_03_to_2026_09"]
    backlog = baseline["backlog_2005_to_creator"]
    recent = baseline["rolling_6m"]
    double_oos = costs["combined_2x_costs"]["oos_2024_03_to_2026_09"]
    all_neighbor_oos_positive = all(
        row["oos_2024_03_to_2026_09"]["net_profit_usd"] > 0
        and row["oos_2024_03_to_2026_09"]["profit_factor"] > 1.0
        for row in neighbors.values()
    )
    gates = {
        "backlog_positive": backlog["net_profit_usd"] > 0,
        "backlog_pf_above_1": backlog["profit_factor"] > 1.0,
        "oos_positive": oos["net_profit_usd"] > 0,
        "oos_pf_above_1": oos["profit_factor"] > 1.0,
        "double_cost_oos_positive": double_oos["net_profit_usd"] > 0,
        "double_cost_oos_pf_above_1": double_oos["profit_factor"] > 1.0,
        "all_20_neighbors_oos_positive_pf_above_1": all_neighbor_oos_positive,
        "latest_6m_positive": recent["net_profit_usd"] > 0,
        "latest_6m_pf_above_1": recent["profit_factor"] > 1.0,
    }
    gates["all_gates_pass"] = all(gates.values())

    payload = {
        "strategy": "AI38 Double EMA + Momentum GBPUSD 4H",
        "primary_feed": "Dukascopy midpoint, 4H UTC+2 alignment",
        "source_settings": asdict(baseline_cfg),
        "windows": {k: {"start": a.isoformat(), "end_exclusive": b.isoformat()} for k, (a, b) in WINDOWS.items()},
        "baseline": baseline,
        "cost_variants": costs,
        "neighbor_variants": neighbors,
        "normalized_1x_units": normalized_1x,
        "feed_alignment_sensitivity": feed_alignment,
        "yearly": years,
        "gates": gates,
        "principle": "Frozen strategy. Every predeclared cost/parameter neighbour is reported; no OOS-driven retuning or best-neighbour selection is performed.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, allow_nan=True), encoding="utf-8")

    print("AI38 frozen full validation")
    for name in ("backlog_2005_to_creator", "creator_2020_03_to_2024_03", "oos_2024_03_to_2026_09", "rolling_6m", "rolling_12m", "rolling_24m"):
        m = baseline[name]
        print(name, f"trades={m['trades']} net={m['net_profit_pct']:.2f}% PF={m['profit_factor']:.3f} win={m['win_rate_pct']:.2f}% DD={m['max_closed_trade_drawdown_pct']:.2f}%")
    print("gates", json.dumps(gates, indent=2))


if __name__ == "__main__":
    main()
