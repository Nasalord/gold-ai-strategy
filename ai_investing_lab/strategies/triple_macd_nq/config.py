from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class TripleMACDNQConfig:
    # Frozen Trade Smart AI NQ1! 10-minute optimization settings.
    long_fast: int = 150
    long_slow: int = 450
    mid_fast: int = 45
    mid_slow: int = 70
    short_fast: int = 28
    short_slow: int = 23
    macd_signal: int = 9

    use_chande_filter: bool = False
    use_trend_filter: bool = False
    use_tdfi_filter: bool = True
    tdfi_lookback: int = 50
    tdfi_high: float = 0.9
    tdfi_low: float = -0.8
    tdfi_smoothing: bool = False
    tdfi_smooth_period: int = 15

    enable_entry_a: bool = True
    enable_entry_b: bool = False
    sl_lookback: int = 10
    risk_reward: float = 3.5
    trade_direction: str = "Both"

    # Creator Properties-tab assumptions for CME NQ.
    initial_capital_usd: float = 1_000_000.0
    order_cash_usd: float = 8_500_000.0
    commission_usd_per_contract_per_order: float = 2.5
    slippage_ticks: int = 5
    min_tick: float = 0.25
    point_value: float = 20.0
    allow_fractional_contracts: bool = False

    @classmethod
    def creator_nq_10m(cls, **overrides) -> "TripleMACDNQConfig":
        return replace(cls(), **overrides)

    def validate(self) -> None:
        for name in (
            "long_fast", "long_slow", "mid_fast", "mid_slow",
            "short_fast", "short_slow", "macd_signal", "tdfi_lookback",
            "tdfi_smooth_period", "sl_lookback",
        ):
            if getattr(self, name) < 1:
                raise ValueError(f"{name} must be >= 1")
        if self.risk_reward <= 0:
            raise ValueError("risk_reward must be positive")
        if self.trade_direction not in {"Long Only", "Short Only", "Both"}:
            raise ValueError("invalid trade_direction")
        if self.initial_capital_usd <= 0 or self.order_cash_usd <= 0:
            raise ValueError("capital and order size must be positive")
        if self.commission_usd_per_contract_per_order < 0:
            raise ValueError("commission must be non-negative")
        if self.slippage_ticks < 0 or self.min_tick <= 0 or self.point_value <= 0:
            raise ValueError("invalid futures contract/slippage settings")
