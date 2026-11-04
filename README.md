# Stocks paper-trading agent

An experimental, rules-based day trader for a dedicated **$2,000 Alpaca paper account**. No live endpoint, borrowed funds, short selling, options, or paid AI calls.

**New entries are PAUSED, including the first canary.** The initial strategy failed its historical diagnostic. The owner requested a better alternative; see [frozen comparison protocol](.docs/strategy-comparison-protocol.md). Running infrastructure is not a qualified trading strategy. Protective exits remain enabled, although there are currently no positions.

The [replacement review](.docs/strategy-review-2026-11-03.md) tested three candidates over 90 evaluation sessions. All lost after modeled costs in both validation and holdout. No replacement is enabled.

This is a scheduled Python service, not an LLM that searches the whole internet. It uses Alpaca IEX prices and volume. TradingAgents, FinRL-DeepSeek and FinRL-Meta are research candidates, not installed dependencies.

## Strategy and limits

- Fixed universe: AAPL, MSFT, AMZN, NVDA, GOOGL, META, SPY, QQQ.
- First verify a paper buy/sell round trip of at most $10 AAPL. A failed/ambiguous test blocks further entries.
- Then test a 15-minute opening-range breakout: fresh crossing, above session VWAP, at least 1.5 times the previous 20 bars' average volume, no chasing more than 0.5% above the range.
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

The first real-session paper round trip and PC-off operation must be observed before calling those acceptance checks complete. See [current state](.agents/artifacts/current-state.md) for measured deployment status.

## Development and operations

Windows: create `.venv`, install `requirements-dev.txt`, then run `.venv\Scripts\python -m unittest discover -s tests -v`. Linux uses the standard library and system timezone database.

- [Approved plan and implementation amendment](.docs/setup-plan.md)
- [Operations, pause, backup and recovery](.docs/operations.md)
- [Owner decisions and retained research sources](.docs/decisions.md)
- [Current verified state](.agents/artifacts/current-state.md)
