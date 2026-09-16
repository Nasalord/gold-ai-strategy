# AI8 + AI58 frozen $5,000 portfolio

Date: 2026-09-16

## Purpose

This experiment tests whether the two strategies that passed the project's Stage 3B small-account research gate — **AI8 BTCUSDT 2H** and **AI58 USDJPY 15m ORB** — provide useful diversification when combined inside one $5,000 research portfolio.

This is still backtest / research / paper evidence only. It does not add live order routing.

## Predeclared design

The strategy signals, indicators, entries and exits remain completely frozen. Only the portfolio allocation layer is being studied.

- total starting equity: **$5,000**;
- common-history start: **2017-08-17**, because that is the earliest trustworthy AI8/Binance history available in this project;
- end: **2026-09-16 exclusive**;
- primary allocation: **50% AI8 / 50% AI58**;
- diagnostic allocation neighbours: **75/25** and **25/75**;
- same-period controls: **100% AI8** and **100% AI58**;
- no borrowing and no cross-sleeve borrowing;
- no periodic rebalancing: the two sleeves compound independently after the initial split;
- AI8 keeps its Stage 3B rule of spreading its 1x sleeve cap across seven possible pyramid legs;
- AI58 keeps its Stage 3B 1,000-unit USD-base sizing granularity and 1x sleeve cap;
- baseline creator/reference costs plus a separate **2x-cost stress**;
- combined drawdown is measured from realized closed-trade portfolio equity, grouping same-timestamp exits before calculating drawdown.

The 50/50 portfolio is the primary experiment. The neighbouring allocations are diagnostics only and are not permitted to replace 50/50 merely because one happens to look better after the test.

## Full common-history results

| Initial allocation | Ending equity | Net % | CAGR % | PF | Closed DD % |
|---|---:|---:|---:|---:|---:|
| 100% AI8 | **$22,295.23** | **+345.90** | **17.89** | **1.475** | **33.12** |
| 75% AI8 / 25% AI58 | **$18,460.89** | **+269.22** | **15.47** | **1.475** | **26.89** |
| **50% AI8 / 50% AI58** | **$14,849.04** | **+196.98** | **12.73** | **1.474** | **20.29** |
| 25% AI8 / 75% AI58 | **$11,290.77** | **+125.82** | **9.38** | **1.478** | **12.25** |
| 100% AI58 | **$7,686.77** | **+53.74** | **4.85** | **1.453** | **6.50** |

The primary 50/50 portfolio compounds $5,000 to about **$14.85k** over the common history. Its closed-trade drawdown is **20.29%**, substantially below the same-period AI8-only control's **33.12%**, while its CAGR remains **12.73%** versus 17.89% for AI8 alone.

This is the expected diversification trade-off: lower historical growth than the aggressive AI8 sleeve, but materially less drawdown.

## 2x transaction-cost stress

| Initial allocation | Ending equity | Net % | CAGR % | PF | Closed DD % |
|---|---:|---:|---:|---:|---:|
| 100% AI8 | **$18,169.08** | **+263.38** | **15.27** | **1.387** | **34.62** |
| 75% AI8 / 25% AI58 | **$15,259.35** | **+205.19** | **13.07** | **1.386** | **28.31** |
| **50% AI8 / 50% AI58** | **$12,430.68** | **+148.61** | **10.55** | **1.380** | **20.67** |
| 25% AI8 / 75% AI58 | **$9,687.17** | **+93.74** | **7.55** | **1.374** | **12.60** |
| 100% AI58 | **$6,971.07** | **+39.42** | **3.73** | **1.347** | **6.56** |

The primary 50/50 portfolio remains profitable under doubled costs, with **PF 1.380**, about **10.55% CAGR**, and **20.67%** closed-trade drawdown.

## Diversification evidence

For the primary 50/50 sleeves, monthly realized-return correlation is only **0.026**, which is very close to zero in this historical sample.

Across the common monthly history:

- both sleeves were negative in **22 months**;
- AI8 was negative while AI58 was positive in **32 months**;
- AI58 was negative while AI8 was positive in **27 months**.

That offsetting behavior is consistent with the reduction in combined drawdown. It is not proof that future correlation will remain low.

The 50/50 portfolio's worst closed-trade drawdown ran from approximately **2017-12-13 to 2018-03-29** and reached **20.29%**.

## Rolling 50/50 windows

Each rolling window starts a fresh $5,000 50/50 simulation using the same frozen strategy logic.

| Window | Net % | CAGR % | PF | DD % |
|---|---:|---:|---:|---:|
| 6m | **+1.77** | **3.55** | **1.322** | **1.93** |
| 12m | **−2.46** | **−2.46** | **0.851** | **7.79** |
| 24m | **+15.43** | **7.44** | **1.409** | **8.73** |
| 36m | **+34.10** | **10.27** | **1.522** | **9.60** |
| 60m | **+65.31** | **10.58** | **1.489** | **10.21** |

The latest 12 months remain weak. Combining the strategies reduces the severity of AI8's current weak regime, but it does not make the weak period disappear. That is important: diversification is reducing risk, not repairing a failing signal window.

## Calendar-year 50/50 behavior

| Year | Net % | PF | DD % |
|---:|---:|---:|---:|
| 2017 partial | +26.39 | 3.623 | 3.14 |
| 2018 | **−12.93** | **0.581** | 15.55 |
| 2019 | +21.12 | 1.770 | 8.04 |
| 2020 | +18.03 | 2.110 | 3.93 |
| 2021 | +16.17 | 1.618 | 5.62 |
| 2022 | +2.18 | 1.096 | 6.78 |
| 2023 | +12.10 | 1.636 | 3.00 |
| 2024 | +22.88 | 2.363 | 5.65 |
| 2025 | +3.41 | 1.158 | 6.78 |
| 2026 to Sep 16 | **−0.02** | **0.998** | 3.81 |

The portfolio still has losing/flat regimes. The evidence does not support treating diversification as a guarantee of positive yearly returns.

## Interpretation

**The frozen 50/50 AI8 + AI58 portfolio is a promising portfolio-level research candidate.** On the common historical window it preserved a double-digit CAGR while reducing closed-trade drawdown materially versus AI8 alone, retained PF well above 1, and survived doubled costs.

The evidence also explains *why* the combination helps: historical monthly sleeve returns were nearly uncorrelated, and there were many months where one sleeve was positive while the other was negative.

However:

- the latest 12-month 50/50 window is negative with PF below 1;
- AI8 and AI58 can both lose at the same time;
- no-rebalance static sleeves gradually drift toward the strategy that compounds faster;
- drawdown here is closed-trade realized equity rather than full mark-to-market intrabar equity;
- the common history starts in 2017 rather than 2016 because of AI8 data availability;
- the test does not justify changing either strategy's frozen parameters.

## Research state

**`PORTFOLIO WATCHLIST / PROSPECTIVE PAPER RESEARCH`**

The 50/50 combination has enough historical evidence to keep studying prospectively, but it is not a live-deployment decision. AI8 and AI58 should continue to be monitored individually, and portfolio-level forward evidence can be accumulated without retuning either strategy or the 50/50 allocation.

## Implementation

- `scripts/run_ai8_ai58_portfolio.py`
- `.github/workflows/ai8_ai58_portfolio.yml`

The workflow is deliberate/manual or explicit-PR only. It is not a recurring daily workflow during the experimentation phase.
