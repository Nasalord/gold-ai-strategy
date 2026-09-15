# Gold AI Strategy

A public, paper-first research repository for systematic strategy reconstruction, creator-parity testing, untouched out-of-sample validation, cost stress, local-neighbour robustness, regime analysis, and frozen health monitoring.

## Long-term objective

The project is trying to identify a strategy that remains economically viable over **5+ years and multiple market regimes**. Only after a candidate survives that evidence-gathering process should it graduate into an automated research/paper system that can run on a daily schedule and produce daily results.

The eventual deployment research is intended to be compatible with a **small starting account around $5,000**, so creator leverage/notional is always separated from signal quality. Small-account feasibility is tested independently rather than assuming the creator's position size is usable.

Right now the project is in the **experiment, validation, and data-collection phase**. No strategy in this repository is approved for live automated execution.

See `docs/LONG_TERM_RESEARCH_PLAN.md` for the promotion ladder and `docs/STRATEGY_SCOREBOARD.md` for the current cross-strategy comparison.

## Research rules

- Reconstruct the creator/source rules before judging performance.
- Require creator parity or label parity unresolved.
- Freeze parameters before untouched OOS testing.
- Include realistic transaction costs and slippage.
- Use predeclared robustness checks; never retune to rescue failed OOS.
- Separate signal quality from creator leverage/position sizing.
- Test practical small-account sizing separately from creator headline sizing.
- Research/backtest/paper-monitoring only; no live broker routing.

## Included experiments

AI1, AI2, AI8, AI15, AI38, AI58, AI65, and Experiment #6 (Triple MACD NQ), including strategy engines, source-fidelity/parity tooling, validation scripts, regression tests, documentation, and GitHub Actions workflows.

Experiment #6 is **research-phase complete and parameter-frozen** with a final classification of **WATCHLIST / SHADOW-PAPER RESEARCH ONLY**. See `docs/EXP6_TRIPLE_MACD_NQ.md`.

AI15 Simple Triple MA is now under active research. Its source reconstruction and short independent 2026 public sample are implemented, including doubled-cost and one-MES/$5k paper sensitivity cases. Long-history ES parity and 5+ year qualification are still pending. See `docs/AI15_SIMPLE_TRIPLE_MA.md`.

The active frozen monitoring set is AI2, AI8, AI38, AI58, and EXP6. AI1 is rejected and is not monitored. AI15 and AI65 do not receive health monitors yet because their independent long-history/replication gates are still incomplete.

## Validation execution

The project keeps full validation depth while limiting duplicate GitHub Actions execution. Routine development uses lean CI, heavyweight experiment validation is deliberate, and the current long-horizon frozen monitors run weekly plus manual-on-demand rather than on ordinary pushes/PR edits. See `docs/ACTIONS_USAGE_POLICY.md` and `ARCHITECTURE.md`.

## Privacy boundary

This public snapshot intentionally excludes personal portfolio balances, brokerage account identifiers, credentials, tokens, cookies, private market-data databases, private execution records, and the private repository's historical commits/issues/PRs.

## Important

Historical and simulated results do not guarantee future performance. Read each strategy's documentation and parity limitations before interpreting results.
