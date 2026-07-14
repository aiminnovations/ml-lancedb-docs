# Integrations Catalog — data platforms + AI frameworks

> last-verified-against: docs `integrations/{index,data/*,ai/*}.mdx`, `integrations/data/pydantic.mdx` + SDK `lancedb==0.30.0`, 2026-07-14
> Sources: `docs/integrations/*`; the LangChain/LlamaIndex/DuckDB-lance/dlt/FiftyOne/Genkit packages.
> Owner expert: `lancedb-integrations-expert`. ⚠️ = version/tier/SDK-verify at build. LanceDB is the store — these bind TO it, they don't replace it.

## Data platforms

### Pydantic (`lancedb.pydantic`)
`LanceModel` = a pydantic base whose schema LanceDB converts to Arrow; `Vector(n)` → `pa.list_(pa.float32(), n)`; `pydantic_to_schema(model)` → `pa.Schema`. The idiomatic way to define a typed table + auto-embedding (`SourceField`/`VectorField`; see `embedding-reranking-catalog.md`).
```python
class LanceDocs(LanceModel):
    text: str
    vector: Vector(2)
tbl = db.create_table("docs", schema=LanceDocs, mode="overwrite")
tbl.add([{"text": "hello", "vector": [1.0, 0.0]}])
tbl.search("hello").limit(1).to_pydantic(LanceDocs)
```

### Pandas & PyArrow
Lance is Arrow-native. `db.create_table("t", data=df)` ingests a DataFrame directly; `.search(vec).select([…]).limit(k).to_pandas()` returns one. Async mirrors it via `connect_async`. Zero-copy in most paths — no serialization tax (`integrations/data/pandas_and_pyarrow.mdx`).

### Polars & Arrow
Zero-copy Arrow interop: build a `pl.DataFrame`, ingest via `.to_arrow()` (`db.create_table("t", data=df.to_arrow())`); read back with `.to_polars()`; for larger-than-RAM use `table.to_polars().lazy()` and chain lazily. Pydantic schemas work too (`integrations/data/polars_arrow.mdx`).

### DuckDB
Two paths (`integrations/data/duckdb.mdx`):
1. **Zero-copy Arrow:** `arrow_tbl = table.to_lance()` then `duckdb.query("SELECT * FROM arrow_tbl")` — DuckDB scans Arrow natively.
2. **Lance extension (recommended):** `INSTALL lance; LOAD lance;` → `ATTACH './local_lancedb' AS lance_ns (TYPE LANCE);` → reference `lance_ns.main.<table>`; pushdown search to Lance via table functions:
   - `lance_vector_search('ns.main.tbl','vector',[…]::FLOAT[], k=1, prefilter=true)` → `_distance`
   - `lance_fts('ns.main.tbl','col','query', k=1, prefilter=true)` → `_score`
   - `lance_hybrid_search(…,'vector',[…],'col','query', k, prefilter, alpha=0.5, oversample_factor=4)` → `_hybrid_score,_distance,_score`

   Extension repo: `github.com/lance-format/lance-duckdb`. Use DuckDB for SQL analytics over the same Lance tables the app queries as vectors — one store, two access patterns.

### dlt
`pip install dlt[lancedb]`; scaffold `dlt init rest_api lancedb`. Configure `.dlt/secrets.toml` (`[destination.lancedb] embedding_model_provider="sentence-transformers" embedding_model="all-MiniLM-L6-v2"`, `[destination.lancedb.credentials] uri=".lancedb"`). Run: `dlt.pipeline(destination="lancedb", dataset_name=…).run(source)`. Auto-embed a field with `lancedb_adapter(source, embed="Title")`. Handles nested-data normalization, schema inference, incremental loading, and embedding at ingest — the ELT front door to a Lance store (`integrations/data/dlt.mdx`).

### Voxel51 / FiftyOne
`compute_similarity(dataset, model="clip-vit-base32-torch", backend="lancedb", brain_key="lancedb_index")` builds a LanceDB similarity index (a LanceDB table); query with `dataset.sort_by_similarity(query, brain_key=…, k=10)` (query = sample ID(s), a vector, or a text prompt) → a `DatasetView`. Backend params: `table_name`, `metric` (`cosine`/`euclidean`, default cosine), `uri` (default `/tmp/lancedb`). The visual-dataset front end to LanceDB vector search (`integrations/data/voxel51.mdx`).

## AI frameworks

