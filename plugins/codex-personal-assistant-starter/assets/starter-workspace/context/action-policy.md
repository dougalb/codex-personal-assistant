# Action policy

## Standing permissions

- Read all authenticated connectors unless excluded in `context/source-registry.md`.
- Read the local workspace, use network access, and create or edit local files.
- Create reversible drafts: unsent email drafts, attendee-free calendar holds, task drafts, and equivalent staged objects.

## One conversational confirmation required

Ask immediately before a final send, publication, purchase, credential/security change, destructive action, external committed mutation, or adding calendar attendees. State the exact destination and effect.

## Automation boundary

Automations may read, summarize, enrich, draft, and checkpoint local knowledge. They never perform the confirmation-required actions above.

## Durable records

Record completed external drafts and approved final external actions in `state/action-log.md`. This policy is authoritative over an inferred preference.
