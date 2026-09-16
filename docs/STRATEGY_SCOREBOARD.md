# Strategy Research Scoreboard

Updated: 2026-09-16 after the standardized 2016-or-earliest rebaseline.

This is the central comparison table for the Gold AI Strategy project. Returns are **not directly comparable across rows** because creator/reference position sizing differs by strategy. Profit factor, OOS direction, cost survival, robustness, regime consistency, drawdown, and the amount of independent non-optimization history matter more than the largest headline return.

No strategy is currently approved for live automated execution.

## Long-term objective

The project is searching for a strategy that can survive **5+ years across materially different market regimes** and can eventually be frozen into an automated research/paper script that produces daily results. The current phase is experimentation, validation, monitoring, and data collection only.

The common historical screen now targets **2016-01-01 to latest**, or the earliest trustworthy provider history when that market begins later. Reliable data before 2016 remains additional evidence rather than being discarded. See `docs/REBASELINE_2016.md` and `docs/LONG_TERM_RESEARCH_PLAN.md`.

## Current scoreboard

| Strategy | Market / TF | Current research class | Monitor | Standardized / deepest long-history evidence | Creator / reconstruction window | Post-creator OOS | Latest 6m | Latest 12m | Latest 24m | Cost / robustness evidence | Long-term readiness |
|---|---|---|---|---|---|---|---:|---:|---:|---|---|
| **AI8** | BTCUSDT 2H | **Long-history signal contender; current 12m weak; creator sizing high-risk** | Weekly | Earliest Binance 2017-08→2026-09: **+1024.26%, PF 1.614, 51.01% DD**; pre-creator **+386.02%, PF 1.606** | 2020-03→2024-03: **+504.11%, PF 1.742** | 2024-03→2026-09: **+112.52%, PF 1.319** | **+23.07%, PF 1.617** | **−50.14%, PF 0.665** | **+126.96%, PF 1.502** | full-history 2x costs **+908.09%, PF 1.524**; prior local OOS neighbours broadly passed | **Leading signal contender; ~$5k normalized full-history gate still required** |
| **AI2** | ETHUSDT 15m | **Historical signal contender; creator 4x sizing rejected; current 12m weak** | Weekly normalized | Earliest Binance 2017-08→2026-09: **+2429.14%, PF 1.552**, but **264.56% creator-size DD**; pre-creator **+624.41%, PF 1.360** | 2020-03→2024-03: **+1564.85%, PF 1.998**, near-exact parity | 2024-03→2026-09: **+233.28%, PF 1.213** at creator sizing; previously normalized OOS remained positive | **+15.76%, PF 1.092** | **−183.97%, PF 0.641** | **+235.05%, PF 1.263** | full-history 2x costs **+2106.33%, PF 1.458**, but creator-size DD **272.82%**; prior **12/12** OOS neighbours passed | **Signal merits continued study; practical status depends on standardized ~$5k/1x full-history test** |
| **AI38** | GBPUSD 4H | **2016+ watchlist; deeper-history conflict** | Weekly | 2016→2026-09: **+357.31%, PF 1.415, 49.83% DD**; 2016→2020 pre-creator **+85.96%, PF 1.248**; separately validated 2005→2020 backlog **−218.12%, PF 0.894** | 2020-03→2024-03: **+203.31%, PF 1.627** | 2024-03→2026-09: **+68.04%, PF 1.359** | **−23.98%, PF 0.480** | **+48.16%, PF 1.817** | **+74.24%, PF 1.559** | 2016+ full-history 2x costs **+247.41%, PF 1.263**; prior **20/20** local OOS neighbours passed | **Useful regime watchlist; pre-2016 failure prevents clean long-term promotion** |
| **AI58** | USDJPY 15m ORB | **Long-history signal contender; creator leverage rejected; recent 6m borderline** | Weekly | 2016→2026-09: **+400.33%, PF 1.438, 32.83% DD**; 2016→2021 pre-creator **+92.87%, PF 1.203**; older 2011+ evidence retained separately | 2021-09→2025-09: **+275.62%, PF 1.731** | 2025-09→2026-09: **+31.83%, PF 1.398** in standardized rebaseline | **+0.43%, PF 1.012** | **+38.38%, PF 1.522** | **+88.46%, PF 1.477** | full-history 2x costs **+309.58%, PF 1.321, 42.19% DD**; prior fresh-period neighbour tests showed regime weakness | **Leading signal contender; normalized ~$5k sizing gate still required** |
| **EXP6** | NQ 10m Triple MACD | **Frozen watchlist; 10-year coverage gate unmet** | Weekly | Current continuous public source only supports scored 2023→2025-10: **+221.36%, PF 1.412**, with 2023 PF <1 and fresh 2025 OOS negative; 2026 is a separate six-trade sample | early-2025 reconstruction **+36.22%, PF 1.296** | fresh Jun-Oct 2025 **−17.26%, PF 0.713**; separate May-Sep 2026 **+35.69%, PF 3.395** on 6 trades | n/a | n/a | n/a | 2025 neighbours **0/22** positive+PF>1; 2026 recovery **17/22** positive+PF>1 | **Does not pass long-history qualification; retain only as frozen prospective research** |
| **AI15** | ES 10m Simple Triple MA | Creator-window structurally reproduced; **long-history durability/small-account gate failed** | None | 2016→2026-06 **+313.16%, PF 1.077, 603.35% DD**; 2016→2020-05 **−403.75%, PF 0.792** | independent 2020-05→2024-05: **+577.68%, PF 1.405, 302 trades** vs creator **+566.98%, PF 1.403, 322 trades** | 2024-05→2026-06 **+155.03%, PF 1.230** | **−44.75%, PF 0.768** | **+6.08%, PF 1.019** | **+111.66%, PF 1.172** | full-history 2x costs **−185.93%, PF 0.957**; one-MES/$5k full history **+122.19%, PF 1.091, 154.03% DD**, 2x costs negative | **REJECT for 5+ year / small-account automation objective** |
| **AI65** | XAUUSD ORB | Replication/parity unresolved | None | No valid standardized long-history classification until replication/execution semantics are resolved | creator target about **+552.94%, PF 1.667, 670 trades** | Independent provider/execution work not yet sufficient | n/a | n/a | n/a | Not eligible for health monitoring until parity/replication gate is resolved | **Incomplete** |
| **AI1** | BTCUSDT 10m | Rejected | None | Existing backlog/OOS evidence already fails durability; no need to spend rebaseline resources before stronger candidates | 2020-03→2024-03 parity **+1868.66%, PF 1.593** | 2024-03→2026-09 **−455.61%, PF 0.798** at creator sizing | **−34.96%, PF 0.883** | **−80.75%, PF 0.892** | **−459.03%, PF 0.735** | 2x costs worsened failure; every predeclared OOS neighbour negative/PF<1 | **REJECT — preserve as failed research record** |

