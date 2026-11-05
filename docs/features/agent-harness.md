# Agent harness migration plan

Source: ParanoydAndroid/coding-agent at 27a983d1c40a4db33ef52efb85b9256382cfbf6c (MPL-2.0).

## Scope and settled design
Adopt the reusable nine-skill harness, canonical instructions, cross-agent entrypoints and persistent memory. Preserve all Stocks trading/research safeguards. This is a development-workflow migration, with no trader deployment, trading-rule changes or runtime access.

Branch from the actual remote default, codex/paper-trading-setup, in an isolated worktree. The separate codex/daily-research branch contains the deployed v2 trader; do not merge, replace or deploy either branch as part of this migration. Reconcile that branch explicitly before a future release/deployment.

## Restructuring audit
| Existing guidance | Destination / disposition |
| --- | --- |
| Stocks AGENTS scope, privacy, trading, research, operations | .agents/rules/stocks.md, preserved verbatim except obsolete imported-skills routing |
| Homelab-specific imported runbooks | Replace with nine generic coding-agent skills; historical versions remain in Git |
| README/product/architecture/testing | Remain canonical product references; add harness usage and branch-state caveat |
| Private decisions/setup/current-state/operations | Preserve in place, ignored; read as operator-only context, never copy into public memory |
| Cross-session public context | .agents/memory/{activeContext,systemPatterns,progress}.md, sanitized branch-local facts |
| Private future handoffs | .agents/memory/private/, ignored; no automatic ingestion or publishing |
| Generic architecture template | Pointer to actual docs/architecture.md rather than a second specification |
| Upstream symlinks | Regular instruction pointers for Windows clones without symlink privileges |
| Upstream Bash setup/audit/tests | Small Python-standard-library adapter; Bash wrappers delegate to it |

## Design review
Blind setup would chmod private files, overwrite hooks and assume main. Reject that behavior: setup only checks the local harness; it neither provisions trading nor copies environment templates. Hook installation is deliberately unsupported; no claims of enforced branch protection. Existing tools/check.py remains the full offline test authority, with added harness behavior tests. Audit checks routing, required files and tracked private paths; it is not a comprehensive secret scanner or runtime health check.

No new package dependencies. No personal source paths, credentials or account records enter the import. Preserve upstream MPL license and provenance, document adapted files. Keep user-review checkpoint before feature completion, merging or tagging. Use existing authorization for routine implementation choices.

## Acceptance
Run full offline suite through both tools/check.py and management entrypoint. Test setup repeatability and preservation of private files/hooks, invalid-command failure, test failure propagation, missing entrypoints and tracked-private-path rejection. Verify clean public diff and anonymous commit metadata. Keep operator workspace and running trader untouched. Update public memory with actual verification results and outstanding branch/release limits.
