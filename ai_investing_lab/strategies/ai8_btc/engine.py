from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from math import inf

from .config import AI8Config, SizingMode
from .indicators import adx, atr, range_filter, supertrend_direction


class ExitReason(str, Enum):
    RANGE_FILTER = "range_filter"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
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
        if self.low <= 0:
            raise ValueError("price must be positive")
        if self.high < max(self.open, self.close, self.low):
            raise ValueError("invalid high")
        if self.low > min(self.open, self.close, self.high):
            raise ValueError("invalid low")


@dataclass
class Trade:
    signal_time: datetime
    entry_time: datetime
    entry_price: float
    quantity_btc: float
    entry_notional_usd: float
    equity_at_signal_usd: float
    stop_price: float
    target_price: float
    entry_commission_usd: float
    exit_time: datetime | None = None
    exit_price: float | None = None
    exit_reason: ExitReason | None = None
    exit_commission_usd: float = 0.0
    gross_pnl_usd: float = 0.0
    net_pnl_usd: float = 0.0
    ambiguous_same_bar: bool = False

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
    max_intrabar_drawdown_pct: float
    ambiguous_trades: int


@dataclass(frozen=True)
class BacktestResult:
    trades: list[Trade]
    metrics: Metrics


class AI8Backtester:
    """Research-only Pine reconstruction for AI8.

    Creator-video parity rules:
    - long only;
    - market entries and strategy.close orders fill on the next bar open;
    - up to seven same-direction entries may be stacked (pyramiding);
    - every accepted entry is a separate closed trade in the Strategy Tester;
    - each qualifying Supertrend signal reissues the same strategy.exit ID, so
      the newest 10x-ATR stop / distant target becomes shared by all open Long
      entries; the creator explicitly describes that newest stop closing all
      earlier stacked entries;
    - a Range Filter sell closes every open Long entry together;
    - TradingView `strategy.cash` sizing converts the cash amount to quantity
      using the order-creation (signal) price, while commission is charged on
      the actual filled transaction value.

    `trade_start`/`trade_end` gate order creation/fills while allowing earlier
    candles to warm indicators without changing starting equity.
    """

    def __init__(self, config: AI8Config):
        config.validate()
        self.cfg = config
        self.slippage = config.slippage_ticks * config.min_tick
        self._intrabar_max_dd_pct = 0.0

    def run(
        self,
        candles: list[Candle],
        *,
        trade_start: datetime | None = None,
        trade_end: datetime | None = None,
        close_at_end: bool = False,
    ) -> BacktestResult:
        if not candles:
            return BacktestResult([], self._metrics([]))
        candles = sorted(candles, key=lambda c: c.time)
        for c in candles:
            c.validate()
        if trade_start is not None and trade_start.tzinfo is None:
            raise ValueError("trade_start must be timezone-aware")
        if trade_end is not None and trade_end.tzinfo is None:
            raise ValueError("trade_end must be timezone-aware")
        if trade_start is not None and trade_end is not None and trade_start >= trade_end:
            raise ValueError("trade_start must be before trade_end")

        self._intrabar_max_dd_pct = 0.0
        highs = [c.high for c in candles]
        lows = [c.low for c in candles]
        closes = [c.close for c in candles]
        adx_values = adx(
            highs,
            lows,
            closes,
            di_length=self.cfg.di_length,
            adx_smoothing=self.cfg.adx_smoothing,
        )
        directions = supertrend_direction(
            highs,
            lows,
            closes,
            factor=self.cfg.supertrend_factor,
            atr_length=self.cfg.supertrend_atr_length,
        )
        stop_atr = atr(highs, lows, closes, self.cfg.stop_atr_length)
        _, _, range_short = range_filter(
            closes, period=self.cfg.range_period, multiplier=self.cfg.range_multiplier
        )

        trades: list[Trade] = []
        open_legs: list[Trade] = []
        pending_entry: dict[str, float | datetime] | None = None
        pending_market_exit = False
        active_stop: float | None = None
        active_target: float | None = None
        peak_equity = self.cfg.initial_capital_usd

        def in_window(when: datetime) -> bool:
            if trade_start is not None and when < trade_start:
                return False
            if trade_end is not None and when >= trade_end:
                return False
            return True

        for i, candle in enumerate(candles):
            if trade_end is not None and candle.time >= trade_end:
                pending_entry = None
                pending_market_exit = False
                break

            # Realized equity before this bar's open fills.
            realized_equity = self._equity(trades)
            peak_equity = max(peak_equity, realized_equity)

            # strategy.close("Long") closes all existing entries with that ID
            # at the next available tick/open. Process it before a same-open new
            # entry, matching the order's creation against the prior position.
            if pending_market_exit and open_legs and in_window(candle.time):
                exit_price = max(self.cfg.min_tick, candle.open - self.slippage)
                self._close_all(open_legs, candle.time, exit_price, ExitReason.RANGE_FILTER)
                open_legs = []
                active_stop = None
                active_target = None
            pending_market_exit = False

            # A qualifying entry signal from the preceding bar fills now.
            if pending_entry is not None:
                if in_window(candle.time) and len(open_legs) < self.cfg.pyramiding:
                    fill = candle.open + self.slippage
                    equity = self._equity(trades)
                    signal_price = float(pending_entry["qty_basis_price"])
                    qty = self._entry_quantity(equity, signal_price)
                    actual_entry_value = qty * fill
                    leg = Trade(
                        signal_time=pending_entry["signal_time"],
                        entry_time=candle.time,
                        entry_price=fill,
                        quantity_btc=qty,
                        entry_notional_usd=actual_entry_value,
                        equity_at_signal_usd=equity,
                        stop_price=float(pending_entry["stop_price"]),
                        target_price=float(pending_entry["target_price"]),
                        entry_commission_usd=self._commission(actual_entry_value),
                    )
                    trades.append(leg)
                    open_legs.append(leg)
                    active_stop = leg.stop_price
                    active_target = leg.target_price
                    for existing in open_legs:
                        existing.stop_price = active_stop
                        existing.target_price = active_target
                pending_entry = None

            # Track a TradingView-style intrabar equity trough for long-only
            # positions using the bar low, after open fills and entry costs.
            # This is reported separately from the legacy closed-trade DD.
            if open_legs:
                realized = self._equity(trades)
                unrealized_at_low = sum(
                    leg.quantity_btc * (candle.low - leg.entry_price)
                    - leg.entry_commission_usd
                    for leg in open_legs
                )
                equity_at_low = realized + unrealized_at_low
                peak_equity = max(peak_equity, realized)
                if peak_equity > 0:
                    self._intrabar_max_dd_pct = max(
                        self._intrabar_max_dd_pct,
                        100.0 * (peak_equity - equity_at_low) / peak_equity,
                    )

            # Shared strategy.exit is active intrabar for all stacked entries.
            if open_legs and active_stop is not None and active_target is not None:
                stop_hit = candle.low <= active_stop
                target_hit = candle.high >= active_target
                if stop_hit or target_hit:
                    ambiguous = stop_hit and target_hit
                    if ambiguous:
                        high_first = abs(candle.open - candle.high) < abs(candle.open - candle.low)
                        reason = ExitReason.TAKE_PROFIT if high_first else ExitReason.STOP_LOSS
                    elif stop_hit:
                        reason = ExitReason.STOP_LOSS
                    else:
                        reason = ExitReason.TAKE_PROFIT

                    if reason == ExitReason.TAKE_PROFIT:
                        exit_price = active_target
                    else:
                        reference = candle.open if candle.open < active_stop else active_stop
                        exit_price = max(self.cfg.min_tick, reference - self.slippage)
                    if ambiguous:
                        for leg in open_legs:
                            leg.ambiguous_same_bar = True
                    self._close_all(open_legs, candle.time, exit_price, reason)
                    open_legs = []
                    active_stop = None
                    active_target = None

            # Update peak from realized equity after any intrabar exits.
            peak_equity = max(peak_equity, self._equity(trades))

            if not in_window(candle.time):
                continue

            direction = directions[i]
            prev_direction = directions[i - 1] if i > 0 else None
            adx_value = adx_values[i]
            atr_value = stop_atr[i]
            long_entry = (
                direction is not None
                and prev_direction is not None
                and direction - prev_direction < 0
                and adx_value is not None
                and adx_value > self.cfg.adx_limit
                and self.cfg.long_only
            )

            if long_entry and atr_value is not None:
                risk = atr_value * self.cfg.stop_atr_multiplier
                new_stop = candle.close - risk
                new_target = candle.close + risk * self.cfg.risk_reward_ratio

                if open_legs:
                    active_stop = new_stop
                    active_target = new_target
                    for leg in open_legs:
                        leg.stop_price = new_stop
                        leg.target_price = new_target

                if len(open_legs) < self.cfg.pyramiding and pending_entry is None:
                    pending_entry = {
                        "signal_time": candle.time,
                        "qty_basis_price": candle.close,
                        "stop_price": new_stop,
                        "target_price": new_target,
                    }
                    active_stop = new_stop
                    active_target = new_target

            if open_legs and range_short[i]:
                pending_market_exit = True

        if open_legs and close_at_end:
            eligible = [c for c in candles if trade_end is None or c.time < trade_end]
            if eligible:
                last = eligible[-1]
                exit_price = max(self.cfg.min_tick, last.close - self.slippage)
                self._close_all(open_legs, last.time, exit_price, ExitReason.DATA_END)

        return BacktestResult(trades, self._metrics(trades))

    def _entry_quantity(self, equity_usd: float, signal_price: float) -> float:
        if signal_price <= 0:
            raise ValueError("signal_price must be positive")
        if self.cfg.sizing_mode == SizingMode.FIXED_CASH:
            cash = self.cfg.fixed_cash_usd
        else:
            cash = max(0.0, equity_usd) * self.cfg.percent_of_equity / 100.0
        return cash / signal_price

    def _entry_notional(self, equity_usd: float) -> float:
        # Retained for tests/callers that want the requested cash amount.
        if self.cfg.sizing_mode == SizingMode.FIXED_CASH:
            return self.cfg.fixed_cash_usd
        return max(0.0, equity_usd) * self.cfg.percent_of_equity / 100.0

    def _commission(self, transaction_value_usd: float) -> float:
        return transaction_value_usd * self.cfg.commission_pct_per_side / 100.0

    def _close_all(
        self,
        legs: list[Trade],
        when: datetime,
        price: float,
        reason: ExitReason,
    ) -> None:
        for leg in list(legs):
            self._close(leg, when, price, reason)

    def _close(self, trade: Trade, when: datetime, price: float, reason: ExitReason) -> None:
        trade.exit_time = when
        trade.exit_price = price
        trade.exit_reason = reason
        exit_value = trade.quantity_btc * price
        trade.exit_commission_usd = self._commission(exit_value)
        trade.gross_pnl_usd = trade.quantity_btc * (price - trade.entry_price)
        trade.net_pnl_usd = (
            trade.gross_pnl_usd - trade.entry_commission_usd - trade.exit_commission_usd
        )

    def _equity(self, trades: list[Trade]) -> float:
        return self.cfg.initial_capital_usd + sum(t.net_pnl_usd for t in trades if t.closed)

    def _metrics(self, trades: list[Trade]) -> Metrics:
        closed = [t for t in trades if t.closed]
        wins = [t for t in closed if t.net_pnl_usd > 0]
        losses = [t for t in closed if t.net_pnl_usd <= 0]
        gp = sum(t.net_pnl_usd for t in wins)
        gl = abs(sum(t.net_pnl_usd for t in losses))
        net = sum(t.net_pnl_usd for t in closed)
        pf = gp / gl if gl > 0 else (inf if gp > 0 else 0.0)

        equity = self.cfg.initial_capital_usd
        peak = equity
        max_dd = 0.0
        for t in closed:
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
            max_intrabar_drawdown_pct=self._intrabar_max_dd_pct,
            ambiguous_trades=sum(t.ambiguous_same_bar for t in closed),
        )
