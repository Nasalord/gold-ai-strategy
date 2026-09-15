from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import Enum
from math import inf
from zoneinfo import ZoneInfo

from .config import AI58Config, SizingMode, TradeDirection
from .indicators import compute_atr, compute_tdfi


class Side(str, Enum):
    LONG = "long"
    SHORT = "short"


class ExitReason(str, Enum):
    TAKE_PROFIT = "take_profit"
    STOP_LOSS = "stop_loss"
    FORCE_EXIT = "force_exit"
    DATA_END = "data_end"


@dataclass(frozen=True)
class Candle:
    time: datetime
    open: float
    high: float
    low: float
    close: float

    def validate(self) -> None:
        if self.time.tzinfo is None:
            raise ValueError("candle timestamps must be timezone-aware")
        if self.low > min(self.open, self.close, self.high):
            raise ValueError("candle low is inconsistent with OHLC")
        if self.high < max(self.open, self.close, self.low):
            raise ValueError("candle high is inconsistent with OHLC")
        if self.low <= 0:
            raise ValueError("USDJPY prices must be positive")


@dataclass
class Trade:
    session_date: date
    side: Side
    entry_time: datetime
    entry_price: float
    quantity_base_usd: float
    theoretical_quantity_base_usd: float
    notional_usd: float
    equity_at_entry_usd: float
    risk_usd: float
    risk_percent: float
    or_high: float
    or_low: float
    or_width: float
    base_distance_jpy: float
    stop_price: float
    target_price: float
    active_stop_price: float
    order_arm_time: datetime | None
    tdfi_at_arm: float | None
    initial_trailing_stop: float | None = None
    trailing_stop: float | None = None
    entry_slippage_price: float = 0.0
    exit_slippage_price: float = 0.0
    exit_time: datetime | None = None
    exit_price: float | None = None
    exit_reason: ExitReason | None = None
    ambiguous_same_bar: bool = False
    gross_pnl_usd: float = 0.0
    commission_usd: float = 0.0
    net_pnl_usd: float = 0.0
    mae_jpy: float = 0.0
    mfe_jpy: float = 0.0

    @property
    def closed(self) -> bool:
        return self.exit_time is not None

    @property
    def holding_minutes(self) -> float | None:
        if self.exit_time is None:
            return None
        return (self.exit_time - self.entry_time).total_seconds() / 60.0

    @property
    def r_multiple(self) -> float | None:
        if not self.closed or self.risk_usd <= 0:
            return None
        return self.net_pnl_usd / self.risk_usd


@dataclass(frozen=True)
class BacktestMetrics:
    trades: int
    wins: int
    losses: int
    long_trades: int
    short_trades: int
    win_rate_pct: float
    net_profit_usd: float
    net_profit_pct: float
    profit_factor: float
    expectancy_usd: float
    average_r: float
    max_drawdown_pct: float
    ambiguous_trades: int


@dataclass
class BacktestResult:
    trades: list[Trade]
    metrics: BacktestMetrics


@dataclass
class _Session:
    key: date
    range_high: float | None = None
    range_low: float | None = None
    range_locked: bool = False
    frozen_range_high: float | None = None
    frozen_range_low: float | None = None
    oco_active: bool = False
    pending_long: bool = False
    pending_short: bool = False
    trades_today: int = 0
    took_long_today: bool = False
    took_short_today: bool = False
    order_arm_time: datetime | None = None
    tdfi_at_arm: float | None = None


