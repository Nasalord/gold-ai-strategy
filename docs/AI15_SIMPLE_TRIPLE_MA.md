# AI15 — Simple Triple MA on ES1! 10m

**Research state:** `COMPLETE UNDER CURRENT FROZEN MODEL / LONG-TERM GATE FAILED`

**Current classification:** **REJECT FOR 5+ YEAR / SMALL-ACCOUNT AUTOMATION OBJECTIVE.** Preserve as a research record; do not retune the frozen baseline to rescue the failed early-history or cost-stress results.

**Deployment state:** research / backtest / paper only. No live order routing.

## Why AI15 was tested

AI15 is a deliberately simple trend/momentum strategy from the creator spreadsheet. The project tested it because simple moving-average trend logic is easier to audit for overfitting than highly parameterized indicator stacks and because the project is looking for a strategy that can survive from 2016 onward, across different regimes, before any later daily automation layer is considered.

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

The source code defines a long signal when MA A crosses above MA B while both are above MA C. The market entry is generated on the signal bar and, under Pine's default historical strategy behavior, is filled at the next bar open. Stop and target prices are calculated from the signal close using that bar's ATR.

The Pine source and narration contain one ambiguity. The Pine variables for stop and target are reassigned on every later valid signal even when pyramiding prevents another entry, while the narration says exit levels do not update while already in a trade. The project treats the **source-code behavior as the parity baseline** and keeps the narrated no-update interpretation as a declared diagnostic variant.

## Creator-reported benchmark

Optimization window: **2020-05-01 through 2024-05-01**.

| Metric | Creator / spreadsheet |
|---|---:|
| Trades | 322 |
| Net profit | +566.98% |
| Profit factor | 1.403 |
| Win rate | 60.87% |
| Max drawdown | 25.39% |

The creator also reported a post-optimization check beginning 2024-05-01 with roughly 44 trades, +65% net profit, PF ~1.5 and ~32% max drawdown at the time of the video. Those are creator-reported figures, not independent results.

## Independent short 2026 check

The first independent check used the public `getdata-finance/es-1m-ohlcv-stocks-historical-data` sample, pinned to commit `0908875a9f414e56c1d5117166965b21175774ed`. April 2026 was warmup only and scoring began 2026-05-01.

| Case | Trades | Win % | Net % | PF | Closed-trade DD % |
|---|---:|---:|---:|---:|---:|
| Creator ES semantics | 15 | 40.00 | +79.53 | 1.449 | 63.38 |
| Narrated no-update variant | 14 | 42.86 | +82.27 | 1.472 | 62.55 |
| Creator semantics / 2× costs | 15 | 40.00 | +74.85 | 1.414 | 64.59 |
| One MES / $5k paper sensitivity | 15 | 40.00 | +51.94 | 1.437 | 51.34 |
| One MES / $5k / 2× costs | 15 | 40.00 | +47.74 | 1.392 | 52.56 |

That short sample was encouraging but far too small for the project's durability requirement.

## Independent 2016-present long-history test

The standardized long-history run uses public yearly ES one-minute files from `worldtradingchampion-source/btcdata`, pinned to immutable commit `40d6a1052fa6c90be2156f23c6ef91f888f28945`.

- 2015 is warmup only.
- Scored history begins **2016-01-01 America/New_York**.
- Source coverage used ends **2026-06-11**.
- The source is already stitched across quarterly contracts and includes a contract-symbol column.
- The runner records symbol transitions and never combines two contract symbols inside one 10-minute bar.
- It does **not** invent a back-adjustment. Exact TradingView ES1! parity therefore remains dependent on provider and roll methodology.

### Frozen baseline windows

| Window | Trades | Net % | PF | Win % | Closed DD % |
|---|---:|---:|---:|---:|---:|
| **2016 → 2026-06** | **798** | **+313.16** | **1.077** | **58.90** | **603.35** |
| **Pre-creator: 2016 → 2020-05** | **334** | **−403.75** | **0.792** | **57.19** | **603.35** |
| **Creator window: 2020-05 → 2024-05** | **302** | **+577.68** | **1.405** | **60.60** | **44.43** |
| **Post-creator OOS: 2024-05 → 2026-06** | **161** | **+155.03** | **1.230** | **59.63** | **59.89** |

Creator-window structural reproduction is strong: 302 vs 322 trades, +577.68% vs +566.98% net, PF 1.405 vs 1.403 and 60.60% vs 60.87% win rate. The drawdown does **not** match closely: independent closed-trade DD is 44.43% versus the creator-reported 25.39%, so exact platform/provider parity is not claimed.

The critical result is the pre-creator history. The same frozen rules lose **−403.75% of the stated $100k initial-capital baseline with PF 0.792** from 2016 through April 2020. Because the backtest's creator sizing can drive modeled equity below zero, later gains do not make that path economically survivable.

