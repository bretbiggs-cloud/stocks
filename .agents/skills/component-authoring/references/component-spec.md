> Reference patterns from upstream, not installed Stocks APIs. Read `.agents/skills/README.md` for actual commands, private credential handling and scope before using these examples.

# Component and Configuration Standards Reference

## Directory Layout & Encapsulation Standards

Maintain a clean, standardized modular structure:

```text
project-root/
├── <component-name>/
│   ├── config.yml (or compose.yml)
│   ├── .env.example
│   └── src/
└── .env.example
```

- Each module or service must be self-contained and explicitly declare its configuration contracts.
- Shared libraries, global configuration, or orchestrator templates should reside in dedicated internal directories (e.g. `shared/`, `pkg/`, or `.configs/`) to prevent circular dependencies.

---

## Canonical Configuration Ordering & Formatting

Maintain consistent key ordering across declarative configurations:

```yaml
service:
  name: <service-name>
  image: <image>:<tag>
  user: "${PUID}:${PGID}"              # Non-root user identity
  restart: unless-stopped
  security:
    no_new_privileges: true
    capabilities_drop:
      - ALL
  environment:
    - PORT=${PORT:?PORT must be defined}
    - DATABASE_URL=${DATABASE_URL:?DATABASE_URL must be defined}
    - LOG_LEVEL=info                   # Static invariants inlined
  volumes:
    - ${DATA_DIR}/<service>/data:/app/data
    - ${SHARED_DIR}:/shared:ro         # Explicit read-only when possible
  ports:
    - "8080:8080"
  logging:
    max_size: "10m"
    max_file: 3
```

---

## Environment Variable Assertion Syntax

All runtime environment variables consumed by deployment manifests or application runtimes must be asserted strictly:

```yaml
${VARIABLE:?Error: VARIABLE must be set. See .env.example.}
```

### Invariant Rules:
1. **Never use inline fallback defaults** in production deployment manifests (e.g. avoid `${VAR:-default}`). All default values belong centrally in `.env.example`.
2. **Fixed component invariants** (such as static internal port bindings, internal timeouts, or log formats) should be hardcoded directly in configuration files rather than cluttering `.env.example`.
3. **Intentionally optional runtime values** (such as one-time setup tokens) must use `${OPTIONAL_KEY:-}` so execution succeeds when the token is omitted.
4. **Script Boundary**: Shell scripts should validate parameters explicitly via preconditions rather than relying on unhandled runtime expansion crashes.

---

## Privilege and Least-Privilege Execution Model

1. **Dedicated User Identities**:
   - Application processes must never run as root (`UID 0`) unless strictly required for low-level socket binding or kernel module interactions.
   - Run services as dedicated non-root users (e.g., standard UID `1000:100` or isolated service UIDs).
2. **Filesystem Isolation**:
   - Persistent data volumes should be owned by the service user.
   - Read-only mounts (`:ro`) must be used for static assets, certificates, or configuration files that the service does not modify.
3. **Process Sandboxing**:
   - Prevent privilege escalation via `no-new-privileges: true`.
   - Drop all default capabilities and re-add only what is strictly necessary (e.g. `NET_BIND_SERVICE`).
