from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ai_investing_lab.strategies.ai2_eth import AI2Backtester, AI2Config, Candle


OOS_START = datetime(2024, 3, 1, tzinfo=timezone.utc)
MIN_12M_TRADES = 20


def parse_dt(value: str) -> datetime:
    x = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return x if x.tzinfo else x.replace(tzinfo=timezone.utc)


def load_csv(path: str) -> list[Candle]:
    out: list[Candle] = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            out.append(Candle(
                time=parse_dt(row["time"]),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row.get("volume", 0.0) or 0.0),
            ))
    return out


def run_window(candles: list[Candle], cfg: AI2Config, start: datetime, end: datetime):
    return AI2Backtester(cfg).run(candles, trade_start=start, trade_end=end, close_at_end=False)


def classify(metrics: dict[str, dict]) -> tuple[str, str]:
    m6 = metrics["trailing_6m"]
    m12 = metrics["trailing_12m"]
    ytd = metrics["calendar_ytd"]

    if m12["trades"] < MIN_12M_TRADES:
        return "observing_insufficient_sample", f"OBSERVING — {m12['trades']}/{MIN_12M_TRADES} trailing-12m trades"

    if m12["net_profit_pct"] < 0 and m12["profit_factor"] < 0.80:
        return "structural_concern", "STRUCTURAL CONCERN — trailing 12m net negative with PF < 0.80"

    six_good = m6["net_profit_pct"] > 0 and m6["profit_factor"] > 1.0
    twelve_good = m12["net_profit_pct"] > 0 and m12["profit_factor"] > 1.0
    ytd_good = ytd["net_profit_pct"] > 0 and ytd["profit_factor"] > 1.0

    if six_good and twelve_good and ytd_good:
        return "healthy", "HEALTHY — 6m, 12m and YTD net positive with PF > 1"
    if six_good and (not ytd_good or not twelve_good):
        return "weak_recovering", "WEAK / RECOVERING — recent 6m positive but a broader window remains weak"
    if twelve_good and not six_good:
        return "weak_recent", "WEAK RECENTLY — trailing 12m positive but latest 6m is weak"
    return "weak", "WEAK — recent frozen windows do not all support PF > 1"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--analysis-end", required=True, help="exclusive UTC date/time")
    ap.add_argument("--output-dir", default="ai2_health")
    args = ap.parse_args()

    candles = load_csv(args.csv)
    end = parse_dt(args.analysis_end)
    cfg = replace(AI2Config.creator_15m(), fixed_cash_usd=10_000.0)

    starts = {
        "trailing_6m": end - timedelta(days=183),
        "trailing_12m": end - timedelta(days=365),
        "trailing_24m": end - timedelta(days=730),
        "calendar_ytd": datetime(end.year, 1, 1, tzinfo=timezone.utc),
        "full_frozen_oos": OOS_START,
    }
    metrics = {
        name: asdict(run_window(candles, cfg, max(start, OOS_START), end).metrics)
        for name, start in starts.items()
    }

    stress_cfg = replace(cfg, commission_pct_per_side=0.2, slippage_ticks=4)
    stress_12m = asdict(run_window(candles, stress_cfg, max(starts["trailing_12m"], OOS_START), end).metrics)

    classification, headline = classify(metrics)
    report = {
        "strategy": "AI2 Simple Triple MA ETHUSDT 15m",
        "mode": "NORMALIZED 1x SHADOW-PAPER RESEARCH ONLY",
        "classification": classification,
        "headline": headline,
        "analysis_end_exclusive": end.isoformat(),
        "normalized_cash_per_trade_usd": 10_000.0,
        "reference_initial_capital_usd": 10_000.0,
        "creator_cash_per_trade_usd": 40_000.0,
        "metrics": metrics,
        "trailing_12m_2x_costs": stress_12m,
        "frozen_health_rules": {
            "sample_gate": f"trailing 12m must have >= {MIN_12M_TRADES} closed trades",
            "structural_concern": "trailing 12m net < 0 and PF < 0.80",
            "healthy": "6m, 12m and calendar YTD each net > 0 and PF > 1",
            "weak_recovering": "6m net > 0 and PF > 1 while 12m or YTD remains weak",
            "weak_recent": "12m net > 0 and PF > 1 while 6m is weak",
            "weak": "otherwise once sample gate is met",
        },
        "permanent_caveats": [
            "Creator parity passed essentially exactly on 2020-03-01 to 2024-03-01.",
            "Creator 4x cash sizing is rejected because historical drawdowns were ruin-level.",
            "Fresh OOS 2024-03-01 through 2026-09-15 remained profitable and 12/12 predeclared neighbours passed.",
            "Calendar 2025 was near breakeven and calendar 2026 was weak at the initial validation date.",
            "No future observation may be used to retune the frozen strategy parameters.",
            "This workflow never places orders and is not a live-trading system.",
        ],
    }

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "ai2_health.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    md = [
        "# AI2 ETHUSDT — Shadow Health",
        "",
        f"**{headline}**",
        "",
        "Normalized research sizing: **$10,000 cash per trade on $10,000 reference capital (1x)**.",
        "Creator 4x sizing is intentionally not used by this monitor.",
        "",
        "| Window | Trades | Net % | PF | Win % | Closed-trade DD % |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    labels = {
        "trailing_6m": "Trailing 6m",
        "trailing_12m": "Trailing 12m",
        "trailing_24m": "Trailing 24m",
        "calendar_ytd": f"Calendar {end.year} YTD",
        "full_frozen_oos": "Full frozen OOS since 2024-03-01",
    }
    for key in ["trailing_6m", "trailing_12m", "trailing_24m", "calendar_ytd", "full_frozen_oos"]:
        m = metrics[key]
        md.append(f"| {labels[key]} | {m['trades']} | {m['net_profit_pct']:.3f} | {m['profit_factor']:.4f} | {m['win_rate_pct']:.2f} | {m['max_closed_trade_drawdown_pct']:.2f} |")
    md.extend([
        "",
        "## 2x-cost stress — trailing 12m",
        "",
        f"{stress_12m['trades']} trades, {stress_12m['net_profit_pct']:.3f}% net, PF {stress_12m['profit_factor']:.4f}, closed-trade DD {stress_12m['max_closed_trade_drawdown_pct']:.2f}%.",
        "",
        "## Permanent caveats",
        "",
    ])
    md.extend(f"- {x}" for x in report["permanent_caveats"])
    (out / "AI2_HEALTH.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
