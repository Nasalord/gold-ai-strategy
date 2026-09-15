from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from math import inf

from .config import AI38Config
from .indicators import crossover, crossunder, ema, growth_percent, momentum, rolling_high, rolling_low


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
    END = "end"


@dataclass
class Trade:
    side: Side
    signal_time: datetime
    entry_time: datetime
    entry_price: float
    qty_units: float
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


class AI38Backtester:
    def __init__(self, config: AI38Config):
        config.validate()
        self.cfg = config

    def _commission(self, qty_units: float) -> float:
        return abs(qty_units) * self.cfg.commission_usd_per_contract_per_side

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

        closes = [c.close for c in candles]
        lows = [c.low for c in candles]
        highs = [c.high for c in candles]
        fast_ema = ema(closes, self.cfg.ema_fast_length)
        slow_ema = ema(closes, self.cfg.ema_slow_length)
        mom_a = momentum(closes, self.cfg.momentum_a_length)
        mom_b = momentum(closes, self.cfg.momentum_b_length)

        slip = self.cfg.slippage_ticks * self.cfg.min_tick
        trades: list[Trade] = []
        position: Trade | None = None
        pending_entry: dict[str, object] | None = None
        seen_mom_b_cross_under = False
        seen_mom_b_cross_over = False

        def in_window(t: datetime) -> bool:
            if trade_start is not None and t < trade_start:
                return False
            if trade_end is not None and t >= trade_end:
                return False
            return True

        def close_position(when: datetime, px: float, reason: ExitReason) -> None:
            nonlocal position
            if position is None:
                return
            exit_comm = self._commission(position.qty_units)
            if position.side == Side.LONG:
                gross = position.qty_units * (px - position.entry_price)
            else:
                gross = position.qty_units * (position.entry_price - px)
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

            # Pine default: strategy.entry() market order created at prior close
            # fills at the next available tick (historically the next bar open).
            if pending_entry is not None and active_window and position is None:
                side = Side(str(pending_entry["side"]))
                fill = c.open + slip if side == Side.LONG else c.open - slip
                qty = self.cfg.fixed_units
                position = Trade(
                    side=side,
                    signal_time=pending_entry["signal_time"],
                    entry_time=c.time,
                    entry_price=fill,
                    qty_units=qty,
                    entry_commission=self._commission(qty),
                    stop=float(pending_entry["stop"]),
                    target=float(pending_entry["target"]),
                )
                trades.append(position)
            pending_entry = None

            # strategy.exit() bracket is active after the entry fill. Use the
            # TradingView historical OHLC path heuristic if both prices touch.
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

                if reason == ExitReason.TARGET and position is not None:
                    # Limit exits can receive a better fill when the bar gaps
                    # beyond the limit before the emulator first sees price.
                    if position.side == Side.LONG:
                        px = max(position.target, c.open) if c.open >= position.target else position.target
                    else:
                        px = min(position.target, c.open) if c.open <= position.target else position.target
                    close_position(c.time, px, reason)
                elif reason == ExitReason.STOP and position is not None:
                    # Stop orders gap at the open and then receive adverse
                    # configured slippage, matching TradingView's slippage model.
                    if position.side == Side.LONG:
                        trigger = c.open if c.open < position.stop else position.stop
                        px = trigger - slip
                    else:
                        trigger = c.open if c.open > position.stop else position.stop
                        px = trigger + slip
                    close_position(c.time, px, reason)

            if not active_window:
                # Still update source-history cross state below so valuewhen()
                # semantics are initialized by warmup data.
                pass

            cross_under_b = crossunder(mom_b, 0.0, i)
            cross_over_b = crossover(mom_b, 0.0, i)
            if cross_under_b:
                seen_mom_b_cross_under = True
            if cross_over_b:
                seen_mom_b_cross_over = True

            if not active_window or position is not None:
                continue
            fe = fast_ema[i]
            se = slow_ema[i]
            ma = mom_a[i]
            mb = mom_b[i]
            if fe is None or se is None or ma is None or mb is None:
                continue

            long_growth = (
                growth_percent(fast_ema, i, self.cfg.ema_fast_lookback, rising=True)
                >= self.cfg.ema_fast_growth_percent
                and growth_percent(slow_ema, i, self.cfg.ema_slow_lookback, rising=True)
                >= self.cfg.ema_slow_growth_percent
            )
            short_growth = (
                growth_percent(fast_ema, i, self.cfg.ema_fast_lookback, rising=False)
                >= self.cfg.ema_fast_growth_percent
                and growth_percent(slow_ema, i, self.cfg.ema_slow_lookback, rising=False)
                >= self.cfg.ema_slow_growth_percent
            )
            if not self.cfg.use_ema_growth_check:
                growth_final = True
            elif self.cfg.trade_direction == "Longs Only":
                growth_final = long_growth
            elif self.cfg.trade_direction == "Shorts Only":
                growth_final = short_growth
            else:
                # Literal Pine source behavior: Both uses OR, and that same
                # combined gate is applied to both long and short conditions.
                growth_final = long_growth or short_growth

            long_condition = (
                float(fe) > float(se)
                and float(ma) > 0.0
                and seen_mom_b_cross_under
                and cross_over_b
                and growth_final
            )
            short_condition = (
                float(fe) < float(se)
                and float(ma) < 0.0
                and seen_mom_b_cross_over
                and cross_under_b
                and growth_final
            )

            if self.cfg.trade_direction != "Shorts Only" and long_condition:
                if self.cfg.candle_lookback:
                    stop = rolling_low(lows, i, self.cfg.candle_lookback)
                else:
                    stop = float(se)
                if stop is not None:
                    target = c.close + (c.close - stop) * self.cfg.risk_reward_ratio
                    pending_entry = {
                        "side": Side.LONG.value,
                        "signal_time": c.time,
                        "stop": stop,
                        "target": target,
                    }
            elif self.cfg.trade_direction != "Longs Only" and short_condition:
                stop = rolling_high(highs, i, self.cfg.candle_lookback)
                if stop is not None:
                    target = c.close - (stop - c.close) * self.cfg.risk_reward_ratio
                    pending_entry = {
                        "side": Side.SHORT.value,
                        "signal_time": c.time,
                        "stop": stop,
                        "target": target,
                    }

        if close_at_end and position is not None and candles:
            last = candles[-1]
            px = last.close - slip if position.side == Side.LONG else last.close + slip
            close_position(last.time, px, ExitReason.END)

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
