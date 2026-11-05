# Stocks harness skill mappings

Imported/adapted from coding-agent at the revision in [../UPSTREAM.md](../UPSTREAM.md). Nine generic skills replace the earlier ten homelab-specific runbooks. Read root AGENTS.md first. Generic examples are reference material; these mappings control execution here.

| Upstream convention | Stocks application |
| --- | --- |
| main / origin/main | Discover remote default; currently codex/paper-trading-setup, never create or assume main |
| feature/<name> | codex/<name>, isolated worktree when needed |
| docs/features/plan_*.md | Public sanitized plans in docs/features/; preserve unrelated plans and evidence, no wildcard cleanup |
| .harness/test-runner.sh / shell test helpers | python tools/check.py and tests/test_*.py (unittest); shell wrapper delegates to same suite |
| setup / convergence | python manage.py setup validates development files only; no service startup, chmod, hooks, .env copying or key generation |
| .env secrets | stacks/stocks/.env.example documents host mappings only; credentials stay in separate private JSON |
| Runtime audit / recovery / curl examples | Offline fakes by default; scoped, separately authorized operational work only |
| Memory bank | Sanitized public branch context; private deployment facts remain ignored |
| Release and tags | Separate reviewed step; never automatic after implementation |

Use feature-initiation for new features, test-authoring for regression coverage, feature-completion only after review. component-authoring/lifecycle cover scoped module/service changes; codebase-audit and system-diagnostics cover inspection; data-safety covers private backups and isolated restore; start-project orients a new clone without authorizing trading. Read supporting references when relevant. Optional subagent prompts do not require delegation.

There are no installed Bash assertion helper functions, generic backup/restore CLI, hook installer, automatic key provisioning or production test suites. The upstream examples describe patterns, not additional implemented Stocks commands.
