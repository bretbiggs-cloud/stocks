> Reference patterns from upstream, not installed Stocks APIs. Read `.agents/skills/README.md` for actual commands, private credential handling and scope before using these examples.

# Environment & Platform Adapters Reference

## Platform Adaptation Guidelines

When deploying or adapting a project across different deployment targets, apply consistent patterns:

### 1. Local Development vs. Production Containers
- **Local Development**:
  - Hot-reloading enabled.
  - Verbose logging (`LOG_LEVEL=debug`).
  - Ephemeral test databases or local SQLite files.
  - Relaxed CORS and TLS termination for localhost.
- **Production Container Environment**:
  - Minified production builds without development toolchains.
  - Structured JSON logging (`LOG_LEVEL=info` or `warn`).
  - Read-only container rootfs where feasible.
  - Strict secret injection via environment variables or secret vaults.

---

### 2. CI/CD Pipeline Adapters
- Configure test harness to run headless with deterministic timeouts.
- Set `NO_COLOR=1` or detect non-TTY outputs to avoid ANSI escape sequences in pipeline log scrapers.
- Use exit code `77` to mark conditionally skipped test suites without causing false build failures.

---

### 3. Filesystem and Storage Adapters
- Standardize on POSIX-compliant paths.
- Avoid hardcoding absolute host paths (e.g. `/home/user/...`). Use environment-driven roots (`${DATA_DIR}`).
- Set explicit umasks and verify user ownership on mounted volumes.
