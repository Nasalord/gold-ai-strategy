# Data Sources and Responsibilities

The scanner is intentionally provider-agnostic. External services populate a normalized point-in-time snapshot; the scanner only consumes validated `SecurityRow` objects.

## Bigdata.com
Use for research enrichment after the mechanical screen:

- company fundamentals and financial statements
- analyst estimates and estimate revisions
- earnings results and calendars
- recent news and media sentiment
- filings, transcripts, research, and catalysts

Bigdata data should be source-attributed and timestamped before it is converted into research features or an agent source packet.

## Interactive Brokers (IBKR)
Use for execution-grade market/account state:

- current quotes and historical prices where available
- account NAV, balances, positions, and orders
- paper-order submission and fill reconciliation

IBKR execution remains PAPER ONLY until a separate live-trading approval milestone is explicitly completed.

## Snapshot contract
Provider data enters the scanner through JSON or CSV using these canonical fields:

- `symbol`
- `price`
- `market_cap`
- `avg_dollar_volume`
- `trading_days`
- `data_asof` (timezone-aware ISO-8601)
- `quality`
- `growth`
- `momentum`
- `revisions`
- `valuation`
- `catalyst`
- `liquidity`

Factor fields may be null. Missing values remain missing; they are never invented or silently replaced with zero. The scanner applies its configured missing-data penalty.

Every snapshot also includes `source`, `snapshot_asof`, and an optional `snapshot_id`.

## Point-in-time rule
A row may not contain information timestamped after the snapshot timestamp. The scanner separately checks that the snapshot itself is not future-dated relative to the scan run. This separation is deliberate to reduce look-ahead leakage in backtests.

## Secrets
API keys, tokens, account identifiers, and brokerage credentials must never be committed to the repository. Future provider adapters should read credentials from environment variables or a secrets manager.
