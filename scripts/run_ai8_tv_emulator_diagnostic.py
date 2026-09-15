from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from math import inf, floor

from ai_investing_lab.strategies.ai8_btc import AI8Config, Candle
from ai_investing_lab.strategies.ai8_btc.indicators import adx, atr, range_filter, supertrend_direction


@dataclass(frozen=True)
class Semantics:
    name: str
    qty_at_fill: bool = False
    stop_update_on_signal: bool = True
    allow_entry_bar_price_exit: bool = True
    qty_step: float | None = None


@dataclass
class Leg:
    signal_time: datetime
    entry_time: datetime
    entry_price: float
    qty: float
    entry_commission: float
    stop: float
    target: float
    exit_time: datetime | None = None
    exit_price: float | None = None
    exit_commission: float = 0.0
    pnl: float = 0.0
    reason: str | None = None


def parse_iso(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def load_csv(path: Path) -> list[Candle]:
    rows: list[Candle] = []
    with path.open("r", newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            rows.append(Candle(
                time=parse_iso(row["timestamp"]),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
            ))
    return rows


def round_down(value: float, step: float | None) -> float:
    if step is None:
        return value
    return floor(value / step + 1e-12) * step


def metrics(legs: list[Leg], initial: float) -> dict[str, float | int]:
    closed = [x for x in legs if x.exit_time is not None]
    wins = [x for x in closed if x.pnl > 0]
    losses = [x for x in closed if x.pnl <= 0]
    gp = sum(x.pnl for x in wins)
    gl = abs(sum(x.pnl for x in losses))
    net = sum(x.pnl for x in closed)
    pf = gp / gl if gl else (inf if gp else 0.0)
    equity = initial
    peak = initial
    dd = 0.0
    # TradingView reports individual closed trades in chronological close order.
    for leg in sorted(closed, key=lambda x: (x.exit_time, x.entry_time)):
        equity += leg.pnl
        peak = max(peak, equity)
        if peak > 0:
            dd = max(dd, (peak - equity) / peak)
    return {
        "trades": len(closed),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_pct": 100 * len(wins) / len(closed) if closed else 0.0,
        "net_profit_usd": net,
        "net_profit_pct": 100 * net / initial,
        "profit_factor": pf,
        "closed_trade_drawdown_pct": 100 * dd,
        "open_legs_at_end": len([x for x in legs if x.exit_time is None]),
    }


def run(candles: list[Candle], sem: Semantics) -> dict[str, object]:
    cfg = AI8Config.creator_fixed_cash()
    start = datetime(2020, 3, 1, tzinfo=timezone.utc)
    end = datetime(2024, 3, 1, tzinfo=timezone.utc)
    candles = sorted(candles, key=lambda c: c.time)
    highs = [c.high for c in candles]
    lows = [c.low for c in candles]
    closes = [c.close for c in candles]
    adxv = adx(highs, lows, closes, di_length=cfg.di_length, adx_smoothing=cfg.adx_smoothing)
    dirs = supertrend_direction(highs, lows, closes, factor=cfg.supertrend_factor, atr_length=cfg.supertrend_atr_length)
    stop_atr = atr(highs, lows, closes, cfg.stop_atr_length)
    _, _, range_short = range_filter(closes, period=cfg.range_period, multiplier=cfg.range_multiplier)

    slip = cfg.slippage_ticks * cfg.min_tick
    legs: list[Leg] = []
    open_legs: list[Leg] = []
    pending: dict[str, object] | None = None
    pending_close = False
    active_stop: float | None = None
    active_target: float | None = None

    def commission(value: float) -> float:
        return value * cfg.commission_pct_per_side / 100.0

    def close_all(when: datetime, px: float, reason: str) -> None:
        nonlocal open_legs
        for leg in open_legs:
            leg.exit_time = when
            leg.exit_price = px
            value = leg.qty * px
            leg.exit_commission = commission(value)
            leg.pnl = leg.qty * (px - leg.entry_price) - leg.entry_commission - leg.exit_commission
            leg.reason = reason
        open_legs = []

    for i, c in enumerate(candles):
        if c.time >= end:
            break
        in_window = c.time >= start

        if pending_close and open_legs and in_window:
            close_all(c.time, max(cfg.min_tick, c.open - slip), "range")
            active_stop = None
            active_target = None
        pending_close = False

        entered_now = False
        if pending is not None and in_window and len(open_legs) < cfg.pyramiding:
            fill = c.open + slip
            basis = fill if sem.qty_at_fill else float(pending["signal_close"])
            qty = round_down(cfg.fixed_cash_usd / basis, sem.qty_step)
            value = qty * fill
            leg = Leg(
                signal_time=pending["signal_time"],
                entry_time=c.time,
                entry_price=fill,
                qty=qty,
                entry_commission=commission(value),
                stop=float(pending["stop"]),
                target=float(pending["target"]),
            )
            legs.append(leg)
            open_legs.append(leg)
            entered_now = True
            if not sem.stop_update_on_signal:
                active_stop = leg.stop
                active_target = leg.target
                for old in open_legs:
                    old.stop = active_stop
                    old.target = active_target
        pending = None

        # Price-dependent strategy.exit orders can normally trigger on an entry bar.
        if open_legs and active_stop is not None and active_target is not None and (sem.allow_entry_bar_price_exit or not entered_now):
            stop_hit = c.low <= active_stop
            target_hit = c.high >= active_target
            if stop_hit or target_hit:
                if stop_hit and target_hit:
                    high_first = abs(c.open - c.high) < abs(c.open - c.low)
                    reason = "target" if high_first else "stop"
                elif stop_hit:
                    reason = "stop"
                else:
                    reason = "target"
                if reason == "target":
                    px = active_target
                else:
                    reference = c.open if c.open < active_stop else active_stop
                    px = max(cfg.min_tick, reference - slip)
                close_all(c.time, px, reason)
                active_stop = None
                active_target = None

        if not in_window:
            continue

        d = dirs[i]
        pd = dirs[i - 1] if i else None
        a = adxv[i]
        av = stop_atr[i]
        signal = d is not None and pd is not None and d - pd < 0 and a is not None and a > cfg.adx_limit
        if signal and av is not None:
            risk = av * cfg.stop_atr_multiplier
            new_stop = c.close - risk
            new_target = c.close + risk * cfg.risk_reward_ratio

            if sem.stop_update_on_signal and open_legs:
                active_stop = new_stop
                active_target = new_target
                for leg in open_legs:
                    leg.stop = new_stop
                    leg.target = new_target

            if len(open_legs) < cfg.pyramiding and pending is None:
                pending = {
                    "signal_time": c.time,
                    "signal_close": c.close,
                    "stop": new_stop,
                    "target": new_target,
                }
                if sem.stop_update_on_signal:
                    active_stop = new_stop
                    active_target = new_target

        if open_legs and range_short[i]:
            pending_close = True

    out = metrics(legs, cfg.initial_capital_usd)
    counts: dict[str, int] = {}
    for leg in legs:
        if leg.reason:
            counts[leg.reason] = counts.get(leg.reason, 0) + 1
    return {"semantics": asdict(sem), "metrics": out, "exit_counts": counts}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_path", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    candles = load_csv(args.csv_path)

    variants = [
        Semantics("baseline_signal_qty_signal_stop"),
        Semantics("cash_qty_at_fill", qty_at_fill=True),
        Semantics("stop_updates_only_after_new_fill", stop_update_on_signal=False),
        Semantics("fill_qty_and_fill_stop", qty_at_fill=True, stop_update_on_signal=False),
        Semantics("no_entry_bar_price_exit", allow_entry_bar_price_exit=False),
        Semantics("btc_qty_step_1e-5", qty_step=0.00001),
        Semantics("fill_qty_step_1e-5", qty_at_fill=True, qty_step=0.00001),
    ]
    payload = {
        "benchmark": {"trades": 319, "net_profit_pct": 637.97, "profit_factor": 1.969, "win_rate_pct": 44.51, "max_drawdown_pct": 27.87},
        "principle": "No strategy inputs changed; only TradingView broker-emulator/accounting interpretations are varied.",
        "variants": {v.name: run(candles, v) for v in variants},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, allow_nan=True), encoding="utf-8")
    print(json.dumps({k: v["metrics"] for k, v in payload["variants"].items()}, indent=2, allow_nan=True))


if __name__ == "__main__":
    main()
