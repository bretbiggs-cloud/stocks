> Reference patterns from upstream, not installed Stocks APIs. Read `.agents/skills/README.md` for actual commands, private credential handling and scope before using these examples.

# Component Lifecycle: 6-Touchpoint Architectural Checklist

This reference provides a comprehensive audit checklist and decommissioning protocol for managing services across their full lifecycle.

---

## 1. The 6-Touchpoint Architectural Checklist

When provisioning a new service, worker, or module, verify all six touchpoints before opening for review:

| Touchpoint | Focus Area | Required Artifacts & Assertions |
| :--- | :--- | :--- |
| **1. Specification & Code** | Module Encapsulation | - Code housed in `<component>/` or `src/<component>/`<br>- Non-root user identity configured (`PUID:PGID` or service account)<br>- Bounded structured logging (e.g. `max-size: 10m`, `max-file: 3`) |
| **2. Environment & Secrets** | Configuration Isolation | - Variables listed in `.env.example` with defaults or blank secrets (`KEY=`)<br>- Mandatory parameter expansion assertion: `${VAR:?Error: VAR required}`<br>- Zero hardcoded paths, personal usernames, or tokens |
| **3. Ingress & Routing** | Boundary Security | - Network bindings, virtual hosts, or API gateway routes declared<br>- Internal-only services isolated to private bridge / localhost<br>- TLS termination and security headers (HSTS, nosniff, CORS boundaries) applied |
| **4. Observability & Health** | Self-Healing Probes | - Deterministic health check endpoint implemented (`/health`, `/ready`)<br>- Probes verify vital dependencies without cascading failure loops<br>- Service status dashboard or monitoring metrics registered |
| **5. Persistence & Backups** | State Durability | - Persistent data standardized under `${DATA_DIR}/<service>/data`<br>- Non-root file permissions and ownership enforced<br>- Online staging dump configured for databases (PostgreSQL, SQLite) |
| **6. Automated Tests** | Regression Coverage | - Automated smoke tests verifying process health added to test harness<br>- Interface and contract assertions added to routing suite<br>- 100% green pass verified on `./manage.sh test all` |

---

## 2. Decommissioning & Retirement Protocol

When retiring or removing a component, execute the structured teardown sequence to prevent orphaned resources:

1. **Connection Drain & Graceful Teardown**:
   - Signal the component to stop accepting traffic and flush pending transactions.
   - Stop and remove runtime processes or containers:
     ```bash
     docker compose -f <component>/compose.yml down -v
     # or systemctl stop <service> && systemctl disable <service>
     ```
2. **Ingress & Interface Cleanup**:
   - Remove virtual host entries, reverse proxy routing rules, and DNS records pointing to the decommissioned service.
3. **Observability Deprecation**:
   - Remove health probes, dashboard entries, Prometheus metric scrapers, and log aggregation configs.
4. **Pre-Deletion State Archive**:
   - Take a final timestamped safety snapshot of persistent data:
     ```bash
     tar -czf "backups/archive-<component>-$(date +%Y%m%d).tar.gz" "${DATA_DIR}/<component>"
     ```
   - Delete the persistent directory after archive confirmation.
5. **Test Harness Cleanliness**:
   - Remove or deprecate tests associated with the retired service.
6. **Mainline Verification**:
   - Run the full test suite (`./manage.sh test all`) to guarantee no remaining services have broken dependencies.
