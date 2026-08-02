# First-Run Interview

Ask in short batches. Record only user-confirmed information in `context/`; keep uncertainty in `state/open-questions.md`.

## Identity and work

- What name, role, responsibilities, teams, and recurring commitments should the assistant know?
- What work deserves the most help this month?
- What tone and level of detail make a useful answer?

## Operating loop

- What timezone and working days should schedules use?
- What time should the morning brief be ready, nightly enrichment run, and weekly review occur?
- Which one workflow should prove value first?

## Sources and authority

- Which authenticated sources should be excluded from reading?
- Where do calendar, email, tasks, documents, decisions, and project status live?
- When sources conflict, which is authoritative?
- What sensitive material must remain excluded even if a connector is authenticated?

## External actions

- Confirm that the assistant may create reversible drafts (email drafts, attendee-free holds, task drafts).
- Confirm that final sends, publication, purchases, credential/security changes, deletions, attendee additions, and committed external changes require one immediate confirmation.
- Are there additional actions that always require confirmation?

## Git and trust

- Does `git config user.name` and `git config user.email` resolve for this repository?
- Did the initial Git commit succeed? If not, should we complete the printed recovery step now?
- Has the user trusted and reopened the project so `.codex` settings can apply?
