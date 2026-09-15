# Long-Term Research Plan

## Objective

Find one or more systematic strategies that remain economically viable over **5+ years and multiple market regimes**, then graduate only the strongest frozen candidate into an automated research/paper system that can run on a daily schedule and report results without manual intervention.

The eventual practical research target is a **small starting account around $5,000**, growing over time. Creator leverage, notional and headline returns are therefore separated from signal quality. Any serious contender must later pass a small-account feasibility layer covering position granularity, realistic costs, turnover and drawdown without relying on extreme leverage.

The current project phase is **experimentation and evidence collection**. It is not a live-trading deployment project.

## Default historical test horizon

For every strategy, the project will target **January 1, 2016 through the latest trustworthy data available** as the standard long-history evaluation horizon.

Rules:

- if reliable data is available from 2016, use the full 2016-to-present history rather than selecting a shorter favorable window;
- if the available dataset starts later than 2016, use the **earliest reliable date actually available** and clearly report the missing-history limitation;
- if a trustworthy dataset extends earlier than 2016, retain that earlier history as an additional deep-history/backlog test rather than discarding it;
- creator optimization/parity windows are still reproduced separately inside the larger historical record;
- untouched post-creator OOS remains separately reported even when it is included in the full 2016-to-present run;
- calendar-year and rolling-window results must be reported so one unusually strong period cannot hide weak regimes;
- no strategy may have its historical start date moved forward after results are observed merely to improve its reported performance.

This is the default for new experiments and should also be applied retrospectively to existing strategies whenever suitable data can be obtained.

## Promotion ladder

### Stage 0 — source reconstruction

- recover the creator/source rules exactly enough to implement them deterministically;
- reproduce execution semantics, costs, sizing, session rules, and provider assumptions;
- label unresolved parity honestly instead of tuning until a headline matches.

### Stage 1 — deterministic validation

- regression tests for signals and execution mechanics;
- creator/source parity or a clearly documented structural-parity limitation;
- realistic commission, slippage, and instrument specifications.

### Stage 2 — independent non-optimization evidence

Use data that was not the basis for the creator's optimization whenever possible:

- pre-optimization backlog;
- untouched post-creator OOS;
- calendar-year regime splits;
- rolling windows;
- doubled-cost stress;
- predeclared local-neighbour robustness.

No OOS failure may be repaired by selecting a nearby parameter after seeing the failure.

### Stage 3 — long-term qualification

A strategy becomes a serious long-term contender only when the evidence supports all of the following:

- the standard historical evaluation targets **2016-to-present** whenever trustworthy data permits;
- **at least 5 years of independent non-optimization evidence in total** when data permits;
- evidence spans materially different volatility/trend regimes rather than one unusually favorable period;
- at least 24 months of untouched post-source OOS before any automation promotion, with the long-run target being 5 years of frozen OOS/forward evidence;
- full-history and major subperiod PF remain economically credible rather than being carried by one exceptional year;
- realistic cost stress remains viable;
- nearby predeclared parameter variants show broad rather than point-fragile behavior;
- risk is assessed at normalized research sizing, separately from creator leverage;
- no unresolved source/parity issue is large enough to invalidate the comparison.

The 5-year rule is a **minimum evidence horizon**, not a guarantee that a strategy is safe or durable.

### Stage 3B — small-account feasibility

Before a long-term contender can be considered for the eventual automation layer, test the frozen signal under account-size constraints that are relevant to the project rather than the creator's headline sizing.

At minimum record:

- a paper baseline around the project's ~$5,000 starting size;
- the smallest practical instrument/position granularity available for the market being studied;
- commission, spread/slippage and turnover as a percentage of account size;
- drawdown depth and duration at the normalized position size;
- whether reasonable sizing is possible without hidden leverage assumptions;
- whether the signal still has economic value after it is scaled down.

This stage is a feasibility test, not permission to trade. A strategy may have a statistically interesting signal and still be unsuitable for a small account.

### Stage 4 — prospective shadow/paper monitoring

Once parameters are frozen, continue collecting forward evidence without retuning.

The monitor should track at minimum:

- 6-month return and PF;
- 12-month return and PF;
- 24-month return and PF;
- calendar YTD;
- current and historical drawdown depth/duration;
- losing streak state;
- data freshness;
- transaction-cost sensitivity.

As enough forward history accumulates, add rolling **36-month and 60-month** windows so the monitoring itself directly measures the 5+ year objective.

### Stage 5 — automated daily research system

Only after a candidate survives the earlier stages should we build the eventual daily automation layer.

That future system should:

1. ingest fresh market data;
2. validate data quality/freshness;
3. run the frozen strategy without changing parameters;
4. update simulated positions and paper P&L;
5. compute daily, rolling, and long-horizon health statistics;
6. produce a concise daily report/dashboard;
7. alert on structural deterioration or broken data/execution assumptions;
8. retain a reproducible audit trail of every signal and result.

Daily reporting does **not** imply live order placement. Live execution, if ever considered, is a separate later gate and is outside the current public research workflow.

## Experiment discipline

For each new experiment:

1. define the source and frozen candidate rules;
2. implement and regression-test locally;
3. establish parity/structural fidelity;
4. acquire the longest trustworthy history available, targeting 2016-to-present;
5. define OOS, cost, robustness, and regime checks before reading their outcome;
6. run one deliberate full validation pass;
7. classify as reject, unresolved, watchlist, or validated-signal contender;
8. monitor only strategies whose evidence justifies consuming ongoing resources;
9. record the result in `docs/STRATEGY_SCOREBOARD.md`.

## GitHub Actions discipline

Validation depth is never reduced to save runner usage. Instead:

- intermediate development stays local/dev where practical;
- related edits are batched;
- routine CI stays lean;
- heavyweight validation runs deliberately at milestones;
- frozen health monitoring runs weekly during the research phase unless a strategy's information cadence genuinely requires more frequent checks;
- future daily automation is reserved for a strategy that has passed the long-term qualification gate.

This keeps the research rigorous while preventing repeated runs from consuming the available Actions budget without adding new information.
