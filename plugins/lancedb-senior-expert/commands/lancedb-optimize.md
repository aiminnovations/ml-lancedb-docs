---
name: lancedb-optimize
description: Optimize a LanceDB store — index tuning (nprobes / refine_factor / ef / type), quantization for cost, compaction + cleanup via optimize(), and query-plan analysis — with measured before/after deltas on recall, latency, and cost.
argument-hint: <table / query to optimize>
---

# /lancedb-optimize

Optimize **$ARGUMENTS** with measured deltas.

1. **Load the skill.** `lancedb-senior-expert` — SKILL.md + `references/indexing-catalog.md` + `references/search-query-catalog.md` + `references/lancedb-docs-protocol.md`.
2. **Baseline.** Dispatch `lancedb-performance-adversary` to read the current recall (vs `bypass_vector_index()`), latency (p50/p95), and cost, and the query plan (`explain_plan`/`analyze_plan`) — identify the bottleneck (a `LanceScan` wanting an index, too-high `nprobes`, unindexed rows, a wrong metric).
3. **Tune.** `lancedb-indexing-expert` + `lancedb-search-expert` propose the change, catalog-cited:
   - Recall low → `refine_factor` then `nprobes`/`ef`; wrong index → change type/params.
   - Latency high → cut columns with `.select()`, lower probes, add the missing index, `fast_search` during rebuilds.
   - Cost high → quantization (PQ→RaBitQ), `optimize(cleanup_older_than=…)` to prune versions + compact.
   - Unindexed rows → `optimize()` to fold them in.
4. **Re-measure.** `lancedb-pipeline-developer` applies it; `lancedb-performance-adversary` re-reads recall/latency/cost → the before/after delta. Loop until the bar is met; never regress recall silently.

**Output:** the tuned index/query + the before/after deltas (recall, latency, cost) + the `optimize()` cadence recommendation.
