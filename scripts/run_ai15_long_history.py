from __future__ import annotations

import calendar
import csv
import io
import json
import math
import urllib.request
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from ai_investing_lab.strategies.ai15_triple_ma.config import TripleMAConfig
from ai_investing_lab.strategies.ai15_triple_ma.engine import Candle, TripleMABacktester

UTC = timezone.utc
ET = ZoneInfo("America/New_York")
SOURCE_REPO = "worldtradingchampion-source/btcdata"
SOURCE_COMMIT = "40d6a1052fa6c90be2156f23c6ef91f888f28945"
SOURCE_TEMPLATE = (
    "https://raw.githubusercontent.com/"
    f"{SOURCE_REPO}/{SOURCE_COMMIT}/ES_1min_{{year}}.csv"
)
OUT = Path("ai15_long_history")
WARMUP_YEAR = 2015
START_YEAR = 2016
END_YEAR = 2026


def et_dt(year: int, month: int, day: int) -> datetime:
    return datetime(year, month, day, tzinfo=ET)


def months_ago(dt: datetime, months: int) -> datetime:
    total = dt.year * 12 + (dt.month - 1) - months
    year, month0 = divmod(total, 12)
    month = month0 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


def metric_dict(result) -> dict:
    data = asdict(result.metrics)
    if not math.isfinite(data["profit_factor"]):
        data["profit_factor"] = None
    return data


def parse_row(row: dict[str, str]) -> tuple[datetime, float, float, float, float, float, str]:
    dt = datetime.fromisoformat(row["datetime_et"])
    return (
        dt,
        float(row["open"]),
        float(row["high"]),
        float(row["low"]),
        float(row["close"]),
        float(row["volume"]),
        row.get("symbol", ""),
    )


