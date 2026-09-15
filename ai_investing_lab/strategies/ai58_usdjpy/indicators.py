from __future__ import annotations

from collections.abc import Sequence

from ai_investing_lab.strategies.ai65_gold.tdfi import compute_tdfi


def compute_atr(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    length: int = 14,
) -> list[float | None]:
    """Approximate Pine `ta.atr` using true range + Wilder RMA.

    Pine's ATR is `ta.rma(ta.tr(true), length)`. The RMA is seeded with the
    simple average of the first `length` true-range observations and then uses
    alpha = 1/length.
    """
    if length <= 0:
        raise ValueError("length must be positive")
    if not (len(highs) == len(lows) == len(closes)):
        raise ValueError("OHLC input lengths must match")

    n = len(closes)
    if n == 0:
        return []

    tr: list[float] = []
    for i in range(n):
        h = float(highs[i])
        l = float(lows[i])
        if i == 0:
            tr.append(h - l)
        else:
            pc = float(closes[i - 1])
            tr.append(max(h - l, abs(h - pc), abs(l - pc)))

    out: list[float | None] = [None] * n
    if n < length:
        return out

    prev = sum(tr[:length]) / length
    out[length - 1] = prev
    alpha = 1.0 / length
    for i in range(length, n):
        prev = alpha * tr[i] + (1.0 - alpha) * prev
        out[i] = prev
    return out


__all__ = ["compute_tdfi", "compute_atr"]
