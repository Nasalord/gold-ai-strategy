from __future__ import annotations

import argparse
import csv
import json
import time
import urllib.error
import urllib.request
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path

from ai_investing_lab.strategies.triple_macd_nq.config import TripleMACDNQConfig
from ai_investing_lab.strategies.triple_macd_nq.engine import Candle, TripleMACDNQBacktester

BASE = "https://raw.githubusercontent.com/MeNameek/AnooReplay/main/public/data/NQ"
UTC = timezone.utc

CREATOR_TARGET = {
    "period_start": "2025-01-01T00:00:00Z",
    "period_end": "2025-06-01T00:00:00Z",
    "trades": 27,
    "net_profit_pct": 19.0,
    "profit_factor": 1.1,
    "max_drawdown_pct": 51.0,
}


def fetch_json(url: str, attempts: int = 4):
    req = urllib.request.Request(url, headers={"User-Agent": "ai-investing-lab/exp6-parity"})
    last: Exception | None = None
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.load(resp)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last = exc
            if attempt + 1 < attempts:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"failed to fetch {url}: {last}")


def load_minutes(start_date: str, end_date: str) -> tuple[list[list[float]], list[str]]:
    dates = fetch_json(f"{BASE}/dates.json")
    selected = [d for d in dates if start_date <= d < end_date]
    rows: list[list[float]] = []
    for idx, day in enumerate(selected, 1):
        day_rows = fetch_json(f"{BASE}/{day}.json")
        rows.extend(day_rows)
        if idx % 25 == 0:
            print(f"downloaded {idx}/{len(selected)} daily files")
    rows.sort(key=lambda x: x[0])
    return rows, selected


def resample_10m(rows: list[list[float]]) -> list[Candle]:
    buckets: dict[int, list[float]] = {}
    for ts, o, h, l, c, v in rows:
        ts = int(ts)
        bucket = ts - (ts % 600)
        if bucket not in buckets:
            buckets[bucket] = [float(o), float(h), float(l), float(c), float(v)]
        else:
            b = buckets[bucket]
            b[1] = max(b[1], float(h))
            b[2] = min(b[2], float(l))
            b[3] = float(c)
            b[4] += float(v)
    return [
        Candle(
            time=datetime.fromtimestamp(ts, tz=UTC),
            open=vals[0],
            high=vals[1],
            low=vals[2],
            close=vals[3],
            volume=vals[4],
        )
        for ts, vals in sorted(buckets.items())
    ]


def metric_dict(result):
    m = result.metrics
    return {
        "trades": m.trades,
        "wins": m.wins,
        "losses": m.losses,
        "win_rate_pct": m.win_rate_pct,
        "net_profit_usd": m.net_profit_usd,
        "net_profit_pct": m.net_profit_pct,
        "profit_factor": m.profit_factor,
        "max_closed_trade_drawdown_pct": m.max_closed_trade_drawdown_pct,
    }


