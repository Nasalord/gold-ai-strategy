from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ai_investing_lab.strategies.triple_macd_nq.config import TripleMACDNQConfig
from ai_investing_lab.strategies.triple_macd_nq.engine import TripleMACDNQBacktester
from scripts.run_exp6_2026_sample import download_rows, resample
from scripts.run_exp6_public_nq_parity import metric_dict

UTC = timezone.utc
MONITOR_START = datetime(2026, 5, 1, tzinfo=UTC)
MIN_TRADES_FOR_HEALTH_CLASSIFICATION = 20


def classify(metrics: dict) -> tuple[str, str]:
    trades = int(metrics["trades"])
    net = float(metrics["net_profit_pct"])
    pf = float(metrics["profit_factor"])
    if trades < MIN_TRADES_FOR_HEALTH_CLASSIFICATION:
        return "observing_insufficient_sample", f"OBSERVING — {trades}/{MIN_TRADES_FOR_HEALTH_CLASSIFICATION} minimum trades"
    if net < 0 and pf < 0.8:
        return "structural_concern", "STRUCTURAL CONCERN — negative return and PF < 0.8"
    if net <= 0 or pf <= 1.0:
        return "weak", "WEAK — return or PF has fallen below the frozen health gate"
    return "healthy", "HEALTHY — positive return and PF > 1"


def main() -> int:
    out = Path("exp6_shadow_health")
    out.mkdir(parents=True, exist_ok=True)

    rows, headers = download_rows()
    candles = resample(rows)
    if not candles:
        raise SystemExit("no NQ candles available")

    # The public source begins Apr 1, 2026. April remains warmup only.
    last_bar = candles[-1].time
    end = last_bar + timedelta(minutes=10)

    normalized = TripleMACDNQConfig.creator_nq_10m(order_cash_usd=1_000_000.0)
    stressed = replace(
        normalized,
        commission_usd_per_contract_per_order=normalized.commission_usd_per_contract_per_order * 2,
        slippage_ticks=normalized.slippage_ticks * 2,
    )

    result = TripleMACDNQBacktester(normalized).run(
        candles, trade_start=MONITOR_START, trade_end=end, close_at_end=False
    )
    stress_result = TripleMACDNQBacktester(stressed).run(
        candles, trade_start=MONITOR_START, trade_end=end, close_at_end=False
    )
    metrics = metric_dict(result)
    stress_metrics = metric_dict(stress_result)
    classification, headline = classify(metrics)

    closed = [t for t in result.trades if t.closed]
    last_exit = max((t.exit_time for t in closed if t.exit_time), default=None)
    last_entry = max((t.entry_time for t in result.trades), default=None)

    report = {
        "experiment": "EXP6 Triple MACD NQ 10m",
        "mode": "SHADOW-PAPER RESEARCH ONLY",
        "classification": classification,
        "headline": headline,
        "frozen_since": "2026-09-15",
        "monitor_start": MONITOR_START.isoformat(),
        "minimum_trades_for_health_classification": MIN_TRADES_FOR_HEALTH_CLASSIFICATION,
        "source": {
            "repository": "getdata-finance/nq-1m-ohlcv-stocks-historical-data",
            "headers": headers,
            "minute_rows": len(rows),
            "ten_minute_bars": len(candles),
            "first_bar": candles[0].time.isoformat(),
            "latest_bar": last_bar.isoformat(),
        },
        "normalized_1m": metrics,
        "normalized_1m_2x_costs": stress_metrics,
        "last_entry": last_entry.isoformat() if last_entry else None,
        "last_exit": last_exit.isoformat() if last_exit else None,
        "frozen_health_rules": {
            "sample_gate": f"remain observing until >= {MIN_TRADES_FOR_HEALTH_CLASSIFICATION} closed trades",
            "healthy": "net > 0 and PF > 1 once sample gate is met",
            "weak": "net <= 0 or PF <= 1 once sample gate is met",
            "structural_concern": "net < 0 and PF < 0.8 once sample gate is met",
        },
        "permanent_caveats": [
            "Exact TradingView creator parity remains unresolved (24 vs 27 trades in Jan-Jun 2025).",
            "Fresh Jun-Oct 2025 OOS failed and 0/22 local neighbours achieved positive net with PF > 1.",
            "May-Sep 2026 recovery was encouraging but began with only six closed baseline trades.",
            "No future result may be used to retune the frozen strategy parameters.",
            "This monitor does not place orders or create trade instructions.",
        ],
    }

    (out / "exp6_health.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    md = [
        "# Experiment 6 — Triple MACD NQ shadow health",
        "",
        f"**{headline}**",
        "",
        "Mode: **shadow-paper research only**",
        "",
        f"Latest source bar: `{last_bar.isoformat()}`",
        f"Closed trades since May 1, 2026: **{metrics['trades']}**",
        f"Normalized $1M net: **{metrics['net_profit_pct']:.3f}%**",
        f"Profit factor: **{metrics['profit_factor']:.3f}**",
        f"Win rate: **{metrics['win_rate_pct']:.2f}%**",
        f"Closed-trade DD: **{metrics['max_closed_trade_drawdown_pct']:.2f}%**",
        "",
        "## 2x execution-cost stress",
        f"- Net: **{stress_metrics['net_profit_pct']:.3f}%**",
        f"- PF: **{stress_metrics['profit_factor']:.3f}**",
        "",
        "## Frozen health rule",
        f"No health verdict is issued until at least **{MIN_TRADES_FOR_HEALTH_CLASSIFICATION}** closed trades have accumulated. After that: positive net + PF > 1 is healthy; net <= 0 or PF <= 1 is weak; negative net + PF < 0.8 is structural concern.",
        "",
        "## Permanent caveats",
        "- Exact creator parity is unresolved.",
        "- Fresh Jun-Oct 2025 OOS failed broadly (0/22 neighbours survived).",
        "- The 2026 recovery began from a small trade sample.",
        "- Parameters remain frozen; no retuning is allowed.",
    ]
    (out / "EXP6_HEALTH.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
