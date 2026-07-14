---
name: lancedb-plan
description: Plan a LanceDB system end-to-end — fill the planning checklist, design the schema + index + search, and pin the invariants (dim, metric, index type, storage, tier) — before a single row is written.
argument-hint: <what to design>
---

# /lancedb-plan

Plan the LanceDB system for **$ARGUMENTS** with the senior expert and domain experts.

1. **Load the skill.** `lancedb-senior-expert` — read its SKILL.md, `references/lancedb-docs-protocol.md`, `references/quorum-protocol.md`, and `references/planning-checklist.md`.
2. **Dispatch the coordinator.** Launch `lancedb-senior-expert` to own the plan:
   - Walk every section of `references/planning-checklist.md` in full (no shortcuts; Considered-and-Rejected for each tactical decision).
   - Pull in the subdomain experts the scope touches: `lancedb-schema-table-expert` (schema + write path), `lancedb-indexing-expert` (index + quantization), `lancedb-search-expert` (query + embedding + rerank), `lancedb-storage-deployment-expert` (backend + tier + namespaces), `lancedb-integrations-expert` (framework/Geneva/training bind), `lancedb-use-case-architect` (pattern) — only the relevant seats.
   - **Pin the invariants first** — vector dimension, distance metric, index type, storage backend, tier — they're expensive to unwind once data is written.
   - Version/tier/SDK-verify ⚠️ any picks against the catalogs; cite the catalog path, not memory.
3. **Report** the filled `references/planning-checklist.md`, the schema + index + search design (with params), and the verification plan (recall vs brute force, latency at scale).

**Output:** a filled planning checklist + the schema/index/search design + the pinned invariants + the verification plan.
