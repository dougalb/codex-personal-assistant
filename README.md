# Codex Personal Assistant Starter

This repository is a Codex plugin marketplace for the Codex Personal Assistant Starter.

The starter helps a user create a local, review-first personal assistant workspace for recurring knowledge work. It includes a first-run setup workflow, starter workspace files, templates, and safety defaults for approval-led work.

## Add This Marketplace To Codex

From Codex:

1. Open `Plugins`.
2. Choose `More`.
3. Choose `Add more`.
4. Choose `Add marketplace`.
5. Use this repository folder or GitHub URL as the source.
6. Install `Codex Personal Assistant Starter`.

After installation, start a new Codex thread and ask:

```text
Set up my Codex Personal Assistant.
```

CLI users can add the local checkout as a marketplace:

```sh
codex plugin marketplace add /path/to/codex-personal-assistant
```

If the installed Codex CLI supports plugin installation, the plugin ID is:

```text
codex-personal-assistant-starter@codex-personal-assistant
```

## Repository Layout

```text
.agents/plugins/marketplace.json
plugins/codex-personal-assistant-starter/
```

The marketplace metadata points Codex at `plugins/codex-personal-assistant-starter`.

## What The Starter Provides

- A bootstrap skill for first-run setup.
- A guided interview for profile, responsibilities, sources, stakeholders, approvals, and first workflows.
- A starter local workspace structure.
- Templates for active work, open questions, waiting-on items, approvals, decisions, run summaries, and recurring workflows.
- Review-first defaults for external systems.

## Safety Defaults

- Keep setup local first.
- Do not store secrets or credentials in the assistant workspace.
- Treat generated summaries and drafts as review material.
- Keep final approval in the destination app.
- Add external connectors only after the user understands the source and action boundary.
