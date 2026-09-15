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

Once an experiment is frozen, scheduled shadow/paper monitoring continues at the frequency justified by the strategy. Monitoring workflows must not also trigger on ordinary source pushes or pull-request edits.

During the current experiment/data-collection phase, long-horizon health monitors use a **weekly cadence** unless a documented strategy-specific reason requires more frequent observation. The current monitored set is AI2, AI8, AI38, AI58, and EXP6: five scheduled monitor runs per week instead of the previous nineteen.

The eventual daily-reporting cadence is reserved for a strategy that has passed the long-term qualification process in `docs/LONG_TERM_RESEARCH_PLAN.md`.

## Development rules

- Batch related edits before opening or updating a validation PR.
- Do not rerun a successful heavy suite because of documentation-only changes.
- Use path filters so unrelated experiments do not run.
- Use concurrency cancellation for superseded PR or monitor runs.
- Re-run failed jobs only when possible instead of restarting successful work.
- Keep artifacts only as long as they remain useful for review.
- Record runner usage after major experiments so future workflow design is based on measured cost.
- Preserve the full scientific validation package; never remove OOS, robustness, cost, parity, or monitoring checks merely to save Actions minutes.
- Do not monitor rejected or replication-incomplete strategies simply because a workflow exists.

## Monitoring schedule

The weekly monitors are staggered on Monday UTC so they do not all start simultaneously:

| Strategy | Schedule |
|---|---|
| EXP6 | Monday 12:15 UTC |
| AI2 | Monday 12:30 UTC |
| AI8 | Monday 12:45 UTC |
| AI38 | Monday 13:00 UTC |
| AI58 | Monday 13:15 UTC |

Every monitor also keeps `workflow_dispatch` for deliberate manual investigation.

## Experiment 6 implementation

Experiment 6 uses:

- lean repository CI for deterministic tests;
- `.github/workflows/exp6_full_validation.yml` for deliberate complete frozen validation;
- `.github/workflows/exp6_triple_macd_shadow_monitor.yml` for weekly or manually requested frozen monitoring only.

This pattern is the default template for future experiments unless a strategy requires a materially different validation cadence.