def download_and_resample() -> tuple[list[Candle], dict]:
    candles: list[Candle] = []
    yearly_rows: dict[str, int] = {}
    yearly_first: dict[str, str] = {}
    yearly_last: dict[str, str] = {}
    invalid_ohlc = 0
    duplicate_timestamps = 0
    symbol_transitions: list[dict] = []
    last_minute_ts: datetime | None = None
    last_symbol: str | None = None

    bucket_key: tuple[int, str] | None = None
    bucket_vals: list[float] | None = None

    def flush_bucket() -> None:
        nonlocal bucket_key, bucket_vals
        if bucket_key is None or bucket_vals is None:
            return
        ts, _symbol = bucket_key
        candles.append(
            Candle(
                datetime.fromtimestamp(ts, tz=UTC),
                bucket_vals[0],
                bucket_vals[1],
                bucket_vals[2],
                bucket_vals[3],
                bucket_vals[4],
            )
        )
        bucket_key = None
        bucket_vals = None

    for year in range(WARMUP_YEAR, END_YEAR + 1):
        url = SOURCE_TEMPLATE.format(year=year)
        request = urllib.request.Request(url, headers={"User-Agent": "gold-ai-strategy-ai15-long-history"})
        count = 0
        first: datetime | None = None
        last: datetime | None = None
        with urllib.request.urlopen(request, timeout=180) as response:
            text = io.TextIOWrapper(response, encoding="utf-8-sig", newline="")
            reader = csv.DictReader(text)
            required = {"datetime_et", "open", "high", "low", "close", "volume", "symbol"}
            if not required.issubset(set(reader.fieldnames or [])):
                raise RuntimeError(f"unexpected columns for {year}: {reader.fieldnames}")

            for raw in reader:
                dt, o, h, l, c, v, symbol = parse_row(raw)
                count += 1
                first = first or dt
                last = dt

                if h < max(o, c, l) or l > min(o, c, h) or min(o, h, l, c) <= 0:
                    invalid_ohlc += 1
                    continue

                if last_minute_ts is not None and dt == last_minute_ts:
                    duplicate_timestamps += 1
                last_minute_ts = dt

                if last_symbol is not None and symbol != last_symbol:
                    symbol_transitions.append(
                        {"time": dt.isoformat(), "from": last_symbol, "to": symbol}
                    )
                last_symbol = symbol

                bucket_ts = int(dt.timestamp())
                bucket_ts -= bucket_ts % 600
                key = (bucket_ts, symbol)
                if bucket_key != key:
                    flush_bucket()
                    bucket_key = key
                    bucket_vals = [o, h, l, c, v]
                else:
                    assert bucket_vals is not None
                    bucket_vals[1] = max(bucket_vals[1], h)
                    bucket_vals[2] = min(bucket_vals[2], l)
                    bucket_vals[3] = c
                    bucket_vals[4] += v

        if count == 0 or first is None or last is None:
            raise RuntimeError(f"no usable source rows for {year}")
        yearly_rows[str(year)] = count
        yearly_first[str(year)] = first.isoformat()
        yearly_last[str(year)] = last.isoformat()

    flush_bucket()
    candles.sort(key=lambda candle: candle.time)
    if not candles:
        raise RuntimeError("long-history source produced no 10-minute bars")

    source_info = {
        "repository": SOURCE_REPO,
        "commit": SOURCE_COMMIT,
        "year_files": [f"ES_1min_{year}.csv" for year in range(WARMUP_YEAR, END_YEAR + 1)],
        "warmup_year": WARMUP_YEAR,
        "scored_start_year": START_YEAR,
        "minute_rows_by_year": yearly_rows,
        "first_minute_by_year": yearly_first,
        "last_minute_by_year": yearly_last,
        "ten_minute_bars": len(candles),
        "first_bar": candles[0].time.isoformat(),
        "last_bar": candles[-1].time.isoformat(),
        "invalid_ohlc_rows_skipped": invalid_ohlc,
        "duplicate_minute_timestamps_seen": duplicate_timestamps,
        "symbol_transition_count": len(symbol_transitions),
        "symbol_transitions": symbol_transitions,
        "continuity_note": (
            "The public source is an already-stitched sequence whose symbol column changes between "
            "quarterly ES contracts. The runner never combines two symbols inside one 10-minute bar. "
            "It does not invent a back-adjustment, so exact TradingView ES1! parity remains provider/roll-method dependent."
        ),
    }
    return candles, source_info


def run_case(candles: list[Candle], cfg: TripleMAConfig, start: datetime, end: datetime | None = None) -> dict:
    result = TripleMABacktester(cfg).run(
        candles,
        trade_start=start,
        trade_end=end,
        close_at_end=False,
    )
    return metric_dict(result)


