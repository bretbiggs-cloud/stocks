# Replacement strategy review — November 3, 2026

## Decision

**No candidate qualified. Keep all new paper entries paused, including the initial canary.** The NAS monitor/protective-exit service remains running; there are no positions or pending orders. It was a mistake to treat successful infrastructure tests as sufficient reason to activate the original losing strategy.

## Research and method

Compared the existing ORB baseline with two fixed, research-inspired alternatives:

- Relative-volume opening-range breakout, inspired by [QuantConnect's stocks-in-play study](https://www.quantconnect.com/research/18444/opening-range-breakout-for-stocks-in-play/p1). Our version uses the eight-symbol universe, long-only fractional positions and $400 caps; the study's broad universe and short trades are not replicated.
- Noise-band momentum, inspired by [Concretum's intraday momentum research](https://concretumgroup.substack.com/p/beat-the-market-with-intraday-momentum). Our version uses SPY/QQQ, long only, without leverage or volatility-targeted sizing. Published returns do not describe this implementation.

Protocol frozen in Git commit `df17a0c` before downloading/evaluating results. No parameter sweep. Excluded the ten sessions already inspected (October 21–November 3). Downloaded 104 sessions with 14 warmup sessions; evaluated 90. Raw data/hashes and full trade logs remain in the private PC research folder, outside Git. Code in `stocks/compare.py` is offline/read-only and cannot place trades.

Phases: development June 12–August 10 (40 sessions), validation August 11–September 22 (30), holdout September 23–October 20 (20). Each phase starts with $2,000 and applies the same cash, $400 position, four-position/four-entry daily, $40 loss and $200 drawdown constraints. The final two phases were not used to change parameters. Two small implementation checks were completed before final reporting: true range requires a real prior close, and the SPY benchmark is explicit. No signal parameters were altered after results.

## Results after modeled costs

Base costs: 10 basis points per filled side. Stress: 20 per side. Dollar amounts below are simulated, before unmeasured electricity/taxes/other costs. Aggregates sum the two independently initialized test phases; they are not a continuous account performance claim.

| Candidate | Validation P/L | Holdout P/L | Combined P/L | Trades in those phases | Combined stress P/L |
|---|---:|---:|---:|---:|---:|
| Original ORB | -$52.44 | -$32.67 | -$85.11 |116| -$177.87 |
| Relative-volume ORB | -$19.62 | -$7.15 | -$26.76 |47| -$64.35 |
| Noise-band momentum | -$13.07 | -$10.16 | -$23.23 |27| -$44.81 |

Every candidate lost in development too. All confidence-bound estimates for validation/holdout mean daily P/L were negative. Neither unseen phase recorded missing closing exits. Cash/no-trade benchmark: $0. Full-$2,000 SPY buy-and-hold price-return benchmark after base modeled costs was -$6.77 in validation and -$13.64 in holdout; that benchmark has materially different exposure/overnight risk and omits dividends.

Noise-band momentum had the smallest combined test loss; relative-volume ORB had the smallest final-holdout loss. Neither demonstrated a positive edge. Larger bets would not fix these findings.

## Limits and next research boundary

IEX minute bars omit consolidated quotes, bid/ask, fill queues and exact intrabar timing. The current fixed universe introduces selection bias. Stops in the replay may execute sooner than the production minute-polling exits. Published strategies are adapted, not independently replicated. These results reject these implementations under these assumptions; they do not prove that every version of the published ideas fails.

Further work should be a new, prospectively documented experiment with new validation data, not retuning against this holdout. Candidates needing broad point-in-time universes or news must first demonstrate data availability, licensing and cost within the approved budget. No new paid subscription authorized. No replacement has been installed or enabled.

40 local tests pass, including optimized baseline agreement with existing signal rules, future-bar exclusion, next-bar fills, entry-bar stop ordering, missing-bar rejection and deterministic bootstrap. NAS production code remains its 35-test version with persistent entry review lock. Research tests are not a profitability guarantee.
