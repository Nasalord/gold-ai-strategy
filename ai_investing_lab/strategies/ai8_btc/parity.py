from __future__ import annotations

from dataclasses import dataclass

from .engine import Metrics


@dataclass(frozen=True)
class CreatorBenchmark:
    trades: int = 319
    net_profit_pct: float = 637.97
    profit_factor: float = 1.969
    win_rate_pct: float = 44.51
    max_drawdown_pct: float = 27.87

    trade_tolerance: int = 4
    net_profit_relative_tolerance: float = 0.08
    profit_factor_tolerance: float = 0.08
    win_rate_tolerance_pct_points: float = 1.5
    max_drawdown_tolerance_pct_points: float = 4.0


def evaluate_creator_parity(metrics: Metrics, benchmark: CreatorBenchmark | None = None) -> dict[str, object]:
    b = benchmark or CreatorBenchmark()
    checks = {
        "trades": abs(metrics.trades - b.trades) <= b.trade_tolerance,
        "net_profit_pct": abs(metrics.net_profit_pct - b.net_profit_pct)
        <= abs(b.net_profit_pct) * b.net_profit_relative_tolerance,
        "profit_factor": abs(metrics.profit_factor - b.profit_factor)
        <= b.profit_factor_tolerance,
        "win_rate_pct": abs(metrics.win_rate_pct - b.win_rate_pct)
        <= b.win_rate_tolerance_pct_points,
        "max_drawdown_pct": abs(metrics.max_closed_trade_drawdown_pct - b.max_drawdown_pct)
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
            "max_closed_trade_drawdown_pct": metrics.max_closed_trade_drawdown_pct,
        },
        "benchmark": {
            "trades": b.trades,
            "net_profit_pct": b.net_profit_pct,
            "profit_factor": b.profit_factor,
            "win_rate_pct": b.win_rate_pct,
            "max_drawdown_pct": b.max_drawdown_pct,
        },
    }
