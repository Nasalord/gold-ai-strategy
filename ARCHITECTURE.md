# Architecture

## Validation flow

```text
Creator source / market data
            ↓
      Source reconstruction
            ↓
        Creator parity
            ↓
   Frozen-parameter backlog
            ↓
     Untouched OOS tests
            ↓
 Cost / neighbour / regime stress
            ↓
 PASS / WATCHLIST / REJECT
            ↓
   Frozen paper/shadow monitor
```

## Execution policy

The scientific checks stay comprehensive, but GitHub Actions are deliberately staged:

```text
L0 local/dev iterations
        ↓
L1 lean deterministic CI
        ↓
L2 deliberate full experiment validation
        ↓
L3 scheduled frozen monitoring
```

Heavy validation does not run on every push. Relevant edits are batched, obsolete runs are cancelled, experiment workflows are path-scoped, and frozen monitors run on their research cadence rather than on ordinary code changes. See `docs/ACTIONS_USAGE_POLICY.md`.

This public repository contains research/backtest/paper-monitoring code only.
