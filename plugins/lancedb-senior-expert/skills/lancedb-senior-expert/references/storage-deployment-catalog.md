# Storage + Deployment Catalog — object stores, storage_options, namespaces, Cloud/Enterprise

> last-verified-against: docs `storage/{index,configuration}.mdx`, `namespaces/{index,usage}.mdx`, `enterprise/{index,architecture,security,performance,quickstart,deployment/*}.mdx` + SDK `lancedb==0.30.0`, 2026-07-14
> Sources: `docs/storage/*`, `docs/namespaces/*`, `docs/enterprise/*`; SDK `__init__.py` connect signatures.
> Owner expert: `lancedb-storage-deployment-expert`. ⚠️ = version/tier/SDK-verify at build.

## Backends + connect

The URI scheme selects the backend (`storage/configuration.mdx`): `s3://` (AWS S3 + compatible: MinIO, Tigris, S3 Express, WekaFS), `gs://` (GCS), `az://` (Azure Blob), a local path, or `db://` (Cloud/Enterprise).
```python
lancedb.connect("s3://bucket/path")
lancedb.connect("gs://bucket/path")
lancedb.connect("az://bucket/path")
lancedb.connect("s3://bucket/path", storage_options={"region":"us-east-1","endpoint":"http://minio:9000"})
lancedb.connect("s3://bucket/path", storage_options={"endpoint":"https://t3.storage.dev","region":"auto"})  # Tigris
```

## storage_options

Keys are **case-insensitive** (lowercase in `storage_options`, uppercase as env vars); settable at **connection level or per-table** (`storage/configuration.mdx`):
- General: `allow_http`, `allow_invalid_certificates`, `connect_timeout`, `timeout`, `user_agent`, `proxy_url`, `download_retry_count`, `client_max_retries`, `client_retry_timeout`.
- Cloud-specific: `region`, `endpoint`, `service_account`, Azure credential keys.
- New-table format keys: `new_table_data_storage_version` (default `stable`), `new_table_enable_v2_manifest_paths` (default false), `new_table_enable_stable_row_ids` (default false) — see `lance-format-catalog.md`.

**AWS S3:** env `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` (+ optional `AWS_SESSION_TOKEN`); region optional for AWS, required for most S3-compatible; min IAM: `s3:{PutObject,GetObject,DeleteObject,ListBucket,GetBucketLocation}`; `http://` endpoints need `allow_http=True`. **Concurrent writers on S3** (no atomic put) need the **DynamoDB commit store**: `s3+ddb://bucket/path?ddbTableName=my-table` (table: hash key `base_uri` string, range key `version` number). S3 Express One Zone supported. **GCS:** `GOOGLE_SERVICE_ACCOUNT` (JSON path); set `HTTP1_ONLY=false` for HTTP/2. **Azure:** `AZURE_STORAGE_ACCOUNT_NAME`+`AZURE_STORAGE_ACCOUNT_KEY`, or service principal / SAS / managed identity.

**Dynamic credentials** (Python): pass a `storage_options_provider` implementing `fetch_storage_options()` to `create_table`/`open_table`; if it returns `expires_at_millis`, LanceDB refreshes before expiry (`refresh_offset_millis` to refresh earlier).

## Separation of storage & compute (`storage/index.mdx`)

LanceDB is disk-first and writes **immutable fragments**, so storage and compute are separable — good for stateless, horizontally-scalable deployments. Backend latency vs cost (lowest cost → lowest latency): **Object storage** (100s ms p95, cheapest, unlimited) → **File storage** EFS/Filestore (<100 ms, IOPS-bound) → third-party MinIO/WekaFS (<100 ms) → **Block** EBS/PD (<30 ms, not shareable) → **Local SSD/NVMe** (<10 ms p95, hardest to scale, priciest). Pick the tier by the latency the workload actually needs; object storage is the default and cheapest for most stores.

## Namespaces (`tables-and-namespaces.mdx`, `namespaces/*`)

LanceDB is a **Multimodal Lakehouse**: a **table** = data (schema/rows/indexes/versions); a **namespace** = a catalog object (a hierarchy of names + table grouping + name resolution). That's why `create_table`/`open_table`/`drop_table`/`rename_table` accept a namespace path. Namespaces are recursive (contain tables and sub-namespaces); the empty path `[]` is the root. The **namespace client** presents a consistent API; the **implementation** resolves names to table locations.

