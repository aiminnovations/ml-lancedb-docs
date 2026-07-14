---
name: lancedb-index
description: Design and build the LanceDB index strategy — the vector index (IVF_PQ / IVF_HNSW_SQ / IVF_RQ), quantization, scalar indexes, and the FTS index — chosen from the catalog by scale, recall, and filter-heaviness, then verified against brute force.
argument-hint: <table / workload>
---

# /lancedb-index

Design the index strategy for **$ARGUMENTS**.

1. **Load the skill.** `lancedb-senior-expert` — SKILL.md + `references/indexing-catalog.md` + `references/lancedb-docs-protocol.md`.
2. **Dispatch `lancedb-indexing-expert`** for the grounded, catalog-cited index spec:
   - The vector index type by scale + recall + filter-heaviness (⚠️ `IVF_HNSW_SQ` fluctuates under heavy filters → prefer PQ/RQ), with `num_partitions` / `num_sub_vectors` / `metric` / `num_bits` / HNSW `m`/`ef_construction` set explicitly at scale.
   - Quantization (PQ / SQ / RaBitQ / binary) by the size/recall trade (`dim % 8 == 0` where required).
   - Scalar indexes (BTREE / BITMAP / LABEL_LIST) on filtered + merge_insert-key columns; the FTS index (native, `with_position` for phrases) if keyword/hybrid.
   - The build plan (GPU `accelerator`?, `wait_for_index`) + the `optimize()` cadence.
3. **Build + verify.** `lancedb-pipeline-developer` builds exactly the cited index; `lancedb-performance-adversary` confirms it builds and measures recall vs `bypass_vector_index()` — raise `refine_factor`/`nprobes`/`ef` if below target, else loop back for a different type/params.

**Output:** the index spec (type + all params, cited) + the built index + the recall verdict vs brute force.
