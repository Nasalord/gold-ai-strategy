from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from math import inf

from ai_investing_lab.strategies.ai8_btc import AI8Config, Candle
from ai_investing_lab.strategies.ai8_btc.indicators import adx, atr, range_filter, supertrend_direction


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
    out: list[Candle] = []
    with path.open("r", newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            out.append(Candle(
                time=parse_iso(row["timestamp"]),
                open=float(row["open"]), high=float(row["high"]),
                low=float(row["low"]), close=float(row["close"]),
            ))
    return out


def summarize(legs: list[Leg], initial: float) -> dict[str, float | int]:
    closed = [x for x in legs if x.exit_time is not None]
    wins = [x for x in closed if x.pnl > 0]
    losses = [x for x in closed if x.pnl <= 0]
    gp = sum(x.pnl for x in wins)
    gl = abs(sum(x.pnl for x in losses))
    net = sum(x.pnl for x in closed)
    equity = initial
    peak = initial
    dd = 0.0
    for x in sorted(closed, key=lambda z: (z.exit_time, z.entry_time)):
        equity += x.pnl
        peak = max(peak, equity)
        if peak > 0:
            dd = max(dd, (peak - equity) / peak)
    return {
        "trades": len(closed),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_pct": 100 * len(wins) / len(closed) if closed else 0.0,
        "net_profit_pct": 100 * net / initial,
        "profit_factor": gp / gl if gl else (inf if gp else 0.0),
        "closed_trade_drawdown_pct": 100 * dd,
        "open_legs_at_end": len([x for x in legs if x.exit_time is None]),
    }


def run(candles: list[Candle], mode: str) -> dict[str, object]:
    cfg = AI8Config.creator_fixed_cash()
    start = datetime(2020, 3, 1, tzinfo=timezone.utc)
    end = datetime(2024, 3, 1, tzinfo=timezone.utc)
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

    def fee(value: float) -> float:
        return value * cfg.commission_pct_per_side / 100.0

    def close_leg(leg: Leg, when: datetime, px: float, reason: str) -> None:
        leg.exit_time = when
        leg.exit_price = px
        leg.exit_commission = fee(leg.qty * px)
        leg.pnl = leg.qty * (px - leg.entry_price) - leg.entry_commission - leg.exit_commission
        leg.reason = reason

    def close_all(when: datetime, px: float, reason: str) -> None:
        nonlocal open_legs
        for leg in open_legs:
            close_leg(leg, when, px, reason)
        open_legs = []

    for i, c in enumerate(candles):
        if c.time >= end:
            break
        in_window = c.time >= start

        if pending_close and open_legs and in_window:
            close_all(c.time, max(cfg.min_tick, c.open - slip), "range")
        pending_close = False

        if pending is not None and in_window and len(open_legs) < cfg.pyramiding:
            fill = c.open + slip
            qty = cfg.fixed_cash_usd / float(pending["signal_close"])
            leg = Leg(
                signal_time=pending["signal_time"], entry_time=c.time,
                entry_price=fill, qty=qty, entry_commission=fee(qty * fill),
                stop=float(pending["stop"]), target=float(pending["target"]),
            )
            legs.append(leg)
            open_legs.append(leg)
        pending = None

        if open_legs and mode != "no_stop_range_only":
            if mode == "shared_latest":
                stop = open_legs[-1].stop
                target = open_legs[-1].target
                stop_hit = c.low <= stop
                target_hit = c.high >= target
                if stop_hit or target_hit:
                    if stop_hit and target_hit:
                        high_first = abs(c.open - c.high) < abs(c.open - c.low)
                        reason = "target" if high_first else "stop"
                    elif stop_hit:
                        reason = "stop"
                    else:
                        reason = "target"
                    px = target if reason == "target" else max(cfg.min_tick, (c.open if c.open < stop else stop) - slip)
                    close_all(c.time, px, reason)
            elif mode == "per_leg_original":
                survivors: list[Leg] = []
                for leg in open_legs:
                    stop_hit = c.low <= leg.stop
                    target_hit = c.high >= leg.target
                    if not stop_hit and not target_hit:
                        survivors.append(leg)
                        continue
                    if stop_hit and target_hit:
                        high_first = abs(c.open - c.high) < abs(c.open - c.low)
                        reason = "target" if high_first else "stop"
                    elif stop_hit:
                        reason = "stop"
                    else:
                        reason = "target"
                    px = leg.target if reason == "target" else max(cfg.min_tick, (c.open if c.open < leg.stop else leg.stop) - slip)
                    close_leg(leg, c.time, px, reason)
                open_legs = survivors
            else:
                raise ValueError(mode)

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
            if mode == "shared_latest":
                for leg in open_legs:
                    leg.stop = new_stop
                    leg.target = new_target
            if len(open_legs) < cfg.pyramiding:
                pending = {
                    "signal_time": c.time,
                    "signal_close": c.close,
                    "stop": new_stop,
                    "target": new_target,
                }

        if open_legs and range_short[i]:
            pending_close = True

    counts: dict[str, int] = {}
    for x in legs:
        if x.reason:
            counts[x.reason] = counts.get(x.reason, 0) + 1
    return {"metrics": summarize(legs, cfg.initial_capital_usd), "exit_counts": counts}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_path", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    candles = load_csv(args.csv_path)
    variants = {mode: run(candles, mode) for mode in ["shared_latest", "per_leg_original", "no_stop_range_only"]}
    payload = {
        "benchmark": {"trades": 319, "net_profit_pct": 637.97, "profit_factor": 1.969, "win_rate_pct": 44.51, "max_drawdown_pct": 27.87},
        "variants": variants,
        "note": "Controls only. No strategy input is altered; this isolates strategy.exit scope / stop contribution.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, allow_nan=True), encoding="utf-8")
    print(json.dumps({k: v["metrics"] for k, v in variants.items()}, indent=2, allow_nan=True))


if __name__ == "__main__":
    main()
