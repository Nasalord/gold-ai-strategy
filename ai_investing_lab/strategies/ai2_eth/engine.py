from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from math import inf

from .config import AI2Config
from .indicators import atr, crossover, moving_average


@dataclass(frozen=True)
class Candle:
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


class ExitReason(str, Enum):
    STOP = "stop"
    TARGET = "target"
    END_OF_TEST = "end_of_test"


@dataclass
class Trade:
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
    net_pnl_usd: float = 0.0
    exit_reason: ExitReason | None = None

    @property
    def closed(self) -> bool:
        return self.exit_time is not None


@dataclass(frozen=True)
class Metrics:
    trades: int
    wins: int
    losses: int
    win_rate_pct: float
    net_profit_usd: float
    net_profit_pct: float
    profit_factor: float
    max_closed_trade_drawdown_pct: float


@dataclass(frozen=True)
class BacktestResult:
    metrics: Metrics
    trades: tuple[Trade, ...]


class AI2Backtester:
    """Literal emulator for the supplied Pine v5 Triple MA strategy."""

    def __init__(self, config: AI2Config):
        config.validate()
        self.cfg = config

    def _commission(self, value: float) -> float:
        return value * self.cfg.commission_pct_per_side / 100.0

    def run(
        self,
        candles: list[Candle],
        *,
        trade_start: datetime | None = None,
        trade_end: datetime | None = None,
        close_at_end: bool = False,
    ) -> BacktestResult:
        candles = sorted(candles, key=lambda c: c.time)
        if not candles:
            return BacktestResult(self._metrics([]), ())

        source = [float(getattr(c, self.cfg.source)) for c in candles]
        highs = [c.high for c in candles]
        lows = [c.low for c in candles]
        closes = [c.close for c in candles]
        ma_a = moving_average(source, self.cfg.ma_a_length, self.cfg.ma_a_type)
        ma_b = moving_average(source, self.cfg.ma_b_length, self.cfg.ma_b_type)
        ma_c = moving_average(source, self.cfg.ma_c_length, self.cfg.ma_c_type)
        atrv = atr(highs, lows, closes, self.cfg.atr_length)

        slip = self.cfg.slippage_ticks * self.cfg.min_tick
        trades: list[Trade] = []
        position: Trade | None = None
        pending_entry: dict[str, object] | None = None
        last_active_bar: Candle | None = None

        def in_window(t: datetime) -> bool:
            if trade_start is not None and t < trade_start:
                return False
            if trade_end is not None and t >= trade_end:
                return False
            return True

        def close_position(when: datetime, raw_px: float, reason: ExitReason, *, stop_order: bool) -> None:
            nonlocal position
            if position is None:
                return
            px = raw_px
            if stop_order:
                px = max(self.cfg.min_tick, raw_px - slip)
            exit_value = position.qty * px
            exit_comm = self._commission(exit_value)
            gross = position.qty * (px - position.entry_price)
            position.exit_time = when
            position.exit_price = px
            position.exit_commission = exit_comm
            position.net_pnl_usd = gross - position.entry_commission - exit_comm
            position.exit_reason = reason
            position = None

        for i, c in enumerate(candles):
            if trade_end is not None and c.time >= trade_end:
                break
            active_window = in_window(c.time)
            if active_window:
                last_active_bar = c

            # Pine default process_orders_on_close=false: market entry created
            # at the prior close fills on this bar's open, with slippage.
            if pending_entry is not None and active_window and position is None:
                fill = max(self.cfg.min_tick, c.open + slip)
                qty = self.cfg.fixed_cash_usd / fill
                entry_value = qty * fill
                position = Trade(
                    signal_time=pending_entry["signal_time"],
                    entry_time=c.time,
                    entry_price=fill,
                    qty=qty,
                    entry_commission=self._commission(entry_value),
                    stop=float(pending_entry["stop"]),
                    target=float(pending_entry["target"]),
                )
                trades.append(position)
            pending_entry = None

            # Existing exit orders act intrabar before this close can replace
            # the stop/target with values from a new valid signal.
            if position is not None and active_window:
                stop_hit = c.low <= position.stop
                target_hit = c.high >= position.target
                reason: ExitReason | None = None
                if stop_hit and target_hit:
                    high_first = abs(c.open - c.high) < abs(c.open - c.low)
                    reason = ExitReason.TARGET if high_first else ExitReason.STOP
                elif stop_hit:
                    reason = ExitReason.STOP
                elif target_hit:
                    reason = ExitReason.TARGET

                if reason == ExitReason.TARGET and position is not None:
                    raw = c.open if c.open >= position.target else position.target
                    close_position(c.time, raw, reason, stop_order=False)
                elif reason == ExitReason.STOP and position is not None:
                    trigger = c.open if c.open < position.stop else position.stop
                    close_position(c.time, trigger, reason, stop_order=True)

            if not active_window:
                continue

            cond = (
                crossover(ma_a, ma_b, i)
                and ma_a[i] is not None
                and ma_b[i] is not None
                and ma_c[i] is not None
                and float(ma_a[i]) > float(ma_c[i])
                and float(ma_b[i]) > float(ma_c[i])
                and atrv[i] is not None
            )
            if not cond:
                continue

            stop = c.close - float(atrv[i]) * self.cfg.atr_stop_multiplier
            target = c.close + float(atrv[i]) * self.cfg.atr_take_profit_multiplier

            # The Pine source updates these var prices on every valid signal,
            # even when pyramiding prevents another entry. The stop may move
            # either upward or downward; preserving that is required for parity.
            if position is not None:
                position.stop = stop
                position.target = target
            else:
                pending_entry = {
                    "signal_time": c.time,
                    "stop": stop,
                    "target": target,
                }

        if close_at_end and position is not None and last_active_bar is not None:
            raw = max(self.cfg.min_tick, last_active_bar.close - slip)
            close_position(last_active_bar.time, raw, ExitReason.END_OF_TEST, stop_order=False)

        return BacktestResult(self._metrics(trades), tuple(trades))

    def _metrics(self, trades: list[Trade]) -> Metrics:
        closed = [t for t in trades if t.closed]
        wins = [t for t in closed if t.net_pnl_usd > 0]
        losses = [t for t in closed if t.net_pnl_usd <= 0]
        gross_profit = sum(t.net_pnl_usd for t in wins)
        gross_loss = abs(sum(t.net_pnl_usd for t in losses))
        net = sum(t.net_pnl_usd for t in closed)
        pf = gross_profit / gross_loss if gross_loss else (inf if gross_profit else 0.0)

        equity = self.cfg.initial_capital_usd
        peak = equity
        max_dd = 0.0
        for t in sorted(closed, key=lambda x: (x.exit_time, x.entry_time)):
            equity += t.net_pnl_usd
            peak = max(peak, equity)
            if peak > 0:
                max_dd = max(max_dd, (peak - equity) / peak)

        n = len(closed)
        return Metrics(
            trades=n,
            wins=len(wins),
            losses=len(losses),
            win_rate_pct=100.0 * len(wins) / n if n else 0.0,
            net_profit_usd=net,
            net_profit_pct=100.0 * net / self.cfg.initial_capital_usd,
            profit_factor=pf,
            max_closed_trade_drawdown_pct=100.0 * max_dd,
        )
