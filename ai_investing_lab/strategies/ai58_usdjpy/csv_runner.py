from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, time
from pathlib import Path

from .config import AI58Config, SizingMode, TradeDirection
from .orb_engine import AI58Backtester, Candle, Trade
from .parity import evaluate_creator_parity


def parse_clock(value: str) -> time:
    try:
        return datetime.strptime(value, "%H:%M").time()
    except ValueError as exc:
        raise argparse.ArgumentTypeError("time must be HH:MM") from exc


def load_candles_csv(path: str | Path) -> list[Candle]:
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
        "side": trade.side.value,
        "order_arm_time": trade.order_arm_time.isoformat() if trade.order_arm_time else None,
        "entry_time": trade.entry_time.isoformat(),
        "entry_price": trade.entry_price,
        "quantity_base_usd": trade.quantity_base_usd,
        "theoretical_quantity_base_usd": trade.theoretical_quantity_base_usd,
        "notional_usd": trade.notional_usd,
        "equity_at_entry_usd": trade.equity_at_entry_usd,
        "risk_usd": trade.risk_usd,
        "risk_percent": trade.risk_percent,
        "or_high": trade.or_high,
        "or_low": trade.or_low,
        "or_width": trade.or_width,
        "base_distance_jpy": trade.base_distance_jpy,
        "stop_price": trade.stop_price,
        "target_price": trade.target_price,
        "initial_trailing_stop": trade.initial_trailing_stop,
        "trailing_stop": trade.trailing_stop,
        "tdfi_at_arm": trade.tdfi_at_arm,
        "entry_slippage_price": trade.entry_slippage_price,
        "exit_slippage_price": trade.exit_slippage_price,
        "exit_time": trade.exit_time.isoformat() if trade.exit_time else None,
        "exit_price": trade.exit_price,
        "exit_reason": trade.exit_reason.value if trade.exit_reason else None,
        "ambiguous_same_bar": trade.ambiguous_same_bar,
        "gross_pnl_usd": trade.gross_pnl_usd,
        "commission_usd": trade.commission_usd,
        "net_pnl_usd": trade.net_pnl_usd,
        "mae_jpy": trade.mae_jpy,
        "mfe_jpy": trade.mfe_jpy,
        "holding_minutes": trade.holding_minutes,
        "r_multiple": trade.r_multiple,
    }


