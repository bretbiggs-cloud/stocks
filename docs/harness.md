# Coding-agent harness for Stocks

The harness organizes development instructions and handoffs; it is separate from the scheduled trading service. Source and license are recorded in [.agents/UPSTREAM.md](../.agents/UPSTREAM.md).

## Commands
Use the existing Python environment (3.12/3.13):

```sh
python manage.py setup
python manage.py audit
python manage.py test all
```

Setup is an idempotent readiness check. It does not provision services, copy environment settings, change permissions, install hooks or generate keys. Audit checks required harness files, entrypoint routing and tracked private paths. It is not a full secret scanner, filesystem-permission audit or NAS health check. Test delegates to the existing offline tools/check.py with the same interpreter and propagates failures. Unknown commands/suites fail. Git is needed for tracked-path auditing. No external Python packages are added.

For Bash users, ./manage.sh and ./.harness/test-runner.sh are thin adapters. Set PYTHON to an interpreter executable if python is not the intended environment. Windows users need no Bash or symlink privileges; use manage.py. Hook installation is unsupported: existing hooks are preserved and no branch protection is claimed.

## Instructions and memory
AGENTS.md routes to Stocks rules, generic engineering conventions, nine progressive-disclosure skills and actual product docs. CLAUDE.md, GEMINI.md, agent.md and .cursorrules are regular instruction pointers. .skills/README.md points to canonical .agents/skills; tool-specific automatic discovery beyond these entrypoints is not verified.

Read the three public .agents/memory files at session start and update them at task handoff. Keep them sanitized and branch-specific. Private deployment, credentials, reports and account history must remain in ignored local notes, including .agents/memory/private if used. Existing private decisions/setup/operations/current-state remain in place; a clean worktree or public clone will not contain them. Never infer authorization from a clone or memory entry.

## Migration and branch state
The harness branch starts from codex/paper-trading-setup. The deployed v2 research implementation is on separate codex/daily-research. This migration does not integrate that branch or change the running service. Reconcile the two feature branches before any release intended to include both. The strategy description in this checkout describes its own code, not proof of current deployment.

Legacy homelab skills were replaced by generic component, diagnostics and data-safety workflows. Stocks mappings override generic shell/infra examples. Review the [migration plan](features/agent-harness.md) for the preservation map. No old private history, upstream release tags or upstream memory claims were imported. Feature completion, merging and release tags remain a separate review step.