def write_trades(path: Path, result) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "side", "signal_time", "entry_time", "entry_price", "contracts",
            "stop", "target", "exit_time", "exit_price", "net_pnl_usd", "exit_reason",
        ])
        for t in result.trades:
            w.writerow([
                t.side.value,
                t.signal_time.isoformat(),
                t.entry_time.isoformat(),
                t.entry_price,
                t.contracts,
                t.stop,
                t.target,
                t.exit_time.isoformat() if t.exit_time else "",
                t.exit_price if t.exit_price is not None else "",
                t.net_pnl_usd,
                t.exit_reason.value if t.exit_reason else "",
            ])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--warmup-start", default="2024-12-15")
    ap.add_argument("--trade-start", default="2025-01-01")
    ap.add_argument("--trade-end", default="2025-06-01")
    ap.add_argument("--out-dir", default="exp6_public_parity")
    args = ap.parse_args()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Pull a few days beyond the trade window only for source diagnostics; the
    # backtester itself is hard-bounded by trade_end below.
    minute_rows, source_dates = load_minutes(args.warmup_start, args.trade_end)
    candles = resample_10m(minute_rows)
    if not candles:
        raise SystemExit("no candles downloaded")

    trade_start = datetime.fromisoformat(args.trade_start).replace(tzinfo=UTC)
    trade_end = datetime.fromisoformat(args.trade_end).replace(tzinfo=UTC)

    creator_cfg = TripleMACDNQConfig.creator_nq_10m()
    creator = TripleMACDNQBacktester(creator_cfg).run(
        candles,
        trade_start=trade_start,
        trade_end=trade_end,
        close_at_end=False,
    )

    half_cfg = replace(creator_cfg, order_cash_usd=4_000_000.0)
    half = TripleMACDNQBacktester(half_cfg).run(
        candles,
        trade_start=trade_start,
        trade_end=trade_end,
        close_at_end=False,
    )

    creator_metrics = metric_dict(creator)
    half_metrics = metric_dict(half)
    comparison = {
        "trade_count_delta": creator_metrics["trades"] - CREATOR_TARGET["trades"],
        "net_profit_pct_delta": creator_metrics["net_profit_pct"] - CREATOR_TARGET["net_profit_pct"],
        "profit_factor_delta": creator_metrics["profit_factor"] - CREATOR_TARGET["profit_factor"],
        # Closed-trade DD is intentionally not treated as exact TV parity because
        # TradingView's headline DD can include intrabar equity excursions.
        "creator_trade_count_match": creator_metrics["trades"] == CREATOR_TARGET["trades"],
        "creator_trade_count_within_2": abs(creator_metrics["trades"] - CREATOR_TARGET["trades"]) <= 2,
    }

    report = {
        "experiment": "EXP6 Triple MACD NQ 10m",
        "status": "PARITY DIAGNOSTIC — PUBLIC CONTINUOUS DATASET",
        "source": {
            "repository": "MeNameek/AnooReplay",
            "base_url": BASE,
            "warmup_start": args.warmup_start,
            "trade_start": args.trade_start,
            "trade_end": args.trade_end,
            "daily_files": len(source_dates),
            "minute_rows": len(minute_rows),
            "ten_minute_bars": len(candles),
            "first_bar": candles[0].time.isoformat(),
            "first_close": candles[0].close,
            "last_bar": candles[-1].time.isoformat(),
            "last_close": candles[-1].close,
        },
        "creator_target": CREATOR_TARGET,
        "creator_8_5m": creator_metrics,
        "creator_4m_control": half_metrics,
        "comparison": comparison,
        "frozen_config": asdict(creator_cfg),
        "notes": [
            "This is a paper-research parity diagnostic only.",
            "The public dataset is independent of TradingView and may use a different continuous-contract adjustment/roll convention.",
            "Trade count and PF are the primary structural parity fingerprints; TradingView max drawdown is not expected to match closed-trade DD exactly.",
            "No parameters are optimized or selected from these results.",
        ],
    }

    (out / "exp6_public_parity.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_trades(out / "exp6_trades_8_5m.csv", creator)
    write_trades(out / "exp6_trades_4m.csv", half)

    md = [
        "# Experiment 6 — Triple MACD NQ 10m public-data parity",
        "",
        f"Status: **{report['status']}**",
        "",
        "## Creator Jan 1–Jun 1 2025 target",
        "",
        f"- Trades: {CREATOR_TARGET['trades']}",
        f"- Net profit: {CREATOR_TARGET['net_profit_pct']:.1f}%",
        f"- Profit factor: {CREATOR_TARGET['profit_factor']:.1f}",
        f"- Reported max DD: {CREATOR_TARGET['max_drawdown_pct']:.1f}%",
        "",
        "## Independent public-data reconstruction — $8.5M creator sizing",
        "",
        f"- Trades: {creator_metrics['trades']}",
        f"- Win rate: {creator_metrics['win_rate_pct']:.2f}%",
        f"- Net profit: {creator_metrics['net_profit_pct']:.2f}%",
        f"- Profit factor: {creator_metrics['profit_factor']:.4f}",
        f"- Closed-trade DD: {creator_metrics['max_closed_trade_drawdown_pct']:.2f}%",
        "",
        "## $4M sizing control",
        "",
        f"- Trades: {half_metrics['trades']}",
        f"- Net profit: {half_metrics['net_profit_pct']:.2f}%",
        f"- Profit factor: {half_metrics['profit_factor']:.4f}",
        f"- Closed-trade DD: {half_metrics['max_closed_trade_drawdown_pct']:.2f}%",
        "",
        "## Structural comparison",
        "",
        f"- Trade-count delta: {comparison['trade_count_delta']:+d}",
        f"- Net-profit delta: {comparison['net_profit_pct_delta']:+.2f} pp",
        f"- PF delta: {comparison['profit_factor_delta']:+.4f}",
        f"- Trade count within ±2 of creator: **{comparison['creator_trade_count_within_2']}**",
        "",
        "This diagnostic does **not** retune the strategy. A mismatch is evidence about feed/continuous-contract semantics, not a reason to alter parameters.",
    ]
    (out / "EXP6_PUBLIC_PARITY.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
