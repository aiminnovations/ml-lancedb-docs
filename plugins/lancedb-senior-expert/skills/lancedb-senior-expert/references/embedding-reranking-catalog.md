# Embedding + Reranking Catalog — the registry, every provider, the rerankers

> last-verified-against: docs `embedding/{index,quickstart}.mdx`, `integrations/embedding/*`, `integrations/reranking/*`, `reranking/{index,custom-reranker,eval}.mdx` + SDK `lancedb==0.30.0`, 2026-07-14
> Sources: `docs/embedding/*`, `docs/integrations/embedding/*`, `docs/reranking/*`; SDK `lancedb/embeddings/*`, `lancedb/rerankers/*`.
> Owner expert: `lancedb-search-expert`. ⚠️ = version/tier/SDK-verify at build (defaults drift; trust the SDK over prose).

## The embedding registry (auto-embedding)

`from lancedb.embeddings import get_registry` → the singleton `EmbeddingFunctionRegistry`. Fetch a provider **class** by alias and instantiate with `.create(**kwargs)`:
```python
from lancedb.pydantic import LanceModel, Vector
from lancedb.embeddings import get_registry

func = get_registry().get("openai").create(name="text-embedding-3-small")   # ndims() -> 1536

class Doc(LanceModel):
    text: str = func.SourceField()               # embedded on ingest
    vector: Vector(func.ndims()) = func.VectorField()

tbl = db.create_table("docs", schema=Doc, mode="overwrite")
tbl.add([{"text": "hello world"}])               # auto-embeds source
tbl.search("greetings").limit(1).to_pydantic(Doc)   # auto-embeds the query (OSS/Cloud)
```
Mechanics (`embeddings/base.py`, `registry.py`): `SourceField()`/`VectorField()` tag pydantic fields; on `add`, LanceDB embeds the source column; on `search(str)`, it embeds the query. The `EmbeddingFunctionConfig` is serialized into the Arrow table metadata (`b"embedding_functions"`), so a reopened table reconstructs its embedder automatically. `TextEmbeddingFunction` subclasses implement one method, `generate_embeddings(texts)`; `EmbeddingFunction` (multimodal) implements `compute_source_embeddings`/`compute_query_embeddings`/`ndims`. `max_retries` default 7.

⚠️ **Secrets:** sensitive keys (e.g. `api_key`) **cannot be hardcoded** in `.create()` — pass `"$var:api_key"` (set via `registry.set_var("api_key", …)`) or an env var, or you get `ValueError: Sensitive key ... cannot be set to a hardcoded value`. The native-guard/reviewer flags hardcoded keys.

⚠️ **Enterprise:** auto-embeds at **ingestion only**; query-time auto-embedding is not yet supported — generate the query vector manually (`func.generate_embeddings([q])[0]`) and pass it to `search`.

**Custom function:** subclass `TextEmbeddingFunction`/`EmbeddingFunction` + `@register("my-embedder")`, implement `generate_embeddings`/`ndims` (Python); TS extends `EmbeddingFunction<T>`; Rust implements the `EmbeddingFunction` trait + `db.embedding_registry().register(...)`.

## Providers (registry alias → class + key params)

| Alias | Class | Modality | Key params / defaults | Notes |
|---|---|---|---|---|
| `openai` | `OpenAIEmbeddings` | text | `name="text-embedding-ada-002"`, `dim`, `base_url` | ada→1536, 3-large→`dim or 3072`, 3-small→`dim or 1536`. Override `base_url` for OpenAI-compatible/Ollama servers. |
| `sentence-transformers` | `SentenceTransformerEmbeddings` | text | `name="all-MiniLM-L6-v2"`, `device="cpu"`, `normalize=True` | Local, no key. `ndims` probed. |
| `huggingface` | `TransformersEmbeddingFunction` | text | `name="colbert-ir/colbertv2.0"`, `device`, `trust_remote_code=False` | Any AutoModel; mean-pooled. ⚠️ `trust_remote_code=True` runs remote code — trusted repos only. |
| `colbert` | `ColbertEmbeddings` | text | default `colbert-ir/colbertv2.0` | Transformers subclass. |
| `cohere` | `CohereEmbeddingFunction` | text | `name="embed-multilingual-v2.0"`, `source_input_type="search_document"`, `query_input_type="search_query"` | Env `COHERE_API_KEY`. ⚠️ SDK default ≠ some doc prose — trust SDK. |
| `gemini-text` | `GeminiText` | text | `name="gemini-embedding-001"` (768), task types `retrieval_document`/`retrieval_query` | Env `GOOGLE_API_KEY` (`google-genai`). Alias is `gemini-text`. |
| `jina` | `JinaEmbeddings` | text+image | `name="jina-clip-v1"`, `api_key`/`JINA_API_KEY` | ⚠️ `ndims` fixed 768. URLs treated as images. |
| `voyageai` | `VoyageAIEmbeddingFunction` | text+image+video+contextual | `name` (required), `output_dimension` (multimodal-3.5 only) | Env `VOYAGE_API_KEY`. Families: text (`voyage-4/-lite/-large`, `3.5`, `law-2`, `code-2`), multimodal (`voyage-multimodal-3/-3.5`), contextual (`voyage-context-3`). |
| `bedrock-text` | `BedRockText` | text | `name="amazon.titan-embed-text-v1"`, `region`, `profile_name` | AWS boto3; titan-v1→1536, v2→1024. Alias `bedrock-text`. |
| `watsonx` | `WatsonxEmbeddings` | text | `name="ibm/slate-125m-english-rtrvr"`, `api_key`, `project_id`, `url` | Env `WATSONX_API_KEY`/`WATSONX_PROJECT_ID`. |
| `ollama` | `OllamaEmbeddings` | text | `name="nomic-embed-text"`, `host="http://localhost:11434"` | Local Ollama; `ndims` probed. |
| `instructor` | `InstructorEmbeddingFunction` | text | `name="hkunlp/instructor-base"`, `source_instruction`, `query_instruction` | Instruction-prefixed; optional int8 quantize. |
| `colpali` | `ColPaliEmbeddings` | multimodal **multivector** | `model_name="Metric-AI/ColQwen2.5-3b-…"`, `pooling_strategy="hierarchical"` | Late-interaction (text query ↔ image docs). Uses `MultiVector(func.ndims())`, not `Vector`. |
| `imagebind` | `ImageBindEmbeddings` | 6 modalities | `name="imagebind_huge"`, `ndims`=1024 | image/text/audio/depth/thermal/IMU; routes by file extension. |
| `open-clip` | `OpenClipEmbeddings` | text+image | `name="ViT-B-32"`, `pretrained="laion2b_s34b_b79k"`, `normalize=True` | CLIP text↔image; query can be text or PIL.Image. |

