> Reference patterns from upstream, not installed Stocks APIs. Read `.agents/skills/README.md` for actual commands, private credential handling and scope before using these examples.

# Automated Test Suite Catalog and Assertion Patterns

## Suite Organization

All tests are orchestrated via the automated test harness (e.g. `./.harness/test-runner.sh [suite]`) and organized by functional boundary:

| Suite / Category | Scope & Assertions |
| :--- | :--- |
| `runtime` / `containers` | Verifies process lifecycle, daemon healthchecks, container uptime, and zero restart crashes. |
| `interfaces` / `routing` | Tests HTTP/gRPC endpoints, routing rules, virtual host reverse proxying, SSL termination, and HTTP status codes (`200`/`302`). |
| `interconnect` / `network` | Tests service-to-service DNS resolution, internal API communication, message broker queues, and database sockets (`5432`, `6379`). |
| `security` | Negative security tests asserting that protected paths require auth, invalid inputs are rejected, and internal/admin metrics are blocked (`401`/`403`). |
| `persistence` / `storage` | Tests database schema migrations, file snapshot integrity, volume permissions, and state recovery across restarts. |

---

## Assertion Helper Functions

The test harness provides standard assertion helpers:

```bash
# Assert string or value equality
assert_equals "expected" "actual" "Test description"

# Assert command exits with return code 0
assert_success "curl -sf http://localhost:8080/health" "Health endpoint reports success"

# Assert command fails (non-zero return code)
assert_failure "curl -sf http://localhost:8080/admin" "Unauthenticated admin request fails"

# Assert HTTP status code from curl
assert_http_status "http://localhost:8080/api/data" 200 "Data endpoint returns 200 OK" -H "Authorization: Bearer valid-token"

# Assert regex match against output
assert_matches "^v[0-9]+\.[0-9]+" "${version_output}" "Version output matches SemVer pattern"
```

---

## Writing Client-Impersonated HTTP and Interface Tests

When testing reverse proxies, virtual hosts, or API gateways that require specific Host headers or simulated client origins:

```bash
test_service_vhost() {
  local host_header="api.internal.local"
  local target_url="http://127.0.0.1:8080/health"
  local expected_status=200

  local actual_status
  actual_status=$(curl -sk -o /dev/null -w "%{http_code}" -H "Host: ${host_header}" "${target_url}")

  assert_equals "${expected_status}" "${actual_status}" "Virtual host ${host_header} resolves via gateway"
}
```

---

## Handling Slow or Resource-Constrained Environments

When running in resource-constrained environments (CI runners, high disk I/O, heavy background builds):
- Storage and network latency increases.
- Avoid tight sleep loops or microsecond timeouts; use exponential backoff polling for service readiness probes.
- Allow targeted sub-suite execution (`./.harness/test-runner.sh interfaces`) instead of forcing monolithic heavy scans during active debug cycles.
