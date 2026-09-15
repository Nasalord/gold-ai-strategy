# AI2 — Simple Triple MA Strategy — ETHUSDT 15m

**Final research status:** `SOURCE VERIFIED / CREATOR PARITY PASSED / SIGNAL EDGE VALIDATED / CREATOR 4x SIZING REJECTED / CURRENT EDGE WEAKENED / NORMALIZED SHADOW-PAPER ONLY`

This strategy is retained for research and shadow-paper monitoring only. The creator's fixed 4x cash sizing is not accepted as a viable risk profile.

## Source

- Creator video: `https://www.youtube.com/watch?v=by1eLmmAsTI`
- Supplied Pine v5 source: `18 - Triple Moving Average Strategy .txt`
- Ranking ID: **AI2**

## Frozen creator configuration

| Parameter | Frozen value |
| --- | ---: |
| Market | ETHUSDT spot |
| Timeframe | 15 minutes |
| Direction | Long only |
| MA A | TMA(2) on low |
| MA B | EMA(3) on low |
| Trend MA C | SMA(375) on low |
| ATR length | 100 |
| Stop | 10.5 × ATR below signal close |
| Target | 30 × ATR above signal close |
| Initial capital | $10,000 |
| Fixed cash order | $40,000 |
| Creator leverage at inception | 4x |
| Commission | 0.1% per filled side |
| Slippage | 2 ticks |
| Minimum tick modeled | $0.01 |

### Literal Pine semantics preserved

A long signal occurs when TMA(2) crosses above EMA(3) and both are above SMA(375). The market entry is created at the signal-bar close and fills at the next bar open under TradingView's default order processing.

The Pine source stores stop and target in persistent variables. Every new valid long signal recalculates those values even when a long is already open and pyramiding prevents another same-direction entry. Therefore the stop can move **down** as well as up. The emulator preserves this unusual behavior because changing it would break source parity.

## Creator benchmark — 2020-03-01 to 2024-03-01

| Metric | Creator | Independent | Difference |
| --- | ---: | ---: | ---: |
| Closed trades | 179 | **179** | **0** |
| Net profit | +1561.38% | **+1564.85%** | +3.47 pp |
| Profit factor | 1.993 | **1.9976** | +0.0046 |
| Win rate | 39.66% | **39.6648%** | +0.0048 pp |
| Creator-reported max DD | 27.33% | 23.38% closed-trade DD | not directly comparable |

**Parity verdict: PASS.** Trade count and win rate are effectively exact, while net return and profit factor are extremely close. The drawdown difference is expected because the independent headline metric here is closed-trade equity drawdown rather than TradingView's full intratrade equity-drawdown calculation.

## Pre-optimization backlog — 2017-08-17 to 2020-03-01

At the creator's fixed $40,000 cash order size:

- 102 trades
- +624.41% net profit
- PF 1.3600
- 38.24% win rate
- **264.56% closed-trade drawdown**

The positive return/PF before the optimized creator window is evidence that the signal was not created solely by the 2020-2024 optimization period. However, the historical drawdown is ruin-level at the creator's 4x sizing. This is why the signal and the sizing are classified separately.

## Untouched OOS — 2024-03-01 to 2026-09-15

### Creator 4x sizing

- 105 trades
- **+233.28%**
- **PF 1.2131**
- 35.24% win rate
- **64.96% closed-trade DD**

### Normalized 1x research sizing

- 105 trades
- **+58.32%**
- **PF 1.2131**
- 35.24% win rate
- **36.11% closed-trade DD**

The normalized run preserves the signal and trade sequence while reducing cash exposure from $40,000 to $10,000 per trade on the $10,000 reference account. It is the sizing used for ongoing shadow monitoring.

### 2x execution-cost stress

Using 0.2% commission per filled side and 4 ticks of slippage while leaving all signal parameters unchanged:

