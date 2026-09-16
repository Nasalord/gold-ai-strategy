from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from math import floor, inf, sqrt
from pathlib import Path

from ai_investing_lab.strategies.ai8_btc import AI8Backtester, AI8Config
from ai_investing_lab.strategies.ai58_usdjpy import AI58Config
from ai_investing_lab.strategies.ai58_usdjpy.csv_runner import load_candles_csv as load_ai58
from ai_investing_lab.strategies.ai58_usdjpy.source_fidelity import SourceFaithfulAI58Backtester
from scripts.run_ai8_full_validation import load_csv as load_ai8

UTC = timezone.utc
PORTFOLIO_STARTING_EQUITY = 5_000.0
TARGET_START = datetime(2016, 1, 1, tzinfo=UTC)
BTC_STEP = 0.0001
FX_STEP = 1_000.0
CRYPTO_MIN_NOTIONAL = 10.0

# 50/50 is the primary experiment. The surrounding allocations are declared
# before reading the result and are diagnostics only, not alternatives chosen
# after the fact.
ALLOCATIONS = {
    "ai8_only": 1.00,
    "ai8_75_ai58_25": 0.75,
    "ai8_50_ai58_50": 0.50,
    "ai8_25_ai58_75": 0.25,
    "ai58_only": 0.00,
}


def dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def month_shift(value: datetime, months: int) -> datetime:
    index = value.year * 12 + value.month - 1 + months
    year, month0 = divmod(index, 12)
    return datetime(year, month0 + 1, min(value.day, 28), tzinfo=UTC)


def floor_step(value: float, step: float) -> float:
    if value <= 0:
        return 0.0
    return floor((value + step * 1e-12) / step) * step


def simulate_ai8_events(trades, start, end, *, starting_equity: float, fixed_cash: float):
    if starting_equity <= 0:
        return [], {"starting_equity_usd": 0.0, "ending_equity_usd": 0.0, "trades": 0, "skipped": 0}

    equity = starting_equity
    events = []
    open_scale = {}
    skipped = 0
    eligible = [
        t for t in trades
        if t.closed and t.exit_time is not None and start <= t.entry_time < end and t.exit_time < end
    ]
    timeline = []
    for idx, trade in enumerate(eligible):
        reason = trade.exit_reason.value if trade.exit_reason is not None else ""
        exit_priority = 0 if reason == "range_filter" else 2
        timeline.append((trade.entry_time, 1, idx, "entry", trade))
        timeline.append((trade.exit_time, exit_priority, idx, "exit", trade))
    timeline.sort(key=lambda x: (x[0], x[1], x[2]))

    for when, _, idx, kind, trade in timeline:
        if kind == "entry":
            if equity <= 0 or trade.quantity_btc <= 0:
                open_scale[idx] = (0.0, 0.0, 0.0)
                skipped += 1
                continue
            signal_price = fixed_cash / float(trade.quantity_btc)
            leg_cash = equity / 7.0
            qty = floor_step(leg_cash / signal_price, BTC_STEP)
            if qty * signal_price < CRYPTO_MIN_NOTIONAL:
                open_scale[idx] = (0.0, 0.0, 0.0)
                skipped += 1
                continue
            scale = qty / float(trade.quantity_btc)
            notional = qty * float(trade.entry_price)
            commission = float(trade.entry_commission_usd + trade.exit_commission_usd) * scale
            open_scale[idx] = (scale, notional, commission)
            continue

        scale, notional, commission = open_scale.pop(idx, (0.0, 0.0, 0.0))
        if scale <= 0:
            continue
        pnl = float(trade.net_pnl_usd) * scale
        equity += pnl
        events.append({
            "time": when,
            "strategy": "AI8",
            "pnl_usd": pnl,
            "entry_notional_usd": notional,
            "commission_usd": commission,
        })

    return events, {
        "starting_equity_usd": starting_equity,
        "ending_equity_usd": equity,
        "trades": len(events),
        "skipped": skipped,
    }


