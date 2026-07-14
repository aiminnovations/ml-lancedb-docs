---
name: lancedb-status
description: Score a LanceDB store's readiness (0-100) and list the gaps — inspects the schema, index strategy, search path, storage/tier, and verification coverage, then recommends fixes (and offers to /lancedb-scaffold them).
argument-hint: <path>
---

# /lancedb-status

Score the LanceDB readiness of **$ARGUMENTS** and show what's missing.

## Phase 1 — Discovery
- Schema/store: !`grep -rlE "LanceModel|create_table|createTable|create_empty_table" . 2>/dev/null | head -3 || echo "MISSING — no table/schema"`
- Vector index: !`grep -rlE "create_index|createIndex|IVF_PQ|IVF_HNSW|Index\." . 2>/dev/null | head -3 || echo "MISSING — no vector index (brute-force at scale)"`
- Scalar/FTS index: !`grep -rlE "create_scalar_index|create_fts_index|BITMAP|BTREE" . 2>/dev/null | head -3 || echo "MISSING — no scalar/FTS index"`
- Search path: !`grep -rlE "\.search\(|query_type|rerank|nearestTo" . 2>/dev/null | head -3 || echo "MISSING — no search"`
- Verification: !`grep -rlE "bypass_vector_index|recall|explain_plan|analyze_plan" . 2>/dev/null | head -3 || echo "MISSING — no recall/latency verification"`

## Phase 2 — Analysis + score
1. **Load the skill.** `lancedb-senior-expert` — SKILL.md + `references/lancedb-docs-protocol.md` + `references/scaffold-templates.md` (§6 readiness) + `references/indexing-catalog.md`.
2. Dispatch `lancedb-performance-adversary` to score against the §6 weighted checklist (store+schema 20, vector index appropriate 25, scalar/FTS indexes 15, search path correct 15, verification 15, storage+tier explicit 10) → a 0-100 readiness score.

## Phase 3 — Report
```
LANCEDB READINESS: <score>/100
  ✓/✗ store + typed schema (dims pinned)   ✓/✗ vector index appropriate for scale
  ✓/✗ scalar/FTS indexes on filtered/keyword cols   ✓/✗ search path (metric, prefilter, rerank)
  ✓/✗ verification (recall vs brute force + latency)   ✓/✗ storage + tier explicit (secrets via env)
Gaps (prioritized): <list>
Fix: run /lancedb-scaffold to generate the missing files.
```

**Output:** a LanceDB readiness score + prioritized gaps + "Fix: run /lancedb-scaffold".
