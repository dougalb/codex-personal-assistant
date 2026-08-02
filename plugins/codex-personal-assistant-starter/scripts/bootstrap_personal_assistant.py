#!/usr/bin/env python3
"""Bootstrap or upgrade a Git-backed Codex Personal Assistant workspace.

The script deliberately has no network or credential behaviour.  Scheduled tasks and
connector access are configured from Codex after the generated project is trusted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


DEFAULT_TARGET = Path.home() / "Documents" / "Codex" / "Personal Assistant"
GIT_EXECUTABLE = shutil.which("git") or ("/usr/bin/git" if Path("/usr/bin/git").exists() else "git")


@dataclass
class CopyResult:
    created: list[Path]
    preserved: list[Path]
    review: list[Path]
    removed: list[Path]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_git(target: Path, *args: str, check: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [GIT_EXECUTABLE, "-C", str(target), *args], text=True, capture_output=True, check=check
    )


def git_root(target: Path) -> Path | None:
    result = run_git(target, "rev-parse", "--show-toplevel")
    if result.returncode:
        return None
    return Path(result.stdout.strip()).resolve()


def verify_repository_boundary(target: Path) -> Path | None:
    root = git_root(target)
    if root is not None and root != target:
        raise RuntimeError(
            f"Refusing to reuse parent repository {root}. Choose that repository root or a folder outside it."
        )
    return root


def load_upgrade_manifest(source: Path) -> dict[str, object]:
    path = source.parent / "upgrade-manifests" / "v0.1.0.json"
    if not path.exists():
        return {"files": {}, "removed": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def copy_starter(source: Path, target: Path, force: bool, upgrade: bool, dry_run: bool) -> CopyResult:
    created: list[Path] = []
    preserved: list[Path] = []
    review: list[Path] = []
    removed: list[Path] = []
    prior = load_upgrade_manifest(source)
    old_files: dict[str, str] = dict(prior.get("files", {}))
    old_removed: dict[str, str] = dict(prior.get("removed", {}))
    review_root = target / "archive" / "upgrade-review" / "v0.2.0"

    for item in sorted(source.rglob("*")):
        if item.is_dir():
            continue
        rel = item.relative_to(source)
        dest = target / rel
        rel_text = rel.as_posix()
        if not dest.exists():
            if not dry_run:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dest)
            created.append(rel)
            continue
        if force:
            if not dry_run:
                shutil.copy2(item, dest)
            created.append(rel)
            continue
        if upgrade and old_files.get(rel_text) == digest(dest):
            if not dry_run:
                shutil.copy2(item, dest)
            created.append(rel)
            continue
        if upgrade and old_files.get(rel_text):
            incoming = review_root / (rel_text + ".incoming")
            if not dry_run:
                incoming.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, incoming)
            review.append(rel)
            continue
        preserved.append(rel)

    if upgrade:
        for rel_text, old_digest in old_removed.items():
            dest = target / rel_text
            if dest.exists() and digest(dest) == old_digest:
                if not dry_run:
                    dest.unlink()
                removed.append(Path(rel_text))
            elif dest.exists():
                review.append(Path(rel_text))
        if review and not dry_run:
            report = review_root / "MIGRATION-REPORT.md"
            report.parent.mkdir(parents=True, exist_ok=True)
            report.write_text(
                "# Codex Personal Assistant 0.2 upgrade review\n\n"
                "The existing files below differed from the shipped 0.1.0 versions and were preserved. "
                "Review each adjacent `.incoming` candidate before merging it.\n\n"
                + "".join(f"- `{path.as_posix()}`\n" for path in sorted(set(review)))
                + "\nRemoved only unmodified retired files:\n\n"
                + "".join(f"- `{path.as_posix()}`\n" for path in removed),
                encoding="utf-8",
            )
    return CopyResult(created, preserved, review, removed)


def configure_project_git(target: Path) -> list[str]:
    notes: list[str] = []
    hooks = run_git(target, "config", "--get", "core.hooksPath")
    if hooks.returncode:
        run_git(target, "config", "core.hooksPath", ".githooks", check=True)
        notes.append("Installed project pre-commit hook path (.githooks).")
    else:
        notes.append(f"Preserved existing core.hooksPath ({hooks.stdout.strip()}).")
    # Git shell aliases execute at the repository root. Python 3 is a prerequisite of this plugin.
    run_git(target, "config", "alias.pa-checkpoint", "!python3 .codex/tools/checkpoint.py", check=True)
    notes.append("Configured git pa-checkpoint (local-only; it never pushes).")
    return notes


def git_identity_available(target: Path) -> bool:
    return bool(run_git(target, "config", "user.name").stdout.strip()) and bool(
        run_git(target, "config", "user.email").stdout.strip()
    )


def managed_initial_paths(source: Path, target: Path, created: list[Path]) -> list[Path]:
    """Select only generated or byte-for-byte shipped files for a first commit.

    This lets an unpacked v0.1 starter become a complete repository without staging
    arbitrary pre-existing material in the same non-empty folder.
    """
    managed = set(created)
    for item in source.rglob("*"):
        if not item.is_file():
            continue
        rel = item.relative_to(source)
        destination = target / rel
        if destination.exists() and digest(destination) == digest(item):
            managed.add(rel)
    return sorted(managed)


def initial_commit(target: Path, managed: list[Path]) -> tuple[bool, str]:
    files = [str(path) for path in managed if (target / path).exists()]
    if not files:
        return False, "No generated files required staging."
    run_git(target, "add", "--", *files, check=True)
    staged = run_git(target, "diff", "--cached", "--name-only")
    if not staged.stdout.strip():
        return False, "No managed changes required an initial commit."
    if not git_identity_available(target):
        return False, (
            "Git was initialized but has no identity. Configure `git config --global user.name \"Your Name\"` "
            "and `git config --global user.email \"you@example.com\"`, then run `git commit -m "
            "'Initialize Codex Personal Assistant'`."
        )
    result = run_git(target, "commit", "-m", "Initialize Codex Personal Assistant")
    if result.returncode:
        return False, result.stderr.strip() or result.stdout.strip()
    return True, "Created initial Git commit containing only generated assistant files."


def main() -> int:
    parser = argparse.ArgumentParser(description="Create or upgrade a Codex Personal Assistant workspace.")
    parser.add_argument("--target", default=str(DEFAULT_TARGET), help="Destination assistant repository root.")
    parser.add_argument("--force", action="store_true", help="Replace existing starter-managed files.")
    parser.add_argument("--dry-run", action="store_true", help="Show actions without writing or initializing Git.")
    parser.add_argument("--upgrade", action="store_true", help="Safely migrate a 0.1 workspace to 0.2.")
    args = parser.parse_args()
    if args.force and args.upgrade:
        parser.error("--force and --upgrade cannot be used together")

    plugin_root = Path(__file__).resolve().parents[1]
    source = plugin_root / "assets" / "starter-workspace"
    target = Path(args.target).expanduser().resolve()
    if not source.exists():
        print(f"Starter assets not found: {source}", file=sys.stderr)
        return 2

    if not args.dry_run:
        target.mkdir(parents=True, exist_ok=True)
    try:
        existing_root = verify_repository_boundary(target)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.dry_run:
        result = copy_starter(source, target, args.force, args.upgrade, True)
        print(f"Target: {target}")
        print(f"Would create or replace: {len(result.created)} files")
        print(f"Would preserve: {len(result.preserved)} files")
        print("Would initialize Git." if existing_root is None else f"Would use repository: {existing_root}")
        return 0

    initialized = False
    if existing_root is None:
        init = run_git(target, "init")
        if init.returncode:
            print(init.stderr.strip() or "Git initialization failed.", file=sys.stderr)
            return 2
        initialized = True
        existing_root = target

    result = copy_starter(source, target, args.force, args.upgrade, False)
    notes = configure_project_git(target)
    print(f"Target: {target}")
    print(f"Created or replaced: {len(result.created)} files")
    print(f"Preserved existing: {len(result.preserved)} files")
    if result.review:
        print(f"Upgrade review candidates: {len(result.review)} (archive/upgrade-review/v0.2.0)")
    if result.removed:
        print(f"Retired unmodified legacy files: {len(result.removed)}")
    for note in notes:
        print(note)
    if initialized:
        committed, message = initial_commit(target, managed_initial_paths(source, target, result.created))
        print(message)
        if not committed and not git_identity_available(target):
            print("Setup is incomplete until that initial commit succeeds.")
    else:
        print("Existing repository preserved; new files remain reviewable as working-tree changes.")
    print("Next: trust and reopen this project in Codex, then use $codex-personal-assistant-bootstrap.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
