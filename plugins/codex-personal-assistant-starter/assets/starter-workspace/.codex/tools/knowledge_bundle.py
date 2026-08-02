#!/usr/bin/env python3
"""Dependency-free maintenance commands for the assistant's OKF v0.2 bundle.

Frontmatter values intentionally use JSON syntax, which is valid YAML. This keeps the
profile portable while allowing deterministic parsing with Python's standard library.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REQUIRED = ("type", "title", "description", "status", "generated", "sources")
RESERVED = {"index.md", "log.md"}
LINK = re.compile(r"(?<!!)\[[^]]*\]\(([^)]+)\)")
WORD = re.compile(r"[\w-]+", re.UNICODE)


class BundleError(ValueError):
    pass


@dataclass
class Document:
    path: Path
    relative: Path
    metadata: dict[str, Any]
    body: str


def project_root(argument: str | None) -> Path:
    if argument:
        return Path(argument).expanduser().resolve()
    cwd = Path.cwd().resolve()
    if (cwd / "knowledge").is_dir():
        return cwd
    # This is the usual invocation from .codex/tools/checkpoint.py.
    for parent in (cwd, *cwd.parents):
        if (parent / "knowledge").is_dir() and (parent / "state").is_dir():
            return parent
    return cwd


def parse_frontmatter(path: Path, root: Path) -> Document:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise BundleError("missing opening frontmatter delimiter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise BundleError("missing closing frontmatter delimiter")
    raw = text[4:end]
    metadata: dict[str, Any] = {}
    for line_number, line in enumerate(raw.splitlines(), start=2):
        if not line or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            raise BundleError(f"frontmatter line {line_number} is not `key: JSON-value`")
        key, value = line.split(":", 1)
        key = key.strip()
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", key):
            raise BundleError(f"invalid frontmatter key `{key}`")
        try:
            metadata[key] = json.loads(value.strip())
        except json.JSONDecodeError as exc:
            raise BundleError(f"frontmatter `{key}` must be a JSON-compatible YAML value: {exc.msg}") from exc
    return Document(path, path.relative_to(root / "knowledge"), metadata, text[end + 5 :])


def iso_datetime(value: Any, label: str) -> None:
    if not isinstance(value, str):
        raise BundleError(f"`{label}` must be an ISO-8601 string")
    try:
        dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise BundleError(f"`{label}` is not a valid ISO-8601 timestamp") from exc


def validate_document(document: Document) -> list[str]:
    errors: list[str] = []
    meta = document.metadata
    for key in REQUIRED:
        if key not in meta:
            errors.append(f"missing required `{key}`")
    if errors:
        return errors
    if not all(isinstance(meta[key], str) and meta[key].strip() for key in ("type", "title", "description", "status")):
        errors.append("`type`, `title`, `description`, and `status` must be non-empty strings")
    generated = meta["generated"]
    if isinstance(generated, str):
        try:
            iso_datetime(generated, "generated")
        except BundleError as exc:
            errors.append(str(exc))
    elif isinstance(generated, dict) and isinstance(generated.get("by"), str) and generated.get("by"):
        try:
            iso_datetime(generated.get("at"), "generated.at")
        except BundleError as exc:
            errors.append(str(exc))
    else:
        errors.append("`generated` must be an ISO timestamp or `{\"by\": ..., \"at\": ...}`")
    if not isinstance(meta["sources"], list):
        errors.append("`sources` must be a list (empty is allowed only for index/log)")
    elif document.relative.name not in RESERVED and not meta["sources"]:
        errors.append("concepts require at least one source locator")
    for source in meta.get("sources", []):
        if not isinstance(source, dict) or not isinstance(source.get("resource"), str) or not source["resource"]:
            errors.append("each source requires a non-empty `resource` locator")
    for optional in ("tags", "verified"):
        if optional in meta and not isinstance(meta[optional], list):
            errors.append(f"`{optional}` must be a list")
    if "stale_after" in meta:
        try:
            iso_datetime(meta["stale_after"], "stale_after")
        except BundleError as exc:
            errors.append(str(exc))
    return errors


def documents(root: Path) -> list[Document]:
    knowledge = root / "knowledge"
    if not knowledge.is_dir():
        raise BundleError(f"knowledge directory missing: {knowledge}")
    result: list[Document] = []
    for path in sorted(knowledge.rglob("*.md")):
        result.append(parse_frontmatter(path, root))
    return result


def render_index(items: list[Document], index: Document) -> str:
    concepts = [item for item in items if item.relative.name not in RESERVED]
    lines = ["# Knowledge index", "", "Use this compact index first; open only linked concepts needed for the task.", ""]
    for item in sorted(concepts, key=lambda doc: (str(doc.metadata.get("type", "")), str(doc.metadata.get("title", "")))):
        tags = ", ".join(item.metadata.get("tags", []))
        suffix = f" — tags: {tags}" if tags else ""
        lines.append(f"- [{item.metadata['title']}]({item.relative.as_posix()}) — {item.metadata['description']}{suffix}")
    lines.append("")
    header = "---\n" + "\n".join(f"{key}: {json.dumps(value, ensure_ascii=False, sort_keys=True)}" for key, value in index.metadata.items()) + "\n---\n"
    return header + "\n".join(lines)


def lint(root: Path, verbose: bool = True) -> int:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        items = documents(root)
    except BundleError as exc:
        print(f"ERROR: {exc}")
        return 1
    by_relative = {item.relative.as_posix(): item for item in items}
    if "index.md" not in by_relative or "log.md" not in by_relative:
        errors.append("knowledge/index.md and knowledge/log.md are required")
    title_identity: dict[tuple[str, str], Path] = {}
    now = dt.datetime.now(dt.timezone.utc)
    for item in items:
        for message in validate_document(item):
            errors.append(f"{item.relative}: {message}")
        if item.relative.name not in RESERVED:
            identity = (str(item.metadata.get("type")), str(item.metadata.get("title")).casefold())
            if identity in title_identity:
                errors.append(f"{item.relative}: duplicate concept identity also used by {title_identity[identity]}")
            else:
                title_identity[identity] = item.relative
        stale = item.metadata.get("stale_after")
        if isinstance(stale, str):
            try:
                if dt.datetime.fromisoformat(stale.replace("Z", "+00:00")) < now:
                    warnings.append(f"{item.relative}: stale_after has passed")
            except ValueError:
                pass
        for raw_target in LINK.findall(item.body):
            target = raw_target.split("#", 1)[0].split("?", 1)[0]
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            resolved = (item.path.parent / target).resolve()
            try:
                resolved.relative_to(root / "knowledge")
            except ValueError:
                errors.append(f"{item.relative}: link escapes knowledge bundle: {raw_target}")
                continue
            if not resolved.exists():
                errors.append(f"{item.relative}: broken knowledge link: {raw_target}")
    if "index.md" in by_relative:
        expected = render_index(items, by_relative["index.md"])
        actual = by_relative["index.md"].path.read_text(encoding="utf-8")
        if actual != expected:
            errors.append("knowledge/index.md is out of date; run `python3 tools/knowledge_bundle.py index`")
    if "log.md" in by_relative and "# Knowledge semantic log" not in by_relative["log.md"].body:
        errors.append("knowledge/log.md must contain `# Knowledge semantic log`")
    if verbose:
        for message in warnings:
            print(f"WARNING: {message}")
        for message in errors:
            print(f"ERROR: {message}")
        if not errors:
            print(f"OK: {len(items)} OKF documents validated ({len(warnings)} stale warnings).")
    return 1 if errors else 0


def write_index(root: Path) -> int:
    try:
        items = documents(root)
        index = next(item for item in items if item.relative.as_posix() == "index.md")
    except (BundleError, StopIteration) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    index.path.write_text(render_index(items, index), encoding="utf-8")
    print("Regenerated knowledge/index.md")
    return lint(root)


def search(root: Path, query: str) -> int:
    terms = {term.casefold() for term in WORD.findall(query)}
    if not terms:
        return 0
    for item in documents(root):
        haystack = " ".join(
            [str(item.metadata.get("title", "")), str(item.metadata.get("description", "")), " ".join(item.metadata.get("tags", [])), item.body]
        ).casefold()
        if all(term in haystack for term in terms):
            print(json.dumps({"path": item.relative.as_posix(), "title": item.metadata.get("title"), "type": item.metadata.get("type")}, ensure_ascii=False))
    return 0


def changed(root: Path) -> int:
    checkpoint = root / "state" / "knowledge-checkpoint.json"
    since = "1970-01-01T00:00:00+00:00"
    if checkpoint.exists():
        since = json.loads(checkpoint.read_text(encoding="utf-8")).get("local_watermark", since)
    start = dt.datetime.fromisoformat(since.replace("Z", "+00:00")).timestamp()
    candidates: list[dict[str, str]] = []
    for directory in (root / "inbox", root / "outputs"):
        if not directory.is_dir():
            continue
        for path in sorted(candidate for candidate in directory.rglob("*") if candidate.is_file()):
            if path.stat().st_mtime > start:
                candidates.append({"path": str(path.relative_to(root)), "modified": dt.datetime.fromtimestamp(path.stat().st_mtime, dt.timezone.utc).isoformat().replace("+00:00", "Z")})
    print(json.dumps({"since": since, "candidates": candidates}, indent=2))
    return 0


def metrics(root: Path) -> int:
    items = documents(root)
    bundle_chars = sum(len(item.path.read_text(encoding="utf-8")) for item in items)
    index = next((item for item in items if item.relative.name == "index.md"), None)
    selected_chars = len(index.path.read_text(encoding="utf-8")) if index else 0
    checkpoint_path = root / "state" / "knowledge-checkpoint.json"
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8")) if checkpoint_path.exists() else {}
    run_metrics = checkpoint.get("last_run_metrics", {})
    print(json.dumps({
        "concepts": len([item for item in items if item.relative.name not in RESERVED]),
        "bundle_size_chars": bundle_chars,
        "selected_context_chars": selected_chars,
        "bundle_tokens_approx": round(bundle_chars / 4),
        "selected_context_tokens_approx": round(selected_chars / 4),
        "approx_token_reduction": round(1 - selected_chars / bundle_chars, 4) if bundle_chars else 0,
        "last_run": checkpoint.get("last_successful_run"),
        "last_commit": checkpoint.get("last_successful_commit"),
        "sources_scanned": run_metrics.get("sources_scanned", 0),
        "candidates_extracted": run_metrics.get("candidates_extracted", 0),
        "facts_promoted": run_metrics.get("facts_promoted", 0),
        "conflicts_quarantined": run_metrics.get("conflicts_quarantined", 0),
        "concepts_retrieved": run_metrics.get("concepts_retrieved", 0),
        "models_used": run_metrics.get("models_used", []),
        "commit_id": run_metrics.get("commit_id"),
    }, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Maintain the local OKF knowledge bundle.")
    parser.add_argument("--root", help="Assistant repository root (defaults to current repository).")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("lint")
    sub.add_parser("index")
    search_parser = sub.add_parser("search")
    search_parser.add_argument("query")
    sub.add_parser("changed")
    sub.add_parser("metrics")
    args = parser.parse_args()
    root = project_root(args.root)
    if args.command == "lint":
        return lint(root)
    if args.command == "index":
        return write_index(root)
    if args.command == "search":
        return search(root, args.query)
    if args.command == "changed":
        return changed(root)
    return metrics(root)


if __name__ == "__main__":
    raise SystemExit(main())
