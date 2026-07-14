# Geneva Catalog — multimodal feature engineering at scale

> last-verified-against: docs `geneva/{index,overview,udfs/*,udfs/providers/*,jobs/*,deployment/*,reference}.mdx`, 2026-07-14
> Sources: `docs/geneva/*`. Geneva is a LanceDB **Enterprise** package (`geneva`). ⚠️ Beta features noted inline.
> Owner expert: `lancedb-integrations-expert`.

## Overview

Geneva is LanceDB's **Multimodal Feature Engineering** framework — a Python package (`geneva`) that defines features as **columns** in a Lance dataset via UDFs, then computes them with distributed **Ray/KubeRay** jobs (`geneva/index.mdx`). Workflow: prototype a Python function → wrap with a UDF decorator → register as a virtual column via `Table.add_columns()` → configure an execution context → trigger `backfill`. Geneva infers Arrow input/output types from Python type hints. Connect: `geneva.connect(uri)` (local, `gs://`, `s3://`) → a `Connection` managing tables, views, jobs, clusters, manifests. This is how you add embeddings/derived features to a Lance table at scale without an external ETL system — it exploits the format's zero-copy column evolution (`lance-format-catalog.md`).

## The three transform types (`geneva/udfs/index.mdx`)

| | UDF | Scalar UDTF | Batch UDTF |
|---|---|---|---|
| Cardinality | 1:1 | 1:N | N:M |
| Decorator | `@udf` | `@scalar_udtf` | `@udtf` |
| Refresh | Incremental | Incremental | Full |
| Parallelism | Fragment-parallel | Fragment-parallel | Partition-parallel |
| Register | `table.add_columns()` | `db.create_scalar_udtf_view()` | `db.create_udtf_view()` |

Scalar/Batch UDTFs are **Beta (Geneva 0.11.0+)**.

## Scalar UDFs (1:1) (`geneva/udfs/udfs.mdx`)

```python
from geneva import udf
@udf
def area_udf(x: int, y: int) -> int:      # args bind to columns x, y by name
    return x * y
```
**Batched** (faster) needs explicit `data_type` and takes `pa.Array` (one column) or `pa.RecordBatch` (all):
```python
@udf(data_type=pa.int32())
def batch_len(filename: pa.Array) -> pa.Array: ...
```
**Struct/list inputs:** `@udf(data_type=…, input_columns=["info.vals"])` (dot notation; list columns arrive as `np.ndarray`). **Stateful UDFs** — a `Callable` class with `__init__` (e.g. load a model to GPU once) and `__call__`; state managed per worker:
```python
@udf(data_type=pa.list_(pa.float32(), 1536))
class OpenAIEmbedding(Callable):
    def __init__(self, model="text-embedding-3-small"):
        self.model, self.client = model, None
    def __call__(self, text: str) -> pa.Array:
        if self.client is None: self.client = OpenAI()
        return pa.array(self.client.embeddings.create(model=self.model, input=text).data[0].embedding)
tbl.add_columns({"embedding": OpenAIEmbedding()})
```
Options on `@udf`: `num_cpus`, `num_gpus` (fractional for GPU co-location), `memory`, `checkpoint_size`/`min_checkpoint_size`/`max_checkpoint_size`, `task_size`, `on_error`. Swap the UDF with `table.alter_columns({"path":"area","udf":area_v2})`; fix subsets with `table.backfill("area", where="area is null")`.

## Scalar UDTFs (1:N) (`geneva/udfs/scalar-udtfs.mdx`)

`@scalar_udtf` on a function that **yields** rows (or returns a list); schema inferred from the return annotation, or `batch=True` + `output_schema` for vectorized `RecordBatch` expansion. Registered via `db.create_scalar_udtf_view(...)`; the `query`'s `.select()` controls which parent columns are **inherited** into child rows (no join). Can yield **zero rows**. MV-style **incremental refresh** — new source rows expand, deleted parents cascade-delete children, updates re-run. Use for **document chunking, video segmentation, image tiling**.

## Batch UDTFs (N:M) (`geneva/udfs/batch-udtfs.mdx`)

`@udtf` on a class/function receiving a `geneva.GenevaQueryBuilder`, yielding `pa.RecordBatch`/`Table` with arbitrary schema/row count. **Always full refresh.** Params: `output_schema` (**required**), `input_columns`, `partition_by`, `partition_by_indexed_column` (reads partition assignment from an existing IVF index — auto-synced; mutually exclusive with `partition_by`), `num_cpus`/`num_gpus`/`memory`, `on_error`. Registered via `conn.create_udtf_view(name, source=…, udtf=…)`, populated with `.refresh()`. **Version-aware:** O(1) skip if the source version is unchanged. Error handling is **partition-granular** (Fail/Retry/Skip). Use for **dedup, clustering, aggregation, cross-row joins/edge detection**.

## Error handling (`geneva/udfs/error_handling.mdx`)

`on_error=` factory functions: `retry_transient()` (ConnectionError/TimeoutError/OSError), `retry_all()`, `skip_on_error()` (→ `None`), `fail_fast()` (default). Params: `max_attempts` (3), `backoff` (`exponential` default 1/2/4/8s jitter cap 60s / `fixed` / `linear`). **Matchers** `Retry/Skip/Fail(...)` evaluated in order, first match wins, `match=` regex on the message (e.g. `Retry(ValueError, match=r"429|rate.?limit", max_attempts=10)`). Full Tenacity via `error_handling=ErrorHandlingConfig(retry_config=UDFRetryConfig(...))`. Skip works for scalar UDFs, not RecordBatch batch UDFs.

## Blobs (`geneva/udfs/blobs.mdx`)