def simulate_ai58_events(trades, start, end, *, starting_equity: float):
    if starting_equity <= 0:
        return [], {"starting_equity_usd": 0.0, "ending_equity_usd": 0.0, "trades": 0, "skipped": 0}

    equity = starting_equity
    events = []
    skipped = 0
    eligible = [
        t for t in trades
        if t.closed and t.exit_time is not None and start <= t.entry_time < end and t.exit_time < end
    ]
    eligible.sort(key=lambda t: (t.entry_time, t.exit_time))

    for trade in eligible:
        if equity <= 0 or trade.quantity_base_usd <= 0:
            skipped += 1
            continue
        qty = floor_step(equity, FX_STEP)
        if qty <= 0:
            skipped += 1
            continue
        scale = qty / float(trade.quantity_base_usd)
        pnl = float(trade.net_pnl_usd) * scale
        commission = float(trade.commission_usd) * scale
        equity += pnl
        events.append({
            "time": trade.exit_time,
            "strategy": "AI58",
            "pnl_usd": pnl,
            "entry_notional_usd": qty,
            "commission_usd": commission,
        })

    return events, {
        "starting_equity_usd": starting_equity,
        "ending_equity_usd": equity,
        "trades": len(events),
        "skipped": skipped,
    }


def portfolio_metrics(events, start, end, *, starting_equity: float):
    events = sorted(events, key=lambda x: (x["time"], x["strategy"]))
    wins = [e["pnl_usd"] for e in events if e["pnl_usd"] > 0]
    losses = [e["pnl_usd"] for e in events if e["pnl_usd"] <= 0]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    pf = gross_profit / gross_loss if gross_loss else (inf if gross_profit else 0.0)

    # Group exits sharing an identical timestamp so arbitrary tie ordering cannot
    # create a fake within-timestamp drawdown.
    grouped = defaultdict(float)
    for event in events:
        grouped[event["time"]] += event["pnl_usd"]

    equity = starting_equity
    peak = equity
    minimum = equity
    max_dd = 0.0
    max_dd_start = None
    max_dd_end = None
    peak_time = start
    for when in sorted(grouped):
        equity += grouped[when]
        if equity > peak:
            peak = equity
            peak_time = when
        minimum = min(minimum, equity)
        dd = 100.0 * (peak - equity) / peak if peak > 0 else inf
        if dd > max_dd:
            max_dd = dd
            max_dd_start = peak_time
            max_dd_end = when

    years = max((end - start).total_seconds() / (365.25 * 86400.0), 1e-9)
    cagr = None if equity <= 0 else 100.0 * ((equity / starting_equity) ** (1.0 / years) - 1.0)
    return {
        "starting_equity_usd": starting_equity,
        "ending_equity_usd": equity,
        "net_profit_usd": equity - starting_equity,
        "net_profit_pct": 100.0 * (equity / starting_equity - 1.0),
        "cagr_pct": cagr,
        "profit_factor": pf,
        "closed_trade_events": len(events),
        "max_closed_trade_drawdown_pct": max_dd,
        "max_drawdown_start": max_dd_start.isoformat() if max_dd_start else None,
        "max_drawdown_end": max_dd_end.isoformat() if max_dd_end else None,
        "minimum_closed_trade_equity_usd": minimum,
        "commission_usd": sum(e["commission_usd"] for e in events),
        "turnover_multiple_of_starting_equity": sum(e["entry_notional_usd"] for e in events) / starting_equity,
        "ai8_events": sum(e["strategy"] == "AI8" for e in events),
        "ai58_events": sum(e["strategy"] == "AI58" for e in events),
    }


def monthly_returns(events, start, end, starting_equity):
    grouped = defaultdict(float)
    for event in events:
        if start <= event["time"] < end:
            grouped[(event["time"].year, event["time"].month)] += event["pnl_usd"]
    equity = starting_equity
    out = {}
    cursor = datetime(start.year, start.month, 1, tzinfo=UTC)
    while cursor < end:
        key = (cursor.year, cursor.month)
        pnl = grouped.get(key, 0.0)
        out[f"{cursor.year:04d}-{cursor.month:02d}"] = pnl / equity if equity > 0 else 0.0
        equity += pnl
        cursor = month_shift(cursor, 1)
    return out


def correlation(a: dict[str, float], b: dict[str, float]):
    keys = sorted(set(a).intersection(b))
    if len(keys) < 2:
        return None
    xs = [a[k] for k in keys]
    ys = [b[k] for k in keys]
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if vx <= 0 or vy <= 0:
        return None
    return cov / sqrt(vx * vy)


