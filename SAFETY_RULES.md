# Safety Rules

- Research, backtesting, and paper/shadow monitoring only.
- No live broker or exchange order submission.
- No credentials, API keys, account IDs, cookies, tokens, or personal financial balances in Git.
- AI conclusions never override deterministic validation code.
- Strategy parameters are frozen before untouched out-of-sample evaluation.
- Failed OOS results are not retuned away.
- Transaction costs and slippage are modeled explicitly where relevant.
- Creator leverage/sizing is treated separately from signal quality.
- Missing, stale, or unverifiable data is labeled rather than fabricated.
- Health monitors may report status or open GitHub issues; they do not place trades.
