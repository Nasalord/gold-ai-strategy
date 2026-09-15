from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import pandas as pd


def parse_date(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d")


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close"])
    work = df.copy()
    if isinstance(work.index, pd.DatetimeIndex):
        idx = pd.to_datetime(work.index)
        idx = idx.tz_localize("UTC") if idx.tz is None else idx.tz_convert("UTC")
        work.index = idx
    else:
        lower = {str(c).lower(): c for c in work.columns}
        for key in ("timestamp", "datetime", "date", "time"):
            if key in lower:
                work.index = pd.to_datetime(work.pop(lower[key]), utc=True)
                break
        else:
            raise ValueError("could not locate datetime index/column")
    lower = {str(c).lower(): c for c in work.columns}
    cols = [lower[k] for k in ("open", "high", "low", "close")]
    out = work[cols].copy()
    out.columns = ["open", "high", "low", "close"]
    out = out.astype(float).sort_index()
    out = out[~out.index.duplicated(keep="last")]
    return out


def fetch_h1(start: datetime, end: datetime, side: str) -> pd.DataFrame:
    import dukascopy_python
    from dukascopy_python.instruments import INSTRUMENT_FX_MAJORS_GBP_USD

    offer = dukascopy_python.OFFER_SIDE_BID if side == "bid" else dukascopy_python.OFFER_SIDE_ASK
    raw = dukascopy_python.fetch(
        instrument=INSTRUMENT_FX_MAJORS_GBP_USD,
        interval=dukascopy_python.INTERVAL_HOUR_1,
        offer_side=offer,
        start=start,
        end=end,
    )
    return normalize(raw)


def make_mid(bid: pd.DataFrame, ask: pd.DataFrame) -> pd.DataFrame:
    joined = bid.join(ask, how="inner", lsuffix="_bid", rsuffix="_ask")
    out = pd.DataFrame(index=joined.index)
    for col in ("open", "high", "low", "close"):
        out[col] = (joined[f"{col}_bid"] + joined[f"{col}_ask"]) / 2.0
    return out


def aggregate_4h(frame: pd.DataFrame, offset_hours: int) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close"])
    shifted = frame.copy()
    buckets = (shifted.index - pd.Timedelta(hours=offset_hours)).floor("4h") + pd.Timedelta(hours=offset_hours)
    grouped = shifted.groupby(buckets).agg({"open": "first", "high": "max", "low": "min", "close": "last"})
    grouped = grouped.dropna().sort_index()
    out = grouped.copy()
    out.insert(0, "timestamp", out.index.strftime("%Y-%m-%dT%H:%M:%SZ"))
    return out.reset_index(drop=True)


def main() -> None:
    ap = argparse.ArgumentParser(description="Fetch Dukascopy GBPUSD H1 and aggregate to 4H alignment variants")
    ap.add_argument("--start", required=True, type=parse_date)
    ap.add_argument("--end", required=True, type=parse_date)
    ap.add_argument("--output-dir", required=True, type=Path)
    args = ap.parse_args()
    if args.start >= args.end:
        raise ValueError("start must be before end")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    bid = fetch_h1(args.start, args.end, "bid")
    ask = fetch_h1(args.start, args.end, "ask")
    mid = make_mid(bid, ask)
    bases = {"bid": bid, "ask": ask, "mid": mid}

    summary: dict[str, object] = {
        "provider": "Dukascopy via dukascopy-python",
        "symbol": "GBPUSD",
        "source_timeframe": "1h",
        "target_timeframe": "4h",
        "start_inclusive": args.start.date().isoformat(),
        "end_exclusive_intended": args.end.date().isoformat(),
        "variants": {},
    }
    for side, frame in bases.items():
        for offset in range(4):
            out = aggregate_4h(frame, offset)
            name = f"gbpusd_{side}_4h_offset{offset}.csv"
            out.to_csv(args.output_dir / name, index=False)
            summary["variants"][f"{side}_offset{offset}"] = {
                "rows": len(out),
                "first": out.iloc[0]["timestamp"] if len(out) else None,
                "last": out.iloc[-1]["timestamp"] if len(out) else None,
            }
    (args.output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
