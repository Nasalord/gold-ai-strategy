from __future__ import annotations

from dataclasses import dataclass

from .orb_engine import BacktestMetrics


@dataclass(frozen=True)
class VideoBenchmark:
    """Creator metrics shown for the recovered optimized video settings.

    Window: 2021-09-01 through 2025-09-01 on IC Markets USDJPY 15m.
    The video verbally rounds net profit, PF and drawdown, so tolerances are
    intentionally wider than for exact spreadsheet figures.
    """

    trades: int = 185
    net_profit_pct: float = 287.0
    profit_factor: float = 1.70
    max_drawdown_pct: float = 17.0

    trade_tolerance: int = 3
    net_profit_relative_tolerance: float = 0.08
    profit_factor_tolerance: float = 0.08
    max_drawdown_tolerance_pct_points: float = 3.0


@dataclass(frozen=True)
class RankingSheetBenchmark:
    """Later ranking-sheet snapshot; not the first target for the video preset."""

    trades: int = 229
    net_profit_pct: float = 309.74
    profit_factor: float = 1.736
    win_rate_pct: float = 45.41
    max_drawdown_pct: float = 20.79

    trade_tolerance: int = 1
    net_profit_relative_tolerance: float = 0.05
    profit_factor_tolerance: float = 0.03
    win_rate_tolerance_pct_points: float = 0.20
    max_drawdown_tolerance_pct_points: float = 1.0


@dataclass(frozen=True)
class VideoOOSBenchmark:
    """Post-optimization metrics shown in the video.

    Window: 2025-09-01 through 2026-03-14.
    """

    trades: int = 24
    net_profit_pct: float = 32.0
    profit_factor: float = 1.57
    win_rate_pct: float = 50.0
    max_drawdown_pct: float = 14.0


def evaluate_video_parity(
    metrics: BacktestMetrics,
    benchmark: VideoBenchmark | None = None,
) -> dict[str, object]:
    b = benchmark or VideoBenchmark()
    net_tol = abs(b.net_profit_pct) * b.net_profit_relative_tolerance
    checks = {
        "trades": abs(metrics.trades - b.trades) <= b.trade_tolerance,
        "net_profit_pct": abs(metrics.net_profit_pct - b.net_profit_pct) <= net_tol,
        "profit_factor": abs(metrics.profit_factor - b.profit_factor)
        <= b.profit_factor_tolerance,
        "max_drawdown_pct": abs(metrics.max_drawdown_pct - b.max_drawdown_pct)
        <= b.max_drawdown_tolerance_pct_points,
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "observed": _observed(metrics),
        "benchmark": {
            "trades": b.trades,
            "net_profit_pct": b.net_profit_pct,
            "profit_factor": b.profit_factor,
            "max_drawdown_pct": b.max_drawdown_pct,
        },
    }


def evaluate_ranking_sheet_parity(
    metrics: BacktestMetrics,
    benchmark: RankingSheetBenchmark | None = None,
) -> dict[str, object]:
    b = benchmark or RankingSheetBenchmark()
    net_tol = abs(b.net_profit_pct) * b.net_profit_relative_tolerance
    checks = {
        "trades": abs(metrics.trades - b.trades) <= b.trade_tolerance,
        "net_profit_pct": abs(metrics.net_profit_pct - b.net_profit_pct) <= net_tol,
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
        "observed": _observed(metrics),
        "benchmark": {
            "trades": b.trades,
            "net_profit_pct": b.net_profit_pct,
            "profit_factor": b.profit_factor,
            "win_rate_pct": b.win_rate_pct,
            "max_drawdown_pct": b.max_drawdown_pct,
        },
    }


def evaluate_creator_parity(
    metrics: BacktestMetrics,
    benchmark: RankingSheetBenchmark | None = None,
) -> dict[str, object]:
    """Backward-compatible alias for the ranking-sheet diagnostic."""
    return evaluate_ranking_sheet_parity(metrics, benchmark)


def _observed(metrics: BacktestMetrics) -> dict[str, float | int]:
    return {
        "trades": metrics.trades,
        "net_profit_pct": metrics.net_profit_pct,
        "profit_factor": metrics.profit_factor,
        "win_rate_pct": metrics.win_rate_pct,
        "max_drawdown_pct": metrics.max_drawdown_pct,
    }
