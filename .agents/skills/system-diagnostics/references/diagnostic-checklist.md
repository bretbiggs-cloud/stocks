> Reference patterns from upstream, not installed Stocks APIs. Read `.agents/skills/README.md` for actual commands, private credential handling and scope before using these examples.

# Diagnostic Checklist and Common Failure Modes

## Quick Symptom Reference Matrix

| Symptom | Probable Cause | Diagnostic Command |
| :--- | :--- | :--- |
| `502 Bad Gateway` | Upstream service process dead or not listening on port | `netstat -tlpn` / `docker ps -f name=<svc>` |
| `504 Gateway Timeout` | Upstream process hanging, deadlock, or database lock | `journalctl -u <svc>` / `docker logs --tail 50 <svc>` |
| `Connection refused` | Target port closed or bound strictly to `127.0.0.1` | `ss -tuln \| grep <port>` |
| `Host not found / NXDOMAIN` | DNS search domain mismatch or container network unattached | `getent hosts <target-host>` |
| `403 Forbidden` | Ingress header restriction, CORS block, or file permissions | Check reverse proxy labels, ACLs, and `chmod` |
| `OOM Killed (Exit 137)` | Process memory usage exceeded container or host limit | `dmesg -T \| grep -i oom` |
| `Disk write error (No space)` | Storage volume full or inode table exhausted | `df -h` and `df -i` |

---

## Detailed Isolation Techniques

### 1. Distinguishing DNS from Network Failures
When an HTTP request fails:
1. First, attempt curl with direct IP and Host header:
   ```bash
   curl -v -H "Host: service.local" http://127.0.0.1:8080/
   ```
   - If this succeeds, network and application are fine; the issue is DNS lookup on the client or local resolver.
2. If this fails, test raw socket connectivity:
   ```bash
   nc -zvw2 127.0.0.1 8080
   ```
   - If socket connection is refused, the process is not listening. Check service runtime logs.

---

### 2. Investigating Database Deadlocks and Connection Pool Starvation
When an application slows down and begins dropping requests:
1. Check active database connections:
   ```sql
   -- PostgreSQL
   SELECT pid, query_start, state, query FROM pg_stat_activity WHERE state != 'idle';
   ```
2. Identify blocked queries and lock holders:
   ```sql
   -- PostgreSQL Lock Inspection
   SELECT blocked_locks.pid     AS blocked_pid,
          blocking_locks.pid    AS blocking_pid,
          blocked_activity.query    AS blocked_statement,
          blocking_activity.query   AS current_statement_in_blocking_process
   FROM  pg_catalog.pg_locks         blocked_locks
   JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
   JOIN pg_catalog.pg_locks         blocking_locks
        ON blocking_locks.locktype = blocked_locks.locktype
        AND blocking_locks.database IS NOT DISTINCT FROM blocked_locks.database
        AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
        AND blocking_locks.page IS NOT DISTINCT FROM blocked_locks.page
        AND blocking_locks.tuple IS NOT DISTINCT FROM blocked_locks.tuple
        AND blocking_locks.virtualxid IS NOT DISTINCT FROM blocked_locks.virtualxid
        AND blocking_locks.transactionid IS NOT DISTINCT FROM blocked_locks.transactionid
        AND blocking_locks.classid IS NOT DISTINCT FROM blocked_locks.classid
        AND blocking_locks.objid IS NOT DISTINCT FROM blocked_locks.objid
        AND blocking_locks.objsubid IS NOT DISTINCT FROM blocked_locks.objsubid
        AND blocking_locks.pid != blocked_locks.pid
   JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
   WHERE NOT blocked_locks.granted;
   ```
