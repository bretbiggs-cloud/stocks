---
name: feature-completion
description: >-
  Standardized workflow for completing a feature branch: verify full test suite,
  stop on failure, execute systematic documentation and runbook audit, update CHANGELOG.md,
  purge temporary planning artifacts, commit, push, merge to main, and apply dual SemVer/CalVer tags.
---

> Stocks adaptation: first read `AGENTS.md` and `.agents/skills/README.md`. Their mappings override generic commands below; examples never authorize service or trading changes.


# Feature Completion Runbook

This skill automates the safe, verified graduation of a feature branch into `codex/paper-trading-setup`.

## Prerequisites
- Currently on an active feature branch (`git branch --show-current` != `codex/paper-trading-setup`).
- Plan execution and intermediate implementation changes have been committed to the feature branch.
- **MANDATORY USER SIGN-OFF**: The agent has paused, presented the implementation state and test results to the user, and received explicit user approval to proceed with feature completion, changelog drafting, artifact cleanup, and merging. Never auto-trigger this skill without user confirmation.
- Working tree has all feature changes staged or ready to commit.

---

## Execution Procedure

### Step 1: Run Full Regression and Smoke Test Suite
Execute the entire test suite against the target environment:
```bash
./.harness/test-runner.sh all
# or language-specific test runner: npm test / cargo test / pytest
```
* **Assertion**: All test suites must PASS (or explicitly documented skips).
* **CRITICAL STOP-ON-FAILURE**: If any test fails:
  1. STOP immediately.
  2. Do NOT touch `CHANGELOG.md`.
  3. Do NOT delete planning documents.
  4. Do NOT commit, merge, or tag.
  5. Report the exact test failure and logs to the user and wait for instructions.

### Step 2: Systematic Documentation and Runbook Audit
Before writing release notes or committing, conduct a comprehensive audit across all documentation, runbooks, and skills to ensure they accurately reflect the feature's changes:

1. **Branch Diff Inspection**:
   Inspect all modified files on the feature branch relative to `codex/paper-trading-setup`:
   ```bash
   git diff --stat codex/paper-trading-setup...HEAD
   ```
   Identify every touched component, API endpoint, interface contract, configuration key, or data schema.

2. **Core Operational Documentation (`README.md`, `.docs/`)**:
   - **Component Catalog & Interfaces**: If services, modules, exposed ports, API routes, or CLI commands were added, modified, or retired, update reference tables in `README.md` and related docs.
   - **Architecture & System Flow**: If high-level workflows, dependencies, or communication topologies were altered, update architecture documentation and diagrams.
   - **Environment Variables**: If `.env.example` templates were modified, ensure corresponding additions/removals are clearly documented.

3. **Operational Skills and Runbooks (`.agents/skills/`)**:
   - Review skills related to the modified components (e.g., `component-lifecycle`, `system-diagnostics`, `data-safety`, `test-authoring`).
   - Audit for stale terminology or legacy patterns: Search for deprecated function names, obsolete parameters, or outdated code snippets:
     ```bash
     git grep -i "<deprecated-term>" .agents/skills/
     ```
   - Verify that all skill execution runbooks and code block snippets accurately describe active declarative patterns.

4. **Architecture Specifications (`.agents/artifacts/architecture.md`)**:
   - Verify that `.agents/artifacts/architecture.md` aligns with current architectural invariants, component relationships, and persistent data paths.

5. **Style and Brevity Verification**:
   - Ensure all updated documentation adheres to project-wide documentation conventions: value brevity, align detail to audience/scope, eliminate redundant fine details, and omit internal development minutiae.

6. **Memory Bank Synchronization (`.agents/memory/`)**:
   - Synchronize `activeContext.md` by clearing completed feature focus, updating active patterns, and noting upcoming tasks.
   - Synchronize `progress.md` by recording completed capabilities, updating the automated test count, and noting release tags. Never leave finished milestones marked pending.

### Step 3: Update Changelog (SemVer Minor/Major Releases)
Review [SemVer and CalVer Guidelines](./references/semver-calver-guidelines.md) for version tier determination, roll-up synthesis, and format rules.
* **Tagging & Changelog Scope**:
  - Only features automatically receive `semver.minor` or `semver.major` bumps.
  - All `semver.minor` and `semver.major` changes require a curated `CHANGELOG.md` entry.
  - Critical or major security remediations may also warrant a `semver.minor` release.
  - Routine security updates, bugfixes, and patches are typically `semver.patch` or CalVer-only and do not generate a standalone semantic minor version or changelog entry.
  - If the agent cannot confidently determine whether the changes qualify for major, minor, or patch, it must present its analysis, recommend a version tier, and explicitly ask the user for confirmation before proceeding.
* **Roll-Up Overview**:
  - The `CHANGELOG.md` entry must provide a high-level overview of ALL changes across the codebase since the previous changelog entry.
  - The entry rolls up and synthesizes intermediate CalVer commits, hotfixes, refactors, and the completed feature into a unified milestone summary.
* Calculate next minor SemVer (e.g. `v1.2.0`) and today's CalVer (`date +%Y.%-m.%-d`).
* Prepend the new release section to `CHANGELOG.md` directly below the top header:
  ```markdown
  ## [<Next-SemVer>] / [<CalVer>] - <Feature Title> (YYYY-MM-DD)

  ### Added
  - <Bullet points describing user-facing additions>

  ### Changed
  - <Bullet points describing architectural or convention modifications>

  ### Fixed
  - <Bullet points describing remediated issues>

  ### Security
  - <Bullet points describing security hardening or access control updates>
  ```

### Step 4: Clean Up Temporary Planning Artifacts
Remove ephemeral planning and design documents while preserving persistent architectural artifacts:
```bash
# Remove only the reviewed temporary plan for this feature; preserve evidence and unrelated plans.
```
* Note: Keep persistent architectural specifications (such as `.agents/artifacts/architecture.md`) intact.

### Step 5: Final Feature Branch Commit and Push
Stage all modified files (including code, documentation, `CHANGELOG.md`, and rules):
```bash
git add <reviewed-explicit-paths>
git commit -m "feat(<feature-name>): complete <feature-name> implementation and release notes"
git push origin <feature-branch>
```

### Step 6: Merge into Main and Apply Dual Release Tags
Switch to `codex/paper-trading-setup`, synchronize with remote, merge the feature branch, apply tags, and push:
```bash
git checkout codex/paper-trading-setup
git pull --ff-only origin codex/paper-trading-setup
git merge <feature-branch>

# Determine versions
NEXT_SEMVER="<Calculated-SemVer>"
CURRENT_CALVER="<Calculated-CalVer>"

# Tag release
git tag -a "${NEXT_SEMVER}" -m "Release ${NEXT_SEMVER} / ${CURRENT_CALVER}"
git tag -a "${CURRENT_CALVER}" -m "Release ${CURRENT_CALVER}"

# Push mainline and tags
git push origin codex/paper-trading-setup --tags

# Remove local feature branch
git branch -d <feature-branch>
```
