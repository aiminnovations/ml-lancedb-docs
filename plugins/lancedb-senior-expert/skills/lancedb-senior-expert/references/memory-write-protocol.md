# Memory Write Protocol — close every run with a memory write

> Per Juniper governance, substantive work ends with a memory write. The `lancedb-dev-doc-worker`
> performs it; the Stop/SubagentStop hooks remind. References — does NOT redefine — the canonical
> schema in the Juniper memory standards.

## When
- End of any `/lancedb-implement`, `/lancedb-scaffold`, `/lancedb-index`, `/lancedb-migrate`,
  `/lancedb-optimize`, or multi-step session.
- Before context compaction (write the handoff as a memory).

## How (tools, in order of preference)
1. The Juniper memory MCP available in the session — `save_memory` (cortex-graph) /
   `memory_long_term_add` (cortex-core). Do NOT declare a stdio memory MCP inside this plugin
   (governance rule — rely on the project `.mcp.json`). If the built LanceDB store is itself the
   application's memory/KG, note that in the handoff; do not conflate it with the Juniper run-memory.
2. If unreachable, write the handoff markdown to the consuming repo's `dev/` and flag PENDING.

## What to write (envelope)
- **project_name**: the CONSUMING project (REQUIRED). `ml-lancedb-docs` only for plugin work.
- **memory_type**: `decision` (an index/schema/store choice) | `handoff` (session-end) | `reference` (a reusable LanceDB finding).
- **importance**: 8 for a locked schema/index/tier decision (expensive to unwind once data is written); 7 for a build close-out; 6 for a perf/recall finding.
- **tags**: `lancedb`, the stage(s) (`schema`/`indexing`/`search`/`storage`/`integration`/`geneva`/`training`), the tier (`oss`/`cloud`/`enterprise`), the SDK (`python`/`typescript`/`rust`), the command, the task id, the Linear issue id.
- **content**: for a decision — the choice + rationale + Considered/Rejected + catalog citation + the version/tier/SDK note; for a handoff — the filled `handoff-template.md` (incl. the verification verdict).

## Decision-memory shape (LanceDB specifics)
- Name the concrete choice + why: e.g. `"IVF_HNSW_SQ over IVF_PQ for 5M×1024 with heavy filters — recall@10 0.94 vs 0.91, docs indexing/vector-index.mdx"`, or `"merge_insert on (id) for idempotent upserts"`, or `"voyage-context-3 via the embedding registry, 1024-dim pinned before index build"`.
- Record the **pinned invariants** the next session must not silently change: vector dimension, distance metric, index type + params, storage backend, tier. Changing dim/metric = a full re-embed + re-index.
- Record the verification verdict (index built, query correct, recall/latency/cost read) + any migration/data-safety note.
- Link related memories with `[[name]]`.

## Cross-reference
Put the task id / Linear issue id in BOTH the handoff and the memory `tags`.
