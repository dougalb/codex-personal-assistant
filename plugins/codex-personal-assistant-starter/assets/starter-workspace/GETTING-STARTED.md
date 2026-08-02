# Getting Started

1. Confirm this folder is the root of its own Git repository (`git rev-parse --show-toplevel`) and trust/reopen it in Codex so project configuration is active.
2. Complete `context/profile.md`, `context/source-of-truth.md`, `context/source-registry.md`, and `context/action-policy.md`.
3. Add active commitments to `state/active-work.md`; use `knowledge/index.md` as the compact entry point to durable memory.
4. Choose one workflow or create the three local scheduled tasks described in `state/automation-setup.md`.
5. Keep outputs reviewable in `outputs/`. The assistant may create reversible drafts, but asks once before any final external action.
6. After valid durable knowledge changes, run `git pa-checkpoint`. It never pushes; use `git revert` for human-requested rollback.
