# Training + Multimodal Catalog — Lance as the ML training data backend

> last-verified-against: docs `training/{index,torch}.mdx`, `tutorials/*`, 2026-07-14
> Sources: `docs/training/*`; the Lance `torch`/`permutation` data-loader API; the multimodal-lakehouse story.
> Owner expert: `lancedb-integrations-expert`. ⚠️ = version/tier/SDK-verify at build.

## Why Lance for training

Lance is a training-data backend for **random-access, versioned, multimodal** data (`training/index.mdx`). Naive loading iterates the whole table; the value comes from **random access** (sample any row without a full scan), **zero-cost versioning/time-travel** (train reproducibly against a tagged dataset version — see `lance-format-catalog.md`), **native multimodal storage** (images/video/audio/blobs beside labels + embeddings in one table), and **streaming/distributed loading** across nodes. This is the same store the app queries as vectors — no export step between "retrieval store" and "training set."

## The Permutation API (`training/index.mdx`)

`lancedb.permutation` adds row selection, splits, shuffling, and column projection on top of a table:
- `Permutation.identity(table)` — all rows, no separate permutation table; then `.select_columns(["id","prompt"])` to cut IO.
- **Permutation tables** mark which row ids form the dataset (in-memory by default, persistable/shareable across processes/nodes for distributed training): `permutation_builder(table).filter("category = 'cat'").execute()` → `Permutation.from_tables(table, perm_tbl)`.
- **Splits:** `permutation_builder(table).split_random(ratios=[0.95,0.05], split_names=["train","test"]).execute()` → `Permutation.from_tables(table, tbl, split="train")`.
- **Shuffle:** `permutation_builder(table).shuffle().execute()` (avoids order-artifact overfitting).

Column selection reduces I/O; persistable permutation tables are what make multi-node loading consistent (every worker reads the same shuffle/split).

## PyTorch integration (`training/torch.mdx`)

The LanceDB `Table` implements `torch.utils.data.Dataset` — use it directly:
```python
from torch.utils.data import DataLoader
loader = DataLoader(table, batch_size=1024, shuffle=True)   # yields pyarrow.RecordBatch by default
```
Provide a `collate_fn` to convert `RecordBatch` → tensors. `Permutation` is more flexible — default output is a list of dicts; `.with_format(...)` supports **zero-copy** `arrow`/`polars` (and usually `numpy`/`pandas`/`torch_col`), while `python`/`torch` require a full copy (slowest):
```python
ds = Permutation.identity(table).select_columns(["image","label"]).with_format("torch_col")
loader = DataLoader(ds, batch_size=256, collate_fn=lambda x: x)   # torch_col => column-major (C, R); MUST pass identity collate
```
⚠️ `torch_col` produces a column-major tensor `(C, R)` — pair it with `collate_fn=lambda x: x` or you hit `TypeError: stack()…`. Prefer `arrow`/`polars`/`torch_col` (zero-copy) over `python`/`torch` (copy) for throughput.

## Multimodal lakehouse

Store the full multimodal record — raw media (blob-encoded `large_binary`, `lance-format-catalog.md`), text, labels, and embeddings — in one Lance table. The training loader reads media + label columns; the serving path queries the same table's vector index (`search-query-catalog.md`); Geneva backfills new feature columns (`geneva-catalog.md`) without a rewrite. Recipes demonstrate the pattern end to end: `cli-sdk-to-convert-image-datasets-to-lance`, `llm-pretraining-dataloading`, `fine-tuning_LLM_with_PEFT_QLoRA` (`use-cases-catalog.md`).

## Design rules
- **Use `Permutation` for splits/shuffle/projection** — don't hand-roll sampling; persist the permutation table for reproducible, multi-node loading.
- **Prefer zero-copy formats** (`arrow`/`polars`/`torch_col`) over `python`/`torch` copies for loader throughput; remember `torch_col` needs the identity `collate_fn`.
- **Train against a tagged version** — `checkout`/tag the dataset version so a training run is reproducible and auditable.
- **One multimodal table, three consumers** — training loader, serving vector search, and Geneva feature backfill all read the same Lance table; don't export a separate training copy.
- **Blob-encode large media** — `large_binary` + blob metadata keeps loading lazy at scale.
