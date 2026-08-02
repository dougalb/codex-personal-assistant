---
name: codex-personal-assistant-operate
description: Operate a rehydratable Codex Personal Assistant using task-shaped model routing, bounded worker evidence, and a single durable-knowledge curator.
---

# Personal Assistant Operate

1. Rehydrate from `context/`, active `state/`, and `knowledge/index.md`; retrieve deeper knowledge only when the index points to it.
2. Decide whether delegation materially helps. Use Luna High for bounded extraction/classification/transformation, Terra High for ambiguity or validation-heavy work, and Sol High for exceptional planning/review. Fall back Luna → Terra → Sol/default when unavailable and log the fallback.
3. Every worker receives a bounded scope, source set, no durable-write boundary, and completion contract. Require an evidence packet: outcome, claims, source locators, timestamps, confidence, proposed learnings, freshness proposal, and open questions/conflicts.
4. Resolve evidence conflicts. Send candidate durable learning to `pa_knowledge_verifier`, then only `pa_knowledge_curator` may update `knowledge/`.
5. Follow `context/action-policy.md`. Read, network access, local edits, and reversible drafts proceed without confirmation. Ask once immediately before a final external action.
6. Log external drafts/actions in `state/action-log.md`; log run model choices and fallbacks in `state/automation-runs.md` when applicable.

Subagents are inspectable separate threads and do not automatically receive worktrees. Reserve worktrees for independent tasks in other Git projects; this memory repository has one serialized writer.
