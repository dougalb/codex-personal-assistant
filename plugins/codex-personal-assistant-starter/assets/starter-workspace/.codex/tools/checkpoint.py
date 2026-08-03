#!/usr/bin/env python3
"""Validate and commit only assistant-owned durable memory changes; never push."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


ALLOWED_PREFIXES = ("knowledge/",)
ALLOWED_FILES = {
    "state/knowledge-checkpoint.json",
    "state/automation-runs.md",
    "state/open-questions.md",
    "state/action-log.md",
    "state/memory-approvals.json",
    "state/attention-events.json",
    "state/attention-calibration.json",
}
GIT_EXECUTABLE = shutil.which("git") or ("/usr/bin/git" if Path("/usr/bin/git").exists() else "git")


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([GIT_EXECUTABLE, "-C", str(root), *args], text=True, capture_output=True)


def allowed(path: str) -> bool:
    return path in ALLOWED_FILES or any(path.startswith(prefix) for prefix in ALLOWED_PREFIXES)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a validated local personal-assistant checkpoint.")
    parser.add_argument("-m", "--message", default="Update personal assistant knowledge")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    lint = subprocess.run([sys.executable, str(root / ".codex" / "tools" / "knowledge_bundle.py"), "--root", str(root), "lint"])
    if lint.returncode:
        return lint.returncode
    staged = git(root, "diff", "--cached", "--name-only")
    staged_paths = [line for line in staged.stdout.splitlines() if line]
    unrelated = [path for path in staged_paths if not allowed(path)]
    if unrelated:
        print("Refusing checkpoint: unrelated files are already staged:", file=sys.stderr)
        print("\n".join(f"- {path}" for path in unrelated), file=sys.stderr)
        return 2
    status = git(root, "status", "--porcelain", "--", "knowledge", "state/knowledge-checkpoint.json", "state/automation-runs.md", "state/open-questions.md", "state/action-log.md")
    paths = sorted({line[3:] for line in status.stdout.splitlines() if len(line) > 3 and allowed(line[3:])})
    if paths:
        add = git(root, "add", "--", *paths)
        if add.returncode:
            print(add.stderr, file=sys.stderr)
            return add.returncode
    staged = git(root, "diff", "--cached", "--name-only")
    staged_paths = [line for line in staged.stdout.splitlines() if line]
    if not staged_paths:
        print("No assistant-owned durable changes to checkpoint.")
        return 0
    unrelated = [path for path in staged_paths if not allowed(path)]
    if unrelated:
        print("Refusing checkpoint: unrelated staged files detected.", file=sys.stderr)
        return 2
    commit = git(root, "commit", "--no-verify", "-m", args.message)
    if commit.returncode:
        print(commit.stderr or commit.stdout, file=sys.stderr)
        return commit.returncode
    print(commit.stdout.strip())
    print("Checkpoint committed locally. No remote operation was attempted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
