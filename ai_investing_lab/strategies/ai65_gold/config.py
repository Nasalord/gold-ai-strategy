from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from enum import Enum


class ExecutionMode(str, Enum):
    """How closely the simulator follows the uploaded Pine engine."""

    REPLICA = "replica"
    GUARDED = "guarded"


class TDFIGating(str, Enum):
    """When the TDFI filter is evaluated."""

    ARM_TIME = "arm_time"
    ENTRY_TIME = "entry_time"


class SizingMode(str, Enum):
    """Research-only position sizing mode."""

    CREATOR_FIXED_NOTIONAL = "creator_fixed_notional"
    RISK_BASED = "risk_based"


@dataclass(frozen=True)
class AI65Config:
    symbol: str = "XAUUSD"
    timeframe_minutes: int = 60
    timezone: str = "America/New_York"
    range_start: time = time(11, 0)
    range_end: time = time(13, 0)
    direction: str = "long_only"
    max_trades_per_session: int = 1

    use_tdfi: bool = True
    tdfi_lookback: int = 5
    tdfi_long_threshold: float = -0.05
    tdfi_gating: TDFIGating = TDFIGating.ARM_TIME

    stop_mult: float = 3.8
    target_mult: float = 3.3
    use_trailing_atr: bool = False

    use_force_exit: bool = True
    force_exit: time = time(22, 0)
    execution_mode: ExecutionMode = ExecutionMode.REPLICA

    initial_capital: float = 10_000.0

    # Creator-replica sizing.
    sizing_mode: SizingMode = SizingMode.CREATOR_FIXED_NOTIONAL
    fixed_notional: float = 70_000.0

    # Guarded research sizing. Percent is expressed as 0.25 == 0.25%.
    risk_per_trade_pct: float = 0.25
    max_notional: float = 10_000.0

    # TradingView-style cost inputs used by the creator's test.
    commission_per_contract_per_side: float = 0.04
    slippage_ticks: int = 100
    min_tick: float = 0.01

    @property
    def internal_tp_rr(self) -> float:
        """Equivalent Pine RR when target_mult is measured from base distance."""
        if self.stop_mult <= 0:
            raise ValueError("stop_mult must be positive")
        return self.target_mult / self.stop_mult

    @classmethod
    def creator_1h(cls, **overrides) -> "AI65Config":
        """Uploaded-source replica preset.

        This preserves the René Balke-style Pine mechanics: TDFI is checked when
        the pending breakout order is armed. The provider/tick convention remains
        generic because the uploaded source is not the AI65 Gold video script.
        """
        values = {
            "timeframe_minutes": 60,
            "execution_mode": ExecutionMode.REPLICA,
            "sizing_mode": SizingMode.CREATOR_FIXED_NOTIONAL,
            "tdfi_gating": TDFIGating.ARM_TIME,
        }
        values.update(overrides)
        return cls(**values)

    @classmethod
    def creator_3m(cls, **overrides) -> "AI65Config":
        """Uploaded-source mechanics on the video's 3-minute research timeframe."""
        values = {
            "timeframe_minutes": 3,
            "execution_mode": ExecutionMode.REPLICA,
            "sizing_mode": SizingMode.CREATOR_FIXED_NOTIONAL,
            "tdfi_gating": TDFIGating.ARM_TIME,
        }
        values.update(overrides)
        return cls(**values)

    @classmethod
    def video_oanda_1h(cls, **overrides) -> "AI65Config":
        """Best-supported AI65 video parity hypothesis for the 1-hour benchmark.

        Evidence currently points to TradingView OANDA:XAUUSD: the video's stated
        full intraday history begins 2006-03-19, matching OANDA:XAUUSD history on
        TradingView, and OANDA quotes Gold to three decimals. The video also
        describes TDFI as a breakout confirmation, so this preset evaluates TDFI
        at entry/breakout time rather than only when the stop order is armed.

        This is a research hypothesis, not a claim of frame-level provider proof.
        """
        values = {
            "symbol": "OANDA:XAUUSD",
            "timeframe_minutes": 60,
            "execution_mode": ExecutionMode.REPLICA,
            "sizing_mode": SizingMode.CREATOR_FIXED_NOTIONAL,
            "tdfi_gating": TDFIGating.ENTRY_TIME,
            "min_tick": 0.001,
        }
        values.update(overrides)
        return cls(**values)

    @classmethod
    def video_oanda_3m(cls, **overrides) -> "AI65Config":
        """Creator-style 3-minute AI65 video hypothesis using OANDA conventions."""
        values = {
            "symbol": "OANDA:XAUUSD",
            "timeframe_minutes": 3,
            "execution_mode": ExecutionMode.REPLICA,
            "sizing_mode": SizingMode.CREATOR_FIXED_NOTIONAL,
            "tdfi_gating": TDFIGating.ENTRY_TIME,
            "min_tick": 0.001,
        }
        values.update(overrides)
        return cls(**values)

    @classmethod
    def guarded_3m(cls, **overrides) -> "AI65Config":
        """Guarded research mode preserving uploaded-source TDFI timing."""
        values = {
            "timeframe_minutes": 3,
            "execution_mode": ExecutionMode.GUARDED,
            "sizing_mode": SizingMode.RISK_BASED,
            "tdfi_gating": TDFIGating.ARM_TIME,
        }
        values.update(overrides)
        return cls(**values)

    @classmethod
    def video_oanda_guarded_3m(cls, **overrides) -> "AI65Config":
        """Capped paper/research version of the current AI65 video hypothesis."""
        values = {
            "symbol": "OANDA:XAUUSD",
            "timeframe_minutes": 3,
            "execution_mode": ExecutionMode.GUARDED,
            "sizing_mode": SizingMode.RISK_BASED,
            "tdfi_gating": TDFIGating.ENTRY_TIME,
            "min_tick": 0.001,
        }
        values.update(overrides)
        return cls(**values)

    def validate(self) -> None:
        if self.direction != "long_only":
            raise ValueError("AI65 v1 is long-only")
        if self.max_trades_per_session != 1:
            raise ValueError("AI65 v1 permits exactly one filled trade per session")
        if self.timeframe_minutes <= 0:
            raise ValueError("timeframe_minutes must be positive")
        if self.range_start >= self.range_end:
            raise ValueError("range_start must be before range_end")
        if self.tdfi_lookback <= 0:
            raise ValueError("tdfi_lookback must be positive")
        if self.stop_mult <= 0 or self.target_mult <= 0:
            raise ValueError("stop_mult and target_mult must be positive")
        if self.slippage_ticks < 0 or self.min_tick <= 0:
            raise ValueError("invalid slippage/tick configuration")
        if self.initial_capital <= 0:
            raise ValueError("initial_capital must be positive")
        if self.commission_per_contract_per_side < 0:
            raise ValueError("commission cannot be negative")

        if self.sizing_mode == SizingMode.CREATOR_FIXED_NOTIONAL:
            if self.fixed_notional <= 0:
                raise ValueError("fixed_notional must be positive")
        elif self.sizing_mode == SizingMode.RISK_BASED:
            if not 0 < self.risk_per_trade_pct <= 100:
                raise ValueError("risk_per_trade_pct must be in (0, 100]")
            if self.max_notional <= 0:
                raise ValueError("max_notional must be positive")
        else:
            raise ValueError(f"unsupported sizing mode: {self.sizing_mode}")
