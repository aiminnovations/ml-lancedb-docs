# lancedb-senior-expert

**Docs-first master expert for LanceDB and the Lance columnar format — the store-and-retrieval layer for multimodal AI.**

A senior-expert-family plugin, shipped from the [ml-lancedb-docs](https://github.com/aiminnovations/ml-lancedb-docs) marketplace. It builds **correct, fast, data-safe, native** LanceDB implementations — the right schema, the right index for the workload, the right search — verified before they ship, across the **Python, TypeScript, and Rust** SDKs and the **OSS / Cloud / Enterprise** tiers.

> Grounds in the LanceDB docs (`lance`, `tables/*`, `indexing/*`, `search/*`, `embedding/*`, `reranking/*`, `storage/*`, `namespaces/*`, `enterprise/*`, `geneva/*`, `training/*`, `integrations/*`) and the SDK source — never training-time memory. It is the store-layer expert the RAG stack composes.

## The thesis (hard rules)

1. **LanceDB-native, catalog-grounded, version/tier/SDK-aware.** Use the Lance format's own capabilities — zero-copy schema evolution · versioning/time-travel · multimodal blob encoding · native hybrid search · IVF/HNSW + scalar + FTS indexing over object storage — rather than a second store or a hand-rolled reimplementation. Every recommendation names the **tier** (OSS/Cloud/Enterprise) and **SDK** (Python/TS/Rust). Cascade: native API → documented integration → hand-rolled (Sean's prior approval). A **competing vector store** (Pinecone/Weaviate/Qdrant/Chroma/Milvus) is a BLOCKER (the native-guard hook enforces it).
2. **Docs-grounded + verified.** Every API/index/param cites a `references/*-catalog.md`. Every build is verified: the schema round-trips, the index builds, the query returns the expected rows, and recall (vs `bypass_vector_index()` brute force) + latency + cost are read. No un-verified schema/index ships over real data; the invariants (dim, metric, index type, storage, tier) are pinned before the first write.

## The surface (what it owns)

```
Lance format  → fragments/manifest · versioning/time-travel (checkout/restore/tags)
                · zero-copy schema evolution (add/alter/drop_columns) · blob encoding · optimize/compact
tables        → connect (sync/async, local/s3/gs/az/db://) · create (arrow/pandas/polars/LanceModel/empty)
                · merge_insert upsert · multimodal · consistency · bad-vectors
indexing      → IVF_PQ / IVF_HNSW_SQ / IVF_RQ / IVF_FLAT · PQ/SQ/RaBitQ/binary quantization
                · BTREE/BITMAP/LABEL_LIST scalar · native/tantivy FTS · GPU build · optimize/reindex
search        → vector · multivector(ColBERT MaxSim) · full-text · hybrid · SQL filter (prefilter/postfilter)
                · nprobes/refine_factor/ef · explain_plan/analyze_plan
embeddings    → get_registry auto-embedding · OpenAI/Cohere/Gemini/HF/SentenceTransformers/Jina/Voyage
                /Bedrock/IBM/Ollama/ColPali/ImageBind/OpenCLIP/Instructor · rerankers (RRF/CrossEncoder/…)
storage       → local/S3/GCS/Azure/S3-compatible · storage_options · DynamoDB commit store · dynamic creds
namespaces    → directory / REST / external catalogs · connect_namespace
Cloud/Ent.    → architecture · security (SOC2/HIPAA/GDPR) · performance envelope · Managed/BYOC deployment
Geneva        → scalar/batch UDFs & UDTFs · provider embedding UDFs · backfill · materialized views · Ray/K8s
training      → Lance torch DataLoader / Permutation · the multimodal lakehouse
integrations  → pandas/pyarrow/polars/DuckDB/dlt/Voxel51/pydantic · LangChain/LlamaIndex/Agno/Genkit/Kiln/HF
use cases     → multimodal agents · time-travel RAG · recommenders · image/video search · GraphRAG (lance-graph)
```

## Components

