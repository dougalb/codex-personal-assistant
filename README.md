# Codex Personal Assistant

This marketplace provides an autonomous, Git-backed, connector-first personal assistant operating system for Codex. It is designed to rehydrate from local repository state rather than depend on one long-lived chat.

## What 0.3 provides

- Sol Medium orchestration, with Luna High for bounded worker tasks, Terra High for ambiguity/verification, and Sol High for exceptional review.
- Source-enrolled ordinary permissions: task reads, network access, workspace edits, and reversible drafts proceed unattended within the configured data policy.
- One immediate confirmation before a final send, publication, purchase, credential/security change, deletion, attendee addition, or committed external mutation.
- A local Git repository, validated `git pa-checkpoint`, interactive lint hook, and `git revert` rollback path. It never creates or pushes a remote.
- An [OKF v0.2](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)-compatible, distilled knowledge bundle with provenance, freshness, progressive disclosure, source-enrolled memory governance, retention, approval, attention calibration, watermarks, and a single durable-memory writer.
- Morning brief, nightly enrichment, and weekly review prompts for local Codex scheduled tasks.

## Getting started

### First installation

Paste this prompt into Codex:

```text
Install the Codex marketplace from https://github.com/dougalb/codex-personal-assistant, install the Codex Personal Assistant Starter plugin, and tell me when I need to start a new task.
```

Use Codex in the ChatGPT desktop app or Codex CLI. Plugins are supported on those surfaces; the IDE extension does not support plugins. See the [official plugin guide](https://learn.chatgpt.com/docs/plugins) and [CLI marketplace guide](https://developers.openai.com/plugins/build/plugins#add-a-marketplace-from-the-cli) for current surface and command details.

If you prefer to install manually from the CLI, run these equivalent commands:

```sh
codex plugin marketplace add dougalb/codex-personal-assistant
codex plugin add codex-personal-assistant-starter@codex-personal-assistant
codex plugin list
```

The first command adds the GitHub marketplace snapshot, the second installs **Codex Personal Assistant Starter**, and the third verifies that it is available. In the desktop app, select Codex and open **Plugins** to inspect and enable it. In Codex CLI, run `/plugins`, select the installed plugin, and press **Space** if it is off.

Codex may ask for approval to access the network while fetching the marketplace and to write to your user-level Codex configuration while installing it.

After installation and activation, start a new task or CLI session. Then ask:

```text
Set up my autonomous Git-backed Codex Personal Assistant.
```

The bootstrap defaults to `~/Documents/Codex/Personal Assistant`, initializes Git when absent, and only creates an initial local commit when the configured Git identity is available. Existing 0.1 workspaces can use `--upgrade` to reach the starter structure. Existing 0.2 workspaces can use `--upgrade` to migrate concepts into memory schema v0.3; changed user files are preserved with incoming candidates under `archive/upgrade-review/v0.3.0`.

After bootstrap, trust and reopen the project so its `.codex` configuration, project agents, and narrowly scoped checkpoint rule become active. Local schedules require the Codex desktop app and computer to be running.

> Troubleshooting: If the plugin does not appear, use the ChatGPT desktop app or Codex CLI, not the IDE extension, and start a new task or CLI session after installing it. Use `codex plugin list` or the CLI `/plugins` browser to verify the installation and activation state.

## Updating

### Refresh the installed plugin

The GitHub marketplace is a snapshot, and an installed plugin is a separate cached copy. New marketplace commits and new plugin files do not update an existing Personal Assistant workspace automatically. Refresh the marketplace and reinstall the plugin with:

```sh
codex plugin marketplace upgrade codex-personal-assistant
codex plugin remove codex-personal-assistant-starter@codex-personal-assistant
codex plugin add codex-personal-assistant-starter@codex-personal-assistant
```

Start a new task or CLI session after reinstalling so the refreshed plugin is loaded.

### Migrate an existing workspace

Workspace migration is separate from refreshing the installed plugin. In a new task with the current plugin installed, paste:

```text
Upgrade my existing Codex Personal Assistant workspace to the latest supported version. Preview the migration first, preserve my changes, and report anything placed in upgrade review.
```

The bootstrap can use `--dry-run` to preview an upgrade and `--upgrade` to apply it. It preserves user-modified files and quarantines unclassified incoming concepts under `archive/upgrade-review/v0.3.0` for review.

## Repository layout

```text
.agents/plugins/marketplace.json
plugins/codex-personal-assistant-starter/
```

The marketplace metadata points Codex to `plugins/codex-personal-assistant-starter`.

## Knowledge and safety

`context/` stays curated and is never changed merely from inference. `context/data-policy.md` separates task reads from enrichment and durable learning. `state/` tracks volatile work, watermarks, questions, memory approvals, and content-free attention events. `knowledge/` is the OKF bundle: only distilled facts and source locators, never raw connector archives. Every concept carries memory subject, class, evidence, sensitivity, confidence, approval, and retention metadata. Parallel workers only extract and verify; `pa_knowledge_curator` is the sole writer.

The plugin does not bundle a vector database, embedding service, generic RAG layer, third-party OKF CLI, raw connector archive, automatic post-commit model call, worktrees for memory, or remote Git publishing.
