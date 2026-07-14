# Handoff Template — close every LanceDB quorum run

> Filled by `lancedb-dev-doc-worker` at close-out. Pairs with a memory write
> (`memory-write-protocol.md`). A run is incomplete without both AND a verification verdict. Convert
> relative dates to absolute.

```
LANCEDB HANDOFF: <task-id> — <one-line summary>

Surface: Claude Code | Date: <YYYY-MM-DD> | Driver: <name> | Dir: <repo path>
Command: </lancedb-...> | Quorum: <agents that ran> | Tier: <OSS|Cloud|Enterprise> | SDK(s): <py|ts|rust>

## Accomplished
- <what was built/changed, with file paths (the table/schema, the index build, the search, the wiring)>

## Grounding (catalog/docs trace)
- APIs/indexes/params used: <name> ← <references/*-catalog.md or docs path>
- LanceDB-native verified: <yes> | competing store: none
- ⚠️ version/tier/SDK-sensitive picks verified: <index type / default / Cloud-only feature — docs path + date>

## Schema + storage
- Table + schema: <cols, vector dim + type, multimodal/blob cols> | writes: <create/merge_insert keys>
- Storage backend: <local|s3|gcs|azure|s3-compatible> | storage_options: <keys set, secrets redacted>
- Versioning/time-travel: <used? tags/checkpoints>

## Index strategy
- Vector index: <IVF_PQ|IVF_HNSW_SQ|IVF_RQ|IVF_FLAT> | params: <num_partitions, num_sub_vectors, metric, num_bits, m/ef>
- Scalar/FTS indexes: <BTREE/BITMAP/LABEL_LIST/FTS on which columns>
- Quantization: <PQ|SQ|RQ|Flat> + rationale (size/recall)

## Search design
- Query type: <vector|multivector|fts|hybrid|auto> | metric | tuning: <nprobes/refine_factor/ef>
- Filtering: <prefilter/postfilter + predicate> | reranker: <RRF|Cohere|CrossEncoder|custom>
- Embedding: <registry provider + model + dims | pre-computed>

## Verification (MANDATORY — the gate)
- Correctness: <index built? query returns expected rows? schema round-trips?> | pass/fail
- Recall/latency/cost: <recall vs brute-force | p50/p95 latency @ scale | index/quant storage cost> | pass/fail
- Data-safety: <schema-evolution/merge_insert/migration non-destructive? rollback via versioning?> | pass/fail

## Review verdict
- <reviewer + adversary findings, severity-tagged> | Blockers resolved: <list> | Open: <list>

## Next action
- <the single concrete next step>

## Constraints carried forward
- <anything the next session must respect: pinned dims, chosen metric, tier limits>

Links: <related handoffs / memory ids / Linear issue id>
```
