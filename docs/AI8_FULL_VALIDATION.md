# AI8 BTCUSDT — full backlog / OOS / robustness validation

## Status

**LONG-HISTORY + OOS EDGE VALIDATED / CREATOR RETURN NOT REPRODUCED / HIGH CREATOR-SIZING RISK / RECENT RECOVERY AFTER WEAK 12-MONTH REGIME**

This document refers to the independently reproducible Binance Spot AI8 reconstruction, not the creator's unreproduced +637.97% headline.

## Frozen baseline

- BTCUSDT spot, 2-hour bars
- Long only
- SuperTrend ATR 8, factor 1.6
- ADX 14 / 14, threshold >18
- Range Filter 175 / 5
- ATR stop length 50, multiplier 10
- fixed $80,000 cash per accepted entry on a $100,000 reference account
- pyramiding = 7
- 0.1% commission on each entry and exit
- 2 ticks slippage

No baseline strategy parameters were changed after examining OOS data.

## Windows

- Binance warmup history begins 2017-08-17
- pre-optimization backlog: 2018-03-01 to 2020-03-01
- creator window: 2020-03-01 to 2024-03-01
- untouched OOS: 2024-03-01 to 2026-09-15 end-exclusive
- OOS subperiods: 2024-03-01→2025-03-01, 2025-03-01→2026-03-01, and 2026-03-01→2026-09-15

## Baseline results

| Window | Trades | Net | PF | Win rate | Closed-trade DD | Intrabar stress DD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2018-03→2020-03 backlog | 145 | +219.67% | 1.522 | 44.83% | 78.51% | 112.45% |
| 2020-03→2024-03 creator window | 325 | +504.11% | 1.742 | 44.00% | 26.55% | 32.19% |
| 2024-03→2026-09 OOS | 208 | +112.52% | 1.319 | 43.27% | 67.28% | 87.51% |
| 2024-03→2025-03 | 80 | +48.14% | 1.344 | 43.75% | 67.28% | 87.51% |
| 2025-03→2026-03 | 85 | +31.33% | 1.179 | 37.65% | 43.56% | 43.93% |
| 2026-03→2026-09 | 41 | +26.80% | 1.716 | 51.22% | 19.22% | 24.48% |

The full OOS period is positive and PF remains above 1.0, but the path is not smooth. Creator-style sizing can hold up to seven $80K entries, so gross stacked notional can be very large relative to the $100K reference account. The >100% intrabar stress figure in the early backlog is a warning that the simple research backtester does not model margin liquidation and that the creator sizing should not be treated as a practical risk configuration.

## Cost stress

Combined 2x costs (0.2% commission per side + 4 ticks slippage):

- backlog: +196.16%, PF 1.452
- creator window: +451.50%, PF 1.638
- full 2024→2026 OOS: +79.08%, PF 1.213
- 2025-03→2026-03: +17.69%, PF 1.096
- 2026-03→2026-09: +20.20%, PF 1.497

The edge remains positive under the predeclared doubled-cost stress.

## Local-neighbour robustness

Fourteen strategy-parameter neighbour rows were tested without selecting a replacement parameter set.

- 14 / 14 remained positive over full 2024→2026 OOS.
- 14 / 14 retained PF >1 over full OOS.
- 12 / 14 were positive during 2026-03→2026-09.

The two recent-period failures were both Range Filter multiplier neighbours:

- multiplier 4.5: recent −10.62%, PF 0.807
- multiplier 5.5: recent −4.05%, PF 0.927

That means the broad OOS result is robust, while the latest recovery is somewhat sensitive to Range Filter exit behaviour.

## Year-by-year continuous baseline

| Year | Net | PF |
| --- | ---: | ---: |
| 2018 partial | −58.73% | 0.738 |
| 2019 | +234.81% | 2.299 |
| 2020 | +194.59% | 2.682 |
| 2021 | +152.01% | 1.657 |
| 2022 | −47.60% | 0.778 |
| 2023 | +149.22% | 2.150 |
| 2024 | +189.61% | 2.652 |
| 2025 | +51.65% | 1.331 |
| 2026 partial to Sep 15 | −7.65% | 0.910 |

Calendar 2026 remains slightly negative because January–February were weak, even though March→September recovered strongly.

## Rolling regime results

Complete rolling windows ending 2026-09-01:

- 6 months (2026-03-01→2026-09-01): **+30.69%, PF 1.821**
- 12 months (2025-09-01→2026-09-01): **−47.94%, PF 0.684**
- 24 months (2024-09-01→2026-09-01): **+172.44%, PF 1.687**

Across the historical monthly rolling sample:

- about 72.2% of 6-month windows were profitable
- about 90.1% of 12-month windows were profitable
- 100% of sampled 24-month windows were profitable

The latest complete 12-month window is therefore an unusually poor regime even though the last six months show a recovery.

## Continuous drawdown / streak state

From 2018-03-01 through 2026-09-15:

- 679 closed trades
- cumulative fixed-notional research P&L: +857.91% of the $100K reference capital
- PF 1.590
- maximum losing streak: 11 trades
- ending losing streak: 0
- current closed-trade drawdown from the last equity peak: 6.78%
- last closed-trade equity peak: 2025-10-07
- about 342 days underwater from that peak at the evaluation end
- historical maximum closed-trade DD: 78.51%

The strategy has recently recovered on a 6-month basis but has not yet recovered its October 2025 cumulative-equity peak.

## Decision

AI8 passes the core independent edge tests:

- pre-optimization backlog positive / PF >1
- untouched 2024→2026 OOS positive / PF >1
- doubled-cost OOS positive / PF >1
- all tested local neighbours positive over full OOS

However, it should **not** be promoted based on the creator's sizing or headline return. The creator return/PF remains unreproduced, creator-style pyramiding creates very high exposure, and the latest complete 12-month window was unusually poor.

Current research classification:

**VALIDATED SIGNAL EDGE / HIGH-RISK CREATOR SIZING / RECOVERING AFTER WEAK 12-MONTH REGIME / SHADOW-PAPER RESEARCH ONLY**

Do not retune AI8 against the 2025–2026 weak period. Preserve the frozen baseline for forward monitoring.
