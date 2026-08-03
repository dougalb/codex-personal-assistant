# Source Registry

List source-specific task access, enrichment access, authority, memory classes, exclusions, and non-secret watermarks here; never store credentials or raw archives.

| Source | What it is for | Task read | Enrichment read | Memory classes | Authority | Sensitive learning | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [confirm source] | [confirm use] | [confirm] | [confirm] | [confirm] | [confirm] | no | [confirm notes] |

## Access boundaries

- Authentication permits neither enrichment nor durable learning.
- Set `Enrichment read` to `no` unless scheduled scanning is explicitly intended.
- List allowed memory classes rather than granting a source unrestricted promotion.
- Set `Sensitive learning` to `yes` only when proposals may be generated; approval remains mandatory.
- Keep distilled knowledge separate from authoritative source material.
