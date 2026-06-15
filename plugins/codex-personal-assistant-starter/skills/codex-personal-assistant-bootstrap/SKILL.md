---
name: codex-personal-assistant-bootstrap
description: Use when a user wants to set up a Codex Personal Assistant, bootstrap a local assistant workspace on Mac, run the first-run onboarding interview, create source-grounded context/state/workflow files, or learn how compounding knowledge should work in a personal Codex setup. Do not use for general productivity advice unrelated to Codex setup.
---

# Codex Personal Assistant Bootstrap

Use this skill to help a less technical Mac user create and start using a local Codex Personal Assistant workspace.

## Operating boundaries

- Work locally first. Draft files in the user's chosen folder before proposing any external destination.
- Do not send, publish, delete, modify, move, mark read/unread, or connect external systems unless the user explicitly approves that action.
- Do not switch to Browser, Chrome, or Computer Use as a workaround for missing connector access.
- Do not ask the user for secrets, tokens, passwords, private keys, recovery codes, or credential files.
- Do not recommend separate third-party note vaults unless the user explicitly asks.
- If a fact depends on a source file or connected system, mark it as unverified until checked.

## Default setup target

If the user does not give a folder, propose:

`~/Documents/Codex/Personal Assistant`

For nontechnical users, explain paths in plain language and keep commands optional. If they approve the default folder, create it.

## Bootstrap workflow

1. Identify the target folder.
   - Use the default above unless the user gives another location.
   - If the folder already exists, preserve existing files and only add missing starter files.

2. Create starter files.
   - Resolve the plugin root as two directories above this `SKILL.md`.
   - Run:

```bash
python3 <plugin-root>/scripts/bootstrap_personal_assistant.py --target "<target-folder>"
```

3. Run the first-run interview.
   - Read `references/first-run-interview.md`.
   - Ask questions in small batches of 4 to 6.
   - Accept short, imperfect answers.
   - Use `[confirm ...]` placeholders rather than inventing details.

4. Populate durable files.
   - `context/profile.md`: who the user is, role, responsibilities, preferences.
   - `context/source-of-truth.md`: which sources win for calendar, email, documents, tasks, decisions, and project status.
   - `context/source-registry.md`: source list with access status and intended use.
   - `context/stakeholders.md`: key people, teams, and relationship notes.
   - `state/active-work.md`: current work, priority, next action, and confidence.
   - `state/open-questions.md`: unknowns that need source material or user confirmation.
   - `state/approval-ledger.md`: proposed and approved write actions.

5. Pick one first workflow.
   - Recommend one narrow first workflow: daily brief, meeting prep, document review, communication draft, or weekly review.
   - Run it with only local files unless the user explicitly connects a source.

6. Finish with a compact handoff.
   - List files created or updated.
   - List open placeholders.
   - Recommend the next single action.
   - Keep confidence labels for important claims.

## Compounding knowledge rule

Every useful run should leave one small durable improvement: a corrected fact, a better source link, a clearer workflow, an updated active-work item, a resolved open question, or a reusable template. Avoid long summaries that do not improve future runs.
