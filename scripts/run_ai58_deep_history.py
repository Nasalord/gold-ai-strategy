from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime, timezone
from math import inf
from pathlib import Path
from statistics import median

from ai_investing_lab.strategies.ai58_usdjpy import AI58Config
from ai_investing_lab.strategies.ai58_usdjpy.csv_runner import load_candles_csv
from ai_investing_lab.strategies.ai58_usdjpy.source_fidelity import SourceFaithfulAI58Backtester

# The independent Dukascopy 15m path used by the repo returns USDJPY history
# beginning 2011-03-18. Reserve roughly two weeks for ATR/TDFI warmup and start
# scored deep-history metrics on 2011-04-01.
WARMUP_START = datetime(2011, 3, 18, tzinfo=timezone.utc)
ANALYSIS_START = datetime(2011, 4, 1, tzinfo=timezone.utc)
OPT_START = datetime(2021, 9, 1, tzinfo=timezone.utc)
OPT_END = datetime(2025, 9, 1, tzinfo=timezone.utc)
VIDEO_OOS_END = datetime(2026, 3, 15, tzinfo=timezone.utc)
ANALYSIS_END = datetime(2026, 9, 14, tzinfo=timezone.utc)


def trade_metrics(trades, *, initial_capital=10_000.0):
    closed = [t for t in trades if t.closed]
    wins = [t for t in closed if t.net_pnl_usd > 0]
    losses = [t for t in closed if t.net_pnl_usd <= 0]
    gross_profit = sum(t.net_pnl_usd for t in wins)
    gross_loss = abs(sum(t.net_pnl_usd for t in losses))
    pf = gross_profit / gross_loss if gross_loss > 0 else (inf if gross_profit > 0 else 0.0)

    equity = initial_capital
    peak = equity
    max_dd = 0.0
    for t in sorted(closed, key=lambda x: x.exit_time or x.entry_time):
        equity += t.net_pnl_usd
        peak = max(peak, equity)
        if peak > 0:
            max_dd = max(max_dd, (peak - equity) / peak)

    net = sum(t.net_pnl_usd for t in closed)
    return {
        "trades": len(closed),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_pct": 100.0 * len(wins) / len(closed) if closed else 0.0,
        "net_profit_usd": net,
        "net_profit_pct": 100.0 * net / initial_capital,
        "profit_factor": pf,
        "max_drawdown_pct_closed_trade": 100.0 * max_dd,
    }


def in_window(trades, start, end):
    return [t for t in trades if start <= t.entry_time < end and t.closed]


def window_metrics(trades, start, end):
    result = trade_metrics(in_window(trades, start, end))
    result["start"] = start.date().isoformat()
    result["end_exclusive"] = end.date().isoformat()
    return result


def add_years(dt: datetime, years: int) -> datetime:
    try:
        return dt.replace(year=dt.year + years)
    except ValueError:
        return dt.replace(month=2, day=28, year=dt.year + years)


def month_start(dt: datetime) -> datetime:
    return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def add_months(dt: datetime, months: int) -> datetime:
    idx = (dt.year * 12 + (dt.month - 1)) + months
    year, month0 = divmod(idx, 12)
    return datetime(year, month0 + 1, 1, tzinfo=timezone.utc)


def percentile_rank(values, target):
    if not values:
        return None
    return 100.0 * sum(v <= target for v in values) / len(values)


def baseline_deep_run(candles, **overrides):
    cfg = AI58Config.optimized_15m(**overrides)
    selected = [c for c in candles if WARMUP_START <= c.time < ANALYSIS_END]
    return SourceFaithfulAI58Backtester(cfg).run(selected)


