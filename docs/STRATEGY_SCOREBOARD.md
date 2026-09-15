# Strategy Research Scoreboard

Updated: 2026-09-15/16 research snapshot.

This is the central comparison table for the Gold AI Strategy project. Returns are **not directly comparable across rows** because creator/reference position sizing differs by strategy. Profit factor, OOS direction, cost survival, robustness, regime consistency, and the amount of independent non-optimization history matter more than the largest headline return.

No strategy is currently approved for live automated execution.

## Long-term objective

The project is searching for a strategy that can survive **5+ years across materially different market regimes** and can eventually be frozen into an automated research/paper script that produces daily results. The current phase is experimentation, validation, monitoring, and data collection only.

A strategy cannot become an automation candidate merely because its creator window or one recent period is profitable. See `docs/LONG_TERM_RESEARCH_PLAN.md`.

## Current scoreboard

| Strategy | Market / TF | Current research class | Monitor | Creator / reconstruction window | Independent non-optimization evidence | Latest 6m | Latest 12m | Latest 24m | Robustness / cost evidence | Long-term readiness |
|---|---|---|---|---|---|---:|---:|---:|---|---|
| **AI8** | BTCUSDT 2H | Validated signal edge; creator sizing high-risk; recovering after weak 12m | Weekly | 2020-03→2024-03: **+504.11%, PF 1.742** independent reconstruction | 2018-03→2020-03 backlog **+219.67%, PF 1.522**; 2024-03→2026-09 OOS **+112.52%, PF 1.319** | **+30.69%, PF 1.821** | **−47.94%, PF 0.684** | **+172.44%, PF 1.687** | 2x-cost full OOS **+79.08%, PF 1.213**; **14/14** local neighbours positive/PF>1 full OOS | **Strongest current contender, but not automation-ready** |
| **AI2** | ETHUSDT 15m | Signal validated historically; creator 4x sizing rejected; current structural concern | Weekly | 2020-03→2024-03: **+1564.85%, PF 1.998**, near-exact parity | 2017-08→2020-03 backlog **+624.41%, PF 1.360** but ruin-level creator-size DD; normalized 2024-03→2026-09 OOS **+58.32%, PF 1.213** | **+3.94%, PF 1.092** | **−48.75%, PF 0.628** | **+55.89%, PF 1.247** | 2x costs remained positive in frozen OOS; **12/12** local neighbours positive/PF>1 full OOS | **Contender under structural watch; no promotion while 12m health is broken** |
| **AI38** | GBPUSD 4H | Recent-regime OOS edge; deep backlog failed; latest 6m weak | Weekly | 2020-03→2024-03 midpoint: **+203.31%, PF 1.627** | 2005-01→2020-03 backlog **−218.12%, PF 0.894**; 2024-03→2026-09 OOS **+68.04%, PF 1.359** | **−23.98%, PF 0.480** | **+48.16%, PF 1.817** | **+74.24%, PF 1.559** | 2x-cost full OOS **+41.4%, PF 1.199**; **20/20** local neighbours positive/PF>1 full OOS | **Watchlist; long-history failure prevents long-term promotion** |
| **AI58** | USDJPY 15m ORB | Creator/video parity passed; fresh post-video OOS failed | Weekly | 2021-09→2025-09: **+271.95%, PF 1.719** independent midpoint parity | 2025-09→2026-03 **+39.54%, PF 2.016**; fresh 2026-03→2026-09 **−8.76%, PF 0.795**; combined OOS **+27.49%, PF 1.340** | **−8.01%, PF 0.808** | **+29.93%, PF 1.385** | **+80.01%, PF 1.422** | historical 2x-cost / local robustness passed; fresh weakness persisted across nearby variants | **Watchlist; weak but within historical tolerance** |
| **EXP6** | NQ 10m Triple MACD | Frozen watchlist / shadow-paper only | Weekly | early-2025 reconstruction **+36.22%, PF 1.296** vs creator structural target | 2023 **−10.93%, PF 0.948**; 2024 **+159.75%, PF 2.028**; fresh Jun-Oct 2025 **−17.26%, PF 0.713**; May-Sep 2026 **+35.69%, PF 3.395** on only 6 trades | n/a | n/a | n/a | 2025 neighbours **0/22** positive+PF>1; 2026 recovery **17/22** positive+PF>1 | **Early watchlist; sample and history are too short/inconsistent** |
| **AI15** | ES 10m Simple Triple MA | Creator-window structurally reproduced; **long-history durability/small-account gate failed** | None | independent 2020-05→2024-05: **+577.68%, PF 1.405, 302 trades** vs creator **+566.98%, PF 1.403, 322 trades** | 2016→2020-05 **−403.75%, PF 0.792**; 2024-05→2026-06 OOS **+155.03%, PF 1.230**; full 2016→2026-06 **+313.16%, PF 1.077, 603.35% DD** | **−44.75%, PF 0.768** | **+6.08%, PF 1.019** | **+111.66%, PF 1.172** | full-history 2x costs **−185.93%, PF 0.957**; **12/12** neighbours positive/PF>1 full and OOS; one-MES/$5k full history **+122.19%, PF 1.091, 154.03% DD**, 2x costs **−82.65%, PF 0.943** | **REJECT for 5+ year / small-account automation objective** |
| **AI65** | XAUUSD ORB | Replication/parity unresolved | None | creator target about **+552.94%, PF 1.667, 670 trades** | Independent provider/execution work not yet sufficient for a frozen long-term judgment | n/a | n/a | n/a | Not eligible for health monitoring until parity/replication gate is resolved | **Incomplete** |
| **AI1** | BTCUSDT 10m | Rejected | None | 2020-03→2024-03 parity **+1868.66%, PF 1.593** | 2018-03→2020-03 backlog only **+78.75%, PF 1.053**; 2024-03→2026-09 OOS **−455.61%, PF 0.798** at creator sizing | **−34.96%, PF 0.883** | **−80.75%, PF 0.892** | **−459.03%, PF 0.735** | 2x costs worsened failure; every predeclared OOS neighbour negative/PF<1 | **REJECT — preserve as failed research record** |