def simulate_allocation(ai8_trades, ai58_trades, start, end, *, ai8_weight: float, ai8_fixed_cash: float):
    ai8_start = PORTFOLIO_STARTING_EQUITY * ai8_weight
    ai58_start = PORTFOLIO_STARTING_EQUITY - ai8_start
    ai8_events, ai8_sleeve = simulate_ai8_events(
        ai8_trades, start, end, starting_equity=ai8_start, fixed_cash=ai8_fixed_cash
    )
    ai58_events, ai58_sleeve = simulate_ai58_events(
        ai58_trades, start, end, starting_equity=ai58_start
    )
    combined = ai8_events + ai58_events
    metrics = portfolio_metrics(combined, start, end, starting_equity=PORTFOLIO_STARTING_EQUITY)
    metrics.update({
        "ai8_weight_initial": ai8_weight,
        "ai58_weight_initial": 1.0 - ai8_weight,
        "ai8_ending_equity_usd": ai8_sleeve["ending_equity_usd"],
        "ai58_ending_equity_usd": ai58_sleeve["ending_equity_usd"],
        "ai8_skipped_for_granularity": ai8_sleeve["skipped"],
        "ai58_skipped_for_granularity": ai58_sleeve["skipped"],
    })

    if ai8_start > 0 and ai58_start > 0:
        ai8_monthly = monthly_returns(ai8_events, start, end, ai8_start)
        ai58_monthly = monthly_returns(ai58_events, start, end, ai58_start)
        metrics["monthly_sleeve_return_correlation"] = correlation(ai8_monthly, ai58_monthly)
        common = sorted(set(ai8_monthly).intersection(ai58_monthly))
        metrics["months_both_negative"] = sum(ai8_monthly[k] < 0 and ai58_monthly[k] < 0 for k in common)
        metrics["months_ai8_negative_ai58_positive"] = sum(ai8_monthly[k] < 0 < ai58_monthly[k] for k in common)
        metrics["months_ai58_negative_ai8_positive"] = sum(ai58_monthly[k] < 0 < ai8_monthly[k] for k in common)
    else:
        metrics["monthly_sleeve_return_correlation"] = None
        metrics["months_both_negative"] = None
        metrics["months_ai8_negative_ai58_positive"] = None
        metrics["months_ai58_negative_ai8_positive"] = None
    return metrics