Also present ⚠️ (not always documented): `siglip`, `gte`, MLX `gte_mlx_model`. **Discipline:** pin the `name` + resulting `ndims()` before the index build; keep source/query `input_type` symmetric (the registry handles it; manual embedding must not).

## Rerankers (`reranking/*`, `lancedb/rerankers/*`)

Used as `table.search(q[, query_type=…]).rerank(reranker=r).to_list()`. All take `return_score="relevance"|"all"`, `column="text"`.

| Class | Provider | Key params / default model |
|---|---|---|
| `RRFReranker` | — (fusion) | `K=60`; **default hybrid reranker** (reciprocal rank fusion); hybrid only |
| `LinearCombinationReranker` | — (fusion) | `weight=0.7` (vector weight; FTS=1−weight); ⚠️ deprecated, prefer RRF; hybrid only |
| `MRRReranker` | — (fusion) | `weight_vector=0.5`, `weight_fts=0.5` (sum 1.0); hybrid **and** multivector (`rerank_multivector`) |
| `CohereReranker` | Cohere API | `model_name="rerank-english-v2.0"`, `top_n`, `COHERE_API_KEY`; hybrid/vector/fts |
| `CrossEncoderReranker` | sentence-transformers | `model_name="cross-encoder/ms-marco-TinyBERT-L-6"`, `device`; hybrid/vector/fts |
| `ColbertReranker` | local ColBERT | `model_name="colbert-ir/colbertv2.0"`, `device`; hybrid/vector/fts |
| `JinaReranker` | Jina API | `model_name="jina-reranker-v2-base-multilingual"`, `JINA_API_KEY`; hybrid/vector/fts |
| `VoyageAIReranker` | Voyage API | `model_name` (e.g. `rerank-2`/`rerank-2-lite`), `VOYAGE_API_KEY`; hybrid/vector/fts |
| `AnswerdotaiRerankers` | AnswerDotAI lib | `model_type="colbert"`, `model_name="answerdotai/answerai-colbert-small-v1"` |
| `OpenaiReranker` | OpenAI chat (⚠️ experimental) | `model_name="gpt-4-turbo-preview"`, `OPENAI_API_KEY` — LLM-as-reranker, not a rerank model |

**Multi-vector reranking:** `reranker.rerank_multivector([res1, res2, res3], deduplicate=True)` across vector columns (`reranking/index.mdx`).

## Custom rerankers (`reranking/custom-reranker.mdx`)

Subclass `Reranker`; must implement `rerank_hybrid(self, query, vector_results, fts_results)` (both are **PyArrow Tables**). Optionally `rerank_vector`/`rerank_fts`. Base `merge_results()` concatenates + dedups by first-seen `_rowid` (ignores scores); implement custom merging to use scores or support `return_score="all"`. Pass `return_score` to `super().__init__()`.

## Choosing a reranker (`reranking/eval.mdx`)

Two evaluation strategies: **score-based** (weighted linear combo — scores must be normalized; dense/sparse spaces aren't comparable) and **relevance-based** (discard scores, recompute query-doc relevance, e.g. Cross Encoder). Sample hit-rate@k on ~800 hybrid queries (ada-002, vector baseline 0.64): Cohere top-3 **0.81**, LinearCombination 0.73, CrossEncoder 0.71, ColBERT 0.68. **No universally best reranker** — it's dataset/latency dependent; measure on your data.

## Design rules
- **Prefer the registry (`get_registry`) for auto-embedding** — one place pins the model + dims; ingest and query stay symmetric; the config travels in the table metadata.
- **Never hardcode API keys** — `$var:` or env; the guard/reviewer blocks hardcoded secrets.
- **Pin `name` + `ndims()` before the index build** — a model swap that changes dims is a re-embed + re-index.
- **Match modality to provider** — text (OpenAI/Cohere/SentenceTransformers/Voyage), image/multimodal (OpenCLIP/ImageBind/Jina/Voyage-multimodal), late-interaction (ColPali/ColBERT → multivector column).
- **RRF is the hybrid default; measure a domain reranker** — Cohere/Cross-Encoder/Voyage often beat fusion, at a latency cost; verify hit-rate@k on your corpus.
- **Enterprise: embed the query manually** — query-time auto-embedding is ingest-only there.
