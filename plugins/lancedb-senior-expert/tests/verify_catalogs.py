"""verify_catalogs.py — re-runnable smoke check for the lancedb-senior-expert catalogs.

Exercises the core paths the catalogs document against a REAL LanceDB, offline (manual
vectors, no API keys), so catalog drift becomes a concrete PASS/FAIL — the same
verify-before-you-trust discipline the plugin enforces on every build.

Uses the unified config-object index API (`create_index(column, config=...)`), current since
LanceDB 0.25.0. Last live-run: lancedb==0.34.0, 2026-07-14 — 13/13 PASS, recall@10=1.0.

Run:
    python -m venv .venv && . .venv/bin/activate
    pip install "lancedb" numpy pandas
    python plugins/lancedb-senior-expert/tests/verify_catalogs.py
Exit code 0 = all pass; 1 = at least one drift (a catalog claim no longer holds → curator folds it in).
"""
import shutil
import sys
import tempfile

import numpy as np
import lancedb
from lancedb.pydantic import LanceModel, Vector
from lancedb.index import IvfPq, BTree, FTS
from lancedb.rerankers import RRFReranker

DIM = 64
N = 4000
rng = np.random.default_rng(0)

results = []


def check(name, fn):
    try:
        fn()
        results.append(("PASS", name, ""))
        print(f"PASS  {name}")
    except Exception as e:  # noqa: BLE001 - a drift is any failure; report it
        results.append(("FAIL", name, repr(e)))
        print(f"FAIL  {name}: {e!r}")


def rows(n, start=0):
    return [
        {
            "id": f"d{i}",
            "text": f"row number {i} about topic {i % 7}",
            "vector": rng.standard_normal(DIM).astype(np.float32).tolist(),
        }
        for i in range(start, start + n)
    ]


class Doc(LanceModel):
    id: str
    text: str
    vector: Vector(DIM)


def main() -> int:
    db_dir = tempfile.mkdtemp(prefix="lancedb_verify_")
    db = lancedb.connect(db_dir)
    tbl = {}

    def make_table():
        tbl["t"] = db.create_table("docs", schema=Doc, mode="overwrite")
        tbl["t"].add(rows(N))
        assert tbl["t"].count_rows() == N
    check("tables-schema: create_table(schema=LanceModel) + add + count_rows", make_table)

    def merge_insert_upsert():
        t = tbl["t"]
        before = t.count_rows()
        data = rows(10, start=0) + rows(5, start=N)  # 10 existing (update) + 5 new (insert)
        t.merge_insert("id").when_matched_update_all().when_not_matched_insert_all().execute(data)
        assert t.count_rows() == before + 5
        t.merge_insert("id").when_matched_update_all().when_not_matched_insert_all().execute(data)
        assert t.count_rows() == before + 5, "merge_insert not idempotent"
    check("tables-schema: merge_insert upsert is idempotent", merge_insert_upsert)

    def scalar_index():
        tbl["t"].create_index("id", config=BTree())  # unified config-object API
    check("indexing: create_index('id', config=BTree())", scalar_index)

    def vector_index():
        tbl["t"].create_index(
            "vector", config=IvfPq(distance_type="l2", num_partitions=16, num_sub_vectors=16)
        )
        tbl["t"].wait_for_index(["vector_idx"])
    check("indexing: create_index('vector', config=IvfPq(...)) + wait_for_index", vector_index)

    def vector_search():
        q = rng.standard_normal(DIM).astype(np.float32)
        res = tbl["t"].search(q).limit(10).to_list()
        assert len(res) == 10 and "_distance" in res[0]
    check("search: vector search returns _distance", vector_search)

    def recall_vs_bruteforce():
        t = tbl["t"]
        qs = [rng.standard_normal(DIM).astype(np.float32) for _ in range(20)]
        hits = 0.0
        for q in qs:
            exact = {r["id"] for r in t.search(q).bypass_vector_index().limit(10).to_list()}
            approx = {r["id"] for r in t.search(q).refine_factor(10).limit(10).to_list()}
            hits += len(exact & approx) / 10.0
        recall = hits / len(qs)
        print(f"      recall@10 (IVF_PQ+refine vs brute force) = {recall:.3f}")
        assert recall > 0.5, f"recall too low: {recall}"
    check("search: bypass_vector_index brute force + refine_factor recall path", recall_vs_bruteforce)

    def prefilter():
        q = rng.standard_normal(DIM).astype(np.float32)
        res = tbl["t"].search(q).where("id = 'd1'", prefilter=True).limit(5).to_list()
        assert all(r["id"] == "d1" for r in res)
    check("search: SQL where() prefilter over scalar index", prefilter)

    def fts():
        tbl["t"].create_index("text", config=FTS(with_position=True))
        tbl["t"].wait_for_index(["text_idx"])
        res = tbl["t"].search("topic", query_type="fts").limit(5).to_list()
        assert len(res) > 0 and "_score" in res[0]
    check("indexing/search: create_index('text', config=FTS()) + fts query returns _score", fts)

    def hybrid_rrf():
        q = rng.standard_normal(DIM).astype(np.float32)
        res = (
            tbl["t"].search(query_type="hybrid").vector(q).text("topic")
            .rerank(RRFReranker()).limit(5).to_list()
        )
        assert len(res) > 0
    check("search/reranking: hybrid vector+fts fused with RRFReranker", hybrid_rrf)

    def versioning():
        t = tbl["t"]
        v_before = t.version
        assert "version" in t.list_versions()[0]
        t.add(rows(3, start=N + 100))
        assert t.version > v_before
        t.checkout(v_before)
        t.checkout_latest()
        t.tags.create("golden", t.version)
        assert "golden" in t.tags.list()
    check("lance-format: versioning list_versions/version/checkout/checkout_latest/tags", versioning)

    def schema_evolution():
        t = tbl["t"]
        t.add_columns({"text_len": "length(text)"})
        assert "text_len" in t.schema.names
        t.alter_columns({"path": "text_len", "rename": "tlen"})
        assert "tlen" in t.schema.names
        t.drop_columns(["tlen"])
        assert "tlen" not in t.schema.names
    check("lance-format: zero-copy add_columns/alter_columns/drop_columns", schema_evolution)

    def optimize():
        tbl["t"].optimize()  # compaction + cleanup + incremental index
    check("lance-format: optimize()", optimize)

    def explain_plan():
        q = rng.standard_normal(DIM).astype(np.float32)
        plan = tbl["t"].search(q).limit(5).explain_plan(True)
        assert isinstance(plan, str) and plan
    check("search: explain_plan()", explain_plan)

    shutil.rmtree(db_dir, ignore_errors=True)

    passed = sum(1 for r in results if r[0] == "PASS")
    failed = sum(1 for r in results if r[0] == "FAIL")
    print(f"\n=== {passed} PASS / {failed} FAIL  (lancedb {lancedb.__version__}) ===")
    for status, name, err in results:
        if status == "FAIL":
            print(f"  FAIL {name}\n    {err}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
