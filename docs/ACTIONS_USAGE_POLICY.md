# GitHub Actions usage policy

The research standard is not reduced to save runner time. The project reduces **duplicate execution**, not validation depth.

## Four execution levels

### L0 — development

Use local/dev execution for coding, diagnostics, exploratory analysis, and repeated intermediate checks. These iterations should not create GitHub Actions runs.

### L1 — lean CI

Run the small deterministic regression suite on relevant pull requests and merges only. CI should use path filters, one Python version, sensible timeouts, and `concurrency.cancel-in-progress: true` so obsolete runs are cancelled.

### L2 — full experiment validation

Run creator/source parity, untouched OOS, execution-cost stress, predeclared local robustness, regime analysis, and frozen-result fingerprint checks deliberately when an experiment reaches a validation milestone.

Heavy validation must not run on every push. Prefer `workflow_dispatch` or another explicit review gate. When practical, keep the checks in one runner/job so checkout and environment setup are paid once.

### L3 — frozen monitoring

Once an experiment is frozen, scheduled shadow/paper monitoring continues at the frequency justified by the strategy. Monitoring workflows should not also trigger on ordinary source pushes.

## Development rules

- Batch related edits before opening or updating a validation PR.
- Do not rerun a successful heavy suite because of documentation-only changes.
- Use path filters so unrelated experiments do not run.
- Use concurrency cancellation for superseded PR or monitor runs.
- Re-run failed jobs only when possible instead of restarting successful work.
- Keep artifacts only as long as they remain useful for review.
- Record runner usage after major experiments so future workflow design is based on measured cost.
- Preserve the full scientific validation package; never remove OOS, robustness, cost, parity, or monitoring checks merely to save Actions minutes.

## Experiment 6 implementation

Experiment 6 uses:

- lean repository CI for deterministic tests;
- `.github/workflows/exp6_full_validation.yml` for deliberate complete frozen validation;
- `.github/workflows/exp6_triple_macd_shadow_monitor.yml` for weekly or manually requested frozen monitoring only.

This pattern is the default template for future experiments unless a strategy requires a materially different validation cadence.
