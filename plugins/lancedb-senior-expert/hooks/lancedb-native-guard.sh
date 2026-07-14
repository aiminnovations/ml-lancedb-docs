#!/bin/bash
# lancedb-senior-expert PreToolUse guard (Write|Edit|MultiEdit).
# Enforces the LanceDB-native substrate: LanceDB / the Lance format is the store-and-retrieval layer.
# BLOCKS adding a COMPETING vector database (Pinecone / Weaviate / Qdrant / Chroma / Milvus) as the
# primary store inside a LanceDB codebase without escalation — LanceDB already owns embedded + Cloud +
# Enterprise, multimodal blobs, versioning/time-travel, and hybrid search, so a second store is a
# design regression, not a feature. Docs (.md/.mdx) and test files are exempt. Content-only grep
# (CRLF-harmless). Also emits NON-BLOCKING advisories for two high-frequency LanceDB footguns
# (asymmetric embedding input_type; brute-force search with no ANN index) — advisory, never blocked.

input=$(cat)
file=$(echo "$input" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
content=$(echo "$input" | jq -r '[.tool_input.content, .tool_input.new_string, (.tool_input.edits[]?.new_string)] | map(select(. != null)) | join("\n")' 2>/dev/null)

case "$file" in
  *.py|*.js|*.ts|*.mjs|*.cjs|*.jsx|*.tsx|*.rs) ;;
  *) exit 0 ;;
esac
# Never fire on the plugin's own docs/tests or on documentation.
case "$file" in
  *.md|*.mdx|*test*|*spec*|*/tests/*|*/test/*) exit 0 ;;
esac
[ -z "$content" ] && exit 0

# BLOCK: a competing vector DB introduced as a store in a LanceDB codebase.
if echo "$content" | grep -qiE '^[[:space:]]*(import|from)[[:space:]]+(pinecone|weaviate|qdrant_client|chromadb|pymilvus)([[:space:].]|$)|(require\(|from[[:space:]]+)["'\''"]@?(pinecone|pinecone-database|weaviate-(client|ts-client)|@qdrant/js-client-rest|chromadb|@zilliz/milvus2-sdk-node)'; then
  echo '{"decision": "block", "reason": "Vector-store violation: this adds a competing vector database (Pinecone / Weaviate / Qdrant / Chroma / Milvus) to a LanceDB codebase. LanceDB is the approved store-and-retrieval layer — it already provides embedded + serverless (Cloud) + Enterprise deployment, multimodal blob storage, zero-copy versioning/time-travel, IVF/HNSW + scalar + FTS indexing, and native hybrid search over the Lance columnar format. Introducing a second store fragments the data layer and forfeits those guarantees. If a second store is genuinely required, escalate to lancedb-senior-expert with a 3-options Q&A and Sean'\''s approval. See references/storage-deployment-catalog.md and references/lancedb-docs-protocol.md."}'
  exit 2
fi

# NON-BLOCKING advisory: asymmetric embedding discipline (query embedded as a document).
if echo "$content" | grep -qiE 'input_type[[:space:]]*=[[:space:]]*["'\'']document["'\'']' && echo "$content" | grep -qiE '\b(query|search|question)\b'; then
  echo '{"systemMessage": "lancedb-senior-expert advisory: verify input_type symmetry — embed stored rows with input_type=\"document\" and the QUERY with input_type=\"query\". Mixing them silently degrades recall. If you use the LanceDB embedding registry (get_registry), auto-embedding handles this for you. See references/embedding-reranking-catalog.md."}'
  exit 0
fi

# NON-BLOCKING advisory: a vector search with no evidence of an ANN index in the change.
if echo "$content" | grep -qiE '\.search\(' && ! echo "$content" | grep -qiE 'create_index|create_scalar_index|create_fts_index|nprobes|refine_factor'; then
  echo '{"systemMessage": "lancedb-senior-expert advisory: a .search() with no create_index nearby runs a brute-force (flat) scan — fine for <~100K rows or a demo, but at scale build an IVF_PQ / IVF_HNSW_SQ index and tune nprobes/refine_factor. See references/indexing-catalog.md and references/search-query-catalog.md."}'
  exit 0
fi

exit 0
