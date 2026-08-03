---
name: codex-personal-assistant-enrich
description: Run the assistant's OKF v0.2 and memory-schema v0.3 enrichment loop with source enrollment, retention, approval, verification, single-writer curation, calibration, and a validated local Git checkpoint.
---

# Personal Assistant Enrich

## Preconditions

- This is the root of its own Git repository and `git pa-checkpoint` is configured.
- Load `context/action-policy.md`, `context/data-policy.md`, `context/source-registry.md`, `state/knowledge-checkpoint.json`, `state/memory-approvals.json`, and `knowledge/index.md` first.
- Acquire a repository-local enrichment lock with `python3 .codex/tools/enrichment_lock.py acquire`; release it in a finally step. If a lock is held or assistant-owned paths are already dirty, do not overwrite; log and exit.

## Enrichment loop

1. Collect changed local `inbox/` and `outputs/` with `python3 .codex/tools/knowledge_bundle.py changed`.
2. Collect bounded incremental changes only from sources with `Enrichment read` enabled. On an initial run, use 30 days of history plus relevant future calendar commitments; later use each source watermark with a small overlap.
3. Dispatch independent source batches to Luna High workers. They return distilled evidence packets only—never raw message bodies, full documents, calendar archives, or Slack histories. Every proposed learning includes the v0.3 `memory` metadata object.
4. Route ambiguous, contradictory, or consequential candidates to `pa_knowledge_verifier` (Terra High). Continue safe source batches if a connector auth or worker fails; retain that source's prior watermark.
5. The sole `pa_knowledge_curator` promotes sourced, non-conflicting facts with generated/verified/trust/freshness and v0.3 memory metadata. Behavioral inferences require one direct source and verifier confirmation. Sensitive facts require a matching approved proposal in `state/memory-approvals.json`. Put unsupported consequential claims, missing classifications, and contradictions in `state/open-questions.md`.
6. The curator deduplicates concepts, applies source memory-class limits, assigns category-based review and expiry dates, updates links, regenerates indexes, appends `knowledge/log.md`, and runs:

```bash
python3 .codex/tools/knowledge_bundle.py index
python3 .codex/tools/knowledge_bundle.py lint
python3 .codex/tools/knowledge_bundle.py audit
```

7. Store run counters in `state/knowledge-checkpoint.json.last_run_metrics` and report `python3 .codex/tools/knowledge_bundle.py metrics`: sources scanned, candidates extracted, facts promoted, conflicts quarantined, concepts retrieved, bundle size, selected-context size, approximate token reduction, memory classes, expired concepts, pending approvals, models used, and commit ID. Token savings are a local measurement hypothesis, not a promised estimate.
8. Run `python3 .codex/tools/knowledge_bundle.py expire` for due active copies before indexing. Only after validation, use `git pa-checkpoint`. Advance successful source watermarks only after the checkpoint succeeds. If there is no durable change, record that outcome without committing.

Use normal `git revert` for human-requested rollback; never reset history.
