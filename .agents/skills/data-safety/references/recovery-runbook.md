> Reference patterns from upstream, not installed Stocks APIs. Read `.agents/skills/README.md` for actual commands, private credential handling and scope before using these examples.

# Disaster Recovery and Snapshot Mechanics

## Architecture & Principles

Persistent application state consists of:
1. **Dynamic Databases**: Relational (PostgreSQL, MySQL) or embedded (SQLite).
2. **Persistent File Assets**: User uploads, configurations, and state files.
3. **Configuration & Secrets**: Untracked `.env` files and certificates.

---

## Detailed Restoration Sequences

### 1. Granular Single-Service Restoration
When an isolated component experiences corruption, restore only that specific service:
1. Stop the target service to release locks:
   ```bash
   docker compose stop <service> # or systemctl stop <service>
   ```
2. Restore the specific data directory from the verified backup archive.
3. If database-backed, import the staged SQL logical dump:
   ```bash
   psql -U app_user -d app_db < staged_backup.sql
   ```
4. Verify file permissions (`chmod` / `chown`) on restored directories.
5. Restart the target service and run smoke tests.

---

### 2. Full Environment Disaster Recovery
When total data loss or filesystem corruption occurs:
1. **Halt Runtimes**: Stop all active services to avoid concurrent writes.
2. **Safety Snapshot**: Take a final pre-recovery snapshot of the current state (in case forensics are needed).
3. **Restore Files**: Extract the target backup archive into the target root directory.
4. **Permissions Audit**: Verify non-root user ownership on data directories.
5. **Database Initialization**: Bring up database services, wait for socket readiness, and restore logical database dumps.
6. **Start Dependent Services**: Bring up application and background worker services in topological order.
7. **Execute Verification Test Suite**: Run the complete test suite to confirm 100% PASS.
