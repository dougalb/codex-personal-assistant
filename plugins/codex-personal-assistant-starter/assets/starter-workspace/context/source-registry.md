# Source Registry

All authenticated connectors are readable by default. List explicit exclusions, source authority, and non-secret watermarks here; never store credentials or raw archives.

| Source | What it is for | Access status | Authority | Excluded? | Notes |
| --- | --- | --- | --- | --- | --- |
| [confirm source] | [confirm use] | authenticated/readable | [confirm] | no | [confirm notes] |

## Access boundaries

- Authentication permits reading, not final external action.
- Add an explicit exclusion here to prevent enrichment from reading a source.
- Keep distilled knowledge separate from authoritative source material.
