# Indexing + Quantization Catalog — vector, scalar, FTS indexes; PQ/SQ/RaBitQ

> last-verified-against: docs `indexing/{index,vector-index,fts-index,scalar-index,gpu-indexing,quantization,reindexing}.mdx` + SDK `lancedb==0.30.0` (`table.py`, `index.py`), 2026-07-14
> Sources: `docs/indexing/*`; SDK `refs/ml-lancedb/python/python/lancedb/table.py` (`create_index`/`create_scalar_index`/`create_fts_index`), `index.py`.
> Owner expert: `lancedb-indexing-expert`. ⚠️ = version/tier/SDK-verify at build. This is the highest-leverage catalog — a wrong index type or param is expensive to unwind.

## Vector indexes

Two algorithm families (`indexing/index.mdx`, `indexing/vector-index.mdx`): **IVF** (inverted file — partitions vectors into cells) and **HNSW** (a graph). HNSW is NOT a top-level index — it is a sub-index *inside* IVF partitions (`IVF_HNSW_PQ` / `IVF_HNSW_SQ`): IVF partitions, then each probed partition is searched with an HNSW graph. Named types: `IVF_FLAT`, `IVF_PQ`, `IVF_SQ`, `IVF_RQ`, `IVF_HNSW_PQ`, `IVF_HNSW_SQ`. Metrics: `l2` (default), `cosine`, `dot`, `hamming` (binary/`IVF_FLAT` only). ⚠️ TypeScript does not support `IvfSq`.

**Choosing the index** (`indexing/vector-index.mdx`):
| Priority | Index | Compressed size vs raw |
|---|---|---|
| Best recall/latency trade-off | `IVF_HNSW_SQ` | a little larger than 1/4 |
| Maximum compression | `IVF_RQ` (RaBitQ) | ~1/32 |
| Higher accuracy at small dims (dim ≤ 256) | `IVF_PQ` | 1/64 – 1/16 (per `num_sub_vectors`) |

⚠️ **Filter-heavy workloads:** if searches frequently carry `where(...)` filters, prefer `IVF_RQ` or `IVF_PQ` — `IVF_HNSW_SQ` latency can fluctuate significantly under filters (`indexing/vector-index.mdx` warning).

### create_index (real signature, `table.py:745`)
```python
table.create_index(
    metric="l2",              # l2 | cosine | dot | hamming
    num_partitions=256,       # IVF cells      (⚠️ imperative static default 256)
    num_sub_vectors=96,       # PQ sub-vectors (⚠️ imperative static default 96)
    vector_column_name="vector",
    replace=True,
    accelerator=None,         # "cuda" | "mps" for GPU build
    *, index_type="IVF_PQ",
    num_bits=8,               # IVF_PQ only; ONLY 4 or 8 (default 8)
    m=20, ef_construction=300,# HNSW: neighbors/node, build candidates
    wait_timeout=None, train=True,
)
```
⚠️ **Defaults skew by API surface:** the imperative `create_index` uses static `num_partitions=256`/`num_sub_vectors=96`, while the async config class `IvfPq` (`index.py:514`) *derives* them from data — `num_partitions` default = `sqrt(num_rows)`, `num_sub_vectors` = `dim / 16`. Set them explicitly at scale rather than trusting a default.

Build is **asynchronous**: `create_index` returns immediately; block with `wait_timeout=` or `table.wait_for_index([name])`. Index name = `<column>_idx` (e.g. `vector_idx`). Check with `list_indices()` (returns only after fully built) and `index_stats(name)`. Rough build time: minutes per 1M × 1536-dim vectors.

### Tuning rules of thumb (`indexing/vector-index.mdx`)
- `IVF_HNSW_SQ`: `num_partitions ≈ num_rows / 1_048_576`; `ef_construction ≈ 150`.
- `IVF_RQ`: `num_partitions ≈ num_rows / 4096`.
- `IVF_PQ`: `num_partitions ≈ num_rows / 4096`; `num_sub_vectors ≈ dim / 8` (raise for recall, lower for speed/size). Prefer PQ over RQ for dim ≤ 256.
- General IVF heuristic elsewhere in the docs: `num_partitions ≈ sqrt(num_rows)`. `num_sub_vectors` must **divide the dimension**.

### Binary vectors
Store as fixed-size `uint8` (8 bits/byte); dimension must be a **multiple of 8** (128-dim → 16-byte uint8; pack with `np.packbits`). Index with `index_type="IVF_FLAT"`, `metric="hamming"` (`indexing/vector-index.mdx`, `search/vector-search.mdx`).

## Quantization (`indexing/quantization.mdx`)

| Quant | Use | Notes |
|---|---|---|
| **PQ** (Product) | Default; balance size/recall | Splits the vector into sub-vectors, each → nearest codebook centroid. Lossy. 128×float32 → 128× smaller with 8-bit codes. |
| **SQ** (Scalar) | Faster indexing, stable value ranges | Quantizes each dim independently; less compression than PQ, cheaper to build. |
| **RQ** (RaBitQ) | Maximum compression | ~1 bit/dim + 2 corrective scalars; needs `dim % 8 == 0`. 1024-dim float32 (4 KB) → a few hundred bytes. Avoids PQ codebook training; handles updates more gracefully. |
| **None/Flat** | Binary (hamming) or max recall | Raw vectors. |

