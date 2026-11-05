---
name: test-authoring
description: >-
  Systematic recipe and standards for authoring automated smoke, interconnect,
  routing, and security regression tests. Use when introducing new features,
  adding API endpoints, or writing reproduction tests for bug fixes.
---

# Stocks regression authoring

Adapted from coding-agent; read AGENTS.md and .agents/skills/README.md.

1. Identify the behavior and credible failure modes. Consult docs/testing.md and existing tests/test_*.py. The upstream references/suite-catalog.md is a pattern catalog; no Bash assertion helpers or HTTP services are installed here.
2. Add unittest cases with fake brokers, controlled clocks and temporary databases. Reproduce defects before or alongside the fix. Test uncertainty, stale/missing data and retry boundaries for execution changes.
3. Never load credentials, contact a broker, run NAS builds or submit trades in automated tests. Use standard-library mocks for external effects.
4. Run a targeted unittest while iterating, then `python tools/check.py` (equivalently `python manage.py test all`). Resolve failures without weakening assertions. Document untested boundaries.
5. Trading-rule changes additionally require historical evaluation and explicit deployment review. Passing infrastructure tests proves neither profit nor live readiness.
