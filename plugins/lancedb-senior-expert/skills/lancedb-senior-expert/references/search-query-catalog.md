# Search + Query Catalog — vector, multivector, FTS, hybrid, filtering, tuning

> last-verified-against: docs `search/{index,vector-search,multivector-search,full-text-search,hybrid-search,filtering,optimize-queries,sql/*}.mdx` + SDK `lancedb==0.30.0`; **vector/prefilter/fts/hybrid-RRF/refine_factor/bypass_vector_index/explain_plan live-run-verified on `lancedb==0.34.0`, 2026-07-14** (recall@10=1.0)
> Sources: `docs/search/*`; SDK `query.py`; DataFusion predicate reference.
> Owner expert: `lancedb-search-expert`. ⚠️ = version/tier/SDK-verify at build.

## Query types

`table.search(query, query_type=…)`: `"vector"`, `"fts"`, `"hybrid"`, `"auto"` (a `str` → FTS if an FTS index exists / else auto-embed to vector; a vector/array → ANN). Passing a string auto-embeds the query when the table has an embedding function (OSS/Cloud; ⚠️ Enterprise embeds at ingest only — pass a pre-computed query vector). Result converters: `.to_list()`, `.to_pandas()`, `.to_arrow()`, `.to_polars()` (async), `.to_pydantic(Model)`. Result columns: `_distance` (vector), `_score` (FTS/BM25), `query_index` (batch), `_relevance_score` (reranked).

## Vector search (`search/vector-search.mdx`)

Metrics: `l2` (default, Euclidean), `cosine` (unnormalized ok), `dot` (normalized, fastest), `hamming` (binary/`IVF_FLAT`). **Use the metric the embedding model was trained with.** The metric is configurable at search time only if no index exists; otherwise the index's build-time metric wins.
```python
tbl.search(vec).distance_type("cosine").limit(10).to_list()
```
Tuning knobs:
- `.limit(k)` — result count.
- `.nprobes(n)` — IVF partitions scanned; **auto-tuned by default** — leave unset; raise only when recall is below target (diminishing returns), lower for speed.
- `.refine_factor(rf)` — reads extra candidates and **rescores on full vectors in memory** → better `_distance` fidelity + recall. The main recall lever after `nprobes`.
- `.ef(n)` — for `IVF_HNSW_SQ`; start ~`1.5*k`, up to `10*k` for higher recall.
- `.distance_range(lower_bound=, upper_bound=)` — bound results by similarity (one-sided ok).
- `.select([cols])` — project columns (cuts IO); `.fast_search=True` — indexed data only; `.bypass_vector_index()` — exact brute-force kNN.

**`_distance` semantics:** no index / `bypass_vector_index()` → exact true distance; indexed ANN without `refine_factor` → **approximate distance on compressed vectors**; with `refine_factor(≥1)` → recomputed on full vectors for the reranked candidates. **Batch/multi-query:** pass a list/matrix of vectors → results carry `query_index`.

## Multivector search (`search/multivector-search.mdx`)

For late-interaction models (ColBERT, ColPali, XTR). Column is `pa.list_(pa.list_(pa.float32(), dim))` — many vectors per row. **Only `cosine`.** Scoring is **MaxSim**: `Σ_i max_j sim(q_i, d_j)`.
```python
tbl.create_index(metric="cosine", vector_column_name="vector")   # standard IVF_PQ over the multivector col
tbl.search(np.random.random(256)).limit(5).to_pandas()           # single query vector
tbl.search(np.random.random((2, 256))).limit(5).to_pandas()      # multi-vector (late interaction)
```
For < ~100K rows indexing can be skipped. Pairs with multivector reranking + XTR (see the "needle in a haystack" tutorial in `use-cases-catalog.md`).

## Full-text search (`search/full-text-search.mdx`)

Requires an FTS index (`indexing-catalog.md`). String input auto-routes to FTS.
```python
table.search("puppy").limit(10).select(["text"]).to_list()      # returns _score (BM25)
table.search("moon", fts_columns="text")                        # restrict indexed columns
```
Query objects (`from lancedb.query import …`) for structured FTS: `MatchQuery(term, column, fuzziness=, prefix_length=)`, `PhraseQuery(phrase, column, slop=)`, `BoostQuery(positive, negative, negative_boost=0.5)`, `MultiMatchQuery(term, [cols], boosts=[…])`, `BooleanQuery([(Occur, subquery), …])`. Fuzzy: `fuzziness` auto (0/1/2 by term length). Phrase: needs `with_position=True`. ⚠️ Raw `OR`/`AND` keywords inside the search **string** are NOT parsed — use `BooleanQuery` (Python `&`/`|`; TS `Occur.Must`/`Should`/`MustNot`, ≥1 Should/Must required). Substring needs the ngram tokenizer.

