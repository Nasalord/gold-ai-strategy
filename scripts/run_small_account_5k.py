from __future__ import annotations

import argparse
import json
from dataclasses import asdict, replace
from datetime import datetime, timezone
from math import floor, inf
from pathlib import Path

from ai_investing_lab.strategies.ai8_btc import AI8Backtester, AI8Config
from ai_investing_lab.strategies.ai2_eth import AI2Backtester, AI2Config
from ai_investing_lab.strategies.ai38_gbpusd import AI38Backtester, AI38Config
from ai_investing_lab.strategies.ai58_usdjpy import AI58Config
from ai_investing_lab.strategies.ai58_usdjpy.csv_runner import load_candles_csv as load_ai58
from ai_investing_lab.strategies.ai58_usdjpy.source_fidelity import SourceFaithfulAI58Backtester
from scripts.run_ai8_full_validation import load_csv as load_ai8
from scripts.run_ai2_full_validation import load_csv as load_ai2
from scripts.run_ai38_full_validation import load_csv as load_ai38

UTC = timezone.utc
STARTING_EQUITY = 5_000.0
TARGET_START = datetime(2016, 1, 1, tzinfo=UTC)
BTC_STEP = 0.0001
ETH_STEP = 0.001
FX_STEP = 1_000.0
CRYPTO_MIN_NOTIONAL = 10.0

