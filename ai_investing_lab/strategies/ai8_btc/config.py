from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SizingMode(str, Enum):
    PERCENT_EQUITY = "percent_equity"
    FIXED_CASH = "fixed_cash"


@dataclass(frozen=True)
class AI8Config:
    """Configuration for AI8 SuperTrend + Range Filter with ADX.

    Indicator inputs come from the creator-linked Pine v5 source. The creator
    video separately verifies the TradingView Properties used for the reported
    benchmark: $100k initial capital, $80k cash per entry, pyramiding=7,
    0.1% commission on each entry/exit, and 2 ticks of slippage.
    """

    symbol: str = "BTCUSDT"
    timeframe_minutes: int = 120

    supertrend_atr_length: int = 8
    supertrend_factor: float = 1.6
    long_only: bool = True

    adx_smoothing: int = 14
    di_length: int = 14
    adx_limit: float = 18.0

    range_period: int = 175
    range_multiplier: float = 5.0

    stop_atr_length: int = 50
    stop_atr_multiplier: float = 10.0
    risk_reward_ratio: float = 100.0

    initial_capital_usd: float = 100_000.0
    sizing_mode: SizingMode = SizingMode.FIXED_CASH
    percent_of_equity: float = 80.0
    fixed_cash_usd: float = 80_000.0
    pyramiding: int = 7

    commission_pct_per_side: float = 0.1
    slippage_ticks: int = 2
    min_tick: float = 0.01

    @classmethod
    def creator_video(cls, **overrides) -> "AI8Config":
        values = {
            "sizing_mode": SizingMode.FIXED_CASH,
            "fixed_cash_usd": 80_000.0,
            "pyramiding": 7,
        }
        values.update(overrides)
        return cls(**values)

    @classmethod
    def creator_fixed_cash(cls, **overrides) -> "AI8Config":
        return cls.creator_video(**overrides)

    @classmethod
    def creator_percent_equity(cls, **overrides) -> "AI8Config":
        # Counterfactual retained only for sizing diagnostics. The video verifies
        # a fixed $80k cash order, not 80% of changing equity.
        values = {
            "sizing_mode": SizingMode.PERCENT_EQUITY,
            "percent_of_equity": 80.0,
            "pyramiding": 7,
        }
        values.update(overrides)
        return cls(**values)

    @classmethod
    def pine_source_default(cls, **overrides) -> "AI8Config":
        # The strategy() declaration itself says percent_of_equity=15 and does
        # not set pyramiding, so Pine's default pyramiding is one. The video
        # explicitly tells viewers to override these Properties for the test.
        values = {
            "sizing_mode": SizingMode.PERCENT_EQUITY,
            "percent_of_equity": 15.0,
            "pyramiding": 1,
        }
        values.update(overrides)
        return cls(**values)

    def validate(self) -> None:
        positive_ints = {
            "timeframe_minutes": self.timeframe_minutes,
            "supertrend_atr_length": self.supertrend_atr_length,
            "adx_smoothing": self.adx_smoothing,
            "di_length": self.di_length,
            "range_period": self.range_period,
            "stop_atr_length": self.stop_atr_length,
            "pyramiding": self.pyramiding,
        }
        for name, value in positive_ints.items():
            if value <= 0:
                raise ValueError(f"{name} must be positive")
        if self.supertrend_factor <= 0 or self.range_multiplier <= 0:
            raise ValueError("indicator multipliers must be positive")
        if self.stop_atr_multiplier <= 0 or self.risk_reward_ratio <= 0:
            raise ValueError("exit multipliers must be positive")
        if self.initial_capital_usd <= 0:
            raise ValueError("initial capital must be positive")
        if not 0 < self.percent_of_equity <= 100:
            raise ValueError("percent_of_equity must be in (0, 100]")
        if self.fixed_cash_usd <= 0:
            raise ValueError("fixed_cash_usd must be positive")
        if self.commission_pct_per_side < 0:
            raise ValueError("commission cannot be negative")
        if self.slippage_ticks < 0 or self.min_tick <= 0:
            raise ValueError("invalid slippage/tick inputs")
