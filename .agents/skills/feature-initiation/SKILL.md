---
name: feature-initiation
description: >-
  Standardized workflow for starting new features: synchronize main with remote origin,
  create a feature branch (codex/<name>), scaffold an initial architectural plan,
  execute an interactive grill-me design review to eliminate bloat and maintain golden-path
  conventions, and commit the refined plan artifact to the feature branch.
---

> Stocks adaptation: first read `AGENTS.md` and `.agents/skills/README.md`. Their mappings override generic commands below; examples never authorize service or trading changes.


# Feature Initiation and Design Review Runbook

This skill automates the disciplined kickoff of a new feature branch, including mainline synchronization, branch isolation, architectural drafting, and an adversarial design review ("grill-me") before code implementation begins.

## Prerequisites
- Working directory is clean (`git status` reports no untracked or uncommitted changes).
- Reference [Grill-Me Persona & Critique Framework](./references/grill-me-persona.md) for review posture and questions.

---

## Execution Procedure

### Step 1: Mainline Synchronization
Always branch from the latest state of `origin/codex/paper-trading-setup` to avoid drift:
```bash
git checkout codex/paper-trading-setup
git pull --ff-only origin codex/paper-trading-setup
```

### Step 2: Branch Creation
Create and switch to a descriptive feature branch adhering to the `codex/<name>` convention:
```bash
git checkout -b codex/<feature-name>
```

### Step 3: Plan Prompt & Initial Architectural Draft
1. Prompt the user for requirements, constraints, or feature scope if not already provided.
2. Author an initial architectural plan document at `docs/features/plan_<feature-name>.md`.
3. Ensure the initial draft outlines:
   - **Problem Statement & Scope**: What problem is being solved and what is intentionally out of scope.
   - **Proposed Architecture & Components**: Services, modules, data structures, or external dependencies introduced or modified.
   - **Interface & API Contracts**: Network bindings, function signatures, schemas, or routing changes.
   - **Environment & Secrets**: Required configuration variables, `.env.example` keys, and defaults.
   - **Persistence & State**: File persistence, database migrations, or volume mapping changes.
   - **Automated Test Strategy**: Specific test assertions, unit checks, integration cases, or regression tests needed.
4. Update `.agents/memory/activeContext.md` to document the active feature focus, decisions, and planned steps.

### Step 4: Interactive "Grill-Me" Review Cycle
Adopt the persona of a **Principal Software & Systems Architect**:
- **Core Stance**: Ruthlessly simplify, eliminate waste, reduce custom/bespoke glue code, enforce declarative golden-path patterns, and protect long-term maintainability.
- **Review Strategy**:
  1. **Question assumptions**: Can standard language primitives, built-in library features, or existing framework tools replace custom code?
  2. **Critique deviations**: Identify unnecessary abstractions, leaky boundaries, over-engineering, or violation of project conventions.
  3. **Identify failure modes**: Edge cases, network partitions, unhandled error states, security boundaries, race conditions, and migration failures.
  4. **Propose alternatives**: For every flagged critique or hazard, offer a concrete, simpler design alternative.
- Present targeted questions and alternative proposals to the user. Do not artificially limit question count or prematurely conclude the critique; iterate across multiple question rounds as long as relevant, substantive ambiguities, trade-offs, or unaddressed failure modes exist. Do not begin implementation until all design trade-offs are settled.

### Step 5: Iterative Plan Convergence and Commit
1. Refine `docs/features/plan_<feature-name>.md` based on user feedback and resolved architectural decisions.
2. Commit the approved plan artifact directly to the feature branch so design history is tracked in git:
   ```bash
   git add docs/features/plan_<feature-name>.md
   git commit -m "docs(plan): add architectural plan for <feature-name>"
   ```

### Step 6: Plan Execution, Intermediate Commit, and User Review Checkpoint (MANDATORY)
1. Execute the implementation steps according to the approved plan using relevant implementation skills (`component-authoring`, `test-authoring`, `data-safety`).
2. Verify runtime health and execute automated tests (e.g. `./.harness/test-runner.sh` or project test suite).
3. Commit all implementation changes to the feature branch:
   ```bash
   git add <reviewed-explicit-paths>
   git commit -m "feat(<feature-name>): implement <feature-name> changes"
   ```
4. **CRITICAL MANDATORY PAUSE**: Stop immediately. Do NOT run `feature-completion`.
5. **Report & Solicit User Input**: Present a concise operational summary of the current state, runtime behavior, and test verification results to the user.
6. **Wait for User Input**: Explicitly ask the user to inspect, test, and approve the state before proceeding. NEVER proceed autonomously to release notes, changelog updates, artifact cleanup, mainline merge, or tagging until the user provides explicit confirmation.