Read: a scalar UDF arg typed `lance.blob.BlobFile` → `blob.read()`. Write: return `bytes`, `data_type=pa.large_binary()`, `field_metadata={"lance-encoding:blob":"true"}` (`lance-format-catalog.md`).

## Built-in provider UDFs (`geneva/udfs/providers/*`)

Factory functions in `geneva.udfs` with automatic API-key capture (serialized with the UDF — no cluster env config), retry/backoff, batching, optional L2 `normalize`:

| Provider | Embedding UDF | Generation UDF | Extra |
|---|---|---|---|
| OpenAI | `openai_embedding_udf(column, model="text-embedding-3-small", output_dimensionality=256)` | `openai_udf(column, prompt, model="gpt-5-mini", mime_type="image/jpeg")` | `geneva[udf-text-openai]` |
| Gemini | `gemini_embedding_udf(column, model="gemini-embedding-001", task_type="RETRIEVAL_DOCUMENT")` | `gemini_udf(column, prompt, model="gemini-2.5-flash", mime_type=…)` | `geneva[udf-text-gemini]` |
| Sentence Transformers | `sentence_transformer_udf(column, model="…all-MiniLM-L6-v2", num_gpus=1.0)` | — (local) | `geneva[udf-text-sentence-transformers]` |

Because `add_columns` takes a dict, you can compute multiple models/prompts side-by-side in one backfill for comparison.

## Jobs

**Execution contexts** (v0.10.0+, Ray backend) (`geneva/jobs/contexts.mdx`): (1) **Local Ray** `Connection.local_ray_context()`; (2) **KubeRay** `GenevaCluster.create_kuberay(name).namespace(…).config_method(K8sConfigMethod.EKS_AUTH).head_group(…).add_worker_group(KubeRayClusterBuilder.gpu_worker()…).build()` then `db.define_cluster(name, cluster)`; (3) **External Ray** `create_external(name, "ray://ip:port")`. Enter with `with db.context(cluster=…, manifest=…, on_exit=ExitMode.DELETE|RETAIN):`. **Manifests** package dependencies: `GenevaManifest.create_pip(name).pip([…])` / `.create_conda(...)` / `.worker_image(...)`.

**Backfilling** (`geneva/jobs/backfilling.mdx`): `tbl.backfill(col)` — distributed, checkpointed. Concurrency = `concurrency` (process-level, default 8 = #GPUs) × `intra_applier_concurrency` (thread-level, default 1). `num_frags`/`commit_granularity` control visibility. Filtered: `tbl.backfill("content", where="content is null")` (default skips already-valued rows). Async: `backfill_async()`, `plan_backfill()`.

**Materialized views** (`geneva/jobs/materialized-views.mdx`): `db.create_materialized_view(name, table.search(None).shuffle(seed=42).select({…udfs…}))`; populate/update with `db.refresh(name)` (incremental — new/modified fragments only). MVs are tables → support `add_columns`/`backfill`/chaining.

**Lifecycle** (`geneva/jobs/lifecycle.mdx`): PENDING→RUNNING→DONE/FAILED. Job types: Backfill, MV Refresh. Query via `db._history` (`.get(job_id)`, `.list_jobs(...)`). Checkpoint recovery: re-run the same command → skips processed fragments (exactly-once). **Conflicts** (`geneva/jobs/conflicts.mdx`): backfills run on a point-in-time snapshot; safe concurrently — insert-only `merge_insert`, `add`, reads, add-column; conflicting — `compact_files`/`optimize`, updating `merge_insert`, `delete`. Best-practice order: **ingest → backfill → compact**.

**Performance/metrics** (`geneva/jobs/{performance,job_metrics}.mdx`): KubeRay defaults — Head 4CPU/8GiB, CPU worker 4CPU/8GiB (0–100 replicas, idle 60s), GPU worker 8CPU/16GiB/1GPU. `total_cpus ≈ concurrency × intra_applier_concurrency × udf.num_cpus`. Node selectors `geneva.lancedb.com/ray-{head,worker-cpu,worker-gpu}`. Write bottleneck: too few fragments → single serial writer (make fragments > nodes). Diagnostic metrics: `rows_checkpointed`, `rows_committed`, `writer_queue_wait_time_ms`, `commit_conflict_retries` — high checkpointed + low committed ⇒ writer/object-store pressure. **Console** UI via the Geneva Helm chart (`kubectl port-forward svc/geneva-console-ui 3000:3000`).

**Deployment** (`geneva/deployment/*`): Kubernetes + KubeRay 1.1+ + Ray 2.43+; first-class AWS(EKS)/GCP(GKE)/Azure via Terraform+Helm with Workload Identity/IRSA. `compare_ray_environments` diagnoses local↔worker dependency mismatches (numpy/torch/pyarrow/attrs/pydantic). Advanced env vars (`geneva/udfs/advanced-configuration.mdx`): `GENEVA_COMMIT_MAX_RETRIES` (12), `GENEVA_VERSION_CONFLICT_MAX_RETRIES` (10), `JOB__CHECKPOINT__OBJECT_STORE__PATH` (separate checkpoint bucket to decouple IOPS). SDK reference: `lancedb.github.io/geneva/`.

## Design rules
- **Features are columns, computed by UDFs, added zero-copy** — `add_columns` + `backfill`; don't rebuild the table.
- **Pick the transform by cardinality** — `@udf` 1:1, `@scalar_udtf` 1:N (chunking/segmentation), `@udtf` N:M full-refresh (dedup/cluster).
- **Stateful UDF for expensive per-worker init** — load the model once in `__init__`; request `num_gpus`/`memory` explicitly.
- **Order: ingest → backfill → compact** — compaction conflicts with in-flight backfills; sequence them.
- **It's Enterprise + Ray** — name the tier; size KubeRay workers to the UDF's resource requests; keep fragments > nodes to avoid a serial-writer bottleneck.
