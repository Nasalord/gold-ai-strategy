from __future__ import annotations

import argparse
import json
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path

from ai_investing_lab.strategies.triple_macd_nq.config import TripleMACDNQConfig
from ai_investing_lab.strategies.triple_macd_nq.engine import TripleMACDNQBacktester
from scripts.run_exp6_public_nq_parity import load_minutes, metric_dict, resample_10m, write_trades

UTC = timezone.utc


def run_case(candles, cfg, start, end):
    return TripleMACDNQBacktester(cfg).run(
        candles,
        trade_start=start,
        trade_end=end,
        close_at_end=False,
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--warmup-start", default="2025-04-15")
    ap.add_argument("--trade-start", default="2025-06-01")
    ap.add_argument("--trade-end", default="2025-10-06")
    ap.add_argument("--out-dir", default="exp6_public_oos")
    args = ap.parse_args()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    rows, source_dates = load_minutes(args.warmup_start, args.trade_end)
    candles = resample_10m(rows)
    if not candles:
        raise SystemExit("no candles downloaded")

    start = datetime.fromisoformat(args.trade_start).replace(tzinfo=UTC)
    end = datetime.fromisoformat(args.trade_end).replace(tzinfo=UTC)
    base = TripleMACDNQConfig.creator_nq_10m()

    cases = {
        "creator_8_5m": base,
        "four_million": replace(base, order_cash_usd=4_000_000.0),
        "one_million_normalized": replace(base, order_cash_usd=1_000_000.0),
        "creator_8_5m_2x_costs": replace(
            base,
            commission_usd_per_contract_per_order=base.commission_usd_per_contract_per_order * 2.0,
            slippage_ticks=base.slippage_ticks * 2,
        ),
    }

    results = {name: run_case(candles, cfg, start, end) for name, cfg in cases.items()}
    metrics = {name: metric_dict(result) for name, result in results.items()}

    # Direction-level P&L/trade counts are diagnostics only; they do not change
    # or select strategy parameters.
    direction = {}
    for name, result in results.items():
        d = {}
        for side in ("long", "short"):
            trades = [t for t in result.trades if t.closed and t.side.value == side]
            gp = sum(t.net_pnl_usd for t in trades if t.net_pnl_usd > 0)
            gl = abs(sum(t.net_pnl_usd for t in trades if t.net_pnl_usd <= 0))
            d[side] = {
                "trades": len(trades),
                "wins": sum(1 for t in trades if t.net_pnl_usd > 0),
                "net_pnl_usd": sum(t.net_pnl_usd for t in trades),
                "profit_factor": gp / gl if gl else (float("inf") if gp else 0.0),
            }
        direction[name] = d

    report = {
        "experiment": "EXP6 Triple MACD NQ 10m",
        "status": "UNTOUCHED PUBLIC-DATA OOS — PARAMETERS FROZEN",
        "source": {
            "repository": "MeNameek/AnooReplay",
            "warmup_start": args.warmup_start,
            "trade_start": args.trade_start,
            "trade_end": args.trade_end,
            "daily_files": len(source_dates),
            "minute_rows": len(rows),
            "ten_minute_bars": len(candles),
            "first_bar": candles[0].time.isoformat(),
            "last_bar": candles[-1].time.isoformat(),
        },
        "metrics": metrics,
        "direction_diagnostics": direction,
        "frozen_config": asdict(base),
        "notes": [
            "This window begins immediately after the creator's stated Jan-Jun 2025 OOS cutoff.",
            "No parameters were changed based on creator OOS or this window.",
            "The public continuous series is independent of TradingView and exact creator parity remains unresolved (24 vs 27 trades in Jan-Jun 2025).",
            "2x-cost stress doubles both per-contract commission and slippage ticks while keeping signals frozen.",
            "Research/paper-only; no live execution.",
        ],
    }

    (out / "exp6_public_oos.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    for name, result in results.items():
        write_trades(out / f"trades_{name}.csv", result)

    b = metrics["creator_8_5m"]
    c = metrics["creator_8_5m_2x_costs"]
    n = metrics["one_million_normalized"]
    md = [
        "# Experiment 6 — Triple MACD NQ 10m untouched public-data OOS",
        "",
        "Status: **UNTOUCHED OOS — PARAMETERS FROZEN**",
        "",
        f"Window: **{args.trade_start} through {args.trade_end}**",
        "",
        "## Creator $8.5M sizing",
        f"- Trades: {b['trades']}",
        f"- Win rate: {b['win_rate_pct']:.2f}%",
        f"- Net profit: {b['net_profit_pct']:.2f}%",
        f"- Profit factor: {b['profit_factor']:.4f}",
        f"- Closed-trade DD: {b['max_closed_trade_drawdown_pct']:.2f}%",
        "",
        "## Normalized $1M cash sizing",
        f"- Trades: {n['trades']}",
        f"- Net profit: {n['net_profit_pct']:.2f}%",
        f"- Profit factor: {n['profit_factor']:.4f}",
        f"- Closed-trade DD: {n['max_closed_trade_drawdown_pct']:.2f}%",
        "",
        "## 2x execution-cost stress at creator sizing",
        f"- Trades: {c['trades']}",
        f"- Net profit: {c['net_profit_pct']:.2f}%",
        f"- Profit factor: {c['profit_factor']:.4f}",
        f"- Closed-trade DD: {c['max_closed_trade_drawdown_pct']:.2f}%",
        "",
        "No retuning is permitted after observing this window.",
    ]
    (out / "EXP6_PUBLIC_OOS.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