## Small-account lens

The eventual starting account is expected to be around **$5,000**, then grow over time. Creator leverage/notional is therefore never treated as the deployment requirement. Every serious contender should eventually receive a normalized small-account feasibility test covering position granularity, transaction-cost drag, drawdown, turnover and whether the signal remains useful without extreme leverage.

AI15 demonstrates why this is separate from signal parity. Its creator-window reconstruction is very close to the published headline, and even one MES remains profitable over the aggregate 2016-present sample. But the modeled one-MES/$5k full-history drawdown reaches **154.03%** and doubled costs turn that full-history result negative. That is a failure of the project's practical small-account gate even though some recent windows are profitable.

## Monitoring set

The active frozen monitoring set is:

- AI2 — normalized 1x shadow health
- AI8 — normalized pyramiding health
- AI38 — normalized GBPUSD regime health
- AI58 — frozen USDJPY ORB regime health
- EXP6 — frozen NQ shadow health

AI1 and AI15 are rejected for the current long-term objective and should not consume recurring monitoring resources. AI65 does not get a monitor until its independent replication gate is resolved.

## Interpretation rules

1. A large creator-window return is not a score by itself.
2. Untouched OOS and non-optimization backlog matter more than optimized history.
3. Profit factor and robustness must survive realistic costs.
4. The default long-history target is 2016 to the latest reliable data, or the earliest trustworthy history available when 2016 coverage does not exist.
5. A long-term candidate should remain viable across multiple calendar years and rolling 6m/12m/24m/36m/60m windows.
6. Failed OOS or failed long-history evidence is never repaired by retuning against the failed window.
7. Monitoring collects prospective evidence; it is not permission to place live trades.
