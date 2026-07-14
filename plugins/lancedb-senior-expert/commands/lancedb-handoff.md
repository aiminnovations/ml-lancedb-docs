---
name: lancedb-handoff
description: Close a LanceDB run — write the handoff (handoff-template.md) + the memory write (memory-write-protocol.md), both carrying the verification verdict and the pinned invariants (dim, metric, index type + params, storage backend, tier). A run is incomplete without this.
argument-hint: <optional: run/task id>
---

# /lancedb-handoff

Close the LanceDB run for **$ARGUMENTS**.

1. **Load the skill.** `lancedb-senior-expert` — SKILL.md + `references/quorum-protocol.md` + `references/handoff-template.md` + `references/memory-write-protocol.md`.
2. **Dispatch `lancedb-dev-doc-worker`** to close the run:
   - **Confirm seat 4 passed** — the `lancedb-performance-adversary` verdict (index built, query correct, recall/latency/cost). If it didn't pass, the run is NOT closeable — loop back, don't write a "done" handoff.
   - **Confirm native + cited** — LanceDB store, correct SDK, every shipped API cites a catalog; a competing store BLOCKS the close.
   - **Write the handoff** per `handoff-template.md` — build summary, cited APIs, schema + storage, index strategy, search design, verification verdict, the pinned invariants, deviations + escalations, next step.
   - **Write the memory** per `memory-write-protocol.md` — with the verdict, the pinned invariants (dim/metric/index/backend/tier), the citations, and the Linear issue ID in `tags`.
3. **Report** closure (or the blocker preventing it).

**Output:** the handoff document + the memory write (verdict + pinned invariants + citations) + a closure report.
