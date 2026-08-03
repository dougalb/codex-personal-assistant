---
name: codex-personal-assistant-bootstrap
description: Set up or upgrade a local autonomous, Git-backed Codex Personal Assistant workspace; run onboarding and create its local operating loop.
---

# Codex Personal Assistant Bootstrap

Use this skill for first-run setup, a v0.2-to-v0.3 memory-schema upgrade, or onboarding a new local personal-assistant repository.

## Boundaries

- Never request or store secrets, passwords, API keys, private keys, or recovery codes.
- The bootstrap script initializes Git but never creates or pushes a remote.
- Require the selected target to be a repository root; never silently reuse a parent repository or create a nested repository.
- The assistant may read authenticated sources and create reversible drafts after onboarding, but must ask once before final external actions as defined in `context/action-policy.md`.

## Setup

1. Choose a target. Default: `~/Documents/Codex/Personal Assistant`.
2. Run the bundled bootstrap script. Resolve plugin root as two directories above this `SKILL.md`.

```bash
python3 <plugin-root>/scripts/bootstrap_personal_assistant.py --target "<target-folder>"
```

Use `--dry-run` to preview, `--force` only to deliberately replace starter-managed files, and `--upgrade` for a prior v0.2 workspace. Upgrade preserves user-modified files, quarantines unclassified concepts, and writes candidates to `archive/upgrade-review/v0.3.0`.

3. If Git identity is missing, give the exact recovery commands printed by the bootstrap script. Do not fabricate an initial commit.
4. Ask the user to trust and reopen the generated project, because project-scoped `.codex` configuration, agents, and rules become active only then.

## Onboarding interview

Read `references/first-run-interview.md` and ask in small batches. Populate context only from user-confirmed answers. Confirm:

- Timezone, working days, and preferred morning-brief / nightly-enrichment / weekly-review times.
- Git identity status and whether the initial checkpoint succeeded.
- Connected sources, explicit exclusions, task-read versus enrichment-read permissions, eligible memory classes, and authoritative source order.
- The one-confirmation boundary for final external actions.

Authentication does not grant enrichment or durable-learning permission. Keep `context/` curated; do not infer it from a source scan.

## Automations

After the project is trusted, use available scheduled-task tooling to create three **local-project** schedules in the selected timezone, all using Sol Medium:

1. Morning brief: use `automations/morning-brief.md`.
2. Nightly enrichment: use `automations/nightly-enrichment.md`.
3. Weekly review/staleness audit: use `automations/weekly-review.md`.

Memory-mutating tasks run serially in this repository, not disposable worktrees. Explain that the desktop app and computer must be running. If scheduled-task tooling is unavailable, retain the complete prompts in `automations/` and state plainly that schedules were not created.

## Handoff

Report the target, Git status, created/preserved files, source exclusions, action boundary, automation status, and the next useful workflow. Use `$codex-personal-assistant-operate` for ordinary work and `$codex-personal-assistant-enrich` for durable learning.
