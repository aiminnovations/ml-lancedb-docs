# Quorum Protocol — always-deploy-5 (+ the mandatory verification seat)

> The fan-out every LanceDB design/build/migration/optimization runs. Owned by
> `lancedb-senior-expert`. No single-agent builds. A data-layer decision is high-leverage — a wrong
> index type, a broken schema, or a lost-recall quantization choice is expensive to unwind once data
> is written — so the **verification seat is mandatory**.

## The five seats (always deployed)

| Seat | Role | Agent | Owns |
|---|---|---|---|
| 1 | Subdomain expert | the catalog↔expert match (`lancedb-schema-table-expert` / `-indexing-expert` / `-search-expert` / `-storage-deployment-expert` / `-integrations-expert` / `-use-case-architect`) | The grounded, catalog-cited spec for the stage in scope. Runs first. |
| 2 | Pipeline-developer | `lancedb-pipeline-developer` | Builds the LanceDB code strictly against the spec (correct SDK, correct API); may NOT use an un-cited API, a competing store, or a from-memory param. |
| 3 | Reviewer | `lancedb-code-reviewer` | Independent, fresh-context audit: LanceDB-native compliance, correctness against the catalogs, schema/index correctness, data-loss & migration safety. BLOCKS on violations. |
| 4 | **Verification (mandatory)** | `lancedb-performance-adversary` | The correctness + performance gate. A build that hasn't shown the index builds, the query returns correct rows, and recall/latency/cost are acceptable (or a documented plan to measure them) is NOT shippable. |
| 5 | Dev-doc / QC | `lancedb-dev-doc-worker` | Quality control + enforced handoff + memory write (incl. the verification verdict). |

**6th seat (conditional):** `lancedb-performance-adversary` also runs a deeper **pre-mortem** for
high-stakes work — a production migration, a schema/format change over existing data, a large-corpus
index choice, or an Enterprise deployment — hunting data loss, recall collapse, cost blowups, and lock-in.

## Sequence
1. `lancedb-senior-expert` identifies the stage(s) + selects the quorum.
2. Subdomain expert → grounded, catalog-cited spec (which table shape, which index + params, which search, which store).
3. `lancedb-pipeline-developer` writes the code (correct SDK + API); the native-guard hook blocks a competing store live.
4. `lancedb-code-reviewer` + `lancedb-performance-adversary` review in parallel, fresh context. **The adversary checks correctness + recall/latency/cost.**
5. Loop on blockers; re-review fresh. Never ship a schema/index over real data that fails correctness or loses recall silently.
6. `lancedb-dev-doc-worker` closes with a handoff + memory write (with the verification verdict).

## Invariants
- **LanceDB-native, catalog-grounded:** every API/index/param cites a `references/*-catalog.md`; a competing store is a BLOCKER.
- **Version + tier + SDK named:** OSS vs Cloud vs Enterprise, and Python/TS/Rust, stated for every recommendation.
- **Verified:** no ship without the index building, the query returning correct rows, and a recall/latency/cost read (or a plan to get one).
- **Data-safe:** schema evolution, `merge_insert`, migration, and quantization choices are proven non-destructive before they touch real data.
- **Closed with a handoff + verification verdict.**
