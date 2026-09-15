from __future__ import annotations

import argparse
import json
from pathlib import Path


def fmt(value, digits=2):
    if value is None:
        return "n/a"
    return f"{float(value):.{digits}f}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Render AI8 health JSON as concise Markdown")
    parser.add_argument("input_json", type=Path)
    parser.add_argument("--markdown", type=Path, required=True)
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()

    payload = json.loads(args.input_json.read_text(encoding="utf-8"))
    current = payload["current_regime"]
    thresholds = payload["reference_thresholds"]
    pct = payload["current_percentiles_vs_reference"]
    data = payload["data"]
    sizing = payload["monitor_sizing"]

    classification = current["classification"]
    latest6 = current["latest_6m"]
    latest12 = current["latest_12m"]
    latest24 = current["latest_24m"]
    dd = current["current_unrecovered_drawdown"]
    streak = current["current_ending_losing_streak"]

    if classification == "historically_normal":
        headline = "NORMAL"
    elif classification == "weak_but_within_historical_tolerance":
        headline = "WEAK — WITHIN HISTORICAL TOLERANCE"
    elif classification == "high_risk_dormant":
        headline = "HIGH RISK / DORMANT"
    else:
        headline = "STRUCTURAL CONCERN"

    lines = [
        "# AI8 Health Monitor",
        "",
        f"**Status:** `{headline}`",
        "",
        f"Evaluation end (exclusive): **{data['analysis_end_exclusive'][:10]}**  ",
        f"Frozen reference history ends: **{data['reference_history_end'][:10]}**  ",
        f"Latest data bar: **{data['last_bar'][:19]} UTC**",
        "",
        "| Measure | Current | Historical context |",
        "|---|---:|---:|",
        f"| Trailing 6m | {fmt(latest6['net_profit_pct'])}% / PF {fmt(latest6['profit_factor'],3)} | return percentile {fmt(pct['latest_6m_return_percentile'],1)}% |",
        f"| Trailing 12m | {fmt(latest12['net_profit_pct'])}% / PF {fmt(latest12['profit_factor'],3)} | return percentile {fmt(pct['latest_12m_return_percentile'],1)}% |",
        f"| Trailing 24m | {fmt(latest24['net_profit_pct'])}% / PF {fmt(latest24['profit_factor'],3)} | return percentile {fmt(pct['latest_24m_return_percentile'],1)}% |",
        f"| Current drawdown | {fmt(dd['max_drawdown_pct'])}% | ref p95 {fmt(thresholds['drawdown_depth_p95_pct'])}% |",
        f"| Days underwater | {fmt(dd['duration_days'],1)} | ref p95 {fmt(thresholds['drawdown_duration_p95_days'],1)} |",
        f"| Ending losing streak | {int(streak['length'])} trades | ref p95 {fmt(thresholds['losing_streak_length_p95'],1)}, max {thresholds['max_losing_streak']} |",
        "",
        "## Threshold signals",
        "",
    ]

    for key, value in current["signals"].items():
        lines.append(f"- `{key}`: **{'YES' if value else 'no'}**")

    if data.get("data_stale"):
        lines += [
            "",
            "## Data warning",
            "",
            f"The latest downloaded Binance bar is {fmt(data['data_age_hours_at_analysis_end'],1)} hours behind the evaluation boundary. Treat this status as provisional until fresh data is available.",
        ]

    lines += [
        "",
        "## Monitor sizing",
        "",
        f"The health monitor preserves AI8's signals and pyramiding but normalizes each entry to **${float(sizing['fixed_cash_per_leg_usd']):,.2f}**. Seven simultaneous legs therefore represent about **${float(sizing['max_requested_gross_if_full_stack_usd']):,.0f}** requested gross exposure on the $100,000 research account.",
        "",
        "This is a research normalization only. The creator's original $80,000-per-leg configuration remains much more aggressive and is not used to judge drawdown health here.",
        "",
        "## Interpretation",
        "",
        "This monitor does **not** optimize or alter AI8's indicator parameters. Historical health thresholds are permanently frozen from data ending September 1, 2025, before the weak 12-month regime identified during validation.",
        "",
        "Research/paper-simulation only; no broker or exchange execution is connected.",
    ]

    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.write_text("\n".join(lines) + "\n", encoding="utf-8")

    if args.github_output is not None:
        args.github_output.write_text(
            f"classification={classification}\nheadline={headline}\n",
            encoding="utf-8",
        )

    print(classification)


if __name__ == "__main__":
    main()
