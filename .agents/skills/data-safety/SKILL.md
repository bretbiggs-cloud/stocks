---
name: data-safety
description: >-
  Operational runbook for data protection, pre-mutation snapshots, zero-downtime
  database staging, disaster recovery, and automated sandbox restore drills.
  Use when modifying databases, running backups, or verifying snapshot integrity.
---

# Stocks data safety

Adapted from coding-agent; root AGENTS.md controls scope. Read private operations guidance when available and docs/architecture.md. Supporting references/recovery-runbook.md is generic reference material, not a runnable Stocks restore command.

Before an authorized persistent change, take a consistent SQLite online backup through the existing journal/store snapshot mechanism, retain private settings/source evidence and verify integrity. Do not tar an active database as the sole consistency guarantee. Inspect actual function interfaces before use.

Keep snapshots and verification output outside public source control. Restore only into an isolated temporary location, validate SQLite integrity and order/intention consistency, and use fake brokers with no network or credentials. Never start a second enabled executor for the same account.

Never restore old ledger state over newer orders, reset balances to conceal loss, or clear risk locks as part of generic recovery. Reconcile account/order state before any separately reviewed production recovery. Keep unrelated services untouched. Use native path-safe cleanup only after verifying the exact sandbox target. Do not run heavy recovery drills on the trading host during monitoring.
