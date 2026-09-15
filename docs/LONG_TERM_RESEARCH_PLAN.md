# Long-Term Research Plan

## Objective

Find one or more systematic strategies that remain economically viable over **5+ years and multiple market regimes**, then graduate only the strongest frozen candidate into an automated research/paper system that can run on a daily schedule and report results without manual intervention.

The current project phase is **experimentation and evidence collection**. It is not a live-trading deployment project.

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

- **at least 5 years of independent non-optimization evidence in total** when data permits;
- evidence spans materially different volatility/trend regimes rather than one unusually favorable period;
- at least 24 months of untouched post-source OOS before any automation promotion, with the long-run target being 5 years of frozen OOS/forward evidence;
- full-history and major subperiod PF remain economically credible rather than being carried by one exceptional year;
- realistic cost stress remains viable;
- nearby predeclared parameter variants show broad rather than point-fragile behavior;
- risk is assessed at normalized research sizing, separately from creator leverage;
- no unresolved source/parity issue is large enough to invalidate the comparison.

The 5-year rule is a **minimum evidence horizon**, not a guarantee that a strategy is safe or durable.

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
4. define OOS, cost, robustness, and regime checks before reading their outcome;
5. run one deliberate full validation pass;
6. classify as reject, unresolved, watchlist, or validated-signal contender;
7. monitor only strategies whose evidence justifies consuming ongoing resources;
8. record the result in `docs/STRATEGY_SCOREBOARD.md`.

## GitHub Actions discipline

Validation depth is never reduced to save runner usage. Instead:

- intermediate development stays local/dev where practical;
- related edits are batched;
- routine CI stays lean;
- heavyweight validation runs deliberately at milestones;
- frozen health monitoring runs weekly during the research phase unless a strategy's information cadence genuinely requires more frequent checks;
- future daily automation is reserved for a strategy that has passed the long-term qualification gate.

This keeps the research rigorous while preventing repeated runs from consuming the available Actions budget without adding new information.
