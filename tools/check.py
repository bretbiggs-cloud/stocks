"""Run offline regression tests from any working directory. Never loads credentials."""
import ast
from contextlib import ExitStack
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]

def main():
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT))
    for directory in ("stocks", "tests", "tools"):
        for path in (ROOT / directory).rglob("*.py"):
            ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    # Fail accidental external access rather than testing against a real account.
    with ExitStack() as stack:
        for target in ("socket.socket.connect", "socket.socket.connect_ex", "socket.create_connection"):
            stack.enter_context(patch(target, side_effect=AssertionError("Network disabled in regression suite")))
        suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
        if suite.countTestCases() == 0:
            raise RuntimeError("No regression tests discovered")
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    raise SystemExit(main())
