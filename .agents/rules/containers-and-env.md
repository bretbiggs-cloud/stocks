---
trigger: glob
globs:
  - "*compose*.yml"
  - "*compose*.yaml"
  - "Dockerfile*"
  - ".env*"
---

# Containers and Environment Configuration Standards

This rule applies automatically whenever creating, modifying, or reviewing container manifests, Dockerfiles, and environment templates.

## 1. Environment Variable Assertion Syntax
- Deployment manifests and Compose files must enforce required variables using strict assertion syntax:
  ```yaml
  ${VARIABLE:?Error: VARIABLE must be set. See .env.example.}
  ```
- **Never use inline fallback defaults** in production deployment manifests (e.g. avoid `${VAR:-default}`); defaults belong centrally in `.env.example`.
- Fixed invariants (e.g., static log levels, internal ports) must be directly inlined as static values in configuration files rather than exposed as environment variables.
- Truly optional keys (e.g. one-time tokens) must use `${TOKEN:-}` so restarts succeed after token invalidation.

## 2. Least-Privilege Execution Model
- Application services and background workers must run under dedicated, non-root user identities (`PUID:PGID` or service account UID).
- Drop all unnecessary system capabilities (`cap_drop: [ALL]`).
- Enable security restrictions (`no-new-privileges: true` or `security_opt`).
- Mount persistent volumes read-only (`:ro`) when write access is not strictly required.

## 3. Canonical Service Key Ordering
Maintain consistent 2-space YAML key ordering across container service blocks:
`image`, `container_name`, `hostname`, `user`, `restart`, `privileged`, `cap_add`, `cap_drop`, `security_opt`, `sysctls`, `devices`, `group_add`, `environment`, `volumes`, `ports`, `networks`, `logging`, `labels`.
