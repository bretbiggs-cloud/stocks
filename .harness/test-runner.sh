#!/usr/bin/env bash
# Compatibility test entrypoint. Requires Bash and project Python.
# Usage: ./.harness/test-runner.sh [all]. Runs the same offline Python suite
# as tools/check.py and propagates its failure status. No runtime access.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec "${PYTHON:-python}" "${SCRIPT_DIR}/manage.py" test "$@"
