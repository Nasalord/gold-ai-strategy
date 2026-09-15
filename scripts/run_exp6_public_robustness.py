from __future__ import annotations

import argparse
import json
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path

from ai_investing_lab.strategies.triple_macd_nq.config import TripleMACDNQConfig
from ai_investing_lab.strategies.triple_macd_nq.engine import TripleMACDNQBacktester
from scripts.run_exp6_public_nq_parity import load_minutes, metric_dict, resample_10m

UTC = timezone.utc


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--warmup-start", default="2025-04-15")
    ap.add_argument("--trade-start", default="2025-06-01")
    ap.add_argument("--trade-end", default="2025-10-06")
    ap.add_argument("--out-dir", default="exp6_public_robustness")
    args = ap.parse_args()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rows, source_dates = load_minutes(args.warmup_start, args.trade_end)
    candles = resample_10m(rows)
    start = datetime.fromisoformat(args.trade_start).replace(tzinfo=UTC)
    end = datetime.fromisoformat(args.trade_end).replace(tzinfo=UTC)

    base = TripleMACDNQConfig.creator_nq_10m()
    # PREDECLARED one-factor local neighbours. These are diagnostics only and
    # MUST NOT be used to select/re-optimize a replacement after observing OOS.
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
        result = TripleMACDNQBacktester(cfg).run(
            candles, trade_start=start, trade_end=end, close_at_end=False
        )
        results[name] = metric_dict(result)
        m = results[name]
        print(f"{name:20s} trades={m['trades']:3d} net={m['net_profit_pct']:8.3f}% PF={m['profit_factor']:.4f} DD={m['max_closed_trade_drawdown_pct']:.2f}%")

    neighbors = {k: v for k, v in results.items() if k != "BASELINE"}
    positive = sum(1 for v in neighbors.values() if v["net_profit_pct"] > 0)
    pf_gt_1 = sum(1 for v in neighbors.values() if v["profit_factor"] > 1.0)
    both = sum(1 for v in neighbors.values() if v["net_profit_pct"] > 0 and v["profit_factor"] > 1.0)
    summary = {
        "neighbors": len(neighbors),
        "positive_net": positive,
        "pf_gt_1": pf_gt_1,
        "positive_and_pf_gt_1": both,
        "negative_or_pf_le_1": len(neighbors) - both,
    }

    report = {
        "experiment": "EXP6 Triple MACD NQ 10m",
        "status": "PREDECLARED LOCAL ROBUSTNESS — UNTOUCHED PUBLIC OOS",
        "window": {"start": args.trade_start, "end": args.trade_end},
        "source": {"repository": "MeNameek/AnooReplay", "daily_files": len(source_dates), "minute_rows": len(rows), "ten_minute_bars": len(candles)},
        "baseline_config": asdict(base),
        "results": results,
        "summary": summary,
        "guardrail": "Do not select the best neighbour or retune the frozen strategy using these OOS results.",
    }
    (out / "exp6_public_robustness.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = [
        "# Experiment 6 — Triple MACD NQ OOS robustness",
        "",
        "This is a predeclared local-neighbour diagnostic. **No neighbour may replace the frozen baseline based on these results.**",
        "",
        f"Window: {args.trade_start} through {args.trade_end}",
        "",
        f"- Neighbours tested: {summary['neighbors']}",
        f"- Positive net: {summary['positive_net']}",
        f"- PF > 1: {summary['pf_gt_1']}",
        f"- Positive + PF > 1: {summary['positive_and_pf_gt_1']}",
        f"- Failed either condition: {summary['negative_or_pf_le_1']}",
        "",
        "| Variant | Trades | Net % | PF | Closed DD % |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, m in results.items():
        lines.append(f"| {name} | {m['trades']} | {m['net_profit_pct']:.3f} | {m['profit_factor']:.3f} | {m['max_closed_trade_drawdown_pct']:.2f} |")
    (out / "EXP6_PUBLIC_ROBUSTNESS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
