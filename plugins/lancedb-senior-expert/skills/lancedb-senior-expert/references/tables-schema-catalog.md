# Tables + Schema Catalog — connect, create, schema, merge_insert, consistency

> last-verified-against: docs `tables/{index,create,schema,update,consistency,multimodal}.mdx`, `tables-and-namespaces.mdx` + SDK `lancedb==0.30.0`, 2026-07-14
> Sources: `docs/tables/*`; SDK `refs/ml-lancedb/python/python/lancedb/{__init__.py,db.py,table.py,merge.py,pydantic.py}`.
> Owner expert: `lancedb-schema-table-expert`. ⚠️ = version/tier/SDK-verify at build.

## Connect

`__init__.py:65` (sync) / `:218` (async):
```python
lancedb.connect(uri=None, *, api_key=None, region="us-east-1", host_override=None,
                read_consistency_interval=None, storage_options=None, session=None, ...) -> DBConnection
async_db = await lancedb.connect_async(uri, ...)
```
- **URI forms**: local path (`"data/lancedb"`), object store (`s3://…`, `gs://…`, `az://…`), Enterprise/Cloud (`db://your-db`).
- `api_key` set ⇒ LanceDB **Cloud/Enterprise** (env `LANCEDB_API_KEY`); `region` default `us-east-1`; `host_override` for Enterprise endpoints.
- `read_consistency_interval` is **OSS-only** (see Consistency).
- Enterprise: `lancedb.connect("db://db", api_key="…", region="us-east-1", host_override="https://…")`.

`connect` returns a `DBConnection`; `db["name"]` or `db.open_table(name)` opens a table; `db.drop_table(name, ignore_missing=True)` drops one. On `db://`, `open_table` returns a **`RemoteTable`**: `to_arrow()`/`to_pandas()` are NOT implemented — materialize via `table.search(q).limit(n).to_arrow()` or `table.head()` (`tables/index.mdx`, `enterprise/quickstart.mdx`).

## create_table

`db.py:856` (sync) / `:1342` (async):
```python
db.create_table(name, data=None, schema=None, mode="create", exist_ok=False,
                on_bad_vectors="error", fill_value=0.0, embedding_functions=None,
                *, namespace_path=None, storage_options=None, ...) -> LanceTable
```
`mode`: `"create"` (default) | `"overwrite"`; `exist_ok=False` raises if the table exists. Creation sources (`tables/create.mdx`):
- **List of dicts / dict** — `db.create_table("t", data, mode="overwrite")`.
- **Pandas / Polars** (Python-only) — pass the DataFrame; converted to Arrow before write.
- **PyArrow `Table`/`RecordBatch`**; **Rust** uses a `RecordBatchReader`; **batch iterators** for bulk ingest.
- **Pydantic `LanceModel`** (Python-only; `lancedb.pydantic`):
  ```python
  from lancedb.pydantic import LanceModel, Vector
  class Content(LanceModel):
      movie_id: int
      vector: Vector(128)         # -> FixedSizeList<float32, 128>
      title: str
  tbl = db.create_table("movies", schema=Content, mode="overwrite")
  ```
- **Empty table with an Arrow schema**:
  ```python
  schema = pa.schema([pa.field("vector", pa.list_(pa.float32(), 2)),
                      pa.field("item", pa.string()), pa.field("price", pa.float32())])
  tbl = db.create_table("t", schema=schema, mode="overwrite")
  ```
⚠️ TS uses `createTable`/`createEmptyTable`; Rust `create_table`. `LanceModel`, pandas, and Polars ingestion are Python-only.

## Schema

Arrow-typed. A **vector column** is `pa.list_(pa.float32(), dim)` = Arrow `FixedSizeList` (the Pydantic `Vector(dim)` maps to it; `pydantic.py`). Nested structs are supported (a nested pydantic model → `struct<…>`); field-level `metadata` carries blob encoding. `pydantic_to_schema(model)` yields the `pa.Schema`; type map (`integrations/data/pydantic.mdx`): int→int64, float→float64, bool→bool, str→utf8, list→List, BaseModel→Struct, `Vector(n)`→FixedSizeList(float32,n). Inspect with `table.schema`. A **multivector** column (ColBERT/ColPali) is `pa.list_(pa.list_(pa.float32(), dim))` (`search-query-catalog.md`).

## Write, update, delete