def result_dict(result, config: AI58Config) -> dict[str, object]:
    m = result.metrics
    return {
        "config": {
            "symbol": config.symbol,
            "timeframe_minutes": config.timeframe_minutes,
            "timezone": config.timezone,
            "range_start": config.range_start.isoformat(timespec="minutes"),
            "range_end": config.range_end.isoformat(timespec="minutes"),
            "direction": config.direction.value,
            "stop_mult": config.stop_mult,
            "tp_rr": config.tp_rr,
            "use_force_exit": config.use_force_exit,
            "force_exit": config.force_exit.isoformat(timespec="minutes"),
            "use_tdfi": config.use_tdfi,
            "tdfi_lookback": config.tdfi_lookback,
            "tdfi_filter_high": config.tdfi_filter_high,
            "tdfi_filter_low": config.tdfi_filter_low,
            "use_trailing_atr": config.use_trailing_atr,
            "trailing_atr_length": config.trailing_atr_length,
            "trailing_atr_multiplier": config.trailing_atr_multiplier,
            "sizing_mode": config.sizing_mode.value,
            "fixed_notional_usd": config.fixed_notional_usd,
            "risk_per_trade_pct": config.risk_per_trade_pct,
            "max_notional_usd": config.max_notional_usd,
            "slippage_ticks": config.slippage_ticks,
            "min_tick": config.min_tick,
            "commission_usd_per_standard_lot_per_side": config.commission_usd_per_standard_lot_per_side,
        },
        "metrics": {
            "trades": m.trades,
            "wins": m.wins,
            "losses": m.losses,
            "long_trades": m.long_trades,
            "short_trades": m.short_trades,
            "win_rate_pct": m.win_rate_pct,
            "net_profit_usd": m.net_profit_usd,
            "net_profit_pct": m.net_profit_pct,
            "profit_factor": m.profit_factor,
            "expectancy_usd": m.expectancy_usd,
            "average_r": m.average_r,
            "max_drawdown_pct": m.max_drawdown_pct,
            "ambiguous_trades": m.ambiguous_trades,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Research-only AI58 USDJPY ORB backtest from timezone-aware OHLC CSV"
    )
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--timeframe", type=int, default=15)
    parser.add_argument("--timezone", default="America/New_York")
    parser.add_argument("--range-start", type=parse_clock, default=time(9, 30))
    parser.add_argument("--range-end", type=parse_clock, default=time(9, 45))
    parser.add_argument(
        "--direction",
        choices=[x.value for x in TradeDirection],
        default=TradeDirection.BOTH.value,
    )
    parser.add_argument("--stop-mult", type=float, default=1.0)
    parser.add_argument("--tp-rr", type=float, default=1.5)

    parser.add_argument("--use-force-exit", action="store_true")
    parser.add_argument("--force-exit", type=parse_clock, default=time(16, 0))

    parser.add_argument("--use-tdfi", action="store_true")
    parser.add_argument("--tdfi-lookback", type=int, default=13)
    parser.add_argument("--tdfi-high", type=float, default=0.05)
    parser.add_argument("--tdfi-low", type=float, default=-0.05)

    parser.add_argument("--use-trailing-atr", action="store_true")
    parser.add_argument("--atr-length", type=int, default=14)
    parser.add_argument("--atr-mult", type=float, default=5.0)

    parser.add_argument(
        "--sizing",
        choices=[x.value for x in SizingMode],
        default=SizingMode.CREATOR_FIXED_NOTIONAL.value,
    )
    parser.add_argument("--fixed-notional-usd", type=float, default=70_000.0)
    parser.add_argument("--risk-per-trade-pct", type=float, default=0.25)
    parser.add_argument("--max-notional-usd", type=float, default=10_000.0)

    parser.add_argument("--slippage-ticks", type=int, default=12)
    parser.add_argument("--min-tick", type=float, default=0.001)
    parser.add_argument("--commission-per-lot-side", type=float, default=3.50)
    parser.add_argument("--standard-lot-units", type=float, default=100_000.0)

    parser.add_argument("--trades-json", type=Path)
    parser.add_argument(
        "--check-creator-parity",
        action="store_true",
        help="Diagnostic only. Use only after all optimized inputs and the benchmark interval are independently verified.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = AI58Config(
        timeframe_minutes=args.timeframe,
        timezone=args.timezone,
        range_start=args.range_start,
        range_end=args.range_end,
        direction=TradeDirection(args.direction),
        stop_mult=args.stop_mult,
        tp_rr=args.tp_rr,
        use_force_exit=args.use_force_exit,
        force_exit=args.force_exit,
        use_tdfi=args.use_tdfi,
        tdfi_lookback=args.tdfi_lookback,
        tdfi_filter_high=args.tdfi_high,
        tdfi_filter_low=args.tdfi_low,
        use_trailing_atr=args.use_trailing_atr,
        trailing_atr_length=args.atr_length,
        trailing_atr_multiplier=args.atr_mult,
        sizing_mode=SizingMode(args.sizing),
        fixed_notional_usd=args.fixed_notional_usd,
        risk_per_trade_pct=args.risk_per_trade_pct,
        max_notional_usd=args.max_notional_usd,
        slippage_ticks=args.slippage_ticks,
        min_tick=args.min_tick,
        commission_usd_per_standard_lot_per_side=args.commission_per_lot_side,
        standard_lot_base_units=args.standard_lot_units,
    )

    candles = load_candles_csv(args.csv_path)
    result = AI58Backtester(config).run(candles)
    payload = result_dict(result, config)

    if args.check_creator_parity:
        payload["creator_parity"] = evaluate_creator_parity(result.metrics)
        payload["creator_parity_warning"] = (
            "This comparison is meaningful only if the optimized AI58 input set and benchmark interval were independently verified."
        )

    if args.trades_json is not None:
        args.trades_json.parent.mkdir(parents=True, exist_ok=True)
        args.trades_json.write_text(
            json.dumps([trade_dict(t) for t in result.trades], indent=2, allow_nan=True),
            encoding="utf-8",
        )
        payload["trade_log_path"] = str(args.trades_json)

    print(json.dumps(payload, indent=2, allow_nan=True))


if __name__ == "__main__":
    main()
