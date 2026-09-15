from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from math import floor, inf

from .config import TripleMACDNQConfig
from .indicators import macd_hist, tdfi


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
    contracts: float
    stop: float
    target: float
    entry_commission: float
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


def previous_window_low(values: list[float], i: int, lookback: int) -> float:
    if i < lookback:
        raise ValueError("insufficient prior bars")
    return min(values[i - lookback:i])


def previous_window_high(values: list[float], i: int, lookback: int) -> float:
    if i < lookback:
        raise ValueError("insufficient prior bars")
    return max(values[i - lookback:i])


def advance_long_a(
    state: int, *, long_pos: bool, mid_light_g: bool, short_red: bool,
    mid_dark_g: bool, tdfi_value: float | None, cfg: TripleMACDNQConfig,
) -> tuple[int, bool]:
    if not long_pos or cfg.trade_direction == "Short Only":
        return 0, False
    if state == 0 and mid_light_g:
        filter_ok = (not cfg.use_tdfi_filter) or (tdfi_value is not None and tdfi_value > cfg.tdfi_high)
        return (1 if filter_ok else 0), False
    if state == 1 and short_red:
        return 2, False
    if state == 2 and mid_dark_g:
        return 0, True
    return state, False


def advance_short_a(
    state: int, *, long_pos: bool, mid_light_r: bool, short_green: bool,
    mid_dark_r: bool, tdfi_value: float | None, cfg: TripleMACDNQConfig,
) -> tuple[int, bool]:
    if long_pos or cfg.trade_direction == "Long Only":
        return 0, False
    if state == 0 and mid_light_r:
        filter_ok = (not cfg.use_tdfi_filter) or (tdfi_value is not None and tdfi_value < cfg.tdfi_low)
        return (1 if filter_ok else 0), False
    if state == 1 and short_green:
        return 2, False
    if state == 2 and mid_dark_r:
        return 0, True
    return state, False


