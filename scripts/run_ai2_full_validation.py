from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path

from ai_investing_lab.strategies.ai2_eth import AI2Backtester, AI2Config, Candle


CREATOR = {
    "trades": 179,
    "net_profit_pct": 1561.38,
    "profit_factor": 1.993,
    "win_rate_pct": 39.66,
    "max_drawdown_pct": 27.33,
}
CREATOR_START = datetime(2020, 3, 1, tzinfo=timezone.utc)
CREATOR_END = datetime(2024, 3, 1, tzinfo=timezone.utc)
BACKLOG_START = datetime(2017, 8, 17, tzinfo=timezone.utc)


def dt(s: str) -> datetime:
    x = datetime.fromisoformat(s.replace("Z", "+00:00"))
    return x if x.tzinfo else x.replace(tzinfo=timezone.utc)


def load_csv(path: str) -> list[Candle]:
    out = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            out.append(Candle(
                time=dt(row["time"]),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row.get("volume", 0.0) or 0.0),
            ))
    return out


def metric_dict(result):
    return asdict(result.metrics)


def run_window(candles, cfg, start, end):
    return AI2Backtester(cfg).run(candles, trade_start=start, trade_end=end, close_at_end=False)


def buy_hold(candles, start, end):
    rows = [c for c in candles if start <= c.time < end]
    if len(rows) < 2:
        return None
    return 100.0 * (rows[-1].close / rows[0].open - 1.0)


def trade_rows(result):
    rows = []
    for t in result.trades:
        rows.append({
            "signal_time": t.signal_time.isoformat(),
            "entry_time": t.entry_time.isoformat(),
            "entry_price": t.entry_price,
            "qty": t.qty,
            "stop": t.stop,
            "target": t.target,
            "exit_time": t.exit_time.isoformat() if t.exit_time else None,
            "exit_price": t.exit_price,
            "net_pnl_usd": t.net_pnl_usd,
            "exit_reason": t.exit_reason.value if t.exit_reason else None,
        })
    return rows