def build_report(btc_path: Path, jpy_path: Path, end: datetime):
    btc = load_ai8(btc_path)
    jpy = load_ai58(jpy_path)
    common_start = max(TARGET_START, btc[0].time, jpy[0].time)

    ai8_cfg = AI8Config.creator_fixed_cash()
    ai8_stress_cfg = AI8Config.creator_fixed_cash(commission_pct_per_side=0.20, slippage_ticks=4)
    ai58_cfg = AI58Config.optimized_15m()
    ai58_stress_cfg = AI58Config.optimized_15m(
        slippage_ticks=24,
        commission_usd_per_standard_lot_per_side=7.0,
    )

    ai8_base = AI8Backtester(ai8_cfg).run(
        btc, trade_start=common_start, trade_end=end, close_at_end=False
    ).trades
    ai8_stress = AI8Backtester(ai8_stress_cfg).run(
        btc, trade_start=common_start, trade_end=end, close_at_end=False
    ).trades
    selected_jpy = [c for c in jpy if c.time < end]
    ai58_base = SourceFaithfulAI58Backtester(ai58_cfg).run(selected_jpy, close_open_position_at_end=False).trades
    ai58_stress = SourceFaithfulAI58Backtester(ai58_stress_cfg).run(selected_jpy, close_open_position_at_end=False).trades

    baseline = {}
    stress = {}
    for name, weight in ALLOCATIONS.items():
        baseline[name] = simulate_allocation(
            ai8_base, ai58_base, common_start, end,
            ai8_weight=weight, ai8_fixed_cash=ai8_cfg.fixed_cash_usd,
        )
        stress[name] = simulate_allocation(
            ai8_stress, ai58_stress, common_start, end,
            ai8_weight=weight, ai8_fixed_cash=ai8_stress_cfg.fixed_cash_usd,
        )

    rolling = {}
    for months in (6, 12, 24, 36, 60):
        start = max(common_start, month_shift(end, -months))
        rolling[str(months)] = simulate_allocation(
            ai8_base, ai58_base, start, end,
            ai8_weight=0.50, ai8_fixed_cash=ai8_cfg.fixed_cash_usd,
        )

    calendar = {}
    for year in range(common_start.year, end.year + 1):
        a = max(common_start, datetime(year, 1, 1, tzinfo=UTC))
        b = min(end, datetime(year + 1, 1, 1, tzinfo=UTC))
        if a < b:
            calendar[str(year)] = simulate_allocation(
                ai8_base, ai58_base, a, b,
                ai8_weight=0.50, ai8_fixed_cash=ai8_cfg.fixed_cash_usd,
            )

    primary = baseline["ai8_50_ai58_50"]
    primary_stress = stress["ai8_50_ai58_50"]
    return {
        "experiment": "AI8 + AI58 frozen two-strategy $5k portfolio",
        "status": "research-only portfolio diversification test",
        "method": {
            "starting_equity_usd": PORTFOLIO_STARTING_EQUITY,
            "common_start": common_start.isoformat(),
            "end_exclusive": end.isoformat(),
            "primary_allocation": "50% AI8 / 50% AI58 initial sleeves",
            "allocation_neighbours": ["75/25", "25/75"],
            "controls": ["100% AI8", "100% AI58"],
            "rebalancing": "none; sleeves compound independently after the initial split",
            "borrowing": "none; each sleeve uses the Stage 3B 1x/no-borrowing sizing rule",
            "ai8_rule": "seven possible pyramid legs, each sized to 1/7 of current AI8 sleeve realized equity",
            "ai58_rule": "USD base notional rounded down to 1,000 units and capped at AI58 sleeve realized equity",
            "drawdown": "combined closed-trade realized-equity drawdown; same-timestamp exits are grouped",
        },
        "baseline_allocations": baseline,
        "double_cost_allocations": stress,
        "primary_50_50_rolling_months": rolling,
        "primary_50_50_calendar_years": calendar,
        "comparison": {
            "ai8_only_dd_pct": baseline["ai8_only"]["max_closed_trade_drawdown_pct"],
            "ai58_only_dd_pct": baseline["ai58_only"]["max_closed_trade_drawdown_pct"],
            "portfolio_50_50_dd_pct": primary["max_closed_trade_drawdown_pct"],
            "portfolio_50_50_cagr_pct": primary["cagr_pct"],
            "portfolio_50_50_2x_cost_pf": primary_stress["profit_factor"],
        },
        "guardrails": [
            "AI8 and AI58 signal/exit parameters remain frozen.",
            "50/50 is the primary predeclared portfolio; 75/25 and 25/75 are diagnostics, not post-hoc replacements.",
            "No allocation is selected or retuned from these results.",
            "The portfolio uses a common-history start so both sleeves are evaluated on identical dates.",
            "This is backtest/research evidence only and adds no live routing.",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Frozen AI8 + AI58 $5k portfolio diversification test")
    ap.add_argument("--btc", type=Path, required=True)
    ap.add_argument("--jpy", type=Path, required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    report = build_report(args.btc, args.jpy, dt(args.end))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=True, default=str), encoding="utf-8")

    print("AI8 + AI58 frozen $5k portfolio")
    for name, row in report["baseline_allocations"].items():
        print(
            f"{name:20s} ending=${row['ending_equity_usd']:.2f} "
            f"net={row['net_profit_pct']:.2f}% CAGR={row['cagr_pct']:.2f}% "
            f"PF={row['profit_factor']:.3f} DD={row['max_closed_trade_drawdown_pct']:.2f}%"
        )
    row = report["double_cost_allocations"]["ai8_50_ai58_50"]
    print(
        f"50/50 2x costs: ending=${row['ending_equity_usd']:.2f} "
        f"CAGR={row['cagr_pct']:.2f}% PF={row['profit_factor']:.3f} "
        f"DD={row['max_closed_trade_drawdown_pct']:.2f}%"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