Backends: **directory** (`"dir"`) — one root dir, the OSS default; **REST** (`"rest"`) — remote object stores + a central catalog (Enterprise runs a REST namespace server); external catalogs (Glue/Hive/Unity) are referenced conceptually ⚠️ (usage examples not in these docs — verify at build).
```python
db = lancedb.connect_namespace("dir", {"root": "./local_lancedb"})
db.create_namespace(["prod"], mode="exist_ok")
db.create_namespace(["prod","search"], mode="exist_ok")
db.create_table("user", data=[…], namespace=["prod","search"], mode="create")
db.list_namespaces()                       # ['prod']
db.list_tables(namespace=["prod","search"])
# REST (Enterprise catalog), forwarding an auth header:
ns = lancedb.connect_namespace("rest", {"uri":"https://catalog", "headers.Authorization": f"Bearer {tok}"})
ns.open_table("adventurers", namespace=["prod","search"])
```
Lifecycle (Python): `create_namespace`, `list_namespaces`, `describe_namespace`, `drop_namespace(path, mode="skip")`. Rust mirrors it via request structs + `.namespace(vec![…])` on builders. ⚠️ **TypeScript** does not expose namespace lifecycle on `Connection` (root namespace only; manage via REST/admin). ⚠️ The real Python `create_table` kwarg is `namespace_path=` while several snippets show `namespace=` — verify against your SDK. **Best practice:** the directory root suffices for standalone OSS apps; use explicit namespaces for shared remote catalogs across teams/environments; treat namespace paths (`"prod/search"`) as stable IDs; don't hard-code object-store paths.

## OSS vs Cloud vs Enterprise (`enterprise/index.mdx`)

Same Lance format across all three — migration is a **connection-string change**, no data conversion.
- **OSS** — embedded, single-process; object-store latency 500–1000 ms; ~10–50 QPS; no cache; manual indexing/compaction.
- **Cloud** — serverless; managed indexing/compaction/cleanup; `db://` connection with `api_key`.
- **Enterprise** — distributed fleet; 50–200 ms latency; up to 10,000 QPS; distributed NVMe cache; automatic indexing/compaction.

## Enterprise architecture, security, performance (`enterprise/*`)

**Architecture** (`architecture.mdx`): layers = remote tables → **data plane** (query nodes + plan executors + indexers) → **control plane** (config/identity/policy/lifecycle) → object storage. Compute/storage decoupled. Read path: query node validates/plans → plan executors read object storage via cache → assemble. Write path: query node commits new table state to object storage (durability first) → async signals drive background indexing/compaction/cleanup off the request path. `open_table` returns `RemoteTable`.

**Security** (`security.mdx`): SOC 2 Type II, HIPAA, GDPR; encryption at rest (object store + cache); customer data stays in the customer account (LanceDB receives only health telemetry); trust.lancedb.com.

**Performance** (`performance.mdx`, warmed cache, directional): Vector Search P50 25 ms / P99 35 ms; Vector+Filter P50 30 / P99 50 (selective) up to P99 100 (broad); FTS P50 26 / P99 42 (dbpedia-openai-1M, synthetic 15M×256).

**Deployment models** (`deployment/index.mdx`, `deployment/azure.mdx`): **Managed** (LanceDB-managed cloud accounts, public/private LB) and **BYOC** (installed into the customer VPC; data never leaves the account; provisioned identity manages infra). Azure adds **Hybrid — Bring Your Own Container** (infra in LanceDB's account, storage in the customer's). Azure stack: AKS + Azure Blob + Private Link + Workload Identity (RBAC) + EventHub/Kafka; components Query Nodes (Phalanx), Plan Executors, Lance Agent, on-demand Indexer Pods. Multi-account/multi-container storage supported; all models run on AWS/GCP/Azure.

## Design rules
- **Name the tier + backend explicitly** — OSS/Cloud/Enterprise and local/S3/GCS/Azure change the API surface, latency, and ops model.
- **Secrets via env or `storage_options`, never in code** — min-privilege IAM; `allow_http` only for internal endpoints.
- **Concurrent S3 writers → DynamoDB commit store** (`s3+ddb://`) — S3 has no atomic put; a single writer can skip it.
- **Choose the storage tier by required latency** — object storage default/cheapest; block/local only when <30/<10 ms is required and you accept the scaling cost.
- **Use namespaces for shared catalogs** — stable path IDs; directory backend for standalone OSS; REST for Enterprise/team catalogs; note the TS/Glue/Hive/Unity gaps.
- **OSS→Cloud→Enterprise is a connection string** — design portable; don't couple to a tier-only feature without flagging it.