## Hybrid search (`search/hybrid-search.mdx`)

Vector + FTS fused by a reranker. **Default reranker is `RRFReranker()`** (reciprocal rank fusion).
```python
from lancedb.rerankers import RRFReranker
(table.search("flower moon", query_type="hybrid", vector_column_name="vector", fts_columns="text")
    .rerank(RRFReranker())
    .limit(10).to_pandas())
# explicit vector + text:
table.search(query_type="hybrid").vector(vec).text("flower moon").limit(5).to_pandas()
```
Config: `normalize` default `"score"` (or `"rank"`); `reranker` default `RRF()`. TS: `.fullTextSearch(text).nearestTo(vector).rerank(reranker)`. Hybrid is the default for keyword-plus-semantic corpora; tune the reranker for the domain (`embedding-reranking-catalog.md`).

## Filtering + SQL (`search/filtering.mdx`, `search/sql/*`)

Predicates run on **DataFusion**. Supported: `>, >=, <, <=, =`, `AND/OR/NOT`, `IS [NOT] NULL`, `IS TRUE/FALSE`, `IN`, `LIKE`/`NOT LIKE`, `CAST`, `regexp_match(col, pattern)`, `array_has_any`/`array_has_all`, plus DataFusion scalar functions.
```python
table.search(vec).where("(item IN ('foo','bar')) AND (price > 15.0)").limit(5).to_pandas()   # prefilter (default)
table.search(vec).where("label > 1", prefilter=False).limit(5).to_pandas()                    # postfilter
table.search().where("price > 15").limit(3).to_arrow()                                         # pure SQL, no vector
```
- **Prefilter (default)** applies the filter *before* ANN — backed by a scalar index it's fast and returns full `limit`. **Postfilter** (`prefilter=False` / TS `.postfilter()`) filters *after* ANN — can return fewer than `limit`.
- Backtick special/keyword/uppercase column names; ⚠️ field names containing **periods** are unsupported. Literals: `date '2021-01-01'`, `timestamp '…'`, `decimal(8,3) '1.000'`.
- Highly selective filter → consider `bypass_vector_index()`. When in doubt, prefilter.
- **Enterprise SQL** (`search/sql/index.mdx`, Enterprise-only): Arrow **FlightSQL** endpoint (port 10025), DataFusion engine; Python `flightsql-dbapi`, TS `@lancedb/flightsql-client`. **Enterprise FTS-SQL** (`search/sql/fts-sql.mdx`, ⚠️ beta): `fts()` UDTF with a JSON query (`MatchQuery(...).to_json()`); add `ORDER BY _score DESC` or results are unordered.

## Query optimization (`search/optimize-queries.mdx`)

- `.explain_plan(verbose)` — logical plan, no execution; confirm index selection / spot missing indexes.
- `.analyze_plan()` — executes and annotates the physical plan with `output_rows`, `elapsed_compute`, `bytes_read`, `iops`, `index_comparisons`, `parts_loaded`.
- Operators to know: `LanceScan` (base scan — high `bytes_read`/`iops` ⇒ add an index), `KNNVectorDistance` (brute-force distance), `ANNIvfPartition (nprobes=N)`, `ANNSubIndex`, `ScalarIndexQuery`, `SortExec: TopK`.
- Index the columns in `WHERE`, the vector columns, and the `merge_insert` join columns; recommended by type: Vector→IVF_PQ/IVF_HNSW_SQ, Scalar→BTree, Categorical→Bitmap, List→Label_list. `.select()` to cut IO; keep `num_unindexed_rows ≈ 0`. Documented example: scalar+vector indexes cut a 1.2M-row query from 1.1M comparisons to ~26K (99.8% ↓).

## Design rules
- **Match the metric to the embedding model** — and remember the index's build-time metric wins once an index exists.
- **Tune recall with `refine_factor` first, `nprobes` second** — `nprobes` auto-tunes; raise `refine_factor` for fidelity; `ef` for HNSW.
- **Prefilter over a scalar index** — the default and usually right; postfilter only when you understand the shortfall risk.
- **Verify recall against `bypass_vector_index()`** — the brute-force result is ground truth; the eval gate compares against it.
- **Read the plan when latency is off** — `explain_plan`/`analyze_plan` reveal a `LanceScan` that wants an index or an ANN with too-high `nprobes`.
- **Hybrid = vector + FTS + reranker** — RRF by default; pass a domain reranker for quality.
