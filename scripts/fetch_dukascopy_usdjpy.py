from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


def _parse_date(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d")


def _normalize_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close"])

    work = df.copy()
    if not isinstance(work.index, pd.DatetimeIndex):
        for candidate in ("timestamp", "datetime", "date", "time"):
            if candidate in {str(c).lower() for c in work.columns}:
                real = next(c for c in work.columns if str(c).lower() == candidate)
                work.index = pd.to_datetime(work.pop(real), utc=True)
                break
        else:
            raise ValueError("could not locate datetime index/column in dukascopy frame")
    else:
        idx = pd.to_datetime(work.index)
        if idx.tz is None:
            idx = idx.tz_localize("UTC")
        else:
            idx = idx.tz_convert("UTC")
        work.index = idx

    lower = {str(c).lower(): c for c in work.columns}
    cols = {}
    for wanted in ("open", "high", "low", "close"):
        if wanted not in lower:
            raise ValueError(f"missing {wanted} column; available={list(work.columns)!r}")
        cols[wanted] = lower[wanted]

    out = work[[cols["open"], cols["high"], cols["low"], cols["close"]]].copy()
    out.columns = ["open", "high", "low", "close"]
    out = out.astype(float)
    out = out[~out.index.duplicated(keep="last")].sort_index()
    out.insert(0, "timestamp", out.index.strftime("%Y-%m-%dT%H:%M:%SZ"))
    return out.reset_index(drop=True)


def fetch_side(start: datetime, end: datetime, side: str) -> pd.DataFrame:
    import dukascopy_python
    from dukascopy_python.instruments import INSTRUMENT_FX_MAJORS_USD_JPY

    offer = (
        dukascopy_python.OFFER_SIDE_BID
        if side == "bid"
        else dukascopy_python.OFFER_SIDE_ASK
    )
    raw = dukascopy_python.fetch(
        instrument=INSTRUMENT_FX_MAJORS_USD_JPY,
        interval=dukascopy_python.INTERVAL_MIN_15,
        offer_side=offer,
        start=start,
        end=end,
    )
    return _normalize_frame(raw)


def make_mid(bid: pd.DataFrame, ask: pd.DataFrame) -> pd.DataFrame:
    b = bid.set_index("timestamp")
    a = ask.set_index("timestamp")
    joined = b.join(a, how="inner", lsuffix="_bid", rsuffix="_ask")
    out = pd.DataFrame(index=joined.index)
    for col in ("open", "high", "low", "close"):
        out[col] = (joined[f"{col}_bid"] + joined[f"{col}_ask"]) / 2.0
    out.insert(0, "timestamp", out.index)
    return out.reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch Dukascopy USDJPY 15m bid/ask/mid bars")
    parser.add_argument("--start", type=_parse_date, required=True)
    parser.add_argument("--end", type=_parse_date, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    if args.start >= args.end:
        raise ValueError("--start must be before --end")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    bid = fetch_side(args.start, args.end, "bid")
    ask = fetch_side(args.start, args.end, "ask")
    mid = make_mid(bid, ask)

    frames = {"bid": bid, "ask": ask, "mid": mid}
    for side, frame in frames.items():
        frame.to_csv(args.output_dir / f"usdjpy_{side}_15m.csv", index=False)

    summary = {
        "provider": "Dukascopy via dukascopy-python",
        "symbol": "USDJPY",
        "timeframe": "15m",
        "start_inclusive": args.start.date().isoformat(),
        "end_exclusive_intended": args.end.date().isoformat(),
        "rows": {side: len(frame) for side, frame in frames.items()},
        "first": {
            side: (frame.iloc[0]["timestamp"] if len(frame) else None)
            for side, frame in frames.items()
        },
        "last": {
            side: (frame.iloc[-1]["timestamp"] if len(frame) else None)
            for side, frame in frames.items()
        },
        "note": "Mid OHLC is the arithmetic mean of aligned bid/ask OHLC fields and is only an independent comparison feed, not IC Markets parity data.",
    }
    (args.output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
