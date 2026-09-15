from __future__ import annotations

from typing import Iterable


def ema(values: list[float], length: int) -> list[float | None]:
    if length < 1:
        raise ValueError("length must be >=1")
    out: list[float | None] = [None] * len(values)
    if not values:
        return out
    alpha = 2.0 / (length + 1.0)
    prev = float(values[0])
    out[0] = prev
    for i in range(1, len(values)):
        prev = alpha * float(values[i]) + (1.0 - alpha) * prev
        out[i] = prev
    return out


def momentum(values: list[float], length: int) -> list[float | None]:
    out: list[float | None] = [None] * len(values)
    for i in range(length, len(values)):
        out[i] = float(values[i]) - float(values[i - length])
    return out


def crossover(values: list[float | None], level: float, i: int) -> bool:
    if i <= 0 or values[i] is None or values[i - 1] is None:
        return False
    return float(values[i]) > level and float(values[i - 1]) <= level


def crossunder(values: list[float | None], level: float, i: int) -> bool:
    if i <= 0 or values[i] is None or values[i - 1] is None:
        return False
    return float(values[i]) < level and float(values[i - 1]) >= level


def growth_percent(values: list[float | None], i: int, lookback: int, *, rising: bool) -> float:
    count = 0
    for offset in range(lookback):
        j = i - offset
        k = j - 1
        if k < 0 or values[j] is None or values[k] is None:
            continue
        if rising and float(values[j]) > float(values[k]):
            count += 1
        elif (not rising) and float(values[j]) < float(values[k]):
            count += 1
    return 100.0 * count / lookback


def rolling_low(values: list[float], i: int, lookback: int) -> float | None:
    if i < 0:
        return None
    start = max(0, i - lookback + 1)
    window = values[start : i + 1]
    return min(window) if window else None


def rolling_high(values: list[float], i: int, lookback: int) -> float | None:
    if i < 0:
        return None
    start = max(0, i - lookback + 1)
    window = values[start : i + 1]
    return max(window) if window else None
