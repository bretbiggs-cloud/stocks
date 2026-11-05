# System patterns

Paper-only fixed endpoints, deterministic validation, single writer, stable order IDs, cash reservations and persistent risk locks are mandatory. Exits precede research. Unknown conditions block entries. Preserve separate broker-paper and hypothetical ledgers, costs and failed research.

Python unittest plus tools/check.py is the regression authority. The management CLI delegates to it using the current interpreter. Offline tests do not prove profit or live deployment health. No hooks or active CI are promised.

Public memory contains generic development state only. Private operator notes stay ignored and are read separately when present. AGENTS.md routes all agents to the same rules; Windows-compatible pointer files avoid symlink requirements. Generic skills never grant trading/deployment authority.
