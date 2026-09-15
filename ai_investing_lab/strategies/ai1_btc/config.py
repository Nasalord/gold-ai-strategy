from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AI1Config:
    """Frozen AI1 SSL + T3 + ADX/EMA configuration.

    Signal inputs come from the user-supplied Pine v5 source and creator video.
    TradingView Properties for the reported benchmark are modeled as a fixed
    $100k notional order on $10k reference capital, one position at a time,
    0.1% commission per side and 2 ticks slippage.
    """

    symbol: str = "BTCUSDT"
    timeframe_minutes: int = 10

    ssl_period: int = 140
    t3_fast_length: int = 40
    t3_slow_length: int = 90
    t3_b: float = 0.7

    adx_smoothing: int = 100
    di_length: int = 110
    adx_ema_length: int = 80

    atr_length: int = 120
    atr_stop_multiplier: float = 10.0
    atr_take_profit_multiplier: float = 20.0

    initial_capital_usd: float = 10_000.0
    fixed_cash_usd: float = 100_000.0
    commission_pct_per_side: float = 0.1
    slippage_ticks: int = 2
    min_tick: float = 0.01

    @classmethod
    def creator_10m(cls, **overrides) -> "AI1Config":
        values = {}
        values.update(overrides)
        return cls(**values)

    def validate(self) -> None:
        ints = {
            "timeframe_minutes": self.timeframe_minutes,
            "ssl_period": self.ssl_period,
            "t3_fast_length": self.t3_fast_length,
            "t3_slow_length": self.t3_slow_length,
            "adx_smoothing": self.adx_smoothing,
            "di_length": self.di_length,
            "adx_ema_length": self.adx_ema_length,
            "atr_length": self.atr_length,
        }
        for name, value in ints.items():
            if value <= 0:
                raise ValueError(f"{name} must be positive")
        if self.atr_stop_multiplier <= 0 or self.atr_take_profit_multiplier <= 0:
            raise ValueError("ATR multipliers must be positive")
        if self.initial_capital_usd <= 0 or self.fixed_cash_usd <= 0:
            raise ValueError("capital/notional must be positive")
        if self.commission_pct_per_side < 0 or self.slippage_ticks < 0 or self.min_tick <= 0:
            raise ValueError("invalid cost inputs")
