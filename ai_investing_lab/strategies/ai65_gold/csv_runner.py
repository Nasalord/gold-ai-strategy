from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

from .config import AI65Config, ExecutionMode, SizingMode, TDFIGating
from .orb_engine import AI65Backtester, Candle, Trade
from .parity import evaluate_creator_parity


def load_candles_csv(path: str | Path) -> list[Candle]:
    """Load timestamp,open,high,low,close from a timezone-aware CSV."""
    candles: list[Candle] = []
    with Path(path).open("r", newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            ts = datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
            if ts.tzinfo is None:
                raise ValueError("CSV timestamps must include a timezone/UTC offset")
            candles.append(
                Candle(
                    time=ts,
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                )
            )
    return candles


def trade_dict(trade: Trade) -> dict[str, object]:
    return {
        "session_date": trade.session_date.isoformat(),
        "order_arm_time": trade.order_arm_time.isoformat() if trade.order_arm_time else None,
        "breakout_time": trade.breakout_time.isoformat() if trade.breakout_time else None,
        "entry_time": trade.entry_time.isoformat(),
        "entry_price": trade.entry_price,
        "quantity": trade.quantity,
        "theoretical_quantity": trade.theoretical_quantity,
        "notional_exposure": trade.notional_exposure,
        "equity_at_entry": trade.equity_at_entry,
        "risk_dollars": trade.risk_dollars,
        "risk_percent": trade.risk_percent,
        "or_high": trade.or_high,
        "or_low": trade.or_low,
        "or_width": trade.or_width,
        "base_distance": trade.base_distance,
        "stop_price": trade.stop_price,
        "target_price": trade.target_price,
        "tdfi_at_range_end": trade.tdfi_at_range_end,
        "tdfi_at_arm": trade.tdfi_at_arm,
        "tdfi_at_entry": trade.tdfi_at_entry,
        "entry_slippage_cost": trade.entry_slippage_cost,
        "exit_slippage_cost": trade.exit_slippage_cost,
        "exit_time": trade.exit_time.isoformat() if trade.exit_time else None,
        "exit_price": trade.exit_price,
        "exit_reason": trade.exit_reason.value if trade.exit_reason else None,
        "ambiguous_same_bar": trade.ambiguous_same_bar,
        "commission": trade.commission,
        "gross_pnl": trade.gross_pnl,
        "net_pnl": trade.net_pnl,
        "mae_price": trade.mae_price,
        "mfe_price": trade.mfe_price,
        "holding_minutes": trade.holding_minutes,
        "r_multiple": trade.r_multiple,
    }


def result_dict(result, config: AI65Config) -> dict[str, object]:
    m = result.metrics
    return {
        "config": {
            "symbol": config.symbol,
            "timeframe_minutes": config.timeframe_minutes,
            "timezone": config.timezone,
            "execution_mode": config.execution_mode.value,
            "tdfi_gating": config.tdfi_gating.value,
            "sizing_mode": config.sizing_mode.value,
            "stop_mult": config.stop_mult,
            "target_mult": config.target_mult,
            "tdfi_lookback": config.tdfi_lookback,
            "tdfi_long_threshold": config.tdfi_long_threshold,
            "force_exit": config.force_exit.isoformat(timespec="minutes"),
            "commission_per_contract_per_side": config.commission_per_contract_per_side,
            "slippage_ticks": config.slippage_ticks,
            "min_tick": config.min_tick,
        },
        "metrics": {
            "trades": m.trades,
            "wins": m.wins,
            "losses": m.losses,
            "win_rate_pct": m.win_rate_pct,
            "gross_profit": m.gross_profit,
            "gross_loss": m.gross_loss,
            "net_profit": m.net_profit,
            "net_profit_pct": m.net_profit_pct,
            "profit_factor": m.profit_factor,
            "expectancy": m.expectancy,
            "average_winner": m.average_winner,
            "average_loser": m.average_loser,
            "average_r": m.average_r,
            "max_drawdown_pct": m.max_drawdown_pct,
            "ambiguous_trades": m.ambiguous_trades,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Research-only backtest for AI65 Gold ORB from OHLC CSV"
    )
    parser.add_argument("csv_path")
    parser.add_argument("--timeframe", type=int, default=60)
    parser.add_argument(
        "--mode",
        choices=[x.value for x in ExecutionMode],
        default=ExecutionMode.REPLICA.value,
    )
    parser.add_argument(
        "--tdfi-gating",
        choices=[x.value for x in TDFIGating],
        default=TDFIGating.ARM_TIME.value,
    )
    parser.add_argument(
        "--sizing",
        choices=[x.value for x in SizingMode],
        default=None,
        help="Defaults to creator fixed-notional in replica mode and capped risk-based in guarded mode.",
    )
    parser.add_argument("--risk-per-trade-pct", type=float, default=0.25)
    parser.add_argument("--max-notional", type=float, default=10_000.0)
    parser.add_argument("--fixed-notional", type=float, default=70_000.0)
    parser.add_argument("--min-tick", type=float, default=0.01)
    parser.add_argument("--slippage-ticks", type=int, default=100)
    parser.add_argument("--commission-per-contract-side", type=float, default=0.04)
    parser.add_argument("--trades-json", type=Path)
    parser.add_argument(
        "--check-creator-parity",
        action="store_true",
        help="Compare metrics to the ranking-sheet 1H AI65 benchmark. Do not use as an optimizer.",
    )
    args = parser.parse_args()

    mode = ExecutionMode(args.mode)
    sizing = (
        SizingMode(args.sizing)
        if args.sizing is not None
        else (
            SizingMode.CREATOR_FIXED_NOTIONAL
            if mode == ExecutionMode.REPLICA
            else SizingMode.RISK_BASED
        )
    )

    config = AI65Config(
        timeframe_minutes=args.timeframe,
        execution_mode=mode,
        tdfi_gating=TDFIGating(args.tdfi_gating),
        sizing_mode=sizing,
        risk_per_trade_pct=args.risk_per_trade_pct,
        max_notional=args.max_notional,
        fixed_notional=args.fixed_notional,
        min_tick=args.min_tick,
        slippage_ticks=args.slippage_ticks,
        commission_per_contract_per_side=args.commission_per_contract_side,
    )

    candles = load_candles_csv(args.csv_path)
    result = AI65Backtester(config).run(candles)

    payload = result_dict(result, config)
    if args.check_creator_parity:
        payload["creator_parity"] = evaluate_creator_parity(result.metrics)

    if args.trades_json is not None:
        args.trades_json.write_text(
            json.dumps([trade_dict(t) for t in result.trades], indent=2, allow_nan=True),
            encoding="utf-8",
        )
        payload["trade_log_path"] = str(args.trades_json)

    print(json.dumps(payload, indent=2, allow_nan=True))


if __name__ == "__main__":
    main()