## Small-account lens

The eventual research target is a starting account around **$5,000**, growing over time. Creator leverage/notional is therefore never treated as the deployment requirement. Every serious contender must receive a normalized small-account feasibility test covering position granularity, transaction-cost drag, drawdown, turnover and whether the signal remains useful without extreme leverage.

The 2016-or-earliest rebaseline makes the next priority clearer:

- **AI8:** signal-level history is strong, but the creator pyramids fixed $80k entries and that sizing is not the eventual model.
- **AI2:** creator 4x fixed notional creates modeled drawdown above initial capital; only normalized sizing can remain under consideration.
- **AI58:** standardized history is comparatively consistent, but creator notional is $70k on $10k capital and must be replaced by a feasible frozen sizing layer.
- **AI38:** can be included as a secondary comparison, but its older 2005-2020 failure remains a major durability warning.

## Monitoring set

The active frozen monitoring set remains:

- AI2 — normalized 1x shadow health
- AI8 — normalized pyramiding health
- AI38 — normalized GBPUSD regime health
- AI58 — frozen USDJPY ORB regime health
- EXP6 — frozen NQ shadow health

AI1 and AI15 are rejected for the current long-term objective and do not consume recurring monitoring resources. AI65 does not get a monitor until its independent replication gate is resolved.

The rebaseline does **not** change monitor parameters or use monitor outcomes to retune a strategy. Exact rolling-health figures can differ slightly from the standardized table because health monitors use their own predeclared boundary dates/continuous-state methodology.

## Interpretation rules

1. A large creator-window return is not a score by itself.
2. Untouched OOS and non-optimization history matter more than optimized history.
3. Profit factor and robustness must survive realistic costs.
4. The default long-history target is 2016 to the latest reliable data, or the earliest trustworthy history available when 2016 coverage does not exist. Reliable earlier data is retained as additional evidence.
5. A long-term candidate should remain viable across multiple calendar years and rolling 6m/12m/24m/36m/60m windows.
6. Failed OOS or failed long-history evidence is never repaired by retuning against the failed window.
7. Creator leverage is separated from signal quality; practical promotion requires a feasible ~$5k sizing test.
8. Monitoring collects prospective evidence; it is not permission to place live trades.