- `table.add(records)` — append (list of dicts / Arrow).
- `table.update(where=…, values={…})` or `values_sql={…}` — mutate matching rows. ⚠️ Nested-column updates not yet supported. Updated rows **leave the index** (still searchable, slower) — rebuild the index if you update a large fraction (`tables/update.mdx`).
- `table.delete(where)` — soft delete (`lance-format-catalog.md`). `table.count_rows(filter=None)`.

## merge_insert (upsert / SCD)

Builder API (`merge.py`, `tables/update.mdx`):
```python
(table.merge_insert("id")                       # join key(s)
    .when_matched_update_all(where=None)         # update existing keys
    .when_not_matched_insert_all()               # insert new keys      -> together = UPSERT
    .when_not_matched_by_source_delete(condition=None)   # delete target rows absent from source
    .execute(incoming_rows))
```
Three row groups — matched (both sides), not-matched (source only), not-matched-by-source (target only). Missing columns on newly-inserted rows are written `null` (fails if the column is non-nullable). It performs a **join on the key**, so **build a scalar index on the join column** (`indexing-catalog.md`) — ⚠️ HTTP 400 `Merge insert cannot be performed because the number of unindexed rows exceeds the maximum of 10000` means the scalar index is stale; run `optimize()`. When the source field feeds the embedding registry and the vector is empty, `merge_insert` auto-computes the embedding. This is the idempotent-ingest primitive — prefer it over `add` for anything re-runnable.

## Multimodal columns

Store raw bytes beside vectors + metadata in a binary column; define the schema explicitly so blobs are `binary`/`large_binary`, not string/list. Large media uses the Blob API (`large_binary` + `{"lance-encoding:blob":"true"}`) for lazy reads (`lance-format-catalog.md`, `tables/multimodal.mdx`). Pattern: one table with `id`, `text`, `image_bytes` (blob), `vector` (from an OpenCLIP/ImageBind/ColPali embedder) — the whole multimodal record in one Lance table, no side blob store.

## Consistency (OSS `LanceTable`)

`read_consistency_interval` on `connect` (`tables/consistency.mdx`), reads only (writes are always consistent):
1. **Unset (default)** — no cross-process refresh; a reader won't see another process's writes until it reconnects/`checkout_latest()`.
2. **`timedelta(0)`** — check on every read (strongest, most requests).
3. **Non-zero interval** — eventual refresh after the interval elapses.
```python
reader = lancedb.connect(uri, read_consistency_interval=timedelta(0))
```
Manual refresh: `table.checkout_latest()`. On Enterprise/`RemoteTable`, consistency is a deployment setting (`weak_read_consistency_interval_seconds`) — not an SDK knob; `checkout_latest` still works.

## Bad vectors (Python-only)

`on_bad_vectors` on create/add; invalid = wrong dimension / NaN / null on a non-nullable column (`tables/consistency.mdx`): `error` (default, raises), `drop`, `fill` (with `fill_value`, default `0.0`), `null` (nullable columns only). Set this explicitly when ingesting embeddings from an external source you don't fully trust.

## Tables vs namespaces (orientation)

A **table** = data (schema, rows, indexes, versions). A **namespace** = a catalog object (a hierarchy of names + table grouping + name resolution). `LanceTable` (direct: local/`file://`/`s3://`, common in OSS) vs `RemoteTable` (catalog-backed `db://`, Enterprise) expose the same table API; namespaces are covered in `storage-deployment-catalog.md`. ⚠️ Note the Python `create_table` real signature uses kw-only `namespace_path=`, while several docs snippets use `namespace=` — verify against your installed SDK.

## Design rules
- **Type the schema up front** — `LanceModel` (Python) or an Arrow schema; pin the vector dim in `Vector(dim)`/`FixedSizeList`. Empty-table-plus-schema when you control types exactly.
- **Prefer `merge_insert` for re-runnable ingest** — idempotent upsert on a keyed, scalar-indexed column; `add` only for pure appends.
- **Name the tier + SDK** — `RemoteTable` lacks `to_pandas`/`to_arrow`; `LanceModel`/pandas/Polars are Python-only; `read_consistency_interval` is OSS-only.
- **Set `on_bad_vectors` on untrusted ingest** — don't let a NaN/dim-mismatch abort a batch silently.
- **Explicit multimodal schema** — binary/large_binary columns with blob metadata, never a stringified blob.