### LangChain — `langchain.vectorstores.LanceDB`
Entry: `LanceDB.from_documents(documents, embeddings)` / `LanceDB.from_texts(texts, embedding)`. Ctor: `connection`, `embedding`, `uri="/tmp/lancedb"`, `vector_key="vector"`, `text_key="text"`, `table_name="vectorstore"`, `api_key`/`region` (Enterprise), `mode="overwrite"`, `distance="l2"`, `reranker`, `limit=4`. Methods: `add_texts`, `add_images`, `create_index`, `similarity_search(query,k,filter,fts,name)`, `similarity_search_with_relevance_scores`, `max_marginal_relevance_search(query,k,fetch_k,lambda_mult=0.5)`, `get_table()`.
```python
from langchain.vectorstores import LanceDB
from langchain_openai import OpenAIEmbeddings
store = LanceDB.from_documents(documents, OpenAIEmbeddings())
docs = store.similarity_search("…")
```

### LlamaIndex — `LanceDBVectorStore`
`pip install llama-index-vector-stores-lancedb`. `LanceDBVectorStore(uri="./lancedb", mode="overwrite", query_type="vector")` (Enterprise: `uri="db://…", api_key, region, host_override`). Wire via `StorageContext.from_defaults(vector_store=…)` → `VectorStoreIndex.from_documents(docs, storage_context=…)` → `.as_retriever(vector_store_kwargs={"where": lance_filter})` / `.as_query_engine(...)`. Filtering: Lance SQL `where` string OR LlamaIndex `MetadataFilters`. Hybrid: `vector_store._add_reranker(ColbertReranker())` + `query_type="hybrid"` (`integrations/ai/llamaIndex.mdx`).

### Agno — `agno.vectordb.lancedb.LanceDb`
Agentic-RAG knowledge backend: `LanceDb(uri="./tmp/lancedb", table_name=…, search_type=SearchType.hybrid, use_tantivy=False, embedder=OpenAIEmbedder(id="text-embedding-3-small"))` wrapped in `Knowledge(vector_db=…)`; attach to `Agent(model=…, knowledge=…, search_knowledge=True)` — retrieval becomes a `search_knowledge_base(...)` tool. `use_tantivy=False` selects native FTS for hybrid (`integrations/ai/agno.mdx`).

### Genkit (TypeScript) — `genkitx-lancedb`
`lancedb([{ dbUri: ".db", tableName: "table", embedder: textEmbedding004 }])` registers LanceDB as both **indexer** and **retriever**; custom flows via `lancedbIndexerRef`/`ai.index` and `lancedbRetrieverRef`/`ai.retrieve({retriever, query, options:{k:3}})`. TS-first RAG (`integrations/ai/genkit.mdx`).

### Kiln — desktop app + `kiln_ai`
No-/low-code RAG builder with deep LanceDB integration for vector, FTS (BM25), and hybrid; compares extractors/embedding models/chunking, runs evals, and can load into LanceDB Enterprise for production (`integrations/ai/kiln.mdx`).

### Hugging Face — direct `hf://` Lance scanning
`lance-huggingface` streams Lance datasets from the Hub without download: `db = lancedb.connect("hf://datasets/lance-format/laion-1m/data"); table = db.open_table("train")` (HF split = table name). Reuses author-built IVF_PQ/FTS indexes; supports projection/filter/vector/FTS scans and `list_versions()`. Upload with `hf upload-large-folder`. ⚠️ Heavy queries can hit HF rate limits — download locally for those (`integrations/ai/huggingface.mdx`).

### PromptTools / Synthetic Data Kit
**PromptTools** (`github.com/hegelai/prompttools`) — harness to test prompts + LanceDB configs against an LLM. **Meta Llama Synthetic Data Kit** — CLI (`ingest`/`create`/`curate`/`save-as`) that generates synthetic fine-tuning datasets stored in the **Lance format** (`--multimodal` yields text+image columns) (`integrations/ai/{prompttools,synthetic-data-kit}.mdx`).

## Design rules
- **Bind to LanceDB, don't front it with a second store** — every framework here uses LanceDB as the vector store; a competing store is the native-guard BLOCKER.
- **Prefer the native LanceDB path when the framework wrapper hides a knob** — index type/params, prefilter, reranker, tier are set on the LanceDB table; reach through the wrapper (`get_table()` / `vector_store`) when needed.
- **One Lance store, many access patterns** — DuckDB SQL, Polars/pandas analytics, FiftyOne visual search, and app vector search all hit the same tables; don't copy data out.
- **Match the framework's embedding to the table's** — if the wrapper embeds, ensure the model/dims match the table's pinned vector column, or use the LanceDB registry as the single source of truth.
- **Name the SDK** — Genkit is TS; LangChain/LlamaIndex/Agno/dlt are Python; some wrappers lag the core API — verify the version.
