# LanceDB Planning Checklist — every LanceDB plan fills this

> The template the quorum fills before building. Owned by `lancedb-senior-expert`. A plan that names
> a tier/SDK it never states, or an index it never justifies, does not pass. Cite the catalog for
> every API/param.

## 1. Frame
- [ ] **Purpose** — what the LanceDB workload is (RAG store / semantic search / recommender / multimodal search / agent memory / feature store / training data) and the query it must serve fast.
- [ ] **Tier + SDK** — OSS embedded vs LanceDB Cloud vs Enterprise; and Python vs TypeScript/Node vs Rust. State both — the API surface differs (`lancedb-docs-protocol.md`).
- [ ] **Scale** — row count, vector dimension, modality (text / image / video / audio / blob), growth rate, and the recall/latency/cost bar.

## 2. Schema + tables (tables-schema-catalog.md)
- [ ] **Connect** — `connect` vs `connect_async`; uri form (local path / `db://` Cloud / `s3://`); `api_key`/`region` for Cloud.
- [ ] **Schema** — Arrow types; vector column as `FixedSizeList<float32, dim>`; nested/struct; multimodal/blob columns; the pydantic `LanceModel` if auto-embedding.
- [ ] **Create + write** — `create_table` source (list/dict/pandas/pyarrow/polars/LanceModel/empty+schema); `mode`/`exist_ok`; `merge_insert` upsert keys for updatable data.
- [ ] **Versioning** — is time-travel / checkout / restore / tags needed? Consistency (`read_consistency_interval`).

## 3. Indexing (indexing-catalog.md) — the highest-leverage choice
- [ ] **Vector index** — `IVF_PQ` / `IVF_HNSW_SQ` / `IVF_RQ` / `IVF_FLAT`(binary) chosen by scale + recall + filter-heaviness; `num_partitions`, `num_sub_vectors`, `metric`, `num_bits`, HNSW `m`/`ef_construction` — cited defaults, not guessed.
- [ ] **Quantization** — PQ vs SQ vs RQ(RaBitQ) vs Flat by the size/recall trade; `dim % 8 == 0` where RQ/binary require it.
- [ ] **Scalar indexes** — BTREE (high-cardinality) / BITMAP (low-cardinality) / LABEL_LIST (list columns) on every frequently-filtered column.
- [ ] **FTS index** — native vs tantivy; `with_position` for phrase; tokenizer/language/stemming — if full-text or hybrid is in scope.
- [ ] **Build + maintain** — GPU (`accelerator`) for large builds; `optimize()` cadence (compaction + cleanup + incremental index); `wait_for_index`.

## 4. Search + retrieval (search-query-catalog.md)
- [ ] **Query type** — vector / multivector(ColBERT) / fts / hybrid / auto; the metric matched to the embedding model.
- [ ] **Tuning** — `nprobes` (auto by default), `refine_factor`, `ef`, `distance_range`; `fast_search` / `bypass_vector_index` where appropriate.
- [ ] **Filtering** — SQL predicate; prefilter (default) vs postfilter; backed by scalar indexes.
- [ ] **Rerank** — RRF (hybrid default) / LinearCombination / CrossEncoder / Cohere / Voyage / ColBERT / custom; the reason.

## 5. Embeddings (embedding-reranking-catalog.md)
- [ ] **Registry vs manual** — the `get_registry()` auto-embedding path (embeds on ingest + query) vs pre-computed vectors.
- [ ] **Provider** — the registry name + params (model, dims, device, api-key env) for the chosen provider; input_type symmetry; multimodal if images/video.

## 6. Storage + deployment (storage-deployment-catalog.md)
- [ ] **Backend** — local / S3 / GCS / Azure / S3-compatible; `storage_options` (region, endpoint, credentials, timeouts, concurrency).
- [ ] **Namespaces** — directory / REST / Glue / Hive / Unity, if a catalog/namespace model is needed.
- [ ] **Enterprise** — architecture / security / performance / deployment specifics if Enterprise.

## 7. Integrations + application (integrations-catalog.md, geneva-catalog.md, training-catalog.md, use-cases-catalog.md)
- [ ] **Data platform** — pandas / pyarrow / polars / DuckDB / dlt / Voxel51 / pydantic entry points.
- [ ] **AI framework** — LangChain / LlamaIndex / Agno / Genkit / Kiln / HuggingFace vectorstore/adapter.
- [ ] **Geneva / training / graph** — feature-engineering UDFs & jobs, Lance torch data loaders, or lance-graph/GraphRAG, if in scope.

## 8. Verification (MANDATORY)
- [ ] **Correctness** — index builds; the target query returns the expected rows; schema round-trips.
- [ ] **Recall/latency/cost** — a recall read vs brute-force (or a plan to measure), latency at the target scale, and the storage/compute cost of the index/quantization choice.
- [ ] **Data-safety** — schema evolution / merge_insert / migration proven non-destructive; versioning enables rollback.

## 9. Output
A filled checklist + the table/schema shape + the index strategy (type + params, cited) + the search design + the storage config + the verification plan. The build implements + verifies against this.
