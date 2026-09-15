from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from math import floor, inf

from .config import TripleMAConfig
from .indicators import atr, crossed_above, moving_average


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
    END = "end"


@dataclass
class Trade:
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


class TripleMABacktester:
    """Paper-only emulator for the supplied AI15 Pine strategy.

    Baseline semantics follow the source code:
    - long only;
    - signal at bar close, market fill at next bar open;
    - TMA/EMA crossover plus both fast MAs above the slow SMA;
    - stop/target frozen from signal-bar close and ATR;
    - Pine-style slippage on market entry and stop fills;
    - no pyramiding;
    - a later valid crossover can modify the persistent stop/target variables
      while a position is open because that is what the supplied Pine does.

    The narrated no-exit-update interpretation is available as an explicit
    config variant and is never silently substituted for the source baseline.
    """

    def __init__(self, config: TripleMAConfig):
        config.validate()
        self.cfg = config

    def _contracts(self, price: float) -> float:
        if self.cfg.fixed_contracts is not None:
            return float(self.cfg.fixed_contracts)
        raw = self.cfg.order_cash_usd / (price * self.cfg.point_value)
        return raw if self.cfg.allow_fractional_contracts else float(floor(raw))

    def _commission(self, contracts: float) -> float:
        return abs(contracts) * self.cfg.commission_usd_per_contract_per_order

    @staticmethod
    def _source(candles: list[Candle], field: str) -> list[float]:
        return [float(getattr(c, field)) for c in candles]

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

        source = self._source(candles, self.cfg.source)
        highs = [c.high for c in candles]
        lows = [c.low for c in candles]
        closes = [c.close for c in candles]
        ma_a = moving_average(source, self.cfg.ma_a_length, self.cfg.ma_a_type)
        ma_b = moving_average(source, self.cfg.ma_b_length, self.cfg.ma_b_type)
        ma_c = moving_average(source, self.cfg.ma_c_length, self.cfg.ma_c_type)
        atr_values = atr(highs, lows, closes, self.cfg.atr_length)

        slip = self.cfg.slippage_ticks * self.cfg.min_tick
        trades: list[Trade] = []
        position: Trade | None = None
        pending: dict[str, object] | None = None

        def in_window(t: datetime) -> bool:
            return (trade_start is None or t >= trade_start) and (trade_end is None or t < trade_end)

        def close_position(when: datetime, px: float, reason: ExitReason) -> None:
            nonlocal position
            if position is None:
                return
            comm = self._commission(position.contracts)
            gross = (px - position.entry_price) * self.cfg.point_value * position.contracts
            position.exit_time = when
            position.exit_price = px
            position.exit_commission = comm
            position.net_pnl_usd = gross - position.entry_commission - comm
            position.exit_reason = reason
            position = None

        for i, candle in enumerate(candles):
            if trade_end is not None and candle.time >= trade_end:
                break
            active = in_window(candle.time)

            # Pine default historical market-order timing: prior signal close ->
            # current bar open, with configured slippage applied adversely.
            if pending is not None and active and position is None:
                fill = candle.open + slip
                contracts = self._contracts(fill)
                if contracts >= 1:
                    position = Trade(
                        signal_time=pending["signal_time"],
                        entry_time=candle.time,
                        entry_price=fill,
                        contracts=contracts,
                        stop=float(pending["stop"]),
                        target=float(pending["target"]),
                        entry_commission=self._commission(contracts),
                    )
                    trades.append(position)
                pending = None

            # Exit orders can fill on the entry bar after the market entry.
            if position is not None and active:
                stop_hit = candle.low <= position.stop
                target_hit = candle.high >= position.target
                reason: ExitReason | None = None
                if stop_hit and target_hit:
                    # TradingView's historical broker emulator assumes an
                    # intrabar path based on which extreme is nearer the open.
                    high_first = abs(candle.open - candle.high) < abs(candle.open - candle.low)
                    reason = ExitReason.TARGET if high_first else ExitReason.STOP
                elif stop_hit:
                    reason = ExitReason.STOP
                elif target_hit:
                    reason = ExitReason.TARGET

                if reason == ExitReason.TARGET:
                    px = max(position.target, candle.open) if candle.open >= position.target else position.target
                    close_position(candle.time, px, reason)
                elif reason == ExitReason.STOP:
                    trigger = candle.open if candle.open < position.stop else position.stop
                    close_position(candle.time, trigger - slip, reason)

            if not active or i < 1:
                continue
            a, b, c, av = ma_a[i], ma_b[i], ma_c[i], atr_values[i]
            if None in (a, b, c, av):
                continue

            signal = crossed_above(ma_a, ma_b, i) and a > c and b > c
            if not signal:
                continue

            stop = candle.close - float(av) * self.cfg.stop_atr_multiple
            target = candle.close + float(av) * self.cfg.target_atr_multiple

            if position is not None:
                if self.cfg.update_exit_on_signal_while_open:
                    position.stop = stop
                    position.target = target
                continue

            if pending is None:
                pending = {
                    "signal_time": candle.time,
                    "stop": stop,
                    "target": target,
                }

        if close_at_end and position is not None:
            last = candles[-1]
            close_position(last.time, last.close - slip, ExitReason.END)

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
        for trade in sorted(closed, key=lambda x: (x.exit_time, x.entry_time)):
            equity += trade.net_pnl_usd
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
