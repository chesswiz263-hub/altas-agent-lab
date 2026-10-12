# ATLAS architecture (v0.4)

ATLAS combines a single-origin FastAPI/vanilla JavaScript workbench with a synchronous agent loop, a bounded local durable queue, three allowlisted tools, persistent SQLite document and event tables, and optional neural embeddings.

## Main execution paths

- **Legacy SSE (`/api/*/stream`)**: Executes the v0.3 model/tool pipeline in the web request, streams events, then writes a run completion record.
- **Durable execution (`/api/jobs`)**: Validates and stores a request as `queued`; a single background task claims it, writes a `runs` entry, appends numbered events, then commits completion. The browser polls `/api/jobs/{id}/events?after=CURSOR` and can send a cancellation request.
- **Recovery**: On startup, jobs left in `running` state are labeled `interrupted` rather than reissued. Queued jobs are still runnable. Cancellation interrupts the active asyncio task; provider network requests might already be billable.
- **Optional memory**: Only when `use_memory=true` on a queued run, up to three related user-authored notes enter the model prompt as bounded, clearly labeled untrusted data. Memory content is not automatically ingested or promoted to policy instructions.

## Storage layout

- `documents`, `chunks`, `chunks_fts`, `chunk_vectors`, `semantic_vectors`: document knowledge and retrieval layers.
- `runs`, `events`: execution telemetry; original user objective and numbered events stay durable.
- `jobs`: request JSON, lifecycle state, cancellation flag and timestamps.
- `memories`, `memories_fts`: manually entered plaintext notes and their full-text index.

SQLite is suitable for this project's local single-process operation and tests. It is not a substitute for a multi-worker queue lease service, tenant-isolated PostgreSQL deployment, or ANN index.

## Agent and evaluation semantics

The single agent uses a bounded sequence of provider completions and tool observations. The team is four sequential stage agents: researcher, analyst, critic, synthesizer. Offline non-research roles are deterministic and explicitly **simulated**. The auto-router uses inspectable task heuristics; it is not learned.

BM25 full-text search and lexical hashed n-gram vectors are offline-capable. Neural semantic search requires `sentence-transformers` and a model download performed only by explicit index commands; versioned embeddings are stored in SQLite and scanned using cosine. The claim inspector verifies citation IDs, superficial token overlap, and numeric literals. The ten-case v0.4 suite evaluates the *heuristic's labels*, not actual factual entailment.

## Trust boundaries

Browser and API requests are untrusted. Optional single-token authentication verifies API requests through a constant-time comparison. Model outputs, memory notes, indexed documents, source passages and intermediary agents are not trusted instructions. Tool execution is restricted to a known allowlist, and API keys remain server-side. All data is single-workspace plaintext SQLite: do not use for sensitive multi-user production systems.


## v0.6: public demo is not the private server

The public `docs/index.html` site is independent of the FastAPI application. It uses only its bundled, read-only `docs/demo/{corpus,engine,app}.js` scripts and CSS. BM25 ranking, excerpt selection and quotation checks execute locally in each visitor's browser. No private API endpoints are accessed.

The original v0.5 `static/` UI and FastAPI routes remain intended for a private Codespace or an authenticated hosted operator. **Do not** assume a GitHub Pages site exposes the private FastAPI app. The public demo deliberately does not provide paid-model execution, document upload, persistent memory, or arbitrary tools.
