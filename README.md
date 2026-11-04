# Stocks paper-trading agent

A rules-based Alpaca paper trader and historical research workflow for evaluating monthly performance after costs. Orders sent to Alpaca paper appear in its order history and positions; hypothetical mock trades are recorded separately. No real-money trading is authorized or implemented through the adapter.

## Product direction

Build a reliable, unattended paper experiment with explainable decisions, reproducible strategy checks and clear performance reporting. The first feature is a **full documentation update** establishing the product contract and the boundary between running features and planned work.

- [Product specification, feature 1 and roadmap](docs/product.md)
- [Architecture, strategy and operating controls](docs/architecture.md)
- [Agent implementation instructions](AGENTS.md)
- [Project skills and Stocks mappings](.agents/skills/README.md)
- [Regression suite and feature acceptance](docs/testing.md)
- [Three-candidate strategy recommendations](docs/recommendations.md)
- [Historical comparison protocol](.docs/strategy-comparison-protocol.md)
- [Earlier candidate results and limitations](.docs/strategy-review-2026-11-03.md)

## Current behavior

The existing operator deployment is authorized to run the news-volume strategy in Alpaca paper on market days until stopped. A new clone is not automatically authorized or provisioned. Qualifying signals, calendar checks, reconciliation and risk limits still determine whether a trade occurs.

The Python service combines IEX price/volume signals with recent symbol-tagged news. It does not interpret news sentiment, autonomously learn from trades or browse the whole internet. Separate mock ledgers and historical replay are research tools, not Alpaca fills. Prior negative research results remain valid; no profitable edge is established.

Historical tooling supports resumable one/five-year collection and selected price-only replay candidates. Full five-year evaluation and point-in-time news backtesting are incomplete. Overnight research is a separate operator workflow and currently depends on local PC/Codex availability; the deployed NAS trader does not.

## Development

Create a Python virtual environment and install `requirements-dev.txt`. Run `python tools/check.py` after every feature. Keep credentials, downloaded data, reports and runtime state outside the repository. See the architecture reference before changing execution or control behavior.

## Private deployment configuration

Copy `stacks/stocks/.env.example` to a private `.env` file on the deployment host. Set the host user/group IDs and absolute paths to source, runtime data and the existing credential JSON. Use an explicit environment-file path so Compose does not pick up unrelated settings:

```sh
docker compose --env-file /path/to/private/.env -f stacks/stocks/compose.yml config --quiet
docker compose --env-file /path/to/private/.env -f stacks/stocks/compose.yml up -d
```

The `.env` file is ignored by Git; only the generic `.env.example` is public. Keep the credential JSON outside the repository with restricted filesystem permissions. API keys remain in that file, mounted read-only, rather than environment variables. The container paths stay fixed; this configuration maps private host paths to them. Required values fail validation if missing.

Paper-only endpoints, trading risk limits, resource limits and exchange timezone remain in code/configuration. Runtime trading authorization and pause controls remain in the private `settings.json`. Environment variables do not authorize live trading or bypass safeguards.

See [AGENTS.md](AGENTS.md) for public agent instructions. Private operator decisions, setup details, operations and current-state notes are intentionally not published.
