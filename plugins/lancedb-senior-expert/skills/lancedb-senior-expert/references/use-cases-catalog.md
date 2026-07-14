# Use Cases + Advanced Applications Catalog — patterns, recipes, GraphRAG

> last-verified-against: docs `tutorials/*`, `demos/index.mdx` + `ml-lancedb-vectordb-recipes` + `ml-lance-graph`, 2026-07-14
> Sources: `docs/tutorials/*`, `docs/demos/index.mdx`; the vectordb-recipes repo (examples/applications/tutorials); the lance-graph repo (Cypher-on-Lance).
> Owner expert: `lancedb-use-case-architect`. ⚠️ = verify the recipe against the current SDK at build.

## How to use this catalog

Map the user's goal to a proven pattern, then hand the concrete build to the subdomain experts (schema→index→search→embedding). Each entry names the pattern + what it demonstrates; the recipes are worked references, not APIs — re-verify against the current SDK.

## Signature patterns (docs tutorials + demos)

- **Time-Travel RAG** (`tutorials/agents/time-travel-rag/`, recipe `time-travel-rag`) — a versioned knowledge base (U.S. Federal Register): `checkout` historical table versions for audit/reproducibility, instant rollback, and A/B testing embedding models (all-MiniLM-L6-v2 vs all-mpnet-base-v2) **without duplicating data**. Pattern: zero-cost data evolution + version checkout for compliance/reproducibility. Grounds in `lance-format-catalog.md` (versioning/tags).
- **Multimodal Agent** (`tutorials/agents/multimodal-agent/`, recipe `multimodal-recipe-agent`) — a recipe-finder over text+image using LanceDB + PydanticAI + SentenceTransformers + CLIP + Streamlit (image upload). Pattern: multimodal retrieval exposed as agent tools (one Lance table, text + image vectors).
- **Multivector "Needle in a Haystack"** (`tutorials/search/multivector-needle-in-a-haystack.mdx`) — token-level intra-document retrieval on AmazonScience/document-haystack (~1,230 pages/doc). Compares `base` (full late-interaction MaxSim with ColPali/ColQwen2/ColSmol + XTR), `flatten` (mean-pool → ANN), `max_pooling`, and two-stage `flatten + multivector rerank` — schema `pa.list_(pa.list_(pa.float32(), 128))`. Lesson: pooling helps document-level recall but hurts token-level precision. Grounds in `search-query-catalog.md` (multivector).
- **Agents index** (`tutorials/agents/index.mdx`) — Contextual RAG (Anthropic), Matryoshka embeddings + LlamaIndex, HyDE, Late Chunking, Agentic RAG.
- **Search index** (`tutorials/search/index.mdx`) — hybrid search+reranking on BEIR, V-JEPA video search, vector arithmetic, NER-powered search, multivector XTR.
- **Feature Engineering** (`tutorials/feature-engineering/`) — Feature Engineering 101 + Materialized Views (Geneva; `geneva-catalog.md`).
- **Demos** (`demos/index.mdx`) — Semantic.art (multimodal art discovery, hybrid + semantic routing), Wikipedia 41M Hybrid Search (FTS+vector at scale), natural-language Video Search.

## Recipe families (`ml-lancedb-vectordb-recipes`)

