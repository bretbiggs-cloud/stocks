> Reference patterns from upstream, not installed Stocks APIs. Read `.agents/skills/README.md` for actual commands, private credential handling and scope before using these examples.

# Component & Architecture Selection Matrix

## Architecture Evaluation Matrix

When onboarding a new project or planning a major evolution, evaluate candidate architectures and components against operational criteria:

| Category | Option | Pros | Cons / Trade-offs | Best Fit For |
| :--- | :--- | :--- | :--- | :--- |
| **Monolith vs. Services** | Modular Monolith | Single repo, easy atomic refactoring, simplified testing | Scales as single unit; deployment coupling | Early to mid-stage projects, small teams |
| | Microservices / Stacks | Independent scaling, isolated failure domains | Network latency, distributed debugging complexity | Multi-team organizations, distinct domain scaling |
| **Data Layer** | PostgreSQL | Robust ACID compliance, rich extensions, JSON support | Higher memory footprint than embedded DBs | Primary relational data store |
| | SQLite | Embedded, zero server administration, ultra-fast reads | Concurrency write bottlenecks | Local tools, single-node apps, edge runtimes |
| | Redis / Key-Value | Microsecond in-memory performance, pub/sub, caching | Volatile by default, memory-bound capacity | Session cache, job queues, ephemeral rate limits |
| **Ingress & Routing** | Reverse Proxy (Caddy / Nginx / Traefik) | Automated TLS, virtual host routing, security headers | Extra network hop, configuration learning curve | Multi-service web APIs, HTTPS termination |
| | Direct Service Binding | Simple setup, minimal latency | Manual TLS management, port binding conflicts | Internal-only tools, point-to-point sockets |

---

## Architectural Decision Records (ADRs)

Document major decisions using a lightweight ADR format:
1. **Context**: What forces or constraints are driving this decision?
2. **Decision**: What architectural path was chosen?
3. **Status**: Proposed / Accepted / Superseded.
4. **Consequences**: What positive trade-offs and negative liabilities are introduced?
