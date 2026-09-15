from __future__ import annotations

from collections.abc import Sequence


def _pine_ema(values: Sequence[float | None], length: int) -> list[float | None]:
    """Replicate Pine's recursive EMA seeding used by ta.ema for non-na series.

    The first non-na source value seeds the EMA, then:
        ema = alpha * source + (1 - alpha) * ema[1]
    """
    if length <= 0:
        raise ValueError("length must be positive")

    alpha = 2.0 / (length + 1.0)
    out: list[float | None] = [None] * len(values)
    prev: float | None = None

    for i, value in enumerate(values):
        if value is None:
            continue
        x = float(value)
        prev = x if prev is None else alpha * x + (1.0 - alpha) * prev
        out[i] = prev

    return out


def compute_tdfi(closes: Sequence[float], lookback: int = 5) -> list[float | None]:
    """Compute the normalized TDFI used by the uploaded ORB Pine source.

    Mirrors:
      mma = ta.ema(source * 1000, lookback)
      smma = ta.ema(mma, lookback)
      tdf = abs(mma-smma) * (((Δmma + Δsmma) / 2) ** 3)
      ntdf = tdf / ta.highest(abs(tdf), lookback * 3)

    A zero normalization denominator produces ``None`` (Pine ``na`` from 0/0),
    which correctly fails the long threshold gate.
    """
    if lookback <= 0:
        raise ValueError("lookback must be positive")

    scaled = [float(x) * 1000.0 for x in closes]
    mma = _pine_ema(scaled, lookback)
    smma = _pine_ema(mma, lookback)

    raw: list[float | None] = [None] * len(closes)
    for i in range(1, len(closes)):
        if (
            mma[i] is None
            or mma[i - 1] is None
            or smma[i] is None
            or smma[i - 1] is None
        ):
            continue

        impulse_mma = mma[i] - mma[i - 1]
        impulse_smma = smma[i] - smma[i - 1]
        divergence = abs(mma[i] - smma[i])
        average_impulse = (impulse_mma + impulse_smma) / 2.0
        raw[i] = divergence * (average_impulse**3)

    normalized: list[float | None] = [None] * len(closes)
    window = lookback * 3

    for i, value in enumerate(raw):
        if value is None:
            continue

        prior = [
            abs(x)
            for x in raw[max(0, i - window + 1) : i + 1]
            if x is not None
        ]
        denominator = max(prior) if prior else 0.0
        normalized[i] = None if denominator == 0.0 else value / denominator

    return normalized