- **Governing skill** + **10 grounded catalogs** + **7 process references** (`lancedb-docs-protocol`, `quorum-protocol`, `planning-checklist`, `handoff-template`, `memory-write-protocol`, `upstream-assets`, `scaffold-templates`).
- **A re-runnable verification harness** (`tests/verify_catalogs.py`) — 13 checks that exercise the catalogs' core paths against a real LanceDB, offline; exit 1 on any drift.
- **12 agents:** the `lancedb-senior-expert` coordinator (opus); 6 subdomain experts (`lancedb-schema-table-`, `-indexing-`, `-search-`, `-storage-deployment-`, `-integrations-`, `-use-case-architect`); the fleet (`lancedb-pipeline-developer`, `lancedb-code-reviewer`, `lancedb-performance-adversary` [opus], `lancedb-dev-doc-worker`, `lancedb-docs-curator`).
- **10 commands:** `/lancedb-plan`, `/lancedb-implement`, `/lancedb-scaffold` + `/lancedb-status` (complete-usable layer), `/lancedb-index`, `/lancedb-search`, `/lancedb-migrate`, `/lancedb-optimize`, `/lancedb-review`, `/lancedb-handoff`.
- **Hooks:** `PreToolUse` native-guard (blocks a competing vector store; advises on asymmetric embedding + brute-force-at-scale footguns); `Stop`/`SubagentStop` handoff reminders.

`★ The verification seat is mandatory ────────────`
A data-layer failure is expensive to unwind once data is written — a wrong index type, a broken schema, a lost-recall quantization, a destructive migration. So the `lancedb-performance-adversary` is a non-skippable quorum seat: a build isn't done until the index builds, the query returns the expected rows, and recall (vs brute force) + latency + cost are **measured**, not asserted. Data-safe before real data — versioning gives you rollback.
`─────────────────────────────────────────────────`

## Complete-usable layer

`/lancedb-scaffold` inspects a project and **generates a runnable LanceDB store** (connect + typed `LanceModel` schema + the index build + the search/rerank + the embedding-registry wiring + a recall/latency eval + a CLAUDE.md section) from `references/scaffold-templates.md`, fitted to the detected SDK; `/lancedb-status` scores LanceDB-readiness 0–100 with prioritized gaps.

## Composes (does not re-implement)

This is the **store-layer expert** the RAG stack composes: `retrieval-rag-senior-architect` names LanceDB as its primary store — this plugin owns how that store is built. Around it: `langgraph-senior-architect` (pipeline orchestration), `master-litellm-architect` (generation over retrieved context), `dspy-senior-architect` (optional prompt optimization), the `cortex-graph` memory/KG. The LanceDB store itself can BE an application's memory/KG substrate.

## Install (in a consuming project)

```
claude plugin marketplace add github.com/aiminnovations/ml-lancedb-docs
claude plugin install lancedb-senior-expert@ml-lancedb-docs
```

Then `/lancedb-plan <system>` to design, or `/lancedb-scaffold <repo>` to generate a runnable LanceDB store.

## Status — M1 (v0.1.0), catalogs live-verified

Complete, valid, installable plugin: every component wired; the 10 catalogs grounded against the LanceDB docs + SDK source (read at core `0.28.0-beta.4`; docs snippets track `lancedb==0.30.0`) **and live-run-verified against `lancedb==0.34.0` (2026-07-14) — 13/13 core paths PASS, recall@10 = 1.0** via `tests/verify_catalogs.py`. That run caught real forward-drift, now folded in: the **unified `create_index(column, config=…)` API** is current (the imperative `create_index(metric=…)` / `create_scalar_index` / `create_fts_index` forms are deprecated since 0.25.0) — see `indexing-catalog.md` + `scaffold-templates.md`. **⚠️ still version/tier/SDK-verify at build:** provider registry names + params, tier-only features (Enterprise query-embed at ingest, TS lacking `IvfSq`/namespace lifecycle, GPU build Python-sync-only). **Intentionally deferred by design:** a `lancedb-docs` MCP — `upstream-assets.md` records the governance rule *not* to declare stdio MCPs inside a plugin (rely on the project `.mcp.json`), so it stays a project-level concern, not a plugin component.

---

**Author:** Sean Rawlings / AIM Innovations · **License:** MIT · part of the Juniper senior-expert plugin family.
