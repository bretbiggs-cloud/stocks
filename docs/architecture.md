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

## Current strategy

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
