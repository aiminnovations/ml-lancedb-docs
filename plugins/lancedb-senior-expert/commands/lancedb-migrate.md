---
name: lancedb-migrate
description: Plan and execute a data-safe LanceDB migration — from another vector DB into Lance, across tiers (OSS→Cloud→Enterprise), a schema/format change, or a re-embed at a new dimension — proven non-destructive with versioning rollback before it touches real data.
argument-hint: <migration: from X / schema change / tier change>
---

# /lancedb-migrate

Plan the migration for **$ARGUMENTS** — data-safety first.

1. **Load the skill.** `lancedb-senior-expert` — SKILL.md + `references/lance-format-catalog.md` + `references/tables-schema-catalog.md` + `references/storage-deployment-catalog.md` + `references/quorum-protocol.md`.
2. **Dispatch the coordinator** (`lancedb-senior-expert`) with the schema/table + storage/deployment experts:
   - **Classify** — inbound (another store → Lance), tier change (OSS→Cloud→Enterprise is a connection-string change, no data conversion), schema/format change, or a re-embed at a new dimension (the 3-step add/drop/rename + re-index — never a silent `alter`).
   - **Prove data-safety** — versioning/tags give rollback (`restore`); `merge_insert` keeps ingest idempotent; a competing source store is migrated OUT of, never kept alongside.
   - **Sequence the steps** — snapshot/tag the current version → migrate → rebuild indexes → verify → keep the old version until verified.
3. **Deeper pre-mortem.** `lancedb-performance-adversary` (6th seat) attacks the migration for dropped rows, corrupted vectors, recall collapse, and irreversibility; unmitigated findings BLOCK.
4. **Verify + close.** Row counts match, the target query returns correct rows, recall holds vs brute force; `lancedb-dev-doc-worker` closes with the handoff + the pinned invariants.

**Output:** the data-safe migration plan + the executed steps + the verification (counts + recall) + the rollback point.
