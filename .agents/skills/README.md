# Imported project skills

Source: [ParanoydAndroid/homelab-configs](https://github.com/ParanoydAndroid/homelab-configs), `.agents/skills`, revision `7f6fa6a5600b72fb936c1595e99608cc2aa4fd7b`. Copied at the operator's request with attribution. All ten skills and nine supporting references are included. Upstream personal domains, LAN ranges and storage paths have been replaced with illustrative values; no upstream deployment configuration or credentials were imported.

## Stocks applicability

- `feature-initiation`: use for new feature planning, design review and implementation handoff.
- `test-authoring`: use its failure-mode and regression discipline with the Python suite.
- `feature-completion`: use for an explicitly requested release/merge after review; importing this folder does not authorize a release.
- Backup, recovery, network, stack and homelab skills are reference workflows. Apply only when relevant to an explicitly scoped Stocks operation. Do not run their example scripts or modify other services.

## Required repository mappings

| Upstream assumption | Stocks mapping |
| --- | --- |
| `origin/main` | Discover the actual remote default branch; currently `codex/paper-trading-setup`. Never invent a main branch. |
| `feature/<name>` | `codex/<feature-name>` for new isolated work |
| `.tests/suites/` and `./homelab.sh test all` | `tests/` and `python tools/check.py` |
| `.agents/artifacts/plan_*.md` committed | Public plans go under `docs/features/` after privacy review; private operational plans stay excluded |
| `homelab.sh`, upstream `.scripts/`, network conventions and stack directories | Not installed here; consult `docs/architecture.md` and actual code instead |
| `.env` credentials | Host paths/IDs only; Alpaca credentials remain in a private read-only JSON file |
| Automatic infrastructure deployment | Preserve existing trading authorization and host boundaries; verify any concrete change separately |

Read root AGENTS.md before applying a skill. Preserve implementation-review checkpoints when using the feature workflow, while respecting explicit user instructions and already-provided authorization. Do not retroactively restart completed features. Documentation imports do not change the trading strategy or running services.
