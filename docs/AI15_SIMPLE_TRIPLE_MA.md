# AI15 — Simple Triple MA on ES1! 10m

**Research state:** source reconstruction implemented; short independent 2026 sample passed directionally; independent long-history parity still pending.

**Deployment state:** research / backtest / paper only. No live order routing.

## Why AI15 is being tested

AI15 is a deliberately simple trend/momentum strategy from the creator spreadsheet. The project is testing it because simple moving-average trend logic is easier to audit for overfitting than highly parameterized indicator stacks, and because the long-term project goal is a strategy that can survive 5+ years and eventually be automated for daily research reporting.

## Source material

- Creator row: AI15 / Simple Triple MA Strategy / ES1! / 10-minute.
- Video: `https://www.youtube.com/watch?v=hxNbhkuffGg`
- Public Pine source: `https://drive.google.com/file/d/1KesZR2KFGfjQjIxjHqEGSFzu-Dw1LTIc/view?usp=sharing`

The downloadable Pine file contains generic defaults. The video instructs users to manually change those inputs for the ES1! optimization. The research code therefore preserves **two separate presets** rather than silently treating the Pine defaults as the ES optimization.

## Frozen ES1! video preset

| Field | ES1! 10m value |
|---|---:|
| Direction | Long only |
| Price source | Low |
| MA A | TMA 35 |
| MA B | EMA 150 |
| MA C | SMA 100 |
| ATR length | 20 |
| Stop | 8.5 × ATR |
| Target | 6.5 × ATR |
| Initial capital | $100,000 |
| Order cash | $1,250,000 |
| ES multiplier | $50 / index point |
| ES tick | 0.25 index point |
| Commission | $2 / contract / filled order |
| Slippage | 5 ticks |

The generic downloadable Pine defaults are TMA(2), EMA(3), SMA(375), ATR(100), SL 10.5 ATR and TP 30 ATR. Those values are **not** the ES optimization used for creator parity.

## Entry and exit semantics

The source code defines a long signal when:

1. MA A crosses above MA B;
2. MA A is above MA C; and
3. MA B is above MA C.

The market entry is generated on the signal bar and, under Pine's default historical strategy behavior, is filled at the next bar open. Stop and target prices are calculated from the **signal close** using that bar's ATR.

The Pine source and the narration contain one important ambiguity. The Pine variables for stop and target are reassigned on every later valid signal, even when pyramiding prevents another entry, so the source code can modify an existing position's exit levels. The video narration says the stop/target levels do not update while already in a trade. The project treats the **source-code behavior as the parity baseline** and reports the narrated no-update interpretation as a predeclared diagnostic variant.

## Creator-reported benchmark

Optimization window: **2020-05-01 through 2024-05-01**.

| Metric | Creator / spreadsheet |
|---|---:|
| Trades | 322 |
| Net profit | +566.98% |
| Profit factor | 1.403 |
| Win rate | 60.87% |
| Max drawdown | 25.39% |

The creator also reported a post-optimization check beginning 2024-05-01 with roughly **44 trades, +65% net profit, PF ~1.5 and ~32% max drawdown** at the time of the video. That is creator-reported OOS evidence, not an independent result.

## Independent public 2026 sample

The first independent check uses the public `getdata-finance/es-1m-ohlcv-stocks-historical-data` sample, pinned to commit `0908875a9f414e56c1d5117166965b21175774ed` for reproducibility. The file contains 55,440 one-minute rows from 2026-04-01 through 2026-09-02; it is resampled to 5,614 ten-minute bars. April is warmup only and scoring begins 2026-05-01.

| Case | Trades | Win % | Net % | PF | Closed-trade DD % |
|---|---:|---:|---:|---:|---:|
| Creator ES semantics / source-code exit updates | 15 | 40.00 | **+79.53** | **1.449** | **63.38** |
| Narrated no-update exit variant | 14 | 42.86 | **+82.27** | **1.472** | **62.55** |
| Creator ES semantics / 2× costs | 15 | 40.00 | **+74.85** | **1.414** | **64.59** |
| One MES / $5k paper sensitivity | 15 | 40.00 | **+51.94** | **1.437** | **51.34** |
| One MES / $5k paper / 2× costs | 15 | 40.00 | **+47.74** | **1.392** | **52.56** |

The short sample is directionally encouraging: profitability survives doubled costs and the source-vs-narration ambiguity does not materially change the conclusion in this window. However, **14–15 trades is far too small for long-term qualification**, and the drawdown is very large at both creator and one-MES/$5k paper sizing. This result is evidence to continue researching AI15, not evidence to promote it.

## Small-account research boundary

The eventual project account is expected to begin around **$5,000**. The creator's $1.25M order-cash setting is therefore treated strictly as a parity/reconstruction setting, not as a deployment plan.

The public runner includes a **one-MES, $5k paper sensitivity case** using the exact same ES signal rules with the Micro E-mini $5/point multiplier. This is only to separate signal behavior from the creator's aggressive sizing. It does not assume a broker margin requirement or imply that a $5k live futures account is appropriate.

The 2026 one-MES sensitivity still produced roughly **51% closed-trade drawdown**, so even the micro-sized version is not yet compatible with the project's long-term small-account risk objective. Future research must investigate whether the underlying signal is durable before any separate position-sizing/risk layer is considered.

## Independent data plan

The public 2026 sample is **not sufficient for the project's 5+ year qualification requirement**. Creator-window parity and long-term qualification still require a continuous historical ES dataset spanning at least 2020-present, with an explicit and reproducible contract-roll method. No parameter changes are allowed after reading those future results.

The next AI15 milestone is therefore an independently constructed long-history ES series with a frozen roll convention, followed by creator-window parity, pre-optimization backlog where available, untouched post-2024 OOS, calendar-year regimes, rolling windows, doubled-cost stress and predeclared local-neighbour robustness.

## Validation ladder

1. deterministic unit tests for source parameters, MA construction, next-bar fills, costs and futures sizing — **complete**;
2. independent 2026 public sample under source-code semantics — **complete**;
3. predeclared narration-ambiguity variant — **complete**;
4. 2× execution-cost stress on the public sample — **complete**;
5. normalized one-MES / $5k paper sensitivity — **complete**;
6. obtain independent continuous ES history and test 2020-2024 creator parity — **next**;
7. test pre-2020 backlog where data permits;
8. test untouched 2024-present OOS, calendar regimes and rolling 6m/12m/24m/36m/60m windows;
9. predeclared local-neighbour robustness without rescuing failures by retuning;
10. only then decide reject / unresolved / watchlist / validated-signal contender.

No AI15 health monitor should be created until the long-history/parity gate is far enough along to justify recurring Actions usage.
