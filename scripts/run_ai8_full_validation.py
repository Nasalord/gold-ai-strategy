from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict
from datetime import datetime, timezone
from math import inf
from pathlib import Path

from ai_investing_lab.strategies.ai8_btc import AI8Backtester, AI8Config, Candle

UTC = timezone.utc
DATA_START = datetime(2017, 8, 17, tzinfo=UTC)
BACKLOG_START = datetime(2018, 3, 1, tzinfo=UTC)
CREATOR_START = datetime(2020, 3, 1, tzinfo=UTC)
CREATOR_END = datetime(2024, 3, 1, tzinfo=UTC)
OOS_1_END = datetime(2025, 3, 1, tzinfo=UTC)
OOS_2_END = datetime(2026, 3, 1, tzinfo=UTC)
VALIDATION_END = datetime(2026, 9, 15, tzinfo=UTC)


def parse_iso(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


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
    return sorted(out, key=lambda c: c.time)


def run_window(candles: list[Candle], cfg: AI8Config, start: datetime, end: datetime):
    return AI8Backtester(cfg).run(
        candles,
        trade_start=start,
        trade_end=end,
        close_at_end=False,
    )


def result_summary(result) -> dict[str, object]:
    closed = [t for t in result.trades if t.closed]
    return {
        **asdict(result.metrics),
        "open_legs_at_end": len([t for t in result.trades if not t.closed]),
        "range_filter_exits": sum(t.exit_reason is not None and t.exit_reason.value == "range_filter" for t in closed),
        "stop_exits": sum(t.exit_reason is not None and t.exit_reason.value == "stop_loss" for t in closed),
        "take_profit_exits": sum(t.exit_reason is not None and t.exit_reason.value == "take_profit" for t in closed),
    }


def summarize_trade_slice(trades, start: datetime, end: datetime, initial: float = 100_000.0) -> dict[str, float | int]:
    closed = [
        t for t in trades
        if t.closed and t.exit_time is not None and start <= t.exit_time < end
    ]
    closed.sort(key=lambda t: (t.exit_time, t.entry_time))
    wins = [t for t in closed if t.net_pnl_usd > 0]
    losses = [t for t in closed if t.net_pnl_usd <= 0]
    gp = sum(t.net_pnl_usd for t in wins)
    gl = abs(sum(t.net_pnl_usd for t in losses))
    net = sum(t.net_pnl_usd for t in closed)
    pf = gp / gl if gl else (inf if gp else 0.0)
    equity = initial
    peak = initial
    dd = 0.0
    for trade in closed:
        equity += trade.net_pnl_usd
        peak = max(peak, equity)
        if peak > 0:
            dd = max(dd, (peak - equity) / peak)
    n = len(closed)
    return {
        "trades": n,
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_pct": 100.0 * len(wins) / n if n else 0.0,
        "net_profit_usd": net,
        "net_profit_pct": 100.0 * net / initial,
        "profit_factor": pf,
        "max_closed_trade_drawdown_pct": 100.0 * dd,
    }


def shift_months(dt: datetime, delta: int) -> datetime:
    total = dt.year * 12 + (dt.month - 1) + delta
    year, month0 = divmod(total, 12)
    return datetime(year, month0 + 1, 1, tzinfo=UTC)


def rolling_windows(trades, months: int, first_end: datetime, last_end: datetime) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    end = first_end
    while end <= last_end:
        start = shift_months(end, -months)
        rows.append({
            "start": start.date().isoformat(),
            "end": end.date().isoformat(),
            **summarize_trade_slice(trades, start, end),
        })
        end = shift_months(end, 1)
    return rows


def percentile_rank(values: list[float], current: float) -> float:
    if not values:
        return 0.0
    return 100.0 * sum(v <= current for v in values) / len(values)


def streak_and_drawdown_state(trades, end: datetime, initial: float = 100_000.0) -> dict[str, object]:
    closed = [t for t in trades if t.closed and t.exit_time is not None and t.exit_time < end]
    closed.sort(key=lambda t: (t.exit_time, t.entry_time))

    max_losing_streak = 0
    current_streak = 0
    ending_streak = 0
    for t in closed:
        if t.net_pnl_usd <= 0:
            current_streak += 1
            max_losing_streak = max(max_losing_streak, current_streak)
        else:
            current_streak = 0
    ending_streak = current_streak

    equity = initial
    peak = initial
    peak_time: datetime | None = BACKLOG_START
    max_dd = 0.0
    max_dd_time: datetime | None = None
    for t in closed:
        equity += t.net_pnl_usd
        if equity >= peak:
            peak = equity
            peak_time = t.exit_time
        elif peak > 0:
            dd = 100.0 * (peak - equity) / peak
            if dd > max_dd:
                max_dd = dd
                max_dd_time = t.exit_time

    current_dd = 100.0 * (peak - equity) / peak if peak > 0 else 0.0
    underwater_days = (end - peak_time).total_seconds() / 86400.0 if peak_time else 0.0
    return {
        "closed_trades": len(closed),
        "ending_losing_streak": ending_streak,
        "max_losing_streak": max_losing_streak,
        "current_closed_trade_drawdown_pct": current_dd,
        "historical_max_closed_trade_drawdown_pct": max_dd,
        "historical_max_drawdown_time": max_dd_time.isoformat() if max_dd_time else None,
        "last_equity_peak_time": peak_time.isoformat() if peak_time else None,
        "days_underwater_from_last_closed_trade_peak": underwater_days,
        "ending_equity_usd": equity,
        "peak_equity_usd": peak,
    }


def evaluate_variant(candles: list[Candle], label: str, **overrides) -> dict[str, object]:
    cfg = AI8Config.creator_fixed_cash(**overrides)
    return {
        "label": label,
        "overrides": overrides,
        "backlog_2018_2020": result_summary(run_window(candles, cfg, BACKLOG_START, CREATOR_START)),
        "creator_2020_2024": result_summary(run_window(candles, cfg, CREATOR_START, CREATOR_END)),
        "oos_2024_2026_09": result_summary(run_window(candles, cfg, CREATOR_END, VALIDATION_END)),
        "oos_2024_2025": result_summary(run_window(candles, cfg, CREATOR_END, OOS_1_END)),
        "oos_2025_2026": result_summary(run_window(candles, cfg, OOS_1_END, OOS_2_END)),
        "recent_2026_03_2026_09": result_summary(run_window(candles, cfg, OOS_2_END, VALIDATION_END)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="AI8 full backlog/OOS/robustness validation")
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    candles = load_csv(args.csv_path)
    if not candles:
        raise RuntimeError("no candles loaded")

    # Fixed before inspecting any post-2024 result. This is a stress matrix,
    # not an optimizer; every row is reported and no replacement parameters
    # are selected from it.
    variants = [
        evaluate_variant(candles, "baseline"),
        evaluate_variant(candles, "commission_1p5x", commission_pct_per_side=0.15),
        evaluate_variant(candles, "commission_2x", commission_pct_per_side=0.20),
        evaluate_variant(candles, "slippage_2x", slippage_ticks=4),
        evaluate_variant(candles, "costs_2x", commission_pct_per_side=0.20, slippage_ticks=4),
        evaluate_variant(candles, "supertrend_atr_7", supertrend_atr_length=7),
        evaluate_variant(candles, "supertrend_atr_9", supertrend_atr_length=9),
        evaluate_variant(candles, "supertrend_factor_1p4", supertrend_factor=1.4),
        evaluate_variant(candles, "supertrend_factor_1p8", supertrend_factor=1.8),
        evaluate_variant(candles, "adx_limit_16", adx_limit=16.0),
        evaluate_variant(candles, "adx_limit_20", adx_limit=20.0),
        evaluate_variant(candles, "range_period_150", range_period=150),
        evaluate_variant(candles, "range_period_200", range_period=200),
        evaluate_variant(candles, "range_multiplier_4p5", range_multiplier=4.5),
        evaluate_variant(candles, "range_multiplier_5p5", range_multiplier=5.5),
        evaluate_variant(candles, "stop_atr_length_40", stop_atr_length=40),
        evaluate_variant(candles, "stop_atr_length_60", stop_atr_length=60),
        evaluate_variant(candles, "stop_multiplier_8", stop_atr_multiplier=8.0),
        evaluate_variant(candles, "stop_multiplier_12", stop_atr_multiplier=12.0),
    ]

    baseline = next(v for v in variants if v["label"] == "baseline")
    double_cost = next(v for v in variants if v["label"] == "costs_2x")
    neighbor_rows = [v for v in variants if v["label"] not in {
        "baseline", "commission_1p5x", "commission_2x", "slippage_2x", "costs_2x"
    }]

    full_result = run_window(candles, AI8Config.creator_fixed_cash(), BACKLOG_START, VALIDATION_END)
    full_trades = full_result.trades

    year_by_year: dict[str, object] = {}
    for year in range(2018, 2027):
        start = max(BACKLOG_START, datetime(year, 1, 1, tzinfo=UTC))
        end = min(VALIDATION_END, datetime(year + 1, 1, 1, tzinfo=UTC))
        if start < end:
            year_by_year[str(year)] = summarize_trade_slice(full_trades, start, end)

    rolling: dict[str, object] = {}
    for months in (6, 12, 24):
        first_end = shift_months(BACKLOG_START, months)
        rows = rolling_windows(full_trades, months, first_end, datetime(2026, 9, 1, tzinfo=UTC))
        latest = summarize_trade_slice(full_trades, shift_months(VALIDATION_END.replace(day=1), -months), VALIDATION_END)
        rolling[str(months)] = {
            "windows": rows,
            "profitable_fraction": sum(r["net_profit_pct"] > 0 for r in rows) / len(rows) if rows else 0.0,
            "pf_above_1_fraction": sum(r["profit_factor"] > 1 for r in rows) / len(rows) if rows else 0.0,
            "latest_partial_to_2026_09_15": latest,
            "latest_return_percentile": percentile_rank([float(r["net_profit_pct"]) for r in rows], float(latest["net_profit_pct"])),
            "latest_pf_percentile": percentile_rank([float(r["profit_factor"]) for r in rows], float(latest["profit_factor"])),
        }

    oos_neighbors_positive = sum(v["oos_2024_2026_09"]["net_profit_pct"] > 0 for v in neighbor_rows)
    oos_neighbors_pf = sum(v["oos_2024_2026_09"]["profit_factor"] > 1 for v in neighbor_rows)
    recent_neighbors_positive = sum(v["recent_2026_03_2026_09"]["net_profit_pct"] > 0 for v in neighbor_rows)

    core_gates = {
        "backlog_positive": baseline["backlog_2018_2020"]["net_profit_pct"] > 0,
        "backlog_pf_above_1": baseline["backlog_2018_2020"]["profit_factor"] > 1,
        "full_oos_positive": baseline["oos_2024_2026_09"]["net_profit_pct"] > 0,
        "full_oos_pf_above_1": baseline["oos_2024_2026_09"]["profit_factor"] > 1,
        "double_cost_oos_positive": double_cost["oos_2024_2026_09"]["net_profit_pct"] > 0,
        "double_cost_oos_pf_above_1": double_cost["oos_2024_2026_09"]["profit_factor"] > 1,
    }
    current_health = {
        "recent_2026_positive": baseline["recent_2026_03_2026_09"]["net_profit_pct"] > 0,
        "recent_2026_pf_above_1": baseline["recent_2026_03_2026_09"]["profit_factor"] > 1,
    }

    if not core_gates["full_oos_positive"] or not core_gates["full_oos_pf_above_1"]:
        classification = "OOS_FAILED"
    elif all(core_gates.values()) and all(current_health.values()) and oos_neighbors_positive >= int(0.75 * len(neighbor_rows)):
        classification = "LONG_HISTORY_AND_OOS_VALIDATED"
    elif all(core_gates.values()) and not all(current_health.values()):
        classification = "LONG_HISTORY_VALIDATED_CURRENT_WEAK_REGIME"
    elif core_gates["full_oos_positive"] and core_gates["full_oos_pf_above_1"]:
        classification = "OOS_POSITIVE_ROBUSTNESS_MIXED"
    else:
        classification = "MIXED"

    payload = {
        "method": "Frozen AI8 Binance Spot reconstruction. Predeclared backlog/OOS windows and symmetric stress matrix; no parameter selection after observing OOS.",
        "data": {
            "source": "Official Binance Vision spot BTCUSDT 2h klines",
            "bars": len(candles),
            "first_bar": candles[0].time.isoformat(),
            "last_bar": candles[-1].time.isoformat(),
        },
        "windows": {
            "warmup_data_start": DATA_START.date().isoformat(),
            "pre_optimization_backlog": "2018-03-01 to 2020-03-01",
            "creator_window": "2020-03-01 to 2024-03-01",
            "untouched_oos": "2024-03-01 to 2026-09-15 (end exclusive)",
            "oos_1": "2024-03-01 to 2025-03-01",
            "oos_2": "2025-03-01 to 2026-03-01",
            "recent": "2026-03-01 to 2026-09-15 (end exclusive)",
        },
        "classification": classification,
        "core_gates": core_gates,
        "current_health": current_health,
        "neighbor_summary": {
            "count": len(neighbor_rows),
            "full_oos_positive_count": oos_neighbors_positive,
            "full_oos_pf_above_1_count": oos_neighbors_pf,
            "recent_2026_positive_count": recent_neighbors_positive,
        },
        "baseline_full_continuous_2018_2026": result_summary(full_result),
        "drawdown_and_streak_state": streak_and_drawdown_state(full_trades, VALIDATION_END),
        "year_by_year_continuous": year_by_year,
        "rolling_closed_trade_windows": rolling,
        "variants": variants,
        "notes": [
            "Creator headline return/PF was not independently reproduced; this validation uses the reproducible Binance Spot reconstruction as the frozen baseline.",
            "All strategy inputs are unchanged in the baseline. Neighbor variants are stress tests only and are not candidates for retuning.",
            "Rolling metrics slice the continuous 2018-2026 closed-trade stream by exit date so the live strategy state is not reset at every rolling boundary.",
            "This repository remains research/backtest/paper only; no live broker routing is added.",
        ],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, allow_nan=True), encoding="utf-8")

    print(json.dumps({
        "classification": classification,
        "core_gates": core_gates,
        "current_health": current_health,
        "neighbor_summary": payload["neighbor_summary"],
        "baseline": baseline,
        "double_costs": double_cost,
        "full_continuous": payload["baseline_full_continuous_2018_2026"],
        "drawdown_state": payload["drawdown_and_streak_state"],
        "year_by_year": year_by_year,
        "rolling_summary": {
            k: {kk: vv for kk, vv in v.items() if kk != "windows"}
            for k, v in rolling.items()
        },
    }, indent=2, allow_nan=True))


if __name__ == "__main__":
    main()
