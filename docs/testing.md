# Feature regression checks

Run after every feature implementation and before deployment:

```sh
python -m pip install -r requirements-dev.txt
python tools/check.py
```

The runner checks Python syntax and discovers the complete unittest suite. It returns nonzero on a failure or zero discovered tests. Socket connection attempts are blocked during test discovery/execution. Tests use fake broker responses and temporary databases; no Alpaca credentials, NAS access or real orders are needed. This is an accidental-network guard, not an operating-system sandbox for untrusted code.

## Coverage map

| Area | Regression evidence |
| --- | --- |
| Risk | Wrong/live endpoint, account status, cash reservations, exposure limits, stale quotes, loss locks |
| Order lifecycle | Ambiguous submission, partial fills, cancellation, restart, duplicate exits and reconciliation |
| Operations | Single writer, host pressure, unavailable metrics, backup integrity |
| News and trial modes | Missing/stale/future/wrong-symbol news, incomplete pagination, paper date authorization, mock isolation, exits during news failure |
| Historical replay | Future bars cannot alter earlier signals, next-bar fill timing, missing fills, chronological splits, tampered/incomplete cache rejection |
| Deployment | Compose accepts public example values and rejects missing required settings |

See individual `tests/test_*.py` cases for exact scenarios. Coverage is not exhaustive and test count is not proof of correctness or profitable trading.

## GitHub checks

The prepared local `.github/workflows/regression.yml` is intended to run on pushes, pull requests and manual dispatch. Publication is currently blocked because the GitHub OAuth login lacks the workflow scope; automatic checks are not active yet. Tests run on Windows/Linux and Python 3.12/3.13; a separate Linux job validates Compose without starting containers. Permissions are read-only, no secrets are supplied and no deployment step exists. Results appear in GitHub Actions and pull-request checks. Branch protection is not configured by this workflow, so a failing check does not itself prevent a direct push or merge.

## New feature acceptance

Add tests that demonstrate the intended behavior and plausible failure modes. For a bug fix, first reproduce the bug in a failing test. Preserve existing safeguards; do not weaken assertions merely to make checks pass. Run the full command, inspect failures, and document any untested behavior. Changed trading rules also require historical evaluation; these tests do not substitute for backtesting or forward paper observation.

The suite does not prove real API availability, broker fill quality, every exchange-calendar edge case, PC-off/reboot behavior, or strategy profitability. Deployment changes require separate private read-only verification; trading tests against an account require explicit authorization. Do not enable a second executor or replay production orders as a test.

Daily research coverage includes broader-universe discovery, broker instrument exclusions, deterministic capped rankings, 48-hour expiry, pagination/API failures, missing daily bars, stale/corrupt artifacts, premarket-only one-request steps, restart persistence, full entry validation outside the legacy list, aggregate held/pending risk, cost-inclusive daily locks, cross-version daily caps, and exits when research is missing. Production feed coverage, broker metadata classification and future signal availability still require observation.
