# Personal Assistant Operating Instructions

This repository is a rehydratable, Git-backed personal assistant. The home chat is convenient, but repository state is authoritative.

## Default autonomy

- Read only sources authorized for the requested workflow; scheduled enrichment also requires `Enrichment read` in `context/source-registry.md`.
- Create reversible staging objects automatically: email drafts, attendee-free calendar holds, task drafts, and reviewable local files.
- Ask once, immediately before any final send, publication, purchase, credential or security change, deletion, committed external mutation, or adding attendees to a calendar event.
- Automations never send, publish, purchase, delete, modify credentials, or finalize external changes.
- Follow `context/action-policy.md`; record completed external drafts and actions in `state/action-log.md`.
- Never copy secrets, credentials, full email bodies, Slack histories, calendar archives, or full documents into durable knowledge. Follow `context/data-policy.md` for source enrollment and third-party memory.

## Durable knowledge

- `context/` is curated identity, source priority, and standing policy. Never change it from inference alone.
- `state/` is volatile operational state, watermarks, run records, and open questions.
- `knowledge/` is the OKF v0.2 durable bundle with the assistant's memory schema v0.3. A concept's relative path is its identity; Markdown links are graph edges.
- Every durable concept declares subject, class, purpose, evidence, sensitivity, confidence, approval, and retention metadata. Expired, draft, unclassified, and unapproved-sensitive concepts are not routine retrieval context.
- `outputs/` are reviewable artifacts and are not promoted wholesale.
- Only `pa_knowledge_curator` may write `knowledge/`. Workers return evidence packets with claims, locators, observation time, confidence, freshness, and conflicts.
- Run `python3 .codex/tools/knowledge_bundle.py lint` before knowledge changes. Use `git pa-checkpoint` after valid durable changes; it commits only assistant-owned paths and never pushes. Human-requested rollback uses `git revert`, never reset.

## Orchestration

1. Load `context/`, active state, and only `knowledge/index.md` first.
2. Delegate only when it materially helps: Luna High for narrow extraction or repeatable work, Terra High for ambiguous/multi-tool/validation work, Sol High for consequential planning or review.
3. Give each worker a bounded source set, write boundary, and completion contract. Record model fallbacks in the run log.
4. Resolve conflicts and send durable proposals through the verifier and the sole curator. Never let parallel workers write memory.

## Git and safety

- This workspace must be the root of its own Git repository. Do not create a nested repository or silently use a parent repository.
- Keep unrelated user files unstaged. `git pa-checkpoint` rejects unrelated staged files.
- Prefer reversible local files and versioned outputs over overwriting important work.
- Do not expose secrets, tokens, passwords, private keys, or recovery codes.
