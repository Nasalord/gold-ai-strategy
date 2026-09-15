from __future__ import annotations

from math import ceil, floor


def sma(values: list[float | None], length: int) -> list[float | None]:
    """Rolling SMA with identical window/na semantics to the literal version."""
    if length <= 0:
        raise ValueError("length must be positive")
    out: list[float | None] = [None] * len(values)
    rolling = 0.0
    missing = 0
    for i, value in enumerate(values):
        if value is None:
            missing += 1
        else:
            rolling += float(value)

        if i >= length:
            old = values[i - length]
            if old is None:
                missing -= 1
            else:
                rolling -= float(old)

        if i >= length - 1 and missing == 0:
            out[i] = rolling / length
    return out


def ema(values: list[float | None], length: int) -> list[float | None]:
    """TradingView-like EMA: seed with the first non-na source value."""
    out: list[float | None] = [None] * len(values)
    alpha = 2.0 / (length + 1.0)
    prev: float | None = None
    for i, value in enumerate(values):
        if value is None:
            continue
        x = float(value)
        prev = x if prev is None else alpha * x + (1.0 - alpha) * prev
        out[i] = prev
    return out


def rma(values: list[float | None], length: int) -> list[float | None]:
    """Wilder RMA with an SMA seed, matching ta.rma/ta.atr behavior."""
    out: list[float | None] = [None] * len(values)
    valid: list[float] = []
    seed_i: int | None = None
    for i, value in enumerate(values):
        if value is None:
            continue
        valid.append(float(value))
        if len(valid) == length:
            seed_i = i
            out[i] = sum(valid) / length
            break
    if seed_i is None:
        return out
    prev = float(out[seed_i])
    for i in range(seed_i + 1, len(values)):
        value = values[i]
        if value is None:
            continue
        prev = (prev * (length - 1) + float(value)) / length
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
    raise ValueError(f"unknown MA type: {kind}")


def true_range(highs: list[float], lows: list[float], closes: list[float]) -> list[float]:
    out: list[float] = []
    for i, (h, l, _c) in enumerate(zip(highs, lows, closes)):
        if i == 0:
            out.append(h - l)
        else:
            pc = closes[i - 1]
            out.append(max(h - l, abs(h - pc), abs(l - pc)))
    return out


def atr(highs: list[float], lows: list[float], closes: list[float], length: int) -> list[float | None]:
    return rma([float(x) for x in true_range(highs, lows, closes)], length)


def crossover(a: list[float | None], b: list[float | None], i: int) -> bool:
    if i <= 0:
        return False
    a0, b0, a1, b1 = a[i - 1], b[i - 1], a[i], b[i]
    return None not in (a0, b0, a1, b1) and float(a1) > float(b1) and float(a0) <= float(b0)
