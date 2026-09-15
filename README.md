# Gold AI Strategy

A public, paper-first research repository for systematic strategy reconstruction, backtesting, out-of-sample validation, robustness testing, and frozen health monitoring.

## Research principles

- Reconstruct creator/source rules before judging performance.
- Require creator-parity or clearly label unresolved parity.
- Freeze parameters before untouched out-of-sample testing.
- Include realistic commissions, spread/slippage, and cost stress.
- Run predeclared local-neighbour robustness tests rather than post-hoc rescue tuning.
- Separate signal quality from leverage/position-sizing risk.
- Keep all broker-facing work paper/read-only unless explicitly redesigned and reviewed.

## Current strategy research

The repository contains frozen research implementations and validation tooling for AI1, AI2, AI8, AI38, AI58, AI65, and the Triple MACD NQ experiment, together with supporting data fetchers, diagnostics, tests, and GitHub Actions workflows.

## Public-repo privacy boundary

This public repository intentionally contains **no personal portfolio balance, brokerage account identifier, credential, token, cookie, private market-data database, or private execution record**. Example portfolio values are synthetic research defaults only.

## Important

This project is for research, backtesting, and paper/simulated monitoring. Historical results do not guarantee future performance. Strategy implementations can contain modeling assumptions or source-parity limitations; read the corresponding documentation before interpreting results.
