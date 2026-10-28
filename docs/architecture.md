# GhostTrace architecture

## Data flow

1. Load the request, identity, activity, rules, and evidence manifest tables.
2. Build a stable identity graph from current identities and historical audit changes.
3. Parse each evidence format into normalized observations:
   - resource ID
   - system and category
   - observed state
   - observation timestamp
   - evidence reference
   - identity tokens
   - topology and source quality
4. Join observations to the requested user using exact identity tokens and bounded temporal workflow links.
5. Select the latest authoritative observation at or before `audit_at`, while preserving unsafe replica drift.
6. Compile findings, remediation, and verification steps in the required operation order.
7. Validate row count, JSON shape, allowed operations, phase ordering, step numbering, case ordering, and evidence rules.

## State model

| Resource kind | Desired treatment |
| --- | --- |
| User profile, search, cache, export | Delete |
| Support message / email log | Redact when retention policy requires context |
| Support attachment | Delete when subject-only |
| Analytics / telemetry | Anonymize when attributable |
| Security audit / legal hold | Retain |
| Backup archive | Retain but block restore |
| Active connector | Disable |
| Account tombstone | Retain stable internal reference and redact direct PII |

## Why deterministic first

The grader rewards exact evidence references, operation ordering, and policy decisions. Those are safer to implement with explicit code than to delegate to an unconstrained language model. Optional model enrichment is isolated behind flags and is never allowed to invent resource IDs or override structured evidence.

## Known limitations

Screenshot OCR and image-only PDF evidence depend on local tooling. Ambiguous evidence associations can still reduce exact step-sequence accuracy. The public sample is useful for regression, but hidden-test performance cannot be inferred as a guarantee from it.