Repo sections: Build-from-Scratch, Multimodal, RAG, Vector Search, Chatbot, Evaluation, AI Agents, Recommender Systems.
- **RAG variants** — Contextual-RAG, HyDE, Late Chunking, Context Enrichment Window, LOTR, FLARE/FLAIR, Contextual Compression, RAG-on-PDF, RAG-using-Groq, RAG-with-watsonx, RAG_Reranking, cognee-RAG, GraphRAG; from-scratch: RAG-from-Scratch, Local-RAG (Llama3), Multi-Head-RAG, Agentic_RAG, Corrective-RAG (LangGraph), Matryoshka+LlamaIndex, multi-document-agentic-rag.
- **Agents** — AI-Email-Assistant (Composio), AI-Trends (CrewAI), Multi-source-Agent, SuperAgent (Autogen), Trip-planner (swarm), customer_support (LangGraph), fintech-ai-agent, reducing_hallucinations_ai_agents.
- **Recommender systems** — product / movie / arxiv / geospatial / music recommenders (embedding + ANN + filters).
- **Multimodal / image / video / audio search** — CLIP+DiffusionDB, multimodal_video_search, Jina-CLIP-v2 (food), Voyage×LanceDB, V-JEPA video, ImageBind (text/audio/image), SAM+CLIP, zero-shot object detection, ColPali vision retriever, Janus-Pro, OpenVINO acceleration; audio: Parler-TTS chatbot, podcast generation, speaker-mapped transcription.
- **Semantic / hybrid search** — Inbuilt-Hybrid-Search (BEIR), BM25+LanceDB, NER-powered semantic search, Vector Arithmetic, Reddit summarize+search, multivector XTR.
- **Evaluation** — RAGAs, HoneyHive×LanceDB, prompttools, evaluate_RAG, Chunking Analysis, Deepseek-R1 vs GPT-4o, ModernBERT comparison.
- **Chatbots / training-adjacent** — Multilingual RAG, talk-with-{github,podcast,wikipedia,youtube}; llm-pretraining-dataloading, PEFT/QLoRA fine-tuning, image-dataset→Lance CLI.
- **Partner platforms** — watsonx, Groq, Composio, CrewAI, Autogen, LangGraph, LlamaIndex, Cognee, OpenVINO, VoyageAI, Databricks DBRX, RASA. (Bindings live in `integrations-catalog.md`.)

## GraphRAG on Lance (`ml-lance-graph`)

Two distinct approaches — name which one you mean:
1. **Native `lance-graph`** — a Cypher-capable graph query engine in **Rust with Python (PyO3) bindings** that interprets Lance datasets as **property graphs** and compiles Cypher → **DataFusion SQL**. API: `GraphConfigBuilder().with_node_label("Person","person_id").with_relationship("FRIEND_OF","p1_id","p2_id").build()`; `CypherQuery(cypher).with_config(cfg).execute({"Person": tbl, "FRIEND_OF": tbl})` → `.to_pandas()`. Supports `MATCH`/`WHERE`/`RETURN`/`WITH`/`UNWIND`/`ORDER BY`/`LIMIT`, variable-length paths `*min..max` (cap 20 hops), a CSR adjacency index, and a `UnityCatalog` bridge (Delta+Parquet). **Vector + graph:** in-Cypher UDFs `vector_distance(a,b,metric)` / `vector_similarity(a,b,metric)` (L2/Cosine/Dot), or the explicit `VectorSearch::new("embedding").query_vector([…]).metric(Cosine).top_k(10).search(candidates)` builder. **GraphRAG pattern:** step 1 = Cypher traversal/filter for candidates; step 2 = vector rerank via Lance ANN — graph structure + semantic retrieval in **one serverless Lance store**, no separate graph DB. The `knowledge_graph` package operationalizes it (CLI + FastAPI, LLM extraction via `gpt-4o-mini`/heuristic, node/relationship tables persisted as Lance datasets). It is a *relational* graph engine — no built-in PageRank/Louvain; its ops are node filter/projection, multi-hop expand, joins, aggregation, variable-length traversal.
2. **Microsoft GraphRAG / cognee with LanceDB as the vector store** (recipes `examples/Graphrag`, `tutorials/GraphRAG_*`) — a hierarchical KG extracted from text with global/local search modes, using LanceDB only as the embedding store. Distinct from the native Cypher engine.

## Design rules
- **Map the goal to a proven pattern first** — pick from the families above, then hand the build to the subdomain experts; don't design from scratch when a recipe demonstrates it.
- **Recipes are references, not APIs** — re-verify code against the current SDK (`lancedb-docs-protocol.md`); many recipes predate the latest index/search surface.
- **Multimodal/agent/recommender all reduce to schema → index → search + rerank** — the use-case is the framing; the catalogs hold the mechanics.
- **Time-travel is a first-class feature, not a workaround** — versioning/tags power audit, reproducibility, and embedding A/B tests without data duplication.
- **Say which GraphRAG** — native Cypher-on-Lance (`lance-graph`) vs LanceDB-as-vector-store-under-MS-GraphRAG; they have different APIs and operational models.
- **Partner-platform apps bind via `integrations-catalog.md`** — the store stays LanceDB; the framework is the client.
