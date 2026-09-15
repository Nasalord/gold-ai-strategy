# AI8 — SuperTrend + Range Filter with ADX (BTCUSDT 2H)

## Status

**SOURCE + VIDEO VERIFIED / TRADE GENERATION NEAR PARITY / CREATOR RETURN-PF PARITY UNRESOLVED**

Research/backtest/paper only. Do not treat the creator headline as independently reproduced and do not route this strategy to live execution.

## Creator-linked Pine inputs

The supplied Pine v5 source and creator video agree on the optimized signal inputs:

- Asset: BTCUSDT
- Timeframe: 2 hours
- Direction: Long only
- SuperTrend ATR length: 8
- SuperTrend factor: 1.6
- ADX smoothing: 14
- DI length: 14
- ADX threshold: > 18
- Range Filter sampling period: 175
- Range Filter multiplier: 5.0
- Stop ATR length in the supplied strategy source: 50
- Stop distance: 10x ATR
- Risk/reward input in source: 100x risk (effectively a remote safety target; creator describes the Range Filter sell as the normal exit)

## Creator-video TradingView Properties

The video resolves the properties that are **not** encoded in the strategy() declaration:

- Initial capital: $100,000
- Order size: fixed $80,000 cash per accepted entry
- Pyramiding: 7
- Commission: 0.1% on each entry and each exit
- Slippage: 2 ticks
- Up to seven Long entries can be stacked.
- A Range Filter sell closes the Long stack on the next bar open.
- The creator states that when a new Long is added, the stop is updated to the newest entry's 10x-ATR stop level and that this stop can close the earlier stacked entries as well.

The raw Pine declaration itself uses percent_of_equity=15 and leaves pyramiding at Pine's default of one. Those declaration defaults are therefore controls only, **not** the creator benchmark Properties.

## Creator benchmark

Spreadsheet/video target for 2020-03-01 through 2024-03-01:

- Trades: 319
- Net profit: +637.97%
- Profit factor: 1.969
- Win rate: 44.51%
- Max drawdown: 27.87%
- Costs: 0.1% commission + 2 ticks slippage

## Independent reconstruction

Data source: official Binance Vision 2-hour klines. No indicator parameter search is performed.

### Warm-start Binance spot BTCUSDT

Indicators are warmed on data beginning 2019-01-01 and trading is gated to 2020-03-01:

- Trades: 325
- Net profit: +504.11%
- Profit factor: 1.7423
- Win rate: 44.00%
- Closed-trade equity drawdown approximation: 26.55%
- Intrabar equity-drawdown diagnostic: 32.19%
- Exit legs: 306 Range Filter, 19 stop-loss

### TradingView-style cold-start control

Because TradingView Deep Backtesting begins script calculations at the selected range start, a second test begins both data calculation and trading at 2020-03-01:

- Trades: 324
- Net profit: +514.81%
- Profit factor: 1.76735
- Win rate: 44.14%
- Closed-trade equity drawdown approximation: 25.94%
- Intrabar equity-drawdown diagnostic: 31.46%
- Exit legs: 306 Range Filter, 18 stop-loss

Cold-start calculation moves the result modestly toward the creator benchmark but does not explain the +637.97% / PF 1.969 headline.

### Binance USD-M perpetual control

Same frozen rules on the Binance perpetual feed:

- Trades: 323
- Net profit: +456.43%
- Profit factor: 1.6509
- Win rate: 44.27%
- Closed-trade equity drawdown approximation: 32.55%
- Intrabar equity-drawdown diagnostic: 38.60%

The perpetual feed is worse and does not explain the creator benchmark. Spot remains the closer independent feed.

## TradingView-fidelity diagnostics completed

The following were tested without changing any strategy indicator parameter:

1. **Pyramiding** — creator-video `pyramiding=7` is essential. It moves the one-position reconstruction from about 131 closed trades to roughly 325 and resolves the main structural trade-count mismatch.
2. **Provider class** — Binance spot is closer than Binance USD-M perpetual; futures are not the missing explanation.
3. **Date boundary** — including March 1, 2024 does not materially change the benchmark result.
4. **Calculation start state** — a cold start at 2020-03-01 improves the result slightly but does not close the gap.
5. **ADX/SuperTrend initialization** — aligned to Pine/TradingView semantics; this does not materially change the mature four-year result.
6. **`strategy.cash` sizing** — fixed $80k cash quantity is derived from the signal-bar price, while percentage commission is applied to the actual next-open filled transaction value. Correcting this changes the result only marginally and is not the missing return/PF source.
7. **Commission / PF accounting** — commission is charged on entry and exit and trade net PnL is used in profit-factor components. Removing costs entirely would still not explain the full creator gap.
8. **Drawdown** — the historical closed-trade DD statistic is only an approximation to TradingView's intrabar Strategy Tester metric. A separate intrabar equity diagnostic is retained, but it is not claimed as byte-for-byte TradingView parity for pyramided positions.

## Interpretation

Trade generation is now very close to the creator report (324–325 vs 319) and win rate is also close (~44.1% vs 44.51%). The remaining difference is concentrated in trade PnL magnitude: independent spot data produces roughly +504% to +515% with PF 1.74–1.77 versus the creator's +637.97% / PF 1.969.

The documented TradingView execution/accounting details tested so far do not explain that residual gap. The most likely unresolved sources are exact TradingView historical chart data/revisions or a creator Strategy Tester state that cannot be reconstructed from the Pine source and video alone. The cleanest way to settle exact parity would be an exported TradingView List of Trades from the creator configuration or equivalent exact chart-data export.

Do **not** optimize the indicator values, dates, or execution assumptions to force the creator headline.

## Current research gate

`SOURCE VERIFIED -> VIDEO PROPERTIES VERIFIED -> TRADE-GENERATION NEAR PARITY -> RETURN/PF PARITY UNRESOLVED`

The independent source/video-faithful engine is now frozen for backlog and post-creator OOS testing. Creator parity and independent OOS are tracked as separate questions.
