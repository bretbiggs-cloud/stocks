#!/usr/bin/env bash
# Stocks development CLI adapter. Requires Bash and the selected Python.
# Usage: ./manage.sh setup|audit|test all|help. Delegates all validation and
# exit status to manage.py; no setup, permission or service mutations here.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "${PYTHON:-python}" "${SCRIPT_DIR}/manage.py" "$@"
