# Product specification

## Intended final product

An unattended paper-trading research system that tests whether a strategy can earn monthly profit after costs. The operator sees submitted orders and filled positions in Alpaca paper, with a clear explanation of each trade, performance against cash and a market benchmark, and the current health of execution and data feeds. It must distinguish broker paper fills from hypothetical simulations.

The trading service runs on the dedicated host while the operator PC is off. Research runs off-hours with bounded resources and cannot delay position monitoring. Proposed changes carry reproducible historical evidence and a version identifier before an explicit deployment decision. No profit target is guaranteed. Real-money execution is outside the authorized product.

## Feature 1: full documentation update

Deliver a coherent README, product specification, architecture/operations reference and agent instructions. Remove obsolete claims that strategy orders are disabled or limited to a single day. Separate implemented capabilities from incomplete work. Keep private deployment identity, credentials and account reports out of all public documentation and history.

Acceptance: public links resolve; documented controls match code; paper and mock behavior are distinct; historical/news limitations are explicit; the roadmap is actionable; no private context is required to understand the product. Documentation alone must not restart trading, alter controls or claim a feature is deployed.

## Current capability and remaining work

| Capability | Implemented | Remaining acceptance/work |
| --- | --- | --- |
| Alpaca paper execution | Fixed paper endpoint, fractional limit entries, reconciliation, local exits | Continue observing fills, outages and recovery; never infer live readiness |
| Daily operation | Explicit ongoing operator authorization, broker calendar, daily date rollover | Persistent locks still require review; no guaranteed daily trade |
| News-volume rules | Eight-symbol price/volume breakout plus recent ticker-tagged news | Sentiment, confirmed catalysts and broader-universe research are not implemented |
| Performance records | Private daily/monthly paper reports; separate mock ledgers | Unified operator-facing performance view and complete actual-cost reconciliation |
| Historical checks | Resumable one/five-year cache and supported price-only candidate replay | Full historical evaluation, point-in-time news validation and production-equivalent replay |
| Overnight research | Separate operator-side scheduled research workflow | PC-independent research execution and measured resource acceptance |
| Strategy improvement | Frozen versions and validation/holdout conventions | Controlled promotion workflow; no automatic self-training or deployment |

## Strategy recommendations feature

An offline three-candidate evidence comparison is implemented in `stocks.recommend`. See [input contract and acceptance](recommendations.md). It consumes existing comparison reports; arbitrary strategy discovery, five-year report ingestion and historical-news validation remain future work. Choosing a candidate does not deploy it.

## Prioritized follow-up features

1. Complete historical data collection and coverage audit; publish only aggregate research evidence, with costs and missing-data limitations.
2. Add point-in-time news replay and verify signal/execution timing against the deployed engine. Do not substitute current articles or future revisions for past information.
3. Present broker paper trades, hypothetical trials, benchmarks, costs and health in a single operator report with clear provenance.
4. Make overnight research independent of the PC only after measuring capacity and proving that it cannot interfere with trading or neighboring services.

Each feature must state its trigger, resulting behavior, evidence, resource/cost impact and acceptance checks. A candidate that fails evaluation remains a failed candidate; do not tune on the final holdout to manufacture success.
