#!/bin/bash
# lancedb-senior-expert Stop / SubagentStop hook — non-blocking close-out reminder.
# A quorum run is incomplete without a handoff + memory write. This reminds; the
# lancedb-dev-doc-worker enforces. Never blocks.

cat >/dev/null  # drain stdin
echo '{"systemMessage": "lancedb-senior-expert: if this session designed/changed a LanceDB implementation, close it with /lancedb-handoff — write the handoff (handoff-template.md) + the memory write (memory-write-protocol.md): the table/schema shape, the index strategy (type + params) and why, the search/retrieval design, the storage backend + storage_options, the SDK(s) touched (py/ts/rust), and the verification result (index built, query returns, recall/latency acceptable). A run without a handoff + a verification verdict is incomplete (quorum-protocol)."}'
exit 0
