# Daily research selection: proposed implementation

Status: design accepted; implementation in progress. No deployment yet.

## Outcome
Replace the temporary eight-symbol production entry universe with a dated daily research shortlist. The existing eight-symbol historical experiments and mock ledgers remain frozen. The operator has requested this paper-only feature; no real-money permission is implied.

## Proposed design
- Use the existing Alpaca news and IEX data access. Discover symbols from a bounded, paginated broad news scan, rather than hard-coding tomorrow's picks. Preserve provider, source URL, publication/update/first-observed timestamps and rejection reasons. Provider news is a research lead, not issuer-confirmed bullish sentiment.
- Validate instrument eligibility independently of news text. Only explicitly identified exchange-listed common stocks/ordinary shares or reviewed ADRs; reject funds, leveraged/inverse products, warrants, units, preferreds, ambiguous identities and unavailable fractional instruments. Unknown instrument classification blocks inclusion.
- Screen completed daily bars for sufficient history, finite prices, minimum price and liquidity. Rank by relative volume with liquidity and symbol tie-breaks; retain at most eight candidates. Freeze exact experimental thresholds before observing selection outputs. Daily IEX volume is partial-market activity, not consolidated volume or the intraday entry signal.
- Produce a versioned session-specific artifact with source-data/rule hashes, screened and rejected symbols, evidence, creation time and expiry. Reject future, stale, incomplete or malformed artifacts. An empty list is a valid no-trade result. Never fall back silently to the old test list.
- Consume the same validated shortlist in news fetching, price signals, risk allowlisting and the final submission boundary. Revalidate evidence age immediately before submitting. Maintain current fractional sizing, cash reservations, reconciliation, one-writer order IDs, daily entry cap, loss locks and exits.
- Preserve holdings management independent of shortlist membership. A stock removed from today's shortlist must still be monitored and exited. Retain paper-versus-mock separation and strategy-version attribution across upgrades.

## Scheduling and resources
Use a bounded sequential premarket collector on the existing host, not a new trading process or service. Advance only one bounded collection step per eligible closed-market cycle while flat, reconciled and within host resource guards. Stop collection before the session opens. Do not perform broad scans or historical backtests while monitoring positions. Reuse the existing scheduler, private data directory and restricted container; add no inbound ports, packages, containers or paid subscriptions. Persist progress across restarts and enforce request/page/symbol/time caps. If a complete daily artifact is unavailable, report why new entries are blocked.

## Design choice awaiting answer
Recommend a 48-hour maximum age for catalyst evidence, with current price/volume and quote checks unchanged. Alternative: retain the old two-hour news age, which excludes many overnight earnings by the open. A longer window is an explicit strategy revision, not a change to quote freshness. News presence still does not establish that the event is positive or independently verified; confirmed issuer analysis must be labeled separately.

## Regression acceptance
- Discovery reaches an eligible stock outside the original eight; excluded instrument types never reach submit.
- Pagination incompleteness, API failures, missing bars, duplicate/future timestamps, invalid numbers, empty results and stale/wrong-session artifacts fail closed.
- Same inputs produce identical rankings; future data cannot affect earlier decisions; all truncation limits are reported.
- Selection survives restart, expires next session, and cannot silently revive yesterday's list.
- Held symbols outside the shortlist still exit on stop, target and close; failed research cannot delay protective exits.
- Risk authorization is checked again at submission; unknown/tampered candidates cannot bypass it; daily caps persist across strategy versions.
- Run python tools/check.py offline and review source diffs/privacy before publishing.

## Evaluation and deployment
The current history_check replay does not support this dynamic-universe/news selector. One/five-year strategy validation is incomplete and must not be invented from fixed-universe results. Preserve baseline losses; label any authorized forward trial experimental. Before deployment: save private source/settings/ledger backups, verify flat paper account and no unresolved orders, verify target-host resource limits, run tests in the target environment, then verify health and the daily artifact without forcing a buy. Do not clear locks or reset balances.

Implementation review is separate from release/merge/tagging under the project feature workflow. No publication of private research or deployment identity.


## Accepted risk-design amendment
The operator accepted $10–$20 planned risk per trade, $20 combined open risk, and a $40 daily threshold including unrealized losses and modeled costs. Size positions from stop distance and cash instead of a fixed $400 amount. The $100 desired daily gain is aspirational, not a required minimum or reason to force entries. Implement pending-order risk reservations and cost-inclusive checks; preserve no borrowing, paper-only execution, reconciliation and protective exits. This replaces the earlier proposal to preserve fixed sizing, but is not deployed. The operator accepted the 48-hour window.


## Frozen initial selection parameters
48-hour provider-news window, 03:00–09:15 Eastern premarket collection, one request per cycle, at most 50 news pages and 100 news-derived eligible stocks. Require 21 consecutive exchange sessions of daily bars, price at least $5, prior-20-session mean IEX dollar volume at least $5 million, latest/prior-20 volume ratio at least 1.2. Rank by ratio, then dollar volume, then symbol; top eight. These experimental thresholds are not optimized. Target $10 planned risk per new entry including modeled round-trip costs, with a $20 aggregate ceiling; retain four entries and four positions as initial operational caps. No profit-target chase.
