#!/usr/bin/env python3
"""Dependency-free maintenance commands for the assistant's OKF v0.2 bundle.

Frontmatter values intentionally use JSON syntax, which is valid YAML. This keeps the
profile portable while allowing deterministic parsing with Python's standard library.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
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
MEMORY_SCHEMA_VERSION = "0.3"
MEMORY_CLASSES = {
    "preference",
    "operating_rule",
    "commitment",
    "role_fact",
    "behavioral_inference",
    "sensitive_fact",
    "project_fact",
    "unclassified",
}
SUBJECT_KINDS = {"user", "third_party", "organization", "project", "system", "unknown"}
EVIDENCE_KINDS = {"user_statement", "direct_source", "derived", "unknown"}
CONFIDENCE_LEVELS = {"low", "medium", "high"}
SENSITIVITY_LEVELS = {"standard", "sensitive"}
APPROVAL_STATUSES = {"not_required", "pending", "approved"}
PURPOSES = {
    "general_assistance",
    "briefing",
    "meeting_prep",
    "communication",
    "task_management",
    "relationship_context",
    "project_context",
    "legacy_review",
}
ATTENTION_ACTIONS = {"surface", "suppress", "stage"}
ATTENTION_IMPORTANCE = {"critical", "important", "routine"}
ATTENTION_OUTCOMES = {"pending", "accepted", "dismissed", "corrected", "missed"}
MIN_ADJUDICATED_EVENTS = 20
MISSED_IMPORTANT_RATE_GUARDRAIL = 0.02
CORRECTION_RATE_GUARDRAIL = 0.05


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


def iso_date(value: Any, label: str) -> None:
    if not isinstance(value, str):
        raise BundleError(f"`{label}` must be an ISO-8601 date")
    try:
        dt.date.fromisoformat(value)
    except ValueError as exc:
        raise BundleError(f"`{label}` is not a valid ISO-8601 date") from exc


def memory_metadata(document: Document) -> dict[str, Any] | None:
    value = document.metadata.get("memory")
    return value if isinstance(value, dict) else None


def is_retrievable(document: Document, today: dt.date | None = None, approvals: dict[str, dict[str, Any]] | None = None) -> bool:
    if document.relative.name in RESERVED:
        return False
    if document.metadata.get("status") in {"draft", "deprecated"}:
        return False
    memory = memory_metadata(document)
    if not memory or memory.get("class") == "unclassified":
        return False
    retention = memory.get("retention")
    if isinstance(retention, dict) and isinstance(retention.get("expires_at"), str):
        try:
            expiry = dt.date.fromisoformat(retention["expires_at"])
        except ValueError:
            return False
        if (today or dt.datetime.now(dt.timezone.utc).date()) >= expiry:
            return False
    approval = memory.get("approval")
    if isinstance(approval, dict) and memory.get("sensitivity") == "sensitive":
        if approval.get("status") != "approved":
            return False
        record = (approvals or {}).get(str(approval.get("proposal_id")))
        if not record or record.get("status") != "approved" or record.get("by") != approval.get("by") or record.get("at") != approval.get("at"):
            return False
    return True


def validate_memory(document: Document, approvals: dict[str, dict[str, Any]] | None = None) -> list[str]:
    memory = memory_metadata(document)
    if memory is None:
        return ["missing required `memory` object"]
    errors: list[str] = []
    subject = memory.get("subject")
    if (
        not isinstance(subject, dict)
        or subject.get("kind") not in SUBJECT_KINDS
        or not isinstance(subject.get("id"), str)
        or not subject["id"].strip()
    ):
        errors.append("`memory.subject` requires a known `kind` and non-empty `id`")
    memory_class = memory.get("class")
    if memory_class not in MEMORY_CLASSES:
        errors.append(f"`memory.class` must be one of {sorted(MEMORY_CLASSES)}")
    purpose = memory.get("purpose")
    if not isinstance(purpose, list) or not purpose or not all(isinstance(item, str) and item in PURPOSES for item in purpose):
        errors.append(f"`memory.purpose` must be a non-empty list drawn from {sorted(PURPOSES)}")
    evidence = memory.get("evidence_kind")
    if evidence not in EVIDENCE_KINDS:
        errors.append(f"`memory.evidence_kind` must be one of {sorted(EVIDENCE_KINDS)}")
    if memory.get("confidence") not in CONFIDENCE_LEVELS:
        errors.append(f"`memory.confidence` must be one of {sorted(CONFIDENCE_LEVELS)}")
    sensitivity = memory.get("sensitivity")
    if sensitivity not in SENSITIVITY_LEVELS:
        errors.append(f"`memory.sensitivity` must be one of {sorted(SENSITIVITY_LEVELS)}")
    retention = memory.get("retention")
    if not isinstance(retention, dict):
        errors.append("`memory.retention` must be an object")
    else:
        for key in ("review_at", "expires_at"):
            if key not in retention:
                errors.append(f"`memory.retention` requires `{key}`")
            elif retention[key] is not None:
                try:
                    iso_date(retention[key], f"memory.retention.{key}")
                except BundleError as exc:
                    errors.append(str(exc))
        if memory_class not in {"preference", "operating_rule", "unclassified"} and retention.get("expires_at") is None:
            errors.append(f"`memory.retention.expires_at` is required for `{memory_class}`")
    approval = memory.get("approval")
    if not isinstance(approval, dict) or approval.get("status") not in APPROVAL_STATUSES:
        errors.append(f"`memory.approval.status` must be one of {sorted(APPROVAL_STATUSES)}")
    elif sensitivity == "sensitive":
        if approval.get("status") != "approved":
            errors.append("sensitive memory requires `memory.approval.status: approved`")
        if not isinstance(approval.get("proposal_id"), str) or not approval["proposal_id"].strip():
            errors.append("approved sensitive memory requires `memory.approval.proposal_id`")
        if not isinstance(approval.get("by"), str) or not approval["by"].startswith("human:"):
            errors.append("approved sensitive memory requires `memory.approval.by: human:<id>`")
        try:
            iso_datetime(approval.get("at"), "memory.approval.at")
        except BundleError as exc:
            errors.append(str(exc))
        record = (approvals or {}).get(str(approval.get("proposal_id")))
        if not record or record.get("status") != "approved" or record.get("by") != approval.get("by") or record.get("at") != approval.get("at"):
            errors.append("approved sensitive memory requires a matching record in `state/memory-approvals.json`")
    elif isinstance(approval, dict) and approval.get("status") != "not_required" and not (
        memory_class == "unclassified" and approval.get("status") == "pending"
    ):
        errors.append("standard memory must use `memory.approval.status: not_required`")
    if memory_class == "behavioral_inference":
        if evidence != "direct_source":
            errors.append("behavioral inferences require `memory.evidence_kind: direct_source`")
        if not document.metadata.get("sources"):
            errors.append("behavioral inferences require at least one direct source locator")
    if memory_class == "unclassified" and document.metadata.get("status") != "draft":
        errors.append("unclassified memory must remain `status: draft`")
    return errors


def validate_document(document: Document, approvals: dict[str, dict[str, Any]] | None = None) -> list[str]:
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
    if document.relative.name not in RESERVED:
        errors.extend(validate_memory(document, approvals))
    return errors


def documents(root: Path) -> list[Document]:
    knowledge = root / "knowledge"
    if not knowledge.is_dir():
        raise BundleError(f"knowledge directory missing: {knowledge}")
    result: list[Document] = []
    for path in sorted(knowledge.rglob("*.md")):
        result.append(parse_frontmatter(path, root))
    return result


def approval_records(root: Path) -> dict[str, dict[str, Any]]:
    path = root / "state" / "memory-approvals.json"
    if not path.exists():
        return {}
    try:
        records = json.loads(path.read_text(encoding="utf-8")).get("approvals", [])
    except (OSError, json.JSONDecodeError, AttributeError):
        return {}
    return {
        str(record.get("proposal_id")): record
        for record in records
        if isinstance(record, dict) and isinstance(record.get("proposal_id"), str)
    }


def render_index(items: list[Document], index: Document, approvals: dict[str, dict[str, Any]] | None = None) -> str:
    concepts = [item for item in items if is_retrievable(item, approvals=approvals)]
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
    approvals = approval_records(root)
    if "index.md" not in by_relative or "log.md" not in by_relative:
        errors.append("knowledge/index.md and knowledge/log.md are required")
    title_identity: dict[tuple[str, str], Path] = {}
    now = dt.datetime.now(dt.timezone.utc)
    for item in items:
        for message in validate_document(item, approvals):
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
        expected = render_index(items, by_relative["index.md"], approvals)
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
    index.path.write_text(render_index(items, index, approval_records(root)), encoding="utf-8")
    print("Regenerated knowledge/index.md")
    return lint(root)


def search(root: Path, query: str) -> int:
    terms = {term.casefold() for term in WORD.findall(query)}
    if not terms:
        return 0
    for item in documents(root):
        if not is_retrievable(item, approvals=approval_records(root)):
            continue
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
    concepts = [item for item in items if item.relative.name not in RESERVED]
    classes: dict[str, int] = {}
    for item in concepts:
        memory = memory_metadata(item) or {}
        key = str(memory.get("class", "missing"))
        classes[key] = classes.get(key, 0) + 1
    calibration_path = root / "state" / "attention-calibration.json"
    calibration = json.loads(calibration_path.read_text(encoding="utf-8")) if calibration_path.exists() else {}
    print(json.dumps({
        "memory_schema_version": MEMORY_SCHEMA_VERSION,
        "concepts": len(concepts),
        "memory_classes": classes,
        "retrievable_concepts": sum(is_retrievable(item, approvals=approval_records(root)) for item in concepts),
        "attention_calibration": calibration.get("metrics", {}),
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


def attention_state_paths(root: Path) -> tuple[Path, Path]:
    return root / "state" / "attention-events.json", root / "state" / "attention-calibration.json"


def rollup_attention(root: Path, now: dt.datetime | None = None) -> dict[str, Any]:
    current = now or dt.datetime.now(dt.timezone.utc)
    event_path, calibration_path = attention_state_paths(root)
    events = json.loads(event_path.read_text(encoding="utf-8")).get("events", []) if event_path.exists() else []
    window_start = current - dt.timedelta(days=30)
    window: list[dict[str, Any]] = []
    for event in events:
        try:
            occurred = dt.datetime.fromisoformat(str(event.get("occurred_at")).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            continue
        if occurred >= window_start:
            window.append(event)
    adjudicated = [event for event in window if event.get("outcome") in {"accepted", "dismissed", "corrected", "missed"}]
    interruptions = sum(event.get("action") == "surface" for event in window)
    accepted_interruptions = sum(event.get("action") == "surface" and event.get("outcome") == "accepted" for event in window)
    corrections = sum(event.get("outcome") == "corrected" for event in adjudicated)
    missed_important = sum(event.get("outcome") == "missed" and event.get("importance") in {"critical", "important"} for event in adjudicated)
    count = len(adjudicated)
    metrics = {
        "window_days": 30,
        "interruptions": interruptions,
        "accepted_interruptions": accepted_interruptions,
        "corrections": corrections,
        "missed_important_items": missed_important,
        "adjudicated_events": count,
        "missed_important_rate": missed_important / count if count else 0,
        "correction_rate": corrections / count if count else 0,
        "tuning_eligible": count >= MIN_ADJUDICATED_EVENTS
        and (missed_important / count if count else 0) <= MISSED_IMPORTANT_RATE_GUARDRAIL
        and (corrections / count if count else 0) <= CORRECTION_RATE_GUARDRAIL,
    }
    state = json.loads(calibration_path.read_text(encoding="utf-8")) if calibration_path.exists() else {"schema_version": MEMORY_SCHEMA_VERSION}
    state.update({
        "schema_version": MEMORY_SCHEMA_VERSION,
        "minimum_adjudicated_events": MIN_ADJUDICATED_EVENTS,
        "missed_important_rate_guardrail": MISSED_IMPORTANT_RATE_GUARDRAIL,
        "correction_rate_guardrail": CORRECTION_RATE_GUARDRAIL,
        "last_rollup": current.isoformat().replace("+00:00", "Z"),
        "metrics": metrics,
    })
    calibration_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return metrics


def record_attention(root: Path, memory_id: str, action: str, importance: str, outcome: str) -> int:
    if action not in ATTENTION_ACTIONS or importance not in ATTENTION_IMPORTANCE or outcome not in ATTENTION_OUTCOMES:
        print(f"ERROR: action, importance, and outcome must use the v0.3 attention enums", file=sys.stderr)
        return 2
    event_path, _ = attention_state_paths(root)
    state = json.loads(event_path.read_text(encoding="utf-8")) if event_path.exists() else {"schema_version": MEMORY_SCHEMA_VERSION, "events": []}
    occurred_at = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    event_id = hashlib.sha256(f"{memory_id}|{action}|{importance}|{outcome}|{occurred_at}".encode()).hexdigest()[:20]
    state.setdefault("events", []).append({
        "event_id": event_id,
        "memory_id": memory_id,
        "action": action,
        "importance": importance,
        "outcome": outcome,
        "occurred_at": occurred_at,
    })
    state["schema_version"] = MEMORY_SCHEMA_VERSION
    event_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"event_id": event_id, "metrics": rollup_attention(root)}, indent=2, sort_keys=True))
    return 0


def audit(root: Path) -> int:
    try:
        items = documents(root)
    except BundleError as exc:
        print(f"ERROR: {exc}")
        return 1
    concepts = [item for item in items if item.relative.name not in RESERVED]
    today = dt.datetime.now(dt.timezone.utc).date()
    counts: dict[str, int] = {}
    expired = 0
    pending_sensitive = 0
    for item in concepts:
        memory = memory_metadata(item) or {}
        key = str(memory.get("class", "missing"))
        counts[key] = counts.get(key, 0) + 1
        retention = memory.get("retention")
        if isinstance(retention, dict) and isinstance(retention.get("expires_at"), str):
            try:
                if dt.date.fromisoformat(retention["expires_at"]) <= today:
                    expired += 1
            except ValueError:
                pass
        if memory.get("sensitivity") == "sensitive" and (memory.get("approval") or {}).get("status") != "approved":
            pending_sensitive += 1
    print(json.dumps({
        "concepts": len(concepts),
        "classes": counts,
        "expired": expired,
        "pending_sensitive": pending_sensitive,
        "retrievable": sum(is_retrievable(item, today, approval_records(root)) for item in concepts),
    }, indent=2, sort_keys=True))
    return lint(root)


def expire(root: Path, as_of: str | None) -> int:
    try:
        cutoff = dt.date.fromisoformat(as_of) if as_of else dt.datetime.now(dt.timezone.utc).date()
        items = documents(root)
    except (BundleError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    removed: list[str] = []
    for item in items:
        if item.relative.name in RESERVED:
            continue
        memory = memory_metadata(item) or {}
        retention = memory.get("retention")
        expires_at = retention.get("expires_at") if isinstance(retention, dict) else None
        if not isinstance(expires_at, str):
            continue
        try:
            if dt.date.fromisoformat(expires_at) > cutoff:
                continue
        except ValueError:
            continue
        digest = hashlib.sha256(item.path.read_bytes()).hexdigest()[:16]
        item.path.unlink()
        removed.append(f"- Expired memory `{digest}` on {cutoff.isoformat()} (active copy removed; Git history retained).")
    if removed:
        log = root / "knowledge" / "log.md"
        with log.open("a", encoding="utf-8") as handle:
            handle.write(f"\n## {cutoff.isoformat()}\n" + "\n".join(removed) + "\n")
        write_index(root)
    print(f"Expired {len(removed)} active memory concept(s).")
    return 0


def migration_memory(document: Document, now: dt.date) -> dict[str, Any]:
    slug = re.sub(r"[^a-z0-9]+", "-", str(document.metadata.get("title", document.relative.stem)).casefold()).strip("-") or document.relative.stem
    if str(document.metadata.get("type", "")).casefold() == "system":
        return {
            "subject": {"kind": "system", "id": slug},
            "class": "operating_rule",
            "purpose": ["general_assistance"],
            "evidence_kind": "direct_source",
            "confidence": "high",
            "sensitivity": "standard",
            "retention": {"review_at": (now + dt.timedelta(days=365)).isoformat(), "expires_at": None},
            "approval": {"status": "not_required"},
        }
    return {
        "subject": {"kind": "unknown", "id": slug},
        "class": "unclassified",
        "purpose": ["legacy_review"],
        "evidence_kind": "unknown",
        "confidence": "low",
        "sensitivity": "standard",
        "retention": {"review_at": (now + dt.timedelta(days=30)).isoformat(), "expires_at": (now + dt.timedelta(days=30)).isoformat()},
        "approval": {"status": "pending", "proposal_id": f"legacy:{document.relative.as_posix()}"},
    }


def migrate(root: Path, from_version: str) -> int:
    if from_version != "0.2":
        print(f"ERROR: only v0.2 workspaces can migrate directly to memory schema {MEMORY_SCHEMA_VERSION}; found {from_version}", file=sys.stderr)
        return 2
    try:
        items = documents(root)
    except BundleError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    now = dt.datetime.now(dt.timezone.utc).date()
    migrated: list[str] = []
    for item in items:
        if item.relative.name in RESERVED or "memory" in item.metadata:
            continue
        text = item.path.read_text(encoding="utf-8")
        end = text.find("\n---\n", 4)
        if end < 0:
            print(f"ERROR: {item.relative} has invalid frontmatter", file=sys.stderr)
            return 1
        metadata = dict(item.metadata)
        metadata["memory"] = migration_memory(item, now)
        metadata["memory_schema_version"] = MEMORY_SCHEMA_VERSION
        if metadata["memory"]["class"] == "unclassified":
            metadata["status"] = "draft"
        header = "---\n" + "\n".join(f"{key}: {json.dumps(value, ensure_ascii=False, sort_keys=True)}" for key, value in metadata.items()) + "\n---\n"
        item.path.write_text(header + text[end + 5 :], encoding="utf-8")
        migrated.append(item.relative.as_posix())
    if migrated:
        report = root / "archive" / "upgrade-review" / "v0.3.0" / "MIGRATION-REPORT.md"
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text("# Memory schema v0.3 migration\n\nThe following concepts were quarantined as `unclassified` and require review:\n\n" + "".join(f"- `{path}`\n" for path in migrated), encoding="utf-8")
        if write_index(root):
            return 1
    print(f"Migrated {len(migrated)} concept(s) from memory schema {from_version} to {MEMORY_SCHEMA_VERSION}.")
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
    sub.add_parser("audit")
    expire_parser = sub.add_parser("expire")
    expire_parser.add_argument("--as-of")
    migrate_parser = sub.add_parser("migrate")
    migrate_parser.add_argument("--from", dest="from_version", required=True)
    attention_parser = sub.add_parser("record-attention")
    attention_parser.add_argument("--memory-id", required=True)
    attention_parser.add_argument("--action", required=True, choices=sorted(ATTENTION_ACTIONS))
    attention_parser.add_argument("--importance", required=True, choices=sorted(ATTENTION_IMPORTANCE))
    attention_parser.add_argument("--outcome", default="pending", choices=sorted(ATTENTION_OUTCOMES))
    sub.add_parser("rollup-attention")
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
    if args.command == "audit":
        return audit(root)
    if args.command == "expire":
        return expire(root, args.as_of)
    if args.command == "migrate":
        return migrate(root, args.from_version)
    if args.command == "record-attention":
        return record_attention(root, args.memory_id, args.action, args.importance, args.outcome)
    if args.command == "rollup-attention":
        print(json.dumps(rollup_attention(root), indent=2, sort_keys=True))
        return 0
    return metrics(root)


if __name__ == "__main__":
    raise SystemExit(main())
