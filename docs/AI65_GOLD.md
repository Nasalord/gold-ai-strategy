# AI65 Gold ORB — research implementation

This module implements the deterministic AI65-style XAUUSD opening-range breakout for
**research/backtesting only**. It is deliberately not wired to any broker adapter.

## Source hierarchy

The implementation combines:

1. the uploaded René Balke-style ORB Pine engine for execution mechanics;
2. the AI65 Gold video settings for the Gold adaptation;
3. the strategy ranking spreadsheet for creator-reported benchmark metrics;
4. independent market-data validation used only to test whether the claimed result can be reproduced.

The uploaded Pine source and the Gold video do not appear to use identical TDFI timing.
The code therefore keeps both interpretations explicit instead of silently replacing one
with the other.

## Shared AI65 settings

- XAUUSD, long-only
- `America/New_York`, DST-aware
- opening range `11:00 <= bar open < 13:00`
- one filled trade per session, no re-entry/pyramiding
- breakout at the locked opening-range high; no close confirmation
- TDFI lookback 5
- TDFI long threshold `> -0.05`
- stop distance `3.8 × (actual fill - frozen OR low)`
- target distance `3.3 × (actual fill - frozen OR low)`
- ATR trailing stop off
- force-exit trigger at 22:00 New York, filled next available bar open
- creator-replica notional: $70,000 on $10,000 initial capital
- commission input: $0.04 per contract per side
- slippage input: 100 ticks for stop/market fills

## Two TDFI interpretations

### Uploaded-source replica: arm-time TDFI

The uploaded Pine source checks TDFI when the breakout stop is armed on the final
range bar. It also sets `ocoActive` even when the filter blocks order creation. If TDFI
fails at that point, the source does **not** retry later in the same session.

`AI65Config.creator_1h()` and `AI65Config.creator_3m()` preserve this behavior with
`TDFIGating.ARM_TIME`.

### Gold-video hypothesis: breakout-time TDFI

The AI65 Gold video describes TDFI as confirmation when the breakout occurs. Independent
parity diagnostics fit the creator-reported win rate and drawdown materially better when
the completed range is armed first and TDFI is evaluated on each bar that actually
breaks the OR high. If a breakout bar fails TDFI, the pending setup can remain active
for a later qualifying breakout in the same session.

`AI65Config.video_oanda_1h()` and `AI65Config.video_oanda_3m()` use this behavior with
`TDFIGating.ENTRY_TIME`.

## Working provider hypothesis: OANDA:XAUUSD

The video transcript does not speak the TradingView provider name, so this is not a
frame-level identification. However, the evidence strongly supports OANDA as the
working hypothesis:

- the video states that its full Gold intraday history begins on **2006-03-19**;
- TradingView OANDA:XAUUSD intraday examples independently begin on that same date;
- TradingView currently presents OANDA XAUUSD with three-decimal pricing, consistent
  with a `0.001` minimum-tick convention.

For that reason the `video_oanda_*` presets use:

```text
symbol      = OANDA:XAUUSD
tdfi_gating = entry_time
min_tick    = 0.001
```

This remains a **research hypothesis** until the exact on-screen provider or original
TradingView chart data can be verified. Do not describe it as an exact creator replica.

## TDFI formula

The TDFI is ported directly from the uploaded Pine expression:

```text
mma  = EMA(close * 1000, lookback)
smma = EMA(mma, lookback)
raw  = abs(mma-smma) * (((delta(mma) + delta(smma)) / 2) ** 3)
ntdf = raw / highest(abs(raw), lookback * 3)
```

The Python helper uses recursive EMA seeding from the first non-`na` value. A flat
series creates a zero normalization denominator, which is kept as `None`/`na` instead
of being converted to zero. That matters because `0 > -0.05` would otherwise create a
false long permission on a flat TDFI series.

## Take-profit semantics

The uploaded Pine source expresses take profit internally as:

```text
risk_distance = base_distance * stopMult
TP distance   = risk_distance * tpRR
```

