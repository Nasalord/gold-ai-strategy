from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from enum import Enum
from math import inf
from zoneinfo import ZoneInfo

from .config import AI65Config, ExecutionMode, SizingMode, TDFIGating
from .tdfi import compute_tdfi


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


@dataclass
class Trade:
    session_date: date
    entry_time: datetime
    entry_price: float
    quantity: float
    theoretical_quantity: float
    notional_exposure: float
    equity_at_entry: float
    risk_dollars: float
    risk_percent: float
    or_high: float
    or_low: float
    or_width: float
    base_distance: float
    stop_price: float
    target_price: float
    order_arm_time: datetime | None
    breakout_time: datetime | None
    tdfi_at_range_end: float | None
    tdfi_at_arm: float | None
    tdfi_at_entry: float | None
    entry_slippage_cost: float = 0.0
    exit_slippage_cost: float = 0.0
    exit_time: datetime | None = None
    exit_price: float | None = None
    exit_reason: ExitReason | None = None
    ambiguous_same_bar: bool = False
    commission: float = 0.0
    gross_pnl: float = 0.0
    net_pnl: float = 0.0
    mae_price: float = 0.0
    mfe_price: float = 0.0

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
        if not self.closed or self.risk_dollars <= 0:
            return None
        return self.net_pnl / self.risk_dollars


@dataclass(frozen=True)
class BacktestMetrics:
    trades: int
    wins: int
    losses: int
    win_rate_pct: float
    gross_profit: float
    gross_loss: float
    net_profit: float
    net_profit_pct: float
    profit_factor: float
    expectancy: float
    average_winner: float
    average_loser: float
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
    oco_active: bool = False
    pending_long: bool = False
    traded: bool = False
    frozen_range_low: float | None = None
    tdfi_at_range_end: float | None = None
    tdfi_at_arm: float | None = None
    order_arm_time: datetime | None = None
    guarded_block: bool = False


