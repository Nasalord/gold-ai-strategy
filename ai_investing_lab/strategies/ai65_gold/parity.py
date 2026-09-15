from __future__ import annotations

from dataclasses import dataclass

from .orb_engine import BacktestMetrics


@dataclass(frozen=True)
class CreatorBenchmark:
    trades: int = 670
    net_profit_pct: float = 552.94
    profit_factor: float = 1.667
    win_rate_pct: float = 52.69
    max_drawdown_pct: float = 25.73

    trade_tolerance: int = 1
    net_profit_relative_tolerance: float = 0.05
    profit_factor_tolerance: float = 0.03
    win_rate_tolerance_pct_points: float = 0.20
    max_drawdown_tolerance_pct_points: float = 1.0


def evaluate_creator_parity(
    metrics: BacktestMetrics,
    benchmark: CreatorBenchmark | None = None,
) -> dict[str, object]:
    """Compare a 1H replica result with the creator-reported AI65 benchmark.

    This is a diagnostic gate, not an optimizer. A failed gate means the data,
    execution assumptions, or implementation should be investigated before any
    parameter search.
    """
    b = benchmark or CreatorBenchmark()
    net_profit_abs_tol = abs(b.net_profit_pct) * b.net_profit_relative_tolerance

    checks = {
        "trades": abs(metrics.trades - b.trades) <= b.trade_tolerance,
        "net_profit_pct": abs(metrics.net_profit_pct - b.net_profit_pct)
        <= net_profit_abs_tol,
        "profit_factor": abs(metrics.profit_factor - b.profit_factor)
        <= b.profit_factor_tolerance,
        "win_rate_pct": abs(metrics.win_rate_pct - b.win_rate_pct)
        <= b.win_rate_tolerance_pct_points,
        "max_drawdown_pct": abs(metrics.max_drawdown_pct - b.max_drawdown_pct)
        <= b.max_drawdown_tolerance_pct_points,
    }

    return {
        "passed": all(checks.values()),
        "checks": checks,
        "observed": {
            "trades": metrics.trades,
            "net_profit_pct": metrics.net_profit_pct,
            "profit_factor": metrics.profit_factor,
            "win_rate_pct": metrics.win_rate_pct,
            "max_drawdown_pct": metrics.max_drawdown_pct,
        },
        "benchmark": {
            "trades": b.trades,
            "net_profit_pct": b.net_profit_pct,
            "profit_factor": b.profit_factor,
            "win_rate_pct": b.win_rate_pct,
            "max_drawdown_pct": b.max_drawdown_pct,
        },
    }
