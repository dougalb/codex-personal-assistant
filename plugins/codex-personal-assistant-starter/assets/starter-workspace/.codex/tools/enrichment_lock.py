#!/usr/bin/env python3
"""Small, dependency-free lock for serialized personal-assistant memory mutation."""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path


def lock_path() -> Path:
    return Path(__file__).resolve().parents[2] / "state" / ".enrichment.lock"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("acquire", "release", "status"))
    args = parser.parse_args()
    path = lock_path()
    if args.command == "status":
        if path.exists():
            print(path.read_text(encoding="utf-8"))
            return 1
        print("unlocked")
        return 0
    if args.command == "acquire":
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            print(f"enrichment lock is already held: {path}", file=sys.stderr)
            return 1
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump({"pid": os.getpid(), "host": socket.gethostname(), "acquired_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")}, handle)
        print(path)
        return 0
    if not path.exists():
        print("enrichment lock was not present")
        return 0
    path.unlink()
    print("released")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