class AI65Backtester:
    """Deterministic AI65 ORB research simulator.

    It is intentionally isolated from broker adapters. The implementation can
    reproduce the aggressive creator sizing for parity research, or use capped
    risk-based sizing in guarded simulation mode. It cannot submit live orders.
    """

    def __init__(self, config: AI65Config):
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
        computed_tdfi = compute_tdfi(closes, self.cfg.tdfi_lookback)

        trades: list[Trade] = []
        session: _Session | None = None
        position: Trade | None = None
        force_exit_next_bar = False
        prev_local_dt: datetime | None = None

        for i, candle in enumerate(candles):
            local_dt = candle.time.astimezone(self.tz)
            key = self._session_key(local_dt)
            tdfi = (
                tdfi_override.get(candle.time)
                if tdfi_override is not None and candle.time in tdfi_override
                else computed_tdfi[i]
            )

            # Market force exits generated on the previous completed bar fill at
            # this bar's open, matching process_orders_on_close=false.
            if force_exit_next_bar and position is not None:
                self._update_excursions(position, candle)
                self._close_trade(
                    position,
                    candle.time,
                    max(0.0, candle.open - self.slippage),
                    ExitReason.FORCE_EXIT,
                    exit_slippage=self.slippage,
                )
                position = None
                force_exit_next_bar = False

            if session is None or key != session.key:
                session = _Session(key=key)
                # Matches source behavior: pending entry state is reset at the
                # new session. An existing position is not silently closed.

            local_clock = local_dt.timetz().replace(tzinfo=None)
            range_start_dt = datetime.combine(key, self.cfg.range_start, self.tz)
            range_end_dt = datetime.combine(key, self.cfg.range_end, self.tz)
            in_range = range_start_dt <= local_dt < range_end_dt

            # Guarded research mode rejects/cancels entries from force-exit time onward.
            if (
                self.cfg.execution_mode == ExecutionMode.GUARDED
                and local_clock >= self.cfg.force_exit
            ):
                session.pending_long = False
                session.guarded_block = True

            # A previously armed stop can fill intrabar after the range.
            if (
                position is None
                and session.pending_long
                and not session.traded
                and not session.guarded_block
                and not in_range
                and session.range_high is not None
                and session.frozen_range_low is not None
                and candle.high >= session.range_high
            ):
                filter_ok = True
                if self.cfg.use_tdfi and self.cfg.tdfi_gating == TDFIGating.ENTRY_TIME:
                    filter_ok = tdfi is not None and tdfi > self.cfg.tdfi_long_threshold

                if filter_ok:
                    raw_fill = max(session.range_high, candle.open)
                    entry_price = raw_fill + self.slippage
                    base_distance = max(
                        entry_price - session.frozen_range_low,
                        self.cfg.min_tick,
                    )
                    stop_price = entry_price - base_distance * self.cfg.stop_mult
                    target_price = entry_price + base_distance * self.cfg.target_mult

                    equity = self._realized_equity(trades)
                    theoretical_qty, quantity = self._position_size(
                        equity=equity,
                        entry_price=entry_price,
                        stop_price=stop_price,
                    )
                    risk_dollars = quantity * (entry_price - stop_price)
                    risk_percent = (
                        100.0 * risk_dollars / equity if equity > 0 else inf
                    )

                    position = Trade(
                        session_date=session.key,
                        entry_time=candle.time,
                        entry_price=entry_price,
                        quantity=quantity,
                        theoretical_quantity=theoretical_qty,
                        notional_exposure=quantity * entry_price,
                        equity_at_entry=equity,
                        risk_dollars=risk_dollars,
                        risk_percent=risk_percent,
                        or_high=session.range_high,
                        or_low=session.frozen_range_low,
                        or_width=session.range_high - session.frozen_range_low,
                        base_distance=base_distance,
                        stop_price=stop_price,
                        target_price=target_price,
                        order_arm_time=session.order_arm_time,
                        breakout_time=candle.time,
                        tdfi_at_range_end=session.tdfi_at_range_end,
                        tdfi_at_arm=session.tdfi_at_arm,
                        tdfi_at_entry=tdfi,
                        entry_slippage_cost=quantity * self.slippage,
                    )
                    trades.append(position)
                    session.traded = True
                    session.pending_long = False

                    # With bar OHLC alone the exact post-entry path may be
                    # unknowable. Resolve conservatively and flag ambiguity.
                    self._update_excursions(position, candle)
                    position, closed = self._evaluate_exit_on_bar(position, candle)
                    if closed:
                        position = None

            # Manage an already-open trade using conservative OHLC ordering.
            elif position is not None:
                self._update_excursions(position, candle)
                position, closed = self._evaluate_exit_on_bar(position, candle)
                if closed:
                    position = None

            # Build the opening range. End timestamp is excluded.
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

                bar_close_utc = candle.time + timedelta(
                    minutes=self.cfg.timeframe_minutes
                )
                bar_close_local = bar_close_utc.astimezone(self.tz)
                is_last_range_bar = bar_close_local >= range_end_dt

                if is_last_range_bar and not session.oco_active:
                    if (
                        session.range_high is not None
                        and session.range_low is not None
                        and session.range_high > session.range_low
                    ):
                        session.range_locked = True
                        session.frozen_range_low = session.range_low
                        session.tdfi_at_range_end = tdfi
                        session.tdfi_at_arm = tdfi
                        session.order_arm_time = bar_close_utc

                        if self.cfg.tdfi_gating == TDFIGating.ENTRY_TIME:
                            # Video hypothesis: the completed range is always armed,
                            # then TDFI is checked only when price breaks the OR high.
                            session.pending_long = True
                        else:
                            filter_ok = (
                                not self.cfg.use_tdfi
                                or (
                                    tdfi is not None
                                    and tdfi > self.cfg.tdfi_long_threshold
                                )
                            )
                            if filter_ok:
                                session.pending_long = True

                        # Source semantics set ocoActive even when arm-time TDFI
                        # blocks order creation, so they do not retry later.
                        # Entry-time/video semantics arm unconditionally and keep
                        # waiting for a breakout bar whose TDFI agrees.
                        session.oco_active = True

            # Source force-exit condition is evaluated using the bar's opening
            # timestamp and fills on the next available bar open.
            crossed_force_exit = (
                self.cfg.use_force_exit
                and local_clock >= self.cfg.force_exit
                and (
                    prev_local_dt is None
                    or prev_local_dt.date() != local_dt.date()
                    or prev_local_dt.timetz().replace(tzinfo=None) < self.cfg.force_exit
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
                max(0.0, last.close - self.slippage),
                ExitReason.DATA_END,
                exit_slippage=self.slippage,
            )

        return BacktestResult(trades, self._metrics(trades))

    def _session_key(self, local_dt: datetime) -> date:
        start = self.cfg.range_start
        local_clock = local_dt.timetz().replace(tzinfo=None)
        return (
            local_dt.date()
            if local_clock >= start
            else (local_dt.date() - timedelta(days=1))
        )

    def _realized_equity(self, trades: list[Trade]) -> float:
        return self.cfg.initial_capital + sum(t.net_pnl for t in trades if t.closed)

    def _position_size(
        self,
        *,
        equity: float,
        entry_price: float,
        stop_price: float,
    ) -> tuple[float, float]:
        if entry_price <= 0:
            raise ValueError("entry_price must be positive")

        if self.cfg.sizing_mode == SizingMode.CREATOR_FIXED_NOTIONAL:
            qty = self.cfg.fixed_notional / entry_price
            return qty, qty

        risk_per_contract = entry_price - stop_price
        if risk_per_contract <= 0:
            raise ValueError("stop must be below entry for a long trade")

        risk_budget = equity * (self.cfg.risk_per_trade_pct / 100.0)
        theoretical_qty = risk_budget / risk_per_contract
        cap_qty = self.cfg.max_notional / entry_price
        actual_qty = min(theoretical_qty, cap_qty)
        return theoretical_qty, actual_qty

    def _update_excursions(self, trade: Trade, candle: Candle) -> None:
        trade.mae_price = max(trade.mae_price, max(0.0, trade.entry_price - candle.low))
        trade.mfe_price = max(trade.mfe_price, max(0.0, candle.high - trade.entry_price))

    def _evaluate_exit_on_bar(self, trade: Trade, candle: Candle) -> tuple[Trade, bool]:
        stop_hit = candle.low <= trade.stop_price
        target_hit = candle.high >= trade.target_price

        if stop_hit and target_hit:
            trade.ambiguous_same_bar = True
            exit_price = max(0.0, trade.stop_price - self.slippage)
            self._close_trade(
                trade,
                candle.time,
                exit_price,
                ExitReason.STOP_LOSS,
                exit_slippage=self.slippage,
            )
            return trade, True

        if stop_hit:
            exit_price = max(0.0, trade.stop_price - self.slippage)
            self._close_trade(
                trade,
                candle.time,
                exit_price,
                ExitReason.STOP_LOSS,
                exit_slippage=self.slippage,
            )
            return trade, True

        if target_hit:
            # TradingView limit exits are filled at the limit price; slippage is
            # applied to stop/market fills, not to the limit target.
            self._close_trade(
                trade,
                candle.time,
                trade.target_price,
                ExitReason.TAKE_PROFIT,
                exit_slippage=0.0,
            )
            return trade, True

        return trade, False

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
        trade.exit_slippage_cost = trade.quantity * exit_slippage
        trade.gross_pnl = trade.quantity * (exit_price - trade.entry_price)
        trade.commission = (
            2.0 * trade.quantity * self.cfg.commission_per_contract_per_side
        )
        trade.net_pnl = trade.gross_pnl - trade.commission

    def _metrics(self, trades: list[Trade]) -> BacktestMetrics:
        closed = [t for t in trades if t.closed]
        wins = [t for t in closed if t.net_pnl > 0]
        losses = [t for t in closed if t.net_pnl <= 0]

        gross_profit = sum(t.net_pnl for t in wins)
        gross_loss_abs = abs(sum(t.net_pnl for t in losses))
        pf = (
            gross_profit / gross_loss_abs
            if gross_loss_abs > 0
            else (inf if gross_profit > 0 else 0.0)
        )

        equity = self.cfg.initial_capital
        peak = equity
        max_dd = 0.0
        for trade in closed:
            equity += trade.net_pnl
            peak = max(peak, equity)
            if peak > 0:
                max_dd = max(max_dd, (peak - equity) / peak)

        net = sum(t.net_pnl for t in closed)
        n = len(closed)
        r_values = [t.r_multiple for t in closed if t.r_multiple is not None]

        return BacktestMetrics(
            trades=n,
            wins=len(wins),
            losses=len(losses),
            win_rate_pct=(100.0 * len(wins) / n) if n else 0.0,
            gross_profit=gross_profit,
            gross_loss=gross_loss_abs,
            net_profit=net,
            net_profit_pct=100.0 * net / self.cfg.initial_capital,
            profit_factor=pf,
            expectancy=(net / n) if n else 0.0,
            average_winner=(
                sum(t.net_pnl for t in wins) / len(wins) if wins else 0.0
            ),
            average_loser=(
                sum(t.net_pnl for t in losses) / len(losses) if losses else 0.0
            ),
            average_r=(sum(r_values) / len(r_values)) if r_values else 0.0,
            max_drawdown_pct=100.0 * max_dd,
            ambiguous_trades=sum(t.ambiguous_same_bar for t in closed),
        )
