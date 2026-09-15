from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from ai_investing_lab.strategies.triple_macd_nq.config import TripleMACDNQConfig
from ai_investing_lab.strategies.triple_macd_nq.engine import TripleMACDNQBacktester
from scripts.run_exp6_public_nq_parity import load_minutes, metric_dict, resample_10m

UTC = timezone.utc

PERIODS = [
    ("2023", "2023-01-01", "2024-01-01"),
    ("2024", "2024-01-01", "2025-01-01"),
    ("creator_oos_2025", "2025-01-01", "2025-06-01"),
    ("fresh_oos_2025", "2025-06-01", "2025-10-06"),
]


def dt(s: str) -> datetime:
    return datetime.fromisoformat(s).replace(tzinfo=UTC)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="exp6_public_regimes")
    args = ap.parse_args()
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    rows, source_dates = load_minutes("2022-12-26", "2025-10-06")
    candles = resample_10m(rows)
    cfg = TripleMACDNQConfig.creator_nq_10m()

    results = {}
    for name, start, end in PERIODS:
        r = TripleMACDNQBacktester(cfg).run(candles, trade_start=dt(start), trade_end=dt(end), close_at_end=False)
        results[name] = metric_dict(r)
        m = results[name]
        print(f"{name:18s} trades={m['trades']:3d} net={m['net_profit_pct']:9.3f}% PF={m['profit_factor']:.4f} win={m['win_rate_pct']:.2f}% DD={m['max_closed_trade_drawdown_pct']:.2f}%")

    # Full public sample is descriptive only. Do not use it for tuning.
    full = TripleMACDNQBacktester(cfg).run(candles, trade_start=dt("2023-01-01"), trade_end=dt("2025-10-06"), close_at_end=False)
    results["full_public_2023_to_2025_10"] = metric_dict(full)

    report = {
        "experiment": "EXP6 Triple MACD NQ 10m",
        "status": "PUBLIC-DATA REGIME DIAGNOSTIC — PARAMETERS FROZEN",
        "source": {
            "repository": "MeNameek/AnooReplay",
            "daily_files": len(source_dates),
            "minute_rows": len(rows),
            "ten_minute_bars": len(candles),
            "first_bar": candles[0].time.isoformat(),
            "last_bar": candles[-1].time.isoformat(),
        },
        "results": results,
        "notes": [
            "2023 and 2024 overlap the creator's optimization era and are not independent OOS.",
            "creator_oos_2025 reproduces the creator's stated Jan-Jun 2025 holdout using an independent public continuous dataset.",
            "fresh_oos_2025 begins after the creator cutoff and is untouched evidence.",
            "Each named period is evaluated with a fresh strategy-state boundary while all indicators use the full preceding candle history.",
            "No result may be used to retune the frozen strategy.",
        ],
    }
    (out / "exp6_public_regimes.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = [
        "# Experiment 6 — Triple MACD NQ public-data regimes",
        "",
        "Parameters are frozen. 2023–2024 are descriptive optimization-era overlap, not independent OOS.",
        "",
        "| Period | Trades | Win % | Net % | PF | Closed DD % |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name, m in results.items():
        lines.append(f"| {name} | {m['trades']} | {m['win_rate_pct']:.2f} | {m['net_profit_pct']:.3f} | {m['profit_factor']:.3f} | {m['max_closed_trade_drawdown_pct']:.2f} |")
    (out / "EXP6_PUBLIC_REGIMES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
