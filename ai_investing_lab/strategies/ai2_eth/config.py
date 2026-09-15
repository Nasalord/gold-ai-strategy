from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AI2Config:
    """Frozen AI2 Simple Triple MA ETHUSDT 15m configuration."""

    symbol: str = "ETHUSDT"
    timeframe_minutes: int = 15

    ma_a_length: int = 2
    ma_a_type: str = "TMA"
    ma_b_length: int = 3
    ma_b_type: str = "EMA"
    ma_c_length: int = 375
    ma_c_type: str = "SMA"
    source: str = "low"

    atr_length: int = 100
    atr_stop_multiplier: float = 10.5
    atr_take_profit_multiplier: float = 30.0

    initial_capital_usd: float = 10_000.0
    fixed_cash_usd: float = 40_000.0
    commission_pct_per_side: float = 0.1
    slippage_ticks: int = 2
    min_tick: float = 0.01

    @classmethod
    def creator_15m(cls, **overrides) -> "AI2Config":
        return cls(**overrides)

    def validate(self) -> None:
        for name, value in {
            "timeframe_minutes": self.timeframe_minutes,
            "ma_a_length": self.ma_a_length,
            "ma_b_length": self.ma_b_length,
            "ma_c_length": self.ma_c_length,
            "atr_length": self.atr_length,
        }.items():
            if value <= 0:
                raise ValueError(f"{name} must be positive")
        allowed = {"SMA", "EMA", "RMA", "DEMA", "TMA"}
        for name, value in {
            "ma_a_type": self.ma_a_type,
            "ma_b_type": self.ma_b_type,
            "ma_c_type": self.ma_c_type,
        }.items():
            if value not in allowed:
                raise ValueError(f"{name} must be one of {sorted(allowed)}")
        if self.source not in {"open", "high", "low", "close"}:
            raise ValueError("source must be OHLC")
        if self.atr_stop_multiplier <= 0 or self.atr_take_profit_multiplier <= 0:
            raise ValueError("ATR multipliers must be positive")
        if self.initial_capital_usd <= 0 or self.fixed_cash_usd <= 0:
            raise ValueError("capital/notional must be positive")
        if self.commission_pct_per_side < 0 or self.slippage_ticks < 0 or self.min_tick <= 0:
            raise ValueError("invalid cost inputs")
