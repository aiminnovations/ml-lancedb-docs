# Scaffold Templates — the complete, runnable LanceDB service starter files

> last-verified-against: LanceDB docs (`tables/*`, `indexing/*`, `search/*`, `embedding/*`) + SDK `lancedb==0.30.0`; **index build path live-run-verified on `lancedb==0.34.0`, 2026-07-14** (config-object API)
> Owner: `lancedb-pipeline-developer` (writes them) + `lancedb-schema-table-expert` (grounds them).
> The "complete usable" payload for `/lancedb-scaffold` — real, runnable files, not advice. Native-first; every
> API cited to a catalog. Generate only after confirmation; never overwrite an existing file without a diff first.

## Discovery (run first)
Inspect before generating, so the scaffold fits the actual project:
```bash
ls -la                                             # project layout
cat pyproject.toml requirements.txt package.json Cargo.toml 2>/dev/null   # which SDK?
python -c "import lancedb; print(lancedb.__version__)" 2>/dev/null         # installed Python SDK?
grep -rEl "lancedb|@lancedb/lancedb|lance" . 2>/dev/null                   # existing usage?
# detect store target: local dir vs db:// (Cloud/Enterprise) vs s3://
grep -rEl "connect\(|connect_async\(|LANCEDB_API_KEY|db://" . 2>/dev/null
```
Report what exists vs what's missing, then generate only the gaps. Pin the **dimension + metric + index type** before the first write — changing them later forces a full re-embed + re-index.

## 1. store.py — connect + schema (LanceModel auto-embedding) + create
The spine. Auto-embedding via the registry means ingest and query both embed automatically (OSS/Cloud; Enterprise embeds at ingest only — embed the query manually). Cite `tables-schema-catalog.md` + `embedding-reranking-catalog.md`.
```python
import lancedb
from lancedb.pydantic import LanceModel, Vector
from lancedb.embeddings import get_registry

# --- connect (choose the tier) ---
db = lancedb.connect("data/lancedb")                       # OSS embedded (local/s3:///gs:///az://)
# db = lancedb.connect("db://my-db", api_key="...", region="us-east-1")   # Cloud/Enterprise

# --- embedding function from the registry (pin the provider + dims) ---
func = get_registry().get("openai").create(name="text-embedding-3-small")  # ndims -> 1536

# --- schema: source column auto-embeds into the vector column ---
class Doc(LanceModel):
    id: str
    text: str = func.SourceField()                         # embedded on ingest
    vector: Vector(func.ndims()) = func.VectorField()      # FixedSizeList<float32, ndims>

table = db.create_table("docs", schema=Doc, mode="create", exist_ok=True)

def ingest(rows: list[dict]) -> None:
    # idempotent upsert on id (create a scalar index on the join key for speed)
    (table.merge_insert("id")
        .when_matched_update_all()
        .when_not_matched_insert_all()
        .execute(rows))
```

## 2. index.py — build the vector + scalar + FTS indexes, then optimize
Choose the index from `indexing-catalog.md` by scale + recall + filter-heaviness. Build is async — wait for it.
Uses the **unified config-object API** (verified on `lancedb==0.34.0`; the imperative `create_index(metric=…)`/`create_scalar_index`/`create_fts_index` forms are deprecated since 0.25.0 — see the catalog note).
```python
from lancedb.index import IvfHnswSq, IvfPq, BTree, Bitmap, FTS

# vector index: IVF_HNSW_SQ (best recall/latency) or IvfPq (max compression at dim<=256)
table.create_index("vector", config=IvfHnswSq(distance_type="cosine"))   # match the embedding model's metric
# table.create_index("vector", config=IvfPq(distance_type="cosine", num_partitions=..., num_sub_vectors=...))
table.wait_for_index(["vector_idx"])

# scalar index on every frequently-filtered column (accelerates prefilter)
table.create_index("id", config=BTree())                   # high-cardinality join key
# table.create_index("category", config=Bitmap())          # low-cardinality

# full-text index for hybrid/keyword search (native backend; with_position for phrases)
table.create_index("text", config=FTS(with_position=True))
table.wait_for_index(["text_idx"])

table.optimize()   # compaction + cleanup(>7d default) + fold new data into indexes
```

