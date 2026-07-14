# Upstream Assets — source ladder + per-catalog provenance

> The grounding sources behind the 10 catalogs. Catalogs are **absorb-everything self-contained** —
> the knowledge is inside them with citations — so the plugin works without the docs checked out.
> LanceDB spans three SDKs and three tiers and moves fast: the ⚠️ picks are version/tier/SDK-verified
> at build time (`lancedb-docs-protocol.md`).

## Source ladder
1. The catalog (`references/*-catalog.md`).
2. The LanceDB docs — this repo's `/docs/*.mdx` (the authoritative content; snippets tested in `/tests/`).
3. The SDK source — the `ml-lancedb` repo (`python/`, `nodejs/`, `rust/`); Context7 (`lancedb`/`lance`) for published API docs.
4. Tavily / web — current releases, deprecations, benchmark numbers for ⚠️ fast-moving picks.

## Per-catalog provenance
| Catalog | Sources |
|---|---|
| `lance-format-catalog.md` | docs `lance.mdx`, `tables/versioning.mdx`, `tables/schema.mdx`; SDK `python/lancedb/table.py` (versioning/tags/optimize); the Lance file/table/catalog spec |
| `tables-schema-catalog.md` | docs `tables/{index,create,schema,update,versioning,consistency,multimodal}.mdx`, `tables-and-namespaces.mdx`; SDK `db.py`, `table.py`, `merge.py`, `pydantic.py` |
| `indexing-catalog.md` | docs `indexing/{index,vector-index,fts-index,scalar-index,gpu-indexing,quantization,reindexing}.mdx`; SDK `table.py` (`create_index`/`create_scalar_index`/`create_fts_index`), `index.py` |
| `search-query-catalog.md` | docs `search/{index,vector-search,multivector-search,full-text-search,hybrid-search,filtering,optimize-queries,sql/*}.mdx`; SDK `query.py`; DataFusion predicate reference |
| `embedding-reranking-catalog.md` | docs `embedding/{index,quickstart}.mdx`, `integrations/embedding/*`, `integrations/reranking/*`, `reranking/{index,custom-reranker,eval}.mdx`; SDK `lancedb/embeddings/*`, `lancedb/rerankers/*` |
| `storage-deployment-catalog.md` | docs `storage/{index,configuration}.mdx`, `namespaces/{index,usage}.mdx`, `enterprise/{index,architecture,security,performance,quickstart,deployment/*}.mdx`; SDK `__init__.py` connect signatures |
| `integrations-catalog.md` | docs `integrations/{index,data/*,ai/*}.mdx`; the LangChain/LlamaIndex/DuckDB-lance/dlt/FiftyOne integration packages |
| `geneva-catalog.md` | docs `geneva/{index,overview,udfs/*,udfs/providers/*,jobs/*,deployment/*,reference}.mdx` |
| `training-multimodal-catalog.md` | docs `training/{index,torch}.mdx`, `tutorials/*`; Lance `torch` data-loader API; the multimodal-lakehouse story |
| `use-cases-catalog.md` | docs `tutorials/*`, `demos/index.mdx`; `ml-lancedb-vectordb-recipes` (applications/examples/tutorials); `ml-lance-graph` (GraphRAG on Lance) |

## Version anchor
The `ml-lancedb` SDK source read for these catalogs was around Rust/core `0.28.0-beta.4`; docs snippets track released Python `lancedb==0.30.0`. In addition, the **core paths were live-run-verified against `lancedb==0.34.0` on 2026-07-14** (13/13 checks PASS, recall@10=1.0) via `tests/verify_catalogs.py`, which surfaced one real forward-drift: the **unified `create_index(column, config=…)` API is the current form (imperative `create_index(metric=…)`/`create_scalar_index`/`create_fts_index` deprecated since 0.25.0)** — folded into `indexing-catalog.md` + `scaffold-templates.md`. Where the imperative API and the async config classes differ, the catalogs flag it ⚠️. Re-verify the installed SDK version at build; `tests/verify_catalogs.py` is the re-runnable smoke check.

## Composes (not re-implements)
`retrieval-rag-senior-architect` (LanceDB is its primary store — this plugin is the store-layer expert it composes), `langgraph-senior-architect` (pipeline orchestration around the store), `master-litellm-architect` (generation over retrieved context), `dspy-senior-architect` (optional prompt optimization), `cortex-graph` (memory/KG). The LanceDB store itself can BE an application's memory/KG substrate — note that in the handoff; do not re-implement the Juniper run-memory.

## Optional future MCP (DEFERRED)
A `lancedb-docs` MCP over the catalogs + vendored LanceDB docs is a possible later phase; NOT at M1. Do NOT declare cortex/linear/auth MCPs as stdio inside this plugin (governance rule — rely on the project `.mcp.json`).

## Freshness
Catalogs carry a `last-verified-against` stamp. LanceDB moves fast (new index types, quantization, providers, Cloud/Enterprise features) — default cadence 14 days, or on a notable release. `lancedb-docs-curator` owns it; the ⚠️ picks are re-verified per build.
