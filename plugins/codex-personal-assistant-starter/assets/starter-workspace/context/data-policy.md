# Memory Data Policy

This policy separates permission to read a source for a task from permission to learn durable memory from it.

## Source permissions

- `task_read`: may be read for an explicitly requested workflow.
- `enrichment_read`: may be scanned by scheduled enrichment.
- `memory_classes`: classes eligible for durable promotion from that source.
- `sensitive_learning`: whether sensitive concepts may be proposed; approval is still required.
- `retention_override`: optional category-specific retention override.

Authentication alone grants neither `enrichment_read` nor permission to retain a claim.

## Memory rules

- Workers return evidence packets; only the curator may write `knowledge/`.
- Every promoted concept must declare its subject, class, purpose, evidence kind, sensitivity, confidence, and retention.
- Behavioral inferences require one attributable direct source and verifier confirmation.
- Sensitive facts require a matching human approval record before promotion.
- Expired or quarantined concepts are excluded from routine retrieval.
- Do not copy raw messages, full documents, private credentials, or connector archives into durable memory.

## Review and forgetting

The `expire` maintenance command removes expired active copies and writes a redacted tombstone. Ordinary Git history is retained for rollback; hard history removal is a separate, explicit manual operation.
