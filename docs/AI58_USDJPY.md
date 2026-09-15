# AI58 — René Balke ORB for USDJPY

Status: **SOURCE VERIFIED / VIDEO PARITY PASSED / FRESH OOS FAILED — WATCHLIST ONLY**

AI58 is the second independently validated strategy candidate after AI65. The repository has the Pine engine linked by the creator ranking sheet, and the user later supplied the full AI58 video transcript containing the optimized settings and benchmark window.

## Evidence-backed optimized setup

The supplied video transcript identifies:

```text
symbol/provider        IC Markets USDJPY
timeframe              15m
timezone               America/New_York
opening range          06:00-08:15 New York
trade direction        Long Only
TDFI                   enabled
TDFI lookback          50
TDFI high / low        0 / 0
ATR trailing           enabled
NNFX ATR X / length    450
ATR SL / multiplier    11
initial capital        $10,000
fixed notional         $70,000 per trade
commission             $3.50 per standard lot per side
slippage               12 ticks (creator calls this 1.2 pips)
bar magnifier          enabled in creator test
recalc                 every tick
in-sample window       2021-09-01 to 2025-09-01
video OOS window       2025-09-01 to 2026-03-14
```

The transcript says the optimized strategy exits only through the ATR trailing stop, but automatic speech recognition renders the fixed stop/TP inputs ambiguously as "one". In the uploaded Pine engine literal `1/1` would create active fixed exits and conflicts with the narration. We therefore predeclared exactly two interpretations for validation:

1. `100/100` fixed-exit practical-disable hypothesis.
2. Literal `1/1` control.

No parameter grid/search was used.

## Creator video benchmark

For 2021-09-01 through 2025-09-01 the video reports approximately:

```text
trades                 185
net profit             +287%
profit factor          1.70
max drawdown           17%
```

For 2025-09-01 through 2026-03-14 it reports:

```text
trades                 24
net profit             +32%
profit factor          1.57
win rate               50%
max drawdown           14%
```

The ranking spreadsheet contains a later/different AI58 row (229 trades, +309.74%, PF 1.736, 45.41% win rate, 20.79% DD). That row is kept separate from the explicit video benchmark rather than silently reconciling the two.

## Independent parity result

Using independent Dukascopy USDJPY 15m bid/ask data and arithmetic midpoint OHLC, the source-faithful `100/100` interpretation reproduced the creator video closely enough to pass the predeclared parity gate.

Midpoint result, 2021-09-01 to 2025-09-01:

```text
trades                 188
net profit             +271.954%
profit factor          1.7191
win rate               46.81%
closed-trade max DD    18.31%
parity gate            PASS
```

Bid and ask variants also independently passed:

```text
bid                     188 trades / +270.70% / PF 1.7156 / DD 18.42%
ask                     188 trades / +265.02% / PF 1.6921 / DD 18.53%
```

The literal `1/1` control failed badly (midpoint: 480 trades, about +11.1%, PF about 1.03). This strongly supports the practical-disable interpretation without treating it as screenshot-confirmed.

## Creator-window OOS replication

Independent midpoint result for 2025-09-01 through 2026-03-14:

```text
trades                 26
net profit             +39.54%
profit factor          2.016
win rate               53.85%
closed-trade max DD    12.12%
```

This was directionally consistent with the creator's 24 trades / +32% / PF 1.57 / 50% win / ~14% DD report.

## Robustness and fresh OOS

A predeclared robustness matrix was then run without selecting a better parameter set. It tested:

- slippage at 18 and 24 ticks;
- commission at 1.5x and 2x;
- combined 2x transaction costs;
- TDFI lookback 40 and 60 around baseline 50;
- ATR length 400 and 500 around baseline 450;
- ATR multiplier 9 and 13 around baseline 11;
- opening range shifted exactly 15 minutes earlier/later;
- a fixed $10k-notional paper-normalized comparison;
- calendar-year results.

The historical/in-sample edge was reasonably robust. Even combined 2x costs remained positive:

```text
in-sample with 2x costs
trades                 188
net profit             +240.13%
profit factor          1.608
max drawdown           20.43%
```

All predeclared neighboring parameter variants stayed profitable in-sample.

However, the genuinely fresh period after the creator video did **not** hold up. Baseline from 2026-03-15 through 2026-09-14 (end exclusive):

```text
trades                 24
wins / losses          7 / 17
win rate               29.17%
net profit             -8.76%
profit factor          0.795
closed-trade max DD    16.50%
```

The fresh period remained negative across every nearby parameter/cost variant tested. Examples:

```text
TDFI 40                -3.39% / PF 0.916
TDFI 60                -0.75% / PF 0.977
ATR length 400         -14.39% / PF 0.680
ATR length 500         -9.75% / PF 0.776
ATR multiplier 9       -16.35% / PF 0.620
ATR multiplier 13      -10.89% / PF 0.736
range 15m earlier      -5.11% / PF 0.868
range 15m later        -7.03% / PF 0.815
2x costs               -12.46% / PF 0.725
```

Because weakness persists across the local parameter neighborhood, the current interpretation is **regime deterioration**, not a single fragile optimized number.

The combined OOS period since 2025-09-01 is still positive because the first six months were strong:

```text
trades                 50
net profit             +27.49%
profit factor          1.340
max drawdown           12.39%
```

That does not override the more recent deterioration.

## Year-by-year baseline

```text
2022   +102.50%   PF 2.173
2023    +26.94%   PF 1.255
2024    +99.67%   PF 2.148
2025     +6.23%   PF 1.052
2026*   +19.54%   PF 1.400
```

`2026*` is a calendar-year partial result through 2026-09-13. It includes the strong January-March period; the isolated post-video March-15-forward segment is negative.

## Current decision

AI58 should **not** be promoted into any live or automated execution path. It also should not be treated as a currently passing strategy just because historical parity was excellent.

Current classification:

```text
Source verification        PASS
Creator video parity       PASS
Creator-window OOS         PASS / directionally consistent
Cost robustness            PASS
Local parameter robustness PASS in-sample
Fresh post-video OOS       FAIL
Overall                    WATCHLIST / SHADOW PAPER RESEARCH ONLY
```

A reasonable next research step is passive/shadow monitoring of unchanged signals and evaluation of other strategy candidates. Do not tune AI58 to repair the March-September 2026 period after observing it.

## Remaining fidelity differences

- creator feed: IC Markets; independent validation feed: Dukascopy;
- creator enabled TradingView Bar Magnifier; current parity engine uses 15m OHLC path assumptions;
- TradingView maximum drawdown may use bar-level mark-to-market rules while the research engine currently reports closed-trade equity drawdown;
- the `100/100` fixed-exit disable values are strongly evidence-supported by parity and narration, but not screenshot-verified.

## Safety boundary

AI58 remains research/backtest/paper-simulation only. It has no broker execution path and is not authorized for live trading.
