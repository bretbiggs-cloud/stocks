---
name: codebase-audit
description: >-
  Systematic drift detection and compliance auditing runbook for software projects.
  Audits process runtimes, service & dependency drift, untracked processes, environment
  variable skew, filesystem permissions, network port exposure, security blocks,
  scheduled job currency, and system service configuration drift.
---

> Stocks adaptation: first read `AGENTS.md` and `.agents/skills/README.md`. Their mappings override generic commands below; examples never authorize service or trading changes.


# Codebase Drift Detection & Project Audit Runbook

This skill provides a systematic diagnostic procedure to detect drift between tracked declarative configurations (source code, manifests, `.env.example`, documentation, rules) and the live runtime environment.

---

## Prerequisites
- Reference [Codebase Audit Inspection Commands & Severity Rules](./references/audit-rules.md) for diagnostic query patterns and punchlist classification criteria.

---

## Audit Checklist & Procedures

### Audit Area 1: Service & Runtime Drift Detection

1. **Declared vs. Running Process Alignment**:
   Compare declared services in manifests against active running processes or containers:
   ```bash
   # In containerized environments:
   grep -rhE "^[[:space:]]*container_name:" */compose.yml | awk '{print $2}' | sort -u
   docker ps --format '{{.Names}}' | sort -u
   ```
   - **Untracked Processes**: Running processes/containers not declared in repository manifests.
   - **Missing/Stopped Services**: Declared services that are absent or stopped in runtime.

2. **Image, Dependency & Package Skew**:
   - Check if running images or dependencies have drifted from declared versions.
   - Run dependency vulnerability and outdated-package audits:
     ```bash
     npm audit / cargo audit / pip-audit / govulncheck ./...
     ```

3. **Environment Variable & Secret Skew**:
   - Check that all variables defined in `.env.example` templates exist in the active runtime `.env` file.
   - Identify unpopulated required secrets (`SECRET=`, `API_KEY=`) or unexpanded variable placeholders:
     ```bash
     grep -E '^[A-Z0-9_]+=$' .env || true
     ```

4. **Port Exposure & Interface Binding Drift**:
   - Verify that services are not binding to unintended network interfaces or exposed ports:
     ```bash
     netstat -tuln / ss -tuln
     # or in Docker:
     docker ps --format 'table {{.Names}}\t{{.Ports}}'
     ```
   - Flag any internal backend ports accidentally bound to public interfaces (`0.0.0.0` or public IPs) instead of localhost or isolated internal bridges.

5. **Documentation & Catalog Drift**:
   - Verify that all active components, endpoints, and configuration parameters are accurately documented in `README.md`.
   - Ensure deprecated or removed components have been scrubbed from documentation.

---

### Audit Area 2: Storage, File Permissions & Access Control

1. **Least-Privilege Ownership & Modes**:
   - Verify that data directories and runtime caches are owned by the intended non-root user (e.g. `1000:100`):
     ```bash
     find data/ -maxdepth 2 -not -user 1000 -not -user root 2>/dev/null || true
     ```
   - Ensure secrets and `.env` files have restricted read permissions (`chmod 600 .env`).
   - Ensure executable scripts have proper execute bits (`chmod 755`) without excessive world-write permissions (`chmod 777` is strictly prohibited).

2. **Read-Only Volume & File Enforcement**:
   - Audit that services mounting shared media, certificates, or configuration files are mounting them strictly read-only (`:ro`).

---

### Audit Area 3: Interface Routing, SSL & Security Hardening

1. **Routing and Endpoint Validation**:
   - Execute the interface and routing test suite:
     ```bash
     ./.harness/test-runner.sh interfaces
     ```
2. **TLS / SSL Certificate Expiration**:
   - Check expiration dates on active SSL certificates:
     ```bash
     openssl x509 -enddate -noout -in certs/server.crt 2>/dev/null || true
     ```
3. **Endpoint Hardening Probes**:
   - Run negative security tests verifying that administrative routes (`/metrics`, `/swagger`, `/debug`) are inaccessible from public ingress points.

---

### Audit Area 4: Background Jobs, Queues & Daemons

1. **Scheduled Job & Timer Health**:
   - Check systemd timers, cron schedules, or background queues:
     ```bash
     systemctl list-timers --all
     # or crontab -l
     ```
   - Verify that scheduled jobs are active and have not failed or halted silently.
2. **Message Queue & Worker Processing**:
   - Check for stalled queues, high message lag, or accumulating dead-letter queues.

---

### Audit Area 5: Backup Automation & Snapshot Currency

1. **Snapshot Currency Probes**:
   - Verify that recent database dumps or filesystem snapshots exist and are younger than 24 hours.
2. **Integrity Validation**:
   - Verify that backup archives are valid and uncorrupted (e.g. `tar -tzf archive.tar.gz > /dev/null`).

---

## Audit Output Report Format

Compile audit findings into a prioritized punchlist categorized by operational severity:

- **Clean**: All declarative definitions match live runtime state with zero drift, verified permissions, and passed security checks.
- **Service & Configuration Drift Warning**:
  - Outdated dependencies or image digest skew.
  - Environment variable skew between `.env.example` and `.env`.
  - Stale backup snapshots (> 24 hours).
  - Missing catalog documentation for newly deployed modules.
  - Minor permission discrepancies that do not cause service outages.
- **Critical / Security Hazard**:
  - Untracked or orphaned processes/containers running on host.
  - Unauthorized public port exposure of internal services or databases.
  - Failing health check probes or crash-looping services.
  - Exposed secrets, world-writable sensitive files (`777`), or broken authentication boundaries.
  - Inactive or failing scheduled backup jobs.
