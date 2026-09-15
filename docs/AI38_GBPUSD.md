# AI38 — Double EMA + Momentum, GBPUSD 4H

## Current status

**SOURCE VERIFIED / CREATOR STRUCTURE SUBSTANTIALLY REPRODUCED / OOS ROBUST / DEEP BACKLOG FAILED / CURRENT 6M WEAK — WATCHLIST ONLY**

Research/backtest/paper only. No live execution.

## Frozen optimized source

- GBPUSD 4H
- EMA fast/slow: 21 / 50
- Momentum A/B: 110 / 30
- Risk/reward: 2.4
- Stop: 3-bar candle low/high
- Both directions, one trade at a time
- EMA growth check: fast 21 bars / 30%, slow 6 bars / 35%
- Literal Pine `Both` gate preserved as `long_growth OR short_growth`
- $10,000 reference capital
- 100,000 GBP units per trade
- commission $0.00005 per contract per side
- slippage 20 ticks (GBPUSD min tick 0.00001)

## Creator parity

Creator benchmark, 2020-03-01 to 2024-03-01:
- 94 trades
- +217.06%
- PF 1.845
- 39.36% win rate
- 19.56% TradingView max DD

Independent Dukascopy structural match at UTC+2 4H alignment:
- bid: 94 trades, +240.49%, PF 1.761, 42.55% win
- midpoint: 96 trades, +203.31%, PF 1.627, 40.63% win
- ask: 94 trades, +119.67%, PF 1.352, 38.30% win

Midpoint UTC+2 is the neutral primary research feed. No strategy parameter was changed to fit the creator benchmark.

## Deep-history validation

Primary feed: Dukascopy midpoint, UTC+2 4H alignment.

### Pre-optimization backlog: 2005-01-01 to 2020-03-01
- 388 trades
- -218.12%
- PF 0.8935
- win rate 28.87%
- closed-trade DD 321.61% in the no-liquidation creator-sized research model

The negative backlog is not a feed-selection artifact: all 12 bid/ask/mid x 4H-alignment diagnostics were negative with PF <1 over the backlog.

### Creator window: 2020-03-01 to 2024-03-01
- 96 trades
- +203.31%
- PF 1.6265
- win rate 40.63%

### Untouched OOS: 2024-03-01 to 2026-09-15
- 64 trades
- +68.04%
- PF 1.3588
- win rate 40.63%
- closed-trade DD 34.19%

OOS splits:
- 2024-03 to 2025-03: +17.89%, PF 1.229
- 2025-03 to 2026-03: +34.60%, PF 1.440
- 2026-03 to 2026-09: -25.97%, PF 0.547

Rolling windows ending 2026-09-15:
- 6m: -23.98%, PF 0.480
- 12m: +48.16%, PF 1.817
- 24m: +74.24%, PF 1.559

## Robustness

Combined 2x costs (commission doubled and slippage 40 ticks):
- full OOS: +41.4%, PF 1.199
- latest 6m: -28.4%, PF 0.428

All 20/20 predeclared local parameter neighbours remained profitable with PF >1 over the full 2024-2026 OOS window. No neighbour was selected as a replacement configuration.

The old backlog remains weak across almost every neighbour; only Momentum-B 25/35 controls were marginally positive over the backlog, and they were not adopted because doing so after seeing history would be selection bias.

## Forward health monitoring

AI38 now has an automated shadow-paper health monitor in `.github/workflows/ai38_health_monitor.yml`.

The monitor:
- keeps every source signal and execution parameter frozen;
- uses the same neutral Dukascopy midpoint / UTC+2 4H alignment as validation;
- compares trailing 6m, 12m and 24m performance against permanently frozen historical distributions;
- tracks current drawdown depth/duration and ending losing streak;
- raises a GitHub issue only if the state reaches `HIGH RISK / DORMANT` or `STRUCTURAL CONCERN`;
- never retunes the strategy from forward results.

Health-reference thresholds are frozen from the successful recent-regime history ending **2026-03-15**, before the subsequently observed weak six-month period. The failed 2005-2020 backlog is retained as a permanent structural caveat and is deliberately not used to loosen the monitor's health thresholds.

For drawdown-health classification, the monitor uses the existing normalized **10,000 GBP units per trade** research size rather than the creator's 100,000-unit position. Signal timing, costs, win rate and profit factor remain unchanged by that scaling.

## Interpretation

AI38 has a credible recent-regime edge: creator-window structure substantially reproduces, untouched OOS is positive, double-cost OOS is positive, and local-neighbour OOS robustness is broad. However, the 2005-2020 pre-optimization history is negative and the latest six months are currently weak.

This is therefore not promoted as a long-history universal edge. Keep the source parameters frozen and treat it as a watchlist/shadow-paper research candidate. Do not retune it on the 2005-2020 failure, the 2026 weakness, or future monitor output.
