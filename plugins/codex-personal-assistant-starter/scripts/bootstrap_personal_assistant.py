#!/usr/bin/env python3
"""Create a local Codex Personal Assistant starter workspace."""

from __future__ import annotations

import argparse
import datetime as dt
import shutil
import sys
from pathlib import Path


DEFAULT_TARGET = Path.home() / "Documents" / "Codex" / "Personal Assistant"


def copy_starter(source: Path, target: Path, force: bool, dry_run: bool) -> tuple[list[Path], list[Path]]:
    created: list[Path] = []
    skipped: list[Path] = []

    for item in sorted(source.rglob("*")):
        rel = item.relative_to(source)
        dest = target / rel

        if item.is_dir():
            if not dry_run:
                dest.mkdir(parents=True, exist_ok=True)
            continue

        if dest.exists() and not force:
            skipped.append(rel)
            continue

        if not dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, dest)
        created.append(rel)

    return created, skipped


def append_bootstrap_log(target: Path, created: list[Path], skipped: list[Path], dry_run: bool) -> None:
    if dry_run:
        return

    log_path = target / "state" / "bootstrap-log.md"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    lines = [
        "",
        f"## {timestamp}",
        "",
        "Starter workspace bootstrap completed.",
        "",
        f"- Files created or replaced: {len(created)}",
        f"- Existing files preserved: {len(skipped)}",
        "",
    ]
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a Codex Personal Assistant starter workspace.")
    parser.add_argument("--target", default=str(DEFAULT_TARGET), help="Destination folder for the assistant workspace.")
    parser.add_argument("--force", action="store_true", help="Replace existing starter files.")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen without writing files.")
    args = parser.parse_args()

    plugin_root = Path(__file__).resolve().parents[1]
    source = plugin_root / "assets" / "starter-workspace"
    target = Path(args.target).expanduser().resolve()

    if not source.exists():
        print(f"Starter assets not found: {source}", file=sys.stderr)
        return 2

    if not args.dry_run:
        target.mkdir(parents=True, exist_ok=True)

    created, skipped = copy_starter(source, target, args.force, args.dry_run)
    append_bootstrap_log(target, created, skipped, args.dry_run)

    action = "Would create or replace" if args.dry_run else "Created or replaced"
    print(f"Target: {target}")
    print(f"{action}: {len(created)} files")
    print(f"Preserved existing: {len(skipped)} files")
    if skipped:
        print("Preserved files:")
        for rel in skipped:
            print(f"- {rel}")
    print("Next: run the first-run interview and fill the context and state files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
