# Stage 3B — $5,000 small-account feasibility

Date: 2026-09-16

## Purpose

This is the project-wide **Stage 3B small-account feasibility** test for the frozen long-history contenders. It asks whether the unchanged signals remain economically usable when the creator's large fixed notionals are removed and the strategy is forced into a roughly $5,000 account with no borrowing.

This is still research/backtest/paper evidence only. It is not live-trading authorization.

## Predeclared sizing framework

The signal, indicator, entry and exit parameters are unchanged. Only the deployment sizing layer changes.

- starting equity: **$5,000**;
- gross entry notional may not exceed current realized equity;
- no borrowing / no creator leverage;
- AI8 keeps its seven-leg pyramiding semantics, but each new leg receives only **1/7 of current realized equity**, so the seven requested legs together stay within the 1x cap;
- AI2 uses at most current realized equity in its single ETH position;
- AI58 rounds USD base notional down to **1,000-unit** increments and caps it at current realized equity;
- AI38 is a secondary comparison and rounds GBP base units down to **1,000-unit** increments so USD entry notional stays below current realized equity;
- research granularity assumptions: **0.0001 BTC**, **0.001 ETH**, **1,000 FX base units**, and a **$10 crypto research minimum notional**;
- creator/reference transaction costs remain in the baseline and a **2x-cost** stress is run separately;
- the long-history horizon remains 2016-to-latest or earliest trustworthy provider history when later.

The quantity increments are conservative reproducible **research assumptions**, not claims about the exact current minimum size of a particular broker or exchange.

## Full-history Stage 3B results

| Strategy | Coverage | Stage 3B class | Ending equity | Net % | CAGR % | PF | Closed DD % | Minimum equity |
|---|---|---|---:|---:|---:|---:|---:|---:|
| **AI8** | 2017-08→2026-09 | `PASS_STAGE_3B_RESEARCH_GATE` | **$22,295.23** | **+345.90%** | **17.89%** | **1.475** | **33.82%** | **$4,793.80** |
| **AI2** | 2017-08→2026-09 | `WATCHLIST_DRAWDOWN_HIGH` | **$150,680.58** | **+2913.61%** | **45.50%** | **1.189** | **60.50%** | **$1,974.85** |
| **AI58** | 2016-01→2026-09 | `PASS_STAGE_3B_RESEARCH_GATE` | **$8,223.29** | **+64.47%** | **4.76%** | **1.425** | **7.52%** | **$4,872.46** |
| **AI38** | 2016-01→2026-09 | `PASS_STAGE_3B_RESEARCH_GATE` mechanically | **$6,242.93** | **+24.86%** | **2.10%** | **1.404** | **4.73%** | **$4,854.98** |

AI38's mechanical Stage 3B pass does **not** supersede its separately validated 2005-2020 backlog failure. Its overall project status therefore remains a secondary watchlist / regime comparison rather than a clean long-term contender.

## 2x transaction-cost stress

| Strategy | Ending equity | Net % | CAGR % | PF | Closed DD % | Minimum equity |
|---|---:|---:|---:|---:|---:|---:|
| **AI8** | **$18,169.08** | **+263.38%** | **15.27%** | **1.387** | **35.20%** | **$4,788.51** |
| **AI2** | **$67,691.63** | **+1253.83%** | **33.23%** | **1.137** | **61.40%** | **$1,930.22** |
| **AI58** | **$7,105.17** | **+42.10%** | **3.34%** | **1.289** | **8.75%** | **$4,855.56** |
| **AI38** | **$5,881.76** | **+17.64%** | **1.53%** | **1.268** | **5.81%** | **$4,791.87** |

All four 2016/earliest-history small-account paths remain positive with PF above 1 under the doubled-cost stress. That does not make their economic quality equivalent: drawdown, regime consistency, turnover and absolute growth remain materially different.

## Pre-creator / creator / post-creator small-account windows

Each window starts a fresh $5,000 sizing simulation while retaining the continuous frozen signal path from the underlying engine.

| Strategy | Pre-creator | Creator window | Post-creator OOS |
|---|---|---|---|
| **AI8** | **+66.71%, PF 1.416, DD 33.82%** | **+119.20%, PF 1.660, DD 20.51%** | **+17.38%, PF 1.248, DD 16.62%** |
| **AI2** | **+37.49%, PF 1.098, DD 60.50%** | **+1756.06%, PF 1.461, DD 42.20%** | **+15.66%, PF 1.042, DD 57.04%** |
| **AI58** | **+11.67%, PF 1.181, DD 7.52%** | **+41.33%, PF 1.661, DD 6.44%** | **+2.68%, PF 1.244, DD 1.88%** |
| **AI38** | **+4.37%, PF 1.195, DD 4.73%** | **+14.72%, PF 1.644, DD 2.77%** | **+4.20%, PF 1.357, DD 2.51%** |

