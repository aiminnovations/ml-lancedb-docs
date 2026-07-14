---
name: lancedb-implement
description: Build a LanceDB implementation with the full quorum — subdomain expert spec → pipeline-developer build → code-reviewer + performance-adversary verification → dev-doc handoff. Never a single-agent build over real data.
argument-hint: <what to build>
---

# /lancedb-implement

Build the LanceDB implementation for **$ARGUMENTS** with the always-deploy quorum.

1. **Load the skill.** `lancedb-senior-expert` — SKILL.md + `references/quorum-protocol.md` + `references/planning-checklist.md` + `references/lancedb-docs-protocol.md`.
2. **Dispatch the coordinator** (`lancedb-senior-expert`) to run the quorum:
   - **Seat 1** — the matching subdomain expert produces the grounded, catalog-cited spec (schema / index / search / storage), pinning dim + metric + index type.
   - **Seat 2** — `lancedb-pipeline-developer` writes the code in the correct SDK, strictly to spec; the native-guard hook blocks a competing store live.
   - **Seats 3+4** — `lancedb-code-reviewer` (native/correctness/data-safety/secrets) + the MANDATORY `lancedb-performance-adversary` (index builds, query correct, recall vs brute force, latency/cost) in parallel, fresh context.
   - **Loop** on blockers; re-review fresh. Add the deeper adversary pre-mortem for a migration / schema-over-data / large-corpus / Enterprise build.
   - **Seat 5** — `lancedb-dev-doc-worker` closes with a handoff + memory write carrying the verification verdict + the pinned invariants.
3. **Report** the built code, the verification verdict, and the handoff.

**Output:** working LanceDB code (correct SDK) + the verification verdict (index built, query correct, recall/latency/cost) + the handoff. Next: `/lancedb-status` then `/lancedb-optimize`.
