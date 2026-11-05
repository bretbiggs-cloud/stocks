> Reference patterns from upstream, not installed Stocks APIs. Read `.agents/skills/README.md` for actual commands, private credential handling and scope before using these examples.

# Codebase Audit: Inspection Commands & Severity Rules Reference

This reference catalogs diagnostic commands, drift detection queries, and operational severity criteria for codebase and infrastructure audits.

---

## 1. Diagnostic Command Catalog

### Runtime & Process Alignment
```bash
# Compare declared container names against running instances
grep -rhE "^[[:space:]]*container_name:" */compose.yml | awk '{print $2}' | sort -u
docker ps --format '{{.Names}}' | sort -u

# Audit active listening ports
ss -tuln || netstat -tuln

# Audit container image digest skew
for c in $(docker ps --format '{{.Names}}'); do
  running_id="$(docker inspect -f '{{.Image}}' "${c}")"
  image_tag="$(docker inspect -f '{{.Config.Image}}' "${c}")"
  latest_id="$(docker image inspect -f '{{.Id}}' "${image_tag}" 2>/dev/null || echo "unknown")"
  if [[ "${latest_id}" != "unknown" && "${running_id}" != "${latest_id}" ]]; then
    echo "IMAGE DRIFT: Container '${c}' is running outdated digest"
  fi
done
```

### Environment & Secret Integrity
```bash
# Find blank required secrets in active .env
grep -E '^[A-Z0-9_]+=$' .env || true

# Check for variables declared in .env.example that are missing in .env
comm -23 \
  <(grep -oE '^[A-Z0-9_]+' .env.example | sort -u) \
  <(grep -oE '^[A-Z0-9_]+' .env | sort -u)
```

### Filesystem & Security Boundary Probes
```bash
# Check for unauthorized files owned by root or unexpected users
find data/ -maxdepth 2 -not -user 1000 -not -user root 2>/dev/null || true

# Audit for dangerous world-writable files (777)
find . -maxdepth 3 -type f -perm -002 -not -path "*/.git/*"

# Check TLS certificate expiration
openssl x509 -enddate -noout -in certs/server.crt 2>/dev/null || true
```

---

## 2. Severity Classification Matrix

| Finding Type | Severity | Required Action |
| :--- | :--- | :--- |
| **Exposed Secret / World-Writable Permissions** | Critical Hazard | Stop immediately, revoke credentials, and re-apply `chmod 600`. |
| **Untracked / Orphaned Process Binding Ports** | Critical Hazard | Identify process, isolate network interface, or terminate process. |
| **Health Probe Failure / Crash Looping** | Critical Hazard | Inspect stdout/stderr logs and remediate runtime failure. |
| **Image Digest Skew (Running Stale Build)** | Warning | Schedule rolling restart or recreate container with updated digest. |
| **Environment Variable Skew (`.env.example` vs `.env`)** | Warning | Synchronize missing keys to runtime `.env`. |
| **Backup Snapshot Age > 24 Hours** | Warning | Verify scheduled backup timer and trigger manual backup if needed. |
| **Documentation Catalog Skew** | Warning | Update README and component references to match active code. |
