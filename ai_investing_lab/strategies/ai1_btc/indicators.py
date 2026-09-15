from __future__ import annotations

from math import isnan
from typing import Iterable


def _sma(values: list[float], length: int) -> list[float | None]:
    out: list[float | None] = [None] * len(values)
    if length <= 0:
        raise ValueError("length must be positive")
    total = 0.0
    for i, v in enumerate(values):
        total += v
        if i >= length:
            total -= values[i - length]
        if i >= length - 1:
            out[i] = total / length
    return out


def ema(values: list[float | None], length: int) -> list[float | None]:
    """Pine-like EMA seeded by the SMA of the first `length` valid values."""
    out: list[float | None] = [None] * len(values)
    alpha = 2.0 / (length + 1.0)
    buf: list[float] = []
    prev: float | None = None
    for i, value in enumerate(values):
        if value is None:
            continue
        if prev is None:
            buf.append(value)
            if len(buf) < length:
                continue
            if len(buf) > length:
                buf.pop(0)
            prev = sum(buf) / length
            out[i] = prev
        else:
            prev = alpha * value + (1.0 - alpha) * prev
            out[i] = prev
    return out


def rma(values: list[float | None], length: int) -> list[float | None]:
    """Wilder/Pine RMA seeded with the first SMA(length)."""
    out: list[float | None] = [None] * len(values)
    alpha = 1.0 / length
    buf: list[float] = []
    prev: float | None = None
    for i, value in enumerate(values):
        if value is None:
            continue
        if prev is None:
            buf.append(value)
            if len(buf) < length:
                continue
            if len(buf) > length:
                buf.pop(0)
            prev = sum(buf) / length
            out[i] = prev
        else:
            prev = alpha * value + (1.0 - alpha) * prev
            out[i] = prev
    return out


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
    return rma([float(x) for x in true_range(highs, lows, closes)], length)


def ssl_state(highs: list[float], lows: list[float], closes: list[float], period: int) -> list[int]:
    sma_high = _sma(highs, period)
    sma_low = _sma(lows, period)
    hlv: list[int] = [0] * len(closes)
    prev = 0
    for i, close in enumerate(closes):
        sh = sma_high[i]
        sl = sma_low[i]
        if sh is not None and close > sh:
            prev = 1
        elif sl is not None and close < sl:
            prev = -1
        hlv[i] = prev
    return hlv


def _ema_float(values: list[float], length: int) -> list[float | None]:
    return ema([float(v) for v in values], length)


def t3(values: list[float], length: int, b: float = 0.7) -> list[float | None]:
    e1 = _ema_float(values, length)
    e2 = ema(e1, length)
    e3 = ema(e2, length)
    e4 = ema(e3, length)
    e5 = ema(e4, length)
    e6 = ema(e5, length)
    c1 = -(b ** 3)
    c2 = 3 * b * b + 3 * (b ** 3)
    c3 = -6 * b * b - 3 * b - 3 * (b ** 3)
    c4 = 1 + 3 * b + (b ** 3) + 3 * b * b
    out: list[float | None] = [None] * len(values)
    for i in range(len(values)):
        if e3[i] is None or e4[i] is None or e5[i] is None or e6[i] is None:
            continue
        out[i] = c1 * e6[i] + c2 * e5[i] + c3 * e4[i] + c4 * e3[i]
    return out


def adx_with_ema(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    di_length: int,
    adx_smoothing: int,
    ema_length: int,
) -> tuple[list[float | None], list[float | None]]:
    n = len(closes)
    plus_dm: list[float | None] = [None] * n
    minus_dm: list[float | None] = [None] * n
    for i in range(1, n):
        up = highs[i] - highs[i - 1]
        down = lows[i - 1] - lows[i]
        plus_dm[i] = up if up > down and up > 0 else 0.0
        minus_dm[i] = down if down > up and down > 0 else 0.0

    tr = [float(x) for x in true_range(highs, lows, closes)]
    tr_rma = rma(tr, di_length)
    plus_rma = rma(plus_dm, di_length)
    minus_rma = rma(minus_dm, di_length)

    plus: list[float | None] = [None] * n
    minus: list[float | None] = [None] * n
    ratio: list[float | None] = [None] * n
    for i in range(n):
        tvr = tr_rma[i]
        pr = plus_rma[i]
        mr = minus_rma[i]
        if tvr is None or pr is None or mr is None:
            continue
        if tvr == 0:
            p = 0.0
            m = 0.0
        else:
            p = 100.0 * pr / tvr
            m = 100.0 * mr / tvr
        plus[i] = p
        minus[i] = m
        s = p + m
        ratio[i] = abs(p - m) / (1.0 if s == 0 else s)

    adx = rma(ratio, adx_smoothing)
    adx100: list[float | None] = [None if x is None else 100.0 * x for x in adx]
    adx_ema = ema(adx100, ema_length)
    return adx100, adx_ema


def crossover(a: list[float | None], b: list[float | None], i: int) -> bool:
    if i <= 0 or a[i] is None or b[i] is None or a[i - 1] is None or b[i - 1] is None:
        return False
    return a[i] > b[i] and a[i - 1] <= b[i - 1]


def crossunder(a: list[float | None], b: list[float | None], i: int) -> bool:
    if i <= 0 or a[i] is None or b[i] is None or a[i - 1] is None or b[i - 1] is None:
        return False
    return a[i] < b[i] and a[i - 1] >= b[i - 1]
