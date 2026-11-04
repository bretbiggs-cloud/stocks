# Stocks paper-trading agent

An experimental, rules-based day trader for a dedicated **$2,000 Alpaca paper account**. No live endpoint, borrowed funds, short selling, options, or paid AI calls.

**Strategy purchases are disabled.** For November 4, the owner requested a paper test and mock trial. The NAS is configured to attempt one <=$10 AAPL paper buy/sell after 09:35 Eastern, then run a separate forward mock ledger after successful reconciliation. This authorization expires after that date; the completed canary cannot unlock strategy orders. Running infrastructure is not a qualified trading strategy. Protective exits remain enabled.

The [replacement review](.docs/strategy-review-2026-11-03.md) tested three candidates over 90 evaluation sessions. All lost after modeled costs in both validation and holdout. No replacement is enabled.

This is a scheduled Python service, not an LLM that searches the whole internet. It uses Alpaca IEX prices and volume. TradingAgents, FinRL-DeepSeek and FinRL-Meta are research candidates, not installed dependencies.

## Strategy and limits

- Fixed universe: AAPL, MSFT, AMZN, NVDA, GOOGL, META, SPY, QQQ.
- First verify a paper buy/sell round trip of at most $10 AAPL. A failed/ambiguous test blocks further entries.
- The mock ledger observes a 15-minute opening-range breakout: fresh crossing, above session VWAP, at least 1.5 times the previous 20 bars' average volume, no chasing more than 0.5% above the range. It sends no strategy orders to Alpaca.
- Entry quote must be fresh, spread at most 0.25%, and instrument active/fractionable. Only completed same-session bars count.
- At most $400 per position, four positions, four strategy entries per day, one entry per symbol per day. Fractional DAY limit buys; no extended-hours entries.
- Attempt exits at a 1% loss or 2% gain; start end-of-session exits 10 minutes before the broker calendar's close. No new entries in the final 30 minutes. Early closes supported.
- $40 daily equity-loss lock; $200 drawdown from highest observed closing equity requires review. Cash and pending orders constrain every entry; displayed margin buying power is ignored.
- Unknown submissions are reconciled by durable client ID, never blindly retried. One process owns the database.

**These numbers are experimental defaults, not optimized or guaranteed profitable.** A preliminary 10-session IEX bar diagnostic produced 28 trades, approximately -$36.32 before modeled costs and -$58.68 after modeled costs. It is not a full execution replay and cannot establish actual future performance. Parameters were not fitted to improve that sample.

## Runtime

NAS project: `/srv/stocks`. Python 3.12 image pinned by digest; non-root UID1000/GID100, 128 MB RAM, no swap allocation, no exposed ports or Docker socket. Polls once per minute; exits precede entry research. Low host memory or high sampled I/O wait defers research and entries. New entries require regular market hours.

Private credentials are outside this repository. Runtime SQLite, reports and backups are also outside source control. Reports show equity, modeled execution costs (10 basis points per filled side), cash and SPY comparisons. Unmeasured electricity/fees mean **net profit is not verified**. AI and data subscription spending for this version is $0.

## Important operating limits

Stops and end-of-session exits run locally, **not as broker-held protective orders**. API outages, NAS failure, stale data, market halts and rejected/unfilled exits can produce losses beyond thresholds or overnight exposure. The service records these conditions; an external alert delivery channel is not configured. Paper execution is not evidence of real-money fill quality.

Deployment acceptance and performance evidence are operator-specific and kept in private local records. Infrastructure tests alone do not establish trading performance.

## Development and operations

Windows: create `.venv`, install `requirements-dev.txt`, then run `.venv\Scripts\python -m unittest discover -s tests -v`. Linux uses the standard library and system timezone database.

## Private deployment configuration

Copy `stacks/stocks/.env.example` to a private `.env` file on the deployment host. Set the host user/group IDs and absolute paths to source, runtime data and the existing credential JSON. Use an explicit environment-file path so Compose does not pick up unrelated settings:

```sh
docker compose --env-file /path/to/private/.env -f stacks/stocks/compose.yml config --quiet
docker compose --env-file /path/to/private/.env -f stacks/stocks/compose.yml up -d
```

The `.env` file is ignored by Git; only the generic `.env.example` is public. Keep the credential JSON outside the repository with restricted filesystem permissions. API keys remain in that file, mounted read-only, rather than environment variables. The container paths stay fixed; this configuration maps private host paths to them. Required values fail validation if missing.

Paper-only endpoints, trading risk limits, resource limits and exchange timezone remain in code/configuration. Runtime trading authorization and pause controls remain in the private `settings.json`. Environment variables do not authorize live trading or bypass safeguards.

See [AGENTS.md](AGENTS.md) for public agent instructions. Private operator decisions, setup details, operations and current-state notes are intentionally not published.
