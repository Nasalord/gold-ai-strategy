from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class TripleMAConfig:
    """Frozen configuration for AI15 / Simple Triple MA research.

    The public Pine file ships generic defaults that are *not* the optimized
    ES1! 10-minute values shown in the source video.  Both presets are kept so
    the distinction cannot be lost later.
    """

    ma_a_length: int = 35
    ma_b_length: int = 150
    ma_c_length: int = 100
    ma_a_type: str = "TMA"
    ma_b_type: str = "EMA"
    ma_c_type: str = "SMA"
    source: str = "low"

    atr_length: int = 20
    stop_atr_multiple: float = 8.5
    target_atr_multiple: float = 6.5

    initial_capital_usd: float = 100_000.0
    order_cash_usd: float = 1_250_000.0
    fixed_contracts: float | None = None
    point_value: float = 50.0
    min_tick: float = 0.25
    slippage_ticks: int = 5
    commission_usd_per_contract_per_order: float = 2.0
    allow_fractional_contracts: bool = False

    # The supplied Pine updates the persistent stop/target variables whenever
    # another valid crossover occurs, even while pyramiding blocks a new entry.
    # The narration says exits do not update while a trade is open.  Source-code
    # semantics are the parity baseline; the narrated behavior is a declared
    # diagnostic variant.
    update_exit_on_signal_while_open: bool = True

    @classmethod
    def creator_es_10m(cls) -> "TripleMAConfig":
        return cls()

    @classmethod
    def pine_file_defaults(cls) -> "TripleMAConfig":
        return cls(
            ma_a_length=2,
            ma_b_length=3,
            ma_c_length=375,
            atr_length=100,
            stop_atr_multiple=10.5,
            target_atr_multiple=30.0,
        )

    @classmethod
    def narrated_exit_variant(cls) -> "TripleMAConfig":
        return replace(cls.creator_es_10m(), update_exit_on_signal_while_open=False)

    @classmethod
    def one_mes_paper(cls, *, initial_capital_usd: float = 5_000.0) -> "TripleMAConfig":
        """One-contract MES sensitivity case for paper research only.

        This preserves the ES signal rules but scales the P&L multiplier from
        $50/point to $5/point.  It is not a claim about broker margin or live
        suitability; those are separate deployment questions.
        """
        return replace(
            cls.creator_es_10m(),
            initial_capital_usd=initial_capital_usd,
            fixed_contracts=1.0,
            order_cash_usd=0.0,
            point_value=5.0,
        )

    def validate(self) -> None:
        if min(self.ma_a_length, self.ma_b_length, self.ma_c_length, self.atr_length) < 1:
            raise ValueError("indicator lengths must be >= 1")
        if self.ma_a_type not in {"SMA", "EMA", "RMA", "DEMA", "TMA"}:
            raise ValueError("unsupported MA A type")
        if self.ma_b_type not in {"SMA", "EMA", "RMA", "DEMA", "TMA"}:
            raise ValueError("unsupported MA B type")
        if self.ma_c_type not in {"SMA", "EMA", "RMA", "DEMA", "TMA"}:
            raise ValueError("unsupported MA C type")
        if self.source not in {"open", "high", "low", "close"}:
            raise ValueError("source must be an OHLC field")
        if self.stop_atr_multiple <= 0 or self.target_atr_multiple <= 0:
            raise ValueError("ATR exit multiples must be positive")
        if self.initial_capital_usd <= 0:
            raise ValueError("initial capital must be positive")
        if self.fixed_contracts is None and self.order_cash_usd <= 0:
            raise ValueError("cash sizing must be positive when fixed_contracts is unset")
        if self.fixed_contracts is not None and self.fixed_contracts <= 0:
            raise ValueError("fixed contracts must be positive")
        if self.point_value <= 0 or self.min_tick <= 0:
            raise ValueError("contract specification must be positive")
        if self.slippage_ticks < 0 or self.commission_usd_per_contract_per_order < 0:
            raise ValueError("cost assumptions cannot be negative")
