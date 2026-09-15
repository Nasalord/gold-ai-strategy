from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from ai_investing_lab.strategies.triple_macd_nq.config import TripleMACDNQConfig
from ai_investing_lab.strategies.triple_macd_nq.engine import TripleMACDNQBacktester
from scripts.run_exp6_2026_sample import download_rows, resample
from scripts.run_exp6_public_nq_parity import metric_dict

UTC = timezone.utc


def main() -> int:
    out = Path("exp6_2026_robustness")
    out.mkdir(parents=True, exist_ok=True)
    rows, headers = download_rows()
    candles = resample(rows)
    start = datetime(2026, 5, 1, tzinfo=UTC)
    end = datetime(2026, 9, 3, tzinfo=UTC)
    base = TripleMACDNQConfig.creator_nq_10m()

    variants = {
        "BASELINE": base,
        "long_fast_135": replace(base, long_fast=135),
        "long_fast_165": replace(base, long_fast=165),
        "long_slow_405": replace(base, long_slow=405),
        "long_slow_495": replace(base, long_slow=495),
        "mid_fast_40": replace(base, mid_fast=40),
        "mid_fast_50": replace(base, mid_fast=50),
        "mid_slow_63": replace(base, mid_slow=63),
        "mid_slow_77": replace(base, mid_slow=77),
        "short_fast_25": replace(base, short_fast=25),
        "short_fast_31": replace(base, short_fast=31),
        "short_slow_21": replace(base, short_slow=21),
        "short_slow_25": replace(base, short_slow=25),
        "tdfi_lookback_45": replace(base, tdfi_lookback=45),
        "tdfi_lookback_55": replace(base, tdfi_lookback=55),
        "tdfi_high_085": replace(base, tdfi_high=0.85),
        "tdfi_high_095": replace(base, tdfi_high=0.95),
        "tdfi_low_m075": replace(base, tdfi_low=-0.75),
        "tdfi_low_m085": replace(base, tdfi_low=-0.85),
        "sl_lookback_8": replace(base, sl_lookback=8),
        "sl_lookback_12": replace(base, sl_lookback=12),
        "rr_3_0": replace(base, risk_reward=3.0),
        "rr_4_0": replace(base, risk_reward=4.0),
    }

    results = {}
    for name, cfg in variants.items():
        r = TripleMACDNQBacktester(cfg).run(candles, trade_start=start, trade_end=end, close_at_end=False)
        m = metric_dict(r)
        results[name] = m
        print(f"{name:20s} trades={m['trades']:2d} net={m['net_profit_pct']:8.3f}% PF={m['profit_factor']:.4f} DD={m['max_closed_trade_drawdown_pct']:.2f}%")

    neighbors = {k:v for k,v in results.items() if k != "BASELINE"}
    summary = {
        "neighbors": len(neighbors),
        "positive_net": sum(v["net_profit_pct"] > 0 for v in neighbors.values()),
        "pf_gt_1": sum(v["profit_factor"] > 1 for v in neighbors.values()),
        "positive_and_pf_gt_1": sum(v["net_profit_pct"] > 0 and v["profit_factor"] > 1 for v in neighbors.values()),
        "sample_warning": "Very small trade counts; robustness breadth is descriptive, not conclusive.",
    }
    report = {
        "experiment": "EXP6 Triple MACD NQ 10m",
        "status": "WARMUP-CORRECTED 2026 RECOVERY ROBUSTNESS — PARAMETERS FROZEN",
        "window": {"start": "2026-05-01", "end": "2026-09-03"},
        "source": {"repository": "getdata-finance/nq-1m-ohlcv-stocks-historical-data", "headers": headers, "minute_rows": len(rows), "ten_minute_bars": len(candles)},
        "results": results,
        "summary": summary,
        "guardrail": "Do not select or retune a neighbor based on this OOS window.",
    }
    (out / "exp6_2026_robustness.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = ["# Experiment 6 — 2026 recovery robustness", "", "Parameters frozen. Small-sample diagnostic only.", "", f"- Neighbours: {summary['neighbors']}", f"- Positive + PF > 1: {summary['positive_and_pf_gt_1']}", "", "| Variant | Trades | Net % | PF | Closed DD % |", "|---|---:|---:|---:|---:|"]
    for name,m in results.items():
        lines.append(f"| {name} | {m['trades']} | {m['net_profit_pct']:.3f} | {m['profit_factor']:.3f} | {m['max_closed_trade_drawdown_pct']:.2f} |")
    (out / "EXP6_2026_ROBUSTNESS.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