def write_trades(path: Path, result):
    rows = trade_rows(result)
    fields = list(rows[0]) if rows else [
        "signal_time", "entry_time", "entry_price", "qty", "stop", "target",
        "exit_time", "exit_price", "net_pnl_usd", "exit_reason",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--analysis-end", required=True)
    ap.add_argument("--out-dir", default="ai2_validation")
    args = ap.parse_args()

    candles = load_csv(args.csv)
    analysis_end = dt(args.analysis_end)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    baseline = AI2Config.creator_15m()
    parity = run_window(candles, baseline, CREATOR_START, CREATOR_END)
    backlog = run_window(candles, baseline, BACKLOG_START, CREATOR_START)
    oos = run_window(candles, baseline, CREATOR_END, analysis_end)
    oos_1x = run_window(candles, replace(baseline, fixed_cash_usd=10_000.0), CREATOR_END, analysis_end)
    oos_2x_cost = run_window(
        candles,
        replace(baseline, commission_pct_per_side=0.2, slippage_ticks=4),
        CREATOR_END,
        analysis_end,
    )

    split_points = [
        (datetime(2024, 3, 1, tzinfo=timezone.utc), datetime(2025, 3, 1, tzinfo=timezone.utc), "2024-03_to_2025-03"),
        (datetime(2025, 3, 1, tzinfo=timezone.utc), datetime(2026, 3, 1, tzinfo=timezone.utc), "2025-03_to_2026-03"),
        (datetime(2026, 3, 1, tzinfo=timezone.utc), analysis_end, "2026-03_to_latest"),
    ]
    splits = {}
    for s, e, name in split_points:
        if s < analysis_end and s < e:
            splits[name] = metric_dict(run_window(candles, baseline, s, min(e, analysis_end)))

    # Predeclared one-factor local neighbors. Diagnostics only: they may never
    # replace the frozen creator settings based on OOS performance.
    neighbor_cfgs = {
        "ma_a_1": replace(baseline, ma_a_length=1),
        "ma_a_3": replace(baseline, ma_a_length=3),
        "ma_b_2": replace(baseline, ma_b_length=2),
        "ma_b_4": replace(baseline, ma_b_length=4),
        "ma_c_325": replace(baseline, ma_c_length=325),
        "ma_c_425": replace(baseline, ma_c_length=425),
        "atr_80": replace(baseline, atr_length=80),
        "atr_120": replace(baseline, atr_length=120),
        "sl_8_5": replace(baseline, atr_stop_multiplier=8.5),
        "sl_12_5": replace(baseline, atr_stop_multiplier=12.5),
        "tp_25": replace(baseline, atr_take_profit_multiplier=25.0),
        "tp_35": replace(baseline, atr_take_profit_multiplier=35.0),
    }
    neighbors = {}
    robust_passes = 0
    for name, cfg in neighbor_cfgs.items():
        m = metric_dict(run_window(candles, cfg, CREATOR_END, analysis_end))
        neighbors[name] = m
        if m["net_profit_pct"] > 0 and m["profit_factor"] > 1:
            robust_passes += 1

    pm = metric_dict(parity)
    parity_checks = {
        "trade_count_delta": pm["trades"] - CREATOR["trades"],
        "net_profit_pct_delta": pm["net_profit_pct"] - CREATOR["net_profit_pct"],
        "profit_factor_delta": pm["profit_factor"] - CREATOR["profit_factor"],
        "win_rate_pct_delta": pm["win_rate_pct"] - CREATOR["win_rate_pct"],
    }
    parity_pass = (
        abs(parity_checks["trade_count_delta"]) <= 5
        and abs(parity_checks["profit_factor_delta"]) <= 0.20
        and abs(parity_checks["win_rate_pct_delta"]) <= 5.0
    )

    om = metric_dict(oos)
    stress = metric_dict(oos_2x_cost)
    bm = metric_dict(backlog)
    all_splits_positive = all(v["net_profit_pct"] > 0 and v["profit_factor"] > 1 for v in splits.values()) if splits else False
    robust_ratio = robust_passes / len(neighbors)

    if not parity_pass:
        classification = "PARITY UNRESOLVED — RESEARCH ONLY"
    elif om["net_profit_pct"] <= 0 or om["profit_factor"] <= 1:
        classification = "REJECT — FRESH OOS FAILED"
    elif stress["net_profit_pct"] <= 0 or stress["profit_factor"] <= 1 or robust_ratio < 0.5:
        classification = "RESEARCH ONLY — OOS POSITIVE BUT FRAGILE"
    elif bm["net_profit_pct"] > 0 and bm["profit_factor"] > 1 and all_splits_positive and robust_ratio >= 0.7:
        classification = "VALIDATED SIGNAL EDGE — SHADOW-PAPER CANDIDATE"
    else:
        classification = "WATCHLIST / SHADOW-PAPER RESEARCH ONLY"

    report = {
        "experiment": "AI2 Simple Triple MA ETHUSDT 15m",
        "status": classification,
        "creator_benchmark": CREATOR,
        "parity": pm,
        "parity_checks": parity_checks,
        "parity_pass": parity_pass,
        "backlog": metric_dict(backlog),
        "oos_full": om,
        "oos_1x_normalized": metric_dict(oos_1x),
        "oos_2x_costs": stress,
        "oos_splits": splits,
        "buy_hold_pct": {
            "creator": buy_hold(candles, CREATOR_START, CREATOR_END),
            "backlog": buy_hold(candles, BACKLOG_START, CREATOR_START),
            "oos": buy_hold(candles, CREATOR_END, analysis_end),
        },
        "robustness": {
            "passing_neighbors": robust_passes,
            "total_neighbors": len(neighbors),
            "pass_ratio": robust_ratio,
            "neighbors": neighbors,
        },
        "frozen_config": asdict(baseline),
        "permanent_rules": [
            "Creator settings are frozen before fresh OOS is inspected.",
            "Neighbor tests are robustness diagnostics and cannot be selected as replacement settings.",
            "No failed OOS period may be retuned away.",
            "Results are research/shadow-paper only; no live orders are placed.",
        ],
    }
    (out / "ai2_validation.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    write_trades(out / "creator_parity_trades.csv", parity)
    write_trades(out / "backlog_trades.csv", backlog)
    write_trades(out / "oos_trades.csv", oos)

    md = []
    md.append("# AI2 — Simple Triple MA ETHUSDT 15m — Full Validation")
    md.append("")
    md.append(f"**Classification:** `{classification}`")
    md.append("")
    md.append("## Creator parity")
    md.append("")
    md.append("| Metric | Creator | Independent | Delta |")
    md.append("|---|---:|---:|---:|")
    for key, label in [("trades", "Trades"), ("net_profit_pct", "Net profit %"), ("profit_factor", "Profit factor"), ("win_rate_pct", "Win rate %")]:
        creator = CREATOR[key]
        independent = pm[key]
        delta = independent - creator
        md.append(f"| {label} | {creator:.4f} | {independent:.4f} | {delta:+.4f} |")
    md.append("")
    md.append(f"Parity gate: **{'PASS' if parity_pass else 'UNRESOLVED'}**")
    md.append("")
    md.append("## Independent windows")
    md.append("")
    md.append("| Window | Trades | Net % | PF | Win % | Closed-trade DD % |")
    md.append("|---|---:|---:|---:|---:|---:|")
    for name, result in [("Backlog 2017→2020", backlog), ("Fresh OOS 2024→latest", oos), ("Fresh OOS 1x normalized", oos_1x), ("Fresh OOS 2x costs", oos_2x_cost)]:
        m = result.metrics
        md.append(f"| {name} | {m.trades} | {m.net_profit_pct:.3f} | {m.profit_factor:.4f} | {m.win_rate_pct:.2f} | {m.max_closed_trade_drawdown_pct:.2f} |")
    md.append("")
    md.append("## Fresh OOS splits")
    md.append("")
    for name, m in splits.items():
        md.append(f"- **{name}:** {m['trades']} trades, {m['net_profit_pct']:.3f}%, PF {m['profit_factor']:.4f}, win {m['win_rate_pct']:.2f}%")
    md.append("")
    md.append("## Local robustness")
    md.append("")
    md.append(f"{robust_passes}/{len(neighbors)} predeclared one-factor neighbors had positive net return and PF > 1 in fresh OOS.")
    md.append("")
    md.append("## Interpretation guardrails")
    md.append("")
    for rule in report["permanent_rules"]:
        md.append(f"- {rule}")
    (out / "AI2_VALIDATION.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
