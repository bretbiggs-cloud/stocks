# Active context

Updated 2026-11-05. Branch: codex/agent-harness, based on default codex/paper-trading-setup.

Harness migration implementation is complete and awaiting user review. Preserve existing paper safeguards and private context. All 63 offline tests pass through both tools/check.py and manage.py; setup and audit pass. No release or deployment is part of this task.

Important branch boundary: codex/daily-research contains the separate deployed daily-research upgrade. This branch retains default-branch trading code. Reconcile those branches explicitly before any future release/deployment; never deploy this checkout over the running upgrade. Public memory is branch-local, not live account evidence.