def neighbour_configs(base: TripleMAConfig) -> dict[str, TripleMAConfig]:
    # Predeclared one-factor neighbours. These are diagnostic only; none may
    # replace the frozen creator baseline after results are observed.
    return {
        "ma_a_30": replace(base, ma_a_length=30),
        "ma_a_40": replace(base, ma_a_length=40),
        "ma_b_135": replace(base, ma_b_length=135),
        "ma_b_165": replace(base, ma_b_length=165),
        "ma_c_90": replace(base, ma_c_length=90),
        "ma_c_110": replace(base, ma_c_length=110),
        "atr_18": replace(base, atr_length=18),
        "atr_22": replace(base, atr_length=22),
        "stop_7_5": replace(base, stop_atr_multiple=7.5),
        "stop_9_5": replace(base, stop_atr_multiple=9.5),
        "target_5_5": replace(base, target_atr_multiple=5.5),
        "target_7_5": replace(base, target_atr_multiple=7.5),
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    candles, source = download_and_resample()

    full_start = et_dt(2016, 1, 1)
    creator_start = et_dt(2020, 5, 1)
    creator_end = et_dt(2024, 5, 1)
    last_time = candles[-1].time.astimezone(ET)
    end_exclusive = last_time.replace(second=0, microsecond=0)

    creator = TripleMAConfig.creator_es_10m()
    narrated = TripleMAConfig.narrated_exit_variant()
    doubled_costs = replace(
        creator,
        commission_usd_per_contract_per_order=4.0,
        slippage_ticks=10,
    )
    mes_5k = TripleMAConfig.one_mes_paper(initial_capital_usd=5_000.0)
    mes_5k_2x = replace(
        mes_5k,
        commission_usd_per_contract_per_order=4.0,
        slippage_ticks=10,
    )

    windows = {
        "full_2016_present": (full_start, None),
        "pre_creator_2016_to_2020_05": (full_start, creator_start),
        "creator_window_2020_05_to_2024_05": (creator_start, creator_end),
        "post_creator_oos_2024_05_present": (creator_end, None),
    }

    baseline_windows = {
        name: run_case(candles, creator, start, end)
        for name, (start, end) in windows.items()
    }
    narrated_windows = {
        name: run_case(candles, narrated, start, end)
        for name, (start, end) in windows.items()
    }

    calendar_years = {}
    for year in range(START_YEAR, END_YEAR + 1):
        start = et_dt(year, 1, 1)
        end = et_dt(year + 1, 1, 1) if year < END_YEAR else None
        calendar_years[str(year)] = run_case(candles, creator, start, end)

    rolling = {}
    for months in (6, 12, 24, 36, 60):
        start = months_ago(last_time, months)
        rolling[f"{months}m"] = run_case(candles, creator, start, None)

    cost_stress = {
        "full_2016_present_2x_costs": run_case(candles, doubled_costs, full_start),
        "creator_window_2x_costs": run_case(candles, doubled_costs, creator_start, creator_end),
        "post_creator_oos_2x_costs": run_case(candles, doubled_costs, creator_end),
    }

    small_account = {
        "one_mes_5k_full_2016_present": run_case(candles, mes_5k, full_start),
        "one_mes_5k_post_creator_oos": run_case(candles, mes_5k, creator_end),
        "one_mes_5k_full_2x_costs": run_case(candles, mes_5k_2x, full_start),
        "one_mes_5k_oos_2x_costs": run_case(candles, mes_5k_2x, creator_end),
    }

    neighbours = {}
    for name, cfg in neighbour_configs(creator).items():
        neighbours[name] = {
            "full": run_case(candles, cfg, full_start),
            "post_creator_oos": run_case(candles, cfg, creator_end),
        }

    def viable(m: dict) -> bool:
        pf = m["profit_factor"]
        return m["net_profit_pct"] > 0 and pf is not None and pf > 1.0

    robustness_summary = {
        "neighbors": len(neighbours),
        "full_positive_and_pf_gt_1": sum(viable(v["full"]) for v in neighbours.values()),
        "oos_positive_and_pf_gt_1": sum(viable(v["post_creator_oos"]) for v in neighbours.values()),
    }

    report = {
        "strategy": "AI15 Simple Triple MA",
        "status": "2016-PRESENT INDEPENDENT LONG-HISTORY RESEARCH",
        "generated_at_utc": datetime.now(tz=UTC).isoformat(),
        "source": source,
        "frozen_creator_target": {
            "window": "2020-05-01 through 2024-05-01",
            "trades": 322,
            "net_profit_pct": 566.98,
            "profit_factor": 1.403,
            "win_rate_pct": 60.87,
            "max_drawdown_pct": 25.39,
        },
        "baseline_source_semantics": baseline_windows,
        "narrated_exit_freeze_semantics": narrated_windows,
        "calendar_years": calendar_years,
        "rolling_windows_ending_at_source_last_bar": rolling,
        "cost_stress": cost_stress,
        "small_account_paper_sensitivity": small_account,
        "local_neighbour_robustness": {
            "summary": robustness_summary,
            "results": neighbours,
        },
        "research_rules": [
            "The creator ES preset is frozen before this run; no result-driven retuning is allowed.",
            "2015 data is warmup only. The standardized scored history begins 2016-01-01 America/New_York.",
            "The public yearly source is pinned to an immutable Git commit.",
            "Creator sizing is used only for parity/reconstruction. One-MES ~$5k cases are separate paper feasibility diagnostics.",
            "Neighbour tests are predeclared one-factor diagnostics and cannot replace the frozen baseline.",
            "No live order routing is performed.",
        ],
    }
    (OUT / "ai15_long_history.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    def fmt(m: dict) -> str:
        pf = "n/a" if m["profit_factor"] is None else f"{m['profit_factor']:.3f}"
        return (
            f"{m['trades']} trades | {m['net_profit_pct']:+.2f}% | PF {pf} | "
            f"win {m['win_rate_pct']:.2f}% | DD {m['max_closed_trade_drawdown_pct']:.2f}%"
        )

    lines = [
        "# AI15 — 2016-present long-history validation",
        "",
        f"Pinned source: `{SOURCE_REPO}@{SOURCE_COMMIT}`",
        f"Source coverage used: {source['first_bar']} → {source['last_bar']}",
        "2015 is warmup only; scoring begins 2016-01-01 America/New_York.",
        "",
        "## Frozen baseline windows",
        "",
    ]
    for name, metrics in baseline_windows.items():
        lines.append(f"- **{name}** — {fmt(metrics)}")

    lines += ["", "## Calendar years", "", "| Year | Trades | Net % | PF | Win % | DD % |", "|---:|---:|---:|---:|---:|---:|"]
    for year, m in calendar_years.items():
        pf = "n/a" if m["profit_factor"] is None else f"{m['profit_factor']:.3f}"
        lines.append(
            f"| {year} | {m['trades']} | {m['net_profit_pct']:+.2f} | {pf} | "
            f"{m['win_rate_pct']:.2f} | {m['max_closed_trade_drawdown_pct']:.2f} |"
        )

    lines += ["", "## Rolling windows", "", "| Window | Trades | Net % | PF | Win % | DD % |", "|---|---:|---:|---:|---:|---:|"]
    for name, m in rolling.items():
        pf = "n/a" if m["profit_factor"] is None else f"{m['profit_factor']:.3f}"
        lines.append(
            f"| {name} | {m['trades']} | {m['net_profit_pct']:+.2f} | {pf} | "
            f"{m['win_rate_pct']:.2f} | {m['max_closed_trade_drawdown_pct']:.2f} |"
        )

    lines += [
        "",
        "## Cost stress",
        "",
        f"- Full history 2x costs — {fmt(cost_stress['full_2016_present_2x_costs'])}",
        f"- Creator window 2x costs — {fmt(cost_stress['creator_window_2x_costs'])}",
        f"- Post-creator OOS 2x costs — {fmt(cost_stress['post_creator_oos_2x_costs'])}",
        "",
        "## ~$5k one-MES paper sensitivity",
        "",
        f"- Full history — {fmt(small_account['one_mes_5k_full_2016_present'])}",
        f"- Post-creator OOS — {fmt(small_account['one_mes_5k_post_creator_oos'])}",
        f"- Full history 2x costs — {fmt(small_account['one_mes_5k_full_2x_costs'])}",
        f"- OOS 2x costs — {fmt(small_account['one_mes_5k_oos_2x_costs'])}",
        "",
        "## Local robustness",
        "",
        f"- Full history profitable + PF>1: **{robustness_summary['full_positive_and_pf_gt_1']}/{robustness_summary['neighbors']}**",
        f"- Post-creator OOS profitable + PF>1: **{robustness_summary['oos_positive_and_pf_gt_1']}/{robustness_summary['neighbors']}**",
        "",
        "Exact TradingView ES1! parity remains conditional on continuous-contract provider/roll methodology; this run is an independent stitched-contract long-history test.",
    ]
    (OUT / "AI15_LONG_HISTORY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
