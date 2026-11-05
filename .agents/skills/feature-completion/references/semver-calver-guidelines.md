> Reference patterns from upstream, not installed Stocks APIs. Read `.agents/skills/README.md` for actual commands, private credential handling and scope before using these examples.

# SemVer and CalVer Release Guidelines (Agile Trunk Governance)

## 1. Versioning Model Overview

The repository tracks changes using a hybrid dual-versioning scheme tailored for **Agile Trunk-Based Development**:

1. **Semantic Versioning (SemVer)**: `vMAJOR.MINOR.PATCH` (e.g. `v1.2.0`)
   - Identifies functional and architectural milestones.
   - Always prefixed with a lower-case `v` to distinguish software releases from CalVer.
   - Used for primary capabilities, breaking changes, and public interface contracts.
2. **Calendar Versioning (CalVer)**: `YYYY.M.D.N` (e.g. `2026.11.4.1`)
   - Identifies chronological snapshots, routine deployments, and configuration commits on `codex/paper-trading-setup`.
   - Adheres to PEP 440 format (no leading zeros in month/day, monotonic sequence revision `.N` for same-day releases).

---

## 2. Tagging Cadence in Agile Trunk Development

In agile trunk-based git, all feature branches merge directly into `codex/paper-trading-setup`. The `codex/paper-trading-setup` branch is always in a releasable state.

| Release Tier | Trigger Event | Cadence | Tagging Action | Changelog Requirement |
| :--- | :--- | :--- | :--- | :--- |
| **Tier 1: Semantic Minor** | Completed feature branch merging to `codex/paper-trading-setup` with new capabilities. | Several times per sprint / continuous | **Dual Tag**: `vX.Y.0` + `YYYY.M.D.N` | **Mandatory**: Curated roll-up milestone entry. |
| **Tier 2: Semantic Major** | Breaking contract changes, architectural redesigns, schema resets. | Infrequent / deliberate | **Dual Tag**: `vX.0.0` + `YYYY.M.D.N` | **Mandatory**: Migration guide & breaking notices. |
| **Tier 3: Trunk Patch / Hotfix** | Routine bug fixes, configuration tweaks, or doc updates. | As needed | **CalVer-Only**: `YYYY.M.D.N` | **Deferred**: Rolled up into next Tier 1 SemVer release. |

### Cadence Invariants:
1. **Never Tag Intermediate Commits on Feature Branches**: Feature branch commits remain untagged. Tags are applied *only* on the merge commit on `codex/paper-trading-setup`.
2. **Annotated Tags Only**: All tags must be created as annotated tags (`git tag -a <tag> -m "<message>"`) to preserve tagger identity, timestamp, and message for `git describe`.

---

### 3. Pre-Tagging Proposal Checklist & Approval Gate

The agent must **NEVER** apply a tag autonomously. Before executing any tagging operation on `codex/paper-trading-setup`, the agent must present the **Tagging Proposal Packet** to the user and wait for explicit confirmation:

```text
[ Pre-Tagging Proposal Packet ]
1. Test Verification:
   All regression suites passed (./manage.sh test all) with 0 failures.

2. Commit Roll-Up Analysis:
   List of commits on main since last SemVer tag:
   - <commit_sha> <commit_message>

3. Version Tier Recommendation:
   "Recommend semver-minor (v1.1.0) paired with CalVer 2026.11.4.1
    Reason: Adds new capability without breaking existing contracts."

4. Changelog Preview:
   Drafted CHANGELOG.md entry categorizing Added, Changed, Fixed, and Security items.
```

**Human Decision Gate**:
The user must explicitly approve or adjust the recommended version tier before the agent commits `CHANGELOG.md`, merges to `codex/paper-trading-setup`, and tags.

---

## 4. Roll-Up Release Synthesis

Each `CHANGELOG.md` entry must provide a high-level overview of **ALL** changes across the codebase since the previous changelog entry.

Because multiple routine patches, bug fixes, and CalVer commits accumulate on `codex/paper-trading-setup` between minor feature releases:
- The changelog entry for a new SemVer release must roll up and synthesize those intermediate commits alongside the new feature.
- Aggregate changes into curated, meaningful bullet points categorized under `Added`, `Changed`, `Fixed`, and `Security`.
- **Deployer-Focused Brevity & Scope**:
  - Write entries strictly from the perspective of users, consumers, and maintainers.
  - Highlight user-facing operational impacts, breaking contracts, service additions/removals, API/CLI updates, and security postures.
  - Avoid purely internal development minutiae: omit lines-of-code metrics, internal test assertion counts/pass rates, internal loop constructs, and issue tracker ticket noise.
- Omit trivial commits, typos, or negligible micro-edits.

---

## 5. Changelog Entry Format Example

```markdown
## [1.2.0] / [2026.11.4.1] - Dedicated Background Worker & Event Queue (2026-11-04)

### Added
- Dedicated event queue consumer service with automated backoff retry and dead-letter queue.
- Automated health check probes and contract assertion test suite.

### Changed
- Standardized environment variable missing parameter assertions across all service manifests.
- Migrated default connection pool timeouts from 30s to 10s to prevent socket starvation.

### Fixed
- Remediated memory leak in websocket event dispatcher during client reconnection storms.

### Security
- Enforced non-root execution container profiles with dropped capabilities (`cap_drop: [ALL]`).
```
