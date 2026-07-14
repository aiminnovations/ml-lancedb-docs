---
name: lancedb-review
description: Review a LanceDB change/diff/branch before merge — a fresh-context, severity-tagged audit of native compliance, correctness against the catalogs, schema/index correctness, data-loss & migration safety, and secret hygiene; adds the performance-adversary for high-stakes changes.
argument-hint: <diff / branch / files>
---

# /lancedb-review

Review the LanceDB change **$ARGUMENTS**.

1. **Load the skill.** `lancedb-senior-expert` — SKILL.md + `references/quorum-protocol.md` + the catalog(s) for the stage under review.
2. **Dispatch `lancedb-code-reviewer`** (fresh context) for a severity-tagged review:
   - Native stack + correct SDK (a competing store / wrong-SDK API BLOCKS).
   - Every API cites a catalog (un-cited / from-memory BLOCKS).
   - Schema/index correctness (pinned-dim vector col; metric matches model AND index; `num_sub_vectors` divides dim; scalar index on filtered/merge keys).
   - Data-loss / migration safety (no silent dim `alter`, no destructive `overwrite`, idempotent ingest, versioning rollback).
   - Secret hygiene (env / `$var:`, never hardcoded).
3. **Escalate high-stakes.** For a migration / schema-over-data / large-corpus / Enterprise change, add `lancedb-performance-adversary` for the recall/latency + data-loss pre-mortem.
4. **Report** the severity-tagged findings; BLOCK the merge on any BLOCKER and loop to the builder.

**Output:** a severity-tagged review (BLOCKER/MAJOR/MINOR/NOTE) with catalog citations + required fixes + a merge verdict.
