from __future__ import annotations

import csv
import io
import json
import math
import urllib.request
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path

from ai_investing_lab.strategies.ai15_triple_ma.config import TripleMAConfig
from ai_investing_lab.strategies.ai15_triple_ma.engine import Candle, TripleMABacktester

UTC = timezone.utc
URL = "https://raw.githubusercontent.com/getdata-finance/es-1m-ohlcv-stocks-historical-data/main/ES_1m.csv"
OUT = Path("ai15_public_2026")


def parse_dt(value: str) -> datetime:
    dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)


def download_rows() -> list[tuple[datetime, float, float, float, float, float]]:
    req = urllib.request.Request(URL, headers={"User-Agent": "gold-ai-strategy-ai15"})
    with urllib.request.urlopen(req, timeout=90) as response:
        text = response.read().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    rows = []
    for row in reader:
        try:
            rows.append(
                (
                    parse_dt(row["datetime"]),
                    float(row["open"]),
                    float(row["high"]),
                    float(row["low"]),
                    float(row["close"]),
                    float(row["volume"]),
                )
            )
        except (KeyError, TypeError, ValueError):
            continue
    rows.sort(key=lambda x: x[0])
    return rows


def resample_10m(rows: list[tuple[datetime, float, float, float, float, float]]) -> list[Candle]:
    buckets: dict[int, list[float]] = {}
    for t, o, h, l, c, v in rows:
        ts = int(t.timestamp())
        bucket = ts - ts % 600
        if bucket not in buckets:
            buckets[bucket] = [o, h, l, c, v]
        else:
            b = buckets[bucket]
            b[1] = max(b[1], h)
            b[2] = min(b[2], l)
            b[3] = c
            b[4] += v
    return [
        Candle(datetime.fromtimestamp(ts, tz=UTC), vals[0], vals[1], vals[2], vals[3], vals[4])
        for ts, vals in sorted(buckets.items())
    ]


def metric_dict(result) -> dict:
    d = asdict(result.metrics)
    if not math.isfinite(d["profit_factor"]):
        d["profit_factor"] = None
    return d


def write_trades(path: Path, result) -> None:
    fields = [
        "signal_time",
        "entry_time",
        "entry_price",
        "contracts",
        "stop",
        "target",
        "entry_commission",
        "exit_time",
        "exit_price",
        "exit_commission",
        "net_pnl_usd",
        "exit_reason",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for trade in result.trades:
            writer.writerow(
                {
                    "signal_time": trade.signal_time.isoformat(),
                    "entry_time": trade.entry_time.isoformat(),
                    "entry_price": trade.entry_price,
                    "contracts": trade.contracts,
                    "stop": trade.stop,
                    "target": trade.target,
                    "entry_commission": trade.entry_commission,
                    "exit_time": trade.exit_time.isoformat() if trade.exit_time else "",
                    "exit_price": trade.exit_price if trade.exit_price is not None else "",
                    "exit_commission": trade.exit_commission,
                    "net_pnl_usd": trade.net_pnl_usd,
                    "exit_reason": trade.exit_reason.value if trade.exit_reason else "",
                }
            )


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = download_rows()
    if not rows:
        raise RuntimeError("public ES sample returned no usable rows")
    candles = resample_10m(rows)

    # April is warmup only.  The public evaluation begins May 1 so all three
    # creator moving averages and ATR have ample history before scoring starts.
    trade_start = datetime(2026, 5, 1, tzinfo=UTC)

    creator = TripleMAConfig.creator_es_10m()
    cases = {
        "creator_es_10m_source_code": creator,
        "creator_es_10m_narrated_exit_freeze": TripleMAConfig.narrated_exit_variant(),
        "creator_es_10m_2x_costs": replace(
            creator,
            commission_usd_per_contract_per_order=4.0,
            slippage_ticks=10,
        ),
        "one_mes_5k_paper": TripleMAConfig.one_mes_paper(initial_capital_usd=5_000.0),
        "one_mes_5k_paper_2x_costs": replace(
            TripleMAConfig.one_mes_paper(initial_capital_usd=5_000.0),
            commission_usd_per_contract_per_order=4.0,
            slippage_ticks=10,
        ),
    }

    metrics = {}
    for name, cfg in cases.items():
        result = TripleMABacktester(cfg).run(candles, trade_start=trade_start, close_at_end=False)
        metrics[name] = metric_dict(result)
        write_trades(OUT / f"trades_{name}.csv", result)
        m = metrics[name]
        print(
            f"{name:40s} trades={m['trades']:3d} net={m['net_profit_pct']:9.3f}% "
            f"PF={m['profit_factor']} win={m['win_rate_pct']:.2f}% "
            f"closedDD={m['max_closed_trade_drawdown_pct']:.2f}%"
        )

    report = {
        "strategy": "AI15 Simple Triple MA",
        "market": "ES price series / 10-minute",
        "status": "INDEPENDENT PUBLIC 2026 SAMPLE — RESEARCH ONLY",
        "source": {
            "url": URL,
            "minute_rows": len(rows),
            "ten_minute_bars": len(candles),
            "first_minute": rows[0][0].isoformat(),
            "last_minute": rows[-1][0].isoformat(),
        },
        "evaluation": {
            "warmup_start": rows[0][0].isoformat(),
            "trade_start": trade_start.isoformat(),
            "trade_end": rows[-1][0].isoformat(),
        },
        "creator_target": {
            "optimization_window": "2020-05-01 through 2024-05-01",
            "trades": 322,
            "net_profit_pct": 566.98,
            "profit_factor": 1.403,
            "win_rate_pct": 60.87,
            "max_drawdown_pct": 25.39,
            "note": "Creator/spreadsheet target only; not an independent parity result.",
        },
        "metrics": metrics,
        "notes": [
            "The ES video optimized parameters are TMA(35), EMA(150), SMA(100), low source, ATR(20), SL 8.5 ATR and TP 6.5 ATR.",
            "The downloadable Pine file contains different generic input defaults; those defaults are preserved separately and are not silently used for ES parity.",
            "The Pine source and video narration disagree about whether a later valid signal can update stop/target while a position is already open. Both interpretations are reported.",
            "The one-MES cases are small-account paper sensitivity tests only; they are not broker-margin or live-trading recommendations.",
            "Creator-window parity and the 5+ year test still require an independently sourced continuous historical ES dataset with explicit roll methodology.",
        ],
    }
    (OUT / "ai15_public_2026.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = [
        "# AI15 public 2026 ES sample",
        "",
        "April 2026 is warmup only; scoring starts 2026-05-01.",
        "",
        "| Case | Trades | Win % | Net % | PF | Closed DD % |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name, m in metrics.items():
        pf = "n/a" if m["profit_factor"] is None else f"{m['profit_factor']:.3f}"
        lines.append(
            f"| {name} | {m['trades']} | {m['win_rate_pct']:.2f} | "
            f"{m['net_profit_pct']:.3f} | {pf} | {m['max_closed_trade_drawdown_pct']:.2f} |"
        )
    (OUT / "AI15_PUBLIC_2026.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
