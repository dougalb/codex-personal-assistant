# Codex Personal Assistant

This marketplace provides an autonomous, Git-backed, connector-first personal assistant operating system for Codex. It is designed to rehydrate from local repository state rather than depend on one long-lived chat.

## What 0.2 provides

- Sol Medium orchestration, with Luna High for bounded worker tasks, Terra High for ambiguity/verification, and Sol High for exceptional review.
- Broad ordinary permissions: reading authenticated sources, network access, workspace edits, and reversible drafts proceed unattended.
- One immediate confirmation before a final send, publication, purchase, credential/security change, deletion, attendee addition, or committed external mutation.
- A local Git repository, validated `git pa-checkpoint`, interactive lint hook, and `git revert` rollback path. It never creates or pushes a remote.
- An [OKF v0.2](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)-compatible, distilled knowledge bundle with provenance, freshness, progressive disclosure, watermarks, and a single durable-memory writer.
- Morning brief, nightly enrichment, and weekly review prompts for local Codex scheduled tasks.

## Install and start

Add this repository as a Codex marketplace, install **Codex Personal Assistant Starter**, then open a new thread and ask:

```text
Set up my autonomous Git-backed Codex Personal Assistant.
```

The bootstrap defaults to `~/Documents/Codex/Personal Assistant`, initializes Git when absent, and only creates an initial local commit when the configured Git identity is available. Existing 0.1 workspaces can use `--upgrade`; changed user files are preserved with incoming candidates under `archive/upgrade-review/v0.2.0`.

After bootstrap, trust and reopen the project so its `.codex` configuration, project agents, and narrowly scoped checkpoint rule become active. Local schedules require the Codex desktop app and computer to be running.

## Repository layout

```text
.agents/plugins/marketplace.json
plugins/codex-personal-assistant-starter/
```

The marketplace metadata points Codex to `plugins/codex-personal-assistant-starter`.

## Knowledge and safety

`context/` stays curated and is never changed merely from inference. `state/` tracks volatile work, watermarks, and questions. `knowledge/` is the OKF bundle: only distilled facts and source locators, never raw connector archives. Parallel workers only extract and verify; `pa_knowledge_curator` is the sole writer.

The plugin does not bundle a vector database, embedding service, generic RAG layer, third-party OKF CLI, raw connector archive, automatic post-commit model call, worktrees for memory, or remote Git publishing.
