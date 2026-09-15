from __future__ import annotations

from math import ceil, floor


def sma(values: list[float | None], length: int) -> list[float | None]:
    out: list[float | None] = [None] * len(values)
    window: list[float] = []
    for i, value in enumerate(values):
        if value is None:
            window.clear()
            continue
        window.append(float(value))
        if len(window) > length:
            window.pop(0)
        if len(window) == length:
            out[i] = sum(window) / length
    return out


def ema(values: list[float | None], length: int) -> list[float | None]:
    out: list[float | None] = [None] * len(values)
    alpha = 2.0 / (length + 1.0)
    prev: float | None = None
    for i, value in enumerate(values):
        if value is None:
            prev = None
            continue
        x = float(value)
        prev = x if prev is None else alpha * x + (1.0 - alpha) * prev
        out[i] = prev
    return out


def rma(values: list[float | None], length: int) -> list[float | None]:
    """Wilder RMA using an SMA seed, matching Pine's ta.rma shape."""
    out: list[float | None] = [None] * len(values)
    seed: list[float] = []
    prev: float | None = None
    alpha = 1.0 / length
    for i, value in enumerate(values):
        if value is None:
            seed.clear()
            prev = None
            continue
        x = float(value)
        if prev is None:
            seed.append(x)
            if len(seed) == length:
                prev = sum(seed) / length
                out[i] = prev
            continue
        prev = alpha * x + (1.0 - alpha) * prev
        out[i] = prev
    return out


def dema(values: list[float | None], length: int) -> list[float | None]:
    e1 = ema(values, length)
    e2 = ema(e1, length)
    out: list[float | None] = [None] * len(values)
    for i, (a, b) in enumerate(zip(e1, e2)):
        if a is not None and b is not None:
            out[i] = 2.0 * a - b
    return out


def tma(values: list[float | None], length: int) -> list[float | None]:
    # Exact construction from the supplied Pine source.
    first = sma(values, ceil(length / 2))
    return sma(first, floor(length / 2) + 1)


def moving_average(values: list[float | None], length: int, kind: str) -> list[float | None]:
    if kind == "SMA":
        return sma(values, length)
    if kind == "EMA":
        return ema(values, length)
    if kind == "RMA":
        return rma(values, length)
    if kind == "DEMA":
        return dema(values, length)
    if kind == "TMA":
        return tma(values, length)
    raise ValueError(f"unsupported moving average kind: {kind}")


def true_range(highs: list[float], lows: list[float], closes: list[float]) -> list[float]:
    out: list[float] = []
    for i, (h, l) in enumerate(zip(highs, lows)):
        if i == 0:
            out.append(h - l)
        else:
            pc = closes[i - 1]
            out.append(max(h - l, abs(h - pc), abs(l - pc)))
    return out


def atr(highs: list[float], lows: list[float], closes: list[float], length: int) -> list[float | None]:
    tr = [float(x) for x in true_range(highs, lows, closes)]
    return rma(tr, length)


def crossed_above(a: list[float | None], b: list[float | None], i: int) -> bool:
    if i < 1:
        return False
    a0, a1, b0, b1 = a[i], a[i - 1], b[i], b[i - 1]
    if None in (a0, a1, b0, b1):
        return False
    return bool(a0 > b0 and a1 <= b1)
