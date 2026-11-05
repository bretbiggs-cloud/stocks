---
name: system-diagnostics
description: >-
  Systematic diagnostic algorithm for troubleshooting software services, network routing,
  DNS resolution, socket connectivity, process crashes, and database connection failures.
---

> Stocks adaptation: first read `AGENTS.md` and `.agents/skills/README.md`. Their mappings override generic commands below; examples never authorize service or trading changes.


# System Diagnostics Runbook

This skill provides a step-by-step diagnostic workflow to troubleshoot routing, interface failures, process crashes, DNS mismatches, and database connectivity issues.

## Prerequisites
- Reference [Diagnostic Checklist and Common Failure Modes](./references/diagnostic-checklist.md) for symptom-specific diagnostic commands.

---

## Diagnostic Flowchart

```text
[ Issue Detected ]
       │
       ├── Ingress / Routing Failure? ──────> Run Phase 1 (Ingress & Proxy Triage)
       ├── Process Crash / Unhealthy? ───────> Run Phase 2 (Runtime & Log Triage)
       ├── Inter-Service Network Failure? ──> Run Phase 3 (Socket & DNS Triage)
       └── Database / Storage Failure? ─────> Run Phase 4 (Persistence & Lock Triage)
```

---

## Diagnostic Procedures

### Phase 1: Ingress, Reverse Proxy & Virtual Host Triage
1. **Check Ingress / Gateway Status and Logs**:
   ```bash
   # Check logs of reverse proxy, webserver, or API gateway
   docker logs --tail 50 <proxy-container>
   # or journalctl -u <gateway-service> -n 50 --no-pager
   ```
2. **Test Direct Endpoint Reachability (Bypassing Public DNS)**:
   ```bash
   # Use client impersonation to test virtual host headers directly against local IP
   curl -k -v -H "Host: <target-domain>" http://127.0.0.1:<port>/health
   ```
   - **Status 200 / 302**: Ingress and routing are functioning correctly; issue is local client DNS or external network resolution.
   - **Status 502 / 504**: Upstream application process is crashed, stopped, or unreachable on the configured internal socket/port.
   - **Status 401 / 403**: Ingress security rule, header filter, or authentication middleware is rejecting the request.

---

### Phase 2: Process Lifecycle & Runtime Log Triage
1. **Verify Process State and Restart Counts**:
   ```bash
   # Check running status, exit codes, and health check output
   docker ps -a --filter name=<service>
   # or systemctl status <service>
   ```
2. **Inspect stderr and stdout Logs**:
   ```bash
   docker logs --tail 100 <service>
   # or journalctl -u <service> -n 100 -e
   ```
   - Look for panic stack traces, unhandled exceptions, missing environment variables, or schema migration errors.
3. **Verify Resource Limits & OOM Kills**:
   ```bash
   # Check if kernel OOM killer terminated the process
   dmesg -T | grep -i -E "oom|out of memory|killed process"
   ```

---

### Phase 3: Inter-Service Network & DNS Resolution Triage
1. **Verify Network Membership**:
   ```bash
   # Check assigned container IP and bridge network
   docker inspect <service> --format '{{json .NetworkSettings.Networks}}'
   ```
2. **Test Internal Service-to-Service DNS**:
   ```bash
   # Query service hostname resolution from calling service
   docker exec <caller-service> getent hosts <target-service>
   # or dig @127.0.0.1 <target-service>
   ```
3. **Test Raw TCP Socket Reachability**:
   ```bash
   # Probe socket without sending application payloads
   nc -zvw3 <target-host> <target-port>
   # or curl -v telnet://<target-host>:<target-port>
   ```

---

### Phase 4: Database & Persistence Layer Triage
1. **Probe Database Socket Readiness**:
   ```bash
   # PostgreSQL readiness probe:
   pg_isready -h localhost -p 5432 -U app_user
   # Redis ping:
   redis-cli ping
   ```
2. **Check Database Connection Pools & Locks**:
   - Verify connection pool limits have not been exhausted.
   - In PostgreSQL: `SELECT count(*) FROM pg_stat_activity;`
3. **Check Filesystem Disk Space and Inodes**:
   ```bash
   df -h
   df -i
   ```
   - *Note*: An exhaustion of disk inodes (`Use% 100%` on `df -i`) prevents file creation even when available gigabytes remain.
4. **Check Filesystem Permissions**:
   - Verify the process user has write permissions to data directories.