def main():
    parser = argparse.ArgumentParser(description="AI58 frozen-parameter deep-history validation")
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    candles = load_candles_csv(args.csv_path)
    if not candles:
        raise RuntimeError("no candles loaded")
    if candles[0].time > WARMUP_START:
        raise RuntimeError(f"deep-history dataset starts too late: {candles[0].time.isoformat()}")

    baseline_result = baseline_deep_run(candles)
    trades = baseline_result.trades
    double_cost_result = baseline_deep_run(
        candles,
        slippage_ticks=24,
        commission_usd_per_standard_lot_per_side=7.0,
    )
    double_cost_trades = double_cost_result.trades
    paper_result = baseline_deep_run(candles, fixed_notional_usd=10_000.0)
    paper_trades = paper_result.trades

    major_periods = {
        "deep_pre_sample_2011_04_to_2021_09": window_metrics(trades, ANALYSIS_START, OPT_START),
        "creator_optimization_2021_09_to_2025_09": window_metrics(trades, OPT_START, OPT_END),
        "creator_video_oos_2025_09_to_2026_03_15": window_metrics(trades, OPT_END, VIDEO_OOS_END),
        "fresh_post_video_2026_03_15_to_2026_09_14": window_metrics(trades, VIDEO_OOS_END, ANALYSIS_END),
        "entire_2011_04_to_2026_09": window_metrics(trades, ANALYSIS_START, ANALYSIS_END),
    }

    cost_stress = {
        "double_costs_deep_pre_sample": window_metrics(double_cost_trades, ANALYSIS_START, OPT_START),
        "double_costs_entire_history": window_metrics(double_cost_trades, ANALYSIS_START, ANALYSIS_END),
        "paper_10k_notional_deep_pre_sample": window_metrics(paper_trades, ANALYSIS_START, OPT_START),
        "paper_10k_notional_entire_history": window_metrics(paper_trades, ANALYSIS_START, ANALYSIS_END),
    }

    yearly = {}
    for year in range(2011, 2027):
        start = max(datetime(year, 1, 1, tzinfo=timezone.utc), ANALYSIS_START)
        end = min(datetime(year + 1, 1, 1, tzinfo=timezone.utc), ANALYSIS_END)
        if start >= end:
            continue
        yearly[str(year)] = window_metrics(trades, start, end)

    rolling_3y = []
    rolling_5y = []
    for year in range(2012, 2027):
        start = datetime(year, 1, 1, tzinfo=timezone.utc)
        end3 = add_years(start, 3)
        end5 = add_years(start, 5)
        if end3 <= ANALYSIS_END:
            rolling_3y.append(window_metrics(trades, start, end3))
        if end5 <= ANALYSIS_END:
            rolling_5y.append(window_metrics(trades, start, end5))

    rolling_6m = []
    start = month_start(ANALYSIS_START)
    while add_months(start, 6) <= ANALYSIS_END:
        rolling_6m.append(window_metrics(trades, start, add_months(start, 6)))
        start = add_months(start, 1)

    march_sep = []
    for year in range(2012, 2027):
        start = datetime(year, 3, 15, tzinfo=timezone.utc)
        end = datetime(year, 9, 14, tzinfo=timezone.utc)
        if end <= ANALYSIS_END:
            march_sep.append(window_metrics(trades, start, end))

    six_month_returns = [w["net_profit_pct"] for w in rolling_6m]
    six_month_pfs = [w["profit_factor"] for w in rolling_6m if w["trades"] > 0 and w["profit_factor"] != inf]
    fresh = major_periods["fresh_post_video_2026_03_15_to_2026_09_14"]
    prior_march_sep = [w for w in march_sep if w["start"] != "2026-03-15"]

    yearly_returns = [v["net_profit_pct"] for v in yearly.values()]
    summary = {
        "profitable_years": sum(v > 0 for v in yearly_returns),
        "losing_years": sum(v <= 0 for v in yearly_returns),
        "median_calendar_year_return_pct": median(yearly_returns) if yearly_returns else None,
        "worst_calendar_year_return_pct": min(yearly_returns) if yearly_returns else None,
        "best_calendar_year_return_pct": max(yearly_returns) if yearly_returns else None,
        "rolling_6m_windows": len(rolling_6m),
        "profitable_rolling_6m_pct": 100.0 * sum(v > 0 for v in six_month_returns) / len(six_month_returns),
        "median_rolling_6m_return_pct": median(six_month_returns),
        "fresh_2026_return_percentile_vs_all_rolling_6m": percentile_rank(six_month_returns, fresh["net_profit_pct"]),
        "fresh_2026_pf_percentile_vs_all_rolling_6m": percentile_rank(six_month_pfs, fresh["profit_factor"]),
        "prior_march_sep_periods": len(prior_march_sep),
        "prior_march_sep_negative_count": sum(w["net_profit_pct"] <= 0 for w in prior_march_sep),
        "fresh_2026_vs_prior_march_sep_return_percentile": percentile_rank(
            [w["net_profit_pct"] for w in prior_march_sep], fresh["net_profit_pct"]
        ),
    }

    payload = {
        "method": "Frozen creator-video AI58 parameters; no optimization or row selection.",
        "data": {
            "source_file": str(args.csv_path),
            "provider": "Dukascopy midpoint proxy",
            "requested_history_start": "2007-12-18",
            "first_available_bar": candles[0].time.isoformat(),
            "analysis_start_after_warmup": ANALYSIS_START.date().isoformat(),
            "analysis_end_exclusive": ANALYSIS_END.date().isoformat(),
            "warmup_start": WARMUP_START.date().isoformat(),
            "bars_loaded": len(candles),
            "last_bar": candles[-1].time.isoformat(),
        },
        "frozen_config": asdict(AI58Config.optimized_15m()),
        "major_periods": major_periods,
        "cost_and_paper_stress": cost_stress,
        "summary": summary,
        "calendar_years": yearly,
        "rolling_3_year_windows": rolling_3y,
        "rolling_5_year_windows": rolling_5y,
        "rolling_6_month_windows": rolling_6m,
        "march15_to_sep14_same_season_windows": march_sep,
        "notes": [
            "The fetch was requested from 2007-12-18, but this Dukascopy path first returned USDJPY 15m bars on 2011-03-18; scored analysis therefore begins 2011-04-01 after warmup.",
            "2011-2021 is a pre-sample/backcast, not a substitute for forward OOS.",
            "The strategy parameters remain the creator-video preset recovered before these tests.",
            "Window metrics assign trades by entry time and reset comparison equity to $10,000 per window.",
            "The engine is run continuously from 2011-03-18 so ATR/TDFI state is not restarted at each window boundary.",
            "Creator used IC Markets; this deep test uses the independent Dukascopy midpoint proxy that already passed the parity screen closely.",
        ],
    }

    def json_default(obj):
        if hasattr(obj, "isoformat"):
            return obj.isoformat()
        if hasattr(obj, "value"):
            return obj.value
        raise TypeError(type(obj).__name__)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, allow_nan=True, default=json_default), encoding="utf-8")
    print(json.dumps({
        "major_periods": major_periods,
        "cost_and_paper_stress": cost_stress,
        "summary": summary,
    }, indent=2, allow_nan=True, default=json_default))


if __name__ == "__main__":
    main()