CREATOR_WINDOWS = {
    "AI8": (datetime(2020, 3, 1, tzinfo=UTC), datetime(2024, 3, 1, tzinfo=UTC)),
    "AI2": (datetime(2020, 3, 1, tzinfo=UTC), datetime(2024, 3, 1, tzinfo=UTC)),
    "AI38": (datetime(2020, 3, 1, tzinfo=UTC), datetime(2024, 3, 1, tzinfo=UTC)),
    "AI58": (datetime(2021, 9, 1, tzinfo=UTC), datetime(2025, 9, 1, tzinfo=UTC)),
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


def summarize(pnls, notionals, commissions, skipped, start, end):
    wins = [x for x in pnls if x > 0]
    losses = [x for x in pnls if x <= 0]
    gp = sum(wins)
    gl = abs(sum(losses))
    pf = gp / gl if gl else (inf if gp else 0.0)
    equity = STARTING_EQUITY
    peak = equity
    minimum = equity
    max_dd = 0.0
    for pnl in pnls:
        equity += pnl
        peak = max(peak, equity)
        minimum = min(minimum, equity)
        if peak > 0:
            max_dd = max(max_dd, 100.0 * (peak - equity) / peak)
    years = max((end - start).total_seconds() / (365.25 * 86400.0), 1e-9)
    cagr = None if equity <= 0 else 100.0 * ((equity / STARTING_EQUITY) ** (1.0 / years) - 1.0)
    return {
        "starting_equity_usd": STARTING_EQUITY,
        "ending_equity_usd": equity,
        "net_profit_usd": equity - STARTING_EQUITY,
        "net_profit_pct": 100.0 * (equity / STARTING_EQUITY - 1.0),
        "cagr_pct": cagr,
        "trades": len(pnls),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_pct": 100.0 * len(wins) / len(pnls) if pnls else 0.0,
        "profit_factor": pf,
        "max_closed_trade_drawdown_pct": max_dd,
        "minimum_closed_trade_equity_usd": minimum,
        "ruin_or_nonpositive_equity": minimum <= 0,
        "skipped_for_granularity": skipped,
        "total_entry_notional_usd": sum(notionals),
        "turnover_multiple_of_starting_equity": sum(notionals) / STARTING_EQUITY,
        "commission_usd": sum(commissions),
        "commission_pct_of_starting_equity": 100.0 * sum(commissions) / STARTING_EQUITY,
    }


def simulate_single(trades, start, end, *, desired_qty, base_qty, entry_notional, commission):
    equity = STARTING_EQUITY
    pnls = []
    notionals = []
    commissions = []
    skipped = 0
    eligible = [
        t for t in trades
        if t.closed and t.exit_time is not None and start <= t.entry_time < end and t.exit_time < end
    ]
    eligible.sort(key=lambda t: (t.entry_time, t.exit_time))
    for trade in eligible:
        if equity <= 0:
            skipped += 1
            continue
        bq = float(base_qty(trade))
        qty = float(desired_qty(trade, equity))
        if bq <= 0 or qty <= 0:
            skipped += 1
            continue
        scale = qty / bq
        pnl = float(trade.net_pnl_usd) * scale
        pnls.append(pnl)
        notionals.append(float(entry_notional(trade, qty)))
        commissions.append(float(commission(trade)) * scale)
        equity += pnl
    return summarize(pnls, notionals, commissions, skipped, start, end)


def simulate_ai8(trades, start, end, fixed_cash):
    equity = STARTING_EQUITY
    pnls = []
    notionals = []
    commissions = []
    skipped = 0
    open_scale = {}
    eligible = [
        t for t in trades
        if t.closed and t.exit_time is not None and start <= t.entry_time < end and t.exit_time < end
    ]
    events = []
    for idx, trade in enumerate(eligible):
        reason = trade.exit_reason.value if trade.exit_reason is not None else ""
        exit_priority = 0 if reason == "range_filter" else 2
        events.append((trade.entry_time, 1, idx, "entry", trade))
        events.append((trade.exit_time, exit_priority, idx, "exit", trade))
    events.sort(key=lambda x: (x[0], x[1], x[2]))

    for _, _, idx, kind, trade in events:
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
            comm = float(trade.entry_commission_usd + trade.exit_commission_usd) * scale
            open_scale[idx] = (scale, notional, comm)
            continue

        scale, notional, comm = open_scale.pop(idx, (0.0, 0.0, 0.0))
        if scale <= 0:
            continue
        pnl = float(trade.net_pnl_usd) * scale
        pnls.append(pnl)
        notionals.append(notional)
        commissions.append(comm)
        equity += pnl

    return summarize(pnls, notionals, commissions, skipped, start, end)


def classify(baseline, stress, post):
    if baseline["ruin_or_nonpositive_equity"]:
        return "FAIL_SMALL_ACCOUNT_RUIN"
    if baseline["net_profit_pct"] <= 0 or baseline["profit_factor"] <= 1:
        return "FAIL_SMALL_ACCOUNT_FULL_HISTORY"
    if stress["net_profit_pct"] <= 0 or stress["profit_factor"] <= 1:
        return "FAIL_SMALL_ACCOUNT_COST_STRESS"
    if post["net_profit_pct"] <= 0 or post["profit_factor"] <= 1:
        return "WATCHLIST_POST_CREATOR_WEAK"
    if baseline["max_closed_trade_drawdown_pct"] >= 50:
        return "WATCHLIST_DRAWDOWN_HIGH"
    return "PASS_STAGE_3B_RESEARCH_GATE"


def windows_for(key, start, end, simulate):
    creator_start, creator_end = CREATOR_WINDOWS[key]
    result = {
        "pre_creator": simulate(start, creator_start),
        "creator_window": simulate(creator_start, creator_end),
        "post_creator_oos": simulate(creator_end, end),
        "rolling": {},
        "calendar_years": {},
    }
    for months in (6, 12, 24, 36, 60):
        a = max(start, month_shift(end, -months))
        result["rolling"][str(months)] = simulate(a, end)
    for year in range(start.year, end.year + 1):
        a = max(start, datetime(year, 1, 1, tzinfo=UTC))
        b = min(end, datetime(year + 1, 1, 1, tzinfo=UTC))
        if a < b:
            result["calendar_years"][str(year)] = simulate(a, b)
    return result


def build_ai8(candles, end):
    start = max(TARGET_START, candles[0].time)
    base_cfg = AI8Config.creator_fixed_cash()
    stress_cfg = AI8Config.creator_fixed_cash(commission_pct_per_side=0.20, slippage_ticks=4)
    base_trades = AI8Backtester(base_cfg).run(candles, trade_start=start, trade_end=end, close_at_end=False).trades
    stress_trades = AI8Backtester(stress_cfg).run(candles, trade_start=start, trade_end=end, close_at_end=False).trades
    sim = lambda a, b: simulate_ai8(base_trades, a, b, base_cfg.fixed_cash_usd)
    full = sim(start, end)
    stress = simulate_ai8(stress_trades, start, end, stress_cfg.fixed_cash_usd)
    windows = windows_for("AI8", start, end, sim)
    return {
        "strategy": "AI8 BTCUSDT 2H",
        "role": "primary contender",
        "scored_start": start.isoformat(),
        "end_exclusive": end.isoformat(),
        "deployment_model": {
            "starting_equity_usd": STARTING_EQUITY,
            "notional_rule": "1x realized-equity cap spread equally across seven possible pyramid legs",
            "quantity_step": "0.0001 BTC",
            "research_min_notional_usd": CRYPTO_MIN_NOTIONAL,
        },
        "baseline": full,
        "double_costs": stress,
        "windows": windows,
        "classification": classify(full, stress, windows["post_creator_oos"]),
        "frozen_config": asdict(base_cfg),
    }


def build_ai2(candles, end):
    start = max(TARGET_START, candles[0].time)
    base_cfg = AI2Config.creator_15m()
    stress_cfg = replace(base_cfg, commission_pct_per_side=0.20, slippage_ticks=4)
    base_trades = AI2Backtester(base_cfg).run(candles, trade_start=start, trade_end=end, close_at_end=False).trades
    stress_trades = AI2Backtester(stress_cfg).run(candles, trade_start=start, trade_end=end, close_at_end=False).trades

    def make_sim(trades):
        return lambda a, b: simulate_single(
            trades, a, b,
            desired_qty=lambda t, eq: (
                floor_step(eq / float(t.entry_price), ETH_STEP)
                if floor_step(eq / float(t.entry_price), ETH_STEP) * float(t.entry_price) >= CRYPTO_MIN_NOTIONAL
                else 0.0
            ),
            base_qty=lambda t: t.qty,
            entry_notional=lambda t, qty: qty * float(t.entry_price),
            commission=lambda t: t.entry_commission + t.exit_commission,
        )

    sim = make_sim(base_trades)
    full = sim(start, end)
    stress = make_sim(stress_trades)(start, end)
    windows = windows_for("AI2", start, end, sim)
    return {
        "strategy": "AI2 ETHUSDT 15m",
        "role": "primary contender",
        "scored_start": start.isoformat(),
        "end_exclusive": end.isoformat(),
        "deployment_model": {
            "starting_equity_usd": STARTING_EQUITY,
            "notional_rule": "single position capped at current realized equity; no borrowing",
            "quantity_step": "0.001 ETH",
            "research_min_notional_usd": CRYPTO_MIN_NOTIONAL,
        },
        "baseline": full,
        "double_costs": stress,
        "windows": windows,
        "classification": classify(full, stress, windows["post_creator_oos"]),
        "frozen_config": asdict(base_cfg),
    }


def build_ai38(candles, end):
    start = TARGET_START
    base_cfg = AI38Config.creator_4h()
    stress_cfg = AI38Config.creator_4h(commission_usd_per_contract_per_side=0.00010, slippage_ticks=40)
    base_trades = AI38Backtester(base_cfg).run(candles, trade_start=start, trade_end=end, close_at_end=False).trades
    stress_trades = AI38Backtester(stress_cfg).run(candles, trade_start=start, trade_end=end, close_at_end=False).trades

    def make_sim(trades):
        return lambda a, b: simulate_single(
            trades, a, b,
            desired_qty=lambda t, eq: floor_step(eq / float(t.entry_price), FX_STEP),
            base_qty=lambda t: t.qty_units,
            entry_notional=lambda t, qty: qty * float(t.entry_price),
            commission=lambda t: t.entry_commission + t.exit_commission,
        )

    sim = make_sim(base_trades)
    full = sim(start, end)
    stress = make_sim(stress_trades)(start, end)
    windows = windows_for("AI38", start, end, sim)
    return {
        "strategy": "AI38 GBPUSD 4H",
        "role": "secondary comparison",
        "scored_start": start.isoformat(),
        "end_exclusive": end.isoformat(),
        "deployment_model": {
            "starting_equity_usd": STARTING_EQUITY,
            "notional_rule": "GBP units rounded down so USD entry notional does not exceed realized equity",
            "quantity_step": "1,000 GBP base units",
        },
        "baseline": full,
        "double_costs": stress,
        "windows": windows,
        "classification": classify(full, stress, windows["post_creator_oos"]),
        "frozen_config": asdict(base_cfg),
        "deep_history_note": "The separate 2005-2020 backlog failure remains part of the strategy record.",
    }


def build_ai58(candles, end):
    start = TARGET_START
    selected = [c for c in candles if c.time < end]
    base_cfg = AI58Config.optimized_15m()
    stress_cfg = AI58Config.optimized_15m(slippage_ticks=24, commission_usd_per_standard_lot_per_side=7.0)
    base_trades = SourceFaithfulAI58Backtester(base_cfg).run(selected, close_open_position_at_end=False).trades
    stress_trades = SourceFaithfulAI58Backtester(stress_cfg).run(selected, close_open_position_at_end=False).trades

    def make_sim(trades):
        return lambda a, b: simulate_single(
            trades, a, b,
            desired_qty=lambda _t, eq: floor_step(eq, FX_STEP),
            base_qty=lambda t: t.quantity_base_usd,
            entry_notional=lambda _t, qty: qty,
            commission=lambda t: t.commission_usd,
        )

    sim = make_sim(base_trades)
    full = sim(start, end)
    stress = make_sim(stress_trades)(start, end)
    windows = windows_for("AI58", start, end, sim)
    return {
        "strategy": "AI58 USDJPY 15m ORB",
        "role": "primary contender",
        "scored_start": start.isoformat(),
        "end_exclusive": end.isoformat(),
        "deployment_model": {
            "starting_equity_usd": STARTING_EQUITY,
            "notional_rule": "USD base notional rounded down to 1,000-unit increments and capped at realized equity",
            "quantity_step": "1,000 USD base units",
        },
        "baseline": full,
        "double_costs": stress,
        "windows": windows,
        "classification": classify(full, stress, windows["post_creator_oos"]),
        "frozen_config": asdict(base_cfg),
    }


def main():
    ap = argparse.ArgumentParser(description="Stage 3B $5k small-account feasibility for frozen strategies")
    ap.add_argument("--btc", type=Path, required=True)
    ap.add_argument("--eth", type=Path, required=True)
    ap.add_argument("--gbp", type=Path, required=True)
    ap.add_argument("--jpy", type=Path, required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    end = dt(args.end)
    strategies = {
        "AI8": build_ai8(load_ai8(args.btc), end),
        "AI2": build_ai2(load_ai2(str(args.eth)), end),
        "AI58": build_ai58(load_ai58(args.jpy), end),
        "AI38": build_ai38(load_ai38(args.gbp), end),
    }
    report = {
        "stage": "Stage 3B small-account feasibility",
        "method": "Frozen signals; $5,000 starting equity; gross entry notional capped at current realized equity; no borrowing; coarse reproducible quantity increments; normal costs plus 2x-cost stress. AI8 spreads the cap over its seven allowed pyramid legs.",
        "granularity_assumptions": {
            "BTCUSDT": "0.0001 BTC, $10 research minimum notional",
            "ETHUSDT": "0.001 ETH, $10 research minimum notional",
            "FX": "1,000 base-currency units",
            "warning": "These are conservative research assumptions, not broker/exchange-specific live contract specifications.",
        },
        "end_exclusive": end.isoformat(),
        "strategies": strategies,
        "guardrails": [
            "Signal and exit parameters are unchanged.",
            "No OOS-driven retuning is permitted.",
            "2x costs are a stress test, not a parameter-selection input.",
            "Drawdown is closed-trade equity drawdown; intrabar mark-to-market risk can be worse.",
            "Passing Stage 3B means research feasibility only, not permission for live trading.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=True, default=str), encoding="utf-8")

    print("Stage 3B $5k small-account feasibility")
    for key, row in strategies.items():
        m = row["baseline"]
        c = row["double_costs"]
        cagr = m["cagr_pct"] if m["cagr_pct"] is not None else float("nan")
        print(
            f"{key}: {row['classification']} | ending=${m['ending_equity_usd']:.2f} "
            f"net={m['net_profit_pct']:.2f}% CAGR={cagr:.2f}% PF={m['profit_factor']:.3f} "
            f"DD={m['max_closed_trade_drawdown_pct']:.2f}% | 2x ending=${c['ending_equity_usd']:.2f} "
            f"PF={c['profit_factor']:.3f} DD={c['max_closed_trade_drawdown_pct']:.2f}%"
        )


if __name__ == "__main__":
    main()
