---
name: lancedb-search
description: Design the LanceDB search/query — the query type (vector / multivector / fts / hybrid), the metric, the tuning (nprobes / refine_factor / ef), the filter (prefilter/postfilter), the embedding, and the reranker — grounded in the catalog and recall-verified.
argument-hint: <query need>
---

# /lancedb-search

Design the search/query for **$ARGUMENTS**.

1. **Load the skill.** `lancedb-senior-expert` — SKILL.md + `references/search-query-catalog.md` + `references/embedding-reranking-catalog.md` + `references/lancedb-docs-protocol.md`.
2. **Dispatch `lancedb-search-expert`** for the grounded, catalog-cited query spec:
   - The embedder (registry provider + `name` + `ndims`; ⚠️ Enterprise query-embed at ingest only).
   - The query type (vector / multivector-MaxSim / fts / hybrid / auto), the metric matched to the model.
   - Tuning — `refine_factor` first, then `nprobes`/`ef`; `distance_range`; `fast_search`/`bypass_vector_index`.
   - Filtering — the DataFusion predicate; prefilter (default, over a scalar index) vs postfilter + the shortfall risk.
   - The reranker — RRF (hybrid default) vs a domain reranker (Cohere/CrossEncoder/Voyage/ColBERT/custom) by measured hit-rate@k.
3. **Build + verify.** `lancedb-pipeline-developer` builds the query; `lancedb-performance-adversary` confirms the query returns the expected rows and measures recall + latency.

**Output:** the query design (type + metric + tuning + filter + reranker, cited) + the built query + the recall/latency verdict.
