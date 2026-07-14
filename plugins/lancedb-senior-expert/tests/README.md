# tests — catalog smoke verification

`verify_catalogs.py` exercises the core paths the catalogs document against a **real LanceDB**,
offline (manual vectors, no API keys), so catalog drift becomes a concrete PASS/FAIL. It embodies
the plugin's own rule: *verify before you trust — don't assert an API from memory.*

## Run
```bash
python -m venv .venv && . .venv/bin/activate
pip install "lancedb" numpy pandas
python plugins/lancedb-senior-expert/tests/verify_catalogs.py
```
Exit `0` = every catalog claim held; exit `1` = at least one drifted (hand it to `lancedb-docs-curator`
to re-verify against the live docs/SDK and fold back in-place, then bump the `last-verified-against` stamp).

## What it covers (13 checks)
tables/schema (`create_table(LanceModel)`, idempotent `merge_insert`) · indexing (unified
`create_index(config=IvfPq/BTree/FTS)`) · search (vector, `bypass_vector_index` brute-force +
`refine_factor` recall, SQL `where` prefilter, native FTS `_score`, hybrid + `RRFReranker`) ·
lance-format (versioning/`checkout`/tags, zero-copy `add_columns`/`alter_columns`/`drop_columns`,
`optimize`) · `explain_plan`.

## Last live run
`lancedb==0.34.0`, 2026-07-14 — **13/13 PASS, recall@10 = 1.0**. That run surfaced the real drift now
folded into `indexing-catalog.md` + `scaffold-templates.md`: the unified `create_index(column, config=…)`
API is current (the imperative `create_index(metric=…)`/`create_scalar_index`/`create_fts_index` forms
are deprecated since 0.25.0). Uses the config-object API, so it runs warning-free.
