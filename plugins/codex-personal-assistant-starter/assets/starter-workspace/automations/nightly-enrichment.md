# Nightly enrichment scheduled-task prompt

Run locally in this assistant repository using Sol Medium. Invoke `$codex-personal-assistant-enrich`. Acquire the workspace lock; if it is held or assistant-owned paths are already dirty, exit without overwriting and log the condition. Use all authenticated connectors except explicit exclusions, with a 30-day initial window plus relevant future calendar commitments and incremental watermarks with overlap thereafter. This task never sends, publishes, purchases, deletes, changes credentials, or finalizes external actions.