### Calendar-year regimes

| Year | Trades | Net % | PF | Win % | DD % |
|---:|---:|---:|---:|---:|---:|
| 2016 | 77 | −116.01 | 0.745 | 54.55 | 175.07 |
| 2017 | 76 | +26.53 | 1.152 | 65.79 | 33.36 |
| 2018 | 76 | −206.74 | 0.611 | 47.37 | 228.34 |
| 2019 | 77 | +10.86 | 1.034 | 61.04 | 64.70 |
| 2020 | 74 | +5.98 | 1.008 | 62.16 | 260.67 |
| 2021 | 76 | +59.27 | 1.188 | 56.58 | 39.89 |
| 2022 | 77 | +185.96 | 1.394 | 58.44 | 46.36 |
| 2023 | 76 | +166.37 | 1.604 | 64.47 | 23.30 |
| 2024 | 78 | +120.10 | 1.420 | 60.26 | 39.00 |
| 2025 | 74 | +73.04 | 1.221 | 59.46 | 102.39 |
| 2026 through Jun 11 | 36 | −28.58 | 0.831 | 55.56 | 79.73 |

The history is strongly regime-dependent. Two early years fail badly and the 2026 portion is negative again.

### Rolling windows ending at the source's last bar

| Window | Trades | Net % | PF | Win % | DD % |
|---|---:|---:|---:|---:|---:|
| 6m | 39 | **−44.75** | **0.768** | 53.85 | 90.86 |
| 12m | 77 | +6.08 | 1.019 | 58.44 | 63.15 |
| 24m | 150 | +111.66 | 1.172 | 59.33 | 71.39 |
| 36m | 226 | +219.38 | 1.237 | 59.73 | 49.30 |
| 60m | 385 | +522.50 | 1.304 | 59.74 | 47.28 |

The recent six-month window is currently weak despite strong 36- and 60-month totals.

## Cost stress

| Window | Net % | PF | DD % |
|---|---:|---:|---:|
| Full 2016-present / **2× costs** | **−185.93** | **0.957** | **893.35** |
| Creator window / 2× costs | +425.20 | 1.282 | 46.73 |
| Post-creator OOS / 2× costs | +103.06 | 1.146 | 67.30 |

The full-history edge does **not** survive the doubled-cost stress. That is a long-term qualification failure even though the creator and recent OOS windows remain profitable.

## ~$5k small-account paper sensitivity

The creator's $1.25M order-cash setting is parity-only. Small-account research uses one MES contract with a $5/point multiplier and a modeled $5,000 starting balance.

| Window | Net % | PF | DD % |
|---|---:|---:|---:|
| One MES / $5k / full history | +122.19 | 1.091 | **154.03** |
| One MES / $5k / post-creator OOS | +66.64 | 1.170 | 45.30 |
| One MES / $5k / full history / 2× costs | **−82.65** | **0.943** | **239.19** |
| One MES / $5k / OOS / 2× costs | +25.64 | 1.062 | 51.97 |

Even one MES produces modeled full-history drawdown greater than the starting account balance, and doubled costs turn the full-history result negative. This fails the project's small-account feasibility gate.

## Predeclared local robustness

Twelve one-factor neighbours were declared before reading the long-history result: MA-A 30/40, MA-B 135/165, MA-C 90/110, ATR 18/22, stop 7.5/9.5 ATR and target 5.5/7.5 ATR.

- Full-history profitable + PF > 1: **12/12**.
- Post-creator OOS profitable + PF > 1: **12/12**.

This shows the recent/aggregate behavior is not confined to one exact parameter point, but it does not override the baseline's early-history ruin-level path or the full-history cost-stress failure. Neighbours are diagnostic only and may not replace the frozen baseline.

## Final classification

**`REJECT FOR LONG-TERM / SMALL-ACCOUNT AUTOMATION OBJECTIVE`**

Reasons:

- creator-window structural parity is good enough to make the comparison meaningful;
- post-creator OOS is profitable and local-neighbour breadth is strong;
- however, the pre-creator 2016–2020 period is deeply negative with PF < 1;
- creator sizing produces modeled drawdown far beyond starting equity;
- one-MES/$5k sizing still exceeds starting equity in full-history drawdown;
- full-history 2× costs fall below PF 1 and become negative;
- the latest six-month window is weak again.

AI15 therefore does **not** receive a recurring monitor. It remains in the public repository as a reproducible failed long-term research record. The frozen baseline should not be retuned against these results.

## Validation implementation

- `ai_investing_lab/strategies/ai15_triple_ma/`
- `tests/test_ai15_triple_ma.py`
- `scripts/run_ai15_public_2026.py`
- `scripts/run_ai15_long_history.py`
- `.github/workflows/ai15_validation.yml`
- `.github/workflows/ai15_long_history.yml`