`num_bits`: RaBitQ default `1` (raise to 2/4/8 for fidelity at higher cost); IVF_PQ supports **only 4 or 8** (default 8). Pin the quantization *before* the index build — changing it is a rebuild.

## Scalar indexes (`indexing/scalar-index.mdx`)

Accelerate `where` filters, prefilters combined with vector/FTS search, and update/delete/merge predicates. Types:
- **`BTREE`** (default) — sorted; for numeric/string/temporal columns with **many distinct values**; supports `<, =, >, in, between, is null`.
- **`BITMAP`** — one bitmap per distinct value; for **low cardinality** (< ~1,000 uniques / boolean).
- **`LABEL_LIST`** — for `List<T>` columns; supports `array_contains_all` / `array_contains_any`.

```python
table.create_scalar_index("book_id")                          # BTREE
table.create_scalar_index("publisher", index_type="BITMAP")
```
Signature (`table.py:850`): `create_scalar_index(column, *, replace=True, index_type="BTREE", wait_timeout=None, name=None)`. New data requires `optimize()` to fold into the scalar index. UUID columns supported as `FixedSizeBinary(16)` (Python ≥ 0.22.0). **Best practice: build a scalar index on every frequently-filtered column** (`search/filtering.mdx`) — and on every `merge_insert` join key.

## Full-text search (FTS) index (`indexing/fts-index.mdx`)

BM25. Two backends: **native lance-index** (default, `use_tantivy=False`) vs legacy **Tantivy** (`use_tantivy=True`). ⚠️ `with_position` is native-only; `writer_heap_size`/`ordering_field_names`/`tokenizer_name` are Tantivy-only.
```python
table.create_fts_index("text", use_tantivy=False, with_position=True)   # sync
table.wait_for_index(["text_idx"])
# AsyncTable has no create_fts_index -> use the config object:
from lancedb.index import FTS
await tbl.create_index("text", config=FTS(language="English"))
```
Key params (`indexing/fts-index.mdx`): `with_position` (default `False`; **required for phrase queries**), `base_tokenizer` (`simple`/`whitespace`/`raw`/`ngram`), `language` (`English`), `max_token_length` (40), `lower_case` (True), `stem` (True), `remove_stop_words` (True), `ascii_folding` (True), `ngram_min_length`/`ngram_max_length` (3/3), `prefix_only` (False). **Phrase queries need `with_position=True` AND `remove_stop_words=False`.** Substring search needs `base_tokenizer="ngram"`. FTS also works on string-array columns. ⚠️ `create_fts_index` is marked "highly experimental" in the SDK docstring — pin the version.

## GPU indexing (`indexing/gpu-indexing.mdx`)

Manual OSS GPU build via the **Python sync SDK only**, requires PyTorch > 2.0:
```python
table.create_index(num_partitions=256, num_sub_vectors=96, accelerator="cuda")  # Linux/NVIDIA
table.create_index(num_partitions=256, num_sub_vectors=96, accelerator="mps")   # Apple Silicon
```
`AssertionError: Torch not compiled with CUDA enabled` → install a CUDA PyTorch build. GPU memory scales with `num_partitions` × dims. Enterprise does automatic GPU indexing (billions of rows in < 4 h on a 1–8 GPU cluster).

## Reindexing + optimize (`indexing/reindexing.mdx`)

New rows are **unindexed** until folded in; until then queries combine index results with a **flat scan** over the new rows (latency grows with unindexed volume). `table.optimize()` is the single entry point — compaction + cleanup(>7d default) + **incremental index update**:
```python
table.add(new_rows); table.optimize()                     # fold new data in
table.optimize(cleanup_older_than=timedelta(days=1))       # aggressive version reclaim
```
`index_stats()` shows `num_unindexed_rows` (0 = fully indexed). During a rebuild, set `fast_search=True` to search only indexed data. Enterprise auto-reindexes in the background. ⚠️ Compaction doesn't immediately free disk — space is reclaimed when old versions are pruned.

## Design rules
- **Pick the vector index by scale + recall + filter-heaviness** — `IVF_HNSW_SQ` for the best recall/latency default; `IVF_PQ` for dim ≤ 256 or memory pressure; `IVF_RQ` for max compression; `IVF_HNSW_SQ` is risky under heavy filters (prefer PQ/RQ there).
- **Set `num_partitions`/`num_sub_vectors` explicitly at scale** — don't trust the imperative static defaults; `num_sub_vectors` must divide the dimension.
- **Scalar-index every filtered column and every merge_insert/update join key** — it's what makes prefiltering and upserts fast (and avoids the 10k-unindexed merge error).
- **FTS: native backend, `with_position` for phrases** — and `remove_stop_words=False` for phrase queries; ngram tokenizer for substring.
- **`optimize()` on a cadence** — new data is brute-forced until folded in; on OSS this is manual.
- **Pin quantization + metric before build** — changing them is a full rebuild; `num_bits` is 4/8 for PQ, 1(+) for RaBitQ.