## 3. search.py — vector / fts / hybrid, filtered + reranked
Cite `search-query-catalog.md` + `embedding-reranking-catalog.md`. Query auto-embeds when you pass a string (OSS/Cloud).
```python
from lancedb.rerankers import RRFReranker

def vector_search(q: str, k: int = 10, where: str | None = None):
    query = table.search(q).limit(k)                       # auto-embeds the string query
    if where:
        query = query.where(where, prefilter=True)         # prefilter (default) uses the scalar index
    return query.refine_factor(10).to_list()               # refine rescoring on full vectors

def hybrid_search(q: str, k: int = 10):
    return (table.search(q, query_type="hybrid")           # vector + FTS fused
            .rerank(RRFReranker())                          # default hybrid reranker
            .limit(k)
            .to_pandas())
```

## 4. eval.py — recall vs brute-force + latency read (the verification gate)
The MANDATORY gate: prove the ANN index does not silently lose recall. Cite `search-query-catalog.md`.
```python
import time

def recall_at_k(queries, k=10):
    hits = 0
    for q in queries:
        exact = {r["id"] for r in table.search(q).bypass_vector_index().limit(k).to_list()}
        approx = {r["id"] for r in table.search(q).limit(k).to_list()}
        hits += len(exact & approx) / max(1, len(exact))
    return hits / len(queries)                              # target: >= 0.9; raise nprobes/refine_factor if low

def latency_ms(queries, k=10):
    t = time.perf_counter()
    for q in queries:
        table.search(q).limit(k).to_list()
    return (time.perf_counter() - t) * 1000 / len(queries)  # p50 proxy; measure p95 at scale
```

## 5. TypeScript variant (@lancedb/lancedb)
For a Node project. Cite the TS surface notes in the catalogs (some features — IvfSq, namespace admin — are Python/Rust-only).
```typescript
import * as lancedb from "@lancedb/lancedb";
import { getRegistry, LanceSchema } from "@lancedb/lancedb/embedding";
import "@lancedb/lancedb/embedding/openai";

const db = await lancedb.connect("data/lancedb");
const func = getRegistry().get("openai")!.create({ model: "text-embedding-3-small" });
const schema = LanceSchema({ text: func.sourceField(new lancedb.Utf8()), vector: func.vectorField() });
const table = await db.createEmptyTable("docs", schema, { mode: "overwrite" });
await table.add([{ text: "hello world" }]);
await table.createIndex("vector", { config: lancedb.Index.ivfPq({ distanceType: "cosine" }) });
const rows = await table.search("greetings").limit(10).toArray();
```

## 6. Readiness checklist (weights for /lancedb-status, 0–100)
- **Store + schema wired** (connect + typed schema, vector col as FixedSizeList, dims pinned) — 20
- **Vector index present + appropriate** (IVF_PQ/HNSW/RQ chosen for scale/filters, not brute-force at scale) — 25
- **Scalar/FTS indexes on filtered/keyword columns** — 15
- **Search path correct** (metric matches model, prefilter over scalar index, rerank for hybrid) — 15
- **Verification** (recall vs brute-force read + latency at scale + `optimize()` cadence) — 15
- **Storage + tier explicit** (backend + storage_options, OSS/Cloud/Enterprise named, secrets via env not hardcoded) — 10

## 7. CLAUDE.md section (append, never silently overwrite)
Generate a `## LanceDB Store` section documenting: the tier + SDK, the table/schema + pinned dims/metric, the index strategy + params, the search design, the storage backend, and the `optimize()` cadence — so the next session inherits the pinned invariants.
