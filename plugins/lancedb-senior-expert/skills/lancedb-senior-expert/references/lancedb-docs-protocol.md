# LanceDB Docs Protocol — the grounding + version-verify ladder

> Never specify a LanceDB API, index type, param, or config from training-time memory. LanceDB
> spans three SDKs (Python, TypeScript/Node, Rust) and three deployment tiers (OSS embedded,
> Cloud, Enterprise) and the API moves fast — ground it and version-verify. Owned by every agent;
> freshness owned by `lancedb-docs-curator`.

## Source ladder (climb in order)
1. **The catalog** (`references/*-catalog.md`) — primary; absorb-everything, cited to a docs path.
2. **The LanceDB docs** (this repo, `/docs/*.mdx`) — the authoritative content the catalogs are
   absorbed from: `lance.mdx`, `tables/*`, `indexing/*`, `search/*`, `reranking/*`, `embedding/*`,
   `storage/*`, `namespaces/*`, `enterprise/*`, `geneva/*`, `training/*`, `integrations/*`,
   `tutorials/*`, `api-reference/*`. The MDX pulls its code from tested snippets in `/tests/`.
3. **The SDK source** — when binding an exact signature or a default not in the docs: the Python
   package (`python/`), the Node package (`nodejs/`), the Rust crates (`rust/`) in the `ml-lancedb`
   repo. Context7 (`lancedb` / `lance`) for current published API docs.
4. **Tavily / web** — for the CURRENT release notes, deprecations, and benchmark numbers when a
   ⚠️ fast-moving pick (a new index type, a new embedding provider, a Cloud/Enterprise feature) is in play.

When rungs 3–4 surface a newer API or default, `lancedb-docs-curator` folds it back into the catalog
and bumps the `last-verified-against` stamp.

## Version-verify discipline (the ⚠️ items)
LanceDB has real cross-tier and cross-SDK skew. Re-verify these at build time, not from memory:
- **Tier skew** — a method may exist in OSS but differ on Cloud/Enterprise (e.g. index build is
  server-side on Cloud; `create_index` params, GPU build, and some SQL features are tier-specific). Name the tier.
- **SDK skew** — Python is the reference SDK; TypeScript and Rust lag or differ in surface (async-only
  in places, different reranker/embedding coverage). Cite the SDK you targeted.
- **Sync vs async** — Python has both `connect` and `connect_async` with different method shapes;
  say which.
- **Index defaults** — `num_partitions`, `num_sub_vectors`, `nprobes`, `refine_factor`, metric, and
  the default index type are dataset-dependent and version-dependent. Cite the docs value, don't assert.
- **Embedding/reranker registry names** — the exact registry string and constructor params per provider.

Cite the docs path (+ date for a web-verified number) when you pick.

## Discipline
- Cite the catalog (or the docs rung) for every API/index/param/config named in a plan or build.
- Prefer the LanceDB-native path (the format's own capability) over an external bolt-on; a competing
  vector store is a BLOCKER (the native-guard hook + `lancedb-code-reviewer` enforce it) — escalate.
- Match the docs' **snippet discipline**: code that matters is tested per SDK in `/tests/` and pulled
  into MDX via `make snippets`; recommend the same for anything shipped.
- Prefer stable/GA APIs; flag experimental/preview features and Cloud/Enterprise-only capabilities explicitly.
