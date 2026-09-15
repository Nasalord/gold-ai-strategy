from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class AI38Config:
    ema_fast_length: int = 21
    ema_slow_length: int = 50
    momentum_a_length: int = 110
    momentum_b_length: int = 30
    risk_reward_ratio: float = 2.4
    candle_lookback: int = 3
    trade_direction: str = "Both"
    use_ema_growth_check: bool = True
    ema_fast_lookback: int = 21
    ema_fast_growth_percent: float = 30.0
    ema_slow_lookback: int = 6
    ema_slow_growth_percent: float = 35.0

    initial_capital_usd: float = 10_000.0
    fixed_units: float = 100_000.0
    commission_usd_per_contract_per_side: float = 0.00005
    slippage_ticks: int = 20
    min_tick: float = 0.00001

    @classmethod
    def creator_4h(cls, **overrides) -> "AI38Config":
        return replace(cls(), **overrides)

    def validate(self) -> None:
        for name in (
            "ema_fast_length",
            "ema_slow_length",
            "momentum_a_length",
            "momentum_b_length",
            "candle_lookback",
            "ema_fast_lookback",
            "ema_slow_lookback",
        ):
            if getattr(self, name) < 1:
                raise ValueError(f"{name} must be >= 1")
        if self.risk_reward_ratio <= 0:
            raise ValueError("risk_reward_ratio must be positive")
        if self.trade_direction not in {"Longs Only", "Shorts Only", "Both"}:
            raise ValueError("invalid trade_direction")
        if self.initial_capital_usd <= 0 or self.fixed_units <= 0:
            raise ValueError("capital and fixed_units must be positive")
        if self.commission_usd_per_contract_per_side < 0:
            raise ValueError("commission must be non-negative")
        if self.slippage_ticks < 0 or self.min_tick <= 0:
            raise ValueError("invalid slippage/tick")
