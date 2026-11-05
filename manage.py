"""Stocks development harness; no credentials, service management or network calls.

setup validates local readiness without writing files. audit additionally checks
Git-tracked paths. test all delegates to the existing offline regression runner.
Run with the project's Python interpreter from any current working directory.
"""
import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
ALIASES = ("CLAUDE.md", "GEMINI.md", "agent.md", ".cursorrules")
SKILLS = ("feature-initiation", "feature-completion", "test-authoring",
          "component-authoring", "component-lifecycle", "codebase-audit",
          "system-diagnostics", "data-safety", "start-project")
REQUIRED = ("AGENTS.md", ".agents/rules/stocks.md", ".agents/rules/project-conventions.md",
            ".agents/UPSTREAM.md", ".agents/LICENSE-MPL-2.0", "tools/check.py",
            ".agents/skills/README.md", "docs/harness.md") + tuple(
    f".agents/memory/{name}.md" for name in ("activeContext", "systemPatterns", "progress")
) + tuple(f".agents/skills/{name}/SKILL.md" for name in SKILLS)
PRIVATE_FILES = {".docs/decisions.md", ".docs/setup-plan.md", ".docs/operations.md",
                 ".agents/artifacts/current-state.md", "start_here.md", "credentials.json"}
PRIVATE_DIRS = {"private", "runtime", "reports", "backups", ".codex-attachments", ".scripts"}


def readiness(root):
    """Return bounded structural failures; never provision or repair files."""
    issues = []
    for name in REQUIRED + ALIASES:
        path = root / name
        if not path.is_file() or not path.read_text(encoding="utf-8").strip():
            issues.append(f"Missing or empty harness file: {name}")
    for name in ALIASES:
        path = root / name
        if path.is_file() and "[AGENTS.md](AGENTS.md)" not in path.read_text(encoding="utf-8"):
            issues.append(f"Entrypoint does not route to AGENTS.md: {name}")
    return issues


def private_path(name):
    """Conservative path audit, not content scanning or proof of no secrets."""
    path = Path(name.replace("\\", "/").lower())
    parts = path.parts
    base = path.name
    return (str(path).replace("\\", "/") in PRIVATE_FILES
            or any(part in PRIVATE_DIRS for part in parts)
            or base == "credentials.json" or base == ".env"
            or (base.startswith(".env.") and base != ".env.example")
            or base.endswith((".db", ".log")) or ".sqlite" in base)


def audit(root):
    """Inspect Git index names only; do not open private file contents."""
    issues = readiness(root)
    result = subprocess.run(["git", "-C", str(root), "ls-files", "-z"],
                            capture_output=True, text=True, check=False)
    if result.returncode:
        issues.append("Git tracked-file inspection failed")
    else:
        count = sum(private_path(name) for name in result.stdout.split("\0") if name)
        if count:
            issues.append(f"Tracked private/runtime paths detected: {count}; review locally")
    return issues


def main(argv=None, root=ROOT):
    """Return errors intact; no deployment commands are exposed."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("setup", "audit", "test", "help"), nargs="?", default="help")
    parser.add_argument("suite", nargs="?")
    args = parser.parse_args(argv)
    if args.suite and (args.command != "test" or args.suite != "all"):
        parser.error("Only 'test all' accepts a suite argument")
    if args.command == "help":
        parser.print_help()
        return 0
    if args.command == "test":
        return subprocess.run([sys.executable, str(root / "tools/check.py")], cwd=root, check=False).returncode
    try:
        issues = audit(root) if args.command == "audit" else readiness(root)
    except (OSError, UnicodeError):
        print("Harness inspection failed; check local file access and Git availability", file=sys.stderr)
        return 1
    for issue in issues:
        print(issue, file=sys.stderr)
    if not issues:
        print("Harness checks passed (development only; no runtime verification)")
    return int(bool(issues))


if __name__ == "__main__":
    raise SystemExit(main())
