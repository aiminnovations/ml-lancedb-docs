# Lance Format Catalog — versioning, zero-copy evolution, blobs, compaction

> last-verified-against: docs `lance.mdx`, `tables/versioning.mdx`, `tables/schema.mdx`, `tables/update.mdx` + SDK `lancedb==0.30.0` (`table.py`); **versioning/checkout/tags/add_columns/alter_columns/drop_columns/optimize live-run-verified on `lancedb==0.34.0`, 2026-07-14**
> Sources: `docs/lance.mdx`; `docs/tables/{versioning,schema,update,multimodal}.mdx`; SDK `refs/ml-lancedb/python/python/lancedb/table.py` (versioning/tags/optimize). SDK read at core `0.28.0-beta.4`.
> Owner expert: `lancedb-schema-table-expert`. ⚠️ = version/tier/SDK-verify at build. `lancedb-docs-curator` keeps fresh.

## Overview

Lance is an open **lakehouse format** — a file format + table format + catalog spec — that is multimodal-first, Arrow-native, and built for object storage (`lance.mdx`). It brings vector search, full-text search, random access, and feature engineering into one system, so you do not build bespoke ETL between a blob store, a vector DB, and a training pipeline. LanceDB is the database built on Lance; understanding the format is what makes the rest of the catalogs make sense.

Three format properties drive every design decision (`lance.mdx`):
1. **Arrow-native columnar storage** — interoperable with the open lakehouse (pandas, Polars, DuckDB, PyArrow) with zero-copy in many paths.
2. **Zero-copy data evolution** — derived columns (features, embeddings) are added *without rewriting existing data*. Only the new column is written; the expensive columns (images, video) are untouched.
3. **Versioned data** — every write creates a new version + a manifest update. Time-travel and rollback are free.

## Fragments, manifest, versions

Data lives in **fragments**; each fragment has one or more `DataFile`s and at most one **deletion file per version** (absent until something is deleted) (`lance.mdx`, `tables/versioning.mdx`). A **manifest** tracks versions via metadata: each version stores only the new/updated data of that transaction plus metadata. So 100 versions are NOT 100 copies of the data — but they DO carry 100× the metadata, which slows queries. **Prune versions you don't need** (`lance.mdx`).

Which operations create a version:
- **Create version:** `create`, `add`, `update`, `delete`, `merge_insert`, `restore`, and system ops (`optimize()`, index build, compaction) all increment the version.
- **Do NOT create a version:** reads, `list_versions`, `version`, `checkout`, `checkout_latest`.

Docs example sequence on a fresh table: v1 create → v2 update → v3 add → v4 restore → v5 delete (`tables/versioning.mdx`).

## Versioning / time-travel (real API)

Python `Table` (`table.py`, `tables/versioning.mdx`):
- `table.version` — current version (property).
- `table.list_versions() -> list[dict]` — each dict has `version` and `timestamp`.
- `table.checkout(version)` — read-only "detached head"; accepts a **version number OR a tag string**. Disables the read-consistency interval; writes fail while checked out.
- `table.checkout_latest()` — return to latest / undo a checkout; also a manual refresh when `read_consistency_interval=None`.
- `table.restore(version=None)` — in-place; creates a NEW version equivalent to the target (data is not copied). Without an arg, restores the currently checked-out version.

**Tags** via `table.tags` (class `Tags`): `.list() -> dict[str, Tag]`, `.get_version(tag) -> int`, `.create(tag, version)`, `.update(tag, version)`, `.delete(tag)`. Async: `AsyncTags`. Tag stable checkpoints (e.g. `"prod-2026-07"`) so `checkout("prod-2026-07")` is reproducible — the backbone of **time-travel RAG** (see `use-cases-catalog.md`).

```python
v1 = table.version
table.add(new_rows)                       # -> v2
old = table.checkout(v1)                   # read the pre-add state (read-only)
table.checkout_latest()                    # back to v2
table.restore(v1)                          # -> v3, contents == v1, nothing copied
table.tags.create("golden", table.version)
```

## Zero-copy schema evolution (real API)

`tables/schema.mdx` — the format's signature capability:
- `table.add_columns(transforms)` — `transforms` is `dict[str,str]` (col → SQL expression), or `pa.Field` / `list[pa.Field]` / `pa.Schema` (adds null-initialized typed columns). Returns `AddColumnsResult` (new `version`). NULL defaults must be cast: `{"created": "cast(NULL as timestamp)"}`.
- `table.alter_columns(*alterations)` — dicts with keys `path`, `rename`, `data_type`, nullability. Rename/nullability only touch metadata (cheap); a `data_type` change **rewrites the column** (costly).
- `table.drop_columns(columns) -> DropColumnsResult` — irreversible; the bytes are reclaimed at compaction.

