from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from enum import Enum


class TradeDirection(str, Enum):
    BOTH = "both"
    LONG_ONLY = "long_only"
    SHORT_ONLY = "short_only"


class SizingMode(str, Enum):
    CREATOR_FIXED_NOTIONAL = "creator_fixed_notional"
    RISK_BASED = "risk_based"


@dataclass(frozen=True)
class AI58Config:
    """Configuration for the uploaded René Balke ORB engine.

    The generic defaults mirror the downloaded Pine template. `optimized_15m`
    is populated only from the creator-video transcript supplied by the user.
    One item remains explicitly inferential: the transcript ASR renders the
    fixed stop/TP values as "one", but the narration says the ATR trail is the
    only possible exit. We therefore encode 100/100 as the parity hypothesis
    because it makes those fixed exits practically unreachable in this engine.
    """

    symbol: str = "USDJPY"
    timeframe_minutes: int = 15
    timezone: str = "America/New_York"

    range_start: time = time(9, 30)
    range_end: time = time(9, 45)
    direction: TradeDirection = TradeDirection.BOTH
    allow_reentry: bool = False
    allow_direction_switch_same_day: bool = False

    stop_mult: float = 1.0
    tp_rr: float = 1.5

    use_force_exit: bool = False
    force_exit: time = time(16, 0)

    use_tdfi: bool = False
    tdfi_lookback: int = 13
    tdfi_filter_high: float = 0.05
    tdfi_filter_low: float = -0.05

    use_trailing_atr: bool = False
    trailing_atr_length: int = 14
    trailing_atr_multiplier: float = 5.0

    initial_capital_usd: float = 10_000.0
    sizing_mode: SizingMode = SizingMode.CREATOR_FIXED_NOTIONAL
    fixed_notional_usd: float = 70_000.0
    risk_per_trade_pct: float = 0.25
    max_notional_usd: float = 10_000.0

    slippage_ticks: int = 12
    min_tick: float = 0.001
    commission_usd_per_standard_lot_per_side: float = 3.50
    standard_lot_base_units: float = 100_000.0

    @classmethod
    def source_default_15m(cls, **overrides) -> "AI58Config":
        """15m control using untouched Pine-template input defaults."""
        values = {"timeframe_minutes": 15}
        values.update(overrides)
        return cls(**values)

    @classmethod
    def guarded_source_default_15m(cls, **overrides) -> "AI58Config":
        """Paper/research sizing with source-default signal parameters."""
        values = {
            "timeframe_minutes": 15,
            "sizing_mode": SizingMode.RISK_BASED,
        }
        values.update(overrides)
        return cls(**values)

    @classmethod
    def optimized_15m(cls, **overrides) -> "AI58Config":
        """Creator-video AI58 optimized preset.

        Video evidence:
        - IC Markets USDJPY, 15m
        - 06:00-08:15 New York opening range
        - long only
        - TDFI lookback 50, high/low thresholds 0
        - ATR trailing enabled, external NNFX ATR illustration X=450 / SL=11
        - no optimized force exit; narration says trailing stop is the only exit
        - $70k fixed notional on $10k initial capital
        - $3.50/standard-lot/side + 12 ticks slippage

        `stop_mult=100` and `tp_rr=100` are an ASR-resolution hypothesis, not a
        screenshot-verified input. The transcript says both fixed values are set
        to "one" while also saying only the ATR trail can exit; literal 1/1 is
        incompatible with that narration in the uploaded engine.
        """
        values = {
            "timeframe_minutes": 15,
            "timezone": "America/New_York",
            "range_start": time(6, 0),
            "range_end": time(8, 15),
            "direction": TradeDirection.LONG_ONLY,
            "stop_mult": 100.0,
            "tp_rr": 100.0,
            "use_force_exit": False,
            "use_tdfi": True,
            "tdfi_lookback": 50,
            "tdfi_filter_high": 0.0,
            "tdfi_filter_low": 0.0,
            "use_trailing_atr": True,
            "trailing_atr_length": 450,
            "trailing_atr_multiplier": 11.0,
            "initial_capital_usd": 10_000.0,
            "sizing_mode": SizingMode.CREATOR_FIXED_NOTIONAL,
            "fixed_notional_usd": 70_000.0,
            "slippage_ticks": 12,
            "min_tick": 0.001,
            "commission_usd_per_standard_lot_per_side": 3.50,
            "standard_lot_base_units": 100_000.0,
        }
        values.update(overrides)
        return cls(**values)

    @classmethod
    def guarded_optimized_15m(cls, **overrides) -> "AI58Config":
        values = {
            "sizing_mode": SizingMode.RISK_BASED,
            "risk_per_trade_pct": 0.25,
            "max_notional_usd": 10_000.0,
        }
        values.update(overrides)
        return cls.optimized_15m(**values)

    def validate(self) -> None:
        if self.timeframe_minutes <= 0:
            raise ValueError("timeframe_minutes must be positive")
        if self.range_start >= self.range_end:
            raise ValueError("the uploaded source only supports same-day ranges")
        if self.stop_mult < 0 or self.tp_rr < 0:
            raise ValueError("stop_mult and tp_rr must be non-negative")
        if self.tdfi_lookback <= 0:
            raise ValueError("tdfi_lookback must be positive")
        if self.trailing_atr_length <= 0 or self.trailing_atr_multiplier < 0:
            raise ValueError("invalid ATR trailing-stop inputs")
        if self.initial_capital_usd <= 0:
            raise ValueError("initial_capital_usd must be positive")
        if self.fixed_notional_usd <= 0:
            raise ValueError("fixed_notional_usd must be positive")
        if self.slippage_ticks < 0 or self.min_tick <= 0:
            raise ValueError("invalid slippage/tick inputs")
        if self.commission_usd_per_standard_lot_per_side < 0:
            raise ValueError("commission cannot be negative")
        if self.standard_lot_base_units <= 0:
            raise ValueError("standard_lot_base_units must be positive")
        if self.sizing_mode == SizingMode.RISK_BASED:
            if not 0 < self.risk_per_trade_pct <= 100:
                raise ValueError("risk_per_trade_pct must be in (0, 100]")
            if self.max_notional_usd <= 0:
                raise ValueError("max_notional_usd must be positive")
