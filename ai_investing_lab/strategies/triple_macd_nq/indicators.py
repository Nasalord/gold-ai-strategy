from __future__ import annotations

from collections import deque
from math import fabs
from typing import Iterable


def ema(values: Iterable[float], length: int) -> list[float]:
    vals = list(values)
    if not vals:
        return []
    alpha = 2.0 / (length + 1.0)
    out = [float(vals[0])]
    for v in vals[1:]:
        out.append(alpha * float(v) + (1.0 - alpha) * out[-1])
    return out


def sma_optional(values: list[float | None], length: int) -> list[float | None]:
    out: list[float | None] = []
    q: deque[float] = deque()
    total = 0.0
    for v in values:
        if v is None:
            q.clear()
            total = 0.0
            out.append(None)
            continue
        q.append(float(v))
        total += float(v)
        if len(q) > length:
            total -= q.popleft()
        out.append(total / length if len(q) == length else None)
    return out


def rolling_high_abs_optional(values: list[float | None], length: int) -> list[float | None]:
    out: list[float | None] = []
    for i, v in enumerate(values):
        if v is None:
            out.append(None)
            continue
        window = [fabs(x) for x in values[max(0, i - length + 1): i + 1] if x is not None]
        out.append(max(window) if window else None)
    return out


def macd_hist(close: list[float], fast: int, slow: int, signal: int = 9) -> list[float]:
    fast_e = ema(close, fast)
    slow_e = ema(close, slow)
    line = [a - b for a, b in zip(fast_e, slow_e)]
    sig = ema(line, signal)
    return [a - b for a, b in zip(line, sig)]


def tdfi(
    close: list[float],
    lookback: int,
    *,
    smooth: bool = False,
    smooth_period: int = 15,
) -> list[float | None]:
    # Literal source formula from the supplied Pine script.
    scaled = [x * 1000.0 for x in close]
    mma = ema(scaled, lookback)
    smma = ema(mma, lookback)
    raw: list[float | None] = [None]
    for i in range(1, len(close)):
        i1 = mma[i] - mma[i - 1]
        i2 = smma[i] - smma[i - 1]
        d = abs(mma[i] - smma[i])
        avg_i = (i1 + i2) / 2.0
        raw.append(d * (avg_i ** 3))
    highs = rolling_high_abs_optional(raw, lookback * 3)
    norm: list[float | None] = []
    for r, h in zip(raw, highs):
        if r is None or h is None:
            norm.append(None)
        else:
            norm.append(r / (h if h != 0 else 1.0))
    if not smooth:
        return norm
    return sma_optional(norm, smooth_period)
