"""Development-harness failure and preservation contracts, without services."""
from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("stocks_manage", Path(__file__).resolve().parents[1] / "manage.py")
manage = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(manage)


class HarnessTests(unittest.TestCase):
    def seed(self, root):
        for name in manage.REQUIRED + manage.ALIASES:
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("[AGENTS.md](AGENTS.md)", encoding="utf-8")

    def call(self, argv, root):
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            return manage.main(argv, root)

    def test_setup_preserves_private_data_hooks_and_permissions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.seed(root)
            for name in (".env", ".git/hooks/pre-commit", ".agents/memory/private/active.md"):
                p = root / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text("local content", encoding="utf-8")
            before = {p.relative_to(root): (p.read_bytes(), p.stat().st_mode) for p in root.rglob("*") if p.is_file()}
            self.assertEqual(self.call(["setup"], root), 0)
            self.assertEqual(self.call(["setup"], root), 0)
            after = {p.relative_to(root): (p.read_bytes(), p.stat().st_mode) for p in root.rglob("*") if p.is_file()}
            self.assertEqual(before, after)

    def test_missing_entrypoint_and_wrong_routing_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.seed(root)
            (root / "CLAUDE.md").unlink()
            self.assertEqual(self.call(["setup"], root), 1)
            (root / "CLAUDE.md").write_text("wrong rules", encoding="utf-8")
            self.assertEqual(self.call(["setup"], root), 1)

    def test_private_paths_rejected_public_examples_allowed(self):
        for path in (".env", "stacks/stocks/.env.prod", ".agents/memory/private/state.md",
                     ".docs/decisions.md", "reports/daily.json", "nested/credentials.json", "data/a.sqlite-wal"):
            self.assertTrue(manage.private_path(path), path)
        for path in ("stacks/stocks/.env.example", ".agents/memory/activeContext.md", "stocks/broker.py"):
            self.assertFalse(manage.private_path(path), path)

    def test_audit_git_failure_and_private_index_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.seed(root)
            for result in (subprocess.CompletedProcess([], 1, "", "failure"),
                           subprocess.CompletedProcess([], 0, ".env\0", "")):
                with patch.object(manage.subprocess, "run", return_value=result):
                    self.assertEqual(self.call(["audit"], root), 1)

    def test_test_dispatch_propagates_failure_and_uses_current_interpreter(self):
        with patch.object(manage.subprocess, "run", return_value=subprocess.CompletedProcess([], 7)) as run:
            self.assertEqual(self.call(["test", "all"], manage.ROOT), 7)
            self.assertEqual(run.call_args.args[0], [manage.sys.executable, str(manage.ROOT / "tools/check.py")])

    def test_unknown_command_and_suite_fail(self):
        for argv in (["deploy"], ["hook", "install"], ["test", "missing"], ["setup", "all"]):
            with self.assertRaises(SystemExit) as raised:
                self.call(argv, manage.ROOT)
            self.assertNotEqual(raised.exception.code, 0)

    def test_checkout_entrypoints_and_skills_present(self):
        self.assertEqual(manage.readiness(manage.ROOT), [])