class AI58Backtester:
    """Research implementation of the uploaded René Balke ORB Pine engine.

    The class intentionally has no broker dependency. It models USDJPY P&L in a
    USD account by converting JPY quote-currency P&L at the exit price.
    """

    def __init__(self, config: AI58Config):
        config.validate()
        self.cfg = config
        self.tz = ZoneInfo(config.timezone)
        self.slippage = config.slippage_ticks * config.min_tick

    def run(
        self,
        candles: list[Candle],
        *,
        tdfi_override: dict[datetime, float | None] | None = None,
        close_open_position_at_end: bool = True,
    ) -> BacktestResult:
        if not candles:
            return BacktestResult([], self._metrics([]))

        candles = sorted(candles, key=lambda c: c.time)
        for candle in candles:
            candle.validate()

        closes = [c.close for c in candles]
        tdfi_series = compute_tdfi(closes, self.cfg.tdfi_lookback)
        atr_series = compute_atr(
            [c.high for c in candles],
            [c.low for c in candles],
            closes,
            self.cfg.trailing_atr_length,
        )

        trades: list[Trade] = []
        session: _Session | None = None
        position: Trade | None = None
        force_exit_next_bar = False
        prev_local_dt: datetime | None = None
        entered_this_bar = False

        for i, candle in enumerate(candles):
            entered_this_bar = False
            local_dt = candle.time.astimezone(self.tz)
            key = self._session_key(local_dt)
            tdfi = (
                tdfi_override[candle.time]
                if tdfi_override is not None and candle.time in tdfi_override
                else tdfi_series[i]
            )

            # A market close submitted on the preceding force-exit bar fills at
            # the next bar open because process_orders_on_close=false.
            if force_exit_next_bar and position is not None:
                self._update_excursions(position, candle)
                self._close_trade(
                    position,
                    candle.time,
                    self._market_exit_price(position.side, candle.open),
                    ExitReason.FORCE_EXIT,
                    exit_slippage=self.slippage,
                )
                position = None
                force_exit_next_bar = False

            if session is None or key != session.key:
                # Source behavior cancels pending entries and resets session
                # counters at the next range-start-defined session.
                session = _Session(key=key)

            range_start_dt = datetime.combine(key, self.cfg.range_start, self.tz)
            range_end_dt = datetime.combine(key, self.cfg.range_end, self.tz)
            next_session_dt = range_start_dt + timedelta(days=1)
            in_range = range_start_dt <= local_dt < range_end_dt
            after_range = range_end_dt <= local_dt < next_session_dt

            # Existing stop/limit exits were submitted on the previous bar. The
            # uploaded Pine script does not have calc_on_order_fills enabled, so
            # a newly filled entry cannot also hit a newly-created SL/TP on the
            # same historical chart bar.
            if position is not None:
                self._update_excursions(position, candle)
                if self._evaluate_active_exit(position, candle):
                    position = None

            # Previously armed OCO breakout orders can fill intrabar.
            if (
                position is None
                and after_range
                and session.oco_active
                and session.trades_today == 0
                and (session.pending_long or session.pending_short)
                and session.frozen_range_high is not None
                and session.frozen_range_low is not None
            ):
                side = self._entry_side_for_bar(session, candle)
                if side is not None:
                    position = self._open_trade(
                        side=side,
                        candle=candle,
                        session=session,
                        equity_usd=self._realized_equity(trades),
                        prev_candle=candles[i - 1] if i > 0 else None,
                        prev_atr=atr_series[i - 1] if i > 0 else None,
                    )
                    trades.append(position)
                    entered_this_bar = True
                    session.trades_today += 1
                    if side == Side.LONG:
                        session.took_long_today = True
                    else:
                        session.took_short_today = True
                    # OCO cancellation after the first fill.
                    session.pending_long = False
                    session.pending_short = False
                    session.oco_active = False
                    self._update_excursions(position, candle)

            # Build range using bar opening timestamps; end is exclusive.
            if in_range:
                session.range_high = (
                    candle.high
                    if session.range_high is None
                    else max(session.range_high, candle.high)
                )
                session.range_low = (
                    candle.low
                    if session.range_low is None
                    else min(session.range_low, candle.low)
                )

                bar_close = candle.time + timedelta(minutes=self.cfg.timeframe_minutes)
                is_last_range_bar = bar_close.astimezone(self.tz) >= range_end_dt
                if is_last_range_bar and not session.oco_active:
                    self._lock_and_arm(session, tdfi=tdfi, arm_time=bar_close)

            # Fallback mirrors canArmFallback for cases where the final range bar
            # did not pre-arm. Orders created here are available from next bar.
            if (
                after_range
                and position is None
                and session.trades_today == 0
                and not session.oco_active
                and not entered_this_bar
                and session.range_high is not None
                and session.range_low is not None
                and session.range_high > session.range_low
            ):
                self._lock_and_arm(
                    session,
                    tdfi=tdfi,
                    arm_time=candle.time + timedelta(minutes=self.cfg.timeframe_minutes),
                )

            # Update trailing stop at this bar close for use on the next bar.
            if position is not None and not entered_this_bar:
                self._update_trailing_stop(position, candle, atr_series[i])

            crossed_force_exit = (
                self.cfg.use_force_exit
                and self._clock_minutes(local_dt) >= self._time_minutes(self.cfg.force_exit)
                and (
                    prev_local_dt is None
                    or self._clock_minutes(prev_local_dt)
                    < self._time_minutes(self.cfg.force_exit)
                )
            )
            if crossed_force_exit and position is not None:
                force_exit_next_bar = True

            prev_local_dt = local_dt

        if position is not None and close_open_position_at_end:
            last = candles[-1]
            self._close_trade(
                position,
                last.time,
                self._market_exit_price(position.side, last.close),
                ExitReason.DATA_END,
                exit_slippage=self.slippage,
            )

        return BacktestResult(trades, self._metrics(trades))

    def _session_key(self, local_dt: datetime) -> date:
        clock = local_dt.timetz().replace(tzinfo=None)
        return (
            local_dt.date()
            if clock >= self.cfg.range_start
            else local_dt.date() - timedelta(days=1)
        )

    @staticmethod
    def _clock_minutes(dt: datetime) -> int:
        return dt.hour * 60 + dt.minute

    @staticmethod
    def _time_minutes(value) -> int:
        return value.hour * 60 + value.minute

    def _lock_and_arm(
        self,
        session: _Session,
        *,
        tdfi: float | None,
        arm_time: datetime,
    ) -> None:
        if session.range_high is None or session.range_low is None:
            return
        if session.range_high <= session.range_low:
            return

        session.range_locked = True
        session.frozen_range_high = session.range_high
        session.frozen_range_low = session.range_low
        session.order_arm_time = arm_time
        session.tdfi_at_arm = tdfi

        can_long = self.cfg.direction in (TradeDirection.BOTH, TradeDirection.LONG_ONLY)
        can_short = self.cfg.direction in (TradeDirection.BOTH, TradeDirection.SHORT_ONLY)
        if not self.cfg.allow_direction_switch_same_day:
            can_long = can_long and not session.took_short_today
            can_short = can_short and not session.took_long_today

        filter_long = True
        filter_short = True
        if self.cfg.use_tdfi:
            filter_long = tdfi is not None and tdfi > self.cfg.tdfi_filter_high
            filter_short = tdfi is not None and tdfi < self.cfg.tdfi_filter_low

        session.pending_long = can_long and filter_long
        session.pending_short = can_short and filter_short

        # The Pine source marks OCO active even when TDFI blocks both entries,
        # preventing a later retry during the same session.
        session.oco_active = True

    def _entry_side_for_bar(self, session: _Session, candle: Candle) -> Side | None:
        assert session.frozen_range_high is not None
        assert session.frozen_range_low is not None

        long_hit = session.pending_long and candle.high >= session.frozen_range_high
        short_hit = session.pending_short and candle.low <= session.frozen_range_low
        if not long_hit and not short_hit:
            return None
        if long_hit and not short_hit:
            return Side.LONG
        if short_hit and not long_hit:
            return Side.SHORT

        # TradingView's historical broker emulator assumes an intrabar path
        # based on whether the open is closer to the high or the low.
        return Side.LONG if self._path_high_first(candle) else Side.SHORT

    @staticmethod
    def _path_high_first(candle: Candle) -> bool:
        return abs(candle.open - candle.high) < abs(candle.open - candle.low)

    def _open_trade(
        self,
        *,
        side: Side,
        candle: Candle,
        session: _Session,
        equity_usd: float,
        prev_candle: Candle | None,
        prev_atr: float | None,
    ) -> Trade:
        assert session.frozen_range_high is not None
        assert session.frozen_range_low is not None

        if side == Side.LONG:
            raw_fill = max(session.frozen_range_high, candle.open)
            entry = raw_fill + self.slippage
            base_distance = max(entry - session.frozen_range_low, self.cfg.min_tick)
            risk_distance = base_distance * self.cfg.stop_mult
            stop = entry - risk_distance
            target = entry + risk_distance * self.cfg.tp_rr
        else:
            raw_fill = min(session.frozen_range_low, candle.open)
            entry = raw_fill - self.slippage
            base_distance = max(session.frozen_range_high - entry, self.cfg.min_tick)
            risk_distance = base_distance * self.cfg.stop_mult
            stop = entry + risk_distance
            target = entry - risk_distance * self.cfg.tp_rr

        theoretical_qty, qty = self._position_size(
            side=side,
            equity_usd=equity_usd,
            entry_price=entry,
            stop_price=stop,
        )
        risk_usd = self._loss_to_stop_usd(side, entry, stop, qty)
        risk_percent = 100.0 * risk_usd / equity_usd if equity_usd > 0 else inf

        initial_trail: float | None = None
        active_stop = stop
        if (
            self.cfg.use_trailing_atr
            and prev_candle is not None
            and prev_atr is not None
        ):
            if side == Side.LONG:
                initial_trail = prev_candle.close - self.cfg.trailing_atr_multiplier * prev_atr
                active_stop = max(active_stop, initial_trail)
            else:
                initial_trail = prev_candle.close + self.cfg.trailing_atr_multiplier * prev_atr
                active_stop = min(active_stop, initial_trail)

        return Trade(
            session_date=session.key,
            side=side,
            entry_time=candle.time,
            entry_price=entry,
            quantity_base_usd=qty,
            theoretical_quantity_base_usd=theoretical_qty,
            notional_usd=qty,
            equity_at_entry_usd=equity_usd,
            risk_usd=risk_usd,
            risk_percent=risk_percent,
            or_high=session.frozen_range_high,
            or_low=session.frozen_range_low,
            or_width=session.frozen_range_high - session.frozen_range_low,
            base_distance_jpy=base_distance,
            stop_price=stop,
            target_price=target,
            active_stop_price=active_stop,
            order_arm_time=session.order_arm_time,
            tdfi_at_arm=session.tdfi_at_arm,
            initial_trailing_stop=initial_trail,
            trailing_stop=initial_trail,
            entry_slippage_price=self.slippage,
        )

    def _position_size(
        self,
        *,
        side: Side,
        equity_usd: float,
        entry_price: float,
        stop_price: float,
    ) -> tuple[float, float]:
        if self.cfg.sizing_mode == SizingMode.CREATOR_FIXED_NOTIONAL:
            qty = self.cfg.fixed_notional_usd
            return qty, qty

        risk_per_base_usd = self._loss_to_stop_usd(side, entry_price, stop_price, 1.0)
        if risk_per_base_usd <= 0:
            raise ValueError("invalid stop geometry")
        risk_budget = equity_usd * (self.cfg.risk_per_trade_pct / 100.0)
        theoretical = risk_budget / risk_per_base_usd
        actual = min(theoretical, self.cfg.max_notional_usd)
        return theoretical, actual

    @staticmethod
    def _loss_to_stop_usd(
        side: Side, entry: float, stop: float, quantity_base_usd: float
    ) -> float:
        if stop <= 0:
            return inf
        quote_loss_jpy = (
            quantity_base_usd * (entry - stop)
            if side == Side.LONG
            else quantity_base_usd * (stop - entry)
        )
        return max(0.0, quote_loss_jpy / stop)

    @staticmethod
    def _gross_pnl_usd(
        side: Side, entry: float, exit_price: float, quantity_base_usd: float
    ) -> float:
        if exit_price <= 0:
            raise ValueError("exit price must be positive")
        quote_pnl_jpy = (
            quantity_base_usd * (exit_price - entry)
            if side == Side.LONG
            else quantity_base_usd * (entry - exit_price)
        )
        return quote_pnl_jpy / exit_price

    def _commission_usd(self, quantity_base_usd: float) -> float:
        lots = quantity_base_usd / self.cfg.standard_lot_base_units
        return 2.0 * lots * self.cfg.commission_usd_per_standard_lot_per_side

    def _market_exit_price(self, side: Side, reference: float) -> float:
        return (
            max(self.cfg.min_tick, reference - self.slippage)
            if side == Side.LONG
            else reference + self.slippage
        )

    def _evaluate_active_exit(self, trade: Trade, candle: Candle) -> bool:
        if trade.side == Side.LONG:
            stop_hit = candle.low <= trade.active_stop_price
            target_hit = candle.high >= trade.target_price
            if stop_hit and target_hit:
                trade.ambiguous_same_bar = True
                reason = (
                    ExitReason.TAKE_PROFIT
                    if self._path_high_first(candle)
                    else ExitReason.STOP_LOSS
                )
            elif stop_hit:
                reason = ExitReason.STOP_LOSS
            elif target_hit:
                reason = ExitReason.TAKE_PROFIT
            else:
                return False
        else:
            stop_hit = candle.high >= trade.active_stop_price
            target_hit = candle.low <= trade.target_price
            if stop_hit and target_hit:
                trade.ambiguous_same_bar = True
                reason = (
                    ExitReason.STOP_LOSS
                    if self._path_high_first(candle)
                    else ExitReason.TAKE_PROFIT
                )
            elif stop_hit:
                reason = ExitReason.STOP_LOSS
            elif target_hit:
                reason = ExitReason.TAKE_PROFIT
            else:
                return False

        if reason == ExitReason.TAKE_PROFIT:
            price = trade.target_price
            slip = 0.0
        elif trade.side == Side.LONG:
            price = max(self.cfg.min_tick, trade.active_stop_price - self.slippage)
            slip = self.slippage
        else:
            price = trade.active_stop_price + self.slippage
            slip = self.slippage

        self._close_trade(trade, candle.time, price, reason, exit_slippage=slip)
        return True

    def _update_trailing_stop(
        self, trade: Trade, candle: Candle, atr: float | None
    ) -> None:
        if not self.cfg.use_trailing_atr or atr is None:
            trade.active_stop_price = trade.stop_price
            return

        if trade.side == Side.LONG:
            candidate = candle.close - self.cfg.trailing_atr_multiplier * atr
            trade.trailing_stop = (
                candidate
                if trade.trailing_stop is None
                else max(trade.trailing_stop, candidate)
            )
            trade.active_stop_price = max(trade.stop_price, trade.trailing_stop)
        else:
            candidate = candle.close + self.cfg.trailing_atr_multiplier * atr
            trade.trailing_stop = (
                candidate
                if trade.trailing_stop is None
                else min(trade.trailing_stop, candidate)
            )
            trade.active_stop_price = min(trade.stop_price, trade.trailing_stop)

    @staticmethod
    def _update_excursions(trade: Trade, candle: Candle) -> None:
        if trade.side == Side.LONG:
            trade.mae_jpy = max(trade.mae_jpy, max(0.0, trade.entry_price - candle.low))
            trade.mfe_jpy = max(trade.mfe_jpy, max(0.0, candle.high - trade.entry_price))
        else:
            trade.mae_jpy = max(trade.mae_jpy, max(0.0, candle.high - trade.entry_price))
            trade.mfe_jpy = max(trade.mfe_jpy, max(0.0, trade.entry_price - candle.low))

    def _close_trade(
        self,
        trade: Trade,
        exit_time: datetime,
        exit_price: float,
        reason: ExitReason,
        *,
        exit_slippage: float,
    ) -> None:
        trade.exit_time = exit_time
        trade.exit_price = exit_price
        trade.exit_reason = reason
        trade.exit_slippage_price = exit_slippage
        trade.gross_pnl_usd = self._gross_pnl_usd(
            trade.side, trade.entry_price, exit_price, trade.quantity_base_usd
        )
        trade.commission_usd = self._commission_usd(trade.quantity_base_usd)
        trade.net_pnl_usd = trade.gross_pnl_usd - trade.commission_usd

    def _realized_equity(self, trades: list[Trade]) -> float:
        return self.cfg.initial_capital_usd + sum(
            t.net_pnl_usd for t in trades if t.closed
        )

    def _metrics(self, trades: list[Trade]) -> BacktestMetrics:
        closed = [t for t in trades if t.closed]
        wins = [t for t in closed if t.net_pnl_usd > 0]
        losses = [t for t in closed if t.net_pnl_usd <= 0]
        gross_profit = sum(t.net_pnl_usd for t in wins)
        gross_loss = abs(sum(t.net_pnl_usd for t in losses))
        pf = (
            gross_profit / gross_loss
            if gross_loss > 0
            else (inf if gross_profit > 0 else 0.0)
        )

        equity = self.cfg.initial_capital_usd
        peak = equity
        max_dd = 0.0
        for trade in closed:
            equity += trade.net_pnl_usd
            peak = max(peak, equity)
            if peak > 0:
                max_dd = max(max_dd, (peak - equity) / peak)

        net = sum(t.net_pnl_usd for t in closed)
        r_values = [t.r_multiple for t in closed if t.r_multiple is not None]
        n = len(closed)
        return BacktestMetrics(
            trades=n,
            wins=len(wins),
            losses=len(losses),
            long_trades=sum(t.side == Side.LONG for t in closed),
            short_trades=sum(t.side == Side.SHORT for t in closed),
            win_rate_pct=100.0 * len(wins) / n if n else 0.0,
            net_profit_usd=net,
            net_profit_pct=100.0 * net / self.cfg.initial_capital_usd,
            profit_factor=pf,
            expectancy_usd=net / n if n else 0.0,
            average_r=sum(r_values) / len(r_values) if r_values else 0.0,
            max_drawdown_pct=100.0 * max_dd,
            ambiguous_trades=sum(t.ambiguous_same_bar for t in closed),
        )
