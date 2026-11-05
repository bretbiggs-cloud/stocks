# Stocks coding-agent entrypoint

Read these sources at session start, in order:
1. README.md, docs/product.md, docs/architecture.md and .docs/strategy-comparison-protocol.md.
2. [.agents/rules/stocks.md](.agents/rules/stocks.md): mandatory trading, research, privacy and verification instructions.
3. [.agents/rules/project-conventions.md](.agents/rules/project-conventions.md), then applicable language/configuration rules.
4. .agents/memory/activeContext.md, systemPatterns.md and progress.md: sanitized branch-local handoff, not deployment authority.
5. If present locally, .docs/decisions.md, .docs/setup-plan.md, .docs/operations.md, .agents/artifacts/current-state.md and .agents/memory/private/. These are private operator context. Keep them private; do not copy them into tracked memory.

Stocks rules and the operator's explicit authorization override generic harness examples. Real-money trading is not authorized. Unknown order/account/data conditions block new entries; never clear locks or deploy revised strategies because a workflow says to converge state.

Use [.agents/skills/README.md](.agents/skills/README.md) to select a workflow. Feature initiation includes scope/design review, isolated implementation and regression checks. Ask only for unresolved decisions; use already provided requirements and authorization. After implementation and testing, present the result for review before feature completion, merge or release tags.

Persistent memory: update activeContext when starting a task; at handoff update it and progress with actual outcomes and outstanding work. Keep public memory generic, dated and branch-specific. Private deployment/account facts belong only in ignored private notes. Memory is a handoff aid, not proof of present runtime state; re-verify before operational claims.

Multi-agent entrypoints are regular pointer files for Windows compatibility. They load this same contract. Subagent role definitions are optional prompts, not permission to launch background work. Never imply an assistant continues running between conversations without a verified scheduler.