- 105 trades
- **+148.32%** at creator cash sizing
- **PF 1.1290**
- 32.38% win rate

The signal remains positive under doubled modeled costs, although the margin of safety compresses substantially.

## OOS subperiods — creator cash sizing

| Window | Trades | Net | PF | Win rate |
| --- | ---: | ---: | ---: | ---: |
| 2024-03 → 2025-03 | 37 | +175.81% | 1.5361 | 43.24% |
| 2025-03 → 2026-03 | 42 | +28.06% | 1.0486 | 30.95% |
| 2026-03 → 2026-09-15 | 26 | +29.41% | 1.1552 | 30.77% |

All major OOS splits remain profitable with PF > 1, but the edge weakened sharply after the first OOS year.

## Calendar-year regime view — creator cash sizing

| Exit year | Trades | Net | PF |
| --- | ---: | ---: | ---: |
| 2017 | 16 | -38.72% | 0.917 |
| 2018 | 37 | +56.94% | 1.092 |
| 2019 | 44 | +346.60% | 1.580 |
| 2020 | 41 | +720.14% | 3.048 |
| 2021 | 40 | +796.26% | 2.784 |
| 2022 | 46 | -8.64% | 0.981 |
| 2023 | 53 | +125.45% | 1.356 |
| 2024 | 33 | +451.48% | 2.976 |
| 2025 | 43 | +6.71% | 1.0115 |
| 2026 YTD through Sep 14 | 33 | **-33.68%** | **0.886** |

The strategy is clearly regime dependent. Its strongest periods were 2020, 2021, and 2024. Calendar 2025 was barely above breakeven, and 2026 YTD is currently below PF 1 even though the Mar-Sep 2026 subwindow recovered.

## Buy-and-hold comparison

Independent ETHUSDT buy-and-hold change over the same start/end windows:

- creator window: +1437.16%
- pre-optimization backlog: -27.87%
- fresh OOS: **-24.68%**

The strategy remained net positive over the fresh OOS window while ETH's simple start-to-end buy-and-hold return was negative.

## Local parameter robustness

Twelve one-factor neighbours were declared before reviewing their results. **12/12** remained profitable with PF > 1 over the full fresh OOS window.

| Neighbour | OOS net | PF |
| --- | ---: | ---: |
| TMA length 1 | +126.48% | 1.1066 |
| TMA length 3 | +60.93% | 1.0504 |
| EMA length 2 | +76.06% | 1.0615 |
| EMA length 4 | +81.81% | 1.0683 |
| SMA length 325 | +209.71% | 1.1812 |
| SMA length 425 | +242.47% | 1.2242 |
| ATR length 80 | +271.44% | 1.2482 |
| ATR length 120 | +214.89% | 1.1948 |
| Stop 8.5 ATR | +19.33% | 1.0151 |
| Stop 12.5 ATR | +400.68% | 1.4404 |
| Target 25 ATR | +219.50% | 1.1945 |
| Target 35 ATR | +240.25% | 1.2195 |

These are robustness diagnostics only. None of these values may replace the frozen creator settings because of OOS performance.

## Decision

### Signal

**Validated enough for continued shadow-paper research.** Evidence includes near-exact creator parity, profitable pre-optimization history, profitable full fresh OOS, survival under 2x modeled costs, positive OOS subperiods, and 12/12 positive local neighbours.

### Position sizing

**Creator 4x sizing rejected.** Historical drawdowns are large enough to invalidate that exposure profile for this research program. Ongoing monitoring uses normalized 1x cash exposure only.

### Current regime

**Weak / recovering, not healthy by default.** Calendar 2026 remains negative through September 14 even though the Mar-Sep subwindow is positive. No parameter may be changed to improve this recent period.

## Research-only rules

- Parameters remain frozen.
- No result observed after the OOS cutoff can be used to retune the strategy.
- The normalized shadow monitor is evidence collection, not a trading instruction.
- No live orders are placed by this strategy research workflow.
