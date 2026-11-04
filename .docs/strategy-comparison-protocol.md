# Frozen strategy comparison, November 3, 2026

Owner challenged deploying a strategy with a losing diagnostic. New NAS entries are paused; protective exits remain enabled. Infrastructure tests are not evidence of a profitable strategy. Do not resume automatically because one backtest looks better.

Freeze these choices before downloading or inspecting comparison results. No parameter grid or iterative tuning in this experiment. Exclude the most recent 10 sessions already used in the previous diagnostic. Use the preceding 104 complete exchange sessions: 14 warmup, 40 development, 30 validation, 20 final holdout. Daily data from prior sessions may update indicators; no future session informs a signal. Save source data hashes and the exact calendar privately. Current fixed universe introduces selection bias; IEX is not a consolidated feed.

## Three candidates

1. Existing ORB-v1 baseline: eight existing symbols; 15-minute opening range, VWAP, fresh cross, volume ratio1.5, max0.5% chase; 1% stop / 2% target. Retain existing entry timing. Its previous ten-day diagnostic is not a qualifying test.
2. Stocks-in-play ORB adaptation: same eight symbols, five-minute range, positive opening candle, opening volume above its previous14-session same-window mean, rank top4 by relative volume. Previous14-session mean true range above$0.50; stop distance10% of that mean true range. Long only, no target, flatten10 minutes before close. One fresh completed-bar crossing per day. This is inspired by published research, **not a replication** of its 1,000-stock universe, shorting or sizing.
3. Noise-band momentum adaptation: SPY and QQQ only, long only; upper bound max(today's open, prior close) times (1 + previous14-session average absolute open-to-same-minute return). At completed30-minute boundaries, enter above upper bound and VWAP. Exit on completed-minute close below max(current upper band,VWAP) or the common1% hard stop; flatten10 minutes before close. No leverage, volatility targeting, shorting, dividends adjustment or repeated symbol entry. Again an adaptation, not a published-return replication.

## Common execution/account assumptions

$2,000 starting equity in each phase; max$400/position, four positions, four entries/day, one entry per symbol/day, no borrowing/shorts. No entries in final30 minutes. Signals use only fully completed bars; orders execute no sooner than the next bar. Buy limit is signal close+5bps and must be fillable at the next bar's open; otherwise skipped. Fractional quantity rounded down. Entry and exit costs deducted from cash at10bps per side; separate stress run at20bps. Stops gap to worse opening price; stop precedes target if both hit in the same bar. Apply stops on entry bar too. Mark positions each minute, enforce$40 daily loss and$200 persistent closing-peak drawdown locks. Account for incomplete closing data and disqualify any run with it. Missing/invalid bars are not forward-filled for entry signals.

Minute OHLC cannot reproduce live bid/ask freshness, queue priority, minute polling latency, exact intrabar path or liquidity. Portfolio replay improves the previous diagnostic but is not the production engine or a guarantee of execution. Modeled P/L is before unmeasured electricity/taxes and any costs not represented by the assumed execution charge. Report all candidates, losses included, and cash/no-trade benchmark0. SPY buy/hold is a descriptive benchmark; it uses a different holding period.

## Promotion gate

Require positive modeled P/L in both validation and final holdout, at least20 trades across those two phases, and positive P/L in both phases under20bps cost stress. Require a positive day-block-bootstrap lower confidence bound on combined validation/holdout mean daily P/L (5-day blocks,5,000 draws,seed20261103,lower1.67th percentile for three candidates). No unresolved data gaps, loss lock or benchmark accounting problems. These are a minimum research screen, not proof of profitability. Final holdout must not be reused to tweak parameters. If none pass, keep strategy entries paused and report that no replacement is qualified.

Sources inspected:
- https://concretumgroup.substack.com/p/beat-the-market-with-intraday-momentum
- https://www.quantconnect.com/research/18444/opening-range-breakout-for-stocks-in-play/p1
- https://papers.ssrn.com/abstract=4729284

Published results use different universes, risk/exposure, costs and data. Do not quote their returns as expected results for this $2,000 account.
