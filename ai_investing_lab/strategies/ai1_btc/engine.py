from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from math import inf

from .config import AI1Config
from .indicators import adx_with_ema, atr, crossover, crossunder, ssl_state, t3


@dataclass(frozen=True)
class Candle:
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


class Side(str, Enum):
    LONG = "long"
    SHORT = "short"


class ExitReason(str, Enum):
    STOP = "stop"
    TARGET = "target"
    T3_OR_SSL = "t3_or_ssl"


@dataclass
class Trade:
    side: Side
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


class AI1Backtester:
    def __init__(self, config: AI1Config):
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

        highs = [c.high for c in candles]
        lows = [c.low for c in candles]
        closes = [c.close for c in candles]
        ssl = ssl_state(highs, lows, closes, self.cfg.ssl_period)
        fast = t3(closes, self.cfg.t3_fast_length, self.cfg.t3_b)
        slow = t3(closes, self.cfg.t3_slow_length, self.cfg.t3_b)
        adxv, adxema = adx_with_ema(
            highs,
            lows,
            closes,
            self.cfg.di_length,
            self.cfg.adx_smoothing,
            self.cfg.adx_ema_length,
        )
        atrv = atr(highs, lows, closes, self.cfg.atr_length)

        slip = self.cfg.slippage_ticks * self.cfg.min_tick
        trades: list[Trade] = []
        position: Trade | None = None
        pending_close = False
        pending_entry: dict[str, object] | None = None

        def in_window(t: datetime) -> bool:
            if trade_start is not None and t < trade_start:
                return False
            if trade_end is not None and t >= trade_end:
                return False
            return True

        def close_position(when: datetime, raw_px: float, reason: ExitReason, *, market: bool) -> None:
            nonlocal position
            if position is None:
                return
            if market:
                px = raw_px - slip if position.side == Side.LONG else raw_px + slip
            else:
                px = raw_px
            px = max(self.cfg.min_tick, px)
            exit_value = abs(position.qty * px)
            exit_comm = self._commission(exit_value)
            if position.side == Side.LONG:
                gross = position.qty * (px - position.entry_price)
            else:
                gross = position.qty * (position.entry_price - px)
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

            # Pine's default process_orders_on_close=false: market orders created
            # on the previous close fill on this bar's open.
            if pending_close and position is not None and active_window:
                close_position(c.time, c.open, ExitReason.T3_OR_SSL, market=True)
            pending_close = False

            if pending_entry is not None and active_window:
                side = Side(str(pending_entry["side"]))
                # strategy.entry() in the opposite direction reverses an
                # existing position. The source normally also calls
                # strategy.close() on the same cross; this fallback preserves
                # Pine reversal behavior if an unusual SSL state blocks it.
                if position is not None and position.side != side:
                    close_position(c.time, c.open, ExitReason.T3_OR_SSL, market=True)
                if position is None:
                    fill = c.open + slip if side == Side.LONG else c.open - slip
                    fill = max(self.cfg.min_tick, fill)
                    qty = self.cfg.fixed_cash_usd / fill
                    entry_value = qty * fill
                    position = Trade(
                        side=side,
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

            # Price orders from strategy.exit are active intrabar. When both
            # stop and target are inside one historical bar, use TradingView's
            # standard OHLC-path heuristic (open nearer high => high first;
            # otherwise low first).
            if position is not None and active_window:
                if position.side == Side.LONG:
                    stop_hit = c.low <= position.stop
                    target_hit = c.high >= position.target
                else:
                    stop_hit = c.high >= position.stop
                    target_hit = c.low <= position.target

                reason: ExitReason | None = None
                if stop_hit and target_hit:
                    high_first = abs(c.open - c.high) < abs(c.open - c.low)
                    if position.side == Side.LONG:
                        reason = ExitReason.TARGET if high_first else ExitReason.STOP
                    else:
                        reason = ExitReason.STOP if high_first else ExitReason.TARGET
                elif stop_hit:
                    reason = ExitReason.STOP
                elif target_hit:
                    reason = ExitReason.TARGET

                if reason is not None and position is not None:
                    if reason == ExitReason.TARGET:
                        # Limit order: fill at the limit, or at a better open if
                        # the market gaps through it.
                        if position.side == Side.LONG:
                            raw = max(position.target, c.open) if c.open >= position.target else position.target
                        else:
                            raw = min(position.target, c.open) if c.open <= position.target else position.target
                        close_position(c.time, raw, reason, market=False)
                    else:
                        # Stop order: gaps fill at the open, otherwise at stop;
                        # TradingView slippage applies adversely to stop fills.
                        if position.side == Side.LONG:
                            trigger = c.open if c.open < position.stop else position.stop
                            raw = max(self.cfg.min_tick, trigger - slip)
                        else:
                            trigger = c.open if c.open > position.stop else position.stop
                            raw = trigger + slip
                        close_position(c.time, raw, reason, market=False)

            if not active_window:
                continue

            cross_up = crossover(fast, slow, i)
            cross_down = crossunder(fast, slow, i)
            a = adxv[i]
            ae = adxema[i]
            av = atrv[i]
            momentum_ok = a is not None and ae is not None and a > ae

            long_condition = cross_up and momentum_ok and ssl[i] > 0
            short_condition = cross_down and momentum_ok and ssl[i] < 0
            exit_long = cross_down or ssl[i] < 0
            exit_short = cross_up or ssl[i] > 0

            if position is not None:
                if position.side == Side.LONG and exit_long:
                    pending_close = True
                elif position.side == Side.SHORT and exit_short:
                    pending_close = True

            if av is not None:
                risk = self.cfg.atr_stop_multiplier * av
                reward = self.cfg.atr_take_profit_multiplier * av
                if long_condition:
                    pending_entry = {
                        "side": Side.LONG.value,
                        "signal_time": c.time,
                        "stop": c.close - risk,
                        "target": c.close + reward,
                    }
                elif short_condition:
                    pending_entry = {
                        "side": Side.SHORT.value,
                        "signal_time": c.time,
                        "stop": c.close + risk,
                        "target": c.close - reward,
                    }

        if close_at_end and position is not None and candles:
            last = candles[-1]
            close_position(last.time, last.close, ExitReason.T3_OR_SSL, market=True)

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
