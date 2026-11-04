# Strategy recommendations

Ask the agent: "Give me three strategy candidates based on our historical evidence." The agent must use saved evaluation results and present the actual periods, cost scenarios, drawdown, trade count, win rate, limitations and reasons each candidate passed or failed. Selecting a candidate requests further research; it does not authorize deployment.

The first implementation is an offline CLI:

```sh
python -m stocks.recommend --evidence /private/research/comparison.json --output /private/research/strategy-options.json
```

Input is the `comparison.json` schema produced by `stocks.compare`, containing three supported candidates: opening-range breakout, relative-volume opening-range breakout and intraday noise-band momentum. This version does not accept the separate `history_check` report schema yet, discover arbitrary strategies, or generate new historical evidence. It produces exactly three comparison cards, labeling absent evidence explicitly, and ranks by reported screening eligibility then combined base validation/holdout P/L. The output includes an evidence hash and reported period/benchmark metadata. Keep inputs and generated reports private.

Eligibility is recomputed from positive base/stress validation and holdout results, at least 20 base trades across those periods, positive reported confidence lower bound, no review locks and no missing exit days. This is a review screen, not proof that the source data are genuine, unseen or complete. Sorting already-inspected results is not a fresh validation experiment. Nonfinite/malformed metrics are rejected. If none pass, the result is `none_qualified`, not a forced trade recommendation.

Acceptance verified: three cards, missing evidence handling, all-negative refusal despite a misleading qualification flag, invalid numeric rejection, incomplete-exit rejection and no input mutation. The existing saved comparison returned three failed candidates. Full five-year and historical-news evidence remain incomplete; do not claim otherwise.