class TripleMACDNQBacktester:
    """Paper-only emulator for the supplied Trade Smart AI NQ1! preset.

    The engine mirrors the supplied Pine state machine for Entry A. Entry B is
    intentionally unsupported in the frozen NQ preset because the source CSV
    disables it. Market entries are created at signal-bar close and filled at
    the next bar open, matching Pine's default historical strategy behavior.
    """

    def __init__(self, config: TripleMACDNQConfig):
        config.validate()
        if config.enable_entry_b:
            raise NotImplementedError("NQ creator preset has Entry B disabled; do not enable it for parity")
        self.cfg = config

    def _contracts(self, price: float) -> float:
        raw = self.cfg.order_cash_usd / (price * self.cfg.point_value)
        return raw if self.cfg.allow_fractional_contracts else float(floor(raw))

    def _commission(self, contracts: float) -> float:
        return abs(contracts) * self.cfg.commission_usd_per_contract_per_order

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
        h_l = macd_hist(closes, self.cfg.long_fast, self.cfg.long_slow, self.cfg.macd_signal)
        h_m = macd_hist(closes, self.cfg.mid_fast, self.cfg.mid_slow, self.cfg.macd_signal)
        h_s = macd_hist(closes, self.cfg.short_fast, self.cfg.short_slow, self.cfg.macd_signal)
        tdf = tdfi(
            closes,
            self.cfg.tdfi_lookback,
            smooth=self.cfg.tdfi_smoothing,
            smooth_period=self.cfg.tdfi_smooth_period,
        )

        slip = self.cfg.slippage_ticks * self.cfg.min_tick
        trades: list[Trade] = []
        position: Trade | None = None
        pending: dict[str, object] | None = None
        long_state = 0
        short_state = 0
        no_reentry_until_index = -1

        def in_window(t: datetime) -> bool:
            return (trade_start is None or t >= trade_start) and (trade_end is None or t < trade_end)

        def close_position(when: datetime, px: float, reason: ExitReason) -> None:
            nonlocal position
            if position is None:
                return
            comm = self._commission(position.contracts)
            move = (px - position.entry_price) if position.side == Side.LONG else (position.entry_price - px)
            gross = move * self.cfg.point_value * position.contracts
            position.exit_time = when
            position.exit_price = px
            position.exit_commission = comm
            position.net_pnl_usd = gross - position.entry_commission - comm
            position.exit_reason = reason
            position = None

        for i, c in enumerate(candles):
            if trade_end is not None and c.time >= trade_end:
                break
            active = in_window(c.time)

            # Pine market order: signal at previous close, fill at this open.
            if pending is not None and active and position is None:
                side = Side(str(pending["side"]))
                fill = c.open + slip if side == Side.LONG else c.open - slip
                contracts = self._contracts(fill)
                if contracts >= 1:
                    position = Trade(
                        side=side,
                        signal_time=pending["signal_time"],
                        entry_time=c.time,
                        entry_price=fill,
                        contracts=contracts,
                        stop=float(pending["stop"]),
                        target=float(pending["target"]),
                        entry_commission=self._commission(contracts),
                    )
                    trades.append(position)
                pending = None

            exited_this_bar = False
            if position is not None and active:
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

                if reason == ExitReason.TARGET:
                    if position.side == Side.LONG:
                        px = max(position.target, c.open) if c.open >= position.target else position.target
                    else:
                        px = min(position.target, c.open) if c.open <= position.target else position.target
                    close_position(c.time, px, reason)
                    exited_this_bar = True
                elif reason == ExitReason.STOP:
                    if position.side == Side.LONG:
                        trigger = c.open if c.open < position.stop else position.stop
                        px = trigger - slip
                    else:
                        trigger = c.open if c.open > position.stop else position.stop
                        px = trigger + slip
                    close_position(c.time, px, reason)
                    exited_this_bar = True

            if exited_this_bar:
                long_state = 0
                short_state = 0
                no_reentry_until_index = i

            if not active or position is not None or i <= no_reentry_until_index:
                continue
            if i < 1 or i < self.cfg.sl_lookback:
                continue

            long_pos = h_l[i] > 0
            mid_light_g = h_m[i] > 0 and h_m[i] <= h_m[i - 1]
            mid_dark_g = h_m[i] > 0 and h_m[i] > h_m[i - 1]
            mid_light_r = h_m[i] < 0 and h_m[i] >= h_m[i - 1]
            mid_dark_r = h_m[i] < 0 and h_m[i] < h_m[i - 1]
            short_red = h_s[i] < 0
            short_green = h_s[i] > 0

            if not self.cfg.enable_entry_a:
                continue

            long_state, long_fire = advance_long_a(
                long_state,
                long_pos=long_pos,
                mid_light_g=mid_light_g,
                short_red=short_red,
                mid_dark_g=mid_dark_g,
                tdfi_value=tdf[i],
                cfg=self.cfg,
            )
            if long_fire:
                stop = previous_window_low(lows, i, self.cfg.sl_lookback)
                target = c.close + (c.close - stop) * self.cfg.risk_reward
                pending = {
                    "side": Side.LONG.value,
                    "signal_time": c.time,
                    "stop": stop,
                    "target": target,
                }

            if pending is None:
                short_state, short_fire = advance_short_a(
                    short_state,
                    long_pos=long_pos,
                    mid_light_r=mid_light_r,
                    short_green=short_green,
                    mid_dark_r=mid_dark_r,
                    tdfi_value=tdf[i],
                    cfg=self.cfg,
                )
                if short_fire:
                    stop = previous_window_high(highs, i, self.cfg.sl_lookback)
                    target = c.close - (stop - c.close) * self.cfg.risk_reward
                    pending = {
                        "side": Side.SHORT.value,
                        "signal_time": c.time,
                        "stop": stop,
                        "target": target,
                    }

        if close_at_end and position is not None:
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