```python
table.add_columns({"discounted": "cast((price * 0.9) as float)"})   # computed column
table.alter_columns({"path": "discounted", "rename": "sale_price"})
table.drop_columns(["temp_col"])
```

⚠️ **Changing a `FixedSizeList` vector's dimension is NOT a compatible cast.** To re-embed at a new dim, use the 3-step pattern: `add_columns` the new-dim column (via `arrow_cast`/recompute) → `drop_columns` the old → `alter_columns` rename the replacement (`tables/schema.mdx`). This is why the `planning-checklist` pins the dimension before the first write.

## Blob / multimodal encoding

Small binaries use a plain `pa.binary()` column. Large files (MB–100s of MB) use the **Blob API**: a `pa.large_binary()` column PLUS field metadata `{"lance-encoding:blob": "true"}`, which enables **lazy, file-like reads** so you work with datasets larger than memory (`tables/multimodal.mdx`, `geneva/udfs/blobs.mdx`).
```python
schema = pa.schema([
    pa.field("id", pa.int64()),
    pa.field("video", pa.large_binary(), metadata={"lance-encoding:blob": "true"}),
])
```
In a UDF, a blob column arrives as `lance.blob.BlobFile` → `blob.read()`; to write a blob, return `bytes` with `data_type=pa.large_binary()` + the blob metadata (`geneva-catalog.md`).

## Deletion semantics (soft delete + recovery)

`delete(where)` is a **soft delete** — rows are marked in the fragment's deletion file and excluded from queries (including index segments), but the bytes remain recoverable as long as the version exists (`lance.mdx`, `tables/update.mdx`). This is why time-travel can undo a delete. If you delete **all** rows and re-ingest, recreate the index. Bytes are physically reclaimed only at cleanup (below).

## Compaction / optimize / cleanup

Modeled on Postgres `VACUUM`. `table.optimize(*, cleanup_older_than: timedelta | None = None, delete_unverified=False, retrain=False)` runs three operations (`tables/update.mdx`, `lance.mdx`):
1. **Compaction** — merges small fragments, removes deleted rows and dropped columns. Read-perf focused; **disk can temporarily grow** because new compacted files coexist with old-version files until cleanup.
2. **Prune** — removes versions older than the retention window. `cleanup_older_than` **defaults to 7 days**; `timedelta(0)` removes all but the latest.
3. **Index** — folds new (unindexed) rows into existing indexes.

Cleanup-only: `table.cleanup_old_versions(older_than=None, *, delete_unverified=False)` — `older_than` defaults to **two weeks**. Compaction-only: `table.compact_files()`. `retrain` is a deprecated no-op ⚠️.

**Tier behavior:** OSS = compaction + cleanup are **manual** — run `optimize()` on a cadence (after large ingests / before heavy read windows). Cloud manages it automatically (`cleanup_old_versions` not available on Cloud). Enterprise auto-compacts/cleans on a cluster-configured schedule.

## New-table format options (via `storage_options`)

`storage/configuration.mdx` — set at `create_table`:
- `new_table_data_storage_version`: `legacy` | `stable` (**default `stable`** — current format, better performance; `legacy` only for old-client compat).
- `new_table_enable_v2_manifest_paths`: default `false`; v2 manifest naming, requires LanceDB ≥ 0.10.0 to read.
- `new_table_enable_stable_row_ids`: default `false`; keeps row IDs stable across compaction/delete/merge — enable if you rely on `_rowid` joins.
- ⚠️ The old `data_storage_version=` param on `create_table` is **deprecated** — use `new_table_data_storage_version` in `storage_options`.

## Lance vs Parquet

Both are columnar and cloud-native. Lance adds what general Parquet lacks (`lance.mdx`): built-in **versioning/time-travel**, **fast random access** for ML training/inference (not just scans), **native multimodal/blob** storage, and **zero-copy column evolution**. Choose Lance when data is versioned, multimodal, or feeds training; Parquet stays fine for static analytical dumps.

## Design rules
- **Pin dimension + metric + storage version before the first write** — they are the format-level invariants; changing a vector's dim is a rewrite (record them in the handoff).
- **Add features as columns, don't rewrite** — `add_columns` with an SQL expression or a Geneva UDF; only the new column is written.
- **Prune versions** — every write is a version; unbounded history slows queries (metadata bloat). Tag the checkpoints you need, `optimize(cleanup_older_than=...)` the rest.
- **Use blob encoding for large binaries** — `large_binary` + `lance-encoding:blob` metadata, not a plain binary column, so reads stay lazy.
- **Lean on soft-delete + versioning for safety** — migrations and destructive edits are reversible via `restore`; that is the data-safety guarantee the quorum verifies.
