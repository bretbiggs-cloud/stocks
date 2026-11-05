---
name: component-authoring
description: >-
  Procedural recipe and validation checklist for authoring, modifying, or refactoring
  services, modules, and components in the project. Use when creating new services,
  editing configuration manifests, adjusting environment variables, or auditing permissions.
---

> Stocks adaptation: first read `AGENTS.md` and `.agents/skills/README.md`. Their mappings override generic commands below; examples never authorize service or trading changes.


# Component Authoring Runbook

This skill guides the creation and modification of services, modules, and components in accordance with project architectural conventions.

## Prerequisites
- Reference [Component and Configuration Standards Reference](./references/component-spec.md) for structure, key ordering, and privilege rules.
- Ensure the repository working tree is clean or on an active feature branch.

---

## Authoring Procedure

### Step 1: Directory Setup & Module Isolation
1. Create a dedicated directory for the component:
   ```bash
   mkdir -p src/<component-name> # or <component-name>/
   ```
2. Verify the directory name is lowercase, alphanumeric, and uses hyphens or underscores in line with repository conventions.
3. Keep component assets encapsulated: code, localized configs, templates, and tests belong in predictable, cohesive paths.

### Step 2: Configuration Construction & Schema Adherence
1. Define configuration manifests (e.g. `compose.yml`, `config.yaml`, or application settings).
2. Apply canonical key ordering and standard formatting.
3. Enforce mandatory parameter expansion assertion syntax on every required runtime variable:
   ```yaml
   ${VARIABLE:?Error: VARIABLE must be set in .env. See .env.example.}
   ```
4. Never hardcode sensitive secrets, credentials, or machine-specific paths into configuration manifests.

### Step 3: Environment Variable Configuration
1. Create or update `.env.example`:
   - List all component-specific configuration keys (`PORT=`, `DATABASE_URL=`, `API_KEY=`) with sensible local defaults or blank secrets (`SECRET=`).
   - Group variables logically by component with clear explanatory comments.
2. Synchronize or populate the local untracked `.env` file without committing secrets.

### Step 4: Privilege & Security Hardening
1. Ensure services execute under non-root identities whenever possible:
   - In containers: configure `user: "${PUID}:${PGID}"` or leverage base images that step down privileges via entrypoints.
   - In native processes: run under dedicated system service accounts.
2. Apply defense-in-depth:
   - Drop unnecessary capabilities (`cap_drop: [ALL]`).
   - Enable security protections (`no-new-privileges: true`).
   - Mount persistent storage with strict read-only flags (`:ro`) when write access is not needed.

### Step 5: Verification & Testing
1. Validate configuration syntax and linting:
   ```bash
   # Config validation (example: docker compose config, or linter check)
   docker compose -f <component>/compose.yml config
   ```
2. Verify component startup and health probes:
   ```bash
   # Check service status or curl healthcheck endpoint
   curl -sf http://localhost:<port>/health
   ```
3. Author automated smoke and contract tests in the project test suite (see `test-authoring` skill).
