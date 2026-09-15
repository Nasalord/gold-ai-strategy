from __future__ import annotations

from math import isnan
from typing import Sequence


def _is_na(value: float | None) -> bool:
    return value is None or (isinstance(value, float) and isnan(value))


def ema(values: Sequence[float | None], length: int) -> list[float | None]:
    """Pine-style EMA: seed from first non-na source, then recurse."""
    if length <= 0:
        raise ValueError("length must be positive")
    alpha = 2.0 / (length + 1.0)
    out: list[float | None] = []
    prev: float | None = None
    for raw in values:
        if _is_na(raw):
            out.append(None)
            continue
        value = float(raw)
        prev = value if prev is None else alpha * value + (1.0 - alpha) * prev
        out.append(prev)
    return out


def rma(values: Sequence[float | None], length: int) -> list[float | None]:
    """Pine ta.rma approximation: SMA seed of first `length` non-na values."""
    if length <= 0:
        raise ValueError("length must be positive")
    out: list[float | None] = [None] * len(values)
    seed: list[float] = []
    prev: float | None = None
    alpha = 1.0 / length
    for i, raw in enumerate(values):
        if _is_na(raw):
            continue
        value = float(raw)
        if prev is None:
            seed.append(value)
            if len(seed) == length:
                prev = sum(seed) / length
                out[i] = prev
        else:
            prev = alpha * value + (1.0 - alpha) * prev
            out[i] = prev
    return out


def true_range(highs: Sequence[float], lows: Sequence[float], closes: Sequence[float]) -> list[float]:
    """Pine ta.tr(true)-style true range used by ta.atr()."""
    if not (len(highs) == len(lows) == len(closes)):
        raise ValueError("OHLC lengths must match")
    out: list[float] = []
    for i, (h, l) in enumerate(zip(highs, lows)):
        h = float(h)
        l = float(l)
        if i == 0:
            out.append(h - l)
        else:
            pc = float(closes[i - 1])
            out.append(max(h - l, abs(h - pc), abs(l - pc)))
    return out


def _true_range_no_handle_na(
    highs: Sequence[float], lows: Sequence[float], closes: Sequence[float]
) -> list[float | None]:
    """Pine `ta.tr` variable semantics: first value is na without prev close."""
    if not (len(highs) == len(lows) == len(closes)):
        raise ValueError("OHLC lengths must match")
    out: list[float | None] = [None]
    for i in range(1, len(highs)):
        h = float(highs[i])
        l = float(lows[i])
        pc = float(closes[i - 1])
        out.append(max(h - l, abs(h - pc), abs(l - pc)))
    return out


def atr(highs: Sequence[float], lows: Sequence[float], closes: Sequence[float], length: int) -> list[float | None]:
    return rma(true_range(highs, lows, closes), length)


def adx(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    *,
    di_length: int,
    adx_smoothing: int,
) -> list[float | None]:
    if not (len(highs) == len(lows) == len(closes)):
        raise ValueError("OHLC lengths must match")
    plus_dm: list[float | None] = [None]
    minus_dm: list[float | None] = [None]
    for i in range(1, len(highs)):
        up = float(highs[i]) - float(highs[i - 1])
        down = float(lows[i - 1]) - float(lows[i])
        plus_dm.append(up if up > down and up > 0 else 0.0)
        minus_dm.append(down if down > up and down > 0 else 0.0)

    # The creator Pine uses `ta.rma(ta.tr, len)`. The `ta.tr` variable is the
    # non-handle-na form, so its first value is na (unlike ta.atr's ta.tr(true)).
    tr_rma = rma(_true_range_no_handle_na(highs, lows, closes), di_length)
    plus_rma = rma(plus_dm, di_length)
    minus_rma = rma(minus_dm, di_length)

    dx: list[float | None] = []
    for trv, pv, mv in zip(tr_rma, plus_rma, minus_rma):
        if trv is None or pv is None or mv is None or trv == 0:
            dx.append(None)
            continue
        plus = 100.0 * pv / trv
        minus = 100.0 * mv / trv
        denom = plus + minus
        dx.append(0.0 if denom == 0 else 100.0 * abs(plus - minus) / denom)
    return rma(dx, adx_smoothing)


