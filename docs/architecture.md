# Architecture and operating contract

## Modules and data flow

| Module | Responsibility |
| --- | --- |
| `stocks/runtime.py` | Single writer, settings reload, minute loop, host-resource guard and heartbeat |
| `stocks/engine.py` | Account/order reconciliation, exits before research, paper entry orchestration, reports |
| `stocks/broker.py` | Fixed Alpaca paper and market-data hosts; private credential-file authentication |
| `stocks/risk.py` | Deterministic cash, exposure, freshness and loss validation |
| `stocks/news.py`, `stocks/strategy.py` | Timestamped news eligibility and completed-bar price/volume signals |
| `stocks/journal.py`, `stocks/store.py` | Durable intents, orders, state, events and consistent snapshots |
| `stocks/shadow.py` | Separate hypothetical ledgers; no broker order submission |
| `stocks/compare.py`, `stocks/history_check.py` | Offline research replay and resumable historical cache |

News and bars inform candidates; deterministic execution checks decide whether an order is permitted. Outside text cannot change endpoints, settings or risk limits. AI interpretation and public-trader signal feeds are not part of the execution loop.

## Legacy strategy and frozen experiments

AAPL, MSFT, AMZN, NVDA, GOOGL, META, SPY and QQQ. Require a fresh crossing above the first 15-minute range, above session VWAP, at least 1.5 times prior 20-bar average volume and no more than 0.5% extension above the range. Use completed same-session bars. Require eligible symbol-tagged news published within two hours; poll news in five-minute intervals. Missing/incomplete news blocks new strategy entries. News presence is not a positive sentiment classification.

Default simulated capital is $2,000; maximum $400 per position, four positions and four strategy attempts per day. No borrowing, shorts or derivatives. Entries require fresh quotes, spreads no wider than 0.25%, and a tradable fractional instrument. Attempt local exits at 1% loss, 2% gain or ten minutes before session close. Stop entries thirty minutes before close. Daily equity loss threshold is $40; closing-peak drawdown threshold is $200. These limits trigger actions, not guaranteed fills or maximum realized losses.

## Private runtime controls

`settings.json` belongs in the private runtime directory. `paper_enabled` gates all submissions, including exits. `strategy_enabled` gates strategy buys. `strategy_daily=true` authorizes the current Eastern date each loop in an operator-authorized ongoing deployment; otherwise `strategy_date` must match. The canary and mock trials retain their separate `canary_date` and `shadow_date` controls. Daily paper authorization does not automatically extend mock trials.

To pause new entries while preserving exits, keep `paper_enabled=true` and set `pause_entries=true`. This creates a persistent review lock; setting it back to false does not clear that lock. Never erase the database or clear locks without reconciliation. Turning off `paper_enabled` or stopping the service also disables protective order submissions.

## Reporting and recovery

Private `heartbeat.json` describes cycle freshness/success. `reports/status.json`, daily and monthly reports describe paper activity; `mock-*.json` describe hypothetical ledgers. Filled and closed are distinct from submitted. Broker totals may include connection-test activity. Costs modeled at 10bps per filled side are additional assumptions, not broker-charged fees. Unknown electricity/other costs prevent verified net-profit claims. Benchmarks can have different start times and exposure.

Check heartbeat age, broker positions/orders, ledger reconciliation, locks and attention together. Container health alone does not prove correct trading. Preserve the ledger and snapshots during upgrades. Restore backups only into an isolated test location, never a second enabled executor for the same account. API/NAS outages can prevent local stops and leave exposure overnight. No external alert delivery is promised by this repository.

## Configuration boundary

The public Compose file reads host UID/GID and mount paths from a private environment file. API keys remain in a separately protected JSON file mounted read-only. Paper endpoints and risk logic are not configurable through `.env`. The example environment file is a template, not the operator deployment. Source/config changes require explicit deployment and verification; a GitHub push alone does not update a running service.


## Daily research strategy (daily-news-volume-v2)
When the private `research_daily` flag is true, the executor uses a session-specific shortlist instead of the legacy eight symbols. A bounded premarket collector runs one network request per eligible minute from 03:00 until 09:15 Eastern, only with the market closed, no positions/orders, reconciliation clear and host capacity available. It paginates 48 hours of provider news (maximum 200 pages), screens broker-listed instruments, and evaluates up to 100 eligible symbols, newest news first. It accepts explicit common-stock/ordinary-share/ADR descriptions on NYSE/NASDAQ; ambiguous names, funds, leveraged/inverse products and non-fractional instruments are excluded. Broker naming is a conservative classification heuristic, not a security-master guarantee.

Require 21 complete exchange sessions, last price at least $5, prior-20-session mean IEX dollar volume at least $5 million, and latest volume at least 1.2 times that mean volume. Rank by relative volume, then liquidity, then symbol; choose at most eight. These are frozen experimental thresholds, not optimized parameters. Partial pagination fails the session; excluded and capped candidates are recorded. Research state survives restarts; terminal collection failures require investigation rather than unbounded retries.

The collector saves `reports/research-YYYY-MM-DD.json` and private ledger state with rules/input hashes, timestamps, candidates, rejected symbols and supporting articles. Hashes detect accidental corruption, not malicious modification by someone controlling the private host. Artifacts expire at that session's close; no previous-day or test-list fallback exists. Entry evidence combines the five most recent eligible articles per selected symbol from the frozen artifact with a fresh two-hour news query. Evidence must remain within 48 hours; the existing intraday breakout/volume/quote checks remain required. Newer observed revisions replace old ones. News activity is not verified positive sentiment or issuer-confirmed earnings analysis. Three-page limits on entry news queries may block entries during unusually busy coverage.

`stocks.sizing` targets $10 planned loss per new entry, accounting for a 1% local stop plus modeled 0.10% costs per side. The accepted per-trade range is $10–$20, but this version uses its lower end. With enough cash/risk room, position notional is approximately $833 rather than $400. Combined held-position and pending-buy planned risk cannot exceed $20. Pending quantities exclude already filled portions, which are counted in holdings. An insufficient remaining budget means no new trade. The four-position/four-entry operational caps remain; entries from old versions count toward the same day's cap. The $40 daily equity-loss threshold additionally includes modeled costs accrued that day. Neither stop levels nor the threshold guarantee a maximum loss in an outage or gap. No borrowing remains enforced.

Holdings management is independent of the shortlist. Exits run before entry research and do not need a valid artifact. The final submission boundary verifies the dated shortlist and the fresh, exact payload's risk validation. New research is observational only and cannot place orders by itself. The fixed-universe mock and historical versions are preserved. Dynamic-universe point-in-time news backtesting is not supported by `history_check`; one/five-year validation of v2 remains incomplete. The $100 daily goal is an aspiration and has no execution trigger.

## Development harness

See [harness commands and memory](harness.md). The shared harness and daily-research upgrade are integrated in this checkout. Repository merges do not deploy or change private runtime settings.