AI2's aggregate growth remains large even after removing creator leverage, but its edge becomes much less convincing outside the optimized window: pre-creator PF is only 1.098 and post-creator PF only 1.042, with roughly 60% and 57% closed-trade drawdowns respectively.

## Latest rolling windows at the $5k sizing layer

| Strategy | 6m | 12m | 24m | 36m | 60m |
|---|---|---|---|---|---|
| **AI8** | **+4.02%, PF 1.594** | **−8.90%, PF 0.643** | **+21.32%, PF 1.391** | **+55.50%, PF 1.560** | **+90.32%, PF 1.453** |
| **AI2** | **−0.65%, PF 0.984** | **−41.39%, PF 0.557** | **+22.48%, PF 1.065** | **+125.16%, PF 1.166** | **+70.45%, PF 1.090** |
| **AI58** | **−0.87%, PF 0.827** | **+4.48%, PF 1.427** | **+11.37%, PF 1.433** | **+14.93%, PF 1.380** | **+47.00%, PF 1.599** |
| **AI38** | **−0.65%, PF 0.670** | **+2.89%, PF 1.817** | **+5.20%, PF 1.634** | **+2.97%, PF 1.206** | **+18.17%, PF 1.646** |

The recent weak-regime signal is still visible after normalized sizing. Sizing does not repair a signal regime: AI8 still has a weak latest 12 months, AI2 remains weak in both 6m and 12m, AI58's latest 6m is mildly negative, and AI38's latest 6m is negative.

## Turnover and cost footprint

The full-history simulator also records total entry notional and commissions relative to the original $5,000 starting balance. Because the account compounds, these ratios are **not** annual expense ratios and should not be interpreted that way; they are cumulative activity diagnostics.

| Strategy | Entry-notional turnover / initial $5k | Baseline commission / initial $5k |
|---|---:|---:|
| **AI8** | **274.45x** | **55.29%** |
| **AI2** | **5903.21x** | **1184.74%** |
| **AI58** | **563.40x** | **3.94%** |
| **AI38** | **240.27x** | **1.86%** |

AI2 is the clear turnover outlier. The cumulative commission figure is enormous relative to the original account because the strategy compounds to a much larger balance and repeatedly turns over the account. The 2x-cost run remains profitable, but the combination of high turnover, low post-creator PF and high drawdown keeps it on the watchlist rather than promoting it.

## Research interpretation

### AI8

**Passes the predeclared Stage 3B research gate.** The signal remains positive from earliest Binance history through 2026 at a 1x no-borrowing sizing layer, survives doubled costs, does not breach starting equity, and keeps post-creator OOS positive. The trade-off is a still-material **33.82%** full-history closed-trade drawdown and a currently weak **12-month** regime.

### AI2

**Does not receive a clean Stage 3B pass.** Removing creator leverage prevents the >100% creator-size drawdown, but the normalized path still reaches **60.50%** closed-trade drawdown. Pre-creator and post-creator PFs are only **1.098** and **1.042**, and the latest 12 months are **−41.39% / PF 0.557**. It remains a signal-research watchlist candidate rather than a practical lead candidate.

### AI58

**Passes the predeclared Stage 3B research gate.** It has the lowest drawdown among the primary contenders (**7.52%**), positive pre-creator / creator / post-creator windows, and survives doubled costs. Its limitation is economic speed: the 1x no-borrowing full-history result compounds at only about **4.76% CAGR**, and the latest six months are mildly negative.

### AI38

The 2016+ small-account layer is mechanically clean, with low drawdown and doubled-cost survival, but the return is modest (**~2.10% CAGR**) and the older 2005-2020 frozen backlog already failed. The Stage 3B sizing result therefore does not change AI38's overall status as a **secondary regime/watchlist comparison**.

## Resulting project state

Under this exact predeclared Stage 3B framework:

- **AI8 — Stage 3B research gate PASS.**
- **AI58 — Stage 3B research gate PASS.**
- **AI2 — WATCHLIST because normalized drawdown remains high and recent/OOS edge is thin.**
- **AI38 — mechanical 2016+ sizing pass, but overall long-term status remains WATCHLIST because deeper history failed.**

The next research step for AI8 and AI58 is not to retune them. Their signal parameters remain frozen while forward/shadow evidence accumulates. AI2 and AI38 remain useful comparisons but should not be upgraded from this test alone.

## Limitations

- drawdown is closed-trade equity drawdown, not full intrabar mark-to-market drawdown;
- the research quantity increments are deliberately conservative but are not broker/exchange-specific live specifications;
- crypto and FX execution quality, spread and minimum-size rules can vary by venue and time;
- this sizing layer uses realized-equity caps and does not model margin borrowing;
- a passing research gate is not evidence that future returns will match the backtest and is not permission for live trading.