def supertrend_direction(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    *,
    factor: float,
    atr_length: int,
) -> list[int | None]:
    """TradingView ta.supertrend direction: -1 uptrend, +1 downtrend."""
    atr_values = atr(highs, lows, closes, atr_length)
    n = len(closes)
    directions: list[int | None] = [None] * n
    upper_final: list[float | None] = [None] * n
    lower_final: list[float | None] = [None] * n
    supertrend: list[float | None] = [None] * n

    for i in range(n):
        av = atr_values[i]
        if av is None:
            # TradingView documents downtrend until ATR becomes available.
            directions[i] = 1
            continue

        hl2 = (float(highs[i]) + float(lows[i])) / 2.0
        basic_upper = hl2 + factor * av
        basic_lower = hl2 - factor * av

        prev_atr = atr_values[i - 1] if i > 0 else None
        if i == 0 or prev_atr is None:
            # First ATR-valid bar starts from its own basic bands. The previous
            # implementation incorrectly carried zeros into this initialization.
            upper_f = basic_upper
            lower_f = basic_lower
            direction = 1
        else:
            prev_upper = float(upper_final[i - 1])
            prev_lower = float(lower_final[i - 1])
            prev_close = float(closes[i - 1])
            upper_f = (
                basic_upper
                if (basic_upper < prev_upper or prev_close > prev_upper)
                else prev_upper
            )
            lower_f = (
                basic_lower
                if (basic_lower > prev_lower or prev_close < prev_lower)
                else prev_lower
            )
            prev_st = float(supertrend[i - 1])
            if prev_st == prev_upper:
                direction = -1 if float(closes[i]) > upper_f else 1
            else:
                direction = 1 if float(closes[i]) < lower_f else -1

        upper_final[i] = upper_f
        lower_final[i] = lower_f
        directions[i] = direction
        supertrend[i] = lower_f if direction == -1 else upper_f

    return directions


def range_filter(
    closes: Sequence[float], *, period: int, multiplier: float
) -> tuple[list[float | None], list[bool], list[bool]]:
    """Return Pine range filter plus first long/short condition transitions."""
    diffs: list[float | None] = [None]
    for i in range(1, len(closes)):
        diffs.append(abs(float(closes[i]) - float(closes[i - 1])))
    avrng = ema(diffs, period)
    smoothed = ema(avrng, period * 2 - 1)
    smrng = [None if x is None else x * multiplier for x in smoothed]

    filt: list[float | None] = [None] * len(closes)
    upward = 0.0
    downward = 0.0
    cond_ini = 0
    range_long: list[bool] = [False] * len(closes)
    range_short: list[bool] = [False] * len(closes)

    for i, close in enumerate(closes):
        r = smrng[i]
        if r is None:
            continue
        x = float(close)
        prev = filt[i - 1] if i > 0 and filt[i - 1] is not None else 0.0
        if x > prev:
            current = prev if x - r < prev else x - r
        else:
            current = prev if x + r > prev else x + r
        filt[i] = current

        prev_filt = filt[i - 1] if i > 0 else None
        if prev_filt is not None:
            if current > prev_filt:
                upward += 1.0
                downward = 0.0
            elif current < prev_filt:
                downward += 1.0
                upward = 0.0

        prev_close = float(closes[i - 1]) if i > 0 else x
        long_cond = x > current and x != prev_close and upward > 0
        short_cond = x < current and x != prev_close and downward > 0
        prev_cond = cond_ini
        if long_cond:
            cond_ini = 1
        elif short_cond:
            cond_ini = -1
        range_long[i] = long_cond and prev_cond == -1
        range_short[i] = short_cond and prev_cond == 1

    return filt, range_long, range_short