The video demonstrates a final target of `3.3 ×` the base distance while the stop is
`3.8 ×` the base distance. The implementation therefore stores `target_mult=3.3`
directly. The equivalent internal Pine RR is `3.3 / 3.8`, not `3.3`.

## Pending order after force-exit time

The uploaded source closes open positions at the force-exit trigger but does not
explicitly cancel an unfilled breakout entry.

- `ExecutionMode.REPLICA` preserves that source behavior for parity research.
- `ExecutionMode.GUARDED` cancels/blocks pending entries from 22:00 onward.

## Position sizing modes

`SizingMode.CREATOR_FIXED_NOTIONAL` reproduces the creator's reported $70,000 fixed
notional on $10,000 initial capital. It exists only for benchmark replication.

`SizingMode.RISK_BASED` sizes from a configurable percentage of current realized
simulated equity and caps notional exposure. The guarded presets default to:

```text
risk_per_trade_pct = 0.25
max_notional       = 10000
```

The trade log records both theoretical and capped quantity so the effect of the cap is
visible.

## Creator benchmark / parity gate

The ranking sheet reports the 1-hour AI65 optimization at approximately:

- 670 trades
- +552.94% net profit
- 1.667 profit factor
- 52.69% win rate
- 25.73% maximum drawdown

`evaluate_creator_parity()` compares a 1-hour run against those values with narrow
tolerances. A failed parity gate means **investigate the data/execution model**; it is
not permission to optimize parameters until the mismatch disappears.

The current independent Dukascopy validation gets materially closer under the
breakout-time/video interpretation but still does not reproduce the 670-trade benchmark.
These are replication targets, not expected future returns.

## Research presets

- `AI65Config.creator_1h()` — uploaded-source mechanics, 1-hour
- `AI65Config.creator_3m()` — uploaded-source mechanics, 3-minute
- `AI65Config.video_oanda_1h()` — best-supported Gold-video/OANDA hypothesis, 1-hour
- `AI65Config.video_oanda_3m()` — same hypothesis, 3-minute creator sizing
- `AI65Config.guarded_3m()` — capped research mode with source arm-time TDFI
- `AI65Config.video_oanda_guarded_3m()` — capped research mode with video breakout-time TDFI

The 1-hour parity problem should be understood before any 3-minute parameter tuning.

## Run from CSV

CSV columns:

```text
timestamp,open,high,low,close
```

`timestamp` must be ISO-8601 and timezone-aware. Feed session structure matters because
TDFI is recursive; synthetic weekend or settlement-break bars can materially change the
signal sequence.

A generic source-style 1-hour run can be launched with:

```bash
python -m ai_investing_lab.strategies.ai65_gold.csv_runner xauusd_1h.csv \
  --timeframe 60 --mode replica --check-creator-parity \
  --trades-json ai65_1h_trades.json
```

Guarded 3-minute research simulation:

```bash
python -m ai_investing_lab.strategies.ai65_gold.csv_runner xauusd_3m.csv \
  --timeframe 3 --mode guarded --risk-per-trade-pct 0.25 \
  --max-notional 10000 --trades-json ai65_3m_guarded_trades.json
```

Always set the feed's real minimum tick before treating results as cost-adjusted.
Same-bar stop/target ambiguity is resolved conservatively in favor of the stop and
counted in `ambiguous_trades`.

## Trade diagnostics

Each trade can record order-arm, breakout, entry and exit timestamps; OR geometry;
TDFI at range-end/arm/entry; actual and theoretical quantity; notional and risk;
slippage and commission; stop/target; MAE/MFE; holding time; P&L; R multiple; and
same-bar ambiguity.

## Safety boundary

This package does not import or call the repo's IBKR broker adapter. The repository's
current `SAFETY_RULES.md` limits broker-submittable instruments to long-only
equities/ETFs, so XAUUSD remains **research/paper-simulation only**. The video/OANDA
presets do not enable live Gold orders.
