---
name: component-lifecycle
description: >-
  Standardized operational runbook for provisioning a new service/component or cleanly
  decommissioning an existing one across all 6 architectural touchpoints:
  implementation specification, environment templates, interface routing, observability,
  data persistence/backups, and automated smoke test assertions.
---

> Stocks adaptation: first read `AGENTS.md` and `.agents/skills/README.md`. Their mappings override generic commands below; examples never authorize service or trading changes.


# Component Lifecycle Runbook (Addition & Decommissioning)

This skill coordinates adding a new component/service or decommissioning an existing one across the 6 core architectural touchpoints of the application platform.

```text
       1. Component Specification (code, manifest, build)
             â”‚
       2. Environment & Secrets (.env.example & .env)
             â”‚
       3. Ingress, Routing & Contracts (APIs, reverse proxy, ports)
             â”‚
       4. Observability & Health (status probes, dashboards, logs)
             â”‚
       5. Persistence & Backups (volumes, migrations, snapshots)
             â”‚
       6. Automated Tests (smoke, unit, integration assertions)
```

---

## Prerequisites
- Reference [6-Touchpoint Architectural Checklist and Decommissioning Protocol](./references/touchpoints-checklist.md) for required artifacts and validation criteria.

---

## Procedure A: Adding a New Component or Service

### Touchpoint 1: Component Specification
1. Create a dedicated directory named `<component-name>/` (lowercase, alphanumeric, hyphens).
2. Author the component manifest or code files adhering to:
   - Encapsulated module boundaries.
   - Non-root user identity and least-privilege security posture.
   - Structured logging with bounded log rotation.

### Touchpoint 2: Environment Templates (`.env.example`)
1. Add new required environment variables to `.env.example`:
   - List variable names with sensible local defaults or blank secrets (`API_KEY=`).
   - Include explanatory comments describing what each variable controls.
2. Update only authorized private host mappings; Stocks API credentials remain in a separate protected JSON file.

### Touchpoint 3: Ingress, Routing & Interface Contracts
1. Configure network bindings, API routes, or reverse proxy virtual hosts.
2. Ensure internal-only services are not bound to external public interfaces.
3. Apply TLS termination and security headers (HSTS, nosniff, CORS boundaries) at the ingress layer.

### Touchpoint 4: Observability & Health Probes
1. Implement a deterministic health check endpoint (e.g. `/health`, `/status`).
2. Verify that health checks probe vital dependencies (e.g. database connectivity) without cascading failure loops.
3. Add service status tracking or dashboard widgets where applicable.

### Touchpoint 5: Persistence & Backup Policy
1. Standardize persistent storage paths under a unified data root (e.g. `${DATA_DIR}/<service>/data`).
2. Ensure correct filesystem permissions and ownership.
3. If database-backed, configure automated migration scripts and staging dump procedures for zero-downtime backups.

### Touchpoint 6: Automated Smoke & Contract Tests
1. Author automated test checks verifying runtime health and status.
2. Add routing and interface contract assertions to the test harness.
3. Run the full test suite (`./.harness/test-runner.sh all`) to verify a complete green pass.

---

## Procedure B: Decommissioning / Retiring a Component

1. **Gracefully Stop & Drain Service**:
   - Drain active connections and gracefully shut down running instances:
     ```bash
     # Stop service gracefully
     docker compose -f <component>/compose.yml down
     # or systemctl stop <service>
     ```
2. **Remove Ingress & Routing Rules**:
   - Delete routing entries, proxy hosts, or API gateway forwarding rules pointing to the retired service.
3. **Remove Observability & Health Probes**:
   - Remove metrics collectors, log aggregators, and dashboard widgets for the component.
4. **Archive or Prune Persistent Data**:
   - Take a final pre-removal safety snapshot of the persistent data:
     ```bash
     tar -czf "archive-<component>-$(date +%Y%m%d).tar.gz" "${DATA_DIR}/<component>"
     ```
   - Preserve the ledger and reports. Deletion requires explicit scoped authorization beyond backup confirmation.
5. **Clean Up Automated Tests**:
   - Remove or decommission assertions associated with the retired service in the test harness.
6. **Remove Component Directory**:
   - Remove the retired component directory from the repository.
7. **Verify Mainline Health**:
   - Run the full test suite to confirm that no remaining services have broken dependencies or broken references:
     ```bash
     ./.harness/test-runner.sh all
     ```
