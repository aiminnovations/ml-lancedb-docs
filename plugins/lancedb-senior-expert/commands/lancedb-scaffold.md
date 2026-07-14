---
name: lancedb-scaffold
description: Make a LanceDB store runnable in one command — inspects the project, then GENERATES the complete starter files (connect + schema/LanceModel + index build + search/rerank + embedding-registry wiring + recall/latency eval + CLAUDE.md section) from scaffold-templates.md. Discovery → Analysis → Task, with confirmation before writing.
argument-hint: <target / repo path>
---

# /lancedb-scaffold

Scaffold a runnable LanceDB store for **$ARGUMENTS**. Don't just advise — generate the real files.

## Phase 1 — Discovery (inspect what exists)
- Project layout: !`ls -la`
- Which SDK: !`ls pyproject.toml requirements.txt package.json Cargo.toml 2>/dev/null || echo "none detected"`
- Installed LanceDB (Python): !`python -c "import lancedb; print(lancedb.__version__)" 2>/dev/null || echo "not installed"`
- Existing usage: !`grep -rlE "lancedb|@lancedb/lancedb|lance" . 2>/dev/null | head -5 || echo "no LanceDB usage found"`
- Store target: !`grep -rlE "connect\(|connect_async\(|LANCEDB_API_KEY|db://" . 2>/dev/null | head -3 || echo "no connection found"`

## Phase 2 — Analysis
1. **Load the skill.** `lancedb-senior-expert` — SKILL.md + `references/lancedb-docs-protocol.md` + `references/scaffold-templates.md` + `references/planning-checklist.md`.
2. From Discovery, determine: the SDK (Python/TS/Rust), the tier (local / db:// Cloud/Enterprise / s3://), what store code exists, what's missing. **Pin the dimension + metric + index type** before generating. Report the plan + files to create (existing files → show a diff, never silently overwrite).

## Phase 3 — Task (generate, after confirmation)
Dispatch `lancedb-senior-expert` → `lancedb-schema-table-expert` (schema/write) + `lancedb-indexing-expert` (index) + `lancedb-search-expert` (search + embedding) + `lancedb-pipeline-developer` (build) to generate from `references/scaffold-templates.md`, fitted to the detected SDK:
- `store.py` — connect + typed `LanceModel` schema (vector col pinned) + `merge_insert` ingest.
- `index.py` — the vector index (IVF_PQ / IVF_HNSW_SQ) + scalar + FTS indexes + `optimize()`.
- `search.py` — vector / fts / hybrid search + rerank + prefilter.
- `eval.py` — recall vs `bypass_vector_index()` + latency read (the verification gate).
- `## LanceDB Store` section appended to the project CLAUDE.md (the pinned invariants).
The native-guard hook blocks any competing store. `lancedb-code-reviewer` checks no secret was written; `lancedb-performance-adversary` runs the recall/latency read; `lancedb-dev-doc-worker` closes with a handoff.

**Output:** the generated runnable LanceDB store files (confirmed before writing) + the next step: `/lancedb-status` then `/lancedb-optimize`.
