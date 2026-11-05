---
name: start-project
description: >-
  Interactive onboarding and scaffolding runbook for developers instantiating,
  customizing, or orienting to a software project. Guides project orientation,
  requirements assessment, platform/environment adaptation, adaptation planning,
  secrets scaffolding, and verified initial execution.
---

# Orient a new Stocks workspace

Adapted from coding-agent; read AGENTS.md, product/architecture/testing docs and the three public memory files. Read private operator context only when available locally. Do not ask for secrets in chat.

Inspect the branch and working tree. A clone does not authorize account access or trading. The separate daily-research branch may contain newer runtime code than the default; verify before describing deployed behavior.

Use the existing Python environment or create a virtual environment and install requirements-dev.txt as appropriate. Run `python manage.py setup` and `python manage.py test all`. Setup validates files only: it does not create .env, generate keys, install hooks, normalize permissions or start services.

For a separately requested deployment, read stacks/stocks/.env.example and private operations guidance. Host mappings go in a private environment file; credentials remain a separate protected JSON file. Plan concrete changes and preserve all risk/reconciliation boundaries. No fresh-clone automatic deployment.

The supporting architecture-matrix and environment-adapters references are optional design prompts, not a requirement to provision their example infrastructure.
