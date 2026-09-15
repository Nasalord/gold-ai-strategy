# AI1 — SSL + T3 with ADX/EMA — BTCUSDT 10m

**Status: SOURCE VERIFIED / CREATOR PARITY PASSED / LONG-TERM OOS FAILED — REJECT**

Research/backtest/paper only. No live execution.

## Frozen creator setup

- BTCUSDT, 10-minute
- SSL period 140
- T3 fast 40 / slow 90, b=0.7
- ADX smoothing 100 / DI length 110
- EMA of ADX 80
- ATR 120
- stop 10x ATR / target 20x ATR
- long + short, one position at a time
- $10,000 reference capital
- fixed $100,000 notional per trade (creator 10x sizing)
- 0.1% commission per side
- 2 ticks slippage

## Creator parity

Creator target, 2020-03-01 to 2024-03-01:
- 455 trades
- +1863% net
- PF 1.59
- 34.07% win rate
- 24.42% TradingView max DD

Independent Binance Spot 5m -> 10m reconstruction:
- **455 trades**
- **+1868.66% net**
- **PF 1.59285**
- **34.0659% win rate**
- 228 long / 227 short
- 387 signal exits / 64 targets / 4 stops
- closed-trade DD approximation 19.15%

Trade generation and headline performance reproduce essentially exactly without parameter tuning. The DD difference is metric-methodology related; the independent engine currently reports closed-trade equity DD rather than TradingView's full intrabar/open-equity drawdown measure.

## Long-history validation

### Pre-optimization backlog — 2018-03-01 to 2020-03-01

- 187 trades
- **+78.75%** at creator sizing
- **PF 1.0533**
- 32.62% win rate
- closed-trade DD 92.23%

The backlog is only marginally profitable on PF and already shows extreme risk under creator sizing.

### Untouched OOS — 2024-03-01 to 2026-09-15

- 307 trades
- **-455.61%** at creator sizing
- **PF 0.7980**
- 28.01% win rate
- 148 long / 159 short

Subperiods:
- 2024-03 -> 2025-03: **-256.90%, PF 0.7593**
- 2025-03 -> 2026-03: **-163.76%, PF 0.8161**
- 2026-03 -> 2026-09: **-34.96%, PF 0.8825**

The backtester does not model margin liquidation. Returns below -100% at creator sizing therefore mean the 10x research configuration is economically non-viable, not that an account could actually continue trading unchanged.

At a 1x fixed-notional normalization, P&L magnitude scales down materially, but the OOS signal economics do not improve: PF remains below 1. The full 2018-2026 normalized history is positive only because the very strong 2020-2024 optimization window dominates the combined sample.

## Robustness

Combined 2x costs (0.2% each side + 4 ticks) worsen full OOS to **-1069.76%, PF 0.6051** at creator sizing.

Every predeclared local indicator neighbor tested over full OOS was also negative and PF < 1:
- SSL 120 / 160
- T3 fast 35 / 45
- T3 slow 80 / 100
- ADX smoothing 80 / 120
- DI 100 / 120
- ADX EMA 60 / 100
- ATR length 100 / 140

This broad failure argues against rescuing AI1 by changing one nearby input.

## Regime history

Calendar-year creator-sized P&L/PF:
- 2018 partial: -1.79%, PF 0.997
- 2019: -30.22%, PF 0.963
- 2020: +845.76%, PF 2.233
- 2021: +718.19%, PF 1.718
- 2022: +86.70%, PF 1.096
- 2023: +164.10%, PF 1.297
- 2024: -18.40%, PF 0.980
- 2025: -307.06%, PF 0.680
- 2026 partial: +34.51%, PF 1.079

Latest rolling windows through 2026-09-15:
- 6m: **-34.96%, PF 0.883**
- 12m: **-80.75%, PF 0.892**
- 24m: **-459.03%, PF 0.735**

## Decision

AI1 is **not promoted to shadow monitoring**. It is preserved as a research rejection:

`SOURCE VERIFIED -> CREATOR PARITY PASSED -> BACKLOG WEAK -> OOS FAILED -> REJECT`

Do not retune the strategy using the failed 2024-2026 OOS period; doing so would contaminate the independent test and invite overfitting.
